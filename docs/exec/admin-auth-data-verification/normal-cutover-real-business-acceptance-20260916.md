<!-- [Input] Normal Admin/Dream/Gateway/PostgreSQL services, the user-authorized existing account, and actor-bound public product routes. -->
<!-- [Output] Pre-mutation business scope plus append-only command and acceptance receipts for the 2026-09-16 normal cutover. -->
<!-- [Pos] Real-business acceptance record; contains no password, OAuth token, service credential, transcript body, or database DSN. -->
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
| 既有主体关系 | read-only PostgreSQL probe；只输出主键、状态、映射存在性和口令验证布尔值 | `0` | active canonical user 1 条、active Admin member 1 条；Better Auth user/account、Dream subject link、Admin subject link 均为 0；提供的验收口令与两条旧 hash 均不匹配 | 密码登录 `401` 是正确 fail-closed；不能按同邮箱自动建立映射或覆盖旧 hash |
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
| Dream backend受控重启与浏览器reload | task-owned `127.0.0.1:8765`、现有Chrome登录页 | backend启动完成；Agent选择器不再显示`INVALID_TOKEN_RESOURCE`，历史会话正常加载 |
| Admin管理权限隔离 | 同一浏览器`http://localhost:3000/admin` | 重定向/停留于Admin login，没有进入dashboard |

尚未完成的真实项目：模型消息已选择Screenwriter并准备草稿，但实际发送需浏览器动作时确认；Device批准/拒绝/兑换/refresh/revoke、退出/Session失效、文件与故障恢复仍继续验收。本节不把登录成功扩张为这些下游项目已通过。
