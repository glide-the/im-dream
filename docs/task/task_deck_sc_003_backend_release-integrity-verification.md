# task_deck_sc_003_backend_release-integrity-verification

## 1. 任务标题

发布端实际字节 SHA-256、RFC 8785 Manifest Hash 与签名验证

## 2. 唯一映射与 Domain

| 字段 | 值 |
|---|---|
| Task ID | `TASK-DECK-SC-003` |
| 来源 Issue | `DECK-SC-003` |
| Paperclip TaskDesign Issue | [SUO-275](/SUO/issues/SUO-275) |
| Canonical design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1、§4.2.3 |
| Domain | `backend` |
| 优先级 | P0 |
| 下游 Stage 映射键 | `stage4.supply_chain.DECK-SC-003` |

## 3. 任务目标与非目标

在 release 发布边界对不可变分发字节计算规范 SHA-256，对 RFC 8785 规范化 manifest 计算 hash，并使用 `TASK-DECK-SC-002` verifier 验证 DSSE/Sigstore bundle、publisher identity、时间与撤销状态。验证结果与 release 原子、不可变关联。

非目标：不信任目录、分支、版本名或 `latest`；不自行实现 RFC 8785/密码学；不负责 runtime 二次摘要、留存状态机或 legacy UI；不在验证失败时保留 production-ready。

## 4. 实现步骤

1. 定义 release integrity 字段与不可变约束：`artifact_digest`、`artifact_size_bytes`、`deck_plugin_manifest_hash`、signature metadata、publisher identity、verification status/time/verifier/policy revision。
2. 从最终实际分发 byte stream 计算 `sha256:<64-lowercase-hex>`；打包后任何字节变化必须产生不同 digest。
3. 通过安全评审的 RFC 8785 库 canonicalize manifest，再计算 SHA-256；为数字、Unicode、键顺序和空白建立合规 fixtures。
4. 构造规范签名 payload，证明 bundle 同时绑定 `artifact_digest + deck_plugin_manifest_hash + publisher_identity`；调用 SC-002 verifier 完成 root/identity/algorithm/time/revocation 检查。
5. 在单一事务/提交边界持久化 release + verification；同一 release 验证结果不可原地改写，重试必须幂等。
6. 所有失败输出结构化 reason code 并保持 release non-production；未知撤销/离线过期同样拒绝。
7. 记录脱敏审计：只保存 signer 摘要、proof ref、policy/verifier revision，不内联完整 bundle 或制品。
8. 补齐正向、篡改、过期、撤销、unknown、离线和并发原子性测试，生成可复核证据。

## 5. 涉及文件与写入边界

### 5.1 允许修改闭集

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/deck_plugin.py` | 修改 | 仅追加 release integrity、verification 与不可变字段 |
| `backend/services/deck_plugin/artifact_integrity.py` | 新建 | 实际字节 digest、RFC 8785 canonicalization 和 payload 构造 |
| `backend/services/deck_plugin/release_service.py` | 修改 | 仅集成发布验证与 release 原子关联 |
| `backend/services/deck_plugin/manifest_validator.py` | 修改 | 仅接入规范 manifest hash/禁止可变引用 |
| `backend/services/deck_plugin/signature_verifier.py` | 修改 | 仅接入 SC-002 已冻结 verifier 合同，不放宽策略 |
| `backend/services/errors/error_registry.py` | 新建/修改 | 仅增加本 task 的结构化错误码 |
| `backend/database.py` | 修改 | 仅追加 release verification 字段/约束/审计 |
| `backend/tests/test_deck_plugin_release_integrity.py` | 新建 | digest、RFC 8785、签名与事务测试 |
| `output/evidence/deck-plugin/supply-chain/DECK-SC-003/**` | 生成 | 测试矩阵、release/policy hash 与日志摘要 |

### 5.2 禁止修改范围

- 未列出的实现/测试文件、依赖/锁文件、部署配置和前端；
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`；
- 对解包目录、branch、URL 或标签计算 digest，或接受非规范 `sha256`；
- 自行编写 RFC 8785/密码学原语、跳过签名覆盖项、unknown 状态 warn-only；
- 修改 runtime、retention、purge 或 legacy 迁移逻辑。

## 6. 输入 / 输出与证据格式

输入：不可变打包 byte stream、manifest JSON、signature bundle ref、publisher identity、SC-002 active/draft policy revision、release identity。

输出：不可变 `ReleaseVerificationRecord`，至少包含 `artifact_digest`、`artifact_size_bytes`、`deck_plugin_manifest_hash`、`signature_scheme`、`signature_bundle_ref`、`publisher_identity`、`verification_status`、`verified_at`、`verifier_version`、`trust_policy_revision`、`reason_code|null`。

错误至少包含 `ARTIFACT_SIGNATURE_INVALID`、`ARTIFACT_DIGEST_MISMATCH`、`ARTIFACT_TRUST_ROOT_UNKNOWN`、`ARTIFACT_VERIFICATION_EXPIRED`，并继承 SC-002 的 identity/algorithm/revocation/cache/time reason codes。

证据每例包含 `test_case_id`、fixture SHA-256、expected/actual status、reason code、release ID、run ID、commit SHA、日志摘要链接和 policy revision。

## 7. 依赖、并行性与 StagePlanner 输入

- 直接前置：`TASK-DECK-SC-002`；基线合同：`task_deck_001_backend_manifest-model.md`、`task_deck_002_backend_runtime-lock.md`。
- 下游：`TASK-DECK-SC-004`、`TASK-DECK-SC-005`、`TASK-DECK-SC-007`、`TASK-DECK-SC-009`。
- 可并行性：model/migration、artifact digest/RFC fixtures、release integration 可在 verifier interface 冻结后并行；最终集成必须使用同一 policy revision。
- 冻结点：release verification record、canonical payload、reason codes 和原子性测试通过；SC-002 production policy 未签署时只能输出 `verified_nonproduction`/non-production 结果，不得 production-ready。
- Execute readiness：SC-002 verifier API/reason codes 已冻结；最终 byte stream 边界、RFC 8785 依赖、事务边界和 fixtures 已确认。

## 8. 验收条件

- [ ] `artifact_digest` 只对实际分发字节计算并严格输出 `sha256:<64-lowercase-hex>`。
- [ ] manifest hash 来自标准 RFC 8785 canonical JSON；Unicode、数值、键顺序 fixtures 通过。
- [ ] 签名严格绑定 digest + manifest hash + publisher identity，并完成 root/time/revocation 验证。
- [ ] 验证状态、时间、verifier 和 policy revision 与 release 原子、不可变关联。
- [ ] 字节/manifest/signature/replay/截断/unknown root/过期/撤销/离线过期均检测并拒绝。
- [ ] 事件/日志只存脱敏 signer 摘要和 proof ref。
- [ ] 生产就绪服务端判定未在本 task 中被提前放开。

## 9. 最小测试 / 验证命令

```bash
backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_release_integrity
backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_manifest backend.tests.test_deck_plugin_lock
backend/.venv/bin/python -m compileall -q backend/models/deck_plugin.py backend/services/deck_plugin/artifact_integrity.py backend/services/deck_plugin/release_service.py backend/services/deck_plugin/manifest_validator.py
rg -n 'ARTIFACT_(SIGNATURE_INVALID|DIGEST_MISMATCH|TRUST_ROOT_UNKNOWN|VERIFICATION_EXPIRED)' backend output/evidence/deck-plugin/supply-chain/DECK-SC-003
git diff --check -- backend/models/deck_plugin.py backend/services/deck_plugin backend/services/errors/error_registry.py backend/database.py backend/tests/test_deck_plugin_release_integrity.py
```

## 10. 完成信号与回滚

完成信号：所有正/负向 fixtures 与事务测试通过，release verification 记录不可变且证据可点击。SC-001/SC-002 签署或独立复审未完成时，完成信号只能表示技术 task 完成，不能表示 production-ready。

回滚：暂停新发布并回退到最近稳定 verifier adapter/release pipeline；保留已冻结 release 的原 digest、verification 和 proof。不得通过回滚跳过校验、改写历史结果或删除失败证据。

## 11. 风险与 Clarification

| 风险/澄清 | 处理 | Owner / action |
|---|---|---|
| “实际分发字节”边界不唯一 | 以客户端下载/物化的最终 byte stream 为唯一输入 | Marketplace/制品平台 owner：批准打包与字节边界 |
| RFC 8785/签名依赖不兼容 | 停止自研替代，保留 fail-closed | 安全 owner：批准标准库/版本或 request changes |
| 发布事务无法原子关联 proof | 禁止产生 verified release | Backend owner：提供事务/outbox 方案并留并发测试证据 |

## 12. Gate 声明

发布端验证是双路径链路的前半段，不单独构成 production Gate。未知算法、identity/root、撤销状态或离线缓存 freshness 一律拒绝；独立 reviewer approve 前不得标记 `production_ready`。
