# task_275d_backend_runtime-digest-load-receipt

> Task ID: `task_275d`
> Source Issue: `DECK-SC-004`
> Paperclip Issue: [SUO-275](/SUO/issues/SUO-275)
> Domain / Priority: `backend` / `P0`

## 1. 任务标题

Runtime 物化后二次摘要校验与不可变 Load Receipt

## 2. 关联 Issue

| 关联 | 内容 |
|---|---|
| 来源条目 | `DECK-SC-004` |
| Task-stage Issue | [SUO-275](/SUO/issues/SUO-275) |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1、§4.2.3 |
| 既有 task | `task_deck_002_backend_runtime-lock.md`、`task_deck_008_backend_reconcile-load-receipt.md` |
| Domain / Priority / 标签 | `backend` / P0 / `supply-chain`, `digest`, `runtime`, `verification` |

## 3. 任务目标

在 runtime 物化完成、进入 load 之前，对节点上实际可加载的制品字节重新计算 SHA-256，与不可变 lock 中的 `artifact_digest` 比对，并把结果、节点/session/attempt 和 policy revision 写入不可变 `RuntimeLoadReceipt`。cache 命中仍必须重读实际字节；marketplace 标签、下载响应摘要和 cache metadata 均不是放行证据。

本 task 不重新验证或刷新 marketplace 发布状态，不实现发布端签名验证、引用留存、scheduler 或 session 迁移。

## 4. 实现步骤

1. 扩展 runtime 模型，增加 `runtime_verified_digest`、`runtime_verification_status`、`runtime_verified_at`、`artifact_set_hash`、`runtime_node_id`、`workflow_run_id`、`attempt_id` 与冻结 policy/lock revision。
2. materialization 下载到 attempt-scoped 临时路径；流式读取最终下载字节计算 SHA-256，匹配后才原子发布到版本化 cache。
3. cache 命中也必须打开实际 cache 对象重算摘要；禁止只比较文件名、etag、marketplace metadata 或旧 receipt。
4. 对每个 required lock entry 做逐项校验；任一 digest 不匹配、缺失、算法未知或字节不可读时，整个 required set 不得进入 `loaded/session_loaded`。
5. 生成 append-only `RuntimeLoadReceipt`：
   - 逐项保存 lock digest 与 runtime digest；
   - 保存 node/session/run/attempt、materialized source、验证时间和错误码；
   - receipt 成功写入与 `loaded` 状态变更位于同一事务/提交边界。
6. 匹配失败时隔离临时/cache 对象，返回 `ARTIFACT_DIGEST_MISMATCH`，写审计事件并保持 run 在安全未运行状态。
7. 运行阶段只消费 `task_275c` 已冻结的 verification ref/digest，不联网重新信任 marketplace；发布 verification 被撤销时由独立撤销合同阻断新运行。
8. 使用固定字节 fixture、cache 篡改、并发 attempt、部分 required set、receipt 重放和断电边界测试原子性。

## 5. 涉及文件路径

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/runtime_plugin.py` | 新建/修改 | runtime materialization 与 load receipt 校验字段 |
| `backend/services/runtime_plugin/materialization_manager.py` | 新建 | attempt 临时下载、实际字节校验、原子 cache 发布 |
| `backend/services/runtime_plugin/reconcile_service.py` | 新建/修改 | required set 校验后才允许 load |
| `backend/services/runtime_plugin/load_receipt_service.py` | 新建 | append-only receipt 与 loaded 原子提交 |
| `backend/database.py` | 修改 | materialization/receipt 字段、唯一约束和事务初始化 |
| `backend/tests/test_runtime_plugin_digest_verification.py` | 新建 | 物化/cache/receipt/并发测试 |
| `backend/tests/fixtures/runtime_plugin_artifacts/` | 新建 | 固定公开字节与篡改 fixture |

## 6. 输入 / 输出说明

### 输入

- 不可变 `DeckRuntimePluginLock` 和逐项 `artifact_digest`；
- `workflow_run_id`、`runtime_pool_id`、`runtime_node_id`、`attempt_id`；
- 下载/冷恢复后的实际字节对象；
- 发布端冻结的 `verification_status`、`trust_policy_revision` 和证明 ref。

### 输出

```jsonc
{
  "runtime_load_receipt_id": "rlr_...",
  "workflow_run_id": "run_...",
  "runtime_node_id": "node_...",
  "attempt_id": "attempt_...",
  "entries": [{
    "artifact_digest": "sha256:...",
    "runtime_verified_digest": "sha256:...",
    "runtime_verification_status": "verified|failed",
    "runtime_verified_at": "...",
    "load_status": "loaded|load_failed"
  }]
}
```

失败输出包含 `ARTIFACT_DIGEST_MISMATCH`、artifact/attempt 脱敏标识、审计 ID；不得回显制品内容。

## 7. 依赖项、可并行性与冻结点

- 直接依赖：`task_275c`、`task_deck_002`；与既有 `task_deck_008` 增量合并。
- 下游：`task_275g`、`task_275h` 的 runtime 复核证据。
- Freeze point：所有 required digest 实际重算一致且 receipt 与 `loaded` 原子提交；此前不得创建可运行 session。
- `task_275e` 可在 `task_275c` 后与本 task 并行，但共享 `backend/database.py` 时 Stage 必须安排串行合并。

## 8. 测试策略

最小命令：`python -m unittest backend.tests.test_runtime_plugin_digest_verification`

| 场景 | 通过标准 |
|---|---|
| 新下载实际字节匹配 | 原子进入 cache，receipt verified |
| 新下载字节被篡改/截断 | 拒绝 load，隔离对象，结构化审计 |
| cache metadata 声称匹配但字节被改 | 重算发现 mismatch，拒绝 |
| required set 部分成功 | 整体不得 `session_loaded` |
| 并发相同 materialization key | 单 owner/单成功 receipt，其他返回同 operation 或显式冲突 |
| receipt 写入失败 | 不进入 loaded；重试不产生矛盾 receipt |
| marketplace 失联 | 已冻结且实际字节可验证时不重新查询；不得因此改信标签 |

执行 `git diff --check --` 指定闭集，并交叉用 `shasum -a 256` 校验 fixture。

## 9. 完成标志

- [ ] 物化后对实际字节重新计算 SHA-256。
- [ ] cache 命中不信任 metadata，仍重算实际字节。
- [ ] mismatch 返回 `ARTIFACT_DIGEST_MISMATCH`，拒绝 load 并留审计。
- [ ] receipt 含 runtime digest/status/time/node/run/attempt/lock revision。
- [ ] required entries 全部一致后才允许 `loaded/session_loaded`。
- [ ] runtime 不重新信任 marketplace 标签或可变状态。
- [ ] 下载、cache、并发、部分失败和 receipt 原子性测试通过。

## 10. 风险提示与回滚

| 风险 | 处理 / 回滚 |
|---|---|
| 大制品重算影响冷启动 | 流式计算并度量；不得用 metadata 绕过 |
| cache TOCTOU | 校验与原子发布使用受控文件句柄/rename；加载引用不可变对象 |
| receipt 与 loaded 分叉 | 同事务或可证明的 outbox/幂等提交 |
| 回滚到旧 runtime 绕过新字段 | 阻止相关 release 的 production run，保留 non-production 限域 |

回滚只能暂停/回退 materialization 实现并保持 fail closed；不得接受旧 receipt 伪装为已二次校验。

## 11. 允许 / 禁止修改范围

- 允许：§5 精确闭集。
- 禁止：发布 verifier/trust-policy、retention/purge、scheduler/session 迁移、前端、部署/依赖配置与未列出源码。
- 禁止修改 `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`。

## 12. StagePlanner / Execute Readiness

| 字段 | 值 |
|---|---|
| 前序 | `task_275c`, `task_deck_002`, `task_deck_008` 合同 |
| 可并行 | 与 `task_275e` 逻辑并行；共享 DB 文件串行合并 |
| Freeze point | required entries 二次摘要一致 + immutable load receipt |
| Execute readiness | runtime 路径、cache 原子操作、receipt transaction 与测试 fixture 明确 |
| 证据格式 | 精确测试报告、fixture SHA-256、逐 attempt immutable load receipt、audit ID 与失败隔离记录 |
| Clarification owner/action | runtime owner 确认真实 materialization/cache 路径、required-set 原子边界和 receipt 提交方式；由 `CEOOrchestrator` 路由签署 |
| 未满足 Gate | 冷恢复/留存、真实篡改与恢复报告、owner/reviewer、独立复审 |

本 task 完成不等于 Stage 4 production Gate approve。
