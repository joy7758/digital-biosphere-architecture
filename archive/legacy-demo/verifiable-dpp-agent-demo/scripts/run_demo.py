#!/usr/bin/env python3

import hashlib
import json
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
SPEC_URL = "https://github.com/joy7758/aro-audit/blob/main/docs/aroaudit-profile-v1.md"
MANIFEST_HANDLE = "demo://verifiable-dpp-agent-demo/manifest-v1"
PUBLIC_KEY_FINGERPRINT = "demo-fingerprint-static"
PAPER_DOI = "10.5281/zenodo.18501430"
MVK_REPO = "https://github.com/joy7758/fdo-kernel-mvk"
ARCHITECTURE_REPO = "https://github.com/joy7758/digital-biosphere-architecture"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, sort_keys=True, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dpp_object = load_json(INPUT_PATH)

    agent_result = {
        "compliance_status": "REVIEW_READY",
        "object_id": dpp_object["object_id"],
        "product_name": dpp_object["product_name"],
        "summary": (
            f"Object {dpp_object['object_id']} for {dpp_object['product_name']} "
            f"records {dpp_object['carbon_record']['value']} "
            f"{dpp_object['carbon_record']['unit']} and is REVIEW_READY."
        ),
        "task": dpp_object["compliance_task"],
        "carbon_record": dpp_object["carbon_record"],
    }
    save_json(AGENT_RESULT_PATH, agent_result)

    audit_record = {
        "demo_handle": DEMO_HANDLE,
        "journal_sha256": sha256_file(AGENT_RESULT_PATH),
        "manifest_handle": MANIFEST_HANDLE,
        "profile_handle": PROFILE_HANDLE,
        "public_key_fingerprint": PUBLIC_KEY_FINGERPRINT,
        "spec_url": SPEC_URL,
    }
    save_json(AUDIT_RECORD_PATH, audit_record)

    mvk_input = {
        "agent_result_sha256": sha256_file(AGENT_RESULT_PATH),
        "audit_record_sha256": sha256_file(AUDIT_RECORD_PATH),
        "input_object_sha256": sha256_file(INPUT_PATH),
        "proof_mode": "deterministic-demo",
    }
    save_json(MVK_INPUT_PATH, mvk_input)

    public_evidence_summary = {
        "architecture_repo": ARCHITECTURE_REPO,
        "demo_handle": DEMO_HANDLE,
        "generated_files": [
            {
                "path": "output/agent_result.json",
                "sha256": sha256_file(AGENT_RESULT_PATH),
            },
            {
                "path": "output/aro_audit_record.json",
                "sha256": sha256_file(AUDIT_RECORD_PATH),
            },
            {
                "path": "output/mvk_input.json",
                "sha256": sha256_file(MVK_INPUT_PATH),
            },
        ],
        "mvk_repo": MVK_REPO,
        "paper_doi": PAPER_DOI,
        "profile_handle": PROFILE_HANDLE,
        "spec_url": SPEC_URL,
    }
    save_json(PUBLIC_SUMMARY_PATH, public_evidence_summary)

    print("DEMO_BUILD_OK")


if __name__ == "__main__":
    main()
