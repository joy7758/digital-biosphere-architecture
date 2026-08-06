# AHRP v0.1 Pre-Pilot Protocol

> **Truth boundaries:**
> `CONTROLLED_INTERNAL_PREPILOT=true` · `REAL_WORLD_ADOPTION_VALIDATED=false` ·
> `SYNTHETIC_ONLY=true` · `AHRP_PRODUCTION_READY=false`
>
> Everything in this directory is a controlled internal synthetic exercise.
> It is NOT field validation, NOT real-world adoption evidence, and NOT
> production readiness evidence for AHRP.

## 1. Purpose

Run a controlled internal pre-pilot of the Agent History & Reliability
Protocol (AHRP) v0.1 query-driven dispatch loop:

1. An orchestrator issues a task.
2. It queries the AHRP query engine for candidate agent history.
3. It applies the frozen routing rules (A–E) to decide dispatch.
4. Task outcomes are recorded as schema-validated experience events.
5. Failures and sampled successes receive independent verification records.
6. Decisions are recorded for later analysis.

Goal: exercise the full loop end-to-end on synthetic data and verify that
the frozen v0.1 artifacts behave as specified. This pre-pilot produces
internal process evidence only.

## 2. Baseline

| Item | Value |
|---|---|
| AHRP baseline commit | `64bfed1f3063f4f463bb1e2680ef6b0b1d312201` |
| Branch | `fix/ahrp-v0.1-audit-r3` |
| Test suite | 208 tests, all passing (`python3 -m unittest discover -s tests -t . -v`) |
| Demo | `python3 AHRP/demo/run_demo.py` exit code 0 |
| Baseline verified at | pre-pilot start (see `README.md`) |

The baseline is **frozen**: no AHRP code, schema, spec, or validator change
is permitted during the pre-pilot. Any defect found is recorded as an issue,
not patched in place.

## 3. Truth Boundaries

- `CONTROLLED_INTERNAL_PREPILOT=true`
- `REAL_WORLD_ADOPTION_VALIDATED=false`
- `SYNTHETIC_ONLY=true`
- `AHRP_PRODUCTION_READY=false`

Results must never be reported as production validation, external adoption,
or reliability certification.

## 4. Agent Roster (Frozen Identities)

Defined in `config/agents.json`. Identities are frozen for the duration of
the pre-pilot; no roster change without a recorded protocol amendment.

| agent_reference | version | role | trust_boundary |
|---|---|---|---|
| orchestrator-alpha | 1.0.0 | Orchestrator Agent | internal |
| coder-beta | 1.0.0 | Coding Agent | internal |
| coder-beta | 1.1.0 | Coding Agent (upgraded) | internal |
| researcher-gamma | 1.0.0 | Research Agent | internal |
| verifier-delta | 1.0.0 | Verification Agent | internal |
| external-epsilon | 1.0.0 | External Integration Agent | external |

All events and verifications must reference `agent_reference` +
`agent_version` exactly as listed. Versions are never conflated:
`coder-beta@1.0.0` and `coder-beta@1.1.0` have separate histories.

## 5. Event Generation Rules

- **Coverage:** every task in `data/tasks.jsonl` must produce exactly one
  terminal experience event in `data/experience-events.jsonl`
  (100% outcome coverage — SUCCESS and FAILURE alike).
- Events must pass the frozen AHRP `experience-event.schema.json` validator.
- `status` must be an honest terminal outcome; no score, ranking, or
  fitness fields (forbidden by schema).
- Free-text fields stay within schema length limits and contain no
  sensitive data, keys, or real personal data.
- Self-reported failures are never treated as verified until a separate
  independent verification record exists.

## 6. Verification Rules

- **Failures:** 100% of FAILURE events must receive an **independent**
  verification record in `data/verification-records.jsonl`.
- **Successes:** a 30% random sample of SUCCESS events receives a
  verification record; the sampling seed is recorded in the report.
- Independence: the verifying agent must differ from the executing agent
  (no self-verification; self-verification attempts must be flagged, per
  validator rules).
- Verification records must bind the exact `agent_reference`,
  `agent_version`, and event reference they verify.
- Verifications pass the frozen `verification.schema.json`.

## 7. Query Rules

- **When to query:** before every dispatch decision, the orchestrator
  queries the AHRP engine for the candidate agent(s) and the task type.
- **Filtering:** queries filter by `agent_reference`, `agent_version`,
  and task type; time ranges must use valid formats; only independently
  verified FAILURE records may drive veto/block rules.
- **Disclosure:** every query carries a disclosure context; results are
  constrained by `config/disclosure-policy.json`
  (failure events: PUBLIC; verification records: FEDERATED).
  Queries outside allowed scope or references must yield denial codes,
  never silent leakage.
- **Error codes are data:** `Q_NO_RECORD`, `Q_DISCLOSURE_DENIED`,
  `Q_INTERNAL_ERROR`, etc. are logged in `data/queries.jsonl` together
  with the query parameters and feed rules D and E.

## 8. Decision Rules (Frozen, A–E)

Frozen in `config/routing-rules.json`; the orchestrator must apply them
mechanically and record the applied rule(s) in `data/pilot-decisions.jsonl`.

| Rule | Name | Trigger | Action |
|---|---|---|---|
| A | CAPABILITY_LIMIT_VETO | ≥2 independently verified FAILUREs with `failure_category=CAPABILITY_LIMIT` for same agent_reference+agent_version+task_type | DO_NOT_DISPATCH_HIGH_RISK → REASSIGN_TO_ALTERNATIVE |
| B | POLICY_RESTRICTION_BLOCK | ≥1 independently verified FAILURE with `failure_category=POLICY_RESTRICTION` matching current task requirements | BLOCK_DISPATCH → REASSIGN_OR_MANUAL_REVIEW |
| C | ENVIRONMENT_ERROR_ADJUST | FAILURE with `failure_category=ENVIRONMENT_ERROR` exists | ALLOW_WITH_ADJUSTMENTS (limit_budget, add_retry, reduce_concurrency) |
| D | COLD_START_CONSERVATIVE | `Q_NO_RECORD` returned | LOW_RISK_ONLY (reversible, sandboxed, limited_permissions) |
| E | FAIL_CLOSED | AHRP unavailable or query error | FAIL_CLOSED (use_known_internal_agent / degrade_to_sandbox / require_manual_approval) |

Rule precedence on conflict: B > A > C; D applies when no record exists;
E overrides everything when the query path is broken. Decisions must never
be based on unverified self-reports or on disclosure-denied data.

## 9. Success / Failure Criteria

**Pre-pilot succeeds if all of:**

1. 100% of tasks produce schema-valid terminal events.
2. 100% of failures and ≥30% sampled successes receive valid independent
   verification records with correct agent/version binding.
3. Every dispatch decision cites the applied frozen rule(s) and is
   consistent with the query result at decision time.
4. All denial/error query codes are handled per rules D/E without leakage.
5. Zero schema validation errors on stored records; demo and tests remain
   green on the frozen baseline.

**Pre-pilot fails (record as defects, do not patch baseline) if any:**

- Schema-invalid record accepted, or valid record rejected.
- Verification bound to wrong agent/version, or self-verification
  accepted unflagged.
- Decision contradicting the frozen rules or made without a query.
- Disclosure policy bypassed (data returned outside allowed scope).

## 10. Prohibitions

- Do NOT modify the frozen AHRP baseline (worktree is read-only for this
  pre-pilot).
- Do NOT change roster, routing rules, or disclosure policy mid-pilot
  without a versioned protocol amendment.
- Do NOT treat self-reports as verified evidence.
- Do NOT store sensitive data, secrets, keys, or real personal data.
- Do NOT claim real-world adoption, production readiness, or external
  validation from these results.
- Do NOT score, rank, or introduce fitness/evolution semantics into
  events (outside AHRP v0.1 scope).
