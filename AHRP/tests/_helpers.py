"""Shared synthetic builders for AHRP tests (SYNTHETIC_ONLY)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

AHRP_ROOT = Path(__file__).resolve().parent.parent
if str(AHRP_ROOT) not in sys.path:
    sys.path.insert(0, str(AHRP_ROOT))

EXAMPLES_DIR = AHRP_ROOT / "examples"

VALID_HASH = "sha256:" + "ab" * 32


def make_event(**overrides):
    event = {
        "schema_version": "0.1.0",
        "event_id": "evt-test-0001",
        "agent_reference": {
            "identity_source": "DBOS",
            "identity_ref": "did:example:test-agent",
        },
        "agent_version": "1.0.0",
        "task_type": "DATA_PROCESSING",
        "action_type": "EXECUTE",
        "result_status": "SUCCESS",
        "occurred_at": "2026-08-01T09:30:00Z",
        "evidence_references": [
            {
                "source": "CI_ARTIFACT",
                "version": "1.0.0",
                "reference_id": "ci-run-1/artifacts/report.json",
                "hash": VALID_HASH,
                "availability_status": "AVAILABLE",
            }
        ],
        "verification_references": [],
        "disclosure": {"disclosure_scope": "FEDERATED",
                       "declared_by": "test-holder"},
    }
    event.update(copy.deepcopy(overrides))
    return event


def make_verification(**overrides):
    record = {
        "schema_version": "0.1.0",
        "verification_id": "ver-test-0001",
        "verifier": {
            "verifier_name": "named-verifier-1",
            "verifier_class": "NAMED_VERIFIER",
        },
        "verification_type": "EVENT_CONFIRMATION",
        "verification_status": "VERIFIED",
        "verified_at": "2026-08-01T10:00:00Z",
        "scope": {
            "subject_event_id": "evt-test-0001",
            "subject_type": "EXPERIENCE_EVENT",
            "covered_aspect": "FULL_EVENT",
            "agent_ref": "did:example:test-agent",
            "agent_version": "1.0.0",
        },
        "self_verification": False,
        "authorization_effect": "NONE",
    }
    record.update(copy.deepcopy(overrides))
    return record


def load_example(name: str):
    with open(EXAMPLES_DIR / name, "r", encoding="utf-8") as fh:
        return json.load(fh)
