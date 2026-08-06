"""Evidence reference verifier for the method-v2 experiment.

For EVERY Experience Event (seed history + experiment run events):

 1. parse the event;
 2. resolve each evidence reference to a relative evidence path;
 3. block path traversal (resolved path must stay under evidence/);
 4. read the file bytes;
 5. recompute SHA-256;
 6. compare against the reference hash;
 7. exit non-zero on any missing file, mismatch, or placeholder hash.

Placeholder hashes are rejected explicitly: no reference may reuse another
reference's hash, and obviously-repeated fixture digests are flagged.
"""

import hashlib
import json
import os
import sys
from typing import Dict, List

import history_loader

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE_ROOT = os.path.abspath(os.path.join(HERE, "evidence"))


def resolve_reference(reference_id: str) -> str:
    """Map a reference_id to its evidence file path (traversal-safe)."""
    if reference_id.startswith("exec-"):
        task_id = reference_id[len("exec-"):]
        candidate = os.path.join(EVIDENCE_ROOT, "executions",
                                 f"{task_id}.json")
    elif reference_id.startswith("ev-"):
        # Seed evidence files are named without the leading "ev-".
        candidate = os.path.join(EVIDENCE_ROOT, "history",
                                 f"{reference_id[len('ev-'):]}" ".json")
    else:
        candidate = os.path.join(EVIDENCE_ROOT, "history",
                                 f"{reference_id}.json")
    resolved = os.path.abspath(candidate)
    if os.path.commonpath([resolved, EVIDENCE_ROOT]) != EVIDENCE_ROOT:
        raise ValueError(f"PATH_TRAVERSAL_BLOCKED ref={reference_id}")
    return resolved


def check_events(events: List[Dict], source_label: str,
                 problems: List[str], seen_hashes: Dict[str, str]) -> int:
    checked = 0
    for event in events:
        event_id = event.get("event_id", "<unknown>")
        for reference in event.get("evidence_references", []):
            ref_hash = reference.get("hash", "")
            reference_id = reference.get("reference_id", "")
            if not ref_hash.startswith("sha256:"):
                problems.append(
                    f"{source_label}:{event_id} hash not sha256-prefixed")
                continue
            expected = ref_hash[len("sha256:"):]
            try:
                path = resolve_reference(reference_id)
            except ValueError as exc:
                problems.append(f"{source_label}:{event_id} {exc}")
                continue
            if not os.path.isfile(path):
                problems.append(
                    f"{source_label}:{event_id} evidence file missing: "
                    f"{reference_id}")
                continue
            digest = hashlib.sha256()
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(65536), b""):
                    digest.update(chunk)
            actual = digest.hexdigest()
            if actual != expected:
                problems.append(
                    f"{source_label}:{event_id} hash mismatch for "
                    f"{reference_id}: expected {expected} actual {actual}")
            if expected in seen_hashes and \
                    seen_hashes[expected] != reference_id:
                problems.append(
                    f"{source_label}:{event_id} duplicate hash reused "
                    f"(placeholder suspected): {expected}")
            seen_hashes[expected] = reference_id
            checked += 1
    return checked


def main() -> int:
    problems: List[str] = []
    seen_hashes: Dict[str, str] = {}
    seed_events = history_loader.load_jsonl(
        os.path.join(HERE, "config", "history-events.jsonl"))
    run_events_path = os.path.join(HERE, "data", "experience-events.jsonl")
    run_events = history_loader.load_jsonl(run_events_path) \
        if os.path.isfile(run_events_path) else []
    if not run_events:
        problems.append("no run experience events found "
                        "(run run_experiment.py first)")

    seed_checked = check_events(seed_events, "seed", problems, seen_hashes)
    run_checked = check_events(run_events, "run", problems, seen_hashes)

    result = {
        "status": "PASS" if not problems else "FAIL",
        "seed_events_checked": len(seed_events),
        "run_events_checked": len(run_events),
        "evidence_references_verified": seed_checked + run_checked,
        "distinct_evidence_hashes": len(seen_hashes),
        "problems": problems,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
