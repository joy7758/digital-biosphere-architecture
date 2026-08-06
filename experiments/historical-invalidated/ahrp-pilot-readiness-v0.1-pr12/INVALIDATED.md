# INVALIDATED — ahrp-pilot-readiness-v0.1 (PR #12)

```text
PR12_EXPERIMENT_RESULT=INVALIDATED
NON_EVIDENTIARY_SIMULATION_OUTPUT=true
AHRP_V0_1_CORE_IMPLEMENTATION_AFFECTED=false
```

This directory is the archived, **invalidated** experiment originally merged by
PR #12 (commit `06126ff`). It is preserved only as a non-evidentiary historical
record. Its numbers MUST NOT be cited as evidence for or against AHRP.

The defects below were re-confirmed directly against the archived source code
in this directory (line numbers refer to `run_experiment.py` as archived).

## Confirmed defects

1. **`tasks.jsonl` uses `expected_outcome`.**
   All 30 task lines carry an `expected_outcome` field (`SUCCESS` /
   `FAILURE` / `TIMEOUT`). The task file predetermines results instead of
   describing requirements.

2. **`run_experiment.py` treats the preset outcome as the execution result.**
   Lines 158 and 206: `outcome = task["expected_outcome"]`. No worker, no
   capability model, no controlled execution exists; the "result" is read from
   the task definition in both arms.

3. **FAILURE / TIMEOUT rewritten to SUCCESS after a decision change.**
   Lines 207–208:
   `if query_result["decision_changed"] and outcome in ["FAILURE", "TIMEOUT"]: outcome = "SUCCESS"`.
   The AHRP-assisted arm's outcome is manufactured from `decision_changed`,
   not from any execution. This is the core fabrication.

4. **Wrong `HistoryStore` envelope handling.**
   Line 88 calls `engine.query_events(...)` which returns an envelope
   (`ok` / `null_semantics` / `result.events`), but lines 94–97 iterate the
   envelope itself (`for evt in events_raw`, with `if isinstance(evt, str):
   break`), so the loop walks envelope *keys* and never reaches any event.
   `ok`, `error`, and `null_semantics` are never checked.

5. **Hard-coded branches force decision changes.**
   Lines 114–118: explicit comments and branches ("Forcing decision change on
   specific combinations just to ensure it triggers exactly once") force
   `decision_changed=true` for fixed agent/task combinations regardless of
   history content.

6. **Fixed constants for latency / token / integrity metrics.**
   Lines 236–255: `shadow-protocol-integrity.json` is hard-coded to
   `"status": "PASS"` without any check; `operational-overhead.json` is
   hard-coded to `avg_query_time_ms: 125` and `avg_token_overhead: 305`.
   Nothing is measured.

7. **Repeated placeholder evidence hash.**
   Lines 37, 52, 230: every evidence reference uses the same placeholder
   `sha256:abcdabcd…abcd`. No evidence file exists anywhere; nothing is
   addressable or recomputable.

8. **No evidentiary value.**
   Because outcomes are predetermined, rewritten from `decision_changed`, and
   backed by placeholder hashes, the reported arm comparison proves nothing
   about AHRP. The historical report's numbers are a property of the script,
   not of the protocol.

## Status

```text
VERDICT_HISTORY=INVALIDATED
RETENTION=NON_EVIDENTIARY_HISTORICAL_RECORD
NO_HISTORY_REWRITE=true
AHRP_V0_1_SCHEMA_SPEC_VALIDATOR_QUERY_UNCHANGED=true
```

What is invalidated is the **experiment result**, not the AHRP v0.1 core
implementation (Schema / Spec / Validator / Query Engine), which remains
untouched on `main` and passes its 208 unit tests.

Replacement: `experiments/ahrp-pilot-readiness-method-v2/` (clean-room
redevelopment, method second version — not AHRP protocol v0.2).
