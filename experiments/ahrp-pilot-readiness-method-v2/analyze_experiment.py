"""Metric analysis for the method-v2 experiment.

Reads ONLY raw JSONL (config inputs + recorded data). Never reads a prior
summary as input; every number below is recomputed from raw records.

Allowed claims:      AHRP_HISTORY_WAS_USED,
                     AHRP_ASSOCIATED_WITH_DIFFERENT_DECISION
Forbidden claims:    AHRP_PROVED_TO_IMPROVE_SUCCESS_RATE, FAILURE_PREVENTED

The repeat-selection metric is reported strictly as a
ROUTING_POLICY_CONFORMANCE_OBSERVATION. It is mechanically related to the
configured veto policy. It is not independent evidence of improved
real-world outcomes.
"""

import json
import math
import os
from typing import Any, Dict, List

import history_loader

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config")
DATA = os.path.join(HERE, "data")
ANALYSIS = os.path.join(HERE, "analysis")

ROUTING_METRIC_NOTE = (
    "This metric is mechanically related to the configured veto policy. "
    "It is not independent evidence of improved real-world outcomes.")


def percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    rank = pct / 100.0 * (len(sorted_values) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return sorted_values[lower]
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + \
        sorted_values[upper] * weight


def seed_failure_map() -> Dict[str, set]:
    """Independently verified seed failures per (agent, task_type)."""
    seeds = history_loader.load_jsonl(
        os.path.join(CONFIG, "history-events.jsonl"))
    verification_by_id = {
        v["verification_id"]: v for v in history_loader.load_jsonl(
            os.path.join(CONFIG, "history-verifications.jsonl"))}
    boundary: Dict[str, set] = {}
    for event in seeds:
        if event["result_status"] not in ("FAILURE", "TIMEOUT", "CANCELLED"):
            continue
        independently_verified = False
        for ref in event.get("verification_references", []):
            record = verification_by_id.get(ref.get("verification_id"))
            if record is None:
                continue
            if record["verifier"]["verifier_class"] == "SELF" or \
                    record.get("self_verification"):
                continue
            if record["verification_status"] == "VERIFIED":
                independently_verified = True
        if independently_verified:
            key = event["agent_reference"]["identity_ref"]
            boundary.setdefault(key, set()).add(event["task_type"])
    return boundary


def arm_status_counts(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {"tasks": 0, "SUCCESS": 0, "FAILURE": 0, "TIMEOUT": 0,
              "CANCELLED": 0}
    for record in records:
        counts["tasks"] += 1
        counts[record["result_status"]] += 1
    return counts


def load_optional(name: str) -> List[Dict[str, Any]]:
    path = os.path.join(DATA, name)
    return history_loader.load_jsonl(path) if os.path.isfile(path) else []


def main() -> None:
    tasks = {t["task_id"]: t for t in history_loader.load_jsonl(
        os.path.join(CONFIG, "tasks.jsonl"))}
    allocations = history_loader.load_jsonl(
        os.path.join(DATA, "allocations.jsonl"))
    executions = history_loader.load_jsonl(
        os.path.join(DATA, "controlled-executions.jsonl"))
    queries = history_loader.load_jsonl(os.path.join(DATA, "queries.jsonl"))
    post_records = history_loader.load_jsonl(
        os.path.join(DATA, "post-query-decisions.jsonl"))
    nondispatched = load_optional("non-dispatched-tasks.jsonl")
    final_events = load_optional("experience-events.jsonl")
    verifications = load_optional("verification-records.jsonl")

    boundary = seed_failure_map()
    exec_by_task = {e["task_id"]: e for e in executions}

    def routing_conformance(arm_allocations: List[Dict[str, Any]]
                           ) -> Dict[str, Any]:
        repeats = 0
        for allocation in arm_allocations:
            if allocation["final_agent"] is None:
                continue  # blocked / manual review: nothing was selected
            task = tasks[allocation["task_id"]]
            known = boundary.get(allocation["final_agent"], set())
            if task["task_type"] in known:
                repeats += 1
        return {
            "repeat_selection_of_known_failure_boundary_agent": repeats,
            "interpretation": "ROUTING_POLICY_CONFORMANCE_OBSERVATION",
            "note": ROUTING_METRIC_NOTE,
        }

    def decision_time_stats(arm_allocations: List[Dict[str, Any]]
                            ) -> Dict[str, float]:
        times = sorted(a["decision_time_ms"] for a in arm_allocations)
        return {
            "avg_ms": round(sum(times) / len(times), 6) if times else 0.0,
            "p50_ms": round(percentile(times, 50), 6),
            "p95_ms": round(percentile(times, 95), 6),
        }

    no_ahrp_alloc = [a for a in allocations if a["arm"] == "No-AHRP"]
    ahrp_alloc = [a for a in allocations if a["arm"] == "AHRP-assisted"]
    no_ahrp_exec = [exec_by_task[a["task_id"]] for a in no_ahrp_alloc
                    if a["task_id"] in exec_by_task]
    ahrp_exec = [exec_by_task[a["task_id"]] for a in ahrp_alloc
                 if a["task_id"] in exec_by_task]

    def disposition_counts(arm_allocations: List[Dict[str, Any]]
                           ) -> Dict[str, int]:
        counts = {"DISPATCH": 0, "LOW_RISK_EXPLORATION": 0, "BLOCK": 0,
                  "MANUAL_REVIEW": 0}
        for allocation in arm_allocations:
            counts[allocation["disposition"]] += 1
        return counts

    no_ahrp_dispositions = disposition_counts(no_ahrp_alloc)
    ahrp_dispositions = disposition_counts(ahrp_alloc)

    no_ahrp_arm = {
        "arm": "No-AHRP",
        **arm_status_counts(no_ahrp_exec),
        "dispositions": no_ahrp_dispositions,
        "avg_decision_time": decision_time_stats(no_ahrp_alloc),
        "human_overrides": 0,
        "human_overrides_note": "controlled run: no human intervention "
                                "occurred; counted honestly as zero",
        "routing_policy_conformance": routing_conformance(no_ahrp_alloc),
    }

    ahrp_statuses = arm_status_counts(ahrp_exec)
    decision_changes = [p for p in post_records if p["decision_changed"]]
    latencies = sorted(q["latency_ms"] for q in queries)
    total_chars = sum(q["query_chars"] for q in queries)
    total_tokens = sum(q["token_estimate"] for q in queries)
    ahrp_arm = {
        "arm": "AHRP-assisted",
        **ahrp_statuses,
        "dispositions": ahrp_dispositions,
        "avg_decision_time": decision_time_stats(ahrp_alloc),
        "human_overrides": 0,
        "human_overrides_note": "controlled run: no human intervention "
                                "occurred; counted honestly as zero",
        "routing_policy_conformance": routing_conformance(ahrp_alloc),
        "query_count": len(queries),
        "summary_query_count":
            sum(1 for q in queries if q["query_mode"] == "Summary"),
        "summary_list_query_count":
            sum(1 for q in queries if q["query_mode"] == "SummaryList"),
        "detail_query_count":
            sum(1 for q in queries if q["query_mode"] == "Detail"),
        "no_record_count":
            sum(1 for q in queries if q["null_semantics"] == "NO_RECORD"),
        "withheld_count":
            sum(1 for q in queries if q["null_semantics"] == "WITHHELD"),
        "disclosure_denial_count":
            sum(1 for q in queries
                if q["null_semantics"] == "WITHHELD" or
                (q.get("error_code") or "").startswith("Q_DISCLOSURE")),
        "query_error_count":
            sum(1 for q in queries if not q["ok"]),
        "decision_change_count": len(decision_changes),
        "supporting_event_reference_count":
            sum(len(p["supporting_event_references"])
                for p in post_records),
        "query_char_count": total_chars,
        "token_estimate": total_tokens,
        "token_estimation_method": "ceil(chars/4) heuristic, documented",
        "latency_p50_ms": round(percentile(latencies, 50), 6),
        "latency_p95_ms": round(percentile(latencies, 95), 6),
    }

    # Task flow accounting: submitted vs dispatched vs non-dispatched.
    # Blocked / manual-review tasks are NOT disguised as FAILURE/CANCELLED.
    task_flow = {
        "submitted_tasks": len(allocations),
        "dispatched_tasks":
            sum(1 for a in allocations
                if a["disposition"] == "DISPATCH"),
        "low_risk_exploration_tasks":
            sum(1 for a in allocations
                if a["disposition"] == "LOW_RISK_EXPLORATION"),
        "blocked_tasks":
            sum(1 for a in allocations if a["disposition"] == "BLOCK"),
        "manual_review_tasks":
            sum(1 for a in allocations
                if a["disposition"] == "MANUAL_REVIEW"),
        "executed_tasks": len(executions),
        "experience_event_count": len(final_events),
        "verification_record_count": len(verifications),
        "non_dispatched_record_count": len(nondispatched),
        "note": "dispatched + low_risk_exploration == executed; blocked "
                "and manual-review tasks were never executed and have no "
                "execution evidence, experience event, or verification "
                "record",
    }

    comparison = {
        "task_flow": task_flow,
        "no_ahrp": no_ahrp_arm,
        "ahrp_assisted": ahrp_arm,
        "design_note": "Both arms use the SAME deterministic worker for any "
                       "task they execute; only the decision procedure "
                       "differs. The AHRP arm additionally applies "
                       "fail-closed dispatch semantics (BLOCK / "
                       "MANUAL_REVIEW / LOW_RISK_EXPLORATION), so the two "
                       "arms intentionally execute different task subsets.",
        "allowed_claims": [],
        "forbidden_claims_blocked": [
            "AHRP_PROVED_TO_IMPROVE_SUCCESS_RATE", "FAILURE_PREVENTED"],
    }
    if ahrp_arm["query_count"] > 0:
        comparison["allowed_claims"].append("AHRP_HISTORY_WAS_USED")
    if decision_changes:
        comparison["allowed_claims"].append(
            "AHRP_ASSOCIATED_WITH_DIFFERENT_DECISION")

    changed_tasks = []
    for post in decision_changes:
        execution = exec_by_task.get(post["task_id"])
        changed_tasks.append({
            "task_id": post["task_id"],
            "disposition": post.get("disposition"),
            "reason": post["selection_reason_after_query"],
            "supporting_event_references":
                post["supporting_event_references"],
            "execution_result": execution["result_status"]
            if execution else "NOT_EXECUTED",
        })
    comparison["decision_change_detail"] = changed_tasks

    # EXPERIMENT_RESULT gate: synthetic controlled sample, no external
    # validation. The verdict stays INCONCLUSIVE regardless of arm deltas.
    experiment_result = "INCONCLUSIVE"
    comparison["experiment_result"] = experiment_result
    comparison["truth_boundary"] = {
        "CONTROLLED_INTERNAL_EXPERIMENT": True,
        "SYNTHETIC_AGENT_ROSTER": True,
        "REAL_EXTERNAL_AGENT": False,
        "REAL_WORLD_ADOPTION_VALIDATED": False,
        "AHRP_PRODUCTION_READY": False,
        "AHRP_STANDARD_PUBLISHED": False,
        "NETWORK_SERVICE_RECOMMENDATION": "DEFER",
        "REAL_INDEPENDENT_VERIFICATION": False,
        "SYNTHETIC_SYSTEM_VERIFICATION": True,
        "POST_RUN_RECOMPUTATION_VERIFIED": True,
    }

    shadow_integrity_note = (
        "Shadow protocol integrity is validated by validate_shadow_protocol.py"
        " against the raw JSONL; this analysis does not re-assert it.")
    operational_overhead = {
        "source": "recomputed from raw data/queries.jsonl",
        "query_count": ahrp_arm["query_count"],
        "latency_p50_ms": ahrp_arm["latency_p50_ms"],
        "latency_p95_ms": ahrp_arm["latency_p95_ms"],
        "query_char_count": total_chars,
        "token_estimate": total_tokens,
        "avg_decision_time_no_ahrp_ms":
            no_ahrp_arm["avg_decision_time"]["avg_ms"],
        "avg_decision_time_ahrp_ms":
            ahrp_arm["avg_decision_time"]["avg_ms"],
    }

    os.makedirs(ANALYSIS, exist_ok=True)
    for name, payload in (
            ("no-ahrp-arm.json", no_ahrp_arm),
            ("ahrp-assisted-arm.json", ahrp_arm),
            ("comparison.json", comparison),
            ("shadow-integrity.json",
             {"note": shadow_integrity_note,
              "validator": "validate_shadow_protocol.py",
              "input": ["data/pre-query-decisions.jsonl",
                        "data/post-query-decisions.jsonl",
                        "data/queries.jsonl"]}),
            ("operational-overhead.json", operational_overhead)):
        with open(os.path.join(ANALYSIS, name), "w",
                  encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    print(json.dumps({"status": "ANALYSIS_COMPLETE",
                      "experiment_result": experiment_result,
                      "task_flow": task_flow,
                      "no_ahrp": no_ahrp_arm,
                      "ahrp_assisted": ahrp_arm}, indent=2))


if __name__ == "__main__":
    main()
