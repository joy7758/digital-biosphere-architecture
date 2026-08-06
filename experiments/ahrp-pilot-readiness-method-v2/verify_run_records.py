"""Post-run system verifier for the method-v2 experiment (SEPARATE process).

Verification independence fix: the runner only executes and writes
UNVERIFIED experience events (``verification_references=[]``). This program
runs AFTER the runner, as an independent post-processing step, and:

 1. reads the frozen tasks and the frozen capability matrix (commitment
    hash re-checked);
 2. reads the controlled execution evidence files;
 3. RECOMPUTES the expected result through the same deterministic worker;
 4. compares selected_agent / result_status / failure_category /
    capability-matrix hash / evidence SHA-256;
 5. validates every generated Experience Event and Verification Record with
    the real AHRP v0.1 Validator;
 6. verifies the event <-> verification binding (subject_event_id,
    agent_ref, agent_version, covered_aspect);
 7. only then writes ``data/experience-events.jsonl`` and
    ``data/verification-records.jsonl``.

Truth boundary:

    REAL_INDEPENDENT_VERIFICATION=false
    SYNTHETIC_SYSTEM_VERIFICATION=true
    POST_RUN_RECOMPUTATION_VERIFIED=true

The verifier class is SYSTEM_BENCHMARK (verifier name
``method-v2-post-run-verifier``). This is a deterministic recomputation by
the experiment harness itself, NOT an independent agent. INDEPENDENT_AGENT
is never claimed for generated records.

Any failure exits non-zero and refuses to publish the final files.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import history_loader
import worker

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config")
DATA = os.path.join(HERE, "data")
EVIDENCE = os.path.join(HERE, "evidence")
ANALYSIS = os.path.join(HERE, "analysis")

AGENT_VERSION = "1.0.0"
VERIFIER_NAME = "method-v2-post-run-verifier"
VERIFIER_CLASS = "SYSTEM_BENCHMARK"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_validator():
    from validator.core import (validate_experience_event,
                                validate_verification_record)
    return validate_experience_event, validate_verification_record


def recompute_and_compare(tasks_by_id: Dict[str, Dict[str, Any]],
                          matrix: Dict[str, Any], matrix_hash: str,
                          committed_hash: str,
                          executions: List[Dict[str, Any]],
                          events: List[Dict[str, Any]]
                          ) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    """Deterministic recomputation of every execution through the worker."""
    problems: List[str] = []
    if matrix_hash != committed_hash:
        problems.append(
            f"capability matrix hash {matrix_hash} does not match the "
            f"pre-run commitment {committed_hash}")
    events_by_task = {e["event_id"]: e for e in events}
    recomputed: Dict[str, Dict[str, Any]] = {}
    for execution in executions:
        task_id = execution["task_id"]
        task = tasks_by_id.get(task_id)
        event_id = f"evt-run-{task_id}"
        event = events_by_task.get(event_id)
        if task is None:
            problems.append(f"{task_id}: execution without frozen task")
            continue
        if event is None:
            problems.append(f"{task_id}: execution without unverified event")
            continue
        status, category, rule = worker.execute_task(
            task, execution["selected_agent"], matrix)
        record = {"task_id": task_id, "expected_status": status,
                  "expected_category": category, "expected_rule": rule}
        recomputed[task_id] = record
        if event["agent_reference"]["identity_ref"] != \
                execution["selected_agent"]:
            problems.append(f"{task_id}: event agent does not match "
                            "execution selected_agent")
        if execution["result_status"] != status:
            problems.append(
                f"{task_id}: recorded result {execution['result_status']} "
                f"!= recomputed {status}")
        if execution["failure_category"] != category:
            problems.append(
                f"{task_id}: recorded failure_category "
                f"{execution['failure_category']} != recomputed {category}")
        if event["result_status"] != status:
            problems.append(f"{task_id}: event result != recomputed result")
        # Evidence file hash recomputation.
        evidence_path = os.path.join(HERE, execution["evidence_path"])
        if not os.path.isfile(evidence_path):
            problems.append(f"{task_id}: evidence file missing")
            continue
        actual_hash = file_sha256(evidence_path)
        references = event.get("evidence_references", [])
        if len(references) != 1:
            problems.append(f"{task_id}: expected exactly one evidence "
                            "reference")
            continue
        declared = references[0].get("hash", "")
        if declared != f"sha256:{actual_hash}":
            problems.append(
                f"{task_id}: evidence hash mismatch declared={declared} "
                f"actual=sha256:{actual_hash}")
        evidence_doc = json.load(open(evidence_path, encoding="utf-8"))
        if evidence_doc.get("selected_agent") != execution["selected_agent"]:
            problems.append(f"{task_id}: evidence selected_agent mismatch")
        if evidence_doc.get("result") != status:
            problems.append(f"{task_id}: evidence result mismatch")
    return problems, recomputed


def build_final_records(executions: List[Dict[str, Any]],
                        events: List[Dict[str, Any]]
                        ) -> Tuple[List[Dict[str, Any]],
                                   List[Dict[str, Any]]]:
    """Attach SYSTEM_BENCHMARK verification references to each event and
    build the matching verification records."""
    events_by_task = {e["event_id"]: e for e in events}
    final_events: List[Dict[str, Any]] = []
    verifications: List[Dict[str, Any]] = []
    for execution in executions:
        event_id = f"evt-run-{execution['task_id']}"
        verification_id = f"ver-run-{execution['task_id']}"
        event = json.loads(json.dumps(events_by_task[event_id]))
        event["verification_references"] = [{
            "verification_id": verification_id,
            "verifier_name": VERIFIER_NAME,
        }]
        final_events.append(event)
        verifications.append({
            "schema_version": "0.1.0",
            "verification_id": verification_id,
            "verifier": {"verifier_name": VERIFIER_NAME,
                         "verifier_class": VERIFIER_CLASS},
            "verification_type": "EVENT_CONFIRMATION",
            "verification_status": "VERIFIED",
            "verified_at": utc_now_iso(),
            "scope": {"subject_event_id": event_id,
                      "subject_type": "EXPERIENCE_EVENT",
                      "agent_ref": event["agent_reference"]["identity_ref"],
                      "agent_version": event["agent_version"],
                      "covered_aspect": "FULL_EVENT"},
            "self_verification": False,
            "authorization_effect": "NONE",
            "notes": "Deterministic post-run recomputation by the "
                     "method-v2 harness (SYSTEM_BENCHMARK). NOT an "
                     "independent agent verification: "
                     "REAL_INDEPENDENT_VERIFICATION=false.",
        })
    return final_events, verifications


def check_binding(final_events: List[Dict[str, Any]],
                  verifications: List[Dict[str, Any]]) -> List[str]:
    problems: List[str] = []
    verification_by_id = {v["verification_id"]: v for v in verifications}
    for event in final_events:
        refs = event.get("verification_references", [])
        if len(refs) != 1:
            problems.append(
                f"{event['event_id']}: final event must reference exactly "
                "one verification record")
            continue
        record = verification_by_id.get(refs[0]["verification_id"])
        if record is None:
            problems.append(f"{event['event_id']}: verification reference "
                            "does not resolve")
            continue
        scope = record["scope"]
        if scope["subject_event_id"] != event["event_id"]:
            problems.append(f"{event['event_id']}: subject_event_id "
                            "binding mismatch")
        if scope["agent_ref"] != event["agent_reference"]["identity_ref"]:
            problems.append(f"{event['event_id']}: agent_ref binding "
                            "mismatch")
        if scope["agent_version"] != event["agent_version"]:
            problems.append(f"{event['event_id']}: agent_version binding "
                            "mismatch")
        if scope["covered_aspect"] != "FULL_EVENT":
            problems.append(f"{event['event_id']}: covered_aspect must be "
                            "FULL_EVENT")
        if refs[0]["verifier_name"] != VERIFIER_NAME:
            problems.append(f"{event['event_id']}: verifier_name mismatch "
                            "in event reference")
    return problems


def main() -> int:
    validate_event, validate_verification = load_validator()

    tasks = history_loader.load_jsonl(os.path.join(CONFIG, "tasks.jsonl"))
    tasks_by_id = {t["task_id"]: t for t in tasks}
    with open(os.path.join(CONFIG, "capability-matrix.commitment"),
              encoding="utf-8") as handle:
        committed_hash = handle.read().strip().split()[0]
    matrix_hash = file_sha256(
        os.path.join(CONFIG, "capability-matrix.json"))
    matrix = json.load(open(os.path.join(CONFIG, "capability-matrix.json"),
                            encoding="utf-8"))

    unverified_path = os.path.join(DATA,
                                   "experience-events-unverified.jsonl")
    if not os.path.isfile(unverified_path):
        print("MISSING data/experience-events-unverified.jsonl -- run "
              "run_experiment.py first", file=sys.stderr)
        return 2
    unverified_events = history_loader.load_jsonl(unverified_path)
    executions = history_loader.load_jsonl(
        os.path.join(DATA, "controlled-executions.jsonl"))

    problems: List[str] = []
    schema_failures: List[Dict[str, Any]] = []

    # Runner output must be unverified by construction.
    for event in unverified_events:
        if event.get("verification_references"):
            problems.append(
                f"{event['event_id']}: runner emitted verification "
                "references; runner must stay unverified")

    recompute_problems, recomputed = recompute_and_compare(
        tasks_by_id, matrix, matrix_hash, committed_hash, executions,
        unverified_events)
    problems.extend(recompute_problems)

    final_events, verifications = build_final_records(executions,
                                                      unverified_events)
    for event in final_events:
        result = validate_event(event)
        if not result.valid:
            schema_failures.append({"object": event["event_id"],
                                    "kind": "experience_event",
                                    "errors": result.errors})
    for record in verifications:
        result = validate_verification(record)
        if not result.valid:
            schema_failures.append({"object": record["verification_id"],
                                    "kind": "verification_record",
                                    "errors": result.errors})
    binding_failures = check_binding(final_events, verifications)
    problems.extend(
        f"schema: {item['object']}" for item in schema_failures)
    problems.extend(binding_failures)

    status = "PASS" if not problems else "FAIL"
    report = {
        "events_checked": len(final_events),
        "verifications_checked": len(verifications),
        "schema_failures": schema_failures,
        "binding_failures": binding_failures,
        "recomputation_problems": recompute_problems,
        "capability_matrix_sha256": matrix_hash,
        "capability_matrix_commitment": committed_hash,
        "verifier_name": VERIFIER_NAME,
        "verifier_class": VERIFIER_CLASS,
        "truth_boundary": {
            "REAL_INDEPENDENT_VERIFICATION": False,
            "SYNTHETIC_SYSTEM_VERIFICATION": True,
            "POST_RUN_RECOMPUTATION_VERIFIED": status == "PASS",
        },
        "status": status,
    }
    os.makedirs(ANALYSIS, exist_ok=True)
    with open(os.path.join(ANALYSIS, "generated-object-validation.json"),
              "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    if status != "PASS":
        print(json.dumps(report, indent=2))
        print("POST_RUN_VERIFICATION_FAILED: final records NOT published",
              file=sys.stderr)
        return 1

    with open(os.path.join(DATA, "experience-events.jsonl"), "w",
              encoding="utf-8") as handle:
        for event in final_events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    with open(os.path.join(DATA, "verification-records.jsonl"), "w",
              encoding="utf-8") as handle:
        for record in verifications:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
