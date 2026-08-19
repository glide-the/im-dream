# task_deck_sc_004_backend_runtime-digest-receipt

## 1. 任务标题

Runtime 物化后二次摘要校验与 Load Receipt 绑定

## 2. 唯一映射与 Domain

| 字段 | 值 |
|---|---|
| Task ID | `TASK-DECK-SC-004` |
| 来源 Issue | `DECK-SC-004` |
| Paperclip TaskDesign Issue | [SUO-275](/SUO/issues/SUO-275) |
| Canonical design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1、§4.2.3 |
| Domain | `backend` |
| 优先级 | P0 |
| 下游 Stage 映射键 | `stage4.supply_chain.DECK-SC-004` |

## 3. 任务目标与非目标

在 ClaudeAgent runtime 物化/缓存命中后，重新对实际制品字节计算 SHA-256，与冻结的 `DeckRuntimePluginLock.artifact_digest` 比对，并把结果不可变绑定到 `RuntimeLoadReceipt`。只有每个 required artifact 都验证一致，session 才可进入 `loaded`。

非目标：不重新查询或信任 marketplace 标签/当前状态；不重新裁决 publisher signature；不把 node cache 当权威留存；不改变 pool/node/session readiness 设计；不处理 purge。

## 4. 实现步骤

1. 扩展 runtime materialization/load receipt 模型，记录 lock/release/policy/verifier 引用和 runtime 实算 digest。
2. 下载或 cache 命中后，从将被加载的实际 byte stream 计算 SHA-256；禁止使用 cache metadata 代替重算。
3. 常量时间/严格格式比对 runtime digest 与 lock digest；不一致、缺失、算法不支持或读取不完整时立即拒绝加载并审计。
4. 校验发布端冻结状态：只消费 lock 中绑定的 `verification_status`、`trust_policy_revision` 和 proof ref；若状态非 verified/未知则 fail closed，不在线重新信任标签。
5. 原子生成 `RuntimeLoadReceipt`，逐项记录 `runtime_verified_digest`、status、time、node/session/cache source 和 reason code；receipt 与实际 session 绑定且不可复用到另一 session。
6. required 项全部一致后才写 `session_loaded`；任一失败不得进入 `loaded/running`，并返回 `ARTIFACT_DIGEST_MISMATCH` 或更具体 reason。
7. 补齐直接下载、cache hit、截断/替换、并发、重试和 receipt 不可变测试；记录 runtime owner 审批所需证据。

## 5. 涉及文件与写入边界

### 5.1 允许修改闭集

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/runtime_plugin.py` | 新建/修改 | 仅追加 runtime verification 与 load receipt 字段 |
| `backend/services/runtime_plugin/materialization_manager.py` | 新建/修改 | 仅在实际物化/cache byte stream 上重算 digest |
| `backend/services/runtime_plugin/reconcile_service.py` | 新建/修改 | 仅集成 fail-closed 校验与 receipt 生成 |
| `backend/services/errors/error_registry.py` | 修改 | 仅增加 runtime digest/verification 错误码 |
| `backend/database.py` | 修改 | 仅追加 runtime verification/receipt 字段与不可变约束 |
| `backend/tests/test_runtime_artifact_digest.py` | 新建 | 下载/cache/篡改/receipt 测试 |
| `output/evidence/deck-plugin/supply-chain/DECK-SC-004/**` | 生成 | runtime 校验矩阵、receipt 摘要与日志引用 |

### 5.2 禁止修改范围

- 未列出的实现/测试路径、依赖/锁文件、部署配置和前端；
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`；
- 在线重新信任 marketplace 标签、跳过 cache 内容重算、以 warn-only 接受不一致；
- 修改 release 签名验证、CAS/冷存储、retention/purge 或 Workflow Run 业务状态机；
- 伪造 `session_loaded`、跨 session 复用 receipt 或覆盖历史 receipt。

## 6. 输入 / 输出与证据格式

输入：冻结 `DeckRuntimePluginLock`、发布端 `ReleaseVerificationRecord` 引用、物化后的 byte stream、runtime node/session/cache identity。

输出：逐项 `RuntimeLoadReceipt`，至少包含 `runtime_load_receipt_id`、`runtime_node_id`、`agent_session_id`、`runtime_plugin_lock_id`、`artifact_digest`、`runtime_verified_digest`、`runtime_verification_status`、`runtime_verified_at`、`cache_source`、`trust_policy_revision`、`reason_code|null`。

证据每例包含 `test_case_id`、lock/receipt/session ID、expected/actual digest、source（download/cache）、status/reason、run ID、commit SHA、日志摘要链接。日志不得内联制品或完整签名包。

## 7. 依赖、并行性与 StagePlanner 输入

- 直接前置：`TASK-DECK-SC-003`；基线合同：`task_deck_002_backend_runtime-lock.md`、`task_deck_008_backend_reconcile-load-receipt.md`。
- 下游：`TASK-DECK-SC-007`；同时向 `TASK-DECK-SC-009` 提供 production 拒绝状态。
- 可并行性：可与 `TASK-DECK-SC-005` 并行；model/DB、materialization、negative tests 可在 receipt schema 冻结后并行。
- 冻结点：runtime owner 对“发布冻结结果 + runtime 实字节重算 + receipt/session 绑定”路径具名 `approve`；所有 mismatch/cache 篡改测试通过。
- Execute readiness：SC-003 record/lock 字段稳定；DECK-008 materialization/receipt baseline 可用；实际加载 byte stream 边界、node/session identity 和测试 cache adapter 已明确。

## 8. 验收条件

- [ ] 物化或 cache 命中后均对实际字节重新计算 SHA-256。
- [ ] 结果与 lock digest 不一致、缺失或算法未知时拒绝加载并审计。
- [ ] receipt 的 runtime digest/status/time 与 lock、node、session 一致且不可变。
- [ ] required 项全部验证前不得进入 `loaded/running`。
- [ ] runtime 不重新查询/信任 marketplace 标签，只消费冻结验证结果。
- [ ] 下载/cache 正反例、截断/替换、重试、并发和 receipt 复用攻击测试通过。
- [ ] runtime owner 签署绑定证据 hash；独立复审前不输出 production-ready。

## 9. 最小测试 / 验证命令

```bash
backend/.venv/bin/python -m unittest backend.tests.test_runtime_artifact_digest
backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_lock
backend/.venv/bin/python -m compileall -q backend/models/runtime_plugin.py backend/services/runtime_plugin/materialization_manager.py backend/services/runtime_plugin/reconcile_service.py
rg -n 'runtime_verified_digest|runtime_verification_status|ARTIFACT_DIGEST_MISMATCH|session_loaded' backend output/evidence/deck-plugin/supply-chain/DECK-SC-004
git diff --check -- backend/models/runtime_plugin.py backend/services/runtime_plugin backend/services/errors/error_registry.py backend/database.py backend/tests/test_runtime_artifact_digest.py
```

## 10. 完成信号与回滚

完成信号：下载/cache 全矩阵通过，失败路径无 `loaded/running`，receipt 可追溯到 lock/node/session，runtime owner 对真实证据 `approve`。签署或独立复审缺失时仅能标技术实现完成。

回滚：停止新 session 或回到最近稳定 materialization adapter，但继续强制 digest 校验；保留所有 receipt/失败审计。禁止回滚到跳过校验、只信 cache metadata 或伪造 ready 的版本。

## 11. 风险与 Clarification

| 风险/澄清 | 处理 | Owner / action |
|---|---|---|
| 实际加载字节与下载文件边界不同 | 以最终加载前不可变包字节为准，差异时阻断 | Runtime owner：批准 byte-stream 边界和 receipt 绑定点 |
| cache 文件可被进程外修改 | 每次加载前重算；失败隔离 cache entry | Runtime/SRE owner：确认 cache 权限与隔离告警 |
| receipt baseline 尚未实现 | 不新建平行 readiness 模型 | `task_deck_008` owner：先提供可扩展 receipt/session 合同 |

## 12. Gate 声明

runtime digest 验证是双路径校验后半段。任何未知或不一致均 fail closed；本 task 完成不等于 Stage 4 production Gate approve。
