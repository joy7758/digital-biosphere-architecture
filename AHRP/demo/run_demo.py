#!/usr/bin/env python3
"""AHRP v0.1 minimal demo (SYNTHETIC_ONLY, Python 3 stdlib only).

Scenario:
  1. Agent A executes a task -> an Experience Event is produced.
  2. An Evidence Reference is bound (reference-style; no evidence body).
  3. A named verifier produces a Verification Record.
  4. Both records pass reference validation and are ingested (fail-closed).
  5. Agent B asks "does this agent have relevant history?" and receives the
     Experience Summary FIRST (Selective Disclosure First), then drills down
     into detail only on explicit request.

Run from the AHRP root:  python3 demo/run_demo.py

Truth boundaries:
  SYNTHETIC_ONLY=true; no real agents, no real evidence, no network.
  This demo is a reference illustration, not a conformance certification.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AHRP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AHRP_ROOT))

from query import HistoryStore, structured_decision_inputs  # noqa: E402
from query.engine import IngestError  # noqa: E402
from validator import (  # noqa: E402
    validate_experience_event,
    validate_verification_record,
)

BANNER = "=" * 72


def show(title: str, payload) -> None:
    print(f"\n{BANNER}\n{title}\n{BANNER}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> int:
    print(BANNER)
    print("AHRP v0.1 minimal demo -- SYNTHETIC_ONLY=true")
    print("AHRP is a Historical Experience Protocol, NOT a Rating /")
    print("Recommendation / Learning System.")
    print(BANNER)

    # -- Step 1+2: Agent A executes a task; event produced with evidence ref.
    event = {
        "schema_version": "0.1.0",
        "event_id": "evt-demo-0001",
        "agent_reference": {
            "identity_source": "DBOS",
            "identity_ref": "did:example:agent-A",
        },
        "agent_version": "1.2.0",
        "task_type": "DATA_PROCESSING",
        "action_type": "EXECUTE",
        "result_status": "SUCCESS",
        "occurred_at": "2026-08-04T10:00:00Z",
        "evidence_references": [
            {
                "source": "CI_ARTIFACT",
                "version": "2.1.0",
                "reference_id": "ci-run-1/artifacts/report.json",
                "hash": "sha256:" + "ab" * 32,
                "availability_status": "AVAILABLE",
            }
        ],
        "verification_references": [
            {"verification_id": "ver-demo-0001", "verifier_name": "orchestrator-x"}
        ],
        "disclosure": {"disclosure_scope": "FEDERATED",
                       "declared_by": "agent-A-holder"},
        "notes": "SYNTHETIC_ONLY demo note (DATA channel, never an instruction).",
    }

    verification = {
        "schema_version": "0.1.0",
        "verification_id": "ver-demo-0001",
        "verifier": {
            "verifier_name": "orchestrator-x",
            "verifier_class": "ORCHESTRATOR",
        },
        "verification_type": "EVENT_CONFIRMATION",
        "verification_status": "VERIFIED",
        "verified_at": "2026-08-04T10:05:00Z",
        "scope": {
            "subject_event_id": "evt-demo-0001",
            "subject_type": "EXPERIENCE_EVENT",
            "covered_aspect": "FULL_EVENT",
            "agent_ref": "did:example:agent-A",
            "agent_version": "1.2.0",
        },
        "self_verification": False,
        "authorization_effect": "NONE",
    }

    # -- Step 3+4: validate then ingest (fail-closed).
    ev_result = validate_experience_event(event)
    vr_result = validate_verification_record(verification)
    show("Step 1-3: validation results (PASS required before ingest)",
         {"event": ev_result.to_dict(), "verification": vr_result.to_dict()})
    if not (ev_result.valid and vr_result.valid):
        print("demo aborted: validation failed")
        return 1

    store = HistoryStore()
    store.ingest_event(event)
    store.ingest_verification(verification)
    print("\nStep 4: event + verification ingested into the federated holder.")

    # A second, unverified event to make counts meaningful.
    event2 = dict(event)
    event2["event_id"] = "evt-demo-0002"
    event2["task_type"] = "ANALYSIS"
    event2["result_status"] = "FAILURE"
    event2["failure_category"] = "RESOURCE_UNAVAILABLE"
    event2["verification_references"] = []
    event2["evidence_references"] = []
    event2["occurred_at"] = "2026-08-04T11:00:00Z"
    store.ingest_event(event2)

    # -- Step 5: Agent B queries. Summary FIRST (default).
    summary = store.summary("did:example:agent-A")
    show("Step 5a: Agent B asks 'any relevant history?' -> SUMMARY FIRST "
         "(raw counts; no ratios, no scores)", summary)

    decisions = structured_decision_inputs(summary)
    print("\nConsumer decision path receives ONLY structured facts:")
    print(json.dumps(decisions, indent=2, ensure_ascii=False))

    # Filtered queries.
    coding_like = store.query_events(identity_ref="did:example:agent-A",
                                     task_type="DATA_PROCESSING")
    show("Step 5b: filtered by task_type=DATA_PROCESSING (summary projection)",
         coding_like["result"])

    verified_only = store.query_events(identity_ref="did:example:agent-A",
                                       verification_status="VERIFIED")
    show("Step 5c: filtered by verification_status=VERIFIED",
         verified_only["result"])

    # On-demand drill-down (explicit capability='detail').
    detail = store.get_event("evt-demo-0001", capability="detail")
    show("Step 5d: explicit drill-down -> detail; note travels in "
         "restricted_text channel and is excluded from decisions", detail)

    # Three-state null semantics demonstration.
    unknown = store.summary("did:example:nobody")
    failure_q = store.get_failure_category("evt-demo-0002")
    na_q = store.get_failure_category("evt-demo-0001")
    show("Step 6: three-state null semantics", {
        "unknown_agent": unknown["null_semantics"],
        "failure_event_category": {
            "null_semantics": failure_q["null_semantics"],
            "failure_category": failure_q["result"]["failure_category"],
        },
        "success_event_category": na_q["null_semantics"],
    })

    print(f"\n{BANNER}\nDemo complete. SYNTHETIC_ONLY=true; no real agents, "
          f"no real evidence.\n{BANNER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
