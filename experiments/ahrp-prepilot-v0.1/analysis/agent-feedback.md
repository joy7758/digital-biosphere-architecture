# Orchestrator Agent Assessment (Agent Feedback)

> **Truth boundaries:** `CONTROLLED_INTERNAL_PREPILOT=true` ·
> `REAL_WORLD_ADOPTION_VALIDATED=false` · `SYNTHETIC_ONLY=true` ·
> `AHRP_PRODUCTION_READY=false`

Assessment recorded from the perspective of `orchestrator-alpha@1.0.0`
after completing the controlled internal pre-pilot. All observations are
based solely on the synthetic data in `data/` and `evidence/`.

## 1. Would the Orchestrator continue querying AHRP?

**Yes — conditionally.** The queries provided actionable information:

- `q-013` exposed 2 independently verified CAPABILITY_LIMIT failures for
  `coder-beta@1.0.0`, which mechanically triggered Rule A and changed the
  dispatch decision (`dec-013`, the recorded
  EVIDENCE_SUPPORTED_DECISION_CHANGE).
- `q-015` exposed an independently verified POLICY_RESTRICTION failure,
  triggering Rule B block (`dec-015`).
- `q-016` correctly returned NO_RECORD for the new version
  `coder-beta@1.1.0` (identity continuity fail-closed; v1.0.0 history not
  inherited), which triggered conservative Rule D dispatch (`dec-016`).
- `q-023` simulated unavailability produced a clean fail-closed path via
  Rule E (`dec-023`).

In every dispatch decision, the query result was either the trigger for a
rule or the confirmation that no rule applied. No query returned data that
was ignored or unusable.

## 2. What was valuable?

1. **Structured decision inputs.** `structured_decision_inputs()` with
   `restricted_text` stripped gave a clean, machine-checkable basis for
   rules A–E; no decision needed free text.
2. **Independence-aware verification flags.** `has_independent_verification`
   and `self_only` made it unambiguous which failures could drive veto/block
   rules; self-reported successes never masqueraded as verified evidence.
3. **Version-scoped history.** `coder-beta@1.1.0` was treated as having no
   history despite `coder-beta@1.0.0` having 8 events. This fail-closed
   identity continuity behavior prevented unearned trust transfer.
4. **Error codes as data.** `NO_RECORD` and `Q_INTERNAL_ERROR` were
   unambiguous signals that drove rules D and E without guessing.
5. **Summary mode was usually sufficient.** 4 of 7 queries used summary
   mode; detail drilldowns (3) were only needed when a rule trigger had to
   be checked against specific failure categories.

## 3. What was not valuable / friction points?

1. **Small sample sizes.** With 17 events total, rule triggers are driven
   by single-digit counts; no statistical confidence is possible. This is
   inherent to a pre-pilot, but the orchestrator cannot distinguish
   "genuine capability limit" from "two unlucky tasks" at this scale.
2. **No timing/recency signals in structured facts.** Rules A–E treat all
   independently verified failures equally regardless of age. For production
   use, the orchestrator would benefit from structured `occurred_at` being a
   first-class decision input rather than requiring event drilldowns.
3. **Rule precedence reasoning lives outside the query layer.** At `dec-020`
   both Rule A and Rule C applied; precedence (B > A > C) had to be
   resolved by the orchestrator manually. A machine-readable precedence
   annotation in the response would reduce interpretation risk.

## 4. What would need to change for production use?

1. **Real agents and real task volume.** Everything here is synthetic;
   production requires independent agents with verifiable identities (DBOS
   binding) and enough events for thresholds to be meaningful.
2. **A durable, replicated query endpoint.** The simulated outage (q-023)
   exercised Rule E; production needs the endpoint's availability and
   fail-closed behavior proven under real network partitions.
3. **Network/transport layer.** The pre-pilot ran against a local
   in-process engine; production needs a networked query service with
   authentication and disclosure enforcement at the transport boundary.
4. **Verification capacity.** 100% independent verification of failures
   was feasible at 6 failures; at production scale this needs a defined
   verifier pool and throughput budget.
5. **Audit and retention policy.** Production requires defined retention,
   disclosure policy governance, and an appeal/correction path for
   disputed records — none of which were exercised here.

## Summary

The orchestrator would continue querying AHRP: queries were cheap,
structured, and directly actionable (1 EVIDENCE_SUPPORTED_DECISION_CHANGE,
1 policy block, 1 fail-closed fallback — all correctly driven by query
results). Readiness for production requires the conditions listed in
section 4; none of them were in scope for this synthetic pre-pilot.
