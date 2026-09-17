<!-- [Input] Better Auth 1.7.4 installed source, Admin auth composition, canonical auth/device contract and isolated PostgreSQL harness. -->
<!-- [Output] Executable RFC 8628 public-contract, transaction, rotation and disclosure validation plan. -->
<!-- [Pos] Coordinator-owned Device Flow validation stage; Admin owns protocol implementation, Dream owns consumer behavior. -->
<!-- [Sync] 2026-09-15: public contract passed; require an Admin error-boundary fix and a zero-disclosure atomic rerun. -->

# Admin Device Flow 公开合同验证计划

## 背景与问题

Admin 已组合 `oauthProvider()` 与 `oauthDeviceAuthorization()`，并禁用会签发 Better Auth Session token 的 `/token`、`/device/token`。现有单元测试覆盖认证组合与 Dream 退役路径，但尚未从已安装 Better Auth 1.7.4 的公开生产入口验证 RFC 8628 的完整状态机、OAuth token 兑换、refresh 轮换和并发消费。

已核实的 1.7.4 源码规定：`POST /api/auth/device/code` 建立 `pending` 记录；`GET /api/auth/device?user_code=...` 在存在 Admin Session 时以条件更新绑定用户，并只向绑定用户投影 client、scope 和 resource；`POST /api/auth/device/approve` 与 `/device/deny` 使用 `userCode`；设备在 `POST /api/auth/oauth2/token` 使用 `urn:ietf:params:oauth:grant-type:device_code` 兑换 OAuth token。`/api/auth/device/token` 属于 Session Device Flow，不能作为本轮成功路径。

## 目标与边界

- 在身份已验证的具名隔离 PostgreSQL 中，通过 Admin 的真实 `handleAuthRequest` 和公开 HTTP 路径验证协议，不直接调用插件内部 handler 或复制状态机。
- CLI 使用已注册 public client，不提供固定 client secret；scope 与 resource 必须由 Admin 配置和 OAuth client/resource 关系限制。
- Root 负责数据库复制/fixture、秘密注入、事务故障与最终保存检查；Luna 只执行不创建 schema、不接触正常数据库的确定性公开请求。
- 不执行真实 Google 登录，不把隔离 Session 当成真实账户验收；登录后的 device 上下文恢复使用隔离已认证 Session 验证。
- 不改 Dream Runtime、SSE、共享文件系统、资源策略、admission/lease 或 `.claude-tmp` 协议。
- 当前轮先验证实现与文档一致；只有源码或公开回执证明缺陷时才修改产品代码。

## 概念与规则

- `device_code` 是设备端持有的一次性兑换凭据；`user_code` 只用于浏览器恢复和审阅上下文，二者都不是用户身份。
- `verification_uri` 指向 Admin 授权页，`verification_uri_complete` 只携带 `user_code`；浏览器登录和 return 参数不能改变 client、scope 或 resource。
- 插件内部状态保持 `pending`、`approved`、`denied`；产品页面显示可操作状态，不重命名第三方持久化状态。
- pending 首次轮询返回 `authorization_pending`；过快轮询返回 `slow_down` 并增加 5 秒间隔；拒绝返回 `access_denied`；过期返回 `expired_token`；未知、错误 client、重复消费返回相应 `invalid_request`、`invalid_client` 或 `invalid_grant`。
- Admin 的 ORM 事务先锁定 Device/Refresh 记录，再由 Better Auth adapter 和 OAuth provider 完成状态更新与 token 持久化。响应未知时按原 token/code 与原 client 恢复，禁止换请求 ID 或盲目重复产生 grant。
- OAuth access token、refresh token、Google token、OIDC ID token、Better Auth Session token用途不同；Dream Resource Server 只接受满足 issuer、audience、算法、时间、subject、client 和 scope 的目标 OAuth access token。
- `device_code`、`user_code`、Session、access/refresh token、私钥、密码、DSN 不进入版本库、任务消息或公开测试回执；回执只记录摘要、行数、状态码和不含秘密的断言。

## Optimized Prompt

You are the primary RFC 8628 integration-validation owner for Admin Better Auth 1.7.4 and the Dream resource server. Use the exact installed package source, Admin `createAdminAuth`/`handleAuthRequest`, canonical architecture contract and a proven named disposable PostgreSQL database. Verify the real public endpoints rather than plugin internals: device authorization at `/api/auth/device/code`, browser review at `GET /api/auth/device`, decisions at `/api/auth/device/approve` and `/api/auth/device/deny`, and OAuth exchange/refresh at `/api/auth/oauth2/token`. Confirm that `/api/auth/device/token` remains disabled and cannot issue a Session token. Seed only the configured public device client, allowed Dream resource, canonical subject link and isolated login Session through Admin-owned schema/ORM-compatible fixtures; never put a client secret in the CLI request. Exercise valid code fields, verification URIs, scope/resource projection, unauthenticated review, authenticated context binding, approve, deny, pending, slow_down with interval increase, expiry, invalid client, invalid scope/resource, single consumption, duplicate and concurrent exchange, refresh issuance when allowed, rotation, replay rejection or exact supported recovery, revocation, and Dream JWT/JWKS enforcement. Preserve the installed plugin's internal status names and compare every response to actual 1.7.4 behavior. Use row/advisory locks and full transaction rollback for injected storage or final-response faults; unknown commit recovery must prove token/grant cardinality. Root owns database creation, credentials, fault injection and destructive fixtures; Luna executes the bounded provider-free public request suite after fixture readiness. Do not contact Google, normal PostgreSQL or normal user data. Scan all owned artifacts for credentials and token material, archive only scrubbed receipts with commands, cwd, exit codes, assertion counts, target identity and preservation evidence. Treat any harness inability separately from a business failure, fix proven product mismatches, rerun only affected gates, and do not claim real Google, real-user or full-business acceptance from this isolated stage.

USER REQUIREMENT:
Validate the complete Admin-owned RFC 8628 Device Flow and Dream OAuth consumer contract against the installed versions, with DTO/ORM boundaries, public production paths, isolated database safety and verifiable results.

## Optional Enhancers

- 在本机正常服务具备 Google 登录状态后，追加一次真实 public-client 授权与 Dream API 调用；单独标记为真实验收。
- 在协议公开验证通过后，追加浏览器授权页视觉与返回上下文 E2E；不重复执行底层数据库故障测试。

## 所属项目、责任与依赖

| 项目/责任人 | 责任 | 依赖 | 输出 |
| --- | --- | --- | --- |
| Admin 任务 | Better Auth composition、公开路由、OAuth client/resource、Drizzle schema、事务与 token authority | 已注册 identity schema、capability、严格配置 | 源码修复（如需）、Admin 合同和测试 |
| Dream 任务 | 授权导航、旧路由 410、JWT/JWKS resource server、scope 检查 | Admin issuer、resource、client/capability | consumer 回归与产品失败反馈 |
| Root | exact-version 源码审计、隔离 DB/fixture、故障与保存验证、证据归档 | 现有 owned PG 及正常 DB 不变证明 | 可复核命令、回执、风险与状态 |
| Luna | provider-free 公开 HTTP 与确定性回归 | Root fixture-ready、无 secret 参数 | 实际退出码和断言回执 |

依赖顺序为 exact 1.7.4 事实冻结 → 隔离目标身份核验 → public client/resource/subject/Session fixture → 公开流程 → 并发/故障/保存 → Dream verifier → 文档与证据 gate。SystemConfig、Workspace 等数据迁移可并行，但不能改写认证表或共享隔离 fixture。

## 需要读取的证据

- Admin：`app/lib/auth/server.ts`、`config.ts`、`dto.ts`、transaction/repository、公开 auth Route Handler、identity Drizzle schema/migration、授权页面及已有 auth tests。
- 安装源码：`@better-auth/oauth-provider/dist/index.mjs`、OAuth `/oauth2/token` extension grant、`better-auth/dist/plugins/device-authorization/routes.mjs`。
- Dream：BFF auth start/callback/device 页面、退役 auth routes、JWT/JWKS verifier、capability client 和实际 API auth dependency。
- 文档：Admin canonical contract、两项目 `auth.md`/`auth-device.md`、数据库 ownership、验证矩阵与发布顺序。
- 官方资料只用于解释 RFC/产品边界；实际 endpoint、字段和状态以锁定依赖源码为准。

## 接口、数据与配置变化

本阶段预期不新增业务 API；若公开验证发现问题，修复仍限于现有 Better Auth route composition、严格配置和 ORM transaction wrapper。Device 请求 DTO 为 form/json 中明确字段，不接受外部 `user_id`、`actor_id` 或 `canonical_user_id`。认证 schema 和索引只由 Admin Drizzle 管理；测试不得 runtime DDL，fixture 仅写已迁移表。配置使用 issuer、resource、origins、public device client ID、scope 与过期策略，不硬编码部署地址或业务主体。

## 正常流程、失败与状态转换

1. Device client 请求 code；Admin 校验 client、scope、resource 后持久化 pending，并返回 RFC 字段。
2. 未登录浏览器只能看到 code/status；登录后条件绑定当前 Session 主体，页面展示 client/scope/resource。
3. 当前主体 approve 或 deny；另一主体、无 Session、已处理或过期请求失败且不改变决定。
4. pending 轮询返回 `authorization_pending`；时间间隔不足返回 `slow_down` 并推进 interval；deny/expiry 为终态。
5. approved code 在 `/oauth2/token` 单次消费并签发目标 OAuth token；并发只能一个成功，重复不能产生第二组持久化 token。
6. refresh 在允许时绑定原 client/resource/scopes，旧 refresh 原子轮换；重放、撤销和失效返回实际 1.7.4 错误并不复活 grant。
7. Dream 接受正确 token，拒绝 Session、Google、ID token、错误算法/issuer/audience/time/scope/kid。
8. 存储错误返回 503 并回滚；最终响应丢失通过原凭据查询/重试语义证明数据库最终结果，不盲目重复写入。

## 验收标准与命令

- source-contract gate：解析安装源码和 lockfile，输出版本、真实端点、字段、状态与 SHA；无 parse error。
- public-flow gate：运行公开 `Request`→Admin handler，覆盖 code/review/approve/deny/poll/exchange，断言状态、headers、字段和数据库基数。
- concurrency/fault gate：相同 code/refresh 并发与选择性异常，断言单消费、全事务回滚或单一最终提交。
- consumer gate：Dream verifier 的 signature/alg/issuer/audience/time/sub/client/scope 与 JWKS cache/refresh tests。
- preservation gate：目标外 identity 行、此前 public domain fixture 与正常数据库标识/行数不变。
- disclosure/docs gate：owned artifacts secret scan、Markdown inventory、相对引用与文件头同步全部通过。

所有执行回执必须包含工作目录、完整命令、实际退出码、断言数、隔离目标名称摘要和关键输出。测试目标身份不明确、normal DB、凭据缺失或 migration head 不匹配时 fail closed。

## 当前核验结果与修复门禁

具名隔离目标 `ink_auth_data_codex_test_792494523a17_deviceflow81` 已通过公开合同续测：累计 59 个公开请求、509 项断言，覆盖 public client、pending/slow_down/deny/expiry、单次和并发兑换、refresh 轮换与零重用重放失效、Dream principal 与 ES256 验证。实际 access-token `aud` 同时包含 Dream resource 与 OAuth userinfo audience；只读 scope 不签发 refresh token。这两项按 1.7.4 的实际行为写入现行契约，不按旧 harness 预期修改产品。

首次 Device 写入故障验证证明事务已进入回滚边界，同时揭示 Better Auth/Better Call 的默认未知异常日志会输出 Drizzle 查询参数；参数包含动态 `device_code` 与 `user_code`。该次原始回执只保留为 `0600` 私有证据，公开回执已经脱敏，后续故障步骤立即停止。Admin 必须启用已安装 1.7.4 的异常重抛边界，使未知 ORM/插件异常跳过 Better Call 的 `console.error`，由 `handleAuthRequest` 返回 `Cache-Control: no-store` 的 `503 {"error":"temporarily_unavailable"}`。

原子阶段只有在修复后续测同时满足以下条件时通过：三个选择性写入故障均返回通用 503，125 个关系逐字节回滚，故障对象全部清理，产品处理期间 `console.error` 调用数为零；真实最终 `COMMIT` 后响应丢失只留下一个 grant，原 device code 重试返回 `invalid_grant`，客户端按新 Device Flow 恢复。续测脚本只导出汇总 proof，永不导出 child stdout/stderr 或异常对象。

该门禁已通过；实际命令、1,429 项断言、历史泄露处置和适用范围见 [Device Flow81 日志边界与原子恢复回执](../exec/admin-auth-data-verification/deviceflow81-log-boundary-atomic.md)。

## 风险与回滚

- `prepareProtocolRequest` 的自定义锁或诊断顺序可能与插件内部更新重复；以公开响应和并发基数判断，不靠源码推测宣布问题。
- public client 的 client authentication、refresh issuance 和错误码由 1.7.4 实际实现决定；文档偏差先修文档，产品安全/一致性偏差才修代码。
- 故障 harness 只允许命名 target 的事务代理；任何目标身份不匹配立即停止。
- 产品修复按同一 forward-only Admin migration/API capability 发布；测试 fixture 可删除，正常业务数据和既有 tag/release 不回滚或移动。
