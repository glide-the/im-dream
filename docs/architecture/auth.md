<!-- [Sync] 2026-09-15: file reads consume current OAuth Thread ownership before unchanged file rules. -->
<!-- [Sync] 2026-09-15: consume public Preflight GET with canonical actor/ID matching and no Workspace SQL. -->
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
<!-- [Sync] 2026-09-15: distinguish server turn persistence from CLI and Editor purpose grants. -->
<!-- [Sync] 2026-09-15: retire standalone authority and require explicit OAuth/profile account matching in scripts. -->
<!-- [Sync] 2026-09-14: record the implemented Admin BFF and public issuer retirement; retain original history. -->


五公开Deck写操作的正常流程、状态、原错误/删除反馈与验收以[现行稿](../design/deck-mutations-current.md)为准；尚未迁移的list/detail/create/default/安装metadata保留依赖。

# Dream 接入 Admin 认证

统一Client的catalog refresh/readiness与广告检查共享同步边界。正在加载时其它已验证调用等待完整结果；失败清空ready/广告并由后续认证重新加载，不能沿用旧广告。领域HTTP保持并发、显式per-request token/DTO/UUID，认证校验、scope与原receipt语义不变。

## 背景与问题

baseline `7d38715c` 中 `backend/auth.py` 自签 HS256 用户 token，`routers/oauth.py` 用 Authlib 做 Google 登录并按配置合并同邮箱账户，`routers/device_oauth.py` 自行维护 device/refresh 状态。浏览器读取 URL fragment/localStorage token，部分 API 直达 Python。这些实际实现与 Admin 唯一认证中心目标冲突。

本稿记录迁移目标、当前源码范围与评审约束，不能作为正常部署或真实账户验收回执。状态见[执行计划](../exec/dream-admin-auth-data-plan.md)。[旧认证原文](history/pre-admin-auth-data-20260914/auth.md)完整保留接口和历史测试；其中旧 authority、邮箱自动合并与 DB 直连不再是目标规范。

## 目标与边界

Admin 使用 Better Auth 内置 Google social sign-in、Admin callback、OAuth authorization/device/token、JWKS与账户映射。Dream Next 是同源 BFF；FastAPI 是 OAuth Resource Server 与业务编排，不能签用户登录 token、验证 Google token或维护另一套 session/refresh/device authority。Admin管理和Dream访问权限独立，同主体登录Dream不获得Admin管理。

Admin唯一规范位于其仓库 `docs/architecture/admin-dream-auth-data-contract.md`。当前客户端已按实际DTO与路径消费；发布能力与本机业务回执分别记录，本稿不自定 endpoint、claim 或 capability。跨项目业务设计见[认证与数据交互](admin-auth-data-interaction.md)。

## 概念与规则

| 边界 | 执行模块与判断 | 失败处理 |
| --- | --- | --- |
| Google身份认证 | Admin Better Auth校验state/code/OIDC与稳定provider subject | 登录页说明失败；Dream不签token |
| 用户映射 | Admin保留users.id与业务FK，仅显式校验的关联流程绑定已有账户 | 同邮箱不自动合并；冲突返回明确错误 |
| BFF登录 | Next发起code+PKCE；callback校验一次性state、code、固定redirect URI与PKCE | 拒绝缺失/重放/开放redirect，清该次登录状态 |
| BFF会话 | Dream host-only HttpOnly opaque handle；tokens存服务端；Admin session只属Admin origin | 撤销/过期重新登录；服务故障保留可恢复状态 |
| Dream API | 成熟JWT/JWKS库验证签名、闭集算法、issuer/audience、时间、subject与scope | 无效/过期/错误资源为401；scope不足403 |
| Admin领域数据 | 独立service credential+用户access token或限定后台授权；Admin检查实体归属 | service不能凭body/header任意user_id改actor |
| Admin管理 | 独立管理权限校验 | Dream scope不授予管理能力 |

### 浏览器主拓扑与配置

主拓扑：Dream同源BFF + PKCE → Admin OAuth authorization → Admin Google/login → Dream callback。Admin与Dream分别持有host-only cookie，无Domain共享，不因同网段推断cookie互通。生产HTTPS使用Secure/HttpOnly；SameSite与callback method按实际契约冻结。浏览器REST/SSE认证读写进入Dream origin；不能跨域转发任意Cookie或启用通配credential CORS。

server-owned配置明确Dream public origin、Admin issuer/origin、注册callback URI、内部FastAPI URL。代理按部署配置确定origin，不相信任意forwarded header。BFF mutation校验origin/CSRF，return location限定同Dream origin页面并恢复device上下文。callback URL不能携带access/refresh token。

当前本机事实由协调只读确认：Web配置同时出现`127.0.0.1:5173`与`localhost:5173`，Python为8765、Admin/Gateway为3000，Admin allowlist未覆盖所有Dream origin；这不是最终一致拓扑。实施必须选定一个显式Dream origin并对齐OAuth注册、Google callback、代理、Cookie/CORS/CSRF。gitignored用户环境不进commit。

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

未登录 → 登录中 → callback校验 → 会话建立 → 已登录。拒绝、错误state、过期code返回未登录。refresh先保留现有会话，成功原子替换，invalid grant重新登录；Admin故障显示稍后重试，不解释为错误密码或删除数据。logout先等Admin成功撤销才清本BFF handle，失败保留会话并提示，不增加重复确认。

Browser唯一owner保存strict immutable公开session snapshot，并从该snapshot导出内存CSRF。每个session读取取得当前read object identity，fetch/JSON await或catch后检查identity与AbortSignal；aborted/superseded返回null且不修改状态，旧401/失败不能清除新session或覆盖错误。clear与logout开始使已有read失效；logout失败保留已验证snapshot，strict success才清除并使期间pending读取失效。AuthContext在then提交前同时检查未abort与returned snapshot仍属当前owner，避免已返回但随后被clear/新session替换的user被再次显示。该规则只处理Browser异步状态，不修改服务端handle/refresh或MCP OAuth。

业务前校验身份/scope，Admin再校验实体权限。401、403、409、capability不足、unavailable、timeout分别保留语义。日志仅记录request ID、operation、状态，不记录token/code/secret/正文。

## 影响范围、验收与发布

依据[完整数据清单](../exec/dream-admin-data-inventory.md)迁移。验收覆盖Google redirect/callback/state/PKCE、Cookie/CORS/CSRF/origin、JWT各字段与kid刷新、并发refresh/撤销、Device、实体权限、REST/SSE/Voice/Node/stdio/background委托和旧authority静态复查、公开生产入口。

Luna runner执行确定性技术验证并返回cwd/command/exit/output。真实验收必须正常本机Dream/Admin/Gateway/PG、用户指定现有账户实体模型限次、正常Admin可见Run与日志；fixture不能替代。发布按Admin expand/API capability → Dream兼容切换 → backfill/validate → contract；两端共同确定session/密钥回滚策略。

## 当前旧入口与外部协议边界

`/api/register`、`/api/login`、`/oauth/google/login/callback`、`/oauth/device/code`、`/oauth/device/verify` GET/POST、`/oauth/token` 和 Python `/auth/logout` 保留原路径并返回410 `DREAM_AUTHENTICATION_RETIRED`。配置解析出的Admin issuer/authorize/token/device/code/revoke/JWKS/verification/resource信息用于client迁移；不解析或转发密码、code、refresh和Cookie，不签本地token、不更新账户/device/refresh表。公开authority缺失或非法时503，不从Host/query猜目标。Browser由Next `/auth/start/callback/session/logout`执行既有PKCE/handle流程，密码、注册和Google功能在Admin唯一UI。

Authlib在原两个issuer router中仅用于Dream Google/Device authority，现已退役，并与bcrypt一起从Python manifest/lock/export移除，其余依赖版本不变。Managed MCP外部server授权继续由标准 `mcp.client.auth.OAuthClientProvider`和TokenStorage执行，协议、加密存储、refresh和取消保持；Notion connector的现有credential/login不受本阶段影响。`backend/auth.py`保留历史helper标识符，本地签发/密码接口抛安全退役错误，旧token验证/renewal拒绝，只有duration/SHA-256/header纯函数保持；不读secret或默认key。两个维护/验收脚本必须显式提供Admin OAuth，缺失时在I/O前失败；公开 `/api/me` 必须匹配指定账户，错配时在thread/model/业务写入前失败。Gateway verifier的旧subject helper仍需purpose迁移。typed `/api/me`/`/auth/me`与独立数据导入保持，导入DB还未迁移。

公开Chat以当前OAuth读取Admin唯一Workflow上下文，在message/SSE前拒绝权限、绑定、capability或DTO失败；immutable snapshot只带已认证actor/thread和原上下文，不含credential，不向Browser/SDK投影。Service包括普通null均复用该snapshot，内部confirmation/launch仍待typed服务身份迁移；不能据此声明后台long-turn授权已完成。

公开Agent的Thread resume读取和SDK init/final/repair Session回写复用该exact Thread/Run server-persistence grant。`AdminTurnPersistence`校验reply Thread/canonical actor，未知user/session写共用原operation/input/UUID恢复；最近一次确认Session才可复用，A→B→A必须重新写。SDK init失败继续原日志处理，已经运行的turn/cancel保持原语义；未迁移assistant/Run写不属于此owner，不能据此宣称全域未知写屏障。

公开user-turn先创建绑定当前Thread/authoritative Run、仅dream read/write的server-persistence委托，再调用Admin原子user message/title/confirmation事务；Service复用已确认的同一输入。未知写保留原request ID并只查询原receipt，absent阻止后续写与推理。Factory在既有admission后启动后台renew，SSE断开保留turn，terminal/cancel安排自有cleanup并由shutdown drain同步writer、renewal线程和独立HTTP client。凭据不进入Browser、CLI或Editor；assistant/后台Session上下文与其它后台领域仍待迁移，Gateway/Editor仍需独立purpose。详细状态与失败处理见[认证与数据交互](admin-auth-data-interaction.md)。

Next同名password/Google/Device/token薄adapter也返回410，login/register在generic proxy前执行，避免未登录401遮住迁移响应；Next `/auth/logout`仍执行实际BFF handle撤销。两端退役owner只读取三项公开authority配置，不要求private service凭据。

公开Session六operation由当前已认证request OAuth执行，继续绑定Admin principal；shared helper只投影该Bearer到指定typed consumer，不接受body actor ID、不做本地renew。Session read/write的工具与后台授权独立于Thread server-persistence，现行Handler拒绝该purpose；后续Editor只能消费exact existing Session的editor-stdio grant。失败/unknown和Edit Session事件规则见[交互设计](admin-auth-data-interaction.md)。

公开Deck内容版本五operation只使用当前request OAuth与Admin principal，schema要求identity/unified/content-versions/canonical-storage四项exact v1。管理权限不接受Thread或CLI/Editor purpose。共享actor invocation保持同一认证和threadpool，只由domain adapter生成安全错误响应。领域catalog刷新失败清除ready，下一认证重新加载后再执行profile/Chat等operation；不回退旧issuer/SQL。

公开user-preferences.get/save只由当前OAuth用户管理；所有Runtime entity grant不能替代该授权。闭集字段不含body actor/firstlogin/systemconfig；identity/unified exact capabilities与Admin principal继续校验。原NULL partial merge/缺行{}保留，后台context/System/first-login与import仍独立。现行[用户偏好设计](../design/user-preferences-current.md)描述状态与失败，不以该领域扩大Runtime授权。

公开GET /api/decks/{deck_id}消费deck.detail/current OAuth，four exact schemas/hash，outer与每个Voice deck_id必须匹配。原null404/owner int/时间/Memory值保持；无read retry或DB fallback。实际Admin producer目前将empty Memory归null，与原Dream保留emptytext不同，仍需修正且不计该值真实验收完成。详见[Deck详情现行规则](../design/deck/deck-detail-version-history.md)。

GET /api/decks的published false/true两mode均消费deck.list/current OAuth/dream:read与four exact schema/hash。Admin处理过滤/计数/排序/policy；user保留total_voice_count并省略author_display_name，community保留author_display_name并省略total_voice_count。无默认初始化/文件检查/DB fallback/read retry。详见[现行规则](../design/deck/deck-detail-version-history.md)。

GET /api/story-workspace/workflow-preflights/{preflight_id} 独立消费 workflow-preflight.read/current OAuth/dream:read 与 identity/unified exact schemas/hash，响应匹配 canonical actor 和 ID，复用原 17 字段状态/微秒与 datetime JSON。移除该读取无关 default Workspace 初始化；原坏 ID/owner/missing 404 保留，其他安全错误带原 UUID 无重试。详见[现行读取设计](../design/workflow-preflight-read-current.md)；POST execute、Run 创建/重试与隐藏 source 持久化仍为后续入口。

Workspace content/download 的 current OAuth 身份继续共用 get_current_user；Thread ownership 改为 chat-thread.get 与原 strict DTO/four exact schema/hash，reply ID/actor 匹配后才执行原 Mode/path/existing filesystem。metadata 错配/不可用固定503/null404，无自动重试或PG fallback；原 ZIP/symlink/no-create/header保持。SystemConfig读取与其他文件管理metadata仍pending，技术测试不代表普通共享文件/真实Bash验收。
