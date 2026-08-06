# AHRP Pilot-Readiness Experiment — method-v2 (clean-room rebuild)

```text
CLEAN_ROOM_REDEVELOPMENT=true
SANDBOX_ARTIFACT_DEPENDENCY=false
METHOD_V2=EXPERIMENT_METHOD_SECOND_VERSION   # NOT AHRP protocol v0.2
AHRP_V0_1_MODIFIED=false
EXPERIMENT_RESULT=INCONCLUSIVE
```

This experiment is the clean-room replacement for the invalidated PR #12
experiment (archived at
`../historical-invalidated/ahrp-pilot-readiness-v0.1-pr12/`, see its
`INVALIDATED.md` and `docs/review/PR-012-post-merge-integrity-audit.md`).

## What this experiment can and cannot show

- It exercises the **unmodified AHRP v0.1** Validator and Query Engine
  (`AHRP/` is byte-identical to `origin/main`) over a synthetic roster of
  three agents and 32 controlled synthetic tasks.
- It measures protocol mechanics: envelope handling, three-state null
  semantics, fail-closed dispatch (NO_RECORD / WITHHELD / QUERY_ERROR are
  UNKNOWN and never dispatchable), disclosure fail-closed behavior,
  two-phase shadow-protocol integrity, evidence-hash referential
  integrity, post-run recomputation verification, and operational
  overhead.
- It does **not** measure real agents, real adoption, or production value.

## Layout

| Path | Role |
|---|---|
| `config/capability-matrix.json` + `.commitment` | frozen capability matrix, SHA-256 committed pre-run |
| `config/tasks.jsonl` | 32 controlled tasks (no result fields of any kind; LOW-risk sandbox flags are experiment-only) |
| `config/history-events.jsonl`, `history-verifications.jsonl` | synthetic seed history (validator-checked, evidence-backed) |
| `worker.py` | deterministic execution model (pure function) |
| `history_loader.py` | HistoryStore loading + correct envelope parsing |
| `run_experiment.py` | two-arm runner; fail-closed `DispatchDecision` (DISPATCH / LOW_RISK_EXPLORATION / BLOCK / MANUAL_REVIEW); writes ONLY unverified events |
| `verify_run_records.py` | separate post-run SYSTEM_BENCHMARK verifier: recomputes results, re-checks hashes, validates objects through the AHRP Validator |
| `validate_shadow_protocol.py` | shadow-protocol integrity validator (incl. tamper self-test) |
| `verify_evidence_references.py` | evidence hash referential-integrity verifier |
| `analyze_experiment.py` | metrics recomputed from raw JSONL only |
| `build_evidence_package.py` | 10-step pipeline producing the unified evidence ZIP |
| `verify_evidence_package.py` | clean-unpack re-verification of the ZIP |
| `tests/` | 35 independent enumerable tests |
| `data/`, `evidence/`, `analysis/` | generated raw records (incl. `non-dispatched-tasks.jsonl`), evidence files, metrics |

## Reproduce

```bash
python3 run_experiment.py
python3 verify_run_records.py
python3 validate_shadow_protocol.py
python3 verify_evidence_references.py
python3 analyze_experiment.py
python3 -m unittest discover -s tests -v     # Ran 35 tests / OK
python3 build_evidence_package.py            # full pipeline + ZIP
python3 verify_evidence_package.py           # clean-unpack re-verification
```

## Truth boundary

```text
CONTROLLED_INTERNAL_EXPERIMENT=true
SYNTHETIC_AGENT_ROSTER=true
REAL_EXTERNAL_AGENT=false
REAL_WORLD_ADOPTION_VALIDATED=false
AHRP_PRODUCTION_READY=false
AHRP_STANDARD_PUBLISHED=false
NETWORK_SERVICE_RECOMMENDATION=DEFER
PR12_EXPERIMENT_RESULT=INVALIDATED
CLEANROOM_EXPERIMENT_RESULT=INCONCLUSIVE
REAL_INDEPENDENT_VERIFICATION=false
SYNTHETIC_SYSTEM_VERIFICATION=true
POST_RUN_RECOMPUTATION_VERIFIED=true
```

Allowed claims: `AHRP_HISTORY_WAS_USED`,
`AHRP_ASSOCIATED_WITH_DIFFERENT_DECISION`.
Forbidden claims: `AHRP_PROVED_TO_IMPROVE_SUCCESS_RATE`, `FAILURE_PREVENTED`.
