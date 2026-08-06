#!/usr/bin/env python3
"""AHRP Internal Orchestrator Integration Trial v0.1 -- trial runner.

AHRP 内部编排器集成试验 v0.1。

Answers ONE question only:

    Can a programmatic orchestrator integrate the frozen AHRP v0.1 query
    interface and bind returned history to auditable delegation decisions?

程序化编排器能否集成冻结的 AHRP v0.1 查询接口，并将返回的历史记录
绑定到可审计的委派决策？

It does NOT answer whether a model-based or autonomous agent voluntarily
adopts AHRP, and it does NOT answer whether AHRP improves success rates.
The orchestrator and workers are programmatic components (executable role
implementations), not autonomous agents.

Phases:
    NO_AHRP_MODE      baseline: static type routing, AHRP reads forbidden
    AHRP_ASSISTED_MODE: the configured AHRP-assisted execution path lets
                      the programmatic orchestrator query the real
                      (unmodified) AHRP HistoryStore before delegating

Deterministic by construction: fixed task set, fixed seed history,
deterministic clock (task-index derived timestamps), workers whose results
depend only on task requirements and their declared boundary.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

EXP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EXP_ROOT.parent.parent

for path in (str(REPO_ROOT), str(REPO_ROOT / "AHRP")):
    if path not in sys.path:
        sys.path.insert(0, path)

from query.engine import HistoryStore  # noqa: E402
from validator.core import (  # noqa: E402
    validate_experience_event,
    validate_verification_record,
)

from orchestrator import (  # noqa: E402
    CANDIDATES_BY_TYPE,
    ForbiddenHistoryStore,
    OrchestratorAgent,
)
from workers import (  # noqa: E402
    CodingWorker,
    DataProcessingWorker,
    ResearchWorker,
    ReviewWorker,
)

TRIAL_ID = "ahrp-internal-orchestrator-integration-v0.1"
POST_RUN_VERIFIER_NAME = "integration-trial-post-run-verifier"
VERIFIER_CLASS = "SYSTEM_BENCHMARK"

TASK_TYPE_MAP = {
    "coding": "CODING",
    "research": "RESEARCH",
    "review": "VERIFICATION",
    "data_processing": "DATA_PROCESSING",
}


# --------------------------------------------------------------------------
# configuration loading
def load_config() -> dict:
    roster = json.loads((EXP_ROOT / "config" / "agent-roster.json").read_text())
    tasks = json.loads((EXP_ROOT / "config" / "tasks.json").read_text())["tasks"]
    return {"roster": roster, "tasks": tasks}


def agent_versions(roster: dict) -> dict:
    return {a["agent_id"]: a["agent_version"] for a in roster["agents"]}


def build_workers(roster: dict) -> dict:
    by_id = {a["agent_id"]: a for a in roster["agents"]}
    return {
        "did:example:worker-alpha": CodingWorker(by_id["did:example:worker-alpha"]),
        "did:example:worker-beta": ResearchWorker(by_id["did:example:worker-beta"]),
        "did:example:worker-gamma": ReviewWorker(by_id["did:example:worker-gamma"]),
    }


# --------------------------------------------------------------------------
# AHRP store bootstrap (unmodified AHRP v0.1)
def load_seeds() -> tuple:
    events = [
        json.loads(line)
        for line in (EXP_ROOT / "config" / "history-events.jsonl")
        .read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    verifications = [
        json.loads(line)
        for line in (EXP_ROOT / "config" / "history-verifications.jsonl")
        .read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    return events, verifications


def build_store() -> HistoryStore:
    """Validate every seed with the AHRP Validator, then ingest."""
    store = HistoryStore()
    events, verifications = load_seeds()
    for event in events:
        result = validate_experience_event(event)
        if not result.valid:
            raise SystemExit(f"TRIAL_ABORTED: invalid seed event "
                             f"{event.get('event_id')}: {result.errors}")
        store.ingest_event(event)
    for verification in verifications:
        result = validate_verification_record(verification)
        if not result.valid:
            raise SystemExit(f"TRIAL_ABORTED: invalid seed verification "
                             f"{verification.get('verification_id')}: {result.errors}")
        store.ingest_verification(verification)
    return store


# --------------------------------------------------------------------------
# deterministic clock
def occurred_at(phase: str, index: int) -> str:
    hour = "01" if phase == "NO_AHRP_MODE" else "02"
    return f"2026-08-07T{hour}:{index:02d}:00Z"


# --------------------------------------------------------------------------
# run-event recording (AHRP_ASSISTED_MODE only)
def make_run_event(task: dict, selected_agent: str, versions: dict,
                   result: dict, timestamp: str, evidence_hash: str) -> dict:
    event_id = f"evt-trial-run-{task['task_id']}"
    event = {
        "schema_version": "0.1.0",
        "event_id": event_id,
        "agent_reference": {
            "identity_source": "DBOS",
            "identity_ref": selected_agent,
        },
        "agent_version": versions[selected_agent],
        "task_type": TASK_TYPE_MAP[task["task_type"]],
        "action_type": "EXECUTE",
        "result_status": result["status"],
        "occurred_at": timestamp,
        "evidence_references": [
            {
                "source": "TITMAS_EVIDENCE",
                "version": "1.0",
                "reference_id": f"ev-trial-run-{task['task_id']}",
                "hash": f"sha256:{evidence_hash}",
                "availability_status": "AVAILABLE",
            }
        ],
        "verification_references": [
            {
                "verification_id": f"ver-trial-run-{task['task_id']}",
                "verifier_name": POST_RUN_VERIFIER_NAME,
            }
        ],
        "disclosure": {
            "disclosure_scope": "PUBLIC",
            "declared_by": TRIAL_ID,
        },
    }
    if result.get("failure_category"):
        event["failure_category"] = result["failure_category"]
    return event


def make_run_verification(task: dict, selected_agent: str, versions: dict,
                          timestamp: str) -> dict:
    return {
        "schema_version": "0.1.0",
        "verification_id": f"ver-trial-run-{task['task_id']}",
        "verifier": {
            "verifier_name": POST_RUN_VERIFIER_NAME,
            "verifier_class": VERIFIER_CLASS,
        },
        "verification_type": "EVENT_CONFIRMATION",
        "verification_status": "VERIFIED",
        "verified_at": timestamp,
        "scope": {
            "subject_event_id": f"evt-trial-run-{task['task_id']}",
            "subject_type": "EXPERIENCE_EVENT",
            "agent_ref": selected_agent,
            "agent_version": versions[selected_agent],
            "covered_aspect": "FULL_EVENT",
        },
        "self_verification": False,
        "authorization_effect": "NONE",
    }


def write_evidence_body(out_root: Path, task: dict, selected_agent: str,
                        result: dict) -> str:
    event_id = f"evt-trial-run-{task['task_id']}"
    body = (
        f"trial: {TRIAL_ID}\n"
        f"task_id: {task['task_id']}\n"
        f"selected_agent: {selected_agent}\n"
        f"result_status: {result['status']}\n"
        f"failure_category: {result.get('failure_category')}\n"
        f"reason: {result.get('reason')}\n"
        f"artifacts: {', '.join(result.get('artifact_paths', [])) or 'none'}\n"
    )
    path = out_root / "evidence" / "run" / f"{event_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# phases
def run_phase_a(tasks: list, orchestrator: OrchestratorAgent, workers: dict,
                out_root: Path) -> list:
    records = []
    decisions_dir = out_root / "decisions" / "no-ahrp"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    forbidden = ForbiddenHistoryStore()
    for index, task in enumerate(tasks, start=1):
        # baseline: the orchestrator must not read any AHRP record.
        # Any accidental query attempt raises AhrpAccessForbidden.
        decision = orchestrator.decide(task, forbidden)
        selected = decision["selected_agent"]
        worker = _worker_for(task, selected, workers)
        result = worker.execute(task, out_root / "evidence" / "artifacts" / task["task_id"])
        record = {
            "task_id": task["task_id"],
            "mode": "NO_AHRP_MODE",
            "orchestrator_agent_id": orchestrator.agent_id,
            "orchestrator_agent_version": orchestrator.agent_version,
            "candidate_agents": CANDIDATES_BY_TYPE[task["task_type"]],
            "selected_agent": selected,
            "selection_reason": decision["selection_reason"],
            "result": result,
            "occurred_at": occurred_at("NO_AHRP_MODE", index),
        }
        (decisions_dir / f"{task['task_id']}.json").write_text(
            json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8")
        records.append(record)
    return records


def _worker_for(task: dict, selected: str, workers: dict):
    if task["task_type"] == "data_processing":
        # generic data-processing execution profile of the selected worker
        return DataProcessingWorker({"agent_id": selected, "agent_version": "1.0.0",
                                     "role": "DATA_PROCESSING",
                                     "capabilities": ["data_transformation"],
                                     "boundary": "transformations only, no network"})
    return workers[selected]


def run_phase_b(tasks: list, orchestrator: OrchestratorAgent, workers: dict,
                store: HistoryStore, versions: dict, out_root: Path) -> list:
    records = []
    decisions_dir = out_root / "decisions" / "ahrp-assisted"
    events_dir = out_root / "events"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    events_dir.mkdir(parents=True, exist_ok=True)
    for index, task in enumerate(tasks, start=1):
        decision = orchestrator.decide(task, store)
        timestamp = occurred_at("AHRP_ASSISTED_MODE", index)
        after = decision["after_query_decision"]
        if after["decision"] == "DELEGATE":
            selected = after["selected_agent"]
            worker = _worker_for(task, selected, workers)
            result = worker.execute(
                task, out_root / "evidence" / "artifacts" / task["task_id"])
            evidence_hash = write_evidence_body(out_root, task, selected, result)
            event = make_run_event(task, selected, versions, result,
                                   timestamp, evidence_hash)
            verification = make_run_verification(task, selected, versions,
                                                 timestamp)
            if not validate_experience_event(event).valid:
                raise SystemExit(f"TRIAL_ABORTED: invalid run event {event['event_id']}")
            if not validate_verification_record(verification).valid:
                raise SystemExit(f"TRIAL_ABORTED: invalid run verification "
                                 f"{verification['verification_id']}")
            store.ingest_event(event)
            store.ingest_verification(verification)
            (events_dir / f"{event['event_id']}.json").write_text(
                json.dumps(event, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8")
            (events_dir / f"{verification['verification_id']}.json").write_text(
                json.dumps(verification, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8")
        else:
            result = {
                "status": "NOT_EXECUTED",
                "failure_category": None,
                "reason": "routed to human manual review by orchestrator policy",
                "artifact_paths": [],
            }
        decision["result"] = result
        decision["occurred_at"] = timestamp
        (decisions_dir / f"{task['task_id']}.json").write_text(
            json.dumps(decision, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8")
        records.append(decision)
    return records


# --------------------------------------------------------------------------
# analysis
REASON_PRIORITY = ["QUERY_ERROR", "CAPABILITY_LIMIT_HISTORY",
                   "POLICY_RESTRICTION_HISTORY", "POSITIVE_HISTORY", "NO_RECORD"]


def dominant_reason(history_used: list) -> str:
    present = {entry["reason"] for entry in history_used}
    for reason in REASON_PRIORITY:
        if reason in present:
            return reason
    return "NONE"


def analyze(phase_a: list, phase_b: list, ahrp_tree_hash: str) -> dict:
    query_count = sum(r["query_count"] for r in phase_b)
    changed = [r for r in phase_b if r["decision_changed"]]
    history_refs = [
        entry for r in phase_b for entry in r["history_used"]
        if entry["event_id"] is not None
    ]
    a_results = [r["result"]["status"] for r in phase_a]
    b_results = [r["result"]["status"] for r in phase_b]
    summary = {
        "trial_id": TRIAL_ID,
        "objectives": {
            "question": "Can a programmatic orchestrator integrate the frozen "
                        "AHRP v0.1 query interface and bind returned history "
                        "to auditable delegation decisions?",
        },
        "counts": {
            "TASK_COUNT": len(phase_a) + len(phase_b),
            "tasks_no_ahrp": len(phase_a),
            "tasks_ahrp_assisted": len(phase_b),
            "AHRP_QUERY_COUNT": query_count,
            "AHRP_QUERY_COUNT_NOTE": (
                "AHRP_QUERY_COUNT is produced by the configured AHRP-assisted "
                "execution path. It is not evidence that an autonomous agent "
                "voluntarily chose to query AHRP."
            ),
            "PROGRAMMATIC_DECISION_CHANGED_COUNT": len(changed),
            "PROGRAMMATIC_DECISION_CHANGED_NOTE": (
                "PROGRAMMATIC_ROUTING_CHANGE_OBSERVATION only; not an "
                "adoption signal, not an agent demand signal."
            ),
            "DECISION_CHANGED_TASKS": [r["task_id"] for r in changed],
            "RESOLVABLE_HISTORY_REFERENCE_COUNT": len(history_refs),
            "HISTORY_USED_REASONS": {
                r["task_id"]: dominant_reason(r["history_used"]) for r in phase_b
            },
        },
        "execution_outcomes_observational_only": {
            "note": "Recorded for transparency. This trial does NOT claim any "
                    "performance improvement; task mix is designed to trigger "
                    "history consumption, not to measure success rates.",
            "no_ahrp": {s: a_results.count(s) for s in sorted(set(a_results))},
            "ahrp_assisted": {s: b_results.count(s) for s in sorted(set(b_results))},
        },
        "query_cost": {
            "latency_ms_per_query": [
                q["latency_ms"] for r in phase_b for q in r["ahrp_query"]
            ],
            "tokens_estimated_per_query": [
                q["tokens_estimated"] for r in phase_b for q in r["ahrp_query"]
            ],
            "calls_total": query_count,
        },
        "supported_findings": {
            "AHRP_QUERY_INTERFACE_INTEGRATED": True,
            "HISTORY_BOUND_TO_DECISION_RECORD": True,
            "PROGRAMMATIC_DECISION_CHANGED_BY_HISTORY": len(changed) > 0,
            "QUERY_FAILURE_FAIL_CLOSED": any(
                "fail_closed" in r for r in phase_b),
        },
        "unsupported_claims": {
            "note": "These claims cannot be made by this trial.",
            "AGENT_VOLUNTARILY_ADOPTED_AHRP": False,
            "REAL_AGENT_DEMAND_VALIDATED": False,
            "REAL_WORLD_ADOPTION_VALIDATED": False,
        },
        "truth_boundaries": {
            "INTERNAL_EXECUTABLE_INTEGRATION_TRIAL": True,
            "PROGRAMMATIC_ORCHESTRATOR_USED_AHRP": query_count > 0,
            "MODEL_BASED_ORCHESTRATOR": False,
            "AUTONOMOUS_TOOL_SELECTION": False,
            "VOLUNTARY_AHRP_QUERY_VALIDATED": False,
            "REAL_AGENT_ADOPTION_VALIDATED": False,
            "REAL_EXTERNAL_AGENT": False,
            "REAL_HUMAN_ORCHESTRATOR": False,
            "AHRP_PRODUCTION_READY": False,
            "AHRP_STANDARD_PUBLISHED": False,
            "SUCCESS_RATE_IMPROVEMENT_PROVEN": False,
            "REAL_INDEPENDENT_VERIFICATION": False,
            "AHRP_V0_1_MODIFIED": False,
            "INTEGRATION_MECHANISM_DEMONSTRATED": (query_count > 0
                                                   and len(changed) > 0),
            "TRIAL_RESULT": "INCONCLUSIVE",
        },
        "ahrp_tree_hash": ahrp_tree_hash,
    }
    return summary


def ahrp_tree_hash() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "origin/main:AHRP"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "UNKNOWN"


# --------------------------------------------------------------------------
# entry point
def run_all(out_root: Path = None) -> dict:
    out_root = Path(out_root) if out_root else EXP_ROOT
    config = load_config()
    roster = config["roster"]
    versions = agent_versions(roster)
    workers = build_workers(roster)
    orchestrator_reg = next(
        a for a in roster["agents"] if a["role"] == "ORCHESTRATOR")
    orchestrator = OrchestratorAgent(orchestrator_reg, versions)

    store = build_store()
    tasks_a = [t for t in config["tasks"] if t["phase"] == "NO_AHRP_MODE"]
    tasks_b = [t for t in config["tasks"] if t["phase"] == "AHRP_ASSISTED_MODE"]

    phase_a = run_phase_a(tasks_a, orchestrator, workers, out_root)
    phase_b = run_phase_b(tasks_b, orchestrator, workers, store, versions, out_root)

    summary = analyze(phase_a, phase_b, ahrp_tree_hash())
    analysis_dir = out_root / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    (analysis_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")

    counts = summary["counts"]
    print(f"tasks: {counts['TASK_COUNT']} "
          f"(no-ahrp={counts['tasks_no_ahrp']}, ahrp={counts['tasks_ahrp_assisted']})")
    print(f"AHRP_QUERY_COUNT: {counts['AHRP_QUERY_COUNT']}")
    print(f"PROGRAMMATIC_DECISION_CHANGED_COUNT: "
          f"{counts['PROGRAMMATIC_DECISION_CHANGED_COUNT']} "
          f"{counts['DECISION_CHANGED_TASKS']}")
    print(f"RESOLVABLE_HISTORY_REFERENCE_COUNT: "
          f"{counts['RESOLVABLE_HISTORY_REFERENCE_COUNT']}")
    print(f"TRIAL_RESULT: {summary['truth_boundaries']['TRIAL_RESULT']}")
    return summary


if __name__ == "__main__":
    run_all()
