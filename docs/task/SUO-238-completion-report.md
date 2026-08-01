# SUO-238 Completion Report

## 1. 交付结论

[SUO-238](/SUO/issues/SUO-238) 的 task 阶段 Deck-only 合同修订已完成。当前 task 文档统一使用 Deck owner、`DeckPluginRuntimeConfig` / `DeckRuntimeSnapshot` 语义、`deck_runtime_*` 字段、规范错误码与唯一 canonical design 路径；运行配置、不可变快照、secret-ref、权限、preflight、审计、幂等、重试与回滚合同均保留。

Requirement-first gate 已通过：先填充 `docs/task/TASK-REQUIREMENT-task_238_shared_deck-task-contract-normalization.md`，再按该 prompt 修订任务文档。

## 2. Canonical 合同

| 维度 | 当前 task 规范 |
|---|---|
| 唯一业务 owner | Deck；运行配置是 Deck 内部子对象，不形成独立 service/API namespace/权限域 |
| 配置对象 | `DeckAgentProfile`、`DeckPluginRuntimeConfig` |
| 不可变快照 | `DeckRuntimeSnapshot` / `deck_runtime_snapshot_id`；Deck 权威存储，Ink-Dream 只存 ID 与脱敏摘要 |
| 快照合同与策略 | `deck_runtime_snapshot_contract`、`deck_runtime_snapshot_policy` |
| 单次运行来源 | `deck_plugin_id + deck_plugin_version + deck_runtime_snapshot_id + runtime_plugin_lock_id` |
| 配置错误码 | `DECK_RUNTIME_CONFIG_INVALID`、`DECK_RUNTIME_CONFIG_INCOMPATIBLE`、`DECK_RUNTIME_CONFIG_UNAVAILABLE` |
| 输出错误码 | `OUTPUT_CONTRACT_INVALID` |
| API 审阅态 | `pending_review`；“awaiting review”仅为 UI 文案 |
| canonical design | `docs/design/deck/deck-integration-delta.md` |

## 3. 修订文件

### 3.1 Requirement 与 completion report

- `docs/task/TASK-REQUIREMENT-task_238_shared_deck-task-contract-normalization.md`
- `docs/task/SUO-238-completion-report.md`
- `docs/task/SUO-234-completion-report.md`

### 3.2 Backend task

- `docs/task/task_deck_001_backend_manifest-model.md`
- `docs/task/task_deck_002_backend_runtime-lock.md`
- `docs/task/task_deck_003_backend_installation-lifecycle.md`
- `docs/task/task_deck_004_backend_compatibility-capability.md`
- `docs/task/task_deck_006_backend_workflow-preflight.md`
- `docs/task/task_deck_007_backend_workflow-run.md`
- `docs/task/task_deck_009_backend_run-scoped-session.md`
- `docs/task/task_deck_013_backend_events-audit.md`
- `docs/task/task_deck_014_backend_api-error-codes.md`
- `docs/task/task_deck_015_backend_revocation-rollback.md`

`task_deck_008_backend_reconcile-load-receipt.md` 已复核，未发现需要本 Issue 再修改的旧配置域字段或 owner 假设，保留其既有写入边界修订。

### 3.3 Frontend / shared / cross-cutting task

- `docs/task/task_202d_frontend_review-panel.md`
- `docs/task/task_210_shared_deck_plugin_binding.md`
- `docs/task/task_211_frontend_plugin_admin_ui.md`
- `docs/task/task_212_frontend_deck_editor_plugin_binding.md`
- `docs/task/task_213_frontend_story_workspace_status.md`
- `docs/task/task_230_backend_review-gate-aggregation.md`
- `docs/task/task_230_frontend_dream-page-review-gate.md`
- `docs/task/task_230_shared_idempotency-e2e.md`
- `docs/task/task_241_frontend_episode-workspace.md`（新增发现的相关引用）

## 4. 关键修订摘要

1. Manifest、兼容性、preflight、run、session、event 与 API 合同统一为 Deck runtime 类型/字段/错误码。
2. Preflight 不再要求 Ink-Dream 创建第二份配置快照表；改为通过单一 Deck API owner 创建/复用不可变快照，本地只保存受控引用与脱敏摘要。
3. Capability 交集统一为 `manifest_requested ∩ installation_approved ∩ deck_runtime_snapshot_policy ∩ user_and_workspace_grants ∩ claude_agent_runtime_supported`。
4. Workflow Run 状态机补齐 `output_validating → pending_review → confirmed/rejected → continuing/completed`，并明确重试创建新 run。
5. UI 状态、错误恢复、来源展示和 Episodes composer gate 同步使用 Deck 运行配置就绪语义。
6. 不存在的旧编号 task 文件依赖改为已有 task，或显式标注 `SUO-226-*` canonical Issue gate；不再伪装成可直接读取的 task 文件。
7. 三处旧 delta 路径引用统一到 `docs/design/deck/deck-integration-delta.md`。

## 5. 验收与验证

| 验证 | 结果 |
|---|---|
| Issue 指定的旧独立配置域词/前缀全目录扫描 | 0 命中；无保留历史命中需要豁免 |
| `story-workspace-deck.*integration-delta\.md` 扫描 | 0 命中 |
| 旧配置域类型、字段和错误码扫描 | 0 命中 |
| 不存在的旧编号 task 文件引用扫描 | 0 命中 |
| 非 canonical 审阅 API 枚举与旧输出错误码扫描 | 0 命中 |
| canonical 字段/错误码/状态/路径命中 | 49 处，覆盖 backend、frontend、shared 与 completion report |
| 18 份受影响既有 task 的 `## 1`～`## 10` 标准章节 | 全部存在 |
| `git diff HEAD --check -- docs/task` | 通过 |

最小验证只检查文档合同、引用与差异；本 Issue 不运行实现代码构建或测试。

## 6. 写入边界与工作树保护

- 本 Issue 只新增/修改 `docs/task/`。
- 未修改 `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 或实现代码。
- 工作树中既有的 design/issue/stage 修订，以及 SUO-245 的 requirement、completion report 与 task 产物均予以保留；本次不重置、不覆盖、不纳入 rollback。
- `docs/task/TASK-REQUIREMENT-FORMAT.md` 的既有可复用 execute 模板改动保持不变。

## 7. Blocker、风险与回滚

- Blocker：无；[SUO-250](/SUO/issues/SUO-250) 与 [SUO-251](/SUO/issues/SUO-251) 均已完成。
- 剩余风险：Stage/Exec 尚需按新字段、状态和错误码消费 task 合同；不得恢复旧路径或双 owner。
- Rollback：仅回退本报告第 3 节列出的 SUO-238 增量 hunk，并删除本 Issue 新增的 requirement/completion report；禁止回退上游 design/issue 迁移或其他 Issue 的 task 产物。

## 8. Review 建议

建议 StagePlanner 在 [SUO-239](/SUO/issues/SUO-239) 中重点复核：

1. `deck_runtime_snapshot_id` 在 preflight → run → session → event → UI 的冻结与传递顺序；
2. `pending_review` 唯一 API 枚举及 `OUTPUT_CONTRACT_INVALID` 恢复路径；
3. Deck 权威快照与 Ink-Dream 引用边界；
4. `SUO-226-*` Issue gates 与现有 task 的实际准入顺序；
5. rollback 不改写历史 run、快照与审计记录。

## 9. 最终状态

Task 文档修订与最小验证全部完成，无未决 blocker；[SUO-238](/SUO/issues/SUO-238) 可标记 `done`。
