<!-- [Input] Current production import graph, Admin Run DTO routes and three unreachable Dream SQL seams. -->
<!-- [Output] Zero-caller SQL retirement plan and source/test verification boundary. -->
<!-- [Pos] Dream production database closure cleanup before migrating live Artifact/Runtime domains. -->
<!-- [Sync] 2026-09-16: remove legacy Run, reload guard and manifest uniqueness SQL paths. -->

# Dream 不可达 Runtime SQL 边界退役阶段

## 本轮优化指令

**Optimized Prompt:**

根据当前生产 import 图，退役三条没有运行时调用者的 Dream SQL 边界：删除仅由测试导入的
remote reload guard；从 Deck Plugin manifest validator 删除无调用的数据库唯一性参数和 SQL，
保留全部纯 schema/source/capability 校验；删除公开 Preflight/Run 路由已改用 Admin strict DTO
后遗留的 `StoryWorkflowRunApplicationService`、router protocol/factory 和测试 monkeypatch。
更新当前架构与术语文档，增加 source fence，并运行 Admin Run、Preflight、manifest、Agent Session
及 Story Workspace 路由回归。不得改变 Run API、错误结构、状态机、Runtime、SSE、共享文件系统
或 Admin DTO → Service → typed Drizzle Repository 合同。

**Optional Enhancers:** 后续单独迁移仍可达的 Dream Artifact、Story Index、Session/Runtime SQL；
本阶段不提前设计其接口。

## 目标与证据

- `backend/routers/story_workspace.py` 的 Run read/create/retry/cancel 已直接构造
  `Run*InputDTO` 并调用 `AdminRunData`；legacy factory 没有 `Depends` 或生产调用者。
- `remote_interaction_guard.py` 仅由 `backend/tests/test_agent_session.py` 导入；运行时代码没有 import。
- `manifest_validator.validate_manifest` 的生产与测试调用都未传 `db` 或
  `exclude_release_id`；release 唯一性由 Admin Drizzle 约束和 Repository 承担。

## 所属项目与依赖

| 项目 | 责任 | 依赖 |
|---|---|---|
| Admin | Workflow Run strict DTO、Service、typed Drizzle Repository、事务和权限 | Registry 已发布，operation hash 不变 |
| Dream | Run 请求 DTO 构造和响应投影；manifest 纯 artifact 校验 | 当前 Admin OAuth actor 和 capability |
| 本阶段 | 删除三条不可达 SQL seam，修正文档和测试围栏 | 不新增 Admin operation 或 migration |

## 修改范围

- 删除 `backend/services/claude_agent/remote_interaction_guard.py` 及唯一孤立测试。
- `manifest_validator.py` 删除数据库参数、release SELECT 和 `_assert_unique`。
- `story_workflow_application.py` 删除 legacy Run class/singleton/factory；router 删除无调用 protocol/factory。
- 更新测试 SQL inventory、public symbols、路由防回退测试与架构说明。

## 接口、数据库与配置

- Admin Run API、DTO、capability/hash、Drizzle schema 和 migration 均不变。
- Dream HTTP 方法、路径、状态码和 JSON 投影均不变。
- 删除的 reload guard 从未连接生产入口；其删除不会新增或开放 reload 行为。
- 不增加环境变量、数据库凭据或 fallback。

## 保持行为与失败处理

- Run read/create/retry/cancel 继续由 Admin 校验 OAuth actor、Workspace、Preflight、幂等和状态转换。
- Admin 不可用、权限拒绝、capability 缺失和未知提交结果继续使用既有 route error handler。
- manifest 的 schema、SemVer、source allowlist、敏感字段、capability 和 degraded mode 校验保持。
- Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel、LKG、共享文件和
  `CLAUDE_CODE_TMPDIR` 不变。

## 验收

- 生产源码不存在三个退役 symbol/SQL seam。
- Admin Run/Preflight 路由测试证明数据库 fallback 不会被调用。
- Agent Session 与 manifest 纯验证回归通过。
- Story Workspace public symbol 和剩余 PostgreSQL boundary 测试通过。

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_admin_run_routes.py \
  tests/test_admin_default_workspace.py \
  tests/test_admin_preflight_routes.py \
  tests/test_admin_preflight_execution.py \
  tests/test_deck_plugin_manifest.py \
  tests/test_agent_session.py \
  tests/test_story_workspace_public_symbols.py \
  tests/test_postgres_runtime_sql_boundaries.py
PYTHONPATH=. .venv/bin/python -m compileall -q routers services
```

## 风险与回滚

- 历史文档可能仍提及 legacy class；现行架构与术语表必须改用 Admin DTO 名称，历史
  `prompt-rounds.md` 保留原文作为索引。
- 若发现真实 production import，停止删除并恢复对应 symbol；当前 source graph 和测试均未发现。
- 回滚仅恢复三条 seam，不移动 Admin tag、operation hash 或数据库 migration。
