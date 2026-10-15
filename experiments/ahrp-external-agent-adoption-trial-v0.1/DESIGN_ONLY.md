# DESIGN ONLY — AHRP External Agent Adoption Trial v0.1

```text
DESIGN_ONLY=true
TRIAL_EXECUTED=false
```

本目录仅包含设计文档。**未执行任何试验，不存在任何运行结果。**
不得将本文件任何内容引用为运行证据。

## 目的

回答内部编排器集成试验（`ahrp-internal-orchestrator-integration-v0.1`）
无权回答的问题：

> 一个独立运行的模型型 Orchestrator Agent，在 AHRP 只是多个可选工具
> 之一、且没有任何指令要求使用它的情况下，是否会自主决定查询 AHRP
> 历史？

## 设计约束（真正的采用证据必须同时满足）

1. **模型型 Orchestrator 独立运行**：Orchestrator 必须是独立于试验
   代码运行的模型型 Agent（LLM-based）。试验代码不得替它决策、不得
   预编程其路由逻辑。
2. **多工具可选**：Agent 获得多个可选工具（例如：无历史直接执行、
   静态规则表、AHRP 查询等），AHRP 只是其中之一。
3. **Prompt 中立**：系统提示不得要求、暗示或鼓励必须查询 AHRP；
   只能描述可用工具清单。
4. **自主决定**：是否调用 AHRP 工具完全由 Agent 自主决定。
5. **只记录、不替代**：试验代码只记录工具调用（tool-call trace），
   绝不替 Agent 做出或改写决策。
6. **完整留痕**：每次运行保存完整 transcript、tool-call evidence、
   模型名称与版本号、采样参数。
7. **对照组设计**：至少包含两组：
   - AHRP 工具可用组（treatment）；
   - AHRP 工具不可用对照组（control），用于区分「用了 AHRP」与
     「本来就会完成任务」。
8. **真正的成功条件**（只有满足以下全部才可声称采用得到验证）：

```text
MODEL_BASED_AGENT_USED_AHRP=true
AUTONOMOUS_AHRP_TOOL_SELECTION=true
VOLUNTARY_AHRP_QUERY_COUNT>0
```

且上述结论必须来自 Agent 自发行为记录，而非任何试验脚本的配置路径。

## 证据要求（执行前必须先实现）

- transcript 哈希链（每条记录绑定前一条哈希）；
- tool-call 记录与 transcript 的交叉校验；
- 模型版本固定记录（同一批次不得中途换模型）;
- 独立复验脚本：从 transcript 重建全部 tool-call 计数；
- 禁止指标延续：不计算 score / ranking / trust / reliability。

## 真值边界（设计阶段）

```text
DESIGN_ONLY=true
TRIAL_EXECUTED=false
MODEL_BASED_AGENT_USED_AHRP=false
AUTONOMOUS_AHRP_TOOL_SELECTION=false
VOLUNTARY_AHRP_QUERY_COUNT=0
REAL_AGENT_ADOPTION_VALIDATED=false
REAL_WORLD_ADOPTION_VALIDATED=false
AHRP_PRODUCTION_READY=false
```

## 禁止事项

- 不得伪造或预演任何运行结果；
- 不得在实现前声称任何采用结论；
- 不得复用内部集成试验的 12 次查询数字作为采用证据。
