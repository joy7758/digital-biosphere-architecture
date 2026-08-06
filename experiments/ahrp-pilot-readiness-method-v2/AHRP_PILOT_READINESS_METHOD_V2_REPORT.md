# AHRP Pilot-Readiness Experiment — method-v2 Report

```text
CLEAN_ROOM_REDEVELOPMENT=true
SANDBOX_ARTIFACT_DEPENDENCY=false
METHOD_V2=EXPERIMENT_METHOD_SECOND_VERSION   # NOT AHRP protocol v0.2
AHRP_V0_1_MODIFIED=false
EXPERIMENT_RESULT=INCONCLUSIVE
NETWORK_SERVICE_RECOMMENDATION=DEFER
```

## 1. Background

The PR #12 experiment (`experiments/ahrp-pilot-readiness-v0.1/`) was found
to be non-evidentiary: tasks predetermined their own results via
`expected_outcome`, execution results were copied from that preset, and
FAILURE/TIMEOUT outcomes were rewritten to SUCCESS whenever
`decision_changed` was true. Full defect enumeration is recorded in
`../historical-invalidated/ahrp-pilot-readiness-v0.1-pr12/INVALIDATED.md`
and `../../docs/review/PR-012-post-merge-integrity-audit.md`.

```text
PR12_EXPERIMENT_RESULT=INVALIDATED
NON_EVIDENTIARY_SIMULATION_OUTPUT=true
```

This experiment (method-v2) is the clean-room replacement. It was developed
entirely from the authoritative Git baseline; no sandbox artifacts were used.

## 2. What was exercised

- **Unmodified AHRP v0.1** Validator and Query Engine. The `AHRP/` tree is
  byte-identical to `origin/main` (verified via
  `git diff --quiet <base> -- AHRP` and tree-hash comparison).
- Real `HistoryStore.ingest_event` / `ingest_verification` / `query_events`
  with correct envelope discipline (`ok` → `error` → `null_semantics` →
  `result.events`); no top-level envelope iteration.
- Three-state null semantics (`NONE` / `NO_RECORD` / `WITHHELD`),
  independent-verification filtering (`require_independent_verification=True`,
  SELF never counts), disclosure fail-closed behavior, and query-error
  fail-closed handling.
- Two-phase shadow protocol with fsync-durable pre-query commitments,
  hash binding, monotonic sequences, and temporal-order verification.
- Per-execution evidence files with recomputed SHA-256 references.

## 3. Design summary

| Aspect | Value |
|---|---|
| Agents | 3 synthetic workers (`worker-alpha/beta/gamma@1.0.0`) |
| Tasks | 30 controlled synthetic tasks, 6 task types |
| Arm allocation | fixed parity of `sequence` (odd → No-AHRP, even → AHRP), decided before any result exists |
| Execution model | deterministic pure function; arm-blind and decision-blind (test-enforced) |
| History seed | 7 synthetic validator-checked events, 6 verifications, real evidence files, 1 WITHHELD, 1 SELF-only |
| Capability matrix | SHA-256 committed before the run; runner fails closed on mismatch |
| Forbidden fields | `expected_outcome`, `forced_result`, `desired_result` rejected at load time |

Full protocol: `EXPERIMENT_PROTOCOL.md`. Limitations:
`analysis/limitations.md`.

## 4. Results (recomputed from raw JSONL)

### No-AHRP arm (15 tasks)

| Metric | Value |
|---|---|
| SUCCESS / FAILURE / TIMEOUT / CANCELLED | 8 / 4 / 2 / 1 |
| Avg decision time | 0.000194 ms |
| Human overrides | 0 (controlled run, counted honestly) |
| Repeat selection of known failure-boundary agent | **5** |

### AHRP-assisted arm (15 tasks)

| Metric | Value |
|---|---|
| SUCCESS / FAILURE / TIMEOUT / CANCELLED | 8 / 4 / 2 / 1 |
| Avg decision time | 0.197694 ms |
| Human overrides | 0 |
| Repeat selection of known failure-boundary agent | **0** |
| Query count | 34 (Summary 15, SummaryList 19, Detail 0) |
| NO_RECORD / WITHHELD / disclosure-denial / query-error | 11 / 5 / 5 / 0 |
| Decision changes | **3** |
| Supporting event references | 5 |
| Query characters / token estimate | 24,776 / 6,208 (`ceil(chars/4)`) |
| Latency p50 / p95 | 0.008084 ms / 0.024551 ms |

### Decision changes (all three)

| Task | Rule | Supporting events | Execution result |
|---|---|---|---|
| task-m2-004 | RULE_B_POLICY_RESTRICTION_BLOCK | evt-seed-beta-analysis-001 | SUCCESS |
| task-m2-010 | RULE_A_CAPABILITY_LIMIT_VETO | evt-seed-alpha-coding-001, -002 | FAILURE |
| task-m2-020 | RULE_A_CAPABILITY_LIMIT_VETO | evt-seed-alpha-coding-001, -002 | FAILURE |

Two changed decisions still executed as FAILURE: the alternative agent
failed on its own boundary. **No outcome rewriting of any kind exists in
this codebase**; the result distribution is identical across arms.

## 5. Integrity verification

| Check | Result |
|---|---|
| `validate_shadow_protocol.py` | PASS — 15 pre + 15 post records, hashes recompute, temporal order holds, tamper self-test passed |
| `verify_evidence_references.py` | PASS — 37 references (7 seed + 30 run), 37 distinct hashes, zero placeholders |
| method-v2 independent tests | `Ran 20 tests` / `OK` |
| AHRP v0.1 test suite | `Ran 208 tests` / `OK` |
| AHRP demo | exit 0 |

## 6. Interpretation

Observed associations, and nothing more:

- `AHRP_HISTORY_WAS_USED` — every AHRP-arm decision passed through real
  HistoryStore queries against validator-checked, evidence-backed records.
- `AHRP_ASSOCIATED_WITH_DIFFERENT_DECISION` — 3 of 15 AHRP-arm selections
  differed from the pre-query commitment, each bound to disclosed,
  independently verified seed events; the AHRP arm made zero repeat
  selections of agents with known failure boundaries versus five in the
  No-AHRP arm.

Not observed, and not observable by this design:

- `AHRP_PROVED_TO_IMPROVE_SUCCESS_RATE` — forbidden; distributions are
  identical by construction of the deterministic worker.
- `FAILURE_PREVENTED` — forbidden; the two vetoed re-routings still failed.

## 7. Truth boundary (final)

```text
CONTROLLED_INTERNAL_EXPERIMENT=true
SYNTHETIC_AGENT_ROSTER=true
REAL_EXTERNAL_AGENT=false
REAL_WORLD_ADOPTION_VALIDATED=false
AHRP_PRODUCTION_READY=false
AHRP_STANDARD_PUBLISHED=false
NETWORK_SERVICE_RECOMMENDATION=DEFER
```

```text
EXPERIMENT_RESULT=INCONCLUSIVE
```

With 30 synthetic tasks, three synthetic agents, and a deterministic
execution model, no stronger conclusion is available. Any future claim of
readiness requires real agents, real accumulated history, and external
review.
