# AHRP v0.1 Pre-Pilot (`ahrp-prepilot-v0.1`)

**Status flags (must be preserved in all derived reporting):**

- `CONTROLLED_INTERNAL_PREPILOT=true`
- `REAL_WORLD_ADOPTION_VALIDATED=false`
- `SYNTHETIC_ONLY=true`
- `AHRP_PRODUCTION_READY=false`

## What this directory is

The working directory for a **controlled internal pre-pilot** of the Agent
History & Reliability Protocol (AHRP) v0.1 query-driven dispatch loop, run
against the frozen r3 baseline
(commit `64bfed1f3063f4f463bb1e2680ef6b0b1d312201`, branch
`fix/ahrp-v0.1-audit-r3`, 208 tests passing).

It is **not** real-world adoption evidence, not field validation, and not
production-readiness evidence. All agents, tasks, events, and verifications
are synthetic and internal.

## Layout

| Path | Meaning |
|---|---|
| `PREPILOT_PROTOCOL.md` | Frozen protocol: rules for events, verification, queries, decisions (A–E), criteria, prohibitions |
| `config/agents.json` | Agent roster (8 identity/version entries; entries 7–8 added by `config/roster-amendment-001.md`) + control metadata |
| `config/routing-rules.json` | Frozen dispatch decision rules A–E |
| `config/disclosure-policy.json` | Synthetic disclosure policy used by queries |
| `config/roster-amendment-001.md` | Documented amendment adding `researcher-gamma@1.1.0` and `worker-nu@1.0.0` (version-isolation + cold-start tests) |
| `data/tasks.jsonl` | One JSON object per pilot task (populated during the pilot) |
| `data/experience-events.jsonl` | Terminal AHRP experience events, schema-validated |
| `data/verification-records.jsonl` | Independent verification records (100% of failures, 30% sampled successes) |
| `data/queries.jsonl` | Every AHRP query with parameters and response code |
| `data/pilot-decisions.jsonl` | Dispatch decisions citing applied rule(s) |
| `evidence/` | Supporting artifacts (hashes, logs) for records above |
| `analysis/` | Post-hoc analysis outputs |
| `AHRP_PREPILOT_REPORT_v0.1.md` | Final report (placeholder until pilot completes) |

## How to interpret the data

- Each `.jsonl` file is append-only, one JSON object per line, ordered by
  execution time.
- An experience event is **self-reported** until an independent verification
  record binds to it. Routing rules A/B act only on **independently
  verified** failures.
- `agent_reference` + `agent_version` is the identity key; versions are
  never conflated.
- Query response codes (`Q_NO_RECORD`, `Q_DISCLOSURE_DENIED`, …) are part
  of the evidence and drive rules D and E.
- Records must pass the frozen AHRP schemas (`experience-event.schema.json`,
  `verification.schema.json`) from the baseline commit; any deviation is a
  defect, not a data quirk.

## Truth boundaries

Results from this directory may only be described as
*controlled internal synthetic pre-pilot evidence for the AHRP v0.1
process loop*. They must never be presented as production validation,
external adoption, reliability certification, or compliance approval.
The AHRP worktree remains read-only throughout; this directory is the only
place new files may be added.
