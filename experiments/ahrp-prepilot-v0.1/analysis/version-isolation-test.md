# Phase-2 Version Isolation Test (researcher-gamma)

Control: CONTROLLED_INTERNAL_PREPILOT=true, CONTROLLED_INTERNAL_TASK=true,
REAL_EXTERNAL_AGENT=false, SYNTHETIC_MARKET_ADOPTION=false,
REAL_WORLD_ADOPTION_VALIDATED=false. AHRP baseline 64bfed1f3063f4f463bb1e2680ef6b0b1d312201
(frozen, read-only). All timestamps are real UTC from the phase-2 run.

## Setup
1. `researcher-gamma@1.1.0` appended to `config/agents.json`.
2. Cold-start query `q-p2-cs2` for `researcher-gamma@1.1.0` executed BEFORE
   any 1.1.0 event existed -> `null_semantics=NO_RECORD` -> Rule D
   LOW_RISK_ONLY (high-risk withheld).
3. One low-risk SUCCESS event `evt-prepilot-p2-gamma110` ingested for
   `researcher-gamma@1.1.0` (independently verified by `ver-prepilot-p2-gamma110`).

## Query 1: version=1.1.0 (`q-p2-iso110`, query_events)
params: `{"identity_ref": "researcher-gamma", "agent_version": "1.1.0"}`

```
{
  "events": [
    {
      "event_id": "evt-prepilot-p2-gamma110",
      "agent_version": "1.1.0",
      "task_type": "RESEARCH",
      "action_type": "EXECUTE",
      "result_status": "SUCCESS",
      "failure_category": "NOT_APPLICABLE",
      "occurred_at": "2026-08-04T20:32:03.579248+00:00",
      "verification_status": "VERIFIED",
      "evidence_availability": [
        "AVAILABLE"
      ],
      "verifier_classes": [
        "INDEPENDENT_AGENT"
      ],
      "has_independent_verification": true,
      "self_only": false,
      "independence_class": "INDEPENDENT"
    }
  ],
  "count": 1
}
```

Returned event ids: `['evt-prepilot-p2-gamma110']` -> contains ONLY the new 1.1.0 event;
none of the 3 historical v1.0.0 events leaked into the new version
(cold start; identity continuity fail-closed).

## Query 2: version=1.0.0 (`q-p2-iso100`, query_events)
params: `{"identity_ref": "researcher-gamma", "agent_version": "1.0.0"}`

```
{
  "events": [
    {
      "event_id": "evt-prepilot-004",
      "agent_version": "1.0.0",
      "task_type": "RESEARCH",
      "action_type": "EXECUTE",
      "result_status": "SUCCESS",
      "failure_category": "NOT_APPLICABLE",
      "occurred_at": "2026-08-05T04:28:00+08:00",
      "verification_status": "VERIFIED",
      "evidence_availability": [
        "AVAILABLE"
      ],
      "verifier_classes": [
        "INDEPENDENT_AGENT"
      ],
      "has_independent_verification": true,
      "self_only": false,
      "independence_class": "INDEPENDENT"
    },
    {
      "event_id": "evt-prepilot-r3",
      "agent_version": "1.0.0",
      "task_type": "RESEARCH",
      "action_type": "EXECUTE",
      "result_status": "SUCCESS",
      "failure_category": "NOT_APPLICABLE",
      "occurred_at": "2026-08-04T20:32:03.577723+00:00",
      "verification_status": "VERIFIED",
      "evidence_availability": [
        "AVAILABLE"
      ],
      "verifier_classes": [
        "INDEPENDENT_AGENT"
      ],
      "has_independent_verification": true,
      "self_only": false,
      "independence_class": "INDEPENDENT"
    },
    {
      "event_id": "evt-prepilot-r4",
      "agent_version": "1.0.0",
      "task_type": "RESEARCH",
      "action_type": "EXECUTE",
      "result_status": "SUCCESS",
      "failure_category": "NOT_APPLICABLE",
      "occurred_at": "2026-08-04T20:32:03.577949+00:00",
      "verification_status": "VERIFIED",
      "evidence_availability": [
        "AVAILABLE"
      ],
      "verifier_classes": [
        "INDEPENDENT_AGENT"
      ],
      "has_independent_verification": true,
      "self_only": false,
      "independence_class": "INDEPENDENT"
    },
    {
      "event_id": "evt-prepilot-008",
      "agent_version": "1.0.0",
      "task_type": "RESEARCH",
      "action_type": "EXECUTE",
      "result_status": "SUCCESS",
      "failure_category": "NOT_APPLICABLE",
      "occurred_at": "2026-08-05T04:56:00+08:00",
      "verification_status": "VERIFIED",
      "evidence_availability": [
        "AVAILABLE"
      ],
      "verifier_classes": [
        "INDEPENDENT_AGENT"
      ],
      "has_independent_verification": true,
      "self_only": false,
      "independence_class": "INDEPENDENT"
    },
    {
      "event_id": "evt-prepilot-019",
      "agent_version": "1.0.0",
      "task_type": "RESEARCH",
      "action_type": "EXECUTE",
      "result_status": "SUCCESS",
      "failure_category": "NOT_APPLICABLE",
      "occurred_at": "2026-08-05T06:13:00+08:00",
      "verification_status": "VERIFIED",
      "evidence_availability": [
        "AVAILABLE"
      ],
      "verifier_classes": [
        "INDEPENDENT_AGENT"
      ],
      "has_independent_verification": true,
      "self_only": false,
      "independence_class": "INDEPENDENT"
    }
  ],
  "count": 5
}
```

Returned event ids: `['evt-prepilot-004', 'evt-prepilot-008', 'evt-prepilot-019', 'evt-prepilot-r3', 'evt-prepilot-r4']` -> all 3 original
round-1 v1.0.0 events (evt-prepilot-004, evt-prepilot-008, evt-prepilot-019) are intact and unmodified;
the scope additionally contains exactly the phase-2 R3/R4 real tasks executed by
researcher-gamma@1.0.0 (evt-prepilot-r3, evt-prepilot-r4), appended without altering
round-1 records.

## Query 3: subject-level summary, no version filter (`q-p2-isosubject`)
params: `{"identity_ref": "researcher-gamma"}`

```
{
  "agent_identity_ref": "researcher-gamma",
  "identity_continuity": "FAIL_CLOSED_PER_VERSION_COUNTS_ONLY",
  "by_version": {
    "1.0.0": {
      "total_events": 5,
      "verified_events": 5,
      "independently_verified_events": 5,
      "self_verified_events": 0,
      "partially_verified_events": 0,
      "not_assessed_events": 0,
      "conflicted_events": 0,
      "events_by_task_type": {
        "RESEARCH": 5
      },
      "events_by_result_status": {
        "SUCCESS": 5
      }
    },
    "1.1.0": {
      "total_events": 1,
      "verified_events": 1,
      "independently_verified_events": 1,
      "self_verified_events": 0,
      "partially_verified_events": 0,
      "not_assessed_events": 0,
      "conflicted_events": 0,
      "events_by_task_type": {
        "RESEARCH": 1
      },
      "events_by_result_status": {
        "SUCCESS": 1
      }
    }
  },
  "withheld_events": 0,
  "note": "Raw counts only. No derived ratios, scores or rankings (AHRP Constitution Section 9 non-goals). verified_events counts independently verified events only."
}
```

Version grouping: `{"1.0.0": 5, "1.1.0": 1}`
-> versions 1.0.0 and 1.1.0 are reported as SEPARATE per-version count
groups (`identity_continuity=FAIL_CLOSED_PER_VERSION_COUNTS_ONLY`); no
cross-version merge is expressible through the frozen summary API.

## Result
VERSION ISOLATION PASS: new version starts cold (only its own event),
old version history intact, subject-level output groups by version.
