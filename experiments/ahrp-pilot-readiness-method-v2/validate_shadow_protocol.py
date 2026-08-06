"""Two-phase shadow protocol validator for the method-v2 experiment.

Checks (all must pass; any failure exits non-zero):

 1. every AHRP-assisted task has exactly one pre-query record;
 2. every pre-query record hash recomputes from its own fields;
 3. every post-query record binds the matching pre-query hash, and the
    post-query hash recomputes;
 4. pre-query was recorded before the query window, and the query window
    closed before the post-query record;
 5. the monotonic sequence is strictly increasing across both files;
 6. every supporting event reference resolves to an actually-held event;
 7. tamper self-test: mutating or deleting any single record in an in-memory
    copy is detected by this same validation logic.
"""

import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import history_loader

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def canonical_hash(record: Dict[str, Any]) -> str:
    payload = {k: v for k, v in record.items() if k != "record_hash"}
    blob = json.dumps(payload, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def parse_instant(value: str) -> float:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(candidate).timestamp()


def validate(pre_records: List[Dict[str, Any]],
             post_records: List[Dict[str, Any]],
             queries: List[Dict[str, Any]],
             tasks: List[Dict[str, Any]],
             known_event_ids: set) -> List[str]:
    problems: List[str] = []
    ahrp_tasks = [t for t in tasks if t["sequence"] % 2 == 0]

    pre_by_task = {}
    for record in pre_records:
        if record["task_id"] in pre_by_task:
            problems.append(f"duplicate pre-query record {record['task_id']}")
        pre_by_task[record["task_id"]] = record

    post_by_task = {}
    for record in post_records:
        if record["task_id"] in post_by_task:
            problems.append(f"duplicate post-query record {record['task_id']}")
        post_by_task[record["task_id"]] = record

    # 1. coverage
    for task in ahrp_tasks:
        task_id = task["task_id"]
        if task_id not in pre_by_task:
            problems.append(f"missing pre-query record for {task_id}")
        if task_id not in post_by_task:
            problems.append(f"missing post-query record for {task_id}")

    # 2/3. hash integrity + binding
    for task_id, record in pre_by_task.items():
        if canonical_hash(record) != record.get("record_hash"):
            problems.append(f"pre-query hash mismatch for {task_id}")
    for task_id, record in post_by_task.items():
        if canonical_hash(record) != record.get("record_hash"):
            problems.append(f"post-query hash mismatch for {task_id}")
        pre = pre_by_task.get(task_id)
        if pre is not None and \
                record.get("pre_query_record_hash") != pre.get("record_hash"):
            problems.append(f"post-query not bound to pre-query {task_id}")

    # 4. temporal order: pre < query window < post
    queries_by_task: Dict[str, List[Dict[str, Any]]] = {}
    for record in queries:
        queries_by_task.setdefault(record["task_id"], []).append(record)
    for task_id, post in post_by_task.items():
        pre = pre_by_task.get(task_id)
        if pre is None:
            continue
        pre_t = parse_instant(pre["recorded_at"])
        post_t = parse_instant(post["recorded_at"])
        window = post.get("query_window") or {}
        if window:
            if not (pre_t <= parse_instant(window["started_at"])
                    <= parse_instant(window["ended_at"]) <= post_t):
                problems.append(f"temporal order violation for {task_id}")
        for query in queries_by_task.get(task_id, []):
            if query.get("pre_query_record_hash") != pre.get("record_hash"):
                problems.append(f"query not bound to pre-query {task_id}")
            if parse_instant(query["recorded_at"]) < pre_t:
                problems.append(f"query before pre-query for {task_id}")

    # 5. monotonic sequence across the combined protocol stream
    stream = sorted(pre_records + post_records,
                    key=lambda r: r["monotonic_sequence"])
    seen = 0
    for record in stream:
        if record["monotonic_sequence"] != seen + 1:
            problems.append(
                f"monotonic sequence broken at {record['monotonic_sequence']}")
            break
        seen = record["monotonic_sequence"]

    # 6. supporting references and disposition consistency
    valid_dispositions = {"DISPATCH", "LOW_RISK_EXPLORATION", "BLOCK",
                          "MANUAL_REVIEW"}
    for task_id, post in post_by_task.items():
        pre = pre_by_task.get(task_id)
        disposition = post.get("disposition")
        if disposition not in valid_dispositions:
            problems.append(f"unknown disposition {disposition!r} "
                            f"({task_id})")
        after_agent = post.get("selected_agent_after_query")
        if disposition in ("BLOCK", "MANUAL_REVIEW") and \
                after_agent is not None:
            problems.append(
                f"{disposition} record must not name an agent ({task_id})")
        if pre is not None:
            # decision_changed must be recomputable from the two selections;
            # tampering with the flag alone is therefore detected.
            expected_changed = after_agent != \
                pre.get("selected_agent_before_query")
            if post.get("decision_changed") != expected_changed:
                problems.append(
                    f"decision_changed inconsistent with selections "
                    f"({task_id})")
        for event_id in post.get("supporting_event_references", []):
            if event_id not in known_event_ids:
                problems.append(
                    f"supporting event {event_id} not held ({task_id})")
        # Switching to another AGENT requires evidence; a fail-closed BLOCK
        # or MANUAL_REVIEW is supported by the query statuses themselves and
        # legitimately carries no event references.
        if post.get("decision_changed") and after_agent is not None and \
                not post.get("supporting_event_references"):
            problems.append(
                f"decision changed to another agent without supporting "
                f"evidence {task_id}")

    return problems


def load(name: str) -> List[Dict[str, Any]]:
    return history_loader.load_jsonl(os.path.join(DATA, name))


def main() -> int:
    pre_records = load("pre-query-decisions.jsonl")
    post_records = load("post-query-decisions.jsonl")
    queries = load("queries.jsonl")
    tasks = history_loader.load_jsonl(
        os.path.join(HERE, "config", "tasks.jsonl"))
    seed_events = history_loader.load_jsonl(
        os.path.join(HERE, "config", "history-events.jsonl"))
    known_event_ids = {e["event_id"] for e in seed_events}

    problems = validate(pre_records, post_records, queries, tasks,
                        known_event_ids)

    # 7. tamper self-test: this same validator must catch mutation/deletion.
    tamper_checks_passed = True
    import copy
    for index in range(len(pre_records)):
        mutated = copy.deepcopy(pre_records)
        mutated[index]["selected_agent_before_query"] = "did:example:evil"
        if not validate(mutated, post_records, queries, tasks,
                        known_event_ids):
            tamper_checks_passed = False
        deleted = [r for i, r in enumerate(pre_records) if i != index]
        if not validate(deleted, post_records, queries, tasks,
                        known_event_ids):
            tamper_checks_passed = False
    for index in range(len(post_records)):
        mutated = copy.deepcopy(post_records)
        mutated[index]["decision_changed"] = not mutated[index][
            "decision_changed"]
        if not validate(pre_records, mutated, queries, tasks,
                        known_event_ids):
            tamper_checks_passed = False
        deleted = [r for i, r in enumerate(post_records) if i != index]
        if not validate(pre_records, deleted, queries, tasks,
                        known_event_ids):
            tamper_checks_passed = False

    checks = {
        "pre_query_records": len(pre_records),
        "post_query_records": len(post_records),
        "queries": len(queries),
        "problems": problems,
        "tamper_self_test_passed": tamper_checks_passed,
        "status": "PASS" if not problems and tamper_checks_passed
        else "FAIL",
    }
    print(json.dumps(checks, indent=2))
    return 0 if checks["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
