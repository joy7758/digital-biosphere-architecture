# Roster Amendment 001

- **Amendment ID:** `roster-amendment-001`
- **Date:** 2026-08-05
- **Amended file:** `config/agents.json`
- **Status:** CLOSED (post-hoc documentation of an undocumented phase-2
  roster change, per round-2 protocol-integrity review condition)

## Rationale

Phase 2 of the controlled internal pre-pilot required two additional
roster entries to exercise protocol behaviors that the round-1 roster
could not cover:

1. **Version-isolation test** — needed a *second version of an existing
   identity* (`researcher-gamma@1.1.0`) to demonstrate that history is
   scoped strictly by `agent_reference` + `agent_version` and is never
   conflated across versions. See `analysis/version-isolation-test.md`.
2. **Cold-start test** — needed a *brand-new identity*
   (`worker-nu@1.0.0`) with zero history to demonstrate Rule D
   conservative dispatch on `Q_NO_RECORD` before any event existed.

Both additions were made when `run_prepilot_phase2.py` was staged. They
were applied to the prepilot configuration only; the frozen AHRP
baseline (commit `64bfed1f3063f4f463bb1e2680ef6b0b1d312201`) was not
modified.

## Added entries (exact values)

| `agent_reference` | `agent_version` | Role | Trust boundary |
|---|---|---|---|
| `researcher-gamma` | `1.1.0` | Research Agent (upgraded) | internal |
| `worker-nu` | `1.0.0` | General Worker Agent (newly onboarded) | internal |

## Governance note

- New identity/version entries are treated as **cold start**: no history
  inheritance from any other identity or from earlier versions of the
  same reference. `researcher-gamma@1.1.0` does not inherit the record
  of `researcher-gamma@1.0.0`; `worker-nu@1.0.0` starts with
  `Q_NO_RECORD` semantics until its own independently verified events
  exist.
- This amendment documents a change that was executed before being
  documented. Per the round-2 protocol-integrity review condition
  (Ryan), all future roster changes must be amendment-based and
  documented **before** the new entries are used.
- Truth boundaries unchanged: `CONTROLLED_INTERNAL_PREPILOT=true`,
  `REAL_WORLD_ADOPTION_VALIDATED=false`, `SYNTHETIC_ONLY=true`,
  `AHRP_PRODUCTION_READY=false`.

## References

- `analysis/version-isolation-test.md` — phase-2 version isolation test
  setup and results for `researcher-gamma@1.1.0`.
- `analysis/cold-start-cases.md` — cold-start cases including
  `worker-nu@1.0.0`.
- `PREPILOT_PROTOCOL.md` — frozen rules D (cold start) and version
  non-conflation principle.
