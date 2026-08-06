"""Clean-package verifier for the method-v2 evidence ZIP.

Verifies a packaged evidence bundle IN ISOLATION:

 1. unpack into a fresh temporary directory;
 2. refuse ZIP path traversal, absolute paths, and symlinks;
 3. verify the unified MANIFEST.sha256 (full bidirectional coverage and
    per-file SHA-256 equality);
 4. parse every JSON / JSONL file in the package;
 5. validate every final Experience Event and Verification Record with the
    PACKAGED AHRP Validator, including complete event/verification binding;
 6. verify evidence references (packaged verify_evidence_references.py);
 7. validate the shadow protocol (packaged validate_shadow_protocol.py);
 8. verify the truth-boundary file;
 9. exit non-zero on any anomaly.

The package is expected to contain: AHRP/, docs/, the experiment directory,
TRUTH_BOUNDARY.txt, git-baseline.txt and MANIFEST.sha256 (built by
build_evidence_package.py).
"""

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_ZIP = os.path.join(REPO_ROOT, "experiments",
                           "AHRP-pilot-readiness-method-v2-evidence.zip")
MANIFEST_NAME = "MANIFEST.sha256"
EXPERIMENT_REL = os.path.relpath(HERE, REPO_ROOT)

REQUIRED_TRUTH_BOUNDARIES = {
    "CONTROLLED_INTERNAL_EXPERIMENT": "true",
    "SYNTHETIC_AGENT_ROSTER": "true",
    "REAL_EXTERNAL_AGENT": "false",
    "REAL_WORLD_ADOPTION_VALIDATED": "false",
    "AHRP_PRODUCTION_READY": "false",
    "AHRP_STANDARD_PUBLISHED": "false",
    "NETWORK_SERVICE_RECOMMENDATION": "DEFER",
    "PR12_EXPERIMENT_RESULT": "INVALIDATED",
    "CLEANROOM_EXPERIMENT_RESULT": "INCONCLUSIVE",
    "REAL_INDEPENDENT_VERIFICATION": "false",
    "SYNTHETIC_SYSTEM_VERIFICATION": "true",
    "POST_RUN_RECOMPUTATION_VERIFIED": "true",
    "AHRP_V0_1_MODIFIED": "false",
}


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(zip_path: str, dest: str) -> None:
    """Unpack refusing traversal, absolute paths and symlinks."""
    dest_real = os.path.realpath(dest)
    with zipfile.ZipFile(zip_path) as bundle:
        for info in bundle.infolist():
            name = info.filename
            if name.endswith("/"):
                continue
            parts = name.replace("\\", "/").split("/")
            if os.path.isabs(name) or ".." in parts or \
                    (len(parts[0]) > 1 and parts[0][1] == ":"):
                raise SystemExit(
                    f"VERIFY_ABORTED: unsafe ZIP entry path: {name}")
            file_mode = (info.external_attr >> 16) & 0o170000
            if file_mode == stat.S_IFLNK:
                raise SystemExit(
                    f"VERIFY_ABORTED: symlink entry refused: {name}")
            target = os.path.realpath(os.path.join(dest_real, name))
            if not target.startswith(dest_real + os.sep):
                raise SystemExit(
                    f"VERIFY_ABORTED: path traversal refused: {name}")
            bundle.extract(info, dest)


def list_package_files(root: str) -> List[str]:
    found = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            found.append(os.path.relpath(os.path.join(dirpath, name), root))
    return sorted(found)


def verify_manifest(root: str, problems: List[str]) -> Dict[str, str]:
    manifest_path = os.path.join(root, MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        problems.append("MANIFEST.sha256 missing from package")
        return {}
    entries: Dict[str, str] = {}
    with open(manifest_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            if "  " not in line:
                problems.append(f"malformed manifest line: {line!r}")
                continue
            digest, rel = line.split("  ", 1)
            entries[rel] = digest
    disk = set(list_package_files(root)) - {MANIFEST_NAME}
    for rel in sorted(set(entries) - disk):
        problems.append(f"manifest lists missing file: {rel}")
    for rel in sorted(disk - set(entries)):
        problems.append(f"file not covered by manifest: {rel}")
    for rel in sorted(set(entries) & disk):
        actual = file_sha256(os.path.join(root, rel))
        if actual != entries[rel]:
            problems.append(f"sha256 mismatch: {rel}")
    return entries


def parse_all_json(root: str, problems: List[str]) -> int:
    parsed = 0
    for rel in list_package_files(root):
        path = os.path.join(root, rel)
        try:
            if rel.endswith(".json"):
                json.load(open(path, encoding="utf-8"))
                parsed += 1
            elif rel.endswith(".jsonl"):
                with open(path, encoding="utf-8") as handle:
                    for line_number, line in enumerate(handle, 1):
                        if line.strip():
                            json.loads(line)
                parsed += 1
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            problems.append(f"unparseable JSON in {rel}: {exc}")
    return parsed


def load_packaged_validator(ahp_dir: str):
    """Import validator.core from the PACKAGED AHRP tree, not the repo."""
    for module_name in list(sys.modules):
        if module_name == "validator" or module_name.startswith("validator."):
            del sys.modules[module_name]
    sys.path.insert(0, ahp_dir)
    try:
        from validator.core import (validate_experience_event,
                                    validate_verification_record)
    finally:
        sys.path.remove(ahp_dir)
    return validate_experience_event, validate_verification_record


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def verify_generated_objects(experiment_dir: str,
                             problems: List[str]) -> Dict[str, int]:
    validate_event, validate_verification = load_packaged_validator(
        os.path.join(experiment_dir, "..", "..", "AHRP"))
    events = load_jsonl(
        os.path.join(experiment_dir, "data", "experience-events.jsonl"))
    verifications = load_jsonl(
        os.path.join(experiment_dir, "data", "verification-records.jsonl"))
    unverified = load_jsonl(os.path.join(
        experiment_dir, "data", "experience-events-unverified.jsonl"))

    schema_ok = 0
    for event in events:
        result = validate_event(event)
        if result.valid:
            schema_ok += 1
        else:
            problems.append(f"schema FAIL event {event['event_id']}: "
                            f"{result.errors}")
    verification_ok = 0
    for record in verifications:
        result = validate_verification(record)
        if result.valid:
            verification_ok += 1
        else:
            problems.append(
                f"schema FAIL verification {record['verification_id']}: "
                f"{result.errors}")
    for event in unverified:
        if event.get("verification_references"):
            problems.append(
                f"{event['event_id']}: runner output carries verification "
                "references")

    # Complete binding: every event has exactly one matching verification
    # and every verification matches its subject event on all bound fields.
    verification_by_subject = {}
    for record in verifications:
        subject = record["scope"]["subject_event_id"]
        verification_by_subject.setdefault(subject, []).append(record)
    event_by_id = {e["event_id"]: e for e in events}
    for event_id, records in verification_by_subject.items():
        event = event_by_id.get(event_id)
        if event is None:
            problems.append(f"verification without subject event: "
                            f"{event_id}")
            continue
        for record in records:
            agent = event["agent_reference"]
            verifier = record["verifier"]
            scope = record["scope"]
            checks = [
                (scope.get("agent_ref"), agent["identity_ref"]),
                (scope.get("agent_version"), event["agent_version"]),
                (scope.get("covered_aspect"), "FULL_EVENT"),
                (verifier.get("verifier_class"), "SYSTEM_BENCHMARK"),
                (verifier.get("verifier_name"),
                 "method-v2-post-run-verifier"),
            ]
            for actual, expected in checks:
                if actual != expected:
                    problems.append(
                        f"binding mismatch for {event_id}: expected "
                        f"{expected!r}, got {actual!r}")
        reference_ids = {ref.get("verification_id")
                         for ref in event["verification_references"]}
        record_ids = {r["verification_id"] for r in records}
        if reference_ids != record_ids:
            problems.append(
                f"{event_id}: verification_references do not match the "
                "verification records")
    unbound = set(event_by_id) - set(verification_by_subject)
    for event_id in sorted(unbound):
        problems.append(f"event without verification: {event_id}")
    return {"events_checked": len(events),
            "verifications_checked": len(verifications),
            "events_schema_ok": schema_ok,
            "verifications_schema_ok": verification_ok}


def run_packaged_script(experiment_dir: str, script: str,
                        problems: List[str]) -> None:
    completed = subprocess.run([sys.executable, script],
                               cwd=experiment_dir,
                               capture_output=True, text=True)
    if completed.returncode != 0:
        problems.append(f"{script} exited rc={completed.returncode}")
        problems.append(completed.stderr.strip()[-2000:] or
                        completed.stdout.strip()[-2000:])


def verify_truth_boundary(root: str, problems: List[str]) -> None:
    path = os.path.join(root, "TRUTH_BOUNDARY.txt")
    if not os.path.isfile(path):
        problems.append("TRUTH_BOUNDARY.txt missing from package")
        return
    flags = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                flags[key] = value
    for key, expected in REQUIRED_TRUTH_BOUNDARIES.items():
        if flags.get(key) != expected:
            problems.append(
                f"truth boundary violation: {key} expected {expected}, "
                f"got {flags.get(key)!r}")
    if not os.path.isfile(os.path.join(root, "git-baseline.txt")):
        problems.append("git-baseline.txt missing from package")


def main() -> int:
    zip_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ZIP
    if not os.path.isfile(zip_path):
        print(f"VERIFY_ABORTED: package not found: {zip_path}",
              file=sys.stderr)
        return 2

    problems: List[str] = []
    extract_dir = tempfile.mkdtemp(prefix="ahrp-mv2-verify-")
    summary: Dict[str, Any] = {"package": zip_path}
    try:
        # 1-2. fresh unpack with traversal / symlink refusal
        safe_extract(zip_path, extract_dir)
        summary["unpacked"] = True

        # 3. unified manifest
        verify_manifest(extract_dir, problems)

        # 4. parse all JSON / JSONL
        summary["json_files_parsed"] = parse_all_json(extract_dir, problems)

        # 5. generated objects through the packaged AHRP validator
        experiment_dir = os.path.join(extract_dir, EXPERIMENT_REL)
        if not os.path.isdir(experiment_dir):
            problems.append(f"experiment directory missing: "
                            f"{EXPERIMENT_REL}")
        else:
            summary["generated_objects"] = verify_generated_objects(
                experiment_dir, problems)
            # 6. evidence references
            run_packaged_script(experiment_dir,
                                "verify_evidence_references.py", problems)
            # 7. shadow protocol
            run_packaged_script(experiment_dir,
                                "validate_shadow_protocol.py", problems)

        # 8. truth boundary
        verify_truth_boundary(extract_dir, problems)
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)

    summary["status"] = "PASS" if not problems else "FAIL"
    summary["problems"] = problems
    print(json.dumps(summary, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
