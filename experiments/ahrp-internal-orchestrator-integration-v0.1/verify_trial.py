#!/usr/bin/env python3
"""Post-run verifier for the AHRP internal orchestrator integration trial.

AHRP 内部编排器集成试验 v0.1 后运行验证器。

Independent re-read of the produced decision records, run events, run
verifications and analysis summary. Exits non-zero on any problem.

Checks:
 1. truth boundaries present with the mandated fixed values
 2. no-ahrp baseline records never carry AHRP query fields
 3. every decision change is backed by resolvable history references
 4. all-NO_RECORD queries never produce a decision change
 5. run events and verifications pass the AHRP Validator
 6. verification scope is strongly bound to its event (version binding)
 7. run evidence hashes recompute exactly
 8. no prohibited metric (score / ranking / trust / reliability) anywhere
"""

import hashlib
import json
import sys
from pathlib import Path

EXP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EXP_ROOT.parent.parent
for path in (str(REPO_ROOT), str(REPO_ROOT / "AHRP")):
    if path not in sys.path:
        sys.path.insert(0, path)

from validator.core import (  # noqa: E402
    validate_experience_event,
    validate_verification_record,
)

import run_trial  # noqa: E402

PROHIBITED_SUBSTRINGS = ("score", "ranking", "trust", "reliability")

REQUIRED_TRUTH = {
    "INTERNAL_EXECUTABLE_INTEGRATION_TRIAL": True,
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
    "TRIAL_RESULT": "INCONCLUSIVE",
}


def main() -> int:
    problems = []

    summary_path = EXP_ROOT / "analysis" / "summary.json"
    if not summary_path.is_file():
        print("FAIL: analysis/summary.json missing -- run run_trial.py first")
        return 1
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    # 1. truth boundaries
    truth = summary.get("truth_boundaries", {})
    for key, expected in REQUIRED_TRUTH.items():
        if truth.get(key) != expected:
            problems.append(f"truth boundary {key} != {expected}")

    # 8. prohibited metrics (deep scan of the summary)
    flat = json.dumps(summary, sort_keys=True).lower()
    for token in PROHIBITED_SUBSTRINGS:
        if token in flat:
            problems.append(f"prohibited metric token found: {token!r}")

    # load decision records
    no_ahrp = sorted((EXP_ROOT / "decisions" / "no-ahrp").glob("*.json"))
    assisted = sorted((EXP_ROOT / "decisions" / "ahrp-assisted").glob("*.json"))
    if len(no_ahrp) != 10:
        problems.append(f"expected 10 no-ahrp records, found {len(no_ahrp)}")
    if len(assisted) != 10:
        problems.append(f"expected 10 ahrp-assisted records, found {len(assisted)}")

    store = run_trial.build_store()

    # 2. baseline records must not carry AHRP query fields
    for path in no_ahrp:
        record = json.loads(path.read_text(encoding="utf-8"))
        for field in ("ahrp_query", "history_used", "after_query_decision"):
            if field in record:
                problems.append(f"{path.name}: forbidden field {field!r} in baseline")
        for key in ("task_id", "candidate_agents", "selected_agent",
                    "selection_reason", "result"):
            if key not in record:
                problems.append(f"{path.name}: missing field {key!r}")

    # 3/4. assisted records consistency
    changed_with_history = 0
    for path in assisted:
        record = json.loads(path.read_text(encoding="utf-8"))
        for key in ("task_id", "before_query_decision", "ahrp_query",
                    "history_used", "after_query_decision", "decision_changed"):
            if key not in record:
                problems.append(f"{path.name}: missing field {key!r}")
                continue
        if record.get("decision_changed"):
            refs = [e for e in record.get("history_used", [])
                    if e.get("event_id")]
            if not refs:
                problems.append(
                    f"{path.name}: decision_changed without history reference")
            else:
                changed_with_history += 1
        semantics = [q.get("null_semantics") for q in record.get("ahrp_query", [])
                     if q.get("ok")]
        if semantics and all(s == "NO_RECORD" for s in semantics):
            if record.get("decision_changed"):
                problems.append(
                    f"{path.name}: decision change despite all-NO_RECORD history")

    # 5/6. run events and verifications
    events_dir = EXP_ROOT / "events"
    run_events = sorted(events_dir.glob("evt-trial-run-*.json"))
    run_verifications = sorted(events_dir.glob("ver-trial-run-*.json"))
    if not run_events:
        problems.append("no run events recorded")
    for path in run_events:
        event = json.loads(path.read_text(encoding="utf-8"))
        result = validate_experience_event(event)
        if not result.valid:
            problems.append(f"{path.name}: AHRP Validator errors: {result.errors}")
    for path in run_verifications:
        verification = json.loads(path.read_text(encoding="utf-8"))
        result = validate_verification_record(verification)
        if not result.valid:
            problems.append(f"{path.name}: AHRP Validator errors: {result.errors}")
        scope = verification["scope"]
        event_path = events_dir / f"{scope['subject_event_id']}.json"
        if not event_path.is_file():
            problems.append(f"{path.name}: subject event missing")
            continue
        event = json.loads(event_path.read_text(encoding="utf-8"))
        if scope["agent_ref"] != event["agent_reference"]["identity_ref"]:
            problems.append(f"{path.name}: agent_ref binding mismatch")
        if scope["agent_version"] != event["agent_version"]:
            problems.append(f"{path.name}: agent_version binding mismatch")
        if scope["covered_aspect"] != "FULL_EVENT":
            problems.append(f"{path.name}: covered_aspect != FULL_EVENT")
        if verification["verifier"]["verifier_class"] != "SYSTEM_BENCHMARK":
            problems.append(f"{path.name}: verifier_class != SYSTEM_BENCHMARK")
        # ingest into the store so history references can be resolved
        if event["event_id"] not in getattr(store, "_events", {}):
            store.ingest_event(event)
            store.ingest_verification(verification)

    # 3b. history references resolve in the store
    for path in assisted:
        record = json.loads(path.read_text(encoding="utf-8"))
        for entry in record.get("history_used", []):
            if not entry.get("event_id"):
                continue
            envelope = store.get_event(entry["event_id"], capability="summary")
            if not envelope.get("ok"):
                problems.append(
                    f"{path.name}: history reference {entry['event_id']} "
                    f"does not resolve")

    # 7. run evidence hashes recompute
    for path in run_events:
        event = json.loads(path.read_text(encoding="utf-8"))
        for ref in event.get("evidence_references", []):
            body_path = EXP_ROOT / "evidence" / "run" / f"{event['event_id']}.txt"
            if not body_path.is_file():
                problems.append(f"{path.name}: evidence body missing")
                continue
            digest = hashlib.sha256(body_path.read_bytes()).hexdigest()
            if ref["hash"] != f"sha256:{digest}":
                problems.append(f"{path.name}: evidence hash mismatch")

    # consistency: summary counts match records
    counts = summary.get("counts", {})
    actual_queries = sum(
        len(json.loads(p.read_text(encoding="utf-8")).get("ahrp_query", []))
        for p in assisted)
    if counts.get("AHRP_QUERY_COUNT") != actual_queries:
        problems.append("AHRP_QUERY_COUNT inconsistent with decision records")
    actual_changed = sum(
        1 for p in assisted
        if json.loads(p.read_text(encoding="utf-8")).get("decision_changed"))
    if counts.get("PROGRAMMATIC_DECISION_CHANGED_COUNT") != actual_changed:
        problems.append("PROGRAMMATIC_DECISION_CHANGED_COUNT inconsistent "
                        "with decision records")
    # the query-count disclaimer must travel with the metric
    if "configured AHRP-assisted execution path" not in counts.get(
            "AHRP_QUERY_COUNT_NOTE", ""):
        problems.append("AHRP_QUERY_COUNT_NOTE disclaimer missing")

    if problems:
        print("FAIL:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("trial records: 10 no-ahrp + 10 ahrp-assisted")
    print(f"run events: {len(run_events)}, run verifications: {len(run_verifications)}")
    print(f"decision changes backed by history references: {changed_with_history}")
    print("verify_trial: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
