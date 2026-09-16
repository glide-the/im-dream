<!-- [Input] Normal Admin/Dream/Gateway/PostgreSQL services, the user-authorized existing account, and actor-bound public product routes. -->
<!-- [Output] Pre-mutation business scope plus append-only command and acceptance receipts for the 2026-09-16 normal cutover. -->
<!-- [Pos] Real-business acceptance record; contains no password, OAuth token, service credential, transcript body, or database DSN. -->
<!-- [Sync] 2026-09-17: record independent Admin browser login after adding the required local Session TTL. -->
<!-- [Sync] 2026-09-17: record read-only normal desired/effective resource-policy and fresh observer/LKG parity. -->
<!-- [Sync] 2026-09-17: record real Chrome Dream logout, client-local revocation, same-subject SSO re-entry and Admin-login isolation. -->
<!-- [Sync] 2026-09-17: preserve the Chrome control preflight failure and focused 27-test logout/session technical receipt. -->
<!-- [Sync] 2026-09-17: record corrective normal Admin ACL activation and public Notion service-token DTO/ORM validation. -->
<!-- [Sync] 2026-09-17: record independent Admin-session implementation, confidential service OAuth and current deterministic results. -->
<!-- [Sync] 2026-09-16: record real Device approval/exchange, Resource Server access, refresh rotation and replay-family invalidation. -->
<!-- [Sync] 2026-09-16: record independent refresh revocation, Device denial, Admin 0063 publication, Product OAuth forwarding, Gateway key rotation, Settings search and MCP replacement-auth findings. -->
<!-- [Sync] 2026-09-16: record exact legacy Google adoption, successful consent/return and the closed Better Auth audience-array repair. -->
<!-- [Sync] 2026-09-16: record saved Google callbacks, closure of redirect mismatch and the specified email account-not-found result. -->
<!-- [Sync] 2026-09-16: record real browser login, Google callback, identity-mapping and RFC 8628 pending/slow-down evidence. -->
<!-- [Sync] 2026-09-16: define the normal-cutover impact boundary before starting Dream browser or model mutations. -->

# 正常切换与真实业务验收记录

## 背景与问题

Admin 统一认证、Admin DTO/Service/Repository/Drizzle 数据访问以及 Dream 消费端已通过确定性和隔离验证。本轮在本机正常服务、正常 `ink-memory` PostgreSQL 和用户指定的既有账户上验证真实调用链，结果必须能由日常 Admin 查询；隔离数据库、影子账户、临时 Admin 或直接 SQL 业务写入不能作为验收结果。

## 目标与边界

- 只通过 Dream、Admin、OAuth 和业务 API 的公开生产入口完成用户操作。
- Dream 只持有 Admin 服务客户端配置和共享文件系统配置，不持有 PostgreSQL DSN。
- 产生的新 Session、Device grant、Thread、Run、Gateway request、结算和失败回执保留供复核。
- 不修改既有账户角色、订阅、历史正文、既有 Project/Episode 标题或资源策略 desired 值。
- 真实模型调用使用页面和 actor-bound API 返回的可用模型；不硬编码模型、Deck、Thread 或业务主键。

## 概念与规则

| 概念/事实 | 真相源 | 写入/同步责任 | 可见消费方 | 预期影响 |
| --- | --- | --- | --- | --- |
| 应用身份、Account 关联与 Session | Admin Better Auth 与 `identity` 数据 | Admin callback/session 服务 | Dream BFF、Admin 认证页面 | 新增/刷新本轮会话；既有主体 ID 和 Admin 角色不变 |
| Dream 产品访问授权 | Admin OAuth grant、scope、resource/audience | Admin OAuth Provider；Dream Resource Server 校验 | Dream 页面与 FastAPI | 本轮授权可新增；不授予 Admin 管理权限 |
| Device authorization | Admin RFC 8628 状态与 token 记录 | Admin device/OAuth 服务 | Admin 授权页、CLI 风格轮询客户端 | 覆盖允许、拒绝、pending、slow_down、过期/重复兑换、refresh/revoke；不把 Session token 当 access token |
| Deck 与模型选择 | actor-bound Admin DTO/产品 API | Admin 数据服务；Dream 只消费 | Dream Chat/Dream 页面 | 读取既有可用项并选择；Deck、订阅和模型目录保持不变 |
| Shared Thread/Run | Admin 数据服务中的 Thread/Run/消息记录 | Dream Runtime 编排，Admin DTO 事务持久化 | Chat、历史、Admin 查询 | 创建一个可复核 Thread/Run，验证继续、取消、SSE；既有 Thread 不变 |
| Project identity/title | `stories/<project>/project.yaml` 和 Admin 投影 | Agent 写文件；成功 Hook 发布并由 Admin DTO 持久化 | Story 索引、执行页 Project 标题 | 本轮基础对话不要求修改，保持不变 |
| Episode identity/title/content | `episodes/<EPxx>/` canonical artifacts | Agent 写文件；Hook 发布 | Episode API/工作台 | 本轮基础对话不要求修改，保持不变 |
| Run-private publication | `.dream/runtime/runs/<run-id>/artifact/` 与 manifest | Dream host-owned Hook | 服务端 reader、Admin 投影 | 仅在选定流程实际生成制品时新增；不得改写既有 Run |
| 共享文件与元数据 | 规范化 Thread workspace + Admin 文件元数据 DTO | Dream 写文件；Admin 原子保存元数据 | 文件下载、Thread 页面、Admin 查询 | 新文件只属于本轮 Thread；越界/符号链接仍拒绝；旧文件不变 |
| 资源策略 effective/LKG | Admin desired + Dream 内存 LKG | Admin 写 desired；Dream 后台 provider 应用 | Runtime admission/诊断 | 只读验证 revision/value；不得从 turn 主路径查询或修改 |

## 用户流程与成功标准

| 用户流程 | 受影响模块 | 数据与权限 | 验证方式 | 成功标准 | 失败/恢复路径 |
| --- | --- | --- | --- | --- | --- |
| Dream → Admin 登录 → Dream 返回 | Dream BFF、Admin Better Auth/OAuth | Account、Session、OAuth grant；无 Admin RBAC 提升 | 本机 Chrome 可见交互 + `/auth/session` | 返回原 Dream 路由，公开用户 DTO 可读，浏览器不可见 OAuth token | 失败保留 return transaction；重试不创建重复主体 |
| Google 登录与既有主体关联 | Admin `socialProviders.google` | Google Account 关联到稳定应用主体 | 可见 Google OAuth；再查公开 profile | 主体稳定、无按邮箱任意合并 | 外部挑战/账户条件单独记为真实验收未完成，不替换为模拟 |
| Device Flow | Admin device UI/token endpoints | public client、scope、resource、grant/token | 设备请求 + 可见批准/拒绝 + 轮询 | 错误码和状态符合 RFC 8628，refresh/revoke 生效 | 过期或已处理请求要求设备重新发起 |
| Run/Thread/SSE | Dream Chat、Runtime、Admin 191-operation API | actor-bound Thread/Run/message/Gateway/ledger | 页面创建并发送正常用户话术；观察 SSE、继续与取消 | UI 完成且 Admin 可查询关联记录；失败信息明确 | Admin/Gateway/Runtime 错误不回退 DB，不盲重试非幂等写 |
| 文件上传/读取 | Dream BFF/FastAPI、共享文件系统、Admin metadata DTO | Thread owner、路径和 metadata | 可见上传/读取；越权/非法路径负例 | 文件和元数据一致，失败可恢复，无越界/符号链接放行 | 元数据失败不把不完整对象展示为成功 |
| Dream 无 PostgreSQL | Dream 进程、Admin 数据 API | Dream env/进程/连接边界 | 配置清单、进程环境键、连接观察、公开流程 | Dream 无 DSN/driver连接，全部持久化经 Admin | Admin 不可用时明确失败，禁止本地 SQL fallback |

## 对话边界

真实模型消息只使用页面可见语义，例如“请简短回复你已经准备好继续这个对话”。消息不包含内部 ID、绝对路径、`.dream` 协议、Hook 指令或工具命令。若页面存在多个含义相同的目标，测试要求可见澄清，不能在脚本中替用户选择隐藏业务标识。

## 执行记录

后续命令、退出码、关键脱敏输出、Run/Thread/request 标识和未执行原因在本文件追加；任何失败先区分业务缺陷、设计错误或 harness 问题，再修复并重跑受影响流程。

### 2026-09-16 认证与 Device 第一轮

工作目录分别为 Admin `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory` 和 Dream `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`。本轮使用正常 `ink-memory` PostgreSQL 与本机 `localhost:3000/5173/8765` 服务；没有使用隔离账户、数据库副本或临时 Admin。

| 检查 | 入口/命令 | 退出码或 HTTP | 脱敏结果 | 结论 |
| --- | --- | --- | --- | --- |
| 既有主体关系 | read-only PostgreSQL probe；只输出主键、状态、映射存在性和口令验证布尔值 | `0` | active canonical user 1 条、active Admin member 1 条；Better Auth user/account、Dream subject link、Admin subject link 均为 0；第一轮提供的验收口令与两条旧 hash 均不匹配 | 密码登录 `401` 是正确 fail-closed；不能按同邮箱自动建立映射或覆盖旧 hash |
| Dream 登录入口 | Chrome `GET http://localhost:5173/auth/start?return_to=/` | Admin authorize `302` → sign-in `200` | callback/resource/client/scope/PKCE 均来自已注册配置，返回上下文保留 | Dream BFF → Admin authorize 主路径成立 |
| Google 外部身份 | Admin 页面标准 Google social sign-in | Google `400 redirect_uri_mismatch` | 应用已统一请求 `http://localhost:3000/api/auth/callback/google`；Google Cloud 当前未登记该精确 URI | 应用配置问题已关闭；真实 Google callback 仍受外部 OAuth client 配置阻塞，不能声明真实 Google 验收通过 |
| Device code + polling | `node --input-type=module` 调用公开 `/api/auth/device/code` 与 `/api/auth/oauth2/token` | harness `0`; create `200`; poll `400`, `400` | 必需字段齐全，`expires_in=1800`、`interval=5`；首次 `authorization_pending`，立即复轮询 `slow_down`；全部 `Cache-Control: no-store` | 正常未决和减速状态通过；device/user code 未写入本回执或命令输出 |
| Device 负例 | 同一公开 device authorization endpoint | harness `0`; 四项均 `400` | unknown client → `invalid_client`；unknown resource → `invalid_target`；外部 `user_id` → `invalid_request`；未授权 scope → `invalid_scope` | public client、resource、scope 与主体注入边界通过 |

尚未执行：真实 Google callback、显式旧主体 adoption、用户批准/拒绝、OAuth token 兑换、refresh/revoke、Dream Thread/Run/SSE/模型和文件流程。Google 控制台配置与可证明的既有账户登录方法必须分别解决；不得把 Device pending 技术回执或密码 `401` 当作完整业务验收。

### 2026-09-16 Google Cloud 回调与指定账户复核

用户在动作时确认修改现有 Google OAuth Web Client。控制台保存并重新读取后，以下 URI 与原两个旧回调并存：

- `http://localhost:3000/api/auth/callback/google`
- `https://ink-admin.suoxya.com/api/auth/callback/google`

随后从 Dream `GET /auth/start?return_to=/` 重新进入 Admin authorize 并点击标准 Google 登录。Google 已接受精确 `redirect_uri`，正常展示账号选择页，原 `redirect_uri_mismatch` 不再出现。选择“使用其他账号”并提交用户指定验收邮箱后，Google 返回“找不到此账号”；没有进入密码、同意或 callback，也没有创建 Better Auth user/account、subject link、Session 或 OAuth grant。

该结果把剩余条件从“Cloud callback 未配置”收敛为“指定邮箱不是当前可登录的 Google 账号”。不能改用浏览器中其他已登录 Google 账号创建新主体，也不能因此把不同 Google email/subject 自动映射到旧 Dream/Admin 记录。下一步需要用户明确指定一个可登录且允许关联的 Google 账号，或选择受审计的旧 credential 恢复路径。

### 2026-09-16 精确旧 Google 主体采用与真实返回

用户随后在 Google 账号选择页选择了已有可登录账号。真实 callback 到达 Admin 后以 `LEGACY_SUBJECT_LINK_REQUIRED` 关闭，没有按邮箱创建或合并主体。只读核对发现旧 `public.oauth_accounts` 中存在一条 `provider='google'`、非空 `provider_sub` 且外键精确指向 canonical Dream user 的既有绑定；该主体没有 Admin membership。

Admin 按本阶段执行稿实现严格私有 DTO → Domain Service → typed Drizzle Repository 的 release-only adoption。owner-only `0600` 配置绑定数据库身份、旧 canonical/Google行与源指纹；Better Auth IDs只由Admin根据`provider_sub`派生。默认dry-run，正式执行要求`--apply --production-approval`。正常库inspect、dry-run、apply和repeat apply均通过：首个action为`create`，重复为`already-complete`；Better Auth user、Google account、Dream subject link和脱敏audit各一条，Admin link为0，旧Google行仍为一条且未修改。隔离合同还应用完整Admin Drizzle历史并验证错误参数只输出固定脱敏JSON。

重新从Dream公开登录入口发起后，Google callback、Admin OAuth consent和返回Dream全部成功。正常库只读结果为Better Auth Session 1、browser session 1、refresh token lineage 1、OAuth access-token持久行0（access token为短期stateless JWT）；Dream Chat显示既有历史，同一浏览器访问`/admin`仍进入Admin登录页，因此产品登录没有授予管理权限。

真实页面随后暴露 `INVALID_TOKEN_RESOURCE`。脱敏令牌形状核对证明Better Auth 1.7.4签发ES256 `at+jwt`，`aud`为Dream resource和issuer `/oauth2/userinfo`组成的数组；Dream原`strict_aud=True`只接受标量。修复后Dream显式要求resource存在，数组成员只能属于这两个配置派生值，并拒绝额外resource、userinfo-only、重复、空值和非字符串；签名、算法、issuer、TTL、client、scope、JWKS缓存和unknown-kid边界不变。

| 验证 | 工作目录/入口 | 结果 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/test_admin_data_boundary.py` | Dream `backend` | exit 0；81 passed |
| `.venv/bin/python -m pytest -q tests/test_admin_data_boundary.py tests/test_admin_request_auth.py tests/test_product_bff_routes.py` | Dream `backend` | exit 0；117 passed，1个既有FastAPI生命周期deprecation warning |
| `.venv/bin/python -m pytest -q tests` | Dream `backend`当时树；最终结果见文末审计 | exit 0；当时3535 passed、24 skipped、615 subtests passed；只有既有deprecation/SDK提示 |
| Dream backend受控重启与浏览器reload | task-owned `127.0.0.1:8765`、现有Chrome登录页 | backend启动完成；Agent选择器不再显示`INVALID_TOKEN_RESOURCE`，历史会话正常加载 |
| Admin管理权限隔离 | 同一浏览器`http://localhost:3000/admin` | 重定向/停留于Admin login，没有进入dashboard |

尚未完成的真实项目：模型消息已选择Screenwriter并准备草稿，但实际发送需浏览器动作时确认；Device批准/拒绝/兑换/refresh/revoke、退出/Session失效、文件与故障恢复仍继续验收。本节不把登录成功扩张为这些下游项目已通过。

### 文件验收情境边界

本轮文件场景使用一个无敏感内容、具名且可识别为本轮所有的纯文本附件，通过已登录Dream页面的“Add attachment”公开入口附加到既有Thread。选择文件可以创建附件字节和Admin-owned metadata；在模型发送动作获得单独确认前不提交消息、不启动Run。Project、Episode、Deck、历史消息、资源策略和既有文件必须保持不变。

| 事实 | 真相源 | 所有者 | 本轮预期 |
| --- | --- | --- | --- |
| 附件字节 | Dream共享文件系统的规范化Thread路径 | Dream路径/权限/写入边界 | 新增本轮纯文本附件；拒绝越界和符号链接 |
| 附件metadata | Admin具名文件DTO/Repository/Drizzle事务 | Admin数据服务 | 与当前actor/Thread/文件摘要绑定；失败不能显示成功 |
| Chat消息与Run | Admin Thread/Run/message记录 | Dream编排、Admin持久化 | 选择附件阶段保持不变；发送后再单独验收 |
| Project/Episode/资源策略 | canonical artifacts与Admin desired/Dream LKG | 原业务owner | 全部保持不变 |

### 2026-09-16 只读历史与 Device 允许链路

用户在本机正常 Admin 设备授权页检查客户端、目标资源和请求 scope 后点击“允许”。授权动作之前，CLI 风格客户端已通过公开入口取得设备码并验证 `authorization_pending`；设备码、用户码和 token 只保存在 owner-only `0600` 临时文件，未写入文档或公开日志。

| 验证 | 公开入口 | HTTP / 退出结果 | 脱敏证据与结论 |
| --- | --- | --- | --- |
| 允许后兑换 | Admin `POST /api/auth/oauth2/token`，RFC 8628 grant、registered public client/resource | `200`、`Cache-Control: no-store` | 返回 Bearer access、refresh、ID token字段；access TTL 300 秒，scope为已批准的`openid profile offline_access dream:read dream:write`；JWT issuer、双audience和`ink-dream-device` client正确 |
| Dream Resource Server | Dream公开`GET /api/me`，携带设备access token | `200` | 签名/JWKS/issuer/resource audience/scope校验后映射到canonical Dream user `7`，role仍为`user`；profile邮箱保留canonical资料，没有按Google邮箱覆盖或自动合并 |
| Refresh rotation | Admin token endpoint，public client refresh grant | `200`、`Cache-Control: no-store` | 签发新的access与不同refresh；新access再次访问Dream `/api/me` 为`200` |
| 旧 refresh 重放 | 对已轮换旧refresh再次调用token endpoint | `400 invalid_grant`、`no-store` | 无新token；当前family随重放失效，随后主动revoke返回`invalid_request: token not found`，因此这一链路只能证明重放失效，不能冒称主动revoke成功 |
| 重复 device 兑换 | 原device code再次调用token endpoint | `400 invalid_grant`、`no-store` | 无access/refresh，已消费授权不能复活 |
| 已签发 JWT 的失效范围 | refresh family失效后再次调用Dream `/api/me` | `200`（原JWT仍在300秒有效期内） | 符合文档定义的离线JWT边界；refresh/revoke不会虚报为既发JWT即时失效，expiry仍由Dream验证 |
| 真实 access expiry | 首个JWT的`exp`经过后再次调用Dream `/api/me` | `401 INVALID_ACCESS_TOKEN` | 不返回profile；Dream真实运行路径执行时间声明与过期拒绝 |

另以已登录Dream页面完成只读历史验收：会话列表、一个既有Thread及其messages/status/plan/todos/subagents/plugin receipt均经公开路由返回`200`，没有发送消息或创建Run。该过程中Dream Python进程无数据库环境键，到正常PostgreSQL `54329` 的连接数为0，证明历史加载也经过Admin接口而非数据库旁路。

文件场景只完成影响边界和本轮纯文本fixture准备。文件选择器出现时Chrome前台已由用户切换到其他页面，自动化立即停止；没有选择或上传文件，也没有创建metadata、Chat消息或Run。本项仍为未执行，不能把fixture存在当作文件业务验收。

主动refresh revoke需要一条未先触发重放保护的新授权链；拒绝流程也需要新的device code。两项将在独立设备授权页完成，避免复用已消费/已失效的授权记录。

### 2026-09-16 Device 独立撤销与拒绝链路

另建两条互不复用的真实 Device authorization。第一条在用户允许、兑换并取得未轮换 refresh token 后，调用公开 revoke endpoint；再次用原 refresh token 请求 token endpoint 返回 `400 invalid_grant` 与 `Cache-Control: no-store`。这条链路没有先触发 replay-family invalidation，因此证明主动 revoke 已生效。第二条在设备授权页选择拒绝；当时连续公开轮询均返回 `400 access_denied` 且不签发 token，超过设备码有效期后的再次复核返回 `400 expired_token`，符合终态随时间推进的实际响应。两条链路均未把 device/user code 或 token 写入回执。

Device 本轮已覆盖：create、`authorization_pending`、`slow_down`、允许、拒绝、兑换、重复兑换、refresh rotation、旧 refresh 重放、独立主动 revoke、真实 access expiry、`invalid_client`、`invalid_target`、`invalid_scope` 和外部主体注入拒绝。未把 Session token 当 OAuth access token，也未把既发 stateless JWT 描述为可即时撤销。

### 2026-09-16 Admin 0063、Product OAuth 与 Gateway 运行身份

Admin 新增 `0063_smiling_microbe`，只为 runtime delegation 增加 nullable Reflections authority source、精确 cascade FK/CHECK，并发布 `identity.runtime-reflection-authority.v1`。具名可删除 PostgreSQL 从 0000 重放至 0063，64 条 migration receipt、列/FK/CHECK/capability 和 repeat apply 全部通过并已清理；正常 `ink-memory` 也以前向方式应用 0063，当前为 64/64 receipts 与 9 项发布门槛 capability。Dream 没有执行 migration、DDL 或临时建表。

Product 路径删除 Dream 本地 HS256 signer。浏览器产品调用只转发 Admin 已验证 OAuth access token，FastAPI 继续用严格 Pydantic DTO，Admin 执行 Zod DTO → Domain Service → Drizzle Repository；缺少 Admin 或 capability 直接失败，不回退本地数据库。聚焦 Product/SystemConfig 回归 `54 passed`；真实页面读取订阅、计划并完成 public renewal preview/execute，结果仍为既有 Free plan、订阅 revision 2、期间结束日 2026-10-09，未产生付费交易。

真实 Agent 首轮由 Gateway 返回 `403 GATEWAY_SCOPE_REQUIRED`。只读核对发现 canonical subject 的 active Gateway key仍含已退休 `chat:create`，缺少 Runtime 必需 `messages:count_tokens`。Admin 新增严格 rotation DTO、Domain Service、Drizzle transaction/audit 和默认 dry-run operator CLI；一次性当前 secret proof 与 target DTO 分离，明文只写 owner-only Dream env，不进入数据库、DTO、receipt 或日志。正式 rotation 把 exact scopes 收敛为 `models:list/messages:create/messages:count_tokens`，受控重启 Dream 后，同一公开 Chat POST 从 403 变为 `200`。

该请求尚未产生 assistant message。Backend 明确返回已启用 OAuth MCP Server 的 managed credential 必须刷新；这是 Runtime connector credential 问题，不是 Gateway scope、模型路由或数据库回退。随后修复 Settings 失败状态无 replacement 入口的问题，并补齐 managed MCP 稳定 AES-GCM key/callback 部署配置。replacement 使用 fresh SDK TokenStorage，旧 envelope 保留到新 token 交换成功；`19 passed` 的 provider-free OAuth/credential/service 测试证明旧 key 不可读时也能开始替换，取消/失败不删除旧记录。目前真实流程已到远端 provider 的最终 consent 页面，尚未提交最终授权，因此模型可见回复、继续和取消仍不得声明通过。

### 2026-09-16 Settings 搜索与 MCP 恢复交互

Settings 搜索原实现只过滤 General、Subscription、Work、AI models、About 五个一级项，导致实际存在的 `settings-resources`、`settings-plugins` 与 MCP/Notion 别名无法命中。现行实现维护七项完整索引：General、Subscription、Work/Deck、Resource links、Plugins、AI models、About；每项覆盖 section id、现行/兼容路由、翻译标签、说明和必要业务别名。非空查询显示精确目标并直接进入 Work 子 tab，空查询保持原五个一级导航。

| 验证 | 工作目录/入口 | 结果 |
| --- | --- | --- |
| Settings/MCP 相关 Playwright source tests | Dream `frontend` | Luna stage exit `0`；101 passed |
| 搜索索引与 OAuth action policy 聚焦 | Dream `frontend` | exit `0`；11 passed，七个导航 key 全部枚举 |
| TypeScript 与 focused ESLint | Dream `frontend` | exit `0`；无错误 |
| 真实 Chrome Settings 搜索 | 已登录 Dream 页面 | 输入 `MCP` 后唯一显示 `Resource links`；清空后恢复五个一级导航 |
| MCP failed credential UI | 已登录 Dream MCP detail | `failed + OAuth + credential_configured` 显示“重新认证”；active/disabled/anonymous 仍不允许启动第二条 OAuth operation |
| AutoDL/Remote env contracts | Dream repository | exit `0`；AutoDL topology 与 Remote DTO/BFF projection 均通过；退休 Product HS256 secret 不再进入 AutoDL runtime env |

### 2026-09-17 MCP replacement、文件与模型额度边界

用户在远端 provider 页面完成授权后，callback 自动回到 Dream 并完成 token exchange。首次紧接交换的 discovery 返回受控 `CLAUDE_MCP_PROTOCOL_ERROR`；退出详情页再通过正常产品入口加载时，持久化凭据可用，页面显示连接成功，并返回 41 个 Tools、25 个 Resources 和 10 个 Prompts。该结果证明 replacement credential 已提交并被后续请求复用；首次 discovery 失败记录保留为交换完成时的瞬时 provider/runtime 错误，没有通过删除旧数据或数据库旁路掩盖。

随后使用可见 Dream Chat 产品入口创建两条新 Thread，分别在默认模型和用户设置页保存的 `GPT-5.6-Luna` 下上传同一份 87-byte 无敏感内容文本 fixture 并发送正常用户消息。两次上传、消息和失败回执均保留在正常业务数据中，没有自动重试或直接写数据库。

| 检查 | 公开入口/证据 | 结果 | 判定 |
| --- | --- | --- | --- |
| MCP replacement callback | 远端同意页 → Dream callback → 正常 MCP 详情页 | callback 成功；reload 后显示已认证连接，inventory 为 41/25/10 | **通过**；凭据已持久化并可发现能力 |
| 文件上传和读取授权 | Dream Chat attachment、actor-bound 文件 GET | 两次上传成功；登录读取 `200`，未登录读取 `401` | **通过**；未泄露对象键或内部 ID |
| workspace 文件边界 | 本机正常 `AGENT_CWD` 只读 hash/mode/path 检查 | 2 个副本均位于真实 Thread workspace，普通文件、非符号链接、87 bytes，SHA-256 与 fixture 一致；对应 `.claude-tmp` 均为 `0700` 且非符号链接 | **通过**；共享文件系统协议未改变 |
| Thread/message 持久化 | 两次可见 Chat send 与正常历史回读 | 2 条新 Thread 和用户消息保留；页面显示失败可恢复状态，没有伪造 assistant 输出 | **通过持久化，模型终态未通过** |
| 默认模型真实调用 | Dream → Gateway 正常生产入口 | `402 SUBSCRIPTION_TOKEN_ALLOWANCE_EXHAUSTED`；当前周期可用额度小于本次 runtime 需求 | **账户额度阻塞**；不是 MCP、文件或数据库接口失败 |
| Luna 真实调用 | 保存模型设置后新建 Thread，再次走相同入口 | 同样返回 `402`，页面显示消息未处理并提供 reload 恢复 | **账户额度阻塞**；没有继续执行 continue/cancel/SSE 终态 |
| Admin 管理登录边界 | 正常 Admin 登录 + read-only password-proof 检查 + 认证业务域评审 | 验收口令只匹配 canonical Dream user，不匹配旧 Admin member；现行代码已恢复独立`admin_users/admin_sessions/RBAC`、opaque Admin Session与实时RBAC | Dream密码继续返回`401`是正确隔离；真实成功登录只待现有Admin自身凭据，不能由邮箱、Dream token或subject link替代 |

模型执行需要的 token 数高于当前订阅周期余额，因此不能通过缩短断言、伪造回复或修改 runtime 限额来冒充成功。只有在正常账户补足额度后，才能继续验证 assistant 文件读取结果、Run/SSE 终态、continue 和 cancel。Admin 独立 Session 已按评审完成实现和确定性验证；真实成功登录仍需要现有 Admin member 的原凭据，不能使用 Dream 密码、同邮箱或 subject link 代替。

### 2026-09-17 身份域修正与完整确定性复核

Admin operator 与 Dream user 的代码路径已按设计稿分开。Admin 登录只读取`admin_users`独立密码并把opaque随机值的HMAC摘要写入`admin_sessions`，后续请求实时读取member状态和RBAC；Dream Better Auth user、Google account、canonical user、Dream token和`identity.admin_subject_links`均不参与。Dream browser/device仍为public OAuth client；Dream Next/Python服务为confidential client，后台调用使用`client_credentials` access token，用户调用同时携带该服务token和用户委托token。浏览器输入/输出会剥离私有服务bearer，Admin明确拒绝旧静态service ID/secret头。

| 验证 | 工作目录 | 结果 |
| --- | --- | --- |
| `pnpm test:run` | Admin工作分支 | exit `0`；277 files、2091 tests通过，17 files、36 tests按既定条件跳过 |
| `pnpm exec tsc --noEmit --incremental false`、`pnpm lint`、`pnpm build` | Admin工作分支 | 全部exit `0`；Next生产构建完成 |
| `PYTHONPATH=backend backend/.venv/bin/python -m pytest -q backend/tests` | Dream工作分支 | exit `0`；3538 passed、24 skipped、615 subtests passed |
| `pnpm exec tsc --noEmit --incremental false`、`pnpm lint`、`pnpm build` | Dream `frontend` | 全部exit `0`；Lint为0 error、17条既存Hook依赖warning；Next生产构建完成 |
| 生产数据库路径扫描 | Dream `backend`与`frontend`，排除tests/e2e/lockfile | 未发现PostgreSQL驱动、DSN、SQL、连接池或静态service secret发送；测试目录保留的数据库探针不进入运行路径 |

本节是技术验证，不把账户额度阻塞的真实模型回复、Run/Thread继续/取消或SSE终态写成已完成。独立Admin登录的后续正常业务回执记录在下节。

### 2026-09-17 正常Admin ACL修正与Notion后台读取

独立Admin登录首次走公开入口时返回`500`。只读诊断和受限角色复现将原因定位为正常库ACL未包含`admin_users.password_hash`读取与`admin_sessions`写入，而不是用户域合并或密码算法问题。按正常发布路径先生成停止集群的一致物理备份，再以owner-only `0600` manifest执行dry-run、正式apply和重复apply；三次均通过。最终策略绑定Admin `f79a0992eead124b1c05ae049c5440b60baee9e2`和Dream `2df9d9b423dac3131a0f15494272a821cea8f313`，覆盖64个migration、8个激活门禁capability、144条ACL语句、active Gateway与四个实际角色probe。

修正后`ink_auth`可读取独立Admin credential列并写入Session/audit，`ink_admin_control`可读取RBAC；两者仍不能读取Dream `chat_thread`或历史`identity.admin_subject_links`，Dream角色仍是`NOLOGIN`且无database `CONNECT`。公开Admin登录由服务错误恢复为明确`401 ADMIN_CREDENTIALS_INVALID`，同一Chrome已有Dream会话访问Admin `/api/admin/auth/me`也保持`401`。这证明运行路径与ACL已修复，同时Dream登录、同邮箱或Dream密码都不会产生Admin Session。成功Admin登录仍需要该独立Admin member的有效凭据；本轮没有复制Dream密码、重置Admin密码、降低密码策略或建立跨域用户映射。

后续只读诊断确认一个active Admin operator、一个角色绑定和当前scrypt格式hash；错误候选凭据继续返回401，而现有独立Admin凭据越过密码校验后返回503。`pnpm env:check`把原因精确定位为正常`.env.local`与`docker/.env`遗漏必需的`ADMIN_SESSION_TTL_SECONDS`，不是Dream用户、OAuth、ACL、DTO或哈希算法。补齐生成器和模板既定的28800秒后配置检查exit0，公开login/me/logout依次返回200并投影1 role/28 permissions，Chrome进入`/admin`。没有重置密码、修改RBAC或建立跨域映射；聚焦5 files/22 tests通过。

Notion后台同步候选使用Dream confidential OAuth client的`client_credentials`，没有canonical Dream user。Repository先把ORM行的`config_json`、`metadata_json`和`snapshot_json`显式解码投影为严格DTO，再由Service和公开operation返回；DTO没有放宽extra-field策略。定向Repository/Service测试`17/17`、TypeScript和ESLint均通过。正常公开token endpoint返回`200`和300秒Bearer，随后`notion.sync-candidates.list`返回`200`、原request ID与1个connector；响应只含`config`/`metadata`等DTO字段，没有`*_json`存储列。该后台scope没有读取或写入Admin operator，也没有创建、合并或冒充Dream user。

### 2026-09-17 Dream退出与Session失效续验

真实浏览器场景先明确Project、Episode、Thread、文件、Runtime和资源策略全部保持不变，只允许撤销当前Dream browser handle并重新建立同一canonical user会话。第一次Chrome控制通道在任何退出动作前连续三次超时，未产生会话变更；该harness前置失败保留，不计为产品缺陷。重置控制通道并复用本机Chrome后，正常Story Workspace公开页面显示现有Dream产品主体；打开用户菜单点击`Logout`，页面切换到`Log in or create an account`，受保护历史不再展示，证明当前BFF handle/cookie已关闭。

不依赖浏览器状态的生产代码合同随后重跑：在Dream `frontend`执行`node --test app/api/_auth/handlers.test.ts app/_dream/lib/browserSession.test.ts`，exit `0`，27 tests全部通过、0失败、0跳过。覆盖Origin/CSRF、Admin revoke失败时保留handle、严格成功回执后清cookie、401清会话、依赖503保留已确认快照、并发/过期读取不能复活会话，以及confidential service token与用户token分离。

退出后从同一公开Dream登录入口点击`Continue`。Admin origin的Dream Better Auth SSO Session仍有效，因此无需再次输入密码或选择Google账户，code/PKCE流程自动返回Story Workspace；用户菜单再次显示与退出前相同的Dream产品主体，原历史恢复可读。该结果确认退出范围是当前Dream browser client的refresh grant/lineage与BFF handle，不是中央SSO或其他客户端的全局退出。随后同一Chrome profile打开`http://localhost:3000/admin`，仍停留在独立“登录运营控制台”页面，没有进入dashboard；Dream SSO与重新登录均未创建Admin `admin_sessions`或授予RBAC。自然等待中央Session或handle TTL到期尚未执行，27项确定性测试已覆盖401/过期/refresh失败后的关闭行为。

### 2026-09-17 正常资源策略 desired/effective/LKG 只读验收

使用Dream生产`AdminResourceData`和confidential service OAuth从正常Admin公开`resource-policy.read`读取desired，再用owner只读查询核对正常`claude_agent_resource_snapshots`中运行中Dream进程发布的最新Observer DTO。没有直接修改数据库、desired或运行配置，也没有启动Agent turn。命令在Dream工作分支以`PYTHONPATH=backend backend/.venv/bin/python`执行，exit `0`。

公开operation返回`configured` revision 4；desired四项值为并发2、run memory 416 MiB、reserve 128 MiB、retry 60秒，effort为`low`。最新正常Observer心跳年龄约0.23秒，`policy_status=applied`，revision、四项effective和effort全部与desired一致；`required_headroom_bytes=(416+128)×1,048,576`精确成立，effective version为64字符SHA-256。数据库当前保留41个实例快照；最新pipeline包含历史write error计数，但当前心跳新鲜、queue dropped为0，未使LKG回滚或传播到turn。该结果证明正常后台refresh/observer路径正在运行，且Agent turn主路径没有为本检查新增远程查询。
