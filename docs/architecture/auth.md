<!-- [Sync] 2026-09-17: record exact legacy Dream credential adoption without Admin-user merging. -->
<!-- [Sync] 2026-09-17: restore the Dream login/register/Google card through direct Admin form actions before PKCE. -->
<!-- [Sync] 2026-09-17: close Deck detail empty-Memory parity through raw Admin Repository projection and unchanged Dream compatibility parsing. -->
<!-- [Sync] 2026-09-16: select localhost as the single local Dream/Admin browser auth topology and Google callback origin. -->
<!-- [Sync] 2026-09-17: define client-local logout, retained Admin-origin Dream SSO, and independent Admin management sessions. -->
<!-- [Sync] 2026-09-17: define Dream as OAuth client, Dream users as delegated subjects, and Admin operators as a separate management domain. -->
<!-- [Sync] 2026-09-16: FastAPI retires SessionMiddleware and scrubs legacy Dream auth/session secrets; Next BFF remains the only Dream browser-session owner. -->
<!-- [Sync] 2026-09-16: Agent-type clear/Runtime plan/prepare use current Admin OAuth and Registry127-129. -->
<!-- [Sync] 2026-09-16: confirmation Runtime uses Registry121 claim-bound Admin persistence authority. -->
<!-- [Sync] 2026-09-15: localStorage import and first-login completion use Admin Registry101 with no Dream DB fallback. -->
<!-- [Sync] 2026-09-15: public assistant complete/partial writes use the bound server-persistence grant and original receipt recovery. -->
<!-- [Sync] 2026-09-15: three public default resolvers share registered Admin ensure; Deck Plugin role reuses current profile. -->
<!-- [Sync] 2026-09-15: register typed fail/envelope without granting actor IDs background authority. -->
<!-- [Sync] 2026-09-15: consume registered Run cancel with original reason/full result and bounded receipts; other lifecycle gaps remain. -->
<!-- [Sync] 2026-09-15: consume registered76 OAuth-write default Workspace; original text ID/receipt and independent read scope stay explicit. -->
<!-- [Sync] 2026-09-15: file reads consume current OAuth Thread ownership before unchanged file rules. -->
<!-- [Sync] 2026-09-15: consume public Preflight GET with canonical actor/ID matching and no Workspace SQL. -->
<!-- [Sync] 2026-09-15: consume OAuth PF execute and its separate original receipts; keep default lookup explicit. -->
<!-- [Sync] 2026-09-15: consume full Run read/create/retry OAuth domains and original scoped receipts. -->
<!-- [Sync] 2026-09-16: wire launch replay/source/Preflight/Run/dispatch/failure through current Admin OAuth and strict DTO operations. -->
<!-- [Sync] 2026-09-15: record complete Admin Deck list modes and remaining SQL source candidates. -->
<!-- [Sync] 2026-09-15: record Admin-owned Deck detail and unchanged legacy Memory projection. -->
<!-- [Sync] 2026-09-15: index five Admin Deck writes, shared schema gate and closed deletion feedback. -->
<!-- [Sync] 2026-09-15: record catalog refresh/readiness boundary without changing request authentication. -->
<!-- [Sync] 2026-09-15: current Browser session identity fences aborted/stale responses and asynchronous user commits. -->
<!-- [Input] Dream baseline auth/BFF and the Admin-owned contract when frozen. -->
<!-- [Sync] 2026-09-15: bind public Agent Thread/SDK Session operations and scope original-ID recovery. -->
<!-- [Output] Dream consumer design, authority retirement, topology and acceptance gates. -->
<!-- [Pos] Dream authentication consumer; Admin owns Better Auth, OAuth and signing keys. -->
<!-- [Sync] 2026-09-15: user preference management uses current OAuth; entity-limited Runtime grants cannot manage it. -->
<!-- [Sync] 2026-09-15: Deck management uses current request OAuth; purpose grants do not authorize it. -->
<!-- [Sync] 2026-09-15: public Session operations retain explicit request OAuth; server grants do not expand their scopes. -->
<!-- [Sync] 2026-09-15: exact server-persistence grants may call only session.list for Agent prompt context; Admin/read-contract failures stop before Workspace, Runtime and SSE. -->
<!-- [Sync] 2026-09-15: distinguish server turn persistence from CLI and Editor purpose grants. -->
<!-- [Sync] 2026-09-15: retire standalone authority and require explicit OAuth/profile account matching in scripts. -->
<!-- [Sync] 2026-09-14: record the implemented Admin BFF and public issuer retirement; retain original history. -->


五公开Deck写操作的正常流程、状态、原错误/删除反馈与验收以[现行稿](../design/deck-mutations-current.md)为准；相关读写、default与安装metadata均已使用发布的Admin operation，正常环境切换与真实业务验收仍待执行。

# Dream 接入 Admin 认证

认证表关系、旧用户冲突处理、Dream/Admin 权限隔离及浏览器、Google、Admin、Device 完整流程见[登录认证体系：数据 ER 图与流程](./auth-identity-er-and-flows.md)。

统一Client的catalog refresh/readiness与广告检查共享同步边界。正在加载时其它已验证调用等待完整结果；失败清空ready/广告并由后续认证重新加载，不能沿用旧广告。领域HTTP保持并发、显式per-request token/DTO/UUID，认证校验、scope与原receipt语义不变。

## 背景与问题

baseline `7d38715c` 中 `backend/auth.py` 自签 HS256 用户 token，`routers/oauth.py` 用 Authlib 做 Google 登录并按配置合并同邮箱账户，`routers/device_oauth.py` 自行维护 device/refresh 状态。浏览器读取 URL fragment/localStorage token，部分 API 直达 Python。这些实际实现与 Admin 唯一认证中心目标冲突。

本稿记录迁移目标、当前源码范围与评审约束，不能作为正常部署或真实账户验收回执。状态见[执行计划](../exec/dream-admin-auth-data-plan.md)。[旧认证原文](history/pre-admin-auth-data-20260914/auth.md)完整保留接口和历史测试；其中旧 authority、邮箱自动合并与 DB 直连不再是目标规范。

## 目标与边界

Admin 使用 Better Auth 内置 Google social sign-in、Admin callback、OAuth authorization/device/token、JWKS 与 Dream 账户映射。Dream Next/browser、device 和 service 是 OAuth client；Dream 产品用户是用户委托 token 的 subject。FastAPI 是 OAuth Resource Server 与业务编排，不能签用户登录 token、验证 Google token 或维护另一套 session/refresh/device authority。Admin operator 使用独立 Admin Session 与 RBAC；Dream 登录不读取、合并或创建 Admin member。

当前源码中FastAPI不安装`SessionMiddleware`，不读取或继承Dream旧`GOOGLE_CLIENT_SECRET`、通用`JWT_SECRET`、Session/OAuth加密secret及旧Cookie策略；进程入口在导入业务模块前移除这些遗留环境变量和Next-only `INK_DREAM_BFF_COOKIE_SECRET`。浏览器状态只由Next BFF用该key签发host-only HttpOnly handle。Admin的Google/Better Auth/OAuth secrets、Dream注册service credential、Gateway/Product服务令牌和独立Workflow token各自按用途配置，互不回退。Cloud Run使用独立backend/frontend service account及逐secret IAM；BFF cookie secret只绑定Next，缺少Next service credential或cookie secret时发布在构建前fail closed。

Deck Plugin binding 的 current/history/options/validate/runtime-plan 使用当前 OAuth `dream:read`，save/clear/runtime-prepare 使用 `dream:write`。Dream 从已校验主体解析 default Workspace 后只提交业务定位字段和本地不可变 artifact 证据；Admin 仍重新派生 canonical actor 并检查 Deck/Workspace owner。Google token、Session token、任意用户 ID header、Runtime purpose grant 或 Admin RBAC 身份都不能替代该产品 OAuth access token。

Admin唯一规范位于其仓库 `docs/architecture/admin-dream-auth-data-contract.md`。当前客户端已按实际DTO与路径消费；发布能力与本机业务回执分别记录，本稿不自定 endpoint、claim 或 capability。跨项目业务设计见[认证与数据交互](admin-auth-data-interaction.md)。

## 概念与规则

| 边界 | 执行模块与判断 | 失败处理 |
| --- | --- | --- |
| Google身份认证 | Admin Better Auth校验state/code/OIDC与稳定provider subject | 登录页说明失败；Dream不签token |
| 用户映射 | Admin保留users.id与业务FK，仅显式校验的关联流程绑定已有账户 | 同邮箱不自动合并；冲突返回明确错误 |
| 产品登录入口 | Dream渲染原邮箱/密码/注册/Google卡片；浏览器按`/auth/options`直接POST Admin exact-origin action，Dream服务端不接收密码 | 未配置、错误Origin/return或Admin不可用时显示安全反馈；不回退旧Dream认证 |
| BFF登录 | Admin建立Dream identity Session后返回Next `/auth/start`发起code+PKCE；callback校验一次性state、code、固定redirect URI与PKCE | 拒绝缺失/重放/开放redirect，清该次登录状态 |
| BFF会话 | Dream host-only HttpOnly opaque handle；tokens存服务端；Admin session只属Admin origin | 撤销/过期重新登录；服务故障保留可恢复状态 |
| Dream API | 成熟JWT/JWKS库验证签名、闭集算法、issuer/audience、时间、subject与scope | 无效/过期/错误资源为401；scope不足403 |
| Admin领域数据 | 独立service credential+用户access token或限定后台授权；Admin检查实体归属 | service不能凭body/header任意user_id改actor |

本机已有 Dream credential 兼容使用 Admin 发布期专用操作：私有 DTO 固定正常数据库物理目标、canonical Dream user ID、用途证据和 inspect 得到的源行指纹；Admin 服务端派生 Better Auth subject/account ID，在一个 typed Drizzle 事务内原样保存旧 Dream bcrypt 到 `identity.account(providerId='credential')` 并建立 `identity.subject_links`。该操作不修改 `public.users`，不读取或复制 `admin_users` 密码，不创建 `admin_sessions`、RBAC 或 `identity.admin_subject_links`；部分目标、邮箱冲突、Admin link 或源指纹变化全部失败。运行时登录只验证已经建立的 credential，不按邮箱临时合并。
| Admin管理 | `admin_users/admin_sessions/RBAC`独立管理认证与权限校验 | Dream identity、邮箱、scope和subject link均不授予管理能力 |
| Dream service client | confidential client使用`client_credentials`取得限定background scope；用户调用继续传用户delegated token；token连接在未取得HTTP响应的transport error后只恢复一次，第二次最多2秒 | service token不能推导canonical user或访问任意用户数据；HTTP拒绝和业务DTO调用不重试 |

内部 Admin 数据调用有两种凭据形态。background operation 把 service access token 放在 `Authorization`；用户 operation 把用户 access token 放在 `Authorization`，Next/Python 服务端另加私有 `X-Ink-Dream-Service-Authorization` service bearer。浏览器 API 代理会剥离该私有头的输入和输出，旧静态 service ID/secret 头不再发送。Admin 分别校验 confidential client 与 Dream 用户主体；任一 token 缺失、scope/resource 不符或映射失败都关闭请求，不回退 Dream PostgreSQL。无副作用读取（包括使用POST承载的typed read operation与receipt查询）仅在未取得HTTP响应的transport error后重建请求一次，第二次超时上限2秒；HTTP状态拒绝不重试。写操作只派发一次，超时后仅以原`request_id`查询receipt，不重放业务写入。

Dream Next BFF 在进程内复用同一个`AdminBffClient`，包括开发热更新后的`globalThis`实例；短期service access token和并发中的token兑换由该实例统一缓存/合并。Route Handler不能为每个浏览器API请求重新创建client，否则会把一次页面加载放大为多次`client_credentials`兑换并增加Admin认证数据库与网络延迟。public Admin origin/issuer负责浏览器跳转、Token声明和capability核对；可选server-only transport origin只改变DTO、client-credentials与JWKS的网络目的地，不能改变`iss`、resource或回调。配置值变化时丢弃旧实例并按新配置创建。

业务数据继续遵守 strict Pydantic DTO → Admin Zod DTO → Domain Service → typed Drizzle Repository → transaction。Dream 不携带 SQL、表列、事务或 caller-selected user ID；Admin Repository 执行权限过滤、锁、幂等 receipt 和持久化，Dream 保留 Runtime、SSE、业务编排和共享文件系统。

### 浏览器主拓扑与配置

主拓扑：Dream渲染登录卡片 → 浏览器以原生顶层POST直接提交Admin受限表单 → Admin Better Auth密码/注册或Google callback建立Dream identity Session → 返回Dream同源BFF `/auth/start` → Admin OAuth authorization/code+PKCE → Dream callback。Dream不以跨域fetch接收认证响应，避免浏览器把Admin的state/Session `Set-Cookie`作为第三方Cookie丢弃；Dream Next/Python不接收密码，action只由服务端配置投影，return只允许相对路径。Admin与Dream分别持有host-only cookie，无Domain共享，不因同网段推断cookie互通。生产HTTPS使用Secure/HttpOnly；SameSite与callback method按实际契约冻结。浏览器REST/SSE认证读写进入Dream origin；不能跨域转发任意Cookie。

server-owned配置明确Dream public origin、Admin public issuer/origin、可选Admin internal transport origin、注册callback URI与内部FastAPI URL。浏览器表单、OAuth authorize、callback校验、JWT `iss`与capability元数据始终使用public authority；Next/Python的DTO、client-credentials和JWKS HTTP请求可通过显式loopback transport发送，响应仍必须声明同一个public issuer/resource。代理按部署配置确定Dream origin；仅当请求URL为已配置的loopback代理入口时，才接受共同组成精确Dream public origin的单值`X-Forwarded-Proto`与`X-Forwarded-Host`，不接受任意或链式forwarded header。BFF mutation继续校验浏览器`Origin`与CSRF，return location限定同Dream origin页面并恢复device上下文。callback URL不能携带access/refresh token。

本机直接访问配置可使用 Dream `http://localhost:5173` 与 Admin `http://localhost:3000`；启用内网穿透时，浏览器origin、Admin issuer、Google callback、Dream callback与resource必须统一从该次部署的公网Dream/Admin origin派生，不能继续混用localhost。内部Next、FastAPI与Admin监听地址继续使用明确的loopback配置，不参与浏览器OAuth issuer、redirect、Cookie或CSRF origin比较。AutoDL同样从当前实例环境把6006/6008的HTTPS映射分别注入`AUTODL_DREAM_PUBLIC_ORIGIN`与`AUTODL_ADMIN_PUBLIC_ORIGIN`，由生成器派生callback、issuer、resource、CORS和CSRF origin；仓库不固定某个产品域名，实例映射变化后必须重新投影Admin与Dream的gitignored配置。

当前speech recognition按现行业务设计关闭，Python `/ws/speech-recognition` 返回1008。保留显式WS选址，但本迁移不启用语音、不新增WS授权scope或upgrade通道。未来恢复语音能力须另按实际业务/API合同校验origin与用户身份，不能用旧query token或opaque handle冒充OAuth token。

### JWT/JWKS与撤销

API仅接受Admin目标OAuth access token。固定issuer、audience、算法集合，必需时间、非空subject、scope按规范校验；拒绝Google access/ID token、旧HS256、任意身份头、错误资源token。成熟库按配置缓存JWKS，未知kid触发受控刷新，失败不绕过验证，不逐请求下载JWKS。缓存/刷新失败与是否可用已有合法key必须按Admin契约冻结。

session/refresh由Admin撤销；access token短寿命、introspection/deny-list适用范围、服务委托寿命和logout对存量token影响需要明确。不能声称离线JWT提供即时撤销。

### Refresh与兼容退役

Next服务端使用Admin OAuth refresh grant，对同handle并发refresh做单次交换/原子替换。invalid grant清会话；网络故障保留恢复状态；未知兑换结果按Admin请求恢复规则处理。Dream停止`X-New-Access-Token`滑动自签。CLI public client不持secret，使用[Device OAuth](auth-device.md)。

| baseline依赖 | 目标与退役条件 |
| --- | --- |
| login/register、Google login/callback | 保留密码登录/注册/Google产品能力，认证迁Admin并恢复OAuth上下文；旧路径如保留仅明确导航/协议转发/错误，不签token |
| auth/me、api/me | 保持profile DTO，主体来自Admin、数据来自领域接口 |
| logout、oauth/token、Device | 按规范撤销/导航或兼容转发，不保留authority |
| AuthContext/getAuthToken、localStorage、fragment、renewal interceptor | 改同源会话API；清旧token，不清其他用户数据 |
| FastAPI dependency/SSE、Node MCP Apps、stdio tools、后台任务 | 消费Admin主体/受限委托，保持实体绑定与取消语义 |
| Gateway subject token/product auth | 保持计费PK；Admin规范定义服务投影，不作为Dream登录authority |
| Authlib/外部MCP OAuth | 先盘点调用依赖，只退役Dream登录authority，保留仍用外部协议 |

## 正常流程、状态与失败反馈

未登录 → 登录中 → callback校验 → 会话建立 → 已登录。拒绝、错误state、过期code返回未登录。refresh先保留现有会话，成功原子替换，invalid grant重新登录；Admin故障显示稍后重试，不解释为错误密码或删除数据。logout先等Admin成功撤销当前Dream browser client的refresh grant/lineage和BFF handle，成功后清Dream cookie，失败保留会话并提示，不增加重复确认。该动作不结束Admin origin上用于Dream OAuth授权页的Better Auth SSO Session，也不影响其他browser/device client；中央Session仍有效时，再次登录可以直接完成code/PKCE并返回。Admin管理`admin_sessions`始终独立，Dream退出和SSO均不授予或撤销Admin管理权限。

Browser唯一owner保存strict immutable公开session snapshot，并从该snapshot导出内存CSRF。每个session读取取得当前read object identity，fetch/JSON await或catch后检查identity与AbortSignal；aborted/superseded返回null且不修改状态，旧401/失败不能清除新session或覆盖错误。clear与logout开始使已有read失效；logout失败保留已验证snapshot，strict success才清除并使期间pending读取失效。AuthContext在then提交前同时检查未abort与returned snapshot仍属当前owner，避免已返回但随后被clear/新session替换的user被再次显示。该规则只处理Browser异步状态，不修改服务端handle/refresh或MCP OAuth。

业务前校验身份/scope，Admin再校验实体权限。401、403、409、capability不足、unavailable、timeout分别保留语义。日志仅记录request ID、operation、状态，不记录token/code/secret/正文。

## 影响范围、验收与发布

依据[完整数据清单](../exec/dream-admin-data-inventory.md)迁移。验收覆盖Google redirect/callback/state/PKCE、Cookie/CORS/CSRF/origin、JWT各字段与kid刷新、并发refresh/撤销、Device、实体权限、REST/SSE/Voice/Node/stdio/background委托和旧authority静态复查、公开生产入口。

Luna runner执行确定性技术验证并返回cwd/command/exit/output。真实验收必须正常本机Dream/Admin/Gateway/PG、用户指定现有账户实体模型限次、正常Admin可见Run与日志；fixture不能替代。发布按Admin expand/API capability → Dream兼容切换 → backfill/validate → contract；两端共同确定session/密钥回滚策略。

## 当前旧入口与外部协议边界

`/api/register`、`/api/login`、`/oauth/google/login/callback`、`/oauth/device/code`、`/oauth/device/verify` GET/POST、`/oauth/token` 和 Python `/auth/logout` 保留原路径并返回410 `DREAM_AUTHENTICATION_RETIRED`。配置解析出的Admin issuer/authorize/token/device/code/revoke/JWKS/verification/resource信息用于client迁移；这些旧Dream服务入口不解析或转发密码、code、refresh和Cookie，不签本地token、不更新账户/device/refresh表。公开authority缺失或非法时503，不从Host/query猜目标。Dream React只渲染表单，浏览器按Next `/auth/options`直接提交Admin `/auth/dream/password|google`；Next `/auth/start/callback/session/logout`继续执行PKCE/handle流程，密码校验、账户创建、Google callback和Session均由Admin唯一承担。

Authlib在原两个issuer router中仅用于Dream Google/Device authority，现已退役，并与bcrypt一起从Python manifest/lock/export移除，其余依赖版本不变。Managed MCP外部server授权继续由标准 `mcp.client.auth.OAuthClientProvider`和TokenStorage执行，协议、加密存储、refresh和取消保持；Notion connector的现有credential/login不受本阶段影响。`backend/auth.py`保留历史helper标识符，本地签发/密码接口抛安全退役错误，旧token验证/renewal拒绝，只有duration/SHA-256/header纯函数保持；不读secret或默认key。两个维护/验收脚本必须显式提供Admin OAuth，缺失时在I/O前失败；公开 `/api/me` 必须匹配指定账户，错配时在thread/model/业务写入前失败。Gateway与Editor purpose grant已经使用各自的显式服务用途，不恢复旧subject登录authority。

`/api/import-local-data`与`/api/import-calendar-recovery`先在Dream按localStorage字段独立解析，转成闭合Session/Picture/Preferences/Report raw-JSON DTO，再以当前OAuth调用同一个`local-data.import`。某字段解析失败只排除对应类别；合法旧Report缺少`timestamp`时使用一次请求内相同UTC时间，已有安全整数毫秒转换为RFC3339，显式非法时间排除整个Report类别。Admin在单一UOW内完成owner检查、四类写入、receipt与audit，回复计数是公开结果；未知提交只读原request ID回执。`/api/mark-first-login-completed`独立调用幂等`first-login.complete`，公开回复仍为`{success:true}`。三入口无Dream数据库fallback，Admin 401/403/capability/transport/DTO失败保持失败，正文、图片、Token与原异常不进入日志。

公开Chat以当前OAuth读取Admin唯一Workflow上下文，在message/SSE前拒绝权限、绑定、capability或DTO失败；immutable snapshot只带已认证actor/thread和原上下文，不含credential，不向Browser/SDK投影。Service包括普通null均复用该snapshot。confirmation dispatcher通过Registry121从当前durable claim派生typed服务身份；launch、后台turn和持久化owner均使用已注册的限定委托，源码关闭门禁证明不存在旧登录authority或数据库fallback。正常服务切换和真实long-turn验收仍单独记录。

公开Agent的Thread resume读取、SDK init/final/repair Session回写和assistant完整/部分消息复用该exact Thread/Run server-persistence grant。confirmation dispatcher 也把 Registry121 返回的 claim-bound grant 组合成同一 `AdminTurnPersistence`，并在 Runtime 前注入 Workflow/Deck snapshots。`AdminTurnPersistence`校验reply Thread/canonical actor，未知user/session/assistant写共用原operation/input/UUID恢复；最近一次确认Session才可复用，A→B→A必须重新写。SDK init失败继续原日志处理，已经运行的turn/cancel保持原语义；其他尚未迁移的内部路径不属于此owner，不能据此宣称全域未知写屏障。

公开user-turn先创建绑定当前Thread/authoritative Run、仅dream read/write的server-persistence委托，再调用Admin原子user message/title/confirmation事务；Service复用已确认的同一输入。成功assistant与cancel/error partial在同一owner内调用既有Chat消息operation，先检查四项exact schema，再提交原parts/metadata/history字段。未知写保留原request ID并只查询原receipt，absent阻止后续写与推理。Factory在既有admission后启动后台renew，SSE断开保留turn，terminal/cancel安排自有cleanup并由shutdown drain同步writer、renewal线程和独立HTTP client。confirmation dispatcher通过Registry121使用相同owner；首次或Settings prompt重建时，同一owner以精确授权调用Admin `session.list`取得近期Session投影。401/403/503、能力缺失、超时或坏DTO在Workspace/Runtime/SSE前传播，成功空列表才显示empty block。凭据不进入Browser、CLI或Editor；Reflections、后台输出和其它数据库领域已逐项绑定Admin operation，Gateway/Editor继续使用独立purpose。详细状态与失败处理见[认证与数据交互](admin-auth-data-interaction.md)。

Next同名password/Google/Device/token薄adapter也返回410，login/register在generic proxy前执行，避免未登录401遮住迁移响应；Next `/auth/logout`仍执行实际BFF handle撤销。两端退役owner只读取三项公开authority配置，不要求private service凭据。

公开Session六operation由当前已认证request OAuth执行，继续绑定Admin principal；shared helper只投影该Bearer到指定typed consumer，不接受body actor ID、不做本地renew。OAuth行为保持不变。Admin Session Handler只为同配置service已完整解析、绑定Thread、Editor Session为空、包含`dream:read`且未过期的`server-persistence` grant放行`session.list`；save/get/batch/text-list/delete仍拒绝该purpose。Session工具和Reflections后台授权独立于Chat turn owner；Editor只能消费exact existing Session的editor-stdio grant。失败/unknown和Edit Session事件规则见[交互设计](admin-auth-data-interaction.md)。

公开Deck内容版本五operation只使用当前request OAuth与Admin principal，schema要求identity/unified/content-versions/canonical-storage四项exact v1。管理权限不接受Thread或CLI/Editor purpose。共享actor invocation保持同一认证和threadpool，只由domain adapter生成安全错误响应。领域catalog刷新失败清除ready，下一认证重新加载后再执行profile/Chat等operation；不回退旧issuer/SQL。

公开user-preferences.get/save只由当前OAuth用户管理；所有Runtime entity grant不能替代该授权。闭集字段不含body actor/firstlogin/systemconfig；identity/unified exact capabilities与Admin principal继续校验。原NULL partial merge/缺行{}保留，后台context/System/first-login与import仍独立。现行[用户偏好设计](../design/user-preferences-current.md)描述状态与失败，不以该领域扩大Runtime授权。

公开GET /api/decks/{deck_id}消费deck.detail/current OAuth，four exact schemas/hash，outer与每个Voice deck_id必须匹配。原null404/owner int/时间/Memory值保持；Admin Repository按原字节投影nullable/raw Memory文本，Dream兼容投影继续把合法JSON解析为原值、保留empty text并把非法JSON映射为null，不在读取时回写修复。无read retry或DB fallback。详见[Deck详情现行规则](../design/deck/deck-detail-version-history.md)。

GET /api/decks的published false/true两mode均消费deck.list/current OAuth/dream:read与four exact schema/hash。Admin处理过滤/计数/排序/policy；user保留total_voice_count并省略author_display_name，community保留author_display_name并省略total_voice_count。无默认初始化/文件检查/DB fallback/read retry。详见[现行规则](../design/deck/deck-detail-version-history.md)。

GET /api/story-workspace/workflow-preflights/{preflight_id} 独立消费 workflow-preflight.read/current OAuth/dream:read 与 identity/unified exact schemas/hash，响应匹配 canonical actor 和 ID，复用原 17 字段状态/微秒与 datetime JSON。移除该读取无关 default Workspace 初始化；原坏 ID/owner/missing 404 保留，其他安全错误带原 UUID 无重试。POST 使用 OAuth/dream:write、三项 exact schemas 与 workflow-preflight.execute，input_json沿原 canonical 参数编码，reply actor/Deck/revision匹配，保留202/17字段。独立服务器 receipt reader支持原 absent/in_progress/committed，不自动resume或重发；通用两态receipt保持。详见[现行消费设计](../design/workflow-preflight-read-current.md)；POST default Workspace已由注册76的OAuth-write ensure承担，隐藏 source 持久化仍为后续入口。

Run read/create/retry使用当前OAuth read/write、identity/unified两项exact schemas与已发布hash，原200/201和完整28字段/lifecycle/微秒JSON保持。Reply匹配actor/Workspace，read ID、write key/retry_of及Create source；相同key可保留原同语义PF ID。未知提交保留原UUID/unknown，显式generic两态receipt，不重发；原业务errors仅按实际code/status匹配投影。三个入口的default依赖已使用注册76的OAuth-write ensure；服务器尚无workspace_id的Run GET也要求write，read-only403且停止。其余生命周期与内部default持久化已由对应Admin operation接管。详见[现行Run消费](../design/workflow-run-admin-consumer-current.md)。

生产 launch endpoint 把同一个服务端 `AdminRequestActor` 与 `AdminDataClient` 传给 source、Preflight、Run、dispatch 和 failure 适配器。Registry133 `dream-launch-replay.lookup` 在 current actor 的 owned Workspace/Deck 范围内恢复原 Run/Preflight/source identity；无 replay 才解析当前模型并执行 Registry130-132 Runtime 准备。source/Preflight/Run 写入、claim/finish、Run fail 与 failure envelope 都使用严格 Pydantic DTO，对应 Admin Zod DTO → Service → typed Drizzle Repository；未知写只读取原 request receipt，不重发，也不回退 Dream PostgreSQL。Voice system prompt 通过 `deck.detail` 读取，Agent Runtime、EventBus、SSE 与共享文件仍在 Dream。详见[launch 现行设计](../design/dream-launch-admin-metadata-current.md)。

Workspace content/download 的 current OAuth 身份继续共用 get_current_user；Thread ownership 改为 chat-thread.get 与原 strict DTO/four exact schema/hash，reply ID/actor 匹配后才执行原 Mode/path/existing filesystem。metadata 错配/不可用固定503/null404，无自动重试或PG fallback；原 ZIP/symlink/no-create/header保持。SystemConfig与其它文件metadata通过Admin DTO读取；普通共享文件和真实Bash仍需在正常服务切换后的业务验收中确认。

公开Run cancel复用OAuth-write/default ensure、原reason编码和两项exact schemas，调用workflow-run.cancel并返回绑定actor/Workspace/Run/cancelled的原28字段模型/200。Unknown使用原UUID/显式generic两态receipt/no resend；原业务error映射/scoped安全422与微秒保持。Agent cancel和其它生命周期生产入口不改，见[现行Run规则](../design/workflow-run-admin-consumer-current.md#公开-run-cancel)。

三个公开默认resolver已共用routers.deps.resolve_admin_default_workspace，服务器workspace_id非空复用，否则OAuth-write/empty ensure/two exact schemas/原text ID/default-before-domain，unknown原UUID且不自动重发。Deck Plugin已有服务器role非空保持；缺role时复用AdminRequestAuth.current_profile，OAuth dream:read/identity v1/原profile hash及canonical ID匹配后取raw role，unavailable/timeout/错配不使用user fallback。原permission/scope/DTO判断不变，只有write且需profile的POST按已发布readscope403。三resolver、binding/control-plane provider和internal/background输出均无Dream SQL或数据库fallback。详见[共享默认规则](../design/workflow-preflight-read-current.md#三个公开-current-user-resolver)。
### Launch 失败持久化

Request owner 注册 `workflow-run.fail` 与 `dream-launch-failure.envelope` 并由生产 `DreamLaunchFailureRecorder` 消费。Run fail 只检查 current actor/Workspace/Run/failed 完整模型，保留同 failed 重放的历史详情；envelope 匹配服务器 source IDs 与原始 error，不接受 caller metadata/codec。

生产 launch 请求使用 current OAuth `dream:write`；Dream 不用 actor_id 或通用服务密钥推断权限。失败路径保持两个提交边界：先提交 Run failed，再提交 source failure envelope；任一步结果未知都用原 UUID 查询原 receipt，第二步不会在第一步未确认 failed 时执行。技术与正常业务验收边界见[Run规则](../design/workflow-run-admin-consumer-current.md#run-fail-生产接线)与[launch 现行设计](../design/dream-launch-admin-metadata-current.md)。
