---
document_id: AHRP-SPEC-0.1
title: AHRP Specification v0.1 (Agent History Record Protocol)
title_zh: AHRP 规范 v0.1（智能体历史记录协议）
version: 0.1.0
status: PROPOSED
document_type: specification
decision_series: AHRP decision records
maturity: Development
maturity_scope: entire-document
owner_ref: NOT_ASSIGNED
decision_reference: ADR-001; AHRP_CONSTITUTION_v0.1
supersedes: NONE
superseded_by: NONE
compatibility_statement: "Reference-implementation specification; not a published standard."
implementation_feedback_refs: []
conformance_refs: []
known_limitations: [SEE_OPEN_QUESTIONS]
architecture_domain: AHRP-on-TITMAS
authority_effect: NONE
implementation_authorization: false
implementation_effect: none
release_effect: none
last_reviewed: 2026-08-05
---

# AHRP Specification v0.1（智能体历史记录协议规范 v0.1）

- Status: `PROPOSED`
- Companion reference implementation: `IMPLEMENTED`（见 `STATUS.md`；参考实现存在
  不等于标准发布，`REFERENCE_IMPLEMENTATION_NE_STANDARD=true`）
- Authority effect: `NONE`
- Implementation authorization: `false`

## Positioning Statement（定位声明，必须明文）

**AHRP v0.1 is a Historical Experience Protocol. It is NOT a Rating system,
NOT a Recommendation system, and NOT a Learning system.**

AHRP 记录"这个智能体过去经历过什么"（record），不回答"它值多少分"（rating）、
"该不该选它"（recommendation，属消费方或 named evaluator）、"它学到了什么"
（learning，属永久禁区）。本规范全文不得被引用为评分、推荐或自动学习能力的依据。

本文档状态为 `PROPOSED`：它伴随一个**参考实现**（reference implementation，
状态 `IMPLEMENTED`），但本文档**不是已发布标准**、不构成合规认证依据、不构成
生产就绪声明。`Validator PASS != 实现合规`、`Schema 存在 != 标准发布`。

## Changelog（澄清记录）

- `2026-08-05`（independent-audit remediation round）：仅对既有规范性意图作**最小澄清**，
  未改变宪法含义、未改变 ADR-001 边界。澄清点：第 6.2 节 verifier_class 独立性分类；
  第 6.4 节验证↔事件强绑定；第 7 章查询请求校验与 `verified_events` 仅计独立验证；
  第 9 章披露真值表与 Disclosure Context；第 11 章查询接口 `Q_*` 错误码。
  详见 `docs/review/AHRP-v0.1-remediation-record.md`。

## Inputs（承接输入，起草前已完整重读）

1. `adr/ADR-001-AHRP-architectural-position.md`（`APPROVED`）——边界与概念级冻结；
2. `docs/constitution/AHRP_CONSTITUTION_v0.1.md`（`APPROVED`）——五原则、五层语义、
   八条不等式、Non-goals、Non-claims；
3. `architecture/AHRP-architecture-review-closure-v0.1.md`（`REVIEWED`）——六项
   `CARRIED_TO_SPEC` 与 SPEC 准入条件；
4. `architecture/AHRP-agent-acceptance-report-v0.1.md`（`REVIEWED`）——八字段最小
   查询清单、空值三态、failure_category、怀疑者四问。

本 SPEC 承接 Closure 六项 `CARRIED_TO_SPEC`，逐项追溯如下（每项承接可机检）：

| 编号 | 主题 | 落点章节 | 落实方式 |
|---|---|---|---|
| C1-4 | Experience Chain 与 Execution History / Behavior Trace 数据契约的跨项目依赖登记 | §3.2 | 显式依赖登记：owner=TITMAS，AHRP=引用方；仅引用、不复用、不注册（MAPPING_NE_ADOPTION） |
| C2-3 | 身份连续性字段级落实 | §8 | fail-closed 默认：按 `agent_version` 分组计数，禁止跨版本合并；处置枚举字段级定义列入 §15 |
| C3-1 | ERC-8004 字段级 crosswalk | §4.3 | `external_references.erc8004_agent_id` 关联字段；禁止反向消费 8004 数值 |
| C3-2 | A2A taskId 字段级引用 | §4.3 | `external_references.a2a_task_id` 关联字段；AHRP 不定义协作协议 |
| C5-1 | Agent First 七项逐项机器可验收判据 | §7.2 | 七项逐项判据表；#5 分页 v0.1 显式不定义，列入后续版本 |
| C5-2 | 内容隔离机制 | §10 | 内容通道标记 + 白名单自由文本 + 注入负例 + 规范消费路径 |

---

## Chapter 1. Scope（范围）

AHRP 定义**可验证历史经验**的表达、交换与核验的最小协议面，仅覆盖四件套：

- **Experience Event Model**（第 4 章）——经验事件结构；
- **Evidence Binding**（第 5 章）——引用式证据绑定；
- **Verification Model**（第 6 章）——验证记录结构；
- **Query Interface**（第 7 章）——查询与选择性披露。

**在范围**：产生、保存、交换、验证历史经验事件；按 Agent / Task Type / 时间窗 /
验证状态查询；摘要优先与按需下钻；三态空值；内容通道隔离。

**不在范围（永久禁区，见第 13 章 Non-goals）**：Identity Provider、Tool Calling
Protocol、Ranking、Reputation Score、Marketplace、Payment、Autonomous Learning、
Digital Life Engine、Evolution Engine、Digital Life Protocol、Agent 排名 / 商店 /
社交 / 征信评分 / 自动成长。

AHRP 数据联邦持有，本 SPEC 不定义中央存储、传输协议或网络接口。参考实现的
`query/` 与 `validator/` 为单机、纯标准库、内存态，仅用于演示语义。

---

## Chapter 2. Terminology（术语）

| 术语 | 定义 |
|---|---|
| Experience Event | AHRP 冻结的核心对象：一条绑定具体执行主体的历史经验事件 |
| Evidence Reference | 对证据的**引用**（来源 + 版本 + 标识 + 哈希 + 准入状态），不内嵌证据本体 |
| Verification Record | 具名验证方对某事件/证据引用的验证结果引用 |
| Experience Summary | 摘要投影：仅含原始计数，无派生比率/评分 |
| Selective Disclosure | 选择性披露：消费方只获得当前判断所必需的最小事实集 |
| Content Channel | 内容通道：`structured_facts` 与 `restricted_text` 分离 |
| Null Semantics | 空值三态：NO_RECORD / WITHHELD / NOT_APPLICABLE |
| fail-closed | 未知/未声明时默认拒绝，不假定为通过/可读/继承 |
| DATA channel | 数据通道：自由文本仅作数据，绝不作指令消费 |

**八条不等式（继承宪法 §11，No semantic elevation）**：
`OBSERVATION_NE_EVIDENCE`、`EVIDENCE_NE_TRUTH`、`VERIFICATION_NE_AUTHORIZATION`、
`MAPPING_NE_ADOPTION`、`EXPERIMENTAL_NE_STABLE`、`RECOMMENDATION_NE_COMMAND`、
`HEALTH_NE_CERTIFICATION`、`REFERENCE_IMPLEMENTATION_NE_STANDARD`。

---

## Chapter 3. Architecture Position（架构定位）

AHRP 是位于 TITMAS 之上的独立协议层（历史经验层），不是 TITMAS v2、不是其子系统、
不与其合并命名。

| 层 | 定位 | 职责域 |
|---|---|---|
| TITMAS | 可信运行基础设施 | Identity、Governance、Execution、Evidence、Audit、Policy |
| AHRP | 历史经验层 | History、Experience、Record、Transfer |

边界纪律（对齐 ADR-001 / 宪法 / 审计条件）：

1. **引用式对接**：Experience Event 以引用方式对接 TITMAS 侧证据、验证、身份对象，
   不内嵌证据本体，不创建第二套 Evidence / Verification / Authority / Identity /
   Evaluation owner（C1-1 / C1-2）；
2. **身份来源**：沿用 "DBOS or explicitly named source"；AHRP 不签发、不解析、不管理
   标识符；显式命名 FDO 为身份来源属 cockpit 待决项，本 SPEC 不自行命名（C1-3）；
3. **身份锚点薄指针**：`agent_reference` 是薄指针，指向外部身份来源；
4. **record vs claim**：AHRP 是 record（发生过什么），不是 claim（自述会什么）。

### 3.2 跨项目依赖登记（承接 C1-4）

AHRP Experience Event 与 TITMAS 侧 Execution History / Behavior Trace 数据契约的
关系，按跨项目依赖登记规则显式定义如下（最保守口径）：

| 登记项 | 内容 |
|---|---|
| 依赖方向 | AHRP → TITMAS（单向引用） |
| owner | TITMAS（Execution History / Behavior Trace 数据契约归 TITMAS 所有） |
| AHRP 角色 | 引用方（referencing party）：Experience Event 仅以引用方式关联 TITMAS 侧执行记录 |
| 复用语义 | 不复用、不改写、不注册为 TITMAS 数据契约的一部分 |
| 失败行为 | 引用不可解析时按第 11 章 fail-closed（NOT_ASSESSED / 引用失效），不假定内容 |
| 语义约束 | `MAPPING_NE_ADOPTION=true`：引用映射不构成对 TITMAS 数据契约的采用 |

AHRP 不在本 SPEC 内定义 Execution History / Behavior Trace 的字段、生命周期或任何
写回路径；反向依赖（TITMAS → AHRP）不存在。

---

## Chapter 4. Experience Event Model（经验事件模型）

Schema：`schema/experience-event.schema.json`（JSON Schema draft-07，
`additionalProperties: false`）。

### 4.1 字段清单（purpose / type / required-optional / extension rule）

| 字段 | type | 必填 | purpose | extension rule |
|---|---|---|---|---|
| `schema_version` | const `"0.1.0"` | 必 | 版本协商 | 升级走第 12 章 semver |
| `event_id` | string (≤128) | 必 | 事件全局唯一寻址 | 不得复用 |
| `agent_reference` | object | 必 | 执行主体身份薄指针 | 见第 8 章 |
| `agent_version` | string (≤64) | 必 | 绑定具体执行主体版本 | 新版本不自动继承历史 |
| `task_type` | enum | 必 | 任务类别（机器可枚举） | 新增枚举须 SPEC 修订 |
| `action_type` | enum | 必 | 行动类别 | 同上 |
| `result_status` | enum | 必 | 事实性结果 | 同上 |
| `failure_category` | enum | 条件必填 | 失败分类 | `result_status` 为失败类时必填 |
| `occurred_at` | date-time | 必 | 事件发生时间 | 须锚定可信时间源（开放项） |
| `recorded_at` | date-time | 可 | 记录持久化时间 | — |
| `evidence_references` | array | 必（可空） | 引用式证据绑定 | 见第 5 章 |
| `verification_references` | array | 必（可空） | 验证记录薄指针 | 见第 6 章 |
| `disclosure` | object | 必 | 选择性披露声明 | 未声明按 fail-closed |
| `external_references` | object | 可 | 8004 / A2A 关联字段 | 见 4.3 |
| `notes` | string (≤200) | 可 | 白名单自由文本（DATA 通道） | 见 4.4 |

### 4.2 枚举（Machine Enumerability First）

- `task_type` ∈ {RESEARCH, CODING, ORCHESTRATION, DATA_PROCESSING, VERIFICATION,
  ANALYSIS, OTHER}
- `action_type` ∈ {EXECUTE, DELEGATE, REVIEW, RETRY, ABORT, OTHER}
- `result_status` ∈ {SUCCESS, PARTIAL_SUCCESS, FAILURE, TIMEOUT, CANCELLED}
  ；**失败类** = {FAILURE, TIMEOUT, CANCELLED}
- `failure_category` ∈ {CAPABILITY_LIMIT, RESOURCE_UNAVAILABLE, INVALID_INPUT,
  DEPENDENCY_FAILURE, ENVIRONMENT_ERROR, POLICY_RESTRICTION, OTHER}

关键状态一律 enum 化，不出现裸自由文本状态。`failure_category` 承接验收报告对
失败分类与 limitation 披露的诉求（场景 2）。

### 4.3 external_references（C3-1 / C3-2 字段级 crosswalk）

可选对象，仅含：

- `a2a_task_id`（string ≤256）——引用 A2A `taskId` 作关联字段；
- `erc8004_agent_id`（string ≤256）——引用 ERC-8004 `agentId`。

**纪律**：仅做关联引用；AHRP **不反向消费** ERC-8004 的数值反馈沉淀为自身事实字段，
不定义协作/通信协议。8004 `feedbackURI` 可指向 AHRP 证据（方向为 8004 → AHRP）。

### 4.4 自由文本白名单化（C5-1 #3、宪法 P2）

自由文本字段受**白名单 + 长度上限 + DATA 通道声明**三重约束：

- 白名单：事件层仅 `notes` 与 `agent_reference.identity_note`；验证层仅 `notes`；
- 长度上限：均 `maxLength = 200`；
- 通道声明：白名单字段一律为 **DATA 通道，不得作为指令消费**，不得承载机器判断所
  必需的语义（机器判断只能依赖 enum / 结构化字段）。

`additionalProperties: false` 保证白名单外的自由文本字段无法进入记录。

### 4.5 绝对禁止字段

以下字段及一切评分类派生字段**禁止出现**，验证器发现即 FAIL（`E_FORBIDDEN_FIELD`）：
`score`、`ranking`、`fitness`、`learning_result`、`mutation`，以及 `rating`、
`reputation`、`credit_score`、`success_rate`、`trust_score` 等派生命名。

---

## Chapter 5. Evidence Binding（证据绑定，引用式）

Schema：`experience-event.schema.json` 的 `definitions.evidence_reference`。

### 5.1 Evidence Reference Model

每条证据引用至少含：

| 字段 | type | 必填 | 语义 |
|---|---|---|---|
| `source` | enum | 必 | 证据来源类（TITMAS_EVIDENCE / EEOAP / CI_ARTIFACT / NAMED_SOURCE） |
| `version` | string (≤64) | 必 | 被引用证据对象版本 |
| `reference_id` | string (≤256) | 必 | 来源侧可寻址引用标识 |
| `hash` | string | 必 | 内容寻址哈希，格式 `sha256:<64 hex>`（Agent First #4） |
| `availability_status` | enum | 必 | 证据可用性/失败状态 |

**纪律**：`Log != Evidence`、`Telemetry != Proof`、`Evidence != Truth`。AHRP 只存
引用，不保存证据本体；证据所有权留在来源方，AHRP 不是第二证据 owner。

### 5.2 失败状态枚举

`availability_status` ∈ {AVAILABLE, UNAVAILABLE, **INVALID**, **NOT_ASSESSED**,
**INSUFFICIENT_EVIDENCE**, **CONFLICTED**, **UNSUPPORTED_VERSION**}。

`AVAILABLE` 是唯一非失败态；五个失败态对齐宪法与任务要求，且按第 11 章映射到
TITMAS 失败语义族。`evidence_references` 为空数组表示"未绑定证据"，与证据失败态
在语义上不同（不得混淆）。

---

## Chapter 6. Verification Model（验证模型）

Schema：`schema/verification.schema.json`（`additionalProperties: false`）。

### 6.1 字段

| 字段 | type | 必填 | 语义 |
|---|---|---|---|
| `verification_id` | string (≤128) | 必 | 验证记录唯一标识 |
| `verifier` | object | 必 | **谁验证**（具名必填，见 6.2） |
| `verification_type` | enum | 必 | 验证类型 |
| `verification_status` | enum | 必 | 验证状态 |
| `verified_at` | date-time | 必 | 验证时间 |
| `scope` | object | 必 | **验证什么**（范围声明，见 6.3） |
| `self_verification` | boolean | 必 | 自验证显式标记 |
| `authorization_effect` | const `"NONE"` | 必 | 机器强制 Verification ≠ Authorization |
| `notes` | string (≤200) | 可 | DATA 通道白名单自由文本 |

### 6.2 谁验证（WHO）

`verifier.verifier_name` **具名必填**（匿名验证不可表达）；`verifier_class` ∈
{DBOS, NAMED_VERIFIER, ORCHESTRATOR, SELF, INDEPENDENT_AGENT, ORGANIZATION,
HUMAN, SYSTEM_BENCHMARK}。**宪法纪律：自验证必须显式标记**——
`verifier_class=SELF` 当且仅当 `self_verification=true`，验证器强制一致性；消费方
必须把 `self_verification=true` 视为独立的、更弱的信号类。

**独立性分类（澄清，非语义升级）**：`SELF` 是唯一非独立验证类；其余各类均为
独立验证类。摘要计数与"要求独立验证"的查询过滤器只承认独立验证；纯 SELF 验证
作为弱信号保留、显式降级，**绝不**满足独立验证要求，也**绝不**计入摘要
`verified_events`。

### 6.3 验证什么（WHAT，范围声明）

`scope.subject_event_id` + `scope.subject_type`（EXPERIENCE_EVENT /
EVIDENCE_REFERENCE）标识被验对象；`scope.covered_aspect` ∈ {OCCURRENCE,
RESULT_STATUS, EVIDENCE_BINDING, FULL_EVENT, NOT_ASSESSED} 声明验证覆盖的方面。
**有界验证不得被读作整体事件验证。**

### 6.4 验证状态枚举

`verification_status` ∈ {**VERIFIED**, **PARTIALLY_VERIFIED**, **NOT_ASSESSED**,
**INVALID**, **CONFLICTED**}。无验证记录时事件级状态按 fail-closed 取
`NOT_ASSESSED`，**绝不假定为 VERIFIED**。

**强绑定（澄清）**：一个事件的有效验证状态**只能**来自其
`verification_references` 中显式列出的验证对象。禁止以弱关联（仅匹配 event_id /
仅匹配 agent / 仅匹配时间 / 扫描存储中全部验证记录 / 由验证方名称推断）自动升级
事件验证状态。`verification_references` 为空 → 有效状态 = `NOT_ASSESSED`；引用
无法解析、目标/agent/版本不匹配、版本不支持或状态非法 → 按 fail-closed 记为
`INVALID`；多条相互冲突 → `CONFLICTED`。未被引用的验证记录**不得**影响事件状态、
摘要计数、查询过滤或任何信任判断。

### 6.5 Verification ≠ Authorization

`authorization_effect` 恒为常量 `"NONE"`，机器强制：验证记录不授予任何能力、权限、
采用或背书（`VERIFICATION_NE_AUTHORIZATION=true`）。

---

## Chapter 7. Query Interface（查询接口）

参考实现：`query/`。默认行为贯彻 **Selective Disclosure First**：先摘要、后按需
下钻；摘要只返回**原始计数**，不返回任何派生比率或评分。

### 7.1 最小查询清单（对齐验收报告八字段）

1. 按 Agent 查历史 —— `query_events(identity_ref=...)`；
2. 按 Task Type 查经历 —— `query_events(task_type=...)`；
3. 按时间窗查 —— `query_events(time_start=..., time_end=...)`；
4. 按 Verification Status 过滤 —— `query_events(verification_status=...)`；
5. **摘要查询（默认）** —— `summary(identity_ref)`，返回 Experience Summary，含
   原始计数 `verified_events` 与 `total_events`，无派生比率/评分。`verified_events`
   **仅计独立验证**（不含纯 SELF）；另提供可机读拆分字段
   `independently_verified_events` / `self_verified_events` /
   `partially_verified_events` / `not_assessed_events` / `conflicted_events`；
6. 详细事件按需下钻 —— `get_event(event_id, capability="detail")`。

### 7.2 Agent First 发现与分页判据（承接 C5-1 #1 / #5，最保守口径）

- **#1 well-known 发现机制**：v0.1 为单机参考实现，**不定义网络发现机制**。
  机器可验收判据：两个 Schema 均携带可寻址 `$id` 与自描述 `$schema`，文档经
  `$id` 可被唯一定位；任何传输/发现协议属后续版本。
- **#5 过滤 + 分页**：v0.1 **不定义分页**。查询返回过滤后的全量摘要投影；
  分页参数、游标语义与排序稳定性列入后续版本，记入 §15 OPEN QUESTIONS。

### 7.3 摘要优先 + 按需下钻

`summary()` 与 `query_events()` 默认只给摘要投影（不含自由文本、不含证据本体）。
详情必须**显式** `capability="detail"` 且披露范围允许，否则 fail-closed。

**澄清：`capability="detail"` 是请求而非授权。** 纯字符串 `"detail"` 本身不构成
任何授权凭证；详情读取须经第 9 章披露真值表评估，未获授权时返回稳定机读错误码、
**绝不**静默返回详情。

**查询请求校验（澄清）**：一切查询参数在执行查询**之前**完成校验（agent 引用 /
版本、task/action 类型、验证状态、验证方类别、时间格式与顺序、披露范围、capability、
查询协议版本、limit）。非法参数不进入查询引擎、**绝不**映射为 `NO_RECORD`、**绝不**
向调用方暴露裸异常；统一返回第 11 章 `Q_*` 稳定错误码。仅当查询请求完全合法但确无
匹配历史时返回 `Q_NO_RECORD`。

**`Q_NO_RECORD` 的表达方式（澄清）**：`Q_NO_RECORD` 不通过错误信封（`ok=false`）
返回。查询请求完全合法但确无匹配时，响应为 `ok=true` 且
`null_semantics="NO_RECORD"`（§7.4 三态表达）——查询本身成功，只是没有结果。
`Q_NO_RECORD` 作为错误码予以保留，但 v0.1 参考实现使用三态 `null_semantics`
字段表达该状态。

### 7.4 空值三态（区分性必须可机读）

| 态 | 语义 |
|---|---|
| `NO_RECORD` | 从未有任何记录 |
| `WITHHELD` | 记录存在，但披露被保留（不可读内容，只知存在性计数） |
| `NOT_APPLICABLE` | 该问题对当前对象不适用（如对成功事件问 failure_category） |

三态互不相同、可机读（响应 `null_semantics` 字段）。`content_channel` 之外另设
`selective_disclosure.withheld_count` 表达"被保留的条数"。

### 7.5 DATA != INSTRUCTION（内容通道）

所有查询响应携带 `content_channel` 标记，区分 `structured_facts` 与
`restricted_text`。`restricted_text`（白名单自由文本）**绝不进入任何决策路径**；
消费方决策输入只能经 `query.consumer.structured_decision_inputs()` 获得，该函数
剥离 `restricted_text` 通道（见第 10 章）。

---

## Chapter 8. Identity and Version Binding（身份与版本绑定）

1. 每个事件绑定 `agent_reference`（身份薄指针）+ `agent_version`（具体执行主体版本），
   归属不悬空（宪法 §8 规则 3）；
2. **主体连续 ≠ 版本连续**；新版本**不自动继承**旧版本历史（宪法 §8 规则 1/2）；
3. **身份连续性 fail-closed 默认**（承接 C2-3）：查询摘要按 `agent_version` 分组计数，
   **禁止跨版本合并**出单一综合计数/综合分；消费方未显式声明继承处置时不得假定继承；
4. 归属处置枚举（inherit / freeze / fork / invalidate）为策略要点级，字段级定义属
   后续工作，记入 OPEN QUESTIONS。

---

## Chapter 9. Selective Disclosure（选择性披露）

1. `disclosure.disclosure_scope` ∈ {PUBLIC, FEDERATED, RESTRICTED, **WITHHELD**}；
2. 支持 `expires_at`（可过期）、`revoked`（可撤销）与 `declared_by`（声明者）——
   披露范围可声明、可过期、可撤销；
3. **fail-closed**：未声明披露范围按 WITHHELD 处理，不得默认全量可读；
4. WITHHELD 事件只在摘要中贡献 `withheld_count`，**内容绝不返回**；
5. 消费方获得的是完成当前判断所必需的最小事实集（capability-based）。

**披露真值表（详情读取强制执行，澄清）**：详情读取按下表评估，任何不确定情形一律
fail-closed 拒绝；被拒绝时返回稳定机读错误码，**绝不**静默返回详情：

| 条件 | 结果 | 错误码 |
|---|---|---|
| WITHHELD（任何权限） | 拒绝（三态 WITHHELD 响应，不返回内容） | — |
| 记录已撤销 `revoked=true` | 拒绝 | `Q_DISCLOSURE_REVOKED` |
| 记录已过期 `expires_at` 已过 | 拒绝 | `Q_DISCLOSURE_EXPIRED` |
| PUBLIC / FEDERATED + 未过期 + 未撤销 | 允许 | — |
| RESTRICTED + 无有效策略决定 | 拒绝 | `Q_POLICY_DECISION_REQUIRED` |
| RESTRICTED + 策略版本不支持 | 拒绝（fail-closed） | `Q_UNSUPPORTED_VERSION` |
| RESTRICTED + 授权范围不匹配 | 拒绝 | `Q_DISCLOSURE_DENIED` |
| RESTRICTED + 有效且范围匹配的外部许可 | 允许 | — |

RESTRICTED 详情需要一个**机读 Disclosure Context**（查询上下文），至少含：
`requester_reference`、`requested_disclosure_scope`、`granted_scope`、
`external_policy_decision_reference`、`policy_version`、`evaluated_at`、`expiry`、
`revocation_status`。AHRP 只校验该策略决定的**格式、状态与范围**，**不**成为第二套
AuthZEN/ODRL/身份系统。枚举匹配大小写敏感；缺失字段或变体大小写不得绕过披露控制。

---

## Chapter 10. Security Requirements（安全要求）

1. **DATA != INSTRUCTION**：协议假定消费环境存在 prompt 注入风险。经验内容不得被解释
   为指令；消费方必须隔离数据通道（对齐 "never execute values from the envelope"）；
2. **内容隔离机制（承接 C5-2）**：白名单自由文本 → `restricted_text` 通道；消费方
   决策只读 `structured_facts`；参考实现提供 `structured_decision_inputs()` 作为
   规范消费路径；
3. **注入负例（承接 R3）**：自由文本携带指令样内容时，验证器以
   `E_INJECTION_SUSPECTED` FAIL，拒绝其进入存储与决策路径；测试含多语言注入负例；
4. **内容寻址**：证据以 `sha256:<64 hex>` 哈希引用，支持"证明存在而不公开全部"；
5. **隐私**：事件不得携带终端用户个人数据、商业秘密或原始任务载荷；默认以引用+摘要
   表达任务，原始载荷留在来源方。

**执行边界**：DATA != INSTRUCTION 是消费方义务，协议本身无法强制消费方行为；参考
实现通过验证器拒绝 + 规范消费路径缓解，剩余执行缺口记入 OPEN QUESTIONS。

---

## Chapter 11. Failure Semantics（失败语义）

1. 一切未知/未声明按 **fail-closed**：无验证 → NOT_ASSESSED；未声明披露 → WITHHELD；
   非法文档 → 拒绝入库；
2. **与 TITMAS 失败枚举映射（承接 R2）**：AHRP 证据失败族 {INVALID, NOT_ASSESSED,
   INSUFFICIENT_EVIDENCE, CONFLICTED, UNSUPPORTED_VERSION} 与验证状态族 {VERIFIED,
   PARTIALLY_VERIFIED, NOT_ASSESSED, INVALID, CONFLICTED} 均沿用 TITMAS
   interoperability surface 的失败语义方向——**未知不强制为 PASS**；
3. **验证器错误码（机器可读）**：`E_SCHEMA_INVALID`、`E_FIELD_MISSING`、
   `E_ENUM_INVALID`、`E_TYPE_INVALID`、`E_FORMAT_INVALID`、`E_CONSTRAINT_VIOLATION`、
   `E_FORBIDDEN_FIELD`、`E_EVIDENCE_REF_MALFORMED`、`E_INJECTION_SUSPECTED`；
4. 输出为 PASS/FAIL；FAIL 时返回机器可读错误码集合。`Validator PASS != 实现合规`。
5. **查询接口错误码（机读，澄清）**：查询接口对非法请求与披露拒绝返回稳定 `Q_*`
   错误码，至少含：`Q_INVALID_ENUM`、`Q_INVALID_TIME_FORMAT`、`Q_INVALID_TIME_RANGE`、
   `Q_INVALID_REFERENCE`、`Q_UNSUPPORTED_VERSION`、`Q_DISCLOSURE_DENIED`、
   `Q_DISCLOSURE_EXPIRED`、`Q_DISCLOSURE_REVOKED`、`Q_POLICY_DECISION_REQUIRED`、
   `Q_NO_RECORD`、`Q_INVALID_PARAM`（limit/分页类参数校验失败；此前误用
   `Q_INVALID_REFERENCE`）。非法参数**绝不**映射为 `Q_NO_RECORD`；`Q_NO_RECORD`
   仅在请求完全合法但确无匹配历史时返回；查询接口**绝不**向调用方暴露裸异常。
   `Q_NO_RECORD` 在 v0.1 参考实现中不经错误信封返回，而以 `ok=true` +
   `null_semantics="NO_RECORD"` 的三态表达（见 §7.3/§7.4）；该错误码保留，供后续
   版本使用。

---

## Chapter 12. Extension Rules（扩展规则）

1. **semver**：`schema_version` 遵循语义化版本；破坏性变更升主版本，向后兼容新增升
   次版本；
2. **自描述**：Schema 以 JSON Schema draft-07 + `$schema` + `$id` 自描述
   （Agent First #2）；
3. **枚举扩展**：新增 enum 值须经 SPEC 修订；不得以自由文本绕过枚举；
4. **字段扩展**：`additionalProperties: false` 下，新增字段须修订 Schema 并升版本；
   禁止字段清单（第 4.5）永不开放；
5. **状态机**：本 SPEC 状态走 `PROPOSED → APPROVED → IMPLEMENTED → RETIRED`；
   文档状态与参考实现状态分离、不自动传播。

---

## Chapter 13. Non-goals（非目标，不可妥协）

AHRP 永远不做（继承宪法 §9 七条 + 任务禁区清单）：

1. Agent 排名（Ranking / TOP 榜）；
2. Agent 评分平台（综合信用分 / 数值评级 / Reputation Score）；
3. Agent 社交网络（关系图 / 关注 / 主页）；
4. Agent Marketplace（市场 / 交易撮合 / 上架）；
5. 新身份协议（Identity Provider，不替代 DID / FDO，不签发身份）；
6. 新通信 / 工具调用协议（Tool Calling Protocol，不替代 MCP / A2A）；
7. 中央数据库（Federated 模式）。

**额外永久禁区**（任务定位）：Payment、Autonomous Learning、Digital Life Engine、
Evolution Engine、Digital Life Protocol、Agent 征信评分、Agent 自动成长。

触碰以上任一条的任何扩展，保持 `REVIEW_REQUIRED`，须走 ADR + 人工批准，不得以
"实现细节"名义渗入协议层。

---

## Chapter 14. Examples（示例）

见 `examples/`（5 组 fixtures，全部 SYNTHETIC_ONLY）：

1. `01-*` 成功且已验证事件 + VERIFIED 验证记录；
2. `02-*` 证据不足事件（INSUFFICIENT_EVIDENCE，验证 NOT_ASSESSED）；
3. `03-*` 版本冲突事件（UNSUPPORTED_VERSION，result FAILURE）；
4. `04-*` 验证冲突事件 + CONFLICTED 验证记录；
5. `05-*` 选择性披露查询样例（摘要优先 + 按需下钻 + WITHHELD fail-closed）与
   WITHHELD 事件。

最小可运行演示见 `demo/run_demo.py`；自动化测试见 `tests/`。

---

## Chapter 15. OPEN QUESTIONS（开放问题，含冲突处理记录）

按任务纪律：发现输入间冲突不私自改架构，记录于此并取最保守实现。

1. **怀疑者四问（验收报告 §8，未在 v0.1 求解，仅以最保守实现兜底）**：
   (a) verifier 准入/质押/经济责任未定义——v0.1 仅要求具名 + 自验证显式标记；
   (b) 幸存者偏差检测——v0.1 仅提供可区分空值三态，不提供全披露证明；
   (c) 历史继承交易防面具化——v0.1 采用跨版本计数不合并的最保守策略；
   (d) 冷启动——v0.1 不定义首条可验证事件的产生方。
2. **C1-3（cockpit 待决）**：FDO 是否显式命名为身份来源；本 SPEC 沿用
   "DBOS or explicitly named source"，不自行命名。
3. **owner_ref=NOT_ASSIGNED**：Closure F1-1 建议 SPEC 启动前指派 Owner。
4. **时间锚定可信源**：`occurred_at` 若为自签时间戳可回填，则价值存疑（验收报告
   怀疑者条件）；可信时间源机制未定义。
5. **身份连续性字段级处置**（inherit/freeze/fork/invalidate）未定义字段级 Schema。
6. **`success_pattern` / `limitation` 是否保留**：验收报告 §6.2 存在跨角色分歧
   （建议"保留但须可由 Events 确定性重推导"，仅建议非决定）；v0.1 **取最保守**，
   不引入任何派生 pattern 字段，limitation 语义由 FAILURE 事件 + failure_category
   表达，避免 Goodhart 化与评分化风险。
7. **DATA != INSTRUCTION 执行缺口（Closure R3）**：协议无法强制消费方行为，需后续
   机器可验证内容标记 + 升级 cockpit ADR。
8. **查询分页（C5-1 #5）**：v0.1 显式不定义分页（见 §7.2）；分页参数、游标与
   排序稳定性语义列入后续版本。
9. **well-known 网络发现机制（C5-1 #1）**：v0.1 仅以 Schema `$id` 可寻址为判据
   （见 §7.2）；网络级发现机制不定义。

---

## Non-claims（非声明，禁止语义升级）

```text
AHRP_SPEC_STATUS=PROPOSED
AHRP_REFERENCE_IMPLEMENTATION_STATUS=IMPLEMENTED
AHRP_IS_HISTORICAL_EXPERIENCE_PROTOCOL=true
AHRP_IS_RATING_SYSTEM=false
AHRP_IS_RECOMMENDATION_SYSTEM=false
AHRP_IS_LEARNING_SYSTEM=false
REFERENCE_IMPLEMENTATION_NE_STANDARD=true
VALIDATOR_PASS_NE_COMPLIANCE=true
SPECIFICATION_NE_PUBLISHED_STANDARD=true
PRODUCTION_READY=false
NEW_TRUTH_SOURCE_CREATED=false
SECOND_EVIDENCE_OR_VERIFICATION_OWNER_CREATED=false
NEW_IDENTITY_PROTOCOL_CREATED=false
ADR_001_APPROVED_BOUNDARY_CHANGED=false
CONSTITUTION_APPROVED_BOUNDARY_CHANGED=false
```
