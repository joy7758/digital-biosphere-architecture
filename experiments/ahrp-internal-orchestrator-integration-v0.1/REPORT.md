# AHRP Internal Orchestrator Integration Trial v0.1 — Report

AHRP 内部编排器集成试验 v0.1 报告。

Trial ID: `ahrp-internal-orchestrator-integration-v0.1`
Run date (deterministic clock): 2026-08-07
AHRP tree hash at run time: `4d9dd8a00e5605204c2d9583525af2a296ece2e0`
(= `origin/main:AHRP`; AHRP v0.1 was NOT modified)

## 1. Objective

This trial answers ONE question:

> Can a programmatic orchestrator integrate the frozen AHRP v0.1 query
> interface and bind returned history to auditable delegation decisions?
>
> 程序化编排器能否集成冻结的 AHRP v0.1 查询接口，并将返回的历史记录
> 绑定到可审计的委派决策？

It explicitly does NOT answer whether a model-based or autonomous agent
voluntarily adopts AHRP, whether AHRP improves success rates, or whether
AHRP is commercially viable.

## 2. Setup

Executable role implementations (internal, deterministic, pre-programmed —
NOT autonomous agents):

| Component | Role | Version | Boundary (declared) |
|---|---|---|---|
| `did:example:orchestrator-core` | programmatic orchestrator component | 1.0.0 | never executes tasks; selects workers and records rationale |
| `did:example:worker-alpha` | programmatic worker component (Coding) | 1.0.0 | no dependency resolution |
| `did:example:worker-beta` | programmatic worker component (Research) | 1.0.0 | no external source access |
| `did:example:worker-gamma` | programmatic worker component (Review) | 1.0.0 | no security auditing |

Retained facts:

- the Coding worker component actually generates code and compiles it;
- the Research worker component actually generates research files;
- the Review worker component actually generates review records;
- the orchestrator component actually invokes the (unmodified) AHRP v0.1
  HistoryStore query interface;
- history queries actually changed programmatic routing outcomes.

```text
These executable components are not evidence of autonomous,
model-based, or externally operated agent adoption.
这些可执行组件不能证明自主智能体、模型型智能体或外部智能体采用了 AHRP。
```

Seed history: 6 pre-existing records (3 failure, 3 success), each with a
real SHA-256 evidence body and a `SYSTEM_BENCHMARK` verification (NOT
`INDEPENDENT_AGENT`).

## 3. Results

```text
TASK_COUNT:
20   (No-AHRP baseline: 10, AHRP-assisted: 10)

AHRP_QUERY_COUNT:
12

PROGRAMMATIC_DECISION_CHANGED_COUNT:
3    (t-202, t-204, t-206 — each backed by a resolvable history reference)

RESOLVABLE_HISTORY_REFERENCE_COUNT:
16 event references across the assisted phase
```

> AHRP_QUERY_COUNT is produced by the configured AHRP-assisted execution
> path. It is not evidence that an autonomous agent voluntarily chose to
> query AHRP.
>
> AHRP_QUERY_COUNT 来自预先配置的 AHRP 辅助执行路径，不能证明自主智能体
> 自愿选择查询 AHRP。

Decision changes are recorded strictly as
`PROGRAMMATIC_ROUTING_CHANGE_OBSERVATION` (not an adoption signal, not an
agent demand signal):

| Task | Before query | History reason | After query |
|---|---|---|---|
| t-202 (coding, needs dependency resolution) | DELEGATE worker-alpha | CAPABILITY_LIMIT_HISTORY (`evt-seed-alpha-dep-001`) | MANUAL_REVIEW |
| t-204 (research, needs external sources) | DELEGATE worker-beta | POLICY_RESTRICTION_HISTORY (`evt-seed-beta-src-001`) | MANUAL_REVIEW |
| t-206 (review, needs security review) | DELEGATE worker-gamma | CAPABILITY_LIMIT_HISTORY (`evt-seed-gamma-sec-001`) | MANUAL_REVIEW |

No-change discipline observed:

- `t-208` (data_processing): all queries returned `NO_RECORD` → decision
  unchanged.
- `t-210` (controlled query-error injection): engine returned a `Q_*`
  error envelope → the component FAILED CLOSED, kept the before-query
  decision, performed no further queries.
- `t-201/203/205/207/209`: positive history only (`POSITIVE_HISTORY`) →
  decision unchanged.

Query cost (observational):

```text
latency:  min 0.0024 ms / mean 0.0498 ms / max 0.293 ms
tokens:   estimated 52–402 per envelope, 3156 total (len(json)//4)
calls:    12
```

Execution outcomes (recorded for transparency ONLY — no comparison):

```text
No-AHRP phase:       SUCCESS 6, FAILURE 4
AHRP-assisted phase: SUCCESS 7, NOT_EXECUTED 3 (routed to manual review)
```

Verification of generated records:

```text
run events: 7 (all executed delegations)
run verifications: 7 (SYSTEM_BENCHMARK, full-event binding)
all seeds + run records pass the AHRP Validator
verify_trial.py: PASS
tests: 15/15 OK
```

## 4. Supported findings

```text
PROGRAMMATIC_ORCHESTRATOR_USED_AHRP=true
AHRP_QUERY_INTERFACE_INTEGRATED=true
PROGRAMMATIC_DECISION_CHANGED_BY_HISTORY=true
HISTORY_REFERENCES_RESOLVED=true
QUERY_FAILURE_FAIL_CLOSED=true
```

即：冻结的 AHRP v0.1 查询接口可被程序化编排器集成，返回历史可绑定到
可审计的委派决策记录，查询异常可 fail-closed。

## 5. Unsupported findings

```text
MODEL_BASED_AGENT_USED_AHRP=false
AUTONOMOUS_AGENT_SELECTED_AHRP_TOOL=false
VOLUNTARY_AHRP_QUERY_VALIDATED=false
REAL_AGENT_ADOPTION_VALIDATED=false
REAL_WORLD_ADOPTION_VALIDATED=false
```

本试验没有模型型智能体参与，没有自主工具选择，没有自愿查询行为；
查询次数是配置路径的实现结果，不是采用证据。

## 6. Final result

```text
TRIAL_RESULT=INCONCLUSIVE
INTEGRATION_MECHANISM_DEMONSTRATED=true
```

## 7. Limitations

1. **Not a performance claim.** This trial does not prove that AHRP
   improves agent performance. The task mix is designed to trigger history
   consumption; cross-phase outcome differences are observational only.
2. **Not an adoption claim.** All components are pre-programmed; queries
   are configured behavior. Real-agent adoption requires the separate
   model-based trial (DESIGN_ONLY, not executed).
3. Seed history is authored for the trial and verified by
   `SYSTEM_BENCHMARK` recomputation only
   (`REAL_INDEPENDENT_VERIFICATION=false`).
4. Token cost is a byte-length estimate (`len(json)//4`).
5. N=20; no statistical claims of any kind.
6. No agent scores, rankings, trust scores or reliability scores are
   computed (AHRP Constitution Section 9 non-goals).

## Truth boundaries

```text
INTERNAL_EXECUTABLE_INTEGRATION_TRIAL=true
PROGRAMMATIC_ORCHESTRATOR_USED_AHRP=true
MODEL_BASED_ORCHESTRATOR=false
AUTONOMOUS_TOOL_SELECTION=false
VOLUNTARY_AHRP_QUERY_VALIDATED=false
REAL_AGENT_ADOPTION_VALIDATED=false
REAL_EXTERNAL_AGENT=false
REAL_HUMAN_ORCHESTRATOR=false
AHRP_PRODUCTION_READY=false
AHRP_STANDARD_PUBLISHED=false
SUCCESS_RATE_IMPROVEMENT_PROVEN=false
REAL_INDEPENDENT_VERIFICATION=false
AHRP_V0_1_MODIFIED=false
INTEGRATION_MECHANISM_DEMONSTRATED=true
TRIAL_RESULT=INCONCLUSIVE
```

## Reproduction

```bash
cd experiments/ahrp-internal-orchestrator-integration-v0.1
python3 config/generate_seed_history.py   # deterministic seeds
python3 run_trial.py                      # full two-phase run
python3 verify_trial.py                   # post-run verification
python3 -m unittest discover -s tests     # 15 tests
```
