<!-- [Input] Dream current-user picture routes, legacy SQL behavior, Admin social picture DTOs and daily_pictures Drizzle schema. -->
<!-- [Output] Prompt-architect plan for two current-actor picture history reads and three Dream route replacements. -->
<!-- [Pos] Remaining production database-access migration stage; distinct from friendship-authorized picture access. -->
<!-- [Sync] 2026-09-15: freeze current-user list/range/full behavior, ownership and no-fallback validation before implementation. -->

# 当前用户图片历史数据接口迁移

## 背景与问题

Dream `backend/routers/pictures.py` 的 `/api/pictures`、`/api/pictures/range` 与 `/api/pictures/{date}/full` 仍分别调用 `database.get_daily_pictures`、`get_daily_pictures_range` 和 `get_daily_picture_full`。三个 helper 直接读取 PostgreSQL。Admin 已有 `friendship.timeline` 与 `friendship.picture-full`，但它们要求已接受的好友关系，不能被当前用户读取复用为权限判断。`daily_pictures` 表和 Drizzle schema 已由 Admin 管理，无需结构变更。

## 目标与边界

- Admin 增加两个只读业务操作：`picture-history.list` 接受可选 `start_date/end_date` 与 `limit`，同时服务 Dream 的普通列表和范围列表；`picture-history.full` 按日期读取当前 actor 最新原图。
- 采用 strict Zod DTO → Service → typed Drizzle Repository → 调用方 UOW。canonical user ID 只从 OAuth principal 取得，wire 中不得包含 actor、friend、表列或 SQL 选择器。
- Dream 保留三个公开路径、日期错误反馈、列表/范围的公开响应结构和前端图片展示；统一 Pydantic consumer 调用 Admin，不保留数据库 fallback。
- 与好友图片操作共享稳定的 picture/time codec 和 Drizzle 表字段，当前用户读取不执行 friendship 检查，也不复制社交状态机。
- 本轮只有读操作，不新增 receipt、迁移、图片生成、文件系统写入或清理。

## 概念与规则

`picture-history.list` 输入使用 nullable `YYYY-MM-DD` 日期和非负安全整数 `limit`；Dream 继续把空白日期规范化为 null，并对非日期返回原 400 产品错误。Admin 只读取当前 actor 的行，缩略图为空时返回原图，按日期倒序，保留 nullable prompt 与精确 nullable timestamp。Dream 普通列表继续把空 prompt 映射为 `""`，范围列表保持当前结果字段；接口不返回 owner 或数据库 ID。

`picture-history.full` 只接收有效日期，从当前 actor 的同日记录中按创建时间倒序取一张原图；无记录返回 nullable，Dream 维持 `404 Picture not found for this date`。OAuth 缺失、scope 不足、capability 缺失、Admin 超时或响应结构错误均 fail closed；Dream 不能调用旧 helper。只读请求允许由上层按照既有客户端策略有限重试，错误响应不得伪装为空成功。

## Optimized Prompt

You are the Admin/Dream picture-history migration owner. Read both repositories' AGENTS/Agent/folder/rule contracts; Dream `backend/routers/pictures.py`, its three exact legacy helpers and frontend callers; Admin `socialFriendshipDto/Repository`, timestamp codecs, operation handler/registry, `daily_pictures` Drizzle schema and restricted-role integration harnesses. Implement exactly two current-actor read operations: `picture-history.list` with strict nullable ISO-date range and nonnegative safe limit, and `picture-history.full` with one strict ISO date. Use strict Zod DTOs, a Service that enforces OAuth dream:read and rejects entity delegation, and a typed Drizzle Repository inside the existing Admin data UOW. Derive ownership only from the verified canonical principal. Reuse stable picture/timestamp DTOs where their fields match, but do not reuse friendship authorization for the owner path and do not expose friend_id, user_id, SQL, table or column selectors.

Preserve the actual product behavior: thumbnail falls back to the full image; rows are ordered by date descending; range boundaries are inclusive; prompt and created_at retain their existing null/serialization semantics; full-image lookup returns the newest same-date row or null. Dream keeps `/api/pictures`, `/api/pictures/range` and `/api/pictures/{date}/full`, the current validation/404 messages and frontend response shape. Both list routes may call the same Admin operation with null bounds. Admin unavailable, malformed output, missing capability and permission denial must produce an explicit failure; never fall back to Dream PostgreSQL.

Add deterministic DTO/service/repository/registration tests and a provider-free isolated PostgreSQL contract covering owner/other separation, no-filter/start/end/both/zero-limit reads, thumbnail fallback, duplicate dates, full newest selection, invalid dates, closed selectors, missing scope, wrong entity grant, unavailable Admin/capability and exact source-compatible projection. Add Dream consumer/route tests and a runtime fence that makes all three legacy helpers raise while the public routes still succeed through the fake Admin client. Update file headers, `.folder.md`, API/architecture and database-closure evidence. Run focused Vitest/pytest, typecheck/compile/lint, isolated restricted-role contract, AST scan and `git diff --check`. Commit Admin first, freeze its commit/tree/operation hashes, then commit Dream against those exact values. Do not push, modify normal PostgreSQL, use a real account/model, or disturb existing Plugin changes.

USER REQUIREMENT:
将 Dream 全部生产数据库访问迁入 Admin，数据库接口严格遵从 DTO / ORM 设计，保留当前产品交互和数据权限。

## 项目、责任与依赖

| 项目/责任人 | 责任 | 依赖 |
| --- | --- | --- |
| Admin 任务 | 两项 strict DTO、Service、typed Repository、Handler/Registry 与受限角色合同 | Registry101 本地导入先独立提交；复用现有 unified schema capability，不新增 migration |
| Dream 任务 | 统一 Pydantic consumer、三个公开路由替换、旧 helper 运行时封锁 | Admin commit/tree/两项 contract hash 冻结后接入 |
| Root | 源行为核对、隔离数据库准备、跨仓 hash 与 AST/业务验收 | 两项任务分别完成技术回执 |

## 状态转换与失败处理

1. Dream 验证日期与 limit，并把两个列表路径规范化为同一 Admin DTO。
2. Admin 校验服务、OAuth actor、scope、capability 和闭合 DTO 后读取 actor 自有行。
3. Admin 返回严格投影；Dream 只做公开响应兼容映射。
4. 无图由 full 操作返回 null，Dream 映射为既有 404；权限、超时、capability 与结构错误保持失败。
5. 任何失败都不查询 Dream 数据库，也不改变图片、好友、Runtime 或共享文件系统状态。

## 验收与风险

- 三个 Dream 路由零 `database` import、零旧 picture helper 调用，运行时把旧 helper 设为抛错仍可通过 Admin fake。
- Admin wire 无用户/好友/物理选择器，Repository 只使用 Drizzle schema，current actor 与 other actor 数据严格隔离。
- 范围边界、缩略图 fallback、同日最新原图、prompt 与 timestamp 映射和原 400/404 行为有源对照断言。
- 风险是历史 `date` 为 text，范围 cast 遇到损坏值可能导致查询失败；本轮不默默跳过或清洗历史数据，按明确数据错误 fail closed，并把真实修复留给单独受控数据迁移。
- 隔离测试不能冒充指定账户的正常业务验收；正常数据库与日常 Admin 可见性在最终公开入口阶段单独验证。
