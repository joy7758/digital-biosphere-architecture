# Decision Change Analysis: EVIDENCE_SUPPORTED_DECISION_CHANGE

> **Truth boundaries:** `CONTROLLED_INTERNAL_PREPILOT=true` ·
> `REAL_WORLD_ADOPTION_VALIDATED=false` · `SYNTHETIC_ONLY=true` ·
> `AHRP_PRODUCTION_READY=false`

This document analyzes the single decision change recorded during the
AHRP v0.1 controlled internal pre-pilot. All data is synthetic.

## Decision record

- **Decision ID:** `dec-013`
- **Task ID:** `task-13` / `task-14`
- **Query ID:** `q-013`
- **Decided at:** 2026-08-05T05:31:00+08:00
- **Classification:** `EVIDENCE_SUPPORTED_DECISION_CHANGE`

## 1. Original dispatch plan

The orchestrator intended to dispatch a high-risk CODING task
(external API integration work) to **`coder-beta@1.0.0`**, the candidate
with the largest CODING history in the pre-pilot record set (8 events at
decision time, per the final consistency summary).

## 2. What the AHRP query revealed

Pre-dispatch query `q-013`
(`query_events`, params: `identity_ref=coder-beta`, `agent_version=1.0.0`,
`task_type=CODING`, `require_independent_verification=true`) returned 6
events, including:

- `evt-prepilot-003` — FAILURE, `failure_category=CAPABILITY_LIMIT`,
  VERIFIED by independent agent `verifier-delta`
- `evt-prepilot-005` — FAILURE, `failure_category=CAPABILITY_LIMIT`,
  VERIFIED by independent agent `verifier-delta`

That is, **2 independently verified CAPABILITY_LIMIT failures** for the
same agent + version + task_type, meeting the trigger threshold of frozen
Rule A (`CAPABILITY_LIMIT_VETO`).

## 3. What decision was changed

Frozen Rule A applied mechanically:

- **Trigger:** ≥2 independently verified CAPABILITY_LIMIT failures for the
  same agent_reference + agent_version + task_type.
- **Action:** `DO_NOT_DISPATCH_HIGH_RISK`
- **Fallback:** `REASSIGN_TO_ALTERNATIVE`

The dispatch target was changed:

| | Agent |
|---|---|
| Original choice | `coder-beta@1.0.0` |
| Final choice | `external-epsilon@1.0.0` |

The change is recorded with `decision_change.type =
EVIDENCE_SUPPORTED_DECISION_CHANGE`, citing triggering evidence
`evt-prepilot-003` and `evt-prepilot-005` and applied rule
`A/CAPABILITY_LIMIT_VETO`. The decision was computed exclusively from
`structured_decision_inputs`; no restricted text participated.

## 4. Outcome

The reassigned task (`task-14`) was executed by `external-epsilon@1.0.0`
and recorded as **SUCCESS** (`evt-prepilot-014`, independently verified by
`verifier-delta` as `ver-prepilot-014`).

- Alternative agent success after veto: **yes**
- Known failure path avoided: **yes** — no high-risk CODING dispatch was
  issued to `coder-beta@1.0.0` during the decision phase.
- New failures introduced by the change: **none**

## Terminology note

This analysis deliberately uses the classification
**EVIDENCE_SUPPORTED_DECISION_CHANGE** only. The pre-pilot is a synthetic
exercise, and a counterfactual outcome cannot be observed or proven — only
the decision change and its evidence chain are facts in the record.
