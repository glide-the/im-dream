<!-- [Input] Registered Admin workflow-context.resolve DTO/ORM path and the now-unreferenced Dream SQL resolver. -->
<!-- [Output] Executable plan and receipt for retiring duplicate Dream workflow-context database code. -->
<!-- [Pos] Dream production database-access closure stage; Admin remains the sole workflow authority. -->
<!-- [Sync] 2026-09-16: plan legacy Workflow context resolver retirement before implementation. -->

# Workflow Context 旧数据库解析器退役

## Optimized Prompt

You are an Expert Prompt Architect and senior Python, TypeScript, Drizzle,
authentication and DTO engineer. Retire Dream's duplicate PostgreSQL Workflow
context resolver after proving every production caller uses the registered
Admin `workflow-context.resolve` operation. The current public Chat ingress
authenticates its OAuth actor through `AdminRequestAuth`, sends only the owned
Thread ID in a strict DTO, and receives an immutable `AdminWorkflowResolution`.
Admin's typed Drizzle Repository and service validate the Thread owner, complete
retry graph, launch-message provenance, Workspace owner, Deck binding, revision,
plugin/runtime snapshot and active/terminal status inside the data service.

Delete the unused Dream `dream_thread_binding.py` SQL implementation and its
obsolete unit suite, remove stale imports from `story_workflow_application.py`,
and strengthen the existing Admin Workflow consumer tests with a production
source fence. Preserve the current ten-field context DTO, nullable ordinary or
terminal Chat result, actor/Thread binding, capability hashes, OAuth scope,
server-persistence delegation and Runtime activation behavior. The service test
injection seam may remain for provider-free tests, but normal composition must
fail closed when the immutable Admin snapshot is missing; it must never reopen
PostgreSQL or construct authority from a caller user ID.

Do not port the retry algorithm back into Dream, add generic CRUD, add a schema
or migration, change the Thread/Run state machine, or alter Runtime, SSE,
resource-policy LKG, shared filesystem or `CLAUDE_CODE_TMPDIR`. Update file
headers, folder contracts, stage index and migration inventory. Run Workflow,
Chat ingress and Agent service tests, Python compilation, a source-only database
closure scan, Markdown reference validation and `git diff --check`. Preserve
unrelated dirty files.

USER REQUIREMENT:

继续完成 Admin 统一认证与数据库访问服务；数据库改造成接口遵从 DTO/ORM，
Dream 生产运行路径不得保留 PostgreSQL 访问或 fallback。

## 目标、依赖与边界

| 项目 | 当前证据 | 本阶段责任 | 保持不变 |
|---|---|---|---|
| Admin | `workflow-context.resolve` 已注册 strict DTO、capability 和 typed Drizzle Repository；producer覆盖retry/provenance/owner/status | 继续作为唯一数据库与权限执行方；本阶段无需Admin改动 | operation/schema hash、事务内事实读取和409冲突语义 |
| Dream | 公开Chat在创建turn owner前调用`AdminRequestAuth.workflow_context`；Service消费immutable snapshot | 删除零生产调用者的SQL resolver、旧测试和两个未使用import；增加source fence | 请求只含Thread ID、nullable/十字段结果、actor/Thread匹配和Runtime行为 |

正常流程为当前 OAuth actor 请求 Admin Workflow context，Admin 返回 active context
或 `null`，Dream 将同一 snapshot 绑定到 turn persistence 和 Agent service。Admin
不可用、scope不足、capability漂移、DTO不合法或绑定冲突时沿现有错误路径在模型
执行前失败；禁止 Dream 回退数据库。普通Chat与完整终态retry链仍得到 `null`。

## 验收标准

- production 不再存在或导入 `dream_thread_binding.py`，Story application 不保留
  两个无用resolver symbol。
- Dream consumer仍验证 strict DTO、schema/operation capability、immutable actor和
  Thread绑定；公开Chat与Agent Service回归通过。
- source-only回执中该模块的SQL、database import和helper候选消失；其余生产数据库
  入口继续列为未完成，不能据此宣称全仓迁移结束。

## 实施与验收回执

- 删除无生产调用者的 `dream_thread_binding.py` 与其旧算法测试；同时删除 Story
  application两个未使用import和ThreadFactory已不可达的旧Service error用例。
- `test_admin_workflow_data.py` 增加production source fence。Workflow consumer、
  公开Chat、Agent Service和ThreadFactory实际 `exit 0`：`151 passed, 9 subtests
  passed in 1.29s`。
- 受影响Python模块 `py_compile` 实际 `exit 0`。
- source-only AST实际 `exit 0`、`parse_errors=[]`：551模块、77 production
  entry、43 SQL模块、403 SQL literal、15 driver/database import模块、37 legacy
  helper调用和168个Admin operation名。其余模块仍由后续DTO/ORM阶段处理。
