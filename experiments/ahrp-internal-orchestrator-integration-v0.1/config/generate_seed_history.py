#!/usr/bin/env python3
"""Generate deterministic seed history for the internal orchestrator
integration trial (AHRP 内部编排器集成试验 v0.1).

Seeds are pre-existing AHRP records that the programmatic orchestrator
component will query during AHRP_ASSISTED_MODE. They are NOT produced by
this trial's worker components.

Every seed carries:
* a real evidence body file under evidence/seed/ with a real SHA-256 hash;
* a SYSTEM_BENCHMARK verification (NOT INDEPENDENT_AGENT -- the truth
  boundary REAL_INDEPENDENT_VERIFICATION=false must be preserved).

Output: config/history-events.jsonl, config/history-verifications.jsonl.
Deterministic: fixed timestamps and fixed content, no randomness, no clock.
"""

import hashlib
import json
from pathlib import Path

EXP_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = EXP_ROOT / "evidence" / "seed"

VERIFIER_NAME = "integration-trial-seed-verifier"

AGENTS = {
    "alpha": "did:example:worker-alpha",
    "beta": "did:example:worker-beta",
    "gamma": "did:example:worker-gamma",
}

SEEDS = [
    # worker-alpha: coding failure at the dependency-resolution boundary
    {
        "key": "alpha-dep",
        "agent": "alpha",
        "task_type": "CODING",
        "result_status": "FAILURE",
        "failure_category": "CAPABILITY_LIMIT",
        "occurred_at": "2026-08-01T09:05:00Z",
        "evidence_text": (
            "Seed record: worker-alpha attempted a coding task requiring "
            "third-party dependency resolution. The worker has no "
            "package-index access (declared boundary), so the dependency "
            "could not be resolved and the task failed."
        ),
    },
    {
        "key": "alpha-ok",
        "agent": "alpha",
        "task_type": "CODING",
        "result_status": "SUCCESS",
        "failure_category": None,
        "occurred_at": "2026-08-01T10:15:00Z",
        "evidence_text": (
            "Seed record: worker-alpha completed a self-contained coding "
            "task within its declared boundary; produced module compiled "
            "and passed its smoke test."
        ),
    },
    # worker-beta: research failure due to the no-external-source policy
    {
        "key": "beta-src",
        "agent": "beta",
        "task_type": "RESEARCH",
        "result_status": "FAILURE",
        "failure_category": "POLICY_RESTRICTION",
        "occurred_at": "2026-08-01T11:25:00Z",
        "evidence_text": (
            "Seed record: worker-beta attempted a research task requiring "
            "live external sources. Sandbox policy forbids external source "
            "access, so the task failed under a policy restriction."
        ),
    },
    {
        "key": "beta-ok",
        "agent": "beta",
        "task_type": "RESEARCH",
        "result_status": "SUCCESS",
        "failure_category": None,
        "occurred_at": "2026-08-01T13:40:00Z",
        "evidence_text": (
            "Seed record: worker-beta completed a research task using only "
            "locally available documents and produced a structured note."
        ),
    },
    # worker-gamma: review failure at the security-audit boundary
    {
        "key": "gamma-sec",
        "agent": "gamma",
        "task_type": "VERIFICATION",
        "result_status": "FAILURE",
        "failure_category": "CAPABILITY_LIMIT",
        "occurred_at": "2026-08-01T15:50:00Z",
        "evidence_text": (
            "Seed record: worker-gamma attempted a review task requiring a "
            "security audit. Security auditing is outside its declared "
            "boundary, so the task failed."
        ),
    },
    {
        "key": "gamma-ok",
        "agent": "gamma",
        "task_type": "VERIFICATION",
        "result_status": "SUCCESS",
        "failure_category": None,
        "occurred_at": "2026-08-01T16:35:00Z",
        "evidence_text": (
            "Seed record: worker-gamma completed a consistency review "
            "within its declared boundary and produced findings."
        ),
    },
]


def build() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    events = []
    verifications = []
    for seed in SEEDS:
        event_id = f"evt-seed-{seed['key']}-001"
        verification_id = f"ver-seed-{seed['key']}-001"
        agent_ref = AGENTS[seed["agent"]]

        evidence_body = seed["evidence_text"] + "\n"
        evidence_path = EVIDENCE_DIR / f"{event_id}.txt"
        evidence_path.write_text(evidence_body, encoding="utf-8")
        evidence_hash = hashlib.sha256(evidence_body.encode("utf-8")).hexdigest()

        event = {
            "schema_version": "0.1.0",
            "event_id": event_id,
            "agent_reference": {"identity_source": "DBOS", "identity_ref": agent_ref},
            "agent_version": "1.0.0",
            "task_type": seed["task_type"],
            "action_type": "EXECUTE",
            "result_status": seed["result_status"],
            "occurred_at": seed["occurred_at"],
            "evidence_references": [
                {
                    "source": "TITMAS_EVIDENCE",
                    "version": "1.0",
                    "reference_id": f"ev-seed-{seed['key']}-001",
                    "hash": f"sha256:{evidence_hash}",
                    "availability_status": "AVAILABLE",
                }
            ],
            "verification_references": [
                {"verification_id": verification_id, "verifier_name": VERIFIER_NAME}
            ],
            "disclosure": {
                "disclosure_scope": "PUBLIC",
                "declared_by": "integration-trial-seed-generator",
            },
        }
        if seed["failure_category"] is not None:
            event["failure_category"] = seed["failure_category"]

        verification = {
            "schema_version": "0.1.0",
            "verification_id": verification_id,
            "verifier": {
                "verifier_name": VERIFIER_NAME,
                "verifier_class": "SYSTEM_BENCHMARK",
            },
            "verification_type": "EVENT_CONFIRMATION",
            "verification_status": "VERIFIED",
            "verified_at": "2026-08-02T08:00:00Z",
            "scope": {
                "subject_event_id": event_id,
                "subject_type": "EXPERIENCE_EVENT",
                "agent_ref": agent_ref,
                "agent_version": "1.0.0",
                "covered_aspect": "FULL_EVENT",
            },
            "self_verification": False,
            "authorization_effect": "NONE",
        }
        events.append(event)
        verifications.append(verification)

    with open(EXP_ROOT / "config" / "history-events.jsonl", "w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
    with open(EXP_ROOT / "config" / "history-verifications.jsonl", "w", encoding="utf-8") as fh:
        for verification in verifications:
            fh.write(json.dumps(verification, sort_keys=True, ensure_ascii=False) + "\n")

    print(f"seed events: {len(events)}")
    print(f"seed verifications: {len(verifications)}")
    print(f"evidence bodies: {EVIDENCE_DIR}")


if __name__ == "__main__":
    build()
