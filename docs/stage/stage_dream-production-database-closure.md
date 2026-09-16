<!-- [Input] Current dirty-safe Dream source tree, accepted Admin contract catalog and prior108-entry baseline inventory. -->
<!-- [Output] Current production DB-access closure implementation, inventory and verification decisions. -->
<!-- [Pos] Cross-project coordinator evidence for the source cutover and remaining runtime acceptance. -->
<!-- [Sync] 2026-09-16: close the Dream runtime pool/SQL graph and isolate historical database tooling under tests. -->

# Dream 生产数据库入口关闭复盘

## 背景与问题

旧清单基于 baseline `7d38715c`，当前 worktree 已加入多个 Admin strict client，仍保留大量直接数据库模块和内部调用者。必须按当前源码重新识别生产入口、测试/importer边界、SQL/驱动/事务证据和调用者，不能用旧清单或一次关键字搜索宣称完成。

## 目标与边界

现行目标是关闭 Dream 全部生产数据库入口。Dream 仅传严格 DTO、服务身份与已验证用户委托，Admin Service/typed Repository/Drizzle 执行权限、锁、事务与持久化。Runtime、SSE、共享文件和临时目录协议不变。

## 概念与规则

候选按 production、tests、script/importer 分开。AST SQL 字符串、psycopg/数据库模块 import、连接/事务调用和旧 helper call 分别计数；同名 `execute` 不自动算数据库访问。动态 SQL、工厂注入和 startup/health 另列。每个待迁移调用必须关联实际 Admin operation 或明确 pending，不能把多个原子步骤拆成无一致性的 HTTP 调用，也不能添加 Dream PostgreSQL fallback。

## Optimized Prompt:

You are the cross-project migration coordinator performing a read-only current-source closure audit after the registered77 component has been released. Scan the actual dirty-safe Dream worktree without editing, formatting or importing runtime modules. Read the prior machine inventory, current Admin strict client modules, direct database and persistence roots, current router/service/Runtime callers, startup and health paths, and the accepted Admin operation catalog. Parse Python AST for imports, database helper calls, SQL-looking literals, cursor/connection/commit/rollback/savepoint/transaction behavior and syntax errors. Separate production from tests, scripts, importer and explicitly allowed fixtures. Identify dynamic factories and imported aliases so a single grep result cannot be called complete.

Produce an owned machine-readable report with source SHA256, file/function/line, evidence categories, known Admin replacement or pending aggregate, transaction/concurrency notes and explicit false-positive classification. Report counts for scanned production modules, SQL-bearing modules/literals, driver/persistence imports, legacy database helper callsites, Admin client modules and parse errors. Compare current results with the prior baseline only as historical evidence; do not subtract a callsite unless its actual current production path no longer imports/calls SQL or an old database abstraction. Preserve Runner, ThreadFactory, service, EventBus, SSE, turn/resume/cancel, resource LKG/admission/lease, shared filesystem and CLAUDE_CODE_TMPDIR behavior. Recommend the next minimal aggregates by call graph and transaction boundary, with SystemConfig/default Workspace work already owned by active tasks. Do not execute PostgreSQL, real-user actions, provider/model calls, DDL, migration, builds or browser tests.

USER REQUIREMENT:
继续把 Dream 所有生产数据库访问迁到 Admin，接口严格遵从 DTO/ORM；保留 Dream Runtime 与共享文件系统，并以当前代码和可核验结果安排后续实现。

## 验收

扫描器必须正常退出、AST parse errors为空，报告自身与所扫描源码SHA，不包含环境值/Token/DSN；文档记录实际命令、cwd、退出码和关键计数。结果是迁移清单证据，不是“全量无PG”运行证明。

## 当前实际扫描结果

Root只读扫描器先产生两份历史分类输出：首版把自然语言 `Create` 和任意对象的 `execute` 计入，第二版收紧SQL形态与连接receiver；它们不作为最终计数。最初冻结清单命令 `python3 /private/tmp/ink-auth-migration-validation/scan-dream-current-db-closure.py`（cwd Dream Root，读取 ef6e worktree）exit0，未import业务模块、未访问数据库；当时扫描504个Python模块、production候选82，53个SQL模块、504个SQL literal、43个数据库/driver导入模块、110处旧helper和470处具名事务/连接调用，20个Admin data模块和80个operation名称。

Agent Session Context 提交 `2321844e` 后，用相同 AST 逻辑写入新的当前机器清单，exit0：扫描511个Python模块、production候选81；52个SQL模块、496个SQL literal、38个数据库/driver导入模块、95处旧helper和457处具名事务/连接调用；24个production模块消费Admin data client，共88个静态operation名称；非production候选103，legacy schema reference仍166，parse errors为空。该增量包含同期 SystemConfig、Workspace、Editor、Reflections 与 Session Context 变更，不能全部归因于单一提交。

这些是当前源码候选，不是运行可达性或完成断言。优先剩余聚合按原调用链划分为：首 turn Session Context、Story Workspace输出/confirmation/guidance/launch内部UOW、Plugin安装/发布/撤销/Runtime materialization、MCP repository、Notion connector、Reflections后台 task/Picture/Report和startup/health/capability。每批必须先用原事务边界定义单一Admin业务操作，再由Dream统一客户端替换；不能对照88个已存在operation名称直接把52个SQL模块标为迁移完成。

机器清单：[dream-current-db-closure-scan.json](../exec/dream-current-db-closure-scan.json)。

## 2026-09-16 实现状态

- `backend/server.py` 不再加载 `DATABASE_URL`，也不再启动或关闭 Dream connection pool。
- 原 `backend/database.py`、`backend/persistence/`、`backend/schema/` 已迁入 `backend/tests/legacy_database.py`、`backend/tests/legacy_persistence/`、`backend/tests/legacy_schema/`，只由 pytest 历史 fixture 使用。
- SQL migration/bootstrap/Gateway probe 脚本迁入 `backend/tests/harness/`；明确命名的 E2E 脚本仍属 harness，不进入生产模块图。
- Story Workspace SQL Repository、旧 lifecycle/reconcile 和零调用 Workflow Run service 已删除；活跃路径使用 Admin Registry185–191 严格 Pydantic DTO。
- Diary importer与Session tools使用公开OAuth/Profile/Session DTO，不读取数据库凭据。
- Dream部署模板、README和生产依赖不再投影PostgreSQL DSN；psycopg只属于开发测试组。

静态门禁同时扫描 `server.py`、routers、services、Claude Agent 和服务端 libs，拒绝数据库驱动、旧 `database` import、连接池生命周期与 Story Workspace 旧 SQL 文件。该门禁必须与公开入口运行回归共同使用，不能单凭关键字扫描宣称真实业务验收完成。

## Reflections 后修正版扫描

Reflections 提交 `c49fca694af560e21ecd16aab5efe29167729c27` 后，Root 再次运行 dirty-safe AST 扫描。首次新运行发现 worktree 中的 `backend/.venv` 被旧 source selection 当成生产模块；该 2575-module 结果只保留为 harness 诊断，不进入关闭计数。修正版显式排除点目录、`node_modules` 与 `__pycache__`，实际 exit0：522 个仓库 Python 模块、80 个 production entry、52 个 SQL 模块/496 个 literal、34 个数据库驱动或旧 database import 模块、66 个旧 helper call、457 个连接/事务调用、26 个 Admin data 模块/113 个静态 operation name，parse errors 为空。

Reflections 三个生产路由已从旧 helper 清单消失。当前按调用闭包继续处理：本地导入/首次登录（Registry101 正在验证）、当前用户图片历史（阶段设计已冻结）、Deck Chat Context 与默认 Deck、Claude Plugin、Story/Deck workflow、MCP/Notion、资源策略和最终 startup/init。`backend/database.py` 只能在所有生产消费者和动态 composition root 都关闭后移除；最终还要用运行时 fence 证明公开入口没有回退。

- [修正说明与聚合计数](../exec/admin-auth-data-verification/dream-db-closure-after-reflections-c49.md)
- [机器清单](../exec/admin-auth-data-verification/dream-db-closure-after-reflections-c49-source-only.json)


Luna只读一致性门禁实际exit0：报告entries179、production82、source changed空、failures空；核验机器清单内部计数、扫描时全部候选源码SHA、无凭据pattern、Root/ef镜像和两仓diff-check，不import业务模块或访问数据库。见[原始门禁](../exec/admin-auth-data-verification/dream-current-db-closure-scan-gate.md)。
