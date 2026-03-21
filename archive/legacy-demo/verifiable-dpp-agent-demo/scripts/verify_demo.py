#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "input" / "dpp_passport_sample.json"
OUTPUT_DIR = BASE_DIR / "output"
AGENT_RESULT_PATH = OUTPUT_DIR / "agent_result.json"
AUDIT_RECORD_PATH = OUTPUT_DIR / "aro_audit_record.json"
MVK_INPUT_PATH = OUTPUT_DIR / "mvk_input.json"
PUBLIC_SUMMARY_PATH = OUTPUT_DIR / "public_evidence_summary.json"

PROFILE_HANDLE = "21.T11966/aro-audit-profile-v1"
DEMO_HANDLE = "21.T11966/aro-audit-demo-do-1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    print("VERIFY_FAIL")
    print(message, file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    dpp_object = load_json(INPUT_PATH)
    agent_result = load_json(AGENT_RESULT_PATH)
    audit_record = load_json(AUDIT_RECORD_PATH)
    mvk_input = load_json(MVK_INPUT_PATH)
    public_summary = load_json(PUBLIC_SUMMARY_PATH)

    input_hash = sha256_file(INPUT_PATH)
    agent_hash = sha256_file(AGENT_RESULT_PATH)
    audit_hash = sha256_file(AUDIT_RECORD_PATH)

    if audit_record.get("journal_sha256") != agent_hash:
        fail("agent_result hash does not match audit journal hash")
    if mvk_input.get("input_object_sha256") != input_hash:
        fail("input object hash does not match mvk input")
    if mvk_input.get("audit_record_sha256") != audit_hash:
        fail("audit record hash does not match mvk input")
    if mvk_input.get("agent_result_sha256") != agent_hash:
        fail("agent result hash does not match mvk input")

    for entry in public_summary.get("generated_files", []):
        rel_path = entry.get("path")
        expected_hash = entry.get("sha256")
        target_path = BASE_DIR / rel_path
        if not rel_path or not expected_hash or not target_path.is_file():
            fail("public evidence summary references a missing generated file")
        if sha256_file(target_path) != expected_hash:
            fail(f"public evidence summary hash mismatch for {rel_path}")

    if audit_record.get("profile_handle") != PROFILE_HANDLE:
        fail("profile handle mismatch")
    if audit_record.get("demo_handle") != DEMO_HANDLE:
        fail("demo handle mismatch")
    if public_summary.get("profile_handle") != PROFILE_HANDLE:
        fail("public summary profile handle mismatch")
    if public_summary.get("demo_handle") != DEMO_HANDLE:
        fail("public summary demo handle mismatch")
    if agent_result.get("object_id") != dpp_object.get("object_id"):
        fail("agent result object_id mismatch")

    print("VERIFY_PASS")


if __name__ == "__main__":
    main()
