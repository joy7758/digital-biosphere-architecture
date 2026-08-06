# Phase-2 Cold-Start Re-Verification Cases

Control: CONTROLLED_INTERNAL_PREPILOT=true, CONTROLLED_INTERNAL_TASK=true,
REAL_EXTERNAL_AGENT=false, SYNTHETIC_MARKET_ADOPTION=false,
REAL_WORLD_ADOPTION_VALIDATED=false. All timestamps are real UTC from the
phase-2 run.

Semantics under test: `NO_RECORD` (Q_NO_RECORD) is interpreted as
UNKNOWN / COLD_START. It is NEITHER "safe" NOR "dangerous": the orchestrator
withholds high-risk dispatch and permits only low-risk, reversible, sandboxed
exploration with limited permissions (frozen Rule D).

## Case 1: worker-nu@1.0.0 (agent+version never seen)
Query `q-p2-cs1` -> `summary`:

```
{
  "ok": true,
  "protocol": "AHRP",
  "schema_version": "0.1.0",
  "content_channel": {
    "structured_facts": "payload fields not listed in restricted_text",
    "restricted_text": []
  },
  "selective_disclosure": {
    "mode": "summary",
    "withheld_count": 0
  },
  "null_semantics": "NO_RECORD",
  "result": {
    "agent_identity_ref": "worker-nu",
    "total_events": 0,
    "verified_events": 0,
    "withheld_events": 0
  }
}
```

- `null_semantics`: `NO_RECORD` -> UNKNOWN/COLD_START.
- Orchestrator decision `dec-p2-cs1`: NO high-risk dispatch; low-risk
  reversible sandboxed exploration only (Rule D constraints: reversible,
  sandboxed, limited_permissions).
- The exploration task then produced worker-nu's FIRST event
  `evt-prepilot-p2-nu-exploration` (SUCCESS, independently verified by `ver-prepilot-p2-nu-exploration`),
  giving the agent a real starting history instead of an inherited one.

## Case 2: researcher-gamma@1.1.0 (queried BEFORE its event existed)
Query `q-p2-cs2` executed strictly before any 1.1.0 record was ingested
(ordering is part of the test):

```
{
  "ok": true,
  "protocol": "AHRP",
  "schema_version": "0.1.0",
  "content_channel": {
    "structured_facts": "payload fields not listed in restricted_text",
    "restricted_text": []
  },
  "selective_disclosure": {
    "mode": "summary",
    "withheld_count": 0
  },
  "null_semantics": "NO_RECORD",
  "result": {
    "agent_identity_ref": "researcher-gamma",
    "agent_version": "1.1.0",
    "total_events": 0,
    "verified_events": 0,
    "withheld_events": 0,
    "by_version": {}
  }
}
```

- `null_semantics`: `NO_RECORD` -> UNKNOWN/COLD_START,
  even though researcher-gamma v1.0.0 has 3 verified historical events:
  version identity continuity is fail-closed, history is NOT inherited.
- Orchestrator decision `dec-p2-cs2`: high-risk withheld; only the low-risk
  version-change test task was dispatched (event `evt-prepilot-p2-gamma110`, SUCCESS).

## Result
COLD-START PASS (2/2 cases): NO_RECORD never read as "safe", high-risk
withheld in both cases, and exploration/low-risk tasks generated the agents'
first events.
