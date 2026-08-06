# AHRP Internal Orchestrator Integration Trial v0.1

AHRP 内部编排器集成试验 v0.1。

本试验只回答一个问题：

> Can a programmatic orchestrator integrate the frozen AHRP v0.1 query
> interface and bind returned history to auditable delegation decisions?
>
> 程序化编排器能否集成冻结的 AHRP v0.1 查询接口，并将返回的历史记录
> 绑定到可审计的委派决策？

本轮运行结果：**TRIAL_RESULT=INCONCLUSIVE**，
**INTEGRATION_MECHANISM_DEMONSTRATED=true**（12 次接口查询，3 次由历史
驱动的程序化路由改变，1 次查询错误 fail-closed 安全阻断）。详见
[REPORT.md](REPORT.md)。

## 本试验不是什么

本试验**不是**真实 Agent 采用试验：

- 编排器与 Worker 均为**程序化组件**（程序化编排器组件、程序化 Worker
  组件、可执行角色实现），是本地预编程的确定性执行程序；
- AHRP 查询由预先配置的 AHRP 辅助执行路径产生，不是任何智能体自愿
  选择的结果；
- 本试验不能回答模型型智能体是否自主决定查询 AHRP、是否自愿采用
  AHRP、真实 Agent 生态是否存在查询需求。

```text
These executable components are not evidence of autonomous,
model-based, or externally operated agent adoption.
这些可执行组件不能证明自主智能体、模型型智能体或外部智能体采用了 AHRP。
```

真正的外部模型型 Agent 采用试验仅有设计文档，见
`experiments/ahrp-external-agent-adoption-trial-v0.1/DESIGN_ONLY.md`
（DESIGN_ONLY=true，TRIAL_EXECUTED=false）。

## 真值边界

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

## 目录结构

```text
ahrp-internal-orchestrator-integration-v0.1/
├── README.md                 本文件
├── TRIAL_PROTOCOL.md         协议：问题、真值边界、阶段、指标、判定
├── REPORT.md                 运行报告（实际数字 + 支持/不支持结论）
├── config/
│   ├── agent-roster.json     4 个组件注册（id/version/capabilities/boundary）
│   ├── tasks.json            20 个任务（10 基线 + 10 AHRP 辅助）
│   ├── generate_seed_history.py  确定性种子历史生成器
│   ├── history-events.jsonl  6 条种子 Experience Event
│   └── history-verifications.jsonl  6 条 SYSTEM_BENCHMARK 验证
├── orchestrator.py           程序化编排器组件（决策策略 + fail-closed 查询错误阻断）
├── workers.py                程序化 Worker 组件（真实产出工件）
├── run_trial.py              双阶段运行器
├── verify_trial.py           后运行验证器
├── tasks/                    （保留目录）
├── events/                   运行期生成的 Experience Event + Verification
├── evidence/                 种子与运行的证据体 + 工件
├── decisions/                每任务决策记录（no-ahrp / ahrp-assisted）
├── analysis/                 summary.json、限制声明
└── tests/                    25 项测试（8 集成 + 7 真值边界 + 6 fail-closed + 4 语义）
```

## 组件（可执行角色实现）

| 组件 | 角色 | 声明边界 |
|---|---|---|
| orchestrator-core | programmatic orchestrator component | 只委派、不执行，记录委派理由 |
| worker-alpha | programmatic worker component (Coding) | 无依赖解析能力 |
| worker-beta | programmatic worker component (Research) | 禁止访问外部数据源 |
| worker-gamma | programmatic worker component (Review) | 无安全审计能力 |

可以保留的事实：Coding Worker 实际生成代码并编译；Research Worker 实际
生成研究文件；Review Worker 实际生成审查记录；编排器组件实际调用
HistoryStore；历史查询实际改变了程序化处置结果。

## 运行

```bash
python3 config/generate_seed_history.py   # 生成种子（确定性）
python3 run_trial.py                      # 完整双阶段运行
python3 verify_trial.py                   # 后运行验证（PASS/FAIL）
python3 -m unittest discover -s tests     # 25 项测试
```

## 冻结保证

AHRP Schema / Validator / Query Engine / Spec / Constitution 未被本试验
修改。`analysis/summary.json` 记录 `origin/main:AHRP` 树哈希。

## 禁止事项（本试验层）

- 不计算 Agent score / ranking / trust score / reliability score；
- 不声称 "AHRP improved performance"；
- 不声称任何真实 Agent 采用结论；
- 不开发网络服务、Agent Marketplace；
- 不修改 AHRP 协议；不添加评分系统。

## 记录语义

- `history_used` 只包含实际返回的 Experience Event 引用（`event_id != null`）；
- `NO_RECORD` / `WITHHELD` / `QUERY_ERROR` 只进入 `query_observations`，
  不是历史，也不支持任何 history-driven 决策改变声明；
- `QUERY_FAILURE_FAIL_CLOSED=true` 仅在查询错误同时满足：自动委派被阻断、
  worker 未被调用、无工件、无 Experience Event、无 Verification Record
  时成立；仅停止查询但继续执行是 fail-open，不得声明。
