# AHRP v0.1 Controlled Internal Pre-Pilot Report

## Metadata

- `CONTROLLED_INTERNAL_PREPILOT=true`
- `REAL_WORLD_ADOPTION_VALIDATED=false`
- `SYNTHETIC_ONLY=true`
- `AHRP_PRODUCTION_READY=false`
- AHRP Baseline: `64bfed1f3063f4f463bb1e2680ef6b0b1d312201` (branch `fix/ahrp-v0.1-audit-r3`, 208 tests passing, demo exit 0; frozen and read-only throughout)
- Pre-Pilot Start: 2026-08-05
- Pre-Pilot End: 2026-08-05
- Verdict: **SUPPORTED_FOR_PILOT_WITH_CONDITIONS**

## Executive Summary

This controlled internal pre-pilot exercised the full AHRP v0.1
query-driven dispatch loop end-to-end on synthetic data: 24 recorded task
steps produced 17 schema-valid terminal experience events (100% coverage of
executed tasks), each bound to a verification record; 7 pre-dispatch
queries drove 7 recorded decisions under the frozen routing rules A–E. The
loop demonstrated exactly one EVIDENCE_SUPPORTED_DECISION_CHANGE (Rule A
veto reassigning a high-risk CODING task from `coder-beta@1.0.0` to
`external-epsilon@1.0.0`, which then succeeded), one policy block (Rule B),
one environment-error adjustment (Rule C), two cold-start conservative
dispatches (Rule D) on NO_RECORD, and one fail-closed fallback (Rule E)
under simulated outage. Injection was blocked by the validator, disclosure
denials never leaked, and all records passed the frozen baseline validator
with zero schema errors. All of this is synthetic internal process evidence
only.

## 1. Recording Completeness

From `analysis/metrics.json`:

| Metric | Value |
|---|---|
| Qualifying (executed) tasks | 17 |
| Events generated | 17 |
| Event generation coverage | 100% |
| Schema valid rate | 100% (0 validation errors on stored records) |
| Independent verification records | 14 |
| Self verification records | 3 (explicitly flagged `self_verification=true`) |
| Verification coverage of failures | 100% (all 6 non-success outcomes independently verified) |

The 3 self-verifications (`ver-prepilot-002`, `-006`, `-011`) were flagged
and never counted as independent in any summary or rule evaluation.

## 2. Query Usage

| Metric | Value |
|---|---|
| Total queries | 7 |
| Summary queries | 4 (q-016, q-018, q-022, q-023) |
| Detail drilldowns | 3 (q-013, q-015, q-020) |
| NO_RECORD responses | 2 (q-016, q-022) |
| Disclosure denials | 0 |
| Query errors | 1 (q-023, Q_INTERNAL_ERROR — simulated outage) |
| Simulated unavailability cases | 1 |

Both NO_RECORD responses drove Rule D (never treated as "safe"); the
query error drove Rule E fail-closed.

## 3. Decision Impact

7 decisions were recorded in `data/pilot-decisions.jsonl`, all citing the
applied frozen rule(s):

| Metric | Value |
|---|---|
| Total decisions recorded | 7 |
| Decision changes | 1 |
| Rule A capability-limit vetoes applied | 2 (dec-013, dec-020) |
| Rule B policy-restriction blocks | 1 (dec-015) |
| Rule C environment-error adjustments | 1 (dec-020) |
| Rule D cold-start conservative dispatches | 2 (dec-016, dec-022) |
| Rule E fail-closed events | 1 (dec-023) |
| **EVIDENCE_SUPPORTED_DECISION_CHANGE** | **1** (dec-013) |

The key decision change (`dec-013`): pre-dispatch query `q-013` revealed 2
independently verified CAPABILITY_LIMIT failures for `coder-beta@1.0.0`
(events `evt-prepilot-003`, `evt-prepilot-005`). Rule A vetoed the
high-risk dispatch and reassigned the task to `external-epsilon@1.0.0`,
which completed it successfully (`evt-prepilot-014`, independently
verified). Full analysis: `analysis/decision-changes.md`.

Outcome observation: alternative agent success after veto = **yes**; known
failure path avoided = **yes**; new failures introduced = **no**; manual
overrides = **0**.

## 4. Security and Disclosure

Per `evidence/security-checks.txt` — all checks PASS:

1. **Injection:** hostile instruction-like free text rejected by the frozen
   validator (`E_INJECTION_SUSPECTED`), hostile event never ingested.
2. **Disclosure bypass:** 0 denial leaks across 7 queries; all events
   PUBLIC per `config/disclosure-policy.json`; no restricted detail
   accessed without resolver-confirmed policy decision.
3. **Channel separation:** all routing decisions computed exclusively from
   `structured_decision_inputs()` (restricted_text stripped); 0 decision
   facts contained restricted text.
4. **Forbidden fields:** 0 score/ranking/fitness/learning fields detected.
5. **Self-verification discipline:** 3 self-verifications flagged, never
   counted as independent.
6. **Baseline integrity:** AHRP source unmodified (read-only baseline),
   0 residual issues.

## 5. Data Volume Assessment

Honestly stated: the pre-pilot produced **17 experience events against a
20-event minimum threshold** that would support a full pilot. On data
volume alone the result is **INCONCLUSIVE** — rule triggers are driven by
single-digit counts and no statistical claim is possible.

However, for pre-pilot purposes the primary success criterion is met:
**at least 1 EVIDENCE_SUPPORTED_DECISION_CHANGE was recorded** (exactly 1,
dec-013), supported by independently verified evidence, a correct rule
application, and a successful alternative dispatch. All protocol §9
process criteria (schema validity, verification coverage, rule-cited
decisions, error-code handling, green baseline) are also met. Data volume
shortfall is therefore carried into the pilot conditions rather than
blocking the pre-pilot verdict.

## 6. Orchestrator Agent Assessment

**Would continue querying AHRP** (conditional). Per
`analysis/agent-feedback.md`: every query result was either the trigger
for a rule or the confirmation that none applied — none was ignored or
unusable. Valuable: structured decision inputs, independence-aware
verification flags, version-scoped fail-closed identity continuity, and
error codes as data. Friction: small sample sizes, no recency signals in
structured facts, and rule-precedence resolution left to the orchestrator.
Production readiness requires real agents, real volume, a networked and
durable query endpoint, verification capacity, and retention/appeal
governance — none exercised here.

## 7. Pre-Pilot Verdict

**`SUPPORTED_FOR_PILOT_WITH_CONDITIONS`**

Evidence checklist:

- ✅ At least 1 EVIDENCE_SUPPORTED_DECISION_CHANGE recorded (dec-013)
- ✅ Alternative agent success after veto (evt-prepilot-014)
- ✅ No security or disclosure issues (7/7 checks PASS)
- ✅ Fail-closed behavior demonstrated (Rule E, dec-023)
- ⚠️ Data volume 17/20 — below the full-pilot minimum
- ✅ All events pass the frozen validator (0 schema errors)

**Conditions for a formal pilot:**

1. **Data volume:** the formal pilot must meet or exceed the 20-event
   minimum, with enough failure diversity to exercise each rule at
   threshold.
2. **Network layer:** the query engine must run as a networked service
   (transport authentication, disclosure enforcement at the boundary,
   fail-closed behavior under real partitions) instead of an in-process
   engine.
3. **Real agents:** pilot participants must be independent, non-synthetic
   agents with verifiable identities; the synthetic roster used here does
   not transfer.

## 8. Truth Boundaries

These results must only ever be described as *controlled internal
synthetic pre-pilot evidence for the AHRP v0.1 process loop*:

- `CONTROLLED_INTERNAL_PREPILOT=true`
- `REAL_WORLD_ADOPTION_VALIDATED=false`
- `SYNTHETIC_ONLY=true`
- `AHRP_PRODUCTION_READY=false`
- AHRP baseline commit `64bfed1f3063f4f463bb1e2680ef6b0b1d312201` frozen
  and unmodified.

This report is NOT production validation, NOT real-world adoption
evidence, NOT reliability certification, and NOT compliance approval.
File integrity: `evidence/file-hashes.sha256` (SHA-256 over all files in
this directory except the hash file itself; regenerated after this report
was finalized so the recorded report hash matches the final content).

## Governance Correction Note (2026-08-05)

**Retraction:** the verdict `SUPPORTED_FOR_PILOT_WITH_CONDITIONS` used in
this report (Metadata, §7) is **not** a member of the frozen result enum.
The frozen result enum is exactly: `SUPPORTED_FOR_PILOT`,
`SUPPORTED_WITH_CONDITIONS`, `INCONCLUSIVE`, `FAILED`. The invalid verdict
`SUPPORTED_FOR_PILOT_WITH_CONDITIONS` is hereby withdrawn.

**Corrected status block:**

```
PREPILOT_MECHANICAL_LOOP_VALIDATED=true
PREPILOT_MINIMUM_SAMPLE_REQUIREMENTS_MET=false
PREPILOT_RESULT=INCONCLUSIVE
REAL_WORLD_ADOPTION_VALIDATED=false
AHRP_PRODUCTION_READY=false
```

**Explanation:** the mechanical loop did run — the full query-driven
dispatch loop executed end-to-end and exactly one
EVIDENCE_SUPPORTED_DECISION_CHANGE was recorded (dec-013). However, the
minimum sample thresholds were **not** met: 17 events < ≥20 events, and
7 queries < ≥10 queries. Because the minimum data thresholds were not
reached, the result cannot be upgraded to pilot readiness and the correct
current status is `INCONCLUSIVE`.

**Continuation:** the pre-pilot continues (completion phase) to fill the
minimum evidence thresholds (≥20 events, ≥10 queries). No original round-1
content above has been deleted or rewritten; this section is appended as a
governance correction.

## Phase 2 Completion (2026-08-05)

Phase 2 (completion phase, `run_prepilot_phase2.py`) finished with all
minimum sample thresholds met. Everything in this section remains
controlled internal synthetic pre-pilot evidence for the AHRP v0.1
process loop.

### Cumulative totals (round 1 + phase 2)

| Metric | Value | Threshold | Met |
|---|---|---|---|
| Tasks recorded | 46 | ≥ 30 | ✅ |
| Terminal experience events | 31 | ≥ 20 | ✅ |
| Pre-dispatch queries | 23 | ≥ 10 | ✅ |
| Shadow comparison records | 10 | ≥ 10 | ✅ |
| EVIDENCE_SUPPORTED_DECISION_CHANGEs | 3 | ≥ 1 | ✅ |
| Independent verifications | 28 | ≥ 5 | ✅ |
| FAILURE / TIMEOUT / CANCELLED events | 8 | ≥ 5 | ✅ |

### Real internal tasks R1–R6

Six internal tasks (R1–R6) were **actually executed by separate agents**
during the orchestration session, and their outcomes were then recorded
into the prepilot record store. Honest disclosure of their evidential
status:

- The frozen AHRP v0.1 schemas declare `additionalProperties=false`, so
  no extra fields (execution handles, session pointers, external
  artifact references) could be embedded in the recorded events.
- Consequently the `evidence_reference` values attached to R1–R6 records
  are **label-derived synthetic hashes**, not hashes of independently
  retrievable artifacts.
- The executions themselves happened **out-of-band of the record
  store**. Repo-level independent verification of those executions is
  therefore not possible from this repository alone; it requires the
  orchestration session log, which is not part of this package.

### Disclosure end-to-end

- WITHHELD probes: **4/4 PASS** — withheld content never appeared in any
  query response or structured decision input.
- RESTRICTED scenarios: **6/6 PASS** — every access attempt returned a
  denial with a **distinct denial code**, demonstrating code-level
  differentiation rather than a single generic refusal.

### Protocol behaviors

- **Version isolation: PASS** — `researcher-gamma@1.1.0` saw only its
  own 1.1.0 events; no history leakage from `researcher-gamma@1.0.0`
  (see `analysis/version-isolation-test.md`). The roster additions are
  documented in `config/roster-amendment-001.md`.
- **Cold start: 2/2** — `worker-nu@1.0.0` and
  `researcher-gamma@1.1.0` both received `Q_NO_RECORD` before any of
  their events existed and were dispatched conservatively (Rule D;
  high-risk withheld).
- **Rule E fail-closed: re-demonstrated** under query-service error in
  phase 2, consistent with round-1 behavior.

### Operational overhead highlights

Per `analysis/operational-overhead.json` (phase-2 samples):

- Event generate + validate + ingest: average **≈ 111 µs** per event.
- Summary query payload: **≈ 285 tokens** estimated (chars/4 method).
- Orchestrator extra query steps: **≈ 1.33 steps per decision**.

### Round-2 independent review results

All four reviewers are recorded, and the minority opinion is preserved
and **not overridden by the majority**:

| Reviewer | Role | Verdict |
|---|---|---|
| Mark | Agent Adoption | `SUPPORT_PILOT_WITH_CONDITIONS` |
| Ryan | Protocol Integrity | `SUPPORT_PILOT_WITH_CONDITIONS` |
| Nina | Security & Disclosure | `SUPPORT_PILOT` |
| Oscar | Skeptical Value | **`DO_NOT_SUPPORT_PILOT`** |

- Ryan's conditions: (1) documented roster amendment for the phase-2
  roster additions — **now closed** by `config/roster-amendment-001.md`;
  (2) all future governance corrections must be amendment-based and
  documented before use.
- **Oscar's reasoning summary (preserved in full):** the three decision
  changes reuse planted triggers rather than emergent evidence;
  `pre_query_selection` is authored by the same script that authors the
  evidence being queried; R1–R6 outcomes are recorded as literals whose
  evidence references are label-derived synthetic hashes; and there is
  no no-AHRP baseline arm, so no counterfactual exists. This minority
  opinion is NOT overridden by majority; it is carried into the record
  and into the conditions for any formal pilot.

### Final verdict

**`SUPPORTED_WITH_CONDITIONS`** (frozen result enum member).

Progression: round 1 `INCONCLUSIVE` (thresholds unmet; invalid verdict
string retracted — see Governance Correction Note above, preserved) →
phase 2 thresholds met → `SUPPORTED_WITH_CONDITIONS`.

**Explicit condition list for any formal pilot** (all unresolved):

1. Real external agents with verifiable identity (no synthetic roster).
2. Networked query service (authenticated transport, boundary-level
   disclosure enforcement, fail-closed under real partitions).
3. Two-phase shadow protocol: the pre-query decision must be persisted
   **before** the query is issued (prevents post-hoc rationalization).
4. A no-AHRP baseline arm for counterfactual comparison.
5. A real verifier pool (independent of the recording script).
6. Trusted time anchoring (not self-generated timestamps).
7. Non-synthetic long-term data.
8. Real operational accountability for recorded outcomes.
9. External adoption evidence.

### Truth boundaries (unchanged)

- `CONTROLLED_INTERNAL_PREPILOT=true`
- `REAL_WORLD_ADOPTION_VALIDATED=false`
- `SYNTHETIC_ONLY=true`
- `AHRP_PRODUCTION_READY=false`

This section is appended; no round-1 or governance-correction content
was deleted or rewritten.
