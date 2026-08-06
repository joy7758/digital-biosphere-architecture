"""method-v2 pilot-readiness experiment runner (fail-closed dispatch).

Clean-room replacement for the invalidated PR #12 experiment. Hard rules:

* NO ``expected_outcome`` / ``forced_result`` / ``desired_result`` anywhere;
* arm assignment comes from the task sequence, never from results;
* execution results come from ``worker.execute_task`` (deterministic);
* every HistoryStore answer is parsed as an envelope (ok / null_semantics /
  result.events / error) -- never iterated at top level;
* NO compensating branch that forces a decision change on empty history.

Dispatch semantics (AHRP-assisted arm only), fixed in the protocol:

* ``NO_RECORD`` means UNKNOWN / COLD_START. Never CLEAN, SAFE or TRUSTED.
* ``WITHHELD`` means RECORD_EXISTS_BUT_NOT_DISCLOSED. Never permission to
  proceed.
* ``QUERY_ERROR`` is unknown. Fail closed.
* An alternative candidate is dispatchable ONLY when its own query status
  is OK and no veto evidence exists (KNOWN_NON_VETOED_ALTERNATIVE).
* A HIGH-risk task with no known dispatchable candidate is BLOCKed and the
  worker is never invoked; a MEDIUM-risk task becomes MANUAL_REVIEW and is
  never auto-executed; a LOW-risk task may cold-start-explore only with all
  four sandbox flags set.
* The runner never emits verification records. It writes UNVERIFIED
  experience events only; verification is a separate post-run step
  (``verify_run_records.py``).

Run:  python3 run_experiment.py   (from any working directory)
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import history_loader
import worker

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config")
DATA = os.path.join(HERE, "data")
EVIDENCE = os.path.join(HERE, "evidence")

AGENT_VERSION = "1.0.0"
FORBIDDEN_TASK_FIELDS = ("expected_outcome", "forced_result", "desired_result")
FAILURE_CLASS = ("FAILURE", "TIMEOUT", "CANCELLED")
DISPOSITIONS = ("DISPATCH", "LOW_RISK_EXPLORATION", "BLOCK", "MANUAL_REVIEW")
EXPLORATION_FLAGS = ("cold_start_candidate", "reversible", "sandboxed",
                     "limited_permissions")
UNKNOWN_STATUSES = ("NO_RECORD", "WITHHELD", "QUERY_ERROR")


@dataclass(frozen=True)
class DispatchDecision:
    """One dispatch disposition. Experiment-layer object; NOT part of the
    AHRP v0.1 schema."""
    disposition: str
    selected_agent: Optional[str]
    reason: str
    supporting_event_references: List[str] = field(default_factory=list)


# ---------------------------------------------------------------- utilities
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(record: Dict[str, Any]) -> str:
    """SHA-256 over the canonical JSON of the record without record_hash."""
    payload = {k: v for k, v in record.items() if k != "record_hash"}
    blob = json.dumps(payload, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FsyncedJsonlWriter:
    """Append-only JSONL writer with flush + os.fsync per record."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._handle = open(path, "a", encoding="utf-8")

    def write(self, record: Dict[str, Any]) -> None:
        self._handle.write(json.dumps(record, sort_keys=True) + "\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self._handle.close()


# ------------------------------------------------------------- preconditions
def check_capability_commitment() -> str:
    """Fail closed unless the matrix still matches its pre-run commitment."""
    matrix_path = os.path.join(CONFIG, "capability-matrix.json")
    commitment_path = os.path.join(CONFIG, "capability-matrix.commitment")
    with open(commitment_path, "r", encoding="utf-8") as handle:
        committed = handle.read().strip().split()[0]
    actual = file_sha256(matrix_path)
    if actual != committed:
        raise SystemExit(
            f"CAPABILITY_MATRIX_COMMITMENT_MISMATCH committed={committed} "
            f"actual={actual}")
    return actual


def load_tasks() -> List[Dict[str, Any]]:
    tasks = history_loader.load_jsonl(os.path.join(CONFIG, "tasks.jsonl"))
    for task in tasks:
        for field_name in FORBIDDEN_TASK_FIELDS:
            if field_name in task:
                raise SystemExit(
                    f"FORBIDDEN_TASK_FIELD task={task['task_id']} "
                    f"field={field_name}")
    tasks.sort(key=lambda t: t["sequence"])
    return tasks


def arm_for(task: Dict[str, Any]) -> str:
    """Fixed, result-independent allocation: odd -> No-AHRP, even -> AHRP."""
    return "No-AHRP" if task["sequence"] % 2 == 1 else "AHRP-assisted"


def naive_initial_agent(task: Dict[str, Any]) -> str:
    candidates = task["candidate_agents"]
    return candidates[(task["sequence"] - 1) % len(candidates)]


# --------------------------------------------------------------- veto rules
def veto_events_for(events: List[Dict[str, Any]], task: Dict[str, Any]
                    ) -> Tuple[List[str], str]:
    """Return (supporting_event_ids, rule) from disclosed summary events.

    Rule A (CAPABILITY_LIMIT_VETO): >=2 independently verified failure-class
    events with failure_category CAPABILITY_LIMIT for this agent/version and
    this task_type (the query already scopes all three).
    Rule B (POLICY_RESTRICTION_BLOCK): HIGH-risk task and any independently
    verified failure-class event with failure_category POLICY_RESTRICTION.
    Only summary projection fields are consumed.
    """
    capability_limit_ids = []
    policy_restriction_ids = []
    for event in events:
        if event.get("result_status") not in FAILURE_CLASS:
            continue
        if not event.get("has_independent_verification"):
            continue
        category = event.get("failure_category")
        if category == "CAPABILITY_LIMIT":
            capability_limit_ids.append(event["event_id"])
        elif category == "POLICY_RESTRICTION":
            policy_restriction_ids.append(event["event_id"])
    if len(capability_limit_ids) >= 2:
        return capability_limit_ids, "RULE_A_CAPABILITY_LIMIT_VETO"
    if task["risk_level"] == "HIGH" and policy_restriction_ids:
        return policy_restriction_ids, "RULE_B_POLICY_RESTRICTION_BLOCK"
    return [], ""


# ------------------------------------------------------------------ queries
def timed_query(store, identity_ref: str, task: Dict[str, Any],
                seq_counter: List[int], reason: str
                ) -> Tuple[history_loader.QueryOutcome, Dict[str, Any]]:
    """One measured, logged filtered-list query through the real engine."""
    params = {"identity_ref": identity_ref, "agent_version": AGENT_VERSION,
              "task_type": task["task_type"],
              "require_independent_verification": True}
    started = time.perf_counter()
    envelope = store.query_events(**params)
    latency_ms = (time.perf_counter() - started) * 1000.0
    if not envelope.get("ok", False):
        outcome = history_loader.QueryOutcome(
            "QUERY_ERROR", [],
            error_code=envelope.get("error", {}).get("code", ""))
    else:
        semantics = envelope.get("null_semantics")
        withheld = envelope.get("selective_disclosure", {}).get(
            "withheld_count", 0)
        if semantics == "WITHHELD":
            outcome = history_loader.QueryOutcome(
                "WITHHELD", [], withheld_count=withheld)
        elif semantics == "NO_RECORD":
            outcome = history_loader.QueryOutcome(
                "NO_RECORD", [], withheld_count=withheld)
        else:
            outcome = history_loader.QueryOutcome(
                "OK", envelope.get("result", {}).get("events", []),
                withheld_count=withheld)
    seq_counter[0] += 1
    query_chars = len(json.dumps(params, sort_keys=True)) + \
        len(json.dumps(envelope, sort_keys=True))
    record = {
        "query_id": f"q-m2-{seq_counter[0]:04d}",
        "query_mode": "SummaryList",
        "purpose": reason,
        "task_id": task["task_id"],
        "identity_ref": identity_ref,
        "agent_version": AGENT_VERSION,
        "task_type": task["task_type"],
        "ok": envelope.get("ok", False),
        "null_semantics": envelope.get("null_semantics")
        if envelope.get("ok") else None,
        "error_code": outcome.error_code or None,
        "withheld_count": outcome.withheld_count,
        "event_count": len(outcome.events),
        "latency_ms": round(latency_ms, 6),
        "query_chars": query_chars,
        "token_estimate": (query_chars + 3) // 4,
        "recorded_at": utc_now_iso(),
    }
    return outcome, record


def timed_summary(store, identity_ref: str, task: Dict[str, Any],
                  seq_counter: List[int],
                  query_log: List[Dict[str, Any]]) -> None:
    """One measured Experience Summary query (summary channel)."""
    started = time.perf_counter()
    envelope = store.summary(identity_ref, AGENT_VERSION)
    latency_ms = (time.perf_counter() - started) * 1000.0
    seq_counter[0] += 1
    params = {"identity_ref": identity_ref, "agent_version": AGENT_VERSION}
    query_chars = len(json.dumps(params, sort_keys=True)) + \
        len(json.dumps(envelope, sort_keys=True))
    query_log.append({
        "query_id": f"q-m2-{seq_counter[0]:04d}",
        "query_mode": "Summary",
        "purpose": "pre-decision-summary",
        "task_id": task["task_id"],
        "identity_ref": identity_ref,
        "agent_version": AGENT_VERSION,
        "task_type": task["task_type"],
        "ok": envelope.get("ok", False),
        "null_semantics": envelope.get("null_semantics")
        if envelope.get("ok") else None,
        "error_code": envelope.get("error", {}).get("code")
        if not envelope.get("ok", False) else None,
        "withheld_count": envelope.get("selective_disclosure", {}).get(
            "withheld_count", 0),
        "event_count": None,
        "latency_ms": round(latency_ms, 6),
        "query_chars": query_chars,
        "token_estimate": (query_chars + 3) // 4,
        "recorded_at": utc_now_iso(),
    })


# ---------------------------------------------------- fail-closed dispatch
def unknown_fallback(task: Dict[str, Any], status: str,
                     detail: str) -> DispatchDecision:
    """Disposition for an UNKNOWN initial-agent answer, by risk level.

    NO_RECORD / WITHHELD / QUERY_ERROR are never dispatchable states.
    """
    risk = task["risk_level"]
    if risk == "LOW":
        if all(task.get(flag) is True for flag in EXPLORATION_FLAGS):
            return DispatchDecision(
                "LOW_RISK_EXPLORATION", naive_initial_agent(task),
                f"LOW_RISK_EXPLORATION:{status}:{detail}:"
                "SANDBOX_FLAGS_COMPLETE", [])
        return DispatchDecision(
            "BLOCK", None,
            f"BLOCK:{status}:{detail}:SANDBOX_FLAGS_INCOMPLETE", [])
    if risk == "MEDIUM":
        return DispatchDecision(
            "MANUAL_REVIEW", None,
            f"MANUAL_REVIEW_REQUIRED:{status}:{detail}:"
            "NO_AUTO_EXECUTION_WITHOUT_HUMAN_APPROVAL", [])
    return DispatchDecision("BLOCK", None, f"BLOCK:{status}:{detail}", [])


def screen_alternatives(store, task: Dict[str, Any], excluded: str,
                        query_log: List[Dict[str, Any]], seq_counter: List[int]
                        ) -> Tuple[Optional[str], List[str]]:
    """First candidate (declared order) whose query status is OK and which
    carries no veto evidence (KNOWN_NON_VETOED_ALTERNATIVE).

    NO_RECORD, WITHHELD and QUERY_ERROR answers are UNKNOWN and therefore
    never selectable. Returns (agent_or_None, disclosed_event_ids).
    """
    for candidate in task["candidate_agents"]:
        if candidate == excluded:
            continue
        outcome, record = timed_query(
            store, candidate, task, seq_counter,
            reason="alternative-screen-fail-closed")
        query_log.append(record)
        if outcome.status != "OK":
            continue  # unknown: NO_RECORD / WITHHELD / QUERY_ERROR
        supporting, rule = veto_events_for(outcome.events, task)
        if rule:
            continue  # known-vetoed: not dispatchable
        return candidate, [e["event_id"] for e in outcome.events]
    return None, []


def ahrp_decision(store, task: Dict[str, Any], initial: str,
                  query_log: List[Dict[str, Any]], seq_counter: List[int]
                  ) -> DispatchDecision:
    """Fail-closed decision support strictly from disclosed, independently
    verified history."""
    timed_summary(store, initial, task, seq_counter, query_log)
    outcome, record = timed_query(store, initial, task, seq_counter,
                                  reason="initial-agent-screen")
    query_log.append(record)

    if outcome.status in UNKNOWN_STATUSES:
        detail = outcome.error_code \
            if outcome.status == "QUERY_ERROR" else "UNKNOWN"
        # HIGH / MEDIUM unknown answers trigger candidate screening first:
        # a KNOWN, disclosed, non-vetoed alternative may still be dispatched.
        if task["risk_level"] in ("HIGH", "MEDIUM"):
            alternative, disclosed = screen_alternatives(
                store, task, initial, query_log, seq_counter)
            if alternative is not None:
                return DispatchDecision(
                    "DISPATCH", alternative,
                    f"KNOWN_NON_VETOED_ALTERNATIVE_AFTER_INITIAL_"
                    f"{outcome.status}", disclosed)
        return unknown_fallback(task, outcome.status, detail)

    supporting, rule = veto_events_for(outcome.events, task)
    if not rule:
        return DispatchDecision("DISPATCH", initial,
                                "NO_VETO_EVIDENCE_IN_HISTORY", [])

    alternative, disclosed = screen_alternatives(
        store, task, initial, query_log, seq_counter)
    if alternative is not None:
        return DispatchDecision(
            "DISPATCH", alternative,
            f"{rule}:KNOWN_NON_VETOED_ALTERNATIVE", supporting + disclosed)
    if task["risk_level"] == "MEDIUM":
        return DispatchDecision(
            "MANUAL_REVIEW", None,
            f"{rule}:NO_KNOWN_ALTERNATIVE:MANUAL_REVIEW_REQUIRED:"
            "NO_AUTO_EXECUTION_WITHOUT_HUMAN_APPROVAL", supporting)
    # HIGH and LOW: a known-vetoed initial agent with no known alternative
    # is never dispatchable, regardless of sandbox flags (veto is KNOWN bad
    # history, not cold start).
    return DispatchDecision("BLOCK", None,
                            f"{rule}:NO_KNOWN_ALTERNATIVE", supporting)


# --------------------------------------------------------------- execution
def run_controlled_execution(task: Dict[str, Any], final_agent: str,
                             matrix: Dict[str, Any], started_at: str
                             ) -> Tuple[Dict[str, Any], str]:
    """Execute through the deterministic worker; write a real evidence file;
    return (execution_record, evidence_sha256)."""
    result_status, failure_category, rule = worker.execute_task(
        task, final_agent, matrix)
    finished_at = utc_now_iso()
    evidence_doc = {
        "task_id": task["task_id"],
        "selected_agent": final_agent,
        "task_requirements": task["requirements"],
        "capability_match": {
            "agent_key": worker.agent_key(final_agent, AGENT_VERSION),
            "task_type": task["task_type"],
            "required_level": task["requirements"]["min_capability_level"],
            "declared_capability": matrix["agents"][
                worker.agent_key(final_agent, AGENT_VERSION)]["capabilities"]
            .get(task["task_type"]),
        },
        "environment": {"environment_id": matrix["environment"]
                        ["environment_id"]},
        "result": result_status,
        "failure_category": failure_category,
        "deciding_rule": rule,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    evidence_path = os.path.join(EVIDENCE, "executions",
                                 f"{task['task_id']}.json")
    with open(evidence_path, "w", encoding="utf-8") as handle:
        json.dump(evidence_doc, handle, indent=2, sort_keys=True)
        handle.write("\n")
    execution = {
        "task_id": task["task_id"],
        "sequence": task["sequence"],
        "selected_agent": final_agent,
        "result_status": result_status,
        "failure_category": failure_category,
        "deciding_rule": rule,
        "evidence_path": os.path.relpath(evidence_path, HERE),
        "started_at": started_at,
        "finished_at": finished_at,
    }
    return execution, file_sha256(evidence_path)


# --------------------------------------------------------------------- main
def main() -> None:
    matrix_hash = check_capability_commitment()
    tasks = load_tasks()
    matrix = json.load(open(os.path.join(CONFIG, "capability-matrix.json"),
                            encoding="utf-8"))
    store = history_loader.build_store()

    for name in ("allocations.jsonl", "pre-query-decisions.jsonl",
                 "queries.jsonl", "post-query-decisions.jsonl",
                 "controlled-executions.jsonl",
                 "experience-events-unverified.jsonl",
                 "experience-events.jsonl", "verification-records.jsonl",
                 "non-dispatched-tasks.jsonl"):
        path = os.path.join(DATA, name)
        if os.path.exists(path):
            os.remove(path)
    # Stale execution evidence from earlier runs must never survive: a task
    # that is now BLOCKed must leave no evidence file behind.
    executions_dir = os.path.join(EVIDENCE, "executions")
    for name in os.listdir(executions_dir):
        if name.startswith("task-") and name.endswith(".json"):
            os.remove(os.path.join(executions_dir, name))

    allocations = FsyncedJsonlWriter(os.path.join(DATA, "allocations.jsonl"))
    pre_writer = FsyncedJsonlWriter(os.path.join(DATA,
                                                 "pre-query-decisions.jsonl"))
    query_writer = FsyncedJsonlWriter(os.path.join(DATA, "queries.jsonl"))
    post_writer = FsyncedJsonlWriter(os.path.join(DATA,
                                                  "post-query-decisions.jsonl"))
    exec_writer = FsyncedJsonlWriter(os.path.join(DATA,
                                                  "controlled-executions.jsonl"))
    event_writer = FsyncedJsonlWriter(
        os.path.join(DATA, "experience-events-unverified.jsonl"))
    nondispatched_writer = FsyncedJsonlWriter(
        os.path.join(DATA, "non-dispatched-tasks.jsonl"))

    query_log: List[Dict[str, Any]] = []
    seq_counter = [0]          # query ids
    shadow_seq = [0]           # shadow protocol monotonic sequence
    worker_invocations = 0
    disposition_counts = {d: 0 for d in DISPOSITIONS}
    run_started = utc_now_iso()

    for task in tasks:
        arm = arm_for(task)
        initial = naive_initial_agent(task)
        decision_start = time.perf_counter()

        if arm == "No-AHRP":
            # Baseline arm: naive selection, no history consulted, always
            # dispatched (this asymmetry IS the comparison).
            decision = DispatchDecision(
                "DISPATCH", initial, "NAIVE_SELECTION_NO_HISTORY_CONSULTED",
                [])
        else:
            # Two-phase shadow protocol: commit the pre-query decision to
            # durable storage BEFORE any history query happens.
            shadow_seq[0] += 1
            pre_record = {
                "task_id": task["task_id"],
                "candidate_agents": task["candidate_agents"],
                "selected_agent_before_query": initial,
                "selection_reason_before_query":
                    "DETERMINISTIC_NAIVE_SEQUENCE_SELECTION",
                "recorded_at": utc_now_iso(),
                "monotonic_sequence": shadow_seq[0],
            }
            pre_record["record_hash"] = canonical_hash(pre_record)
            pre_writer.write(pre_record)

            query_start = utc_now_iso()
            decision = ahrp_decision(store, task, initial, query_log,
                                     seq_counter)
            query_end = utc_now_iso()
            for record in query_log:
                if "persisted" not in record:
                    record["pre_query_record_hash"] = pre_record["record_hash"]
                    record["query_started_after_pre_query"] = \
                        record["recorded_at"] >= pre_record["recorded_at"]
                    query_writer.write(record)
                    record["persisted"] = True

            shadow_seq[0] += 1
            post_record = {
                "task_id": task["task_id"],
                "pre_query_record_hash": pre_record["record_hash"],
                "query_id_range": [
                    r["query_id"] for r in query_log
                    if r.get("pre_query_record_hash") ==
                    pre_record["record_hash"]],
                "disposition": decision.disposition,
                "selected_agent_after_query": decision.selected_agent,
                "selection_reason_after_query": decision.reason,
                "decision_changed": decision.selected_agent != initial,
                "supporting_event_references":
                    decision.supporting_event_references,
                "query_window": {"started_at": query_start,
                                 "ended_at": query_end},
                "recorded_at": utc_now_iso(),
                "monotonic_sequence": shadow_seq[0],
            }
            post_record["record_hash"] = canonical_hash(post_record)
            post_writer.write(post_record)

        decision_ms = (time.perf_counter() - decision_start) * 1000.0
        disposition_counts[decision.disposition] += 1
        allocations.write({
            "task_id": task["task_id"],
            "sequence": task["sequence"],
            "arm": arm,
            "risk_level": task["risk_level"],
            "initial_agent": initial,
            "final_agent": decision.selected_agent,
            "disposition": decision.disposition,
            "decision_changed": decision.selected_agent != initial,
            "decision_reason": decision.reason,
            "decision_time_ms": round(decision_ms, 6),
            "allocation_basis":
                "SEQUENCE_ODD_NO_AHRP" if arm == "No-AHRP"
                else "SEQUENCE_EVEN_AHRP_ASSISTED",
            "recorded_at": utc_now_iso(),
        })

        if decision.disposition in ("BLOCK", "MANUAL_REVIEW"):
            # Not dispatched: no worker invocation, no execution evidence,
            # no experience event, no verification record.
            nondispatched_writer.write({
                "task_id": task["task_id"],
                "arm": arm,
                "risk_level": task["risk_level"],
                "disposition": decision.disposition,
                "reason": decision.reason,
                "candidate_agents": task["candidate_agents"],
                "query_ids": [r["query_id"] for r in query_log
                              if r["task_id"] == task["task_id"]],
                "recorded_at": utc_now_iso(),
            })
            continue

        started_at = utc_now_iso()
        execution, evidence_hash = run_controlled_execution(
            task, decision.selected_agent, matrix, started_at)
        worker_invocations += 1
        execution["arm"] = arm
        execution["disposition"] = decision.disposition
        execution["decision_reason"] = decision.reason
        exec_writer.write(execution)

        # UNVERIFIED Experience Event for this controlled execution,
        # referencing the REAL evidence file hash (never a placeholder).
        # The runner never emits verification records and never claims a
        # VERIFIED status; verification happens post-run in
        # verify_run_records.py.
        event = {
            "schema_version": "0.1.0",
            "event_id": f"evt-run-{task['task_id']}",
            "agent_reference": {"identity_source": "DBOS",
                                "identity_ref": decision.selected_agent},
            "agent_version": AGENT_VERSION,
            "task_type": task["task_type"],
            "action_type": "EXECUTE",
            "result_status": execution["result_status"],
            "occurred_at": execution["finished_at"],
            "recorded_at": utc_now_iso(),
            "evidence_references": [{
                "source": "TITMAS_EVIDENCE",
                "version": "1.0",
                "reference_id": f"exec-{task['task_id']}",
                "hash": f"sha256:{evidence_hash}",
                "availability_status": "AVAILABLE",
            }],
            "verification_references": [],
            "disclosure": {"disclosure_scope": "PUBLIC",
                           "declared_by": "method-v2-runner"},
        }
        if execution["result_status"] in FAILURE_CLASS:
            event["failure_category"] = execution["failure_category"]
        event_writer.write(event)

    for writer in (allocations, pre_writer, query_writer, post_writer,
                   exec_writer, event_writer, nondispatched_writer):
        writer.close()

    print(json.dumps({
        "status": "RUN_COMPLETE",
        "capability_matrix_sha256": matrix_hash,
        "tasks": len(tasks),
        "queries": len(query_log),
        "worker_invocations": worker_invocations,
        "dispositions": disposition_counts,
        "verification_records_written_by_runner": 0,
        "run_started": run_started,
        "run_finished": utc_now_iso(),
    }, indent=2))


if __name__ == "__main__":
    main()
