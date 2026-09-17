<!-- [Input] Current dirty-safe Dream source tree, accepted Admin contract catalog and prior108-entry baseline inventory. -->
<!-- [Output] Current production DB-access closure implementation, inventory and verification decisions. -->
<!-- [Pos] Cross-project coordinator evidence for the source cutover and remaining runtime acceptance. -->
<!-- [Sync] 2026-09-17: make the closure gate audit Git candidate source rather than ignored runtime/cache artifacts. -->

# Dream 生产数据库入口关闭复盘

## 背景与问题

旧清单基于 baseline `7d38715c`，当时 Dream 仍保留大量直接数据库模块和内部调用者。迁移过程按当前源码持续区分生产入口、测试/importer 边界、SQL/驱动/事务证据和调用者；旧清单和单次关键字搜索均不能替代现行源码门禁与正常业务运行验证。

## 目标与边界

现行源码已经关闭 Dream 全部生产数据库入口。Dream 仅传严格 DTO、服务身份与已验证用户委托，Admin Service/typed Repository/Drizzle 执行权限、锁、事务与持久化。Runtime、SSE、共享文件和临时目录协议不变。正常数据库 migration/capability、角色 ACL 与真实业务运行验证仍是独立发布门禁。

## 概念与规则

候选按 production、tests、script/importer 分开。AST SQL 字符串、psycopg/数据库模块 import、连接/事务调用和旧 helper call 分别计数；同名 `execute` 不自动算数据库访问。动态 SQL、工厂注入和 startup/health 另列。迁移时每个调用均关联实际 Admin operation；原子步骤保持 Admin 单事务，Dream 没有 PostgreSQL fallback。

## 现行裁决（2026-09-17）

- `backend/tests/test_postgres_runtime_sql_boundaries.py` 以 Git 已跟踪文件和未忽略的待提交文件为源码清单，扫描完整 `backend` 生产 Python 图及 `frontend/app`、`frontend/packages` 生产脚本；tests/e2e、虚拟环境、构建产物、缓存目录与 `backend/data/` 运行时工作区不进入清单。任何可提交的数据库驱动/客户端、旧 `database` import、SQL 语句字面量或 Next 侧数据库 DSN 都会使门禁失败。
- 原 `backend/database.py`、`backend/persistence/`、`backend/schema/` 与生产 SQL repository 已退出生产图；历史实现只保存在明确命名的测试 fixture/harness。
- 部署脚本拒绝 Dream 的 `DATABASE_URL`/旧数据库环境文件；运行代码只使用 Admin 严格 DTO 客户端，Admin 使用 Zod DTO、domain Service、typed Repository 与 Drizzle。
- 本节后续扫描数字与 pending 描述是各 Registry 实施时点的历史回执。它们不覆盖上述现行源码裁决，也不能替代尚未执行的正常库切换和真实业务验收。

## 2026-09-17 门禁源码清单修正

### Optimized Prompt:

You are the Dream production database-closure gate maintainer. Correct the deterministic source inventory after a machine restart without deleting or changing user runtime data. Work only in `/Users/dmeck/project/ink-dream-memory`; preserve concurrent user and Agent changes. Use the Git index plus untracked files that are not excluded by repository ignore rules as the candidate source graph. Continue to scan every candidate backend production Python file and Next server source for database drivers, database abstractions, SQL literals, database credentials, pool lifecycle and retired repository paths. Exclude tests and generated build/cache paths according to the existing contract. Treat `backend/data/` as ignored runtime workspace content rather than repository source. Treat a retired directory containing only ignored bytecode cache as retired, while any tracked or non-ignored file added below that path must fail the gate.

Do not weaken the DTO/ORM architecture rule: Dream production code may call only typed Admin clients; Admin Pydantic/Zod DTO validation, domain Service, typed Repository, Drizzle and Unit of Work remain the persistence path. Do not modify Runtime, Runner, ThreadFactory, EventBus, SSE, turn/resume/cancel, resource-policy LKG/admission/lease, shared filesystem behavior or `CLAUDE_CODE_TMPDIR`. Update the test file header, test folder contract and this stage receipt. Validate with the focused pytest module, Python compilation, Markdown local-link inventory and `git diff --check`. Report the original false-positive categories, exact working directory, commands, exit codes and key counts. A passing static gate is production-source closure evidence; it does not replace normal-service runtime socket/process evidence or real business acceptance.

USER REQUIREMENT:
继续跨项目认证与数据库接口重构；后续工作只在 Dream 与 Admin 主目录进行，数据库接口遵从 DTO/ORM，不能把忽略的运行时工作区或旧字节码缓存误判为 Dream 生产数据库访问。

### 执行范围与不变量

| 项目 | 责任与依赖 | 修改范围 | 保持不变 | 失败处理 |
| --- | --- | --- | --- | --- |
| Dream | Root 维护生产数据库关闭门禁；依赖现有 Admin DTO/ORM 合同已经生效 | `backend/tests/test_postgres_runtime_sql_boundaries.py`、测试目录合同和本阶段回执 | 公开 API、数据库接口、配置、Runtime、SSE、资源策略和共享文件系统 | Git 源码清单不可取得、生产源码出现数据库访问或退休路径重新出现时门禁失败 |
| Admin | 本轮不改代码；继续作为数据库访问和事务所有者 | 无 | Zod DTO → Service → typed Repository → Drizzle/UOW | Dream 不得以 Admin 不可用或门禁异常为由回退 PostgreSQL |

正常流程是 Git 返回已跟踪与未忽略候选文件，门禁按生产路径和扩展名筛选后执行 AST/文本断言。忽略的运行时文件与缓存不参与结果；新增且可提交的生产文件立即参与。不存在状态迁移、接口、数据库或配置变化。本轮验收命令为 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_postgres_runtime_sql_boundaries.py`、`python -m py_compile`、Markdown 链接检查与 `git diff --check`。风险是过窄清单漏掉新增源码，因此清单同时包含未跟踪但未忽略的文件，并以 `backend/server.py` 存在、`backend/data/` 和 `__pycache__` 不存在的回归断言锁定边界。

### 执行回执

- 修正前在 `backend/` 运行聚焦 pytest，结果为 `3 failed, 3 passed`：磁盘递归把忽略的 `backend/data/agent-workspace/` 中第三方 Skill 源码计为 1,207 个数据库 import 和 10,981 个 SQL literal，并把仅含忽略字节码的 `backend/persistence/`、`backend/schema/` 判作生产目录。这是测试清单错误，不是 Dream 运行路径重新连接数据库。
- 修正后在相同目录运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_postgres_runtime_sql_boundaries.py`，exit `0`，`7 passed in 2.23s`。
- 在 Dream 根临时创建未忽略的 `backend/persistence/codex_database_closure_probe.py` 后只运行退休路径断言，pytest 按预期 exit `1` 并报告 `backend/persistence`；验证包装器清理探针后 exit `0`。该回执证明未提交候选源码仍会 fail closed，没有留下探针文件。
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m py_compile tests/test_postgres_runtime_sql_boundaries.py` 在 `backend/` exit `0`；两份受影响 Markdown 的本地链接检查为 `local_links=4 missing=0`；Dream 根 `git diff --check` exit `0`。
- 本地 `.venv/bin/ruff` 不存在，随后 `python -m ruff` 也确认模块未安装，分别 exit `127`/`1`；`pyproject.toml` 未声明 Ruff。本轮不把 Ruff 记为通过项，也没有为单文件测试修正改变依赖合同。

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
