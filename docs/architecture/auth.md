<!-- [Input] Dream baseline auth/BFF and the Admin-owned contract when frozen. -->
<!-- [Output] Dream consumer design, authority retirement, topology and acceptance gates. -->
<!-- [Pos] Dream authentication consumer; Admin owns Better Auth, OAuth and signing keys. -->
<!-- [Sync] 2026-09-14: change the target authority and retain original history. -->

# Dream 接入 Admin 认证

## 背景与问题

baseline `7d38715c` 中 `backend/auth.py` 自签 HS256 用户 token，`routers/oauth.py` 用 Authlib 做 Google 登录并按配置合并同邮箱账户，`routers/device_oauth.py` 自行维护 device/refresh 状态。浏览器读取 URL fragment/localStorage token，部分 API 直达 Python。这些实际实现与 Admin 唯一认证中心目标冲突。

本稿是迁移目标与评审约束，尚不能作为实现或部署回执。状态见[执行计划](../exec/dream-admin-auth-data-plan.md)。[旧认证原文](history/pre-admin-auth-data-20260914/auth.md)完整保留接口和历史测试；其中旧 authority、邮箱自动合并与 DB 直连不再是目标规范。

## 目标与边界

Admin 使用 Better Auth 内置 Google social sign-in、Admin callback、OAuth authorization/device/token、JWKS与账户映射。Dream Next 是同源 BFF；FastAPI 是 OAuth Resource Server 与业务编排，不能签用户登录 token、验证 Google token或维护另一套 session/refresh/device authority。Admin管理和Dream访问权限独立，同主体登录Dream不获得Admin管理。

Admin唯一规范位于其仓库 `docs/architecture/admin-dream-auth-data-contract.md`。当前等待冻结；客户端实现前记录实际路径、版本和发布回执，本稿不自定 endpoint、claim 或 capability。跨项目业务设计见[认证与数据交互](admin-auth-data-interaction.md)。

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

Voice WebSocket也必须校验origin并取得受限用户委托，不能将opaque handle当OAuth token或让旧query token绕开新验证。现行Next Route Handler不提供WebSocket upgrade；upgrade/proxy或一次性连接授权必须结合实际Voice路由和Admin契约确定，这是必需接入点。

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

未登录 → 登录中 → callback校验 → 会话建立 → 已登录。拒绝、错误state、过期code返回未登录。refresh先保留现有会话，成功原子替换，invalid grant重新登录；Admin故障显示稍后重试，不解释为错误密码或删除数据。logout清本BFF handle并请求Admin撤销，保留失败范围，不增加重复确认。

业务前校验身份/scope，Admin再校验实体权限。401、403、409、capability不足、unavailable、timeout分别保留语义。日志仅记录request ID、operation、状态，不记录token/code/secret/正文。

## 影响范围、验收与发布

依据[完整数据清单](../exec/dream-admin-data-inventory.md)迁移。验收覆盖Google redirect/callback/state/PKCE、Cookie/CORS/CSRF/origin、JWT各字段与kid刷新、并发refresh/撤销、Device、实体权限、REST/SSE/Voice/Node/stdio/background委托和旧authority静态复查、公开生产入口。

Luna runner执行确定性技术验证并返回cwd/command/exit/output。真实验收必须正常本机Dream/Admin/Gateway/PG、用户指定现有账户实体模型限次、正常Admin可见Run与日志；fixture不能替代。发布按Admin expand/API capability → Dream兼容切换 → backfill/validate → contract；两端共同确定session/密钥回滚策略。
