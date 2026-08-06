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
entirely from the authoritative Git baseline; no sandbox artifacts were
used. A subsequent trust-boundary review of the first method-v2 revision
required fail-closed dispatch semantics; this report describes the
corrected run.

## 2. What was exercised

- **Unmodified AHRP v0.1** Validator and Query Engine. The `AHRP/` tree is
  byte-identical to `origin/main` (verified via
  `git diff --quiet <base> -- AHRP` and tree-hash comparison).
- Real `HistoryStore.ingest_event` / `ingest_verification` / `query_events`
  with correct envelope discipline (`ok` → `error` → `null_semantics` →
  `result.events`); no top-level envelope iteration.
- Three-state null semantics with fail-closed dispatch: `NO_RECORD` means
  UNKNOWN/COLD_START, `WITHHELD` means RECORD_EXISTS_BUT_NOT_DISCLOSED,
  query errors mean QUERY_ERROR; none of the three is ever treated as
  CLEAN/SAFE/TRUSTED and none permits dispatch of the affected agent.
- Independent-verification filtering
  (`require_independent_verification=True`, SELF never counts), disclosure
  fail-closed behavior, and query-error fail-closed handling
  (`task-m2-032` injects a controlled `Q_INVALID_ENUM` at HIGH risk).
- Two-phase shadow protocol with fsync-durable pre-query commitments,
  hash binding, monotonic sequences, temporal-order verification, and
  disposition consistency.
- Per-execution evidence files with recomputed SHA-256 references.
- Verification independence: the runner writes ONLY unverified events;
  a separate post-run SYSTEM_BENCHMARK verifier recomputes every result.

## 3. Design summary

| Aspect | Value |
|---|---|
| Agents | 3 synthetic workers (`worker-alpha/beta/gamma@1.0.0`) |
| Tasks | 32 controlled synthetic tasks, 6 task types + 1 controlled invalid `task_type` for query-error injection |
| Arm allocation | fixed parity of `sequence` (odd → No-AHRP, even → AHRP), decided before any result exists; 16 tasks per arm |
| Execution model | deterministic pure function; arm-blind and decision-blind (test-enforced) |
| Dispatch semantics | experiment-layer `DispatchDecision`: DISPATCH / LOW_RISK_EXPLORATION / BLOCK / MANUAL_REVIEW; alternatives dispatchable only when `OK` and non-vetoed (`KNOWN_NON_VETOED_ALTERNATIVE`) |
| History seed | 9 synthetic validator-checked events, 8 verifications, real evidence files, 1 WITHHELD, 1 SELF-only |
| Capability matrix | SHA-256 committed before the run; runner fails closed on mismatch |
| Forbidden fields | `expected_outcome`, `forced_result`, `desired_result` rejected at load time |

Full protocol: `EXPERIMENT_PROTOCOL.md`. Limitations:
`analysis/limitations.md`.

## 4. Results (recomputed from raw JSONL)

### Task flow (honest accounting)

| Metric | Value |
|---|---|
| submitted_tasks | 32 |
| dispatched_tasks | 22 |
| low_risk_exploration_tasks | 2 |
| blocked_tasks | 6 |
| manual_review_tasks | 2 |
| executed_tasks | 24 (= dispatched + exploration) |
| Experience Event count | 24 |
| Verification Record count | 24 (all SYSTEM_BENCHMARK post-run) |
| non-dispatched records | 8 (recorded in `data/non-dispatched-tasks.jsonl`) |

Blocked and manual-review tasks were never executed and produced no
execution evidence, no Experience Event, and no Verification Record. They
are reported as non-dispatched, never disguised as FAILURE or CANCELLED.

### No-AHRP arm (16 tasks, all dispatched by the naive procedure)

| Metric | Value |
|---|---|
| SUCCESS / FAILURE / TIMEOUT / CANCELLED | 9 / 4 / 2 / 1 |
| Avg decision time | 0.000969 ms |
| Human overrides | 0 (controlled run, counted honestly) |
| Repeat selection of known failure-boundary agent | 5 |

### AHRP-assisted arm (16 tasks, fail-closed dispatch)

| Metric | Value |
|---|---|
| Dispositions | DISPATCH 6, LOW_RISK_EXPLORATION 2, BLOCK 6, MANUAL_REVIEW 2 |
| Executed result distribution (8 executed) | SUCCESS 2, FAILURE 6 |
| Avg decision time | 0.251875 ms |
| Human overrides | 0 |
| Repeat selection of known failure-boundary agent | 0 |
| Query count | 52 (Summary 16, SummaryList 36, Detail 0) |
| NO_RECORD / WITHHELD / disclosure-denial / query-error | 13 / 8 / 8 / 3 |
| Decision changes vs pre-query commitment | 13 |
| Supporting event references | 10 |
| Query characters / token estimate | 37,958 / 9,505 (`ceil(chars/4)`) |
| Latency p50 / p95 | 0.008771 ms / 0.017954 ms |

The two arms intentionally executed DIFFERENT task subsets: the AHRP arm
declined to execute 8 of its 16 tasks (6 BLOCK, 2 MANUAL_REVIEW) because
no candidate was known to be safe. Arm result distributions are therefore
not comparable and are not compared.

### Decision changes (all thirteen)

| Task | Outcome | Reason | Supporting events | Execution |
|---|---|---|---|---|
| task-m2-002 | DISPATCH | KNOWN_NON_VETOED_ALTERNATIVE_AFTER_INITIAL_WITHHELD | 1 | FAILURE |
| task-m2-004 | BLOCK | RULE_B_POLICY_RESTRICTION_BLOCK:NO_KNOWN_ALTERNATIVE | 1 | NOT_EXECUTED |
| task-m2-006 | MANUAL_REVIEW | NO_RECORD, no human approver available | 0 | NOT_EXECUTED |
| task-m2-008 | DISPATCH | KNOWN_NON_VETOED_ALTERNATIVE_AFTER_INITIAL_NO_RECORD | 1 | FAILURE |
| task-m2-010 | DISPATCH | RULE_A_CAPABILITY_LIMIT_VETO:KNOWN_NON_VETOED_ALTERNATIVE | 3 | FAILURE |
| task-m2-014 | BLOCK | WITHHELD + SANDBOX_FLAGS_INCOMPLETE | 0 | NOT_EXECUTED |
| task-m2-018 | BLOCK | NO_RECORD:UNKNOWN | 0 | NOT_EXECUTED |
| task-m2-020 | DISPATCH | RULE_A_CAPABILITY_LIMIT_VETO:KNOWN_NON_VETOED_ALTERNATIVE | 3 | FAILURE |
| task-m2-022 | BLOCK | NO_RECORD:UNKNOWN | 0 | NOT_EXECUTED |
| task-m2-024 | MANUAL_REVIEW | NO_RECORD, no human approver available | 0 | NOT_EXECUTED |
| task-m2-026 | DISPATCH | KNOWN_NON_VETOED_ALTERNATIVE_AFTER_INITIAL_WITHHELD | 1 | FAILURE |
| task-m2-028 | BLOCK | NO_RECORD + SANDBOX_FLAGS_INCOMPLETE | 0 | NOT_EXECUTED |
| task-m2-032 | BLOCK | QUERY_ERROR:Q_INVALID_ENUM (controlled injection) | 0 | NOT_EXECUTED |

Section-9 regression cases: `task-m2-004` (HIGH, POLICY_RESTRICTION veto,
no known alternative) is BLOCK — the deprecated
`ALTERNATIVE_NO_RECORD_CLEAN` path no longer exists anywhere in code or
data. `task-m2-026` (HIGH, initial WITHHELD) never kept the withheld
agent; it dispatched the known, disclosed, non-vetoed candidate.
`task-m2-032` (HIGH, injected query error) is BLOCK with zero worker
invocations. **No outcome rewriting of any kind exists in this
codebase.**

## 5. Integrity verification

| Check | Result |
|---|---|
| `validate_shadow_protocol.py` | PASS — 16 pre + 16 post records, hashes recompute, temporal order holds, disposition consistency holds, tamper self-test passed |
| `verify_evidence_references.py` | PASS — 33 references (9 seed + 24 run), 33 distinct hashes, zero placeholders |
| `verify_run_records.py` (SYSTEM_BENCHMARK) | PASS — 24 events recomputed against the deterministic worker, 24 verifications; result/agent/matrix-hash/evidence-hash comparisons all agree |
| Generated-object validation | PASS — 24 events and 24 verifications pass the real AHRP Validator; complete event/verification binding (`subject_event_id`, `agent_ref`, `agent_version`, `covered_aspect`) (`analysis/generated-object-validation.json`) |
| method-v2 independent tests | `Ran 35 tests` / `OK` (20 original + 15 trust-boundary regressions) |
| AHRP v0.1 test suite | `Ran 208 tests` / `OK` |
| AHRP demo | exit 0 |
| `build_evidence_package.py` | PACKAGE_BUILT — 10-step pipeline, unified MANIFEST.sha256 covering every packaged file except itself |
| `verify_evidence_package.py` | PASS — clean unpack (traversal/symlink refusal), manifest integrity, 62 JSON/JSONL files parsed, 24/24 schema + binding, evidence references, shadow protocol, truth boundary |

## 6. Interpretation

Observed associations, and nothing more:

- `AHRP_HISTORY_WAS_USED` — every AHRP-arm decision passed through real
  HistoryStore queries against validator-checked, evidence-backed records.
- `AHRP_ASSOCIATED_WITH_DIFFERENT_DECISION` — 13 of 16 AHRP-arm decisions
  differed from the pre-query commitment; every dispatch-level change is
  bound to disclosed, independently verified seed events, and every
  unknown-state case failed closed (BLOCK or MANUAL_REVIEW).

Repeat-selection observation, strictly scoped:

```text
ROUTING_POLICY_CONFORMANCE_OBSERVATION
repeat_selection_of_known_failure_boundary_agent: No-AHRP 5, AHRP 0
```

> This metric is mechanically related to the configured veto policy.
> It is not independent evidence of improved real-world outcomes.

It is not reported as `AHRP_VALUE_IMPROVEMENT`, `RELIABILITY_IMPROVEMENT`,
or `FAILURE_PREVENTED`.

Not observed, and not observable by this design:

- `AHRP_PROVED_TO_IMPROVE_SUCCESS_RATE` — forbidden; the worker is
  deterministic and the arms executed different task subsets.
- `FAILURE_PREVENTED` — forbidden; blocked tasks were never executed, so
  no outcome exists for them at all.

## 7. Truth boundary (final)

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

```text
EXPERIMENT_RESULT=INCONCLUSIVE
```

With 32 synthetic tasks, three synthetic agents, a deterministic
execution model, and system-level post-run recomputation instead of real
independent verification, no stronger conclusion is available. Any future
claim of readiness requires real agents, real accumulated history, and
external review.
