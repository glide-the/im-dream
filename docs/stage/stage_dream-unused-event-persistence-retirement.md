<!-- [Input] Unreferenced Dream EventEmitter PostgreSQL implementation, historical tests and live pure event contracts. -->
<!-- [Output] Executable plan and receipt for retiring the unused database path while preserving event DTO/consumer behavior. -->
<!-- [Pos] Dream production database-access closure stage; no new Admin operation is needed for an absent business caller. -->
<!-- [Sync] 2026-09-16: plan unused event persistence retirement before implementation. -->

# 未使用 Event 持久化路径退役

## Optimized Prompt

You are an Expert Prompt Architect and senior Python, PostgreSQL, DTO and
architecture engineer. Remove Dream's unused `EventEmitter` database
implementation after proving it has no production caller. Repository evidence
shows the class is imported only by its own unit tests and an opt-in legacy
PostgreSQL integration test; current business execution, Runtime, SSE and
Admin DTO clients do not instantiate it. The immutable `EventEnvelope` DTO and
pure ordered `EventConsumer` remain separate, useful contracts without database
access.

Delete `backend/services/events/event_emitter.py`, remove its legacy integration
case, and refactor `test_events.py` to construct strict `EventEnvelope` fixtures
directly while retaining payload validation, sensitive-field rejection,
deduplication, ordering and timeout coverage. Do not invent an Admin write
operation for a path with no business caller, and do not remove the `events`
schema or historical design records in this stage. Record the retired source as
historical in the current migration inventory so Markdown links do not point to
a deleted file.

Preserve current Runtime, EventBus/SSE, Workflow state, resource-policy LKG,
shared filesystem and transaction behavior of active modules. Update affected
file headers, test inventory, stage index and database migration inventory. Run
the focused event/consumer suite and the remaining PostgreSQL integration file
in collection/skip-safe mode, compile touched Python, rerun the source-only
database closure scan, validate Markdown references and run `git diff --check`.
Preserve unrelated dirty files.

USER REQUIREMENT:

继续完成 Admin 统一认证与数据库访问服务；数据库改造成接口遵从 DTO/ORM，
Dream 生产运行路径不得保留 PostgreSQL 访问或 fallback；已有合规部分不制造无意义
接口或代码。

## 目标、证据与边界

| 模块 | 已有证据 | 本阶段动作 | 保持不变 |
|---|---|---|---|
| `EventEmitter` | 全仓生产搜索零调用者；只被两个测试文件导入 | 删除未接线的SQL/persist-first实现和专属测试 | 不声称任何真实业务迁移或Admin capability |
| `EventEnvelope` | strict frozen Pydantic DTO，验证必需payload与敏感字段 | 测试直接构造DTO | 字段、枚举、校验和安全projection |
| `EventConsumer` | 纯内存顺序、去重和gap timeout | 保留并继续测试 | handler、aggregate version和alert语义 |

若未来产品流程需要持久化canonical event，应在真实调用方、权限、事务与幂等需求
明确后新增具名 Admin DTO → Service → typed Drizzle Repository 操作；不得复活Dream
SQL或通用事件表CRUD。本阶段不改变数据库结构。

## 验收标准

- production中不存在`event_emitter.py`、`EventEmitter`或其PostgreSQL import。
- Event DTO/consumer核心回归通过，剩余integration文件不再导入被删除模块。
- source-only清单相应减少一个SQL和driver模块，并继续如实保留其他数据库入口。

## 实施与验收回执

- 全仓生产搜索确认零调用者后删除 `event_emitter.py`；旧PostgreSQL integration
  case同步删除，`events` schema和历史设计文件保持。
- `test_events.py` 现在直接构造strict `EventEnvelope`，继续覆盖十类payload和
  pure `EventConsumer`；focused suite实际 `exit 0`：`6 passed, 3 skipped, 5
  subtests passed in 0.15s`。三个skip是未提供显式隔离`TEST_DATABASE_URL`的其余
  integration cases，不是业务失败。
- 受影响Python文件 `py_compile` 实际 `exit 0`。
- source-only AST实际 `exit 0`、`parse_errors=[]`：550模块、76 production
  entry、42 SQL模块、400 SQL literal、14 driver/database import模块、37 legacy
  helper调用、168个Admin operation名。其余数据库模块仍未关闭。
