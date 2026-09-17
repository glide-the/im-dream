<!-- [Input] Dream production import graph, plugin lifecycle SQL modules, Admin data-boundary target, and historical task/exec records. -->
<!-- [Output] Bounded retirement plan for plugin SQL implementations that have no production caller. -->
<!-- [Pos] Current-stage decision record; historical task and exec documents remain unchanged as dated evidence. -->
<!-- [Sync] 2026-09-16: prove revocation, rollback, and legacy materialization managers are test-only before retiring their Dream production-package SQL. -->

# Dream 无生产调用插件 SQL 退役阶段

## Optimized Prompt

在 Dream worktree 中基于 Python 生产 import/call 图核验 `deck_plugin.revocation_service`、`deck_plugin.rollback_manager` 与 `runtime_plugin.materialization_manager`。只退役除自身与测试外没有生产导入者的实现，不为不可达路径新建 Admin 接口。保留仍被生产入口调用的 `InstallationService`、`ReconcileService`、Story Workspace Runtime activation、Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel、共享文件系统和资源策略语义。把仍有价值的降级与 load-receipt 回归从退役 SQL fixture 中拆出；测试 fixture 可以构造严格 Pydantic 领域对象，但不得恢复 Dream 生产数据库访问。更新当前目录说明、数据库访问清单和源码闭包回执，保留历史 task/exec 原文。以零生产调用证据、定向回归、全量测试收集、`py_compile`、Markdown 相对链接和 AST 数据库闭包扫描作为验收。

## 背景与问题

三个模块位于 `backend/services/**` 生产包并包含 SQLite、PostgreSQL 或 runtime materialization SQL，因此会被生产源码闭包计入。当前调用图显示它们除自身和测试外没有导入者：公开 Deck Plugin 路由使用 `DeckPluginAdminService`/`InstallationService`，Story Workspace Runtime activation 使用 `ReconcileService`，并未实例化这三个 manager。继续保留会形成未接线的第二套数据库权威，并违反 Dream 生产服务不得保留数据库访问路径的目标。

## 目标与边界

- 删除三个生产不可达 SQL 实现及其仅验证退役实现的测试。
- 把 `DegradationService` 的独立回归移至独立测试文件。
- `test_runtime_plugin_reconcile.py` 继续验证活跃 `ReconcileService`、receipt、Run guard 与事务边界；它通过严格领域 DTO 构造已物化证据，不再调用退役 manager。
- `test_postgres_runtime_sql_boundaries.py` 不再为 SQLite revocation fixture 提供例外。
- 不改 Admin schema/API，不改活跃插件安装、回滚公开入口、Runtime 执行或文件缓存行为。本阶段没有生产调用方，因此无需制造 DTO/API。

## 所属项目、责任与依赖

| 项目 | 责任 | 依赖 |
| --- | --- | --- |
| Dream | 退役不可达实现、保留活跃回归、更新当前文档与闭包证据 | 当前生产 import 图、现有 Admin/Dream 分支 |
| Admin | 本阶段无代码变化 | 后续活跃 Deck Plugin 控制面迁移仍须 DTO → Service → Drizzle Repository |

## 文件与影响范围

- 删除：`backend/services/deck_plugin/revocation_service.py`、`rollback_manager.py`、`backend/services/runtime_plugin/materialization_manager.py`。
- 拆分/更新：`backend/tests/test_revocation_rollback.py`、`test_runtime_plugin_reconcile.py`、`test_postgres_runtime_sql_boundaries.py`。
- 文档：`backend/.folder.md`、`backend/tests/.folder.md`、当前数据库访问清单、stage/exec 索引和本阶段源码闭包回执。
- 历史 `docs/task/**`、旧 `docs/exec/exec_deck_*.md` 保留原文，并由当前清单标记为历史基线。

## 状态、失败处理与不变行为

1. 若发现任一非测试生产调用者，停止删除并把该能力规划为 Admin DTO → Service → ORM Repository 接口。
2. 若活跃 reconcile/receipt/Run 回归失败，恢复其严格领域证据 fixture，禁止跳过断言。
3. 删除后不得增加 Dream 数据库 fallback；Admin 不可用的活跃路径继续按其既有显式失败处理。
4. Runner、SSE、Runtime 配置、LKG、workspace、`CLAUDE_CODE_TMPDIR` 和共享文件权限不受本阶段影响。

## 验收标准与命令

- 生产源码对三个模块/类的 import 和引用均为零。
- `test_degradation_service.py`、`test_runtime_plugin_reconcile.py`、`test_postgres_runtime_sql_boundaries.py` 通过。
- 相关 Deck Plugin/Runtime 公共回归通过；全量 `pytest --collect-only` 成功。
- `py_compile`、`git diff --check`、修改 Markdown 的相对链接检查成功。
- AST 闭包回执显示 SQL 模块和 SQL 调用数下降，`parse_errors=[]`，且仍列出活跃 `installation_service` 与 `reconcile_service`。

## 风险

最大风险是把历史设计目标误当成当前生产入口。通过全仓库生产 import 图、路由 composition root 和测试拆分控制；历史文档不删除，便于追溯当时实现，但不再作为当前运行规范。

## 实际结果

- 生产 import/引用扫描：三个退役模块与类均为零；活跃 `InstallationService` 和 `ReconcileService` 保留。
- AST 闭包：生产模块 `296→293`、SQL 模块 `27→24`、SQL 调用 `422→389`、driver import 模块 `9→8`、连接相关调用 `1144→1089`，`parse_errors=[]`。
- 定向语法与首轮回归：`py_compile` exit 0；3 文件 15 项测试全部通过。
- Deck Plugin/Runtime/Workflow Run 相关回归：76 passed、1 skipped、35 subtests passed，exit 0。
- 全量测试收集：3703 tests collected，exit 0。
- 本阶段未新增 Admin API。原因是被删除实现没有生产调用方；active control-plane SQL 继续按 DTO → Service → Drizzle Repository 迁移。
