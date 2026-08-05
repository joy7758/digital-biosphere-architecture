# AHRP — Agent History Record Protocol（智能体历史记录协议）v0.1

> **AHRP v0.1 is a Historical Experience Protocol. It is NOT a Rating /
> Recommendation / Learning System.**
>
> 本目录是 AHRP v0.1 的**参考实现**（reference implementation）。文档状态
> `PROPOSED`，实现状态 `IMPLEMENTED`。参考实现存在不等于标准发布：
> `REFERENCE_IMPLEMENTATION_NE_STANDARD=true`、`PRODUCTION_READY=false`。

## 这是什么

AHRP（Agent History Record Protocol）回答一个问题：**这个智能体过去经历过什么？**
（History）。身份机制（DID / FDO / POP / A2A AgentCard）回答"这是谁"（Identity），
但没有任何开放协议以结构化、可验证、联邦化的方式回答"它经历过什么"。AHRP 填补这
一缺口：以 **Experience Event** 为核心对象，引用式绑定证据与验证，支持选择性披露
查询。

## 架构定位

- AHRP 是位于 **TITMAS 之上**的独立协议层（历史经验层），**不是 TITMAS v2**，不
  与其合并命名；
- AHRP 以**引用方式**对接 TITMAS 侧的证据、验证与身份对象：不内嵌证据本体，不创建
  第二套 Identity / Evidence / Verification owner；
- 身份来源沿用 "DBOS or explicitly named source"；AHRP 不签发、不解析、不管理标识符。

依据（均为 cockpit 已批准/已评审文档）：

1. `adr/ADR-001-AHRP-architectural-position.md`（APPROVED）
2. `docs/constitution/AHRP_CONSTITUTION_v0.1.md`（APPROVED）
3. `architecture/AHRP-architecture-review-closure-v0.1.md`（REVIEWED）
4. `architecture/AHRP-agent-acceptance-report-v0.1.md`（REVIEWED）

## 永久禁区（Non-goals）

AHRP 永远不做：Ranking / TOP 榜、Reputation Score / 综合信用分、Agent 社交、
Marketplace、Payment、Identity Provider、Tool Calling Protocol、Autonomous
Learning、Digital Life Engine、Evolution Engine、Digital Life Protocol、Agent
排名 / 商店 / 征信评分 / 自动成长。Schema 中 `score`、`ranking`、`fitness`、
`learning_result`、`mutation` 等字段出现即验证 FAIL。

## 目录结构

```
AHRP/
├── README.md                  # 本文件
├── STATUS.md                  # 状态键与测试证据
├── spec/
│   └── AHRP_SPEC_v0.1.md      # 规范（PROPOSED，14 章 + OPEN QUESTIONS）
├── schema/
│   ├── experience-event.schema.json   # 核心对象 Schema（draft-07）
│   └── verification.schema.json       # 验证记录 Schema（draft-07）
├── validator/                 # 参考验证器（Python 3 纯标准库）
├── query/                     # 查询接口参考实现（摘要优先 / 三态空值 / 内容通道）
├── examples/                  # 5 组合成 fixtures（SYNTHETIC_ONLY）
├── demo/
│   └── run_demo.py            # 最小演示（全程合成数据）
└── tests/                     # unittest 自动化测试（208 项）
```

## 运行（Python 3 标准库，无第三方依赖）

```bash
# 在 AHRP/ 根目录执行：
python3 -m unittest discover        # 全部自动化测试
python3 demo/run_demo.py            # 最小演示
```

## 核心机制速览

- **Machine Enumerability First**：`result_status` / `task_type` / `action_type` /
  `failure_category` / 各失败状态全部 enum 化；
- **Selective Disclosure First**：查询默认返回 Experience Summary（原始计数
  `verified_events` / `total_events`，无派生比率），详情显式下钻；`capability="detail"`
  仅为请求而非授权，详情按披露真值表（范围 × 过期 × 撤销 × 外部策略决定）fail-closed
  评估，未获授权返回稳定 `Q_*` 错误码；
- **验证↔事件强绑定**：事件有效验证只来自其 `verification_references` 显式列出的验证
  对象；无引用 → `NOT_ASSESSED`；弱关联（仅 event_id/agent/时间扫描）被禁止；
- **自验证/独立验证分离**：`verified_events` 仅计独立验证；纯 SELF 作为弱信号保留并
  显式降级，另提供 `independently/self/partially/not_assessed/conflicted` 拆分计数；
- **空值三态**：`NO_RECORD` / `WITHHELD` / `NOT_APPLICABLE`，可机读、可区分；
- **DATA != INSTRUCTION**：自由文本白名单化（≤200 字符），仅走 `restricted_text`
  通道；注入负例在验证器即被拒绝（`E_INJECTION_SUSPECTED`）；
- **身份连续性 fail-closed**：摘要按 agent_version 分组，禁止跨版本合并；
- **Verification ≠ Authorization**：`authorization_effect` 恒为 `"NONE"`（机器强制）；
  自验证必须显式标记（`self_verification` + `verifier_class=SELF` 一致性强制）。

## 真值边界

本目录是**参考实现，非正式标准，不构成生产就绪声明**。全部测试数据为合成数据
（`SYNTHETIC_ONLY=true`），不涉及真实智能体、真实证据或网络。状态键见
`STATUS.md`。
