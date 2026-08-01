# Exec Report: task_deck_007 - Workflow Run 创建、状态与幂等重试

## 1. 执行上下文

- Task ID: `task_deck_007` / 逻辑 Issue `DECK-007`
- Paperclip Issue: `SUO-304`
- 来源控制项: `SUO-217`
- 关联 Issue: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 `DECK-007`
- 关联设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` §11.1~§11.4；`docs/design/story-workspace/story-workspace-layout-design.md` §5.6
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` §18，Stage 2 / Wave 2
- 前置执行: `SUO-281` Workflow Preflight、`SUO-296` Backend Deck Plugin Binding
- 执行 Agent: `ExecTaskAgent`
- Paperclip Run ID: `2c16505b-dad2-48ae-93f8-d06532fe3c5f`
- 执行日期: `2026-08-01`
- checkout: harness 已在本 run 开始前取得 `SUO-304` 执行锁，未重复 checkout

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`（只读）
- Task 文档: `docs/task/task_deck_007_backend_workflow-run.md`（只读）
- 填充记录: `${PAPERCLIP_RUN_SCRATCH_DIR}/task_deck_007_execute_prompt.md`（run 临时证据）
- 输入 Issue: `SUO-304` → `DECK-007`
- 输入 Stage: Stage 2 / Wave 2，`SUO-303` 判定 `ready_to_execute`
- 填充后的目标: 在闭集内实现严格 Run 模型、认证作用域幂等创建、HMAC token consumption、原子 transition、fake receipt 守卫与 fresh-preflight retry
- 关键约束: fingerprint 不含 token/preflight ID；token 原文不落库；冲突不泄露原 run；不实现 Reconcile/Materialization/Receipt 内部逻辑/Session/events/outbox
- 工作树基线: `backend/database.py` 已含前序 manifest/lock/install/binding/preflight 未提交增量；本次采用同文件最小追加，未覆盖或重置既有内容。其余本 task 实现路径原先不存在

## 3. 模型生成的执行任务

- 定义 `RunStatus` 11 态、`WorkflowRun`、`WorkflowRunTransition`、`AuthenticatedActorContext`、`RuntimeLoadReceiptReadiness` 严格合同。
- 以 `BEGIN IMMEDIATE` + 唯一约束实现 `(workspace_id, created_by, idempotency_key)` 原子收敛。
- 复算并常量时间验证现有 Preflight HMAC token；消费表仅持久化 domain-separated HMAC digest。
- 从 Preflight、Binding、Release、runtime lock 和认证上下文冻结来源；canonical fingerprint 排除 token 与 preflight 记录 ID。
- 首次创建在同事务写入 run、token consumption、`NULL → preflight → queued` 两条真实 transition；重放不伪造 transition。
- 合法状态变化同步递增 `status_version` 并追加 append-only transition；失败注入证明双写整体回滚。
- `queued → running` 仅读取注入的 immutable readiness projection，验证 run、lock、canonical lock digest 和 required readiness，一次性绑定 receipt ID。
- retry 要求新的 preflight/token/idempotency key，只在所有冻结来源一致时创建新 run 并设置 `retry_of_run_id`。
- 用定向、并发、回归、静态和差异检查验证。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/models/workflow_run.py` | create | 新增 11 态 Run、冻结运行记录、transition、认证 actor 与 load receipt readiness 严格模型及生命周期校验 |
| `backend/services/workflow/run_service.py` | create | 新增服务端来源冻结、HMAC token 校验/映射、canonical fingerprint、幂等创建、状态原子流转、receipt 守卫、retry 与安全错误合同 |
| `backend/database.py` | update | 增量新增显式、幂等 `create_workflow_run_tables`，创建三张 run-owned 表、必要索引、append-only trigger、来源不可变与状态版本 guard；未新增通用 events/outbox |
| `backend/tests/test_workflow_run.py` | create | 新增 run/token/idempotency/回滚/并发/状态/transition/retry/fake receipt/DB guard 定向测试 |
| `docs/exec/exec_deck_007_backend_workflow-run.md` | create | 本 task 唯一正式执行报告 |

### 兼容性修正记录

首次把 Run schema 直接置于全局 `create_tables()` 后，本任务测试 `15/15` 通过，但前置回归出现 `2 failures + 1 error`：既有 Preflight/Binding 合同明确要求仅初始化其依赖时不存在 `workflow_runs`，且 Binding 历史测试会自行创建最小同名表。

未修改禁止范围内的既有测试，而是把同一 schema 改为 Run 服务启用时显式、幂等初始化。修正后本任务测试增补至 `16/16`，Preflight + Binding 回归 `21/21` 全部通过。该失败未被静默跳过。

## 5. 验收条件逐项结果

| # | 验收条件 | 结果 | 证据 |
|---|---|---|---|
| 1 | 保留 SUO-198 字段并新增 §11.1 字段 | PASS | `WorkflowRun` 严格模型与 schema 字段逐项对应 |
| 2 | workspace/actor 仅认证上下文派生且不可变；唯一域精确 | PASS | `AuthenticatedActorContext`、Preflight+Binding 双重 identity 校验、三字段 UNIQUE、不可变 trigger、跨 workspace 测试 |
| 3 | fingerprint 服务端 canonical 计算且不含 token/preflight ID | PASS | `_semantic_fingerprint` 只读取冻结来源、lock digest、voice source/retry provenance；fresh equivalent preflight 返回相同 run |
| 4 | 合法状态机且终态不可复活 | PASS | transition allowlist、terminal guard、confirmed→continuing/completed、rejected/cancelled/failed 路径测试 |
| 5 | 同 scope/key/语义完整 token 校验后返回原 run，新 token 原子映射 | PASS | exact replay、过期后 exact replay、fresh equivalent token 测试 |
| 6 | key/语义或 consumed-token identity 绑定冲突统一 fail closed | PASS | key/voice/actor/workspace 冲突矩阵均抛 `IDEMPOTENCY_CONFLICT`，异常不含原 run ID |
| 7 | run/token/initial transition 原子，并发只产生一个 run | PASS | 4 个创建故障注入点全部回滚；双连接并发仅 1 run、1 token consumption、1 initial transition |
| 8 | retry 新 run，继承冻结来源 | PASS | fresh preflight retry 产生新 ID、设置 `retry_of_run_id`、逐字段继承 |
| 9 | 改输入/插件/版本/快照/lock 不得伪装 retry | PASS | retry 对完整冻结来源字典做等值校验；changed input 定向测试证明拒绝且 token 未消费 |
| 10 | 来源不可变；receipt 仅 NULL→值一次 | PASS | DB provenance trigger 与直接 UPDATE 拒绝测试 |
| 11 | 每次真实变化与 append-only transition 原子 | PASS | `status_version == transition_seq`、transition UPDATE/DELETE trigger、transition 故障回滚测试 |
| 12 | queued→running 仅消费 fake/stub receipt 投影 | PASS | 错 run/lock/digest/not-ready 全部拒绝，匹配投影成功；未实现 receipt 表、entries 解析或下游逻辑 |

## 6. 测试与验证

### 已执行测试

1. 本 task 定向：

   ```text
   PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_workflow_run -v
   ```

   结果：`16 tests`, `OK`。

2. 前置最小回归：

   ```text
   PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_workflow_preflight backend.tests.test_deck_plugin_binding -v
   ```

   结果：`21 tests`, `OK`。

3. 静态编译：

   ```text
   PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m py_compile backend/models/workflow_run.py backend/services/workflow/run_service.py backend/database.py backend/tests/test_workflow_run.py
   ```

   结果：exit `0`。

4. 差异格式：

   ```text
   git diff --check
   ```

   结果：exit `0`，无 whitespace error。

5. 路径闭集核验：对 `git status --short --untracked-files=all` 与本次创建/修改记录交叉核验。

   结果：本 task 实际写入仅为第 4 节五个允许路径；工作树其他既有脏文件均未修改、覆盖、删除或重置。

### 非失败提示

- 本任务以包路径运行时，若干 fixture 输出既有 warning：`Memory workspace config backfill skipped: No module named 'memory_workspace_defaults'`。命令 exit `0`，所有断言通过；该 warning 来自 `backend/database.py` 既有可选 backfill import，不影响本 task SQLite 合同。

### 未执行 / 未验证

- 未做真实 `DECK-008` runtime load receipt 联调：下游尚未实现，本 task 按授权仅用 fake/stub readiness projection 验证边界。
- 未做 API/E2E：API 路由与前端不在允许范围；服务/数据库合同已由单元和最小集成测试覆盖。
- 未运行全仓测试：任务只要求最小相关验证，且工作树含大量无关并行改动；已执行指定定向与前置回归。

## 7. 风险与阻塞

- 阻塞：无。
- 风险：Run schema 采用服务启用时显式初始化，以保留 Preflight/Binding 的“无 pseudo run storage”既有合同。未来装配 Run API 时必须实例化 `WorkflowRunService`（或显式调用 `create_workflow_run_tables`）后再访问三张表。
- 风险：真实 receipt provider 必须与本实现一致地对 `lock_json` 做 sorted/minified canonical JSON SHA-256；`DECK-008` 联调时需要核对此摘要合同。
- 风险：SQLite `BEGIN IMMEDIATE` 可保证当前单节点并发收敛；多节点/其他数据库迁移仍需下游按同一唯一域和事务语义实现。
- 需要上游澄清：无；真实 receipt 联调由 `DECK-008` owner 承担。

## 8. 完成状态

- [x] 已完成实现
- [x] 已完成定向测试
- [x] 已完成前置回归
- [x] 已完成静态与差异检查
- [x] 已记录全部变更与首次回归失败/修正
- [x] 已满足本 task 验收条件
- [x] 可进入 review / audit

建议 Paperclip 最终状态：`done`。本 Issue 内无剩余实现或真实 reviewer/monitor 等待路径。

## 9. 回滚建议

- 回滚文件：删除本 task 新增的 `backend/models/workflow_run.py`、`backend/services/workflow/run_service.py`、`backend/tests/test_workflow_run.py`、本报告；在 `backend/database.py` 中仅逆向移除 `create_workflow_run_tables` 增量。
- 回滚方式：使用版本控制生成并应用只覆盖上述五个路径/区段的 inverse patch；不得对脏工作树执行 reset/checkout，不得移除前序 manifest/lock/install/binding/preflight schema。
- 数据注意事项：若环境已创建 run 表且已有数据，代码回滚前应先导出 `workflow_runs`、`workflow_run_token_consumptions`、`workflow_run_transitions`；不要直接 DROP，以免丢失不可变执行证据。

