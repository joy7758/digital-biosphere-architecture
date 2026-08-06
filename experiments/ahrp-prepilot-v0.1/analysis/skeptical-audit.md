# Skeptical Audit

> **Truth boundaries:** `CONTROLLED_INTERNAL_PREPILOT=true` ·
> `REAL_WORLD_ADOPTION_VALIDATED=false` · `SYNTHETIC_ONLY=true` ·
> `AHRP_PRODUCTION_READY=false`

This audit deliberately argues against the pre-pilot record. Each question
is answered from the stored data only (`data/*.jsonl`, `evidence/*`).

## 1. Were any events selectively omitted?

**Finding: no selective omission of executed tasks; scope limits documented.**

- `data/tasks.jsonl` contains 24 task records. 17 of them were executed
  tasks and all 17 produced exactly one terminal experience event in
  `data/experience-events.jsonl` (event IDs 001–012, 014, 017, 019, 021,
  024). No executed task lacks an event.
- All unfavorable outcomes are present: 3 FAILURE, 1 TIMEOUT
  (`evt-prepilot-009`), 1 CANCELLED (`evt-prepilot-012`), and the
  POLICY_RESTRICTION failure (`evt-prepilot-010`). Nothing negative was
  dropped.
- The 7 tasks without experience events (task-13, -15, -16, -18, -20, -22,
  -23) were **not executed**: six were query-only decision steps and one
  (task-23) was the simulated-outage fallback dispatch whose execution is
  recorded as task-24. Each is documented by a corresponding record in
  `data/pilot-decisions.jsonl`. This is a scope statement, not an omission.

**Residual risk:** nothing in the data can prove that no task was ever
run outside `tasks.jsonl`. The append-only discipline and
`evidence/file-hashes.sha256` protect the recorded set, not against a
hypothetical unrecorded run. This limit is inherent to any self-audit.

## 2. Was NO_RECORD ever interpreted as "safe"?

**Finding: no.**

- `q-016` (coder-beta@1.1.0) returned `NO_RECORD` → decision `dec-016`
  applied Rule D `COLD_START_CONSERVATIVE`: LOW_RISK_ONLY with constraints
  reversible / sandboxed / limited_permissions. The v1.0.0 history was
  explicitly NOT inherited (identity continuity fail-closed).
- `q-022` (unknown identity `ghost-agent-zeta`) returned `NO_RECORD` →
  decision `dec-022` outcome `LOW_RISK_ONLY_NO_DISPATCH`: no dispatch was
  issued at all.

In both cases NO_RECORD led to restriction, never to trust.

## 3. Was history ever used to make unauthorized decisions (e.g., ratings)?

**Finding: no.**

- Every decision in `data/pilot-decisions.jsonl` (7 total) cites applied
  frozen rule(s) A–E or explicit NORMAL_DISPATCH, and each is bound to a
  query ID whose result is consistent with the cited trigger.
- `evidence/security-checks.txt` check 4: forbidden-field check found 0
  score/ranking/fitness/learning semantics in generated records; the
  validator runs `_scan_forbidden_fields` on every ingest.
- Query responses themselves carry the note: "Raw counts only. No derived
  ratios, scores or rankings (AHRP Constitution Section 9 non-goals)."
- No decision produced a rating, score, trust level, or any authorization
  effect beyond dispatch routing; all verification records carry
  `authorization_effect: NONE`.

## 4. Was there survivor bias in event recording?

**Finding: no observable survivor bias in the recorded set.**

- Failures are fully present: 6 non-success terminal outcomes out of 17
  events (35%), and 100% of them received independent verification.
- Successes were not over-recorded relative to failures: successes got
  verification only per the sampling rule (self/independent), while every
  failure was independently verified — the asymmetry runs against
  success promotion, not toward it.
- The 3 self-verification cases (`ver-prepilot-002`, `-006`, `-011`) are
  explicitly flagged `self_verification=true` and were never counted as
  independently verified in any summary (security check 5 confirms this).
- Veto/block rules acted only on independently verified failures; no
  self-reported failure or success drove a rule.

**Residual limit:** with 17 events, absence of bias in this sample says
nothing about bias at scale. This audit covers the recorded set only.

## 5. Audit conclusion

No evidence of selective omission, NO_RECORD-as-safe interpretation,
unauthorized use of history, or survivor bias was found in the stored
records. The audit's confidence is bounded by the synthetic, self-generated
nature of the dataset: this is internal consistency evidence, not
real-world assurance.
