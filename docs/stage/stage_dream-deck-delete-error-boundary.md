<!-- [Input] Admin-owned Deck delete DTO/ORM operation and the remaining Dream database import used only to format a 409 message. -->
<!-- [Output] Executable plan and receipt for removing that transitive database dependency while preserving public feedback. -->
<!-- [Pos] Dream production database-access closure stage; Admin continues to own deletion checks and persistence. -->
<!-- [Sync] 2026-09-16: plan the Deck delete error-boundary cleanup before implementation. -->

# Deck 删除错误边界收敛

## Optimized Prompt

You are an Expert Prompt Architect and senior Python, DTO, ORM and API
engineer. Close the remaining Dream database dependency in the public Deck
router. Verified evidence shows all five public Deck mutations already call
named Admin operations with strict Pydantic DTOs; Admin's typed Drizzle
Repository performs ownership, dependency, transaction and persistence work.
Dream still imports its legacy `database` module solely to instantiate
`DeckDeletionConflict` and obtain one of four user-facing messages after Admin
returns the closed `DeckDeleteBlockedDetailsDTO` reason.

Replace that presentation-only dependency with a route-owned, closed mapping
for the four DTO-enforced reasons: `child_decks`, `related_threads`,
`runtime_history` and `referenced_records`. Preserve the exact existing message
text, HTTP 409 status, invalid-detail fail-closed behavior and generic fallback
for an otherwise valid response without details. Do not add a database call,
generic CRUD endpoint, caller-supplied identity, retry, schema change or
migration. Keep the existing Admin operation contract, DTO hashes, receipt
recovery and one-operation write behavior unchanged.

Update file headers, router/test folder contracts, the migration inventory and
the stage index. Add a source fence proving the production route has no
`database` import or reference, retain behavioral coverage for every allowed
reason, run the focused Deck/Voice route suite, compile touched Python files,
rerun the source-only database closure inventory, validate Markdown references
and run `git diff --check`. Preserve unrelated dirty files.

USER REQUIREMENT:

继续完成 Admin 统一认证与数据库访问服务；数据库改造成接口遵从 DTO/ORM，
Dream 生产运行路径不得保留 PostgreSQL 访问或 fallback。

## 目标、依赖与影响范围

| 项目 | 当前证据 | 本阶段责任 | 保持不变 |
|---|---|---|---|
| Admin | `deck.delete` 已使用 strict input/output/error DTO 与 typed Drizzle Repository | 继续执行 owner、引用关系和事务检查；本阶段无代码、schema 或 migration 变化 | capability、operation hash、事务和权限语义 |
| Dream | `routers/voices.py` 的删除路由只把 Admin closed reason 转为既有 409 文案 | 删除仅用于文案的 `database` import，并以闭合集合映射反馈 | 路由、当前用户 OAuth、请求 DTO、receipt、HTTP 状态与四条文案 |

正常流程为 Dream 校验当前用户和 write scope，调用一次 Admin `deck.delete`；
成功返回原响应，Admin 报告闭合集合内的依赖原因时返回对应 409。Admin
不可用、DTO 不合法、错误 code/status 不匹配或提交结果未知时继续走既有安全失败
和 receipt 恢复路径。本阶段不改变文件系统、Runtime、SSE、资源策略或共享
workspace。

## 验收标准

- production `backend/routers/voices.py` 不导入或引用 `database`。
- 四个合法 reason 的状态码和原文案完全一致，未知/多余字段继续 fail closed。
- Deck/Voice 相关 provider-free 路由测试、Python 编译、Markdown 引用和 diff
  检查通过。
- 新的 source-only 回执如实列出全仓其余 SQL/driver/helper 候选；本阶段仅声明
  Deck 公共路由的传递数据库依赖关闭。

## 实施与验收回执

- `voices.py` 已移除 `database` import；四个 DTO reason 使用闭合映射，缺少
  details 仍返回原 `referenced_records` 通用文案。
- focused Deck/Voice route suite 实际 `exit 0`，`173 passed in 1.85s`；覆盖四类
  409文案、错误details严格解析、current OAuth scopes、schema/operation hash、
  one-operation写入与unknown receipt恢复。
- Python `py_compile` 与 `git diff --check` 实际 `exit 0`。
- source-only AST实际 `exit 0`、`parse_errors=[]`：553模块、44 SQL模块、404
  SQL literal、16 driver/database import模块、37 legacy helper调用；
  `voices.py` 的SQL、driver、legacy helper和transaction列表均为空。全仓余项仍按
  inventory迁移，本回执不声明Dream已整体关闭PostgreSQL。
