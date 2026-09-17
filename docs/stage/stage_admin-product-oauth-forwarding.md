<!-- [Input] Admin OAuth Product scopes, Dream opaque Browser session and existing strict Product DTO clients. -->
<!-- [Output] Executed plan for retiring Dream Product signing and forwarding verified OAuth delegation. -->
<!-- [Pos] Current Product authentication consolidation stage after PostgreSQL closure. -->
<!-- [Sync] 2026-09-16: implement the single Admin token authority across Dream Product reads and writes. -->

# Product OAuth 委托链收敛

## Optimized Prompt

You are an Expert Prompt Architect and senior OAuth, Python BFF, Next.js,
DTO/ORM and PostgreSQL engineer. Complete the Product portion of the Admin/Dream
refactor using the current source as evidence. Admin already verifies ES256 OAuth
access tokens, resolves the token subject to the stable canonical user and performs
all Product database access through strict DTOs, domain services, repositories and
transactions. Dream's public Product routes already receive the access token from
the opaque same-origin Browser session, but a legacy client still discards that
delegation and signs an HS256 Product token from a caller-side canonical user ID.

Remove that duplicate Dream token authority. Read routes must authenticate the
Admin OAuth actor with `product:read`; write routes must use `product:write`.
Represent the verified principal as an immutable internal actor DTO containing the
canonical ID, granted scopes and hidden access token. Forward only the access token
in the HTTP Authorization header. Never place a user ID in request bodies, query
parameters or identity override headers. Admin must derive and revalidate the
canonical/platform identity from the token before its Product repository runs.

Delete the Dream HS256 signer and its secret/issuer/audience/client configuration.
Keep the existing strict Pydantic request/response DTOs, response field firewall,
origin checks, preview/execute protocol, optimistic version, idempotency, bounded
responses, one-call no-retry policy and safe error mapping. Preserve browser UI,
subscription rules, Gateway eligibility, Runtime, SSE and shared filesystem
behavior. Admin unavailability or missing scope must fail closed; never fall back to
Dream PostgreSQL or a locally signed token.

Update functional file headers, folder contracts, current Product architecture and
the historical stage index. Add deterministic tests proving exact scope selection,
actor-to-token forwarding, absence of signer configuration, response-subject
binding and rejection of caller user IDs. Restart only the task-owned Dream backend,
reauthorize the existing browser through public login, then validate subscription
context and any free-plan renewal through public Product endpoints before retrying
one bounded real model message. Record commands, exit codes and business receipts
without storing access tokens, device codes, secrets or message contents.

USER REQUIREMENT:

Admin 是唯一认证和数据库访问服务；Dream 数据库访问改造成接口时遵从
DTO → domain service → Repository/Drizzle，并且后续授权无需用户重复确认。

## 本阶段接口和状态

| 环节 | 输入 | 执行模块 | 输出/失败 |
|---|---|---|---|
| Browser session resolve | opaque handle | Next BFF → Admin browser session | server-only OAuth access token；失败401/503 |
| Product route auth | OAuth bearer + method | Dream `routers/product.py` | immutable `ProductSessionActor`；read缺`product:read`或write缺`product:write`返回401 |
| Product transport | actor access token + strict DTO | Dream `AdminProductClient` | 单次Admin API调用；不发送canonical user ID，不重试非幂等写 |
| Product authorization/data | OAuth subject + Product DTO | Admin auth → Product service → Repository/Drizzle UOW | active canonical/platform identity和owner过滤；事务结果/安全错误DTO |
| Subscription command | preview receipt + expectedVersion + idempotency key | Admin Product transaction | applied/idempotent receipt；版本冲突409，未知结果由同key恢复 |

## 保持不变

- Dream 的订阅页面、产品文案、模型选择、Agent Runtime、SSE 和共享文件系统职责不变。
- Admin 的 Plan、Subscription、Entitlement、Allowance、Gateway 和事务规则不变。
- Browser 不得到 access/refresh token；Dream Python 不保存或签发新的用户凭据。
- Product API 不接受 `userId`、`x-user-id` 或其他调用方主体覆盖。

## 验收

- `test_admin_product_client.py` 验证同一 OAuth bearer、严格 DTO、no-retry、幂等和响应防火墙。
- `test_product_bff_routes.py` 验证 read/write scope、actor DTO、无 caller user ID 和Admin响应主体绑定。
- source scan 验证 `services/admin_product` 无 PostgreSQL、SQL、HS256 signer 或 Product JWT secret。
- 浏览器重新授权后，订阅 context/catalog 与命令走公开入口；随后重试真实 Gateway model message。
