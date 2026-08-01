# Exec Report: task_deck_006_backend_workflow-preflight - Workflow Preflight

## 1. 执行上下文

- Task ID：`task_deck_006_backend_workflow-preflight`
- 执行 Issue：`SUO-281`
- 来源业务 Issue：`DECK-006`；来源清单 `SUO-223`
- Parent / Ancestor：`SUO-217` / `SUO-216`
- 关联设计稿：
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §10.1、§10.2
  - `docs/design/deck/deck-integration-delta.md` §5.1、§7.2
- 关联 Stage：`docs/stage/stage_deck-plugin-voice-ink-dream-integration.md`，Stage 2 / Wave 1
- 执行 Agent：`ExecTaskAgent`
- 执行时间：`2026-08-01 17:47:25 CST`
- Checkout：本 heartbeat 由 Paperclip harness 预先成功 checkout，未重复请求执行锁。

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径：`docs/task/TASK-REQUIREMENT-FORMAT.md`
- Task 路径：`docs/task/task_deck_006_backend_workflow-preflight.md`
- 填充后的单 task prompt：本次 run scratch 下的 `TASK-REQUIREMENT-FILLED-SUO-281.md`
- 输入 Issue：`SUO-281`，唯一关联 Task 为 `task_deck_006_backend_workflow-preflight`
- 填充后的执行目标：实现固定 8 步权威 preflight、Deck runtime snapshot 受控引用、runtime materialization 校验，以及绑定关键来源的短期一次性 token。
- 关键约束：仅修改 4 个实现/测试闭集路径与本报告；不实现 Workflow Run、ClaudeAgent session、前端、Deck 发布/安装或 Stage/Task 重排。
- 验收条件：Issue 中 7 项验收与 Task §9 完成标志全部逐项带入。
- Stage 准入：wake payload 明确 Stage 1 Gate 已由 `SUO-263`、`SUO-268`、`SUO-271`、`SUO-274` 解除；该信息晚于 Stage 文档中的历史 blocked 快照。

## 3. 模型生成并执行的单任务

- 任务目标：Story Workspace 在创建任何 Workflow Run 或 Agent session 前完成权威 preflight。
- 实现范围：
  1. 严格 Preflight 状态、检查阶段与记录模型。
  2. 身份/权限、binding/release、manifest/schema、兼容性、能力/来源、Deck snapshot、runtime materialization、token 八步固定链。
  3. Deck snapshot 严格 receipt，只接受 ID、脱敏摘要 hash 与复用标志。
  4. token 确定性 HMAC 签发、数据库仅存 token hash、原子消费、防过期与防重放。
  5. SQLite 幂等表/索引与同请求并发复用。
- 文件范围：仅 Task 闭集与本报告。
- 验证方式：定向 unittest、前序四模块最小回归、`py_compile`、SQLite schema/行为断言、diff/path 检查。

## 4. 实现说明

### 4.1 固定顺序与失败短路

`PreflightService.execute_preflight` 依次执行：

1. `identity_workspace_permission`
2. `binding_release`
3. `manifest_workflow_schema`
4. `host_agent_runtime_compatibility`
5. `capability_source_policy`
6. `deck_runtime_snapshot`
7. `runtime_materialization`
8. `token_issuance`

各权威事实通过窄接口注入；callback 返回失败或抛出结构化错误时立即停止，并只持久化 `WorkflowPreflight(status=failed)`。服务没有 Workflow Run 或 ClaudeAgent collaborator，因此失败路径无法启动 Agent 或创建伪运行。

### 4.2 Deck runtime snapshot 所有权

- Snapshot 只通过 `deck_snapshot_owner` 创建或复用。
- `DeckRuntimeSnapshotReceipt` 使用 `extra="forbid"`，仅允许 `deck_runtime_snapshot_id`、`sanitized_summary_hash`、`reused`。
- 本地表只保存 snapshot ID 与脱敏摘要 hash；没有 prompt、secret、secret-ref 或 runtime config 列。

### 4.3 Runtime materialization

对每个 required runtime plugin 验证：

- `declaration_status == declared`
- `materialization_status == materialized`
- `activation_status in {loadable, loaded}`
- 实际 `artifact_digest` 与 runtime lock 期望值一致
- 聚合 `load_smoke_passed == true`

runtime lock ID 漂移、digest 不匹配、未物化/不可加载和 load smoke 失败分别返回结构化错误码。

### 4.4 Token、过期与重放

- 默认 TTL 为 300 秒，可配置但必须为正数。
- HMAC payload 绑定 preflight ID、binding revision、input hash、Deck runtime snapshot ID、runtime lock ID 与过期时间。
- 数据库不保存原始 token，只保存 SHA-256 token hash。
- 消费使用 SQLite `BEGIN IMMEDIATE` 与 `consumed_at IS NULL` 条件更新，保证一次性语义。
- binding/input/snapshot/lock 不匹配不会消费 token；过期会把 preflight 标为 `expired`；已消费 token返回 replay 错误。
- 已消费记录退出活动请求唯一索引，同请求重新 preflight 会生成新 preflight/token。

### 4.5 并发与幂等

- 请求指纹绑定 deck、binding revision、input hash 和 actor。
- 单服务实例使用 per-fingerprint async lock，复用同一 snapshot、preflight 与 token。
- SQLite partial unique index防止多服务实例并发创建多个 active preflight；数据库 race 的 loser 读取 winner 记录，不重复 Deck 工作。

## 5. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/models/workflow_preflight.py` | create | 新增 `WorkflowPreflight`、`PreflightStatus`、`PreflightCheck` 与状态一致性校验 |
| `backend/services/workflow/preflight_service.py` | create | 新增固定 8 步服务、严格 owner receipts、materialization 校验、并发复用、token 签发/消费 |
| `backend/database.py` | update | 在前序 Deck 表之后增量追加 `workflow_preflights` 表及 3 个幂等索引 |
| `backend/tests/test_workflow_preflight.py` | create | 新增 9 个定向测试，覆盖全部任务验收边界 |
| `docs/exec/exec_deck_006_backend_workflow-preflight.md` | create | 本执行报告 |

### 工作树冲突处理

- 执行前工作树已有大量用户/其他 task 未提交内容。
- `backend/database.py` 执行前已有 104 行 Deck Manifest/Runtime Lock/Installation 增量；本 task 只在该连续区段后追加自身表/索引，未修改或重排前序内容。
- 未清理、reset、checkout、覆盖或格式化任何既有改动。
- 其他新增文件在执行基线中不存在，未与他人文件内容重叠。

## 6. 测试与验证

### 已执行测试

1. 静态语法：
   - 命令：`.venv/bin/python -m py_compile backend/models/workflow_preflight.py backend/services/workflow/preflight_service.py backend/database.py backend/tests/test_workflow_preflight.py`
   - 结果：通过，exit 0。
2. 本 task 定向单测：
   - 命令：`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_workflow_preflight -v`
   - 结果：9/9 通过。
3. 前序最小回归：
   - 命令：`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_deck_plugin_manifest backend.tests.test_deck_plugin_lock backend.tests.test_deck_plugin_installation backend.tests.test_deck_plugin_compatibility -v`
   - 结果：47/47 通过。
4. 差异空白检查：
   - 命令：`git diff --check -- backend/database.py`
   - 结果：通过，exit 0。
5. 允许路径检查：
   - `git status --short -- <task 闭集与报告>` 仅显示 `backend/database.py` 修改及 3 个本 task 新文件；报告生成后增加本报告路径。

测试输出中的 `Memory workspace config backfill skipped: No module named 'memory_workspace_defaults'` 是既有 `backend.database` fallback 提示；所有相关测试均通过，未影响本 task 表创建或断言。

### 验证证据映射

| 验收 | 结果 | 证据 |
|---|---|---|
| 固定 8 步、首错短路 | 通过 | 8 个阶段逐一失败测试验证调用前缀和 `failed_check` |
| Snapshot 单 owner、创建/复用、不复制敏感配置 | 通过 | 并发只调用一次 snapshot owner；严格 receipt 拒绝额外 secret；SQLite 列与值检查 |
| declared/materialized/digest/load smoke | 通过 | 6 组 materialization 失败子用例与成功路径 |
| Token 关键绑定、过期、防重放 | 通过 | revision/input/snapshot/lock mismatch、expiry、consume、replay、重新 preflight 测试 |
| 失败不启动 Agent、不创建伪运行 | 通过 | 首步失败仅有 preflight 表记录；服务无 Agent collaborator；无 workflow run 表 |
| 并发行为确定 | 通过 | `asyncio.gather` 同请求返回相同 preflight/snapshot/token，owner 调用 1 次；DB partial unique/race fallback |
| 执行报告完整 | 通过 | 本文记录变更、测试、证据、未验证项、风险与回滚 |

### 未执行测试及原因

- 未运行真实 Deck API + Runtime Admin + ClaudeAgent 的端到端集成测试。
- 原因：当前闭集没有授权 API router、Deck snapshot 实现、runtime materialization adapter、Workflow Run 或 ClaudeAgent session wiring；这些归属后续 Stage 2 task，越权实现会违反本 task 边界。
- 影响：当前证据证明 coordinator、持久化与 owner 接口合同；真实服务 wiring 仍需下游 API/Run task 在其闭集内完成。
- 替代证据：严格 Pydantic owner receipts、SQLite 行为测试、9 个 preflight 定向测试与 47 个前序最小回归。

## 7. 风险与阻塞

- 风险：`DECK-018` 的多节点/临时 runtime 分发策略仍未决。本服务只消费权威聚合 materialization receipt，不自行决定节点分发范围，避免提前冻结错误策略。
- 风险：跨服务真实 wiring 尚未集成；由后续 API/Workflow Run task 负责，不影响本 task coordinator 合同完成。
- 阻塞：无。
- 需要上游澄清的问题：无当前阻塞项。

## 8. 完成状态

- [x] 已完成实现
- [x] 已完成定向测试
- [x] 已完成前序最小回归
- [x] 已记录变更与未验证项
- [x] 已满足本 task 验收条件
- [x] 可进入 review / audit

最终建议状态：`done`。本 Issue 范围内无剩余实现或一等 blocker；真实跨服务 wiring 属于下游 task，不应让本 Issue 保持虚假 `in_progress`。

## 9. 回滚建议

- 回滚文件：
  - 移除 `backend/models/workflow_preflight.py`
  - 移除 `backend/services/workflow/preflight_service.py`
  - 移除 `backend/tests/test_workflow_preflight.py`
  - 从 `backend/database.py` 仅撤回 `workflow_preflights` 表与 `idx_workflow_preflights_*` 三个索引区段
  - 归档或移除本报告
- 数据库回滚：若表已在环境中创建，先确认没有下游 Workflow Run 引用，再导出需保留的 preflight 审计记录，随后仅删除本 task 的 3 个索引与 `workflow_preflights` 表。
- 注意事项：不得回滚 `deck_plugin_releases`、`deck_runtime_plugin_locks`、`deck_plugin_installations` 或其他执行前既有改动。
