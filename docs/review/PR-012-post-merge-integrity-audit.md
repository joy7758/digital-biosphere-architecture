# PR-012 Post-Merge Integrity Audit

```text
AUDIT_TARGET=PR #12 (commit 06126fffaaf3072b91ed211fa88ba9d202025003)
AUDIT_TYPE=POST_MERGE_INTEGRITY_AUDIT
MERGE_MODE=USER_MANUAL_MERGE
HISTORY_REWRITE=false
PR12_EXPERIMENT_RESULT=INVALIDATED
```

## 1. Governance facts

- PR #12 was merged **manually by the user**, not by an automated pipeline and
  not by an AI agent. This audit does not attribute blame; it records
  consequences and remediation.
- This remediation **does not rewrite Git history**. `origin/main` keeps
  commit `06126ff` exactly as merged. All fixes are additive commits on a
  review branch (`fix/ahrp-pr12-cleanroom-redevelopment`) delivered as a
  Draft PR for independent review.
- What is invalidated is **the experiment result shipped by PR #12**
  (`experiments/ahrp-pilot-readiness-v0.1`), **not** the AHRP v0.1 core
  implementation. The AHRP tree (`AHRP/`) is byte-identical before and after
  this remediation (verified by tree-hash comparison in the remediation
  branch).

## 2. What PR #12 deleted (now restored)

Restored verbatim from pre-PR12 baseline `fbc08a3890de5ce1a891e8f55d98067568654cbd`:

| Asset | Restored path |
|---|---|
| Controlled pre-pilot v0.1 | `experiments/ahrp-prepilot-v0.1/` |
| Pre-pilot evidence ZIP | `experiments/ahrp-prepilot-v0.1-evidence.zip` |
| r2 evidence ZIP (`sha256 9f47fbe3…`) | `experiments/AHRP-v0.1-controlled-prepilot-evidence-r2.zip` |
| Recycle-bin governance records | `回收站/` |
| README SAEE ecosystem note | `README.md` (deleted block only) |

## 3. What PR #12 shipped that is now invalidated

`experiments/ahrp-pilot-readiness-v0.1/` — archived to
`experiments/historical-invalidated/ahrp-pilot-readiness-v0.1-pr12/` with an
`INVALIDATED.md` recording eight code-confirmed defects:

1. `tasks.jsonl` predetermines results via `expected_outcome`;
2. the runner treats the preset outcome as the execution result;
3. `decision_changed` rewrites FAILURE/TIMEOUT into SUCCESS in the
   AHRP-assisted arm;
4. the `HistoryStore` envelope is iterated incorrectly (top-level keys
   instead of `result.events`), so no history was ever actually read;
5. hard-coded branches force decision changes regardless of evidence;
6. latency / token / integrity metrics are fixed constants, never measured;
7. every evidence reference shares one placeholder hash pointing at nothing;
8. therefore the arm comparison has **no evidentiary value**.

```text
NON_EVIDENTIARY_SIMULATION_OUTPUT=true
```

## 4. What is explicitly NOT changed

```text
AHRP_V0_1_SCHEMA_MODIFIED=false
AHRP_V0_1_SPEC_MODIFIED=false
AHRP_V0_1_VALIDATOR_MODIFIED=false
AHRP_V0_1_QUERY_ENGINE_MODIFIED=false
AHRP_PROTOCOL_V0_2_ENTERED=false
NETWORK_QUERY_SERVICE_DEVELOPED=false
```

The 208 AHRP unit tests continue to pass unmodified on the remediation branch.

## 5. Truth boundaries after remediation

```text
PR12_EXPERIMENT_RESULT=INVALIDATED
CLEANROOM_EXPERIMENT_RESULT=INCONCLUSIVE
NETWORK_SERVICE_RECOMMENDATION=DEFER
REAL_WORLD_ADOPTION_VALIDATED=false
AHRP_PRODUCTION_READY=false
AHRP_STANDARD_PUBLISHED=false
```

## 6. Remediation deliverables

- Commit `fix(governance): restore assets deleted by PR12`;
- Commit `docs(audit): invalidate PR12 experiment evidence` (this document);
- Commit `experiment(ahrp): rebuild trustworthy pilot-readiness methodology`
  → `experiments/ahrp-pilot-readiness-method-v2/` (clean-room rebuild;
  "method-v2" denotes the second version of the *experiment method*, not
  AHRP protocol v0.2).

The replacement experiment declares only what its controlled synthetic design
supports: `AHRP_HISTORY_WAS_USED` and, where observed,
`AHRP_ASSOCIATED_WITH_DIFFERENT_DECISION`. It never claims
`AHRP_PROVED_TO_IMPROVE_SUCCESS_RATE` or `FAILURE_PREVENTED`.

## 7. Next gate

Draft PR only. Independent review and explicit human approval are required
before any merge. No auto-merge.
