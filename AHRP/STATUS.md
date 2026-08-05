# AHRP v0.1 — STATUS

- Date recorded: `2026-08-05`（trust-boundary hardening round r3：四项信任边界修复 + 回归测试后重测；last update 2026-08-05）
- Scope: 本文件只记录 AHRP v0.1 参考实现的工件存在性与测试证据；
  文档状态（PROPOSED）与实现状态（IMPLEMENTED）分离记录，不自动传播。

## Document Status（文档状态）

| 工件 | 状态 | 说明 |
|---|---|---|
| `spec/AHRP_SPEC_v0.1.md` | `PROPOSED` | 规范提案，伴随参考实现；**非已发布标准** |
| `schema/*.schema.json` | `PROPOSED` | JSON Schema draft-07（参考实现使用） |
| 参考实现（validator / query / demo / tests） | `IMPLEMENTED` | 纯标准库、内存态、单机；`SYNTHETIC_ONLY=true` |

## Implementation Status Keys（实现状态键）

以下四个键初始为 `false`；**仅当全部自动化测试实际通过后**才置 `true`。
置 `true` 的测试证据见下一节。

```text
AHRP_SPEC_EXISTS=true
AHRP_SCHEMA_EXISTS=true
AHRP_VALIDATOR_EXISTS=true
AHRP_IMPLEMENTATION_EXISTS=true
```

## Test Evidence（测试通过证据）

命令（在 `AHRP/` 根目录执行，Python 3 标准库，无第三方依赖）：

```bash
python3 -m unittest discover
```

输出摘要（真实运行结果，含五项缺陷修复、独立审查 r2 修复与 r3 信任边界加固后
的新增回归测试）：

```text
Ran 208 tests in 0.016s

OK
```

覆盖：Schema Test（`tests/test_schema.py`）、Validator Test
（`tests/test_validator.py`）、Query Test（`tests/test_query.py`）、Failure Case
Test（`tests/test_failure_cases.py`，含注入负例与禁止字段负例）、Remediation
Test（`tests/test_remediation.py`，43 项：选择性披露真值表、验证↔事件强绑定、
自验证/独立验证分离、查询请求校验与稳定错误码、安全回归）、Independent-Review
r2 Test（`tests/test_audit_r2.py`，37 项：不可哈希输入类型守卫、验证前置校验门、
独立性洗白防护、NOT_ASSESSED 过滤、WITHHELD 辅助守卫、时钟注入拒绝、
披露范围过滤、limit 错误码、畸形过期 fail-closed）、Trust-Boundary r3 Test
（`tests/test_audit_r3.py`，40 项：披露上下文防伪与 resolver fail-closed、
统一披露守卫、agent+version 强制绑定、NOT_ASSESSED 不授予独立性、查询稳定
错误码回归、真值门一致性）。原有测试全部保留、未被删除/跳过/削弱；受新语义
影响的夹具仅按新规则补充 resolver 注入与完整 agent/version 绑定。
缺陷根因、改动清单与修复前后复现证据见
`docs/review/AHRP-v0.1-remediation-record.md`。

Demo 可运行性证据：

```bash
python3 demo/run_demo.py
# 输出以 "AHRP v0.1 minimal demo -- SYNTHETIC_ONLY=true" 开始，
# 以 "Demo complete. SYNTHETIC_ONLY=true; no real agents, no real evidence." 结束，
# 退出码 0。
```

## Truth Boundaries（真值边界，禁止语义升级）

```text
REFERENCE_IMPLEMENTATION_NE_STANDARD=true
PRODUCTION_READY=false
VALIDATOR_PASS_NE_COMPLIANCE=true
SPECIFICATION_NE_PUBLISHED_STANDARD=true
SYNTHETIC_ONLY=true
PHYSICAL_OR_REAL_AGENT_VALIDATED=false
AHRP_REAL_WORLD_ADOPTION_VALIDATED=false
AHRP_PRODUCTION_READY=false
AHRP_STANDARD_PUBLISHED=false
AHRP_INDEPENDENT_ADVERSARIAL_REVIEW=PENDING_R3
NEW_TRUTH_SOURCE_CREATED=false
SECOND_EVIDENCE_OR_VERIFICATION_OWNER_CREATED=false
NEW_IDENTITY_PROTOCOL_CREATED=false
AHRP_IS_HISTORICAL_EXPERIENCE_PROTOCOL=true
AHRP_IS_RATING_SYSTEM=false
AHRP_IS_RECOMMENDATION_SYSTEM=false
AHRP_IS_LEARNING_SYSTEM=false
EXISTING_FILES_MODIFIED=true
```

## 声明

本目录为 AHRP v0.1 **参考实现**：**非正式标准**、**不构成生产就绪声明**、
**不构成合规认证依据**。全部数据为合成数据，不涉及真实智能体、真实证据、网络或
任何可执行生产系统。任何外部采用、符合性或标准化声明均需另行独立授权。
