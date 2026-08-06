# Limitations — AHRP Internal Orchestrator Integration Trial v0.1

AHRP 内部编排器集成试验 v0.1 限制声明。

1. **Not an adoption claim.** All orchestrator and worker components are
   locally pre-programmed deterministic executables. `AHRP_QUERY_COUNT` is
   produced by the configured AHRP-assisted execution path; it is not
   evidence that an autonomous agent voluntarily chose to query AHRP.
   `MODEL_BASED_ORCHESTRATOR=false`, `AUTONOMOUS_TOOL_SELECTION=false`,
   `VOLUNTARY_AHRP_QUERY_VALIDATED=false`,
   `REAL_AGENT_ADOPTION_VALIDATED=false`.

2. **Not a performance claim.** This trial does not prove that AHRP
   improves agent performance. The task mix is designed to trigger history
   consumption; cross-phase outcome differences are observational only and
   are not comparable.

3. **Internal only.** `REAL_EXTERNAL_AGENT=false`. No external or public
   agent ecosystem participated.

4. **Seed history is authored.** The six seed records were created for the
   trial and verified by `SYSTEM_BENCHMARK` deterministic recomputation
   only. `REAL_INDEPENDENT_VERIFICATION=false`.

5. **Token cost is an estimate.** `tokens_estimated = len(canonical_json)
   // 4`; a byte-length proxy, not a tokenizer measurement.

6. **Tiny sample.** 20 tasks. No statistical inference is made or implied.

7. **No scoring by design.** No agent score, ranking, trust score or
   reliability score is computed (AHRP Constitution Section 9 non-goals).

8. **Result is INCONCLUSIVE by construction.** The trial can demonstrate
   the integration mechanism (`INTEGRATION_MECHANISM_DEMONSTRATED=true`)
   but cannot validate adoption; `TRIAL_RESULT=INCONCLUSIVE`.

9. **Production state unchanged.** `AHRP_PRODUCTION_READY=false`,
   `AHRP_STANDARD_PUBLISHED=false`, `SUCCESS_RATE_IMPROVEMENT_PROVEN=false`
   remain false after this trial.
