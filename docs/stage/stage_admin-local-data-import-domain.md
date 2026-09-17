<!-- [Input] Dream legacy localStorage import routes, current Admin Session/Picture/Preferences/Report repositories and OAuth identity boundary. -->
<!-- [Output] Prompt-architect implementation plan for atomic DTO-to-ORM local-data import and first-login completion. -->
<!-- [Pos] Remaining production database-access migration stage; Admin owns persistence and Dream retains legacy payload interaction. -->
<!-- [Sync] 2026-09-15: freeze current transaction, ownership and replay semantics before implementation. -->

# 本地数据导入与首次登录状态迁移阶段

## 背景与问题

`backend/routers/auth.py` 已把注册、密码登录和本地 logout 关闭，并通过 Admin 获取当前 profile，但三个生产入口仍直接调用 Dream `database.py`：`/api/import-local-data`、`/api/import-calendar-recovery` 和 `/api/mark-first-login-completed`。`database.import_user_data` 在一个事务中写入 Session、每日图片、用户偏好和分析报告；`set_first_login_completed` 用 update-or-insert 写首次登录状态。当前 Session upsert 还能把冲突 ID 的 owner 改成当前用户，未知提交后重试也会重复插入图片和报告。

## 目标与边界

- Dream 保留首次登录页面、localStorage 读取、旧 JSON 字符串解析和用户可见的导入计数；Dream 只把规范化严格 DTO 交给统一 Admin client。
- Admin 增加一个原子 `local-data.import` 聚合操作和一个幂等 `first-login.complete` 操作，经 Zod DTO → Service → typed Drizzle Repository → 单一 UOW 持久化。
- 两个导入入口复用同一聚合操作；日历恢复仅发送 Session 子集。不得把原事务拆成 Session/Picture/Preferences/Report 多个 HTTP 写入。
- 身份只来自已验证 OAuth/BFF actor。输入不得包含 `user_id`、subject、表列名、SQL 或数据库连接；Dream 不保留 PostgreSQL fallback。
- 沿用现有主键和表，不增加 migration。若实现证明需要新的幂等键或约束，必须先在 Admin Drizzle 提交单独 expand migration 和 capability，再注册操作。

## 概念与规则

Dream adapter 逐类解析旧 localStorage 字符串，并产生闭合的版本化 DTO：Session 只含 `id/name/editor_state`，Picture 只含 `date/image_base64/prompt`，Preferences 只含四个现有字段，Report 只含 `type/data/all_notes/timestamp`。旧格式中某一类别无法解析时，该类别不进入 DTO；其他已成功类别仍可导入，返回计数必须以实际发送并由 Admin 接受的记录为准。日志只能记录类别和计数，不能打印用户正文、图片、Token、主体或原始异常内容。

Admin 在一个事务中验证所有项目的 owner 与结构后写入。Session ID 已属于同一 actor 时沿用现有 upsert；属于其他 actor 时拒绝整个事务，不能转移 owner。图片和报告的重复请求由 operation receipt 恢复原提交结果，不能在网络未知结果后再次插入。偏好保持现有全量 import merge 语义，原始 JSON 数值表示不得经浮点转换。`first-login.complete` 对已有/缺失 preference 行都返回同一完成状态，并可安全重复调用。

## Optimized Prompt

You are the Admin/Dream local-data import migration owner. Read the exact three Dream routes in `backend/routers/auth.py`, `database.import_user_data`, `database.set_first_login_completed`, their frontend callers, current Pydantic Admin client patterns, and Admin Session, Social Picture, User Preferences, Analysis Report, Receipt and Audit repositories before editing. Preserve the user-facing first-login/import interaction and the original one-transaction import boundary while removing every production Dream database call.

Define exactly two business operations: OAuth `local-data.import` and OAuth `first-login.complete`. Their Zod and Pydantic DTOs must be strict, versioned and source-compatible, reject caller-supplied user/subject/table/column/SQL fields, and derive the canonical owner only from the authenticated Admin principal. `local-data.import` accepts normalized Session, Picture, Preferences and Report collections and executes them through one Admin Service and typed Drizzle Repository/UOW. Reuse current domain DTO codecs and source-compatible JSON normalization where possible. Do not expose generic CRUD or split the aggregate into separate HTTP writes.

For Session upsert, permit update only when the existing row belongs to the same canonical actor; a foreign-owner ID conflict rejects the entire transaction. Preserve the current same-owner name/editor-state update behavior. Keep picture/report insertion and preference import behavior, but use the existing operation receipt and audit boundary so an identical request ID replays the original committed result and a different payload conflicts. Unknown commit recovery must query the original receipt; Dream must never blindly retry a non-idempotent aggregate. `first-login.complete` atomically inserts or updates `first_login_completed=1`, is idempotent for repeated requests, and returns the stored public result.

Dream keeps parsing legacy JSON strings at its product adapter. Preserve the existing category-independent parsing result: a malformed category contributes zero imported records while other successfully parsed categories may proceed. Validate individual normalized items before calling Admin, keep the visible success/count response shape, and replace raw `print`/traceback output with safe category/count diagnostics. Reuse the current Admin OAuth/BFF owner and unified client; no password, Google token, arbitrary user ID or database credential may be forwarded.

Update affected file headers, `.folder.md`, API/architecture documents and the production database closure inventory. Add deterministic DTO/service/repository/consumer tests for empty imports, every category, malformed legacy JSON, same-owner upsert, foreign-owner collision with full rollback, preference JSON fidelity, duplicate request replay, changed-input conflict, concurrent duplicate request, unknown final COMMIT recovery, first-login insert/update/repeat, Admin 401/403/503/capability failure and a runtime probe that makes both legacy Dream helpers raise. Use a named verified disposable PostgreSQL target only for migration/UOW integration. Run focused tests, typecheck/compile/lint, AST closure scan and `git diff --check`; route bounded isolated validation to Luna. Keep real account/browser/model acceptance separate.

USER REQUIREMENT:
将 Dream 全部生产数据库访问迁到 Admin，数据库接口严格遵从 DTO / ORM 设计，并保留现有产品交互和事务语义。

## 项目、责任与依赖

| 项目/责任人 | 责任 | 依赖 |
| --- | --- | --- |
| Admin 任务 | 两项 DTO、Service、typed Repository、receipt/audit、注册与契约测试 | 已冻结 Session、Preferences、Picture、Report schema；Reflections report 接口冻结后复用 codec |
| Dream 任务 | 旧 localStorage adapter、统一 client、三个路由替换、无 DB fallback | Admin operation/capability hash 发布 |
| Root | 源行为评审、隔离事务/恢复验证、AST 与真实首次登录验收 | 两侧提交和具名测试条件 |

## 状态转换与失败处理

1. Dream 解析每个旧类别：有效类别进入 normalized DTO；无效类别计数为零且不泄漏正文。
2. Admin 校验完整 DTO、当前 actor 和 capability 后开启单一 UOW。
3. 任一 ownership、DTO、约束或持久化失败回滚四类数据，并返回稳定错误。
4. COMMIT 成功写 receipt/audit；响应丢失时按原 request ID 读取原结果，不能重放插入。
5. 首次登录完成从 absent/0 进入1；重复1保持1。导入失败时不得自动标为完成。

## 验收与风险

- 三个 Dream 生产入口零 `database` import、零旧 helper 调用，Admin 不可用时明确失败。
- 聚合接口只有 typed DTO 与 Drizzle Repository，不接受业务 owner、SQL 或任意表列。
- 四类数据同事务；foreign Session 冲突、任一写故障和 receipt 故障均无部分提交。
- 最大风险是大图片/正文导致 transport body 超限。复用服务端 `DREAM_DATA_MAX_BODY_BYTES` 与现有字段约束，产品 adapter 在调用前给出可操作错误；不引入未经依据的业务配额。
- 真实验收使用指定正常账户和公开生产入口，并在日常 Admin 查询中核对结果；技术隔离结果不能冒充真实导入。
