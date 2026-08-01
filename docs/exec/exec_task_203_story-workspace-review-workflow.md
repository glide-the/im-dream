# Exec Report: task_203 - Story Workspace 审阅状态流转与批量操作 API

> 当前结论：`completed`。§1～§10 保留首次执行窗口的 blocked 审计证据；§11 起记录 [SUO-316](/SUO/issues/SUO-316) 解锁后的幂等 retry 与最终完成证据。

## 1. 执行上下文

- Task ID: `task_203`
- 执行 Issue: [SUO-309](/SUO/issues/SUO-309)
- 来源 Issue: [SUO-301](/SUO/issues/SUO-301)；业务映射 `SUO-201-BE-003`
- Parent / Ancestor: [SUO-301](/SUO/issues/SUO-301) / [SUO-273](/SUO/issues/SUO-273) / [SUO-198](/SUO/issues/SUO-198)
- 关联设计稿:
  - `docs/design/story-workspace/story-workspace-layout-design.md` §6.1
  - `docs/design/story-workspace/story-workspace-prd.md` §3.1 `DEC-007` / `DEC-008`、§4.5.1～§4.5.4
- 关联 Task: `docs/task/task_203_backend_story-workspace-review-workflow.md`
- 关联 Stage: `docs/stage/stage_story-workspace.md` §13.2、§13.4
- 执行 Agent: `ExecTaskAgent`
- 执行时间: `2026-08-01 21:15～21:20 CST (+0800)`
- Paperclip run: `57a8c702-f84c-45ce-9131-7f2c2d3f43ba`
- Checkout: PASS；[SUO-309](/SUO/issues/SUO-309) 已由 ExecTaskAgent checkout 并进入 `in_progress`
- 最终执行状态: `blocked`

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`（只读，未修改）
- 单一映射: [SUO-309](/SUO/issues/SUO-309) → `task_203` → Stage §13.2 / §13.4
- 填充位置: 当前 Paperclip run scratch 中的 `TASK-REQUIREMENT-task_203-filled.md`；149 行，`{{...}}` 占位符扫描为零
- 输入 Task: confirm / reject / archive / batch 审阅工作流与 focused unittest
- 填充后的执行目标: 仅在 `task_204` + `task_205b` 冻结基线上追加 7 个单项审阅端点、1 个 batch 端点、私有最小 helper、focused unittest 与本报告
- 允许范围:
  - `backend/routers/story_workspace.py`：仅追加本 Task 端点 / helper
  - `backend/tests/test_story_workspace_review.py`：新建 focused unittest
  - `docs/exec/exec_task_203_story-workspace-review-workflow.md`：唯一正式报告
- 禁止范围: `backend/database.py`、Schema/DDL/migration、canonical contracts、现有 CRUD、`task_204` service/internal endpoint、前端、Claude Agent SSE、依赖/测试框架、上游文档及未列路径
- 验收条件: `AC-203-01`～`AC-203-07` 全量带入，没有删减或放宽
- 测试合同: `py_compile`、focused unittest、database hash / 路径闭集、targeted `git diff --check`
- 模板 Gate 结果: 输入、checkout、文档、边界、验收、测试与回滚信息齐全；实现可行性检查发现冻结 Schema 与验收合同不可同时满足，因此未进入代码写入

## 3. 模型生成的执行任务

基于完整填充后的单 Task 提示词，模型生成以下受闭集约束的执行任务：

1. 保留 canonical imports、现有 CRUD 与 `/internal/agent-output`，仅在 router 追加请求模型、资源映射与审阅 helper。
2. 为 story / character / scene 实现 pending-only confirm / reject；持久化 `confirmed_at` / `review_notes`。
3. 为 story 实现单条 archive；支持 pending / confirmed / rejected，保留 `review_status`，重复 archive 返回 400。
4. 为三类 `resource_type` 实现最多 100 IDs 的 pending-only batch confirm / reject / archive，并返回完整 accounting。
5. 写入前完成全部请求校验；使用 owner 条件与事务保证无部分写入。
6. 成功操作输出结构化 audit 字段，不新增持久化 audit Schema。
7. 新建唯一 focused unittest 并执行 Stage §13.4 的四项验证。

范围校验结果：任务没有申请闭集外路径；但第 2、4 项依赖冻结 Schema 不存在的列，无法合法执行。

## 4. 实现前基线与阻塞证据

### 4.1 冻结基线

| 路径 | 状态 | 权威 / 实测 Git blob | 结论 |
|---|---|---|---|
| `backend/routers/story_workspace.py` | 前序任务未跟踪产物 | `9b8f0a36484d2a6bf188bcadfb5daa8073d40470` | 与 CEOOrchestrator 冻结值一致 |
| `backend/database.py` | 共享工作树既有 modified | `d71289c6c98cf91ebb6b36d9987991ead5663f9a` | 与 CEOOrchestrator 冻结值一致；本 Task 只读 |
| `backend/tests/test_story_workspace_review.py` | MISSING | N/A | 按 Gate 未通过规则未创建 |

执行窗口未运行 reset、stash、checkout 覆盖、清理、格式化或暂存操作。

### 4.2 Schema / Acceptance 冲突

`AC-203-01` 要求 story / character / scene 三类 pending 项均可 confirm / reject，且 confirm 持久化 `confirmed_at`、reject 持久化最长 2000 字 `review_notes`。冻结 Schema 只能支持 story：

| 表 | `review_status` | `confirmed_at` | `review_notes` | `status`（archive） |
|---|---:|---:|---:|---:|
| `story_workspace_stories` | 有 | 有 | 有 | 有 |
| `story_workspace_characters` | 有 | **无** | **无** | **无** |
| `story_workspace_scenes` | 有 | **无** | **无** | **无** |

证据：

- `backend/database.py` 的三个 `CREATE TABLE` 定义与 `backend/tests/test_database.py` 的权威列集合一致。
- 对实际 `backend/data/ink-and-memory.db` 使用 SQLite immutable read-only URI 执行 `PRAGMA table_info`，character 仅有 `... review_status, agent_generated, created_at, updated_at`，scene 同样没有 `confirmed_at` / `review_notes` / `status`。
- `backend/story_workspace/contracts.py` 中 character / scene canonical dataclass 也不拥有 `confirmed_at` / `review_notes` 字段；本 Task 禁止改 canonical 合同。
- 仓库定向扫描不存在可复用的 Story Workspace 持久化 review/audit sink。

此外，Task §5 将 `batch.action='archive'` 与 `resource_type='story'|'character'|'scene'` 放入同一请求合同，Stage §13.4 要求 batch pending-only 更新；character / scene 没有任何可表达 archive 的 `status` 字段。

### 4.3 为什么不能降级实现

- 只在 HTTP 响应临时补 `confirmed_at` / `review_notes` 不属于“写入 / 保存”，重读即丢失，不能作为 `AC-203-01` 通过证据。
- 挪用 character `notes`、scene `description` 或 JSON 字段会破坏既有业务合同和 CRUD 语义。
- 在 router 内执行 `ALTER TABLE`、建立 side table 或进程内缓存均绕过 `backend/database.py` / Schema / DDL 禁止规则。
- 将 character / scene batch archive 静默 skip 会违反“仅更新 pending 项”和完整 batch action 合同。
- ExecTaskAgent 无权自行缩减验收、改变 Schema、重写 Task 或重新设计状态机。

## 5. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `docs/exec/exec_task_203_story-workspace-review-workflow.md` | create | 记录模板 Gate、冻结基线、不可实现证据、阻塞与恢复条件 |

未修改 `backend/routers/story_workspace.py`，未创建 `backend/tests/test_story_workspace_review.py`，未修改任何禁止路径。

## 6. 测试与验证

### 已执行检查

| 检查 | 结果 |
|---|---|
| `git hash-object backend/routers/story_workspace.py backend/database.py` | PASS；分别等于冻结值 `9b8f0a...0470` / `d71289...f9a` |
| `rg` 核对 Schema、canonical contracts、tests 与持久化 sink | BLOCKER CONFIRMED；character / scene 缺少所需字段，无兼容 sink |
| SQLite immutable read-only `PRAGMA table_info` | BLOCKER CONFIRMED；实际运行库与源码 Schema 一致 |
| 模板占位符扫描 | PASS；填充提示词无 `{{...}}` 残留 |

### 未执行测试及原因

- 未执行 `python -m py_compile backend/routers/story_workspace.py backend/tests/test_story_workspace_review.py`：focused test 在 Gate 阻塞后未获准创建，规定命令当前无法形成有效 Task 验证。
- 未执行 `python -m unittest backend.tests.test_story_workspace_review -v`：同上；不存在可合法实现并验证的目标行为。
- 未执行定向 `git diff --check`：router / focused test 均无本 Task 实现差异；本报告为唯一写入。
- 未把 baseline-only router compile 或既有测试冒充本 Task 完成证据。

## 7. 风险与阻塞

- 当前状态: `blocked`
- Blocked 原因: `AC-203-01` 与 batch archive 合同需要 character / scene 持久化字段，但冻结 Schema 明确缺失；Allowed / Forbidden 又禁止本 Task 修改 Schema 或 canonical 合同。
- 缺失输入: 经上游批准且彼此一致的持久化合同。
- 已完成检查项: checkout、Issue / Task / Stage / template / design 读取、模板完整填充、冻结 hash、现有 router、Schema 源码、Schema tests、canonical contracts、实际 SQLite columns 与兼容 sink 检查。
- 解锁 owner: `CEOOrchestrator` 负责协调 `TaskDesignAgent` / Schema owner 完成合同裁决并建立合法前置执行单。
- 需要上游明确选择并冻结以下一种方案：
  1. 先由独立 Schema Task 为 character / scene 增加 `confirmed_at`、`review_notes`，并明确两类资源的 archive 持久化字段，然后重新通过九项 readiness；或
  2. 正式修改 Task / Stage / Issue 的验收与 batch action-resource 矩阵，使其与现有 Schema 一致。
- 恢复条件: 上述冲突通过上游文档与前置 Issue 解决、`backend/database.py` 新冻结 hash 明确、共享路由重新释放、本 Issue 重新 checkout。

## 8. 完成状态

- [ ] 已完成实现
- [ ] 已完成规定测试
- [x] 已记录全部执行前检查与阻塞证据
- [ ] 已满足 `AC-203-01`～`AC-203-07`
- [x] 已确认禁止范围无本 Task 写入
- [ ] 可进入 review / audit

最终 disposition：`blocked`。不得释放 `task_202c_verify`；不得把本报告解释为 Review workflow 已完成。

## 9. 回滚建议

- 没有生产代码或测试文件可回滚。
- 本报告是阻塞审计证据，应保留；若上游完成合同修复，后续 retry 复用同一 `task_id` / `issue_id` / 报告路径并在本报告追加新的执行窗口，不覆盖本次证据。
- 禁止为解除阻塞而回退 `task_204` internal endpoint、`task_205b` canonical imports、既有 CRUD 或 `backend/database.py` 的共享基线。

## 10. 执行完成报告

`task_203` 已完成模板化输入与实现前准入核验，但无法在当前 Allowed 闭集内同时满足冻结 Schema 和 `AC-203-01`～`AC-203-04`。本次没有静默降级、伪造持久化字段或越权修改；Issue 必须保持 blocked，等待 CEOOrchestrator 组织上游合同 / Schema 修复后再 retry。

## 11. Retry 执行上下文（完成窗口）

- 执行时间：`2026-08-01 23:18:10 CST (+0800)`
- Paperclip run：`ae54d990-6be4-47ff-8270-97fe6f8319e6`
- Task / Issue：`task_203` / [SUO-309](/SUO/issues/SUO-309)
- Wake reason：`issue_children_completed`
- Checkout：harness 已为本 run checkout，控制面为 `in_progress`，single assignee 为 `ExecTaskAgent`
- 解锁证据：[SUO-316](/SUO/issues/SUO-316) 已 `done`，最新裁决明确释放 `task_203` 并完成 execute handoff
- 九项 readiness：全部 PASS
- 冻结输入：
  - `backend/database.py` SHA-256 = `22db28fa6269a963c2537a85f648a00fb50e2827e22ccb5d181b581cc0edc356`
  - `backend/story_workspace/contracts.py` SHA-256 = `0a1c748b7fab1e2831d1f746f6ce12b6120ec3c66c049ad8cd6e0ff882fe55e8`

### 11.1 TASK-REQUIREMENT-FORMAT 填充与模型执行任务

- 模板继续只读：`docs/task/TASK-REQUIREMENT-FORMAT.md`
- 本 run 填充文件：`$PAPERCLIP_RUN_SCRATCH_DIR/TASK-REQUIREMENT-task_203-filled.md`
- 填充结果：136 行；`{{...}}` 占位符扫描为零
- 单一映射：[SUO-309](/SUO/issues/SUO-309) → `task_203` → Stage v7 §13.4 / §14.5 / §14.7
- 格式化后的模型执行任务：
  1. 仅追加私有请求模型、资源映射、事务性 review/archive/batch helper 与结构化 audit helper。
  2. 实现 story / character / scene pending-only confirm/reject。
  3. 实现 story 单条 archive 与三类资源 pending-only batch。
  4. 使用 owner、`agent_generated=1`、状态条件和单事务保证隔离与原子性。
  5. 新建 focused unittest，逐项覆盖 `AC-203-01`～`AC-203-07`。
- 范围校验：只申请 router、focused test 与本报告；不申请 Schema、canonical、CRUD、Agent internal endpoint 或任何上游文档写入。

## 12. Retry 实现变更记录

| 文件 | 操作 | 最小变更摘要 |
|---|---|---|
| `backend/routers/story_workspace.py` | update | 追加 review 请求模型、资源闭集、结构化 audit helper、事务性 confirm/reject/archive/batch helper、7 个单条端点和 1 个 batch 端点；保留既有 CRUD 与 `/internal/agent-output` |
| `backend/tests/test_story_workspace_review.py` | create | 新增 7 个 `unittest.TestCase` focused tests，覆盖三类资源、状态矩阵、story archive、batch、认证/owner、原子校验与 audit 字段 |
| `docs/exec/exec_task_203_story-workspace-review-workflow.md` | append | 保留首次 blocked 窗口，追加解锁后的完成证据、测试、风险与回滚建议 |

### 12.1 API 交付

- `POST /api/story-workspace/stories/{id}/confirm`
- `POST /api/story-workspace/stories/{id}/reject`
- `POST /api/story-workspace/stories/{id}/archive`
- `POST /api/story-workspace/characters/{id}/confirm`
- `POST /api/story-workspace/characters/{id}/reject`
- `POST /api/story-workspace/scenes/{id}/confirm`
- `POST /api/story-workspace/scenes/{id}/reject`
- `POST /api/story-workspace/batch`

实现语义：

- confirm/reject 仅处理 owner 的 `agent_generated=1`、`review_status='pending'` 且未归档资源。
- confirm 写 `review_status='confirmed'`、`confirmed_at`、`updated_at`。
- reject 写 `review_status='rejected'`、最长 2000 字 `review_notes`、`updated_at`。
- story 单条 archive 支持 pending/confirmed/rejected，更新 `status='archived'`，保留 `review_status`，重复操作 400。
- batch 限制 1～100 个非空唯一 IDs；confirm/reject/archive 均只更新 pending 且未归档资源，稳定返回 requested/updated/skipped/items。
- character / scene batch archive 同时写 `archived_at`；story 使用其冻结的 `status` 合同。
- 成功操作记录 `id`、`user_id`、`resource_type`、`resource_id`、`action`、`previous_status`、`new_status`、`review_notes`、`created_at` 结构化日志字段。

## 13. Retry 测试与验证

### 13.1 规定命令

| 命令 / 检查 | 结果 |
|---|---|
| `python -m py_compile backend/routers/story_workspace.py backend/tests/test_story_workspace_review.py` | PASS，exit 0 |
| `python -m unittest backend.tests.test_story_workspace_review -v` | PASS，7 tests，`OK` |
| `shasum -a 256 backend/database.py backend/story_workspace/contracts.py` | PASS，与冻结值完全一致 |
| `git diff --check -- backend/routers/story_workspace.py backend/tests/test_story_workspace_review.py` | PASS，exit 0，无 whitespace error |

### 13.2 共享路由回归

`python -m unittest backend.tests.test_story_workspace_api backend.tests.test_story_workspace_agent_integration -v`

- PASS：18 tests，`OK`
- 既有 CRUD、认证/owner、controlled PATCH、query/detail、Agent storage 与 `/internal/agent-output` 均通过。

### 13.3 验收映射

| 验收 ID | 结果 | 验证证据 |
|---|---|---|
| `AC-203-01` | PASS | `test_pending_confirm_and_reject_for_all_resource_types`：三类 confirm/reject、2000 Unicode 字边界与持久化 round-trip |
| `AC-203-02` | PASS | `test_non_pending_review_transition_matrix`：三类 confirmed/rejected/archived × confirm/reject 均 400，含 rejected→confirm |
| `AC-203-03` | PASS | `test_story_archive_matrix_preserves_review_status`：pending/confirmed/rejected 可 archive、review_status 保留、重复 400 |
| `AC-203-04` | PASS | `test_batch_pending_only_and_result_accounting`：三 action、三 resource、pending-only、owner-safe skipped 与完整 accounting |
| `AC-203-05` | PASS | `test_review_authentication_and_owner_isolation`：未认证 401，其他 owner 与非 Agent 生成资源 404 |
| `AC-203-06` | PASS | `test_review_request_validation_is_atomic`：非法 action/resource、空 IDs、101 IDs、2001 字均 422 且无写入 |
| `AC-203-07` | PASS | `test_review_action_emits_structured_audit_log` 验证九项字段；database/contracts hashes 不变，路径闭集通过 |

## 14. 文件边界、风险与阻塞

- 本 task 实际写入仅三条允许路径：router、focused test、本报告。
- `backend/database.py`、`backend/story_workspace/contracts.py` 虽属于共享 dirty worktree 的既有产物，但本 run 未修改，执行前后 SHA-256 均保持冻结值。
- 未修改既有 CRUD、Agent service/internal endpoint、前端、依赖/测试框架、`docs/design/**`、`docs/issue/**`、`docs/task/**`、`docs/stage/**` 或其他 exec report。
- 工作树仍包含其他任务的既有未提交内容；本 run 未 reset、stash、还原、格式化或覆盖它们。
- 当前阻塞：`None`。
- 未验证项：浏览器 / Network 证据不属于本 task，由后序 [SUO-310](/SUO/issues/SUO-310) 负责。
- 剩余风险：SQLite 跨进程并发以 `BEGIN IMMEDIATE` 与条件 UPDATE 串行化；高并发性能不在当前最多 100 项的合同之外扩展。

## 15. 回滚建议

1. 从 `backend/routers/story_workspace.py` 仅移除 `_ReviewActionRequest`、`_BatchReviewRequest`、`_REVIEW_RESOURCES`、本 task 私有 review/archive/batch/audit helpers 与上述 8 条路由。
2. 删除 `backend/tests/test_story_workspace_review.py`。
3. 保留本报告作为执行审计；不得回退 `backend/database.py`、`backend/story_workspace/contracts.py`、既有 CRUD、task_204 internal endpoint 或 task_205b canonical imports。
4. 回滚后重跑两个共享路由回归 suites，确认前序基线仍通过。

## 16. Retry 完成状态

- [x] 已完成实现
- [x] 已完成规定测试
- [x] 已完成共享路由回归
- [x] 已记录变更与验证证据
- [x] 已满足 `AC-203-01`～`AC-203-07`
- [x] 禁止范围无本 task 写入
- [x] 可进入 review / audit

最终 disposition：`done`。`task_203` 已在合法解锁后的单一 checkout 内完成，无剩余实现项；[SUO-310](/SUO/issues/SUO-310) 可由其 owner 按 first-class blocker 自动解锁后继续。
