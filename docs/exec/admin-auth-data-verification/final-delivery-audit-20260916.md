<!-- [Input] Exact Admin/Dream heads, four published baseline releases, current contracts, CI receipts and private cutover preflight state. -->
<!-- [Output] Requirement-by-requirement delivery status that separates source proof, normal deployment and real business acceptance. -->
<!-- [Pos] Final coordinator audit; it is not a production-approval token and contains no credential or business正文. -->
<!-- [Sync] 2026-09-17: record normal resource-policy desired/effective/revision/LKG and fresh observer parity. -->
<!-- [Sync] 2026-09-17: record real Chrome Dream logout, same-subject SSO re-entry and continued Admin-login isolation. -->
<!-- [Sync] 2026-09-17: record focused logout/session regression and the real-Chrome harness boundary before any logout mutation. -->
<!-- [Sync] 2026-09-17: bind the audit to Admin f79a099 / Dream 2df9d9b4, the corrective normal ACL activation and the public Notion DTO/ORM read. -->
<!-- [Sync] 2026-09-17: record independent Admin sessions, confidential service OAuth, complete deterministic suites and the remaining real-acceptance boundary. -->
<!-- [Sync] 2026-09-16: reconcile real Device approval/exchange, Dream resource access, refresh rotation and replay-family invalidation. -->
<!-- [Sync] 2026-09-16: reconcile independent revoke/deny, migration 0063, Product OAuth forwarding, Gateway key rotation, complete Settings search and MCP replacement-auth status. -->
<!-- [Sync] 2026-09-16: reconcile exact legacy Google adoption, successful real return and Better Auth audience compatibility repair. -->
<!-- [Sync] 2026-09-16: reconcile the audit with the applied normal cutover, live no-PostgreSQL proof, OAuth catalog and partial real auth/Device receipts. -->
<!-- [Sync] 2026-09-16: add exact Admin/Dream release binding and physical-backup isolated cutover rehearsal evidence. -->

# Admin 统一认证与数据服务最终交付审计

## 结论边界

源码实现、跨项目契约、隔离数据库合同和确定性构建已经完成并在当前分支复核。本机命名正常 `ink-memory` 已从 54 个 migration receipt 前向升级到 64 个，受限角色/ACL、9项发布门槛 capability、私有配置、OAuth client/resource catalog 和正常 Admin/Dream 服务已经激活。Google Cloud 已保存本地与生产 Admin callback；精确旧 `provider_sub` 主体采用通过 release-only DTO/Service/Drizzle 事务完成，真实 Google callback、Admin consent和返回Dream成功。真实Better Auth双受众JWT暴露的`INVALID_TOKEN_RESOURCE`也已通过封闭受众规则修复并在浏览器复验。Device允许、拒绝、token兑换、Dream Resource Server调用、refresh rotation、旧refresh重放、独立主动revoke、重复device兑换和真实access expiry已经通过。Dream当前browser client的真实退出、登录页回退、同主体SSO重新进入和Admin管理登录隔离也已通过；自然等待中央Session或handle TTL到期仍未执行。Product 本地 signer 已退休，Gateway key exact Runtime scopes 已通过 DTO/Service/Drizzle rotation 修复。MCP replacement 已完成并由正常页面复用持久化凭据返回 41/25/10 inventory；两次真实文件上传、授权读取和 Thread workspace 边界通过。认证业务域评审后的代码已把Admin管理登录恢复为独立`admin_users/admin_sessions/RBAC`，并把Dream服务身份改为confidential OAuth client：后台只用`client_credentials`，用户数据请求同时携带服务token和Dream用户委托token，旧静态service头被拒绝。正常ACL已补齐Admin credential、Session、audit与RBAC所需权限，同时继续拒绝Admin角色读取Dream业务表和旧`identity.admin_subject_links`。Notion后台读取也已通过公开`client_credentials`入口验证严格DTO投影；正常资源策略desired与Dream observer effective/revision/effort、新鲜心跳和精确内存组合已只读对齐。两种页面模型调用均被正常账户的当前周期 Token 额度以 `402` 拒绝，因此可见模型回复、Run/Thread继续/取消和SSE终态仍未完成；Admin真实后台登录还需现有Admin自身有效凭据。本审计不能用于宣称整项任务完成。

实现快照与审查入口：

| 项目 | 实现基线 / 审计分支 | 审查入口 | 状态 |
| --- | --- | --- | --- |
| Admin | `f79a0992eead124b1c05ae049c5440b60baee9e2` / `codex/admin-auth-data-provider` | [Draft PR #15](https://github.com/glide-the/dream-im-platform/pull/15) | 该实现基线落地DTO → Domain Service → typed Repository → Drizzle及正常ACL实际角色探针；审计分支在其后只追加正常资源策略回执文档 |
| Dream | `2df9d9b423dac3131a0f15494272a821cea8f313` / `codex/dream-admin-auth-data-client` | [Draft PR #63](https://github.com/glide-the/im-dream/pull/63) | 该实现基线完成confidential OAuth消费；审计分支在其后只追加本文件等状态文档，前后端验证通过且仅保留既存未跟踪 `.pnpm-store/` |

## 1. 基线发布

四个重构前基线均为已发布 prerelease，tag 指向已提交 commit：

| 项目 | Tag → commit | Release |
| --- | --- | --- |
| Dream | `v0.1.3-pre-admin-auth-data.20260914` → `7d38715c1a8f74cb5fb3dcb114320156eaf6b3e6` | [本次重构前的基线版本 · Dream 0.1.3](https://github.com/glide-the/im-dream/releases/tag/v0.1.3-pre-admin-auth-data.20260914) |
| Admin | `v0.1.0-pre-admin-auth-data.20260914` → `017f3acccc57991f0b3771c1c9bb9dd765255b07` | [本次重构前的基线版本 · Admin 0.1.0](https://github.com/glide-the/dream-im-platform/releases/tag/v0.1.0-pre-admin-auth-data.20260914) |
| Runtime | `v0.1.9-pre-admin-auth-data.20260914` → `d9c16304330b393c86e650926b191c0cfeaf0bf2` | [本次重构前的基线版本 · Runtime 0.1.9](https://github.com/glide-the/ink-claude-code-dream/releases/tag/v0.1.9-pre-admin-auth-data.20260914) |
| Python SDK | `v0.2.145-pre-admin-auth-data.20260914` → `d6b87f14549c01f921c664fe525ba986b4ac8d88` | [本次重构前的基线版本 · Python SDK 0.2.145](https://github.com/glide-the/ink-claude-dream-agent-sdk-python/releases/tag/v0.2.145-pre-admin-auth-data.20260914) |

## 2. 任务与责任

| Codex 任务 | 责任 | 当前证据 |
| --- | --- | --- |
| `01a0a03d-f058-7130-bfa9-71d2bb0bc1c9` | Admin 统一认证、Drizzle、DTO/Service/Repository/API | 最新 turn 完成，任务 idle；分支与 PR 保存实现 |
| `01a0a03e-02f7-7221-9118-8bf3f6a91cb3` | Dream 认证/BFF、Admin data client、全生产数据库入口关闭 | 最新 turn 完成，任务 idle；分支与 PR 保存实现 |
| `01a0a521-96ac-7aa1-98ae-877455d5a8d1` | 跨项目契约、依赖、进度与验收 | 最新 turn 完成，任务 idle；整体 goal 保持 active 等待正常 cutover/真实验收 |

指定任务 `01a0a183-883a-7062-b88b-ca441ebafa26` 的 Admin commit `7a6e6c966561beeac7724fd77828a9f4ce3b26ec` 已是 Admin 工作分支祖先；详情见[最终 worktree 同步审计](worktree-sync-final-audit.md)。

## 3. 能力和数据库归属

采用同一 PostgreSQL database 内的明确 schema/表级职责与受限角色，而不是拆成两个 database：既有 canonical User、Story、Deck、Thread、Subscription、Gateway 与账本存在跨领域 FK 和事务；分库会要求复制身份或引入分布式补偿，整域迁 schema 也不能替代表级 ACL。物理区域为 `identity`、`public`、`dream`、`drizzle`，Admin 使用独立 AUTH/DATA/CONTROL 凭据，Dream 为 NOLOGIN 且生产进程不持有 PostgreSQL DSN。

生产数据调用链固定为：

```text
Dream Pydantic DTO
  → Admin Zod DTO
  → Domain Service
  → typed Repository
  → Drizzle / PostgreSQL transaction
```

Admin 契约 artifact 当前含 191 个具名 operation。接口不接受任意 SQL、表列 selector、任意外部 user ID、Google token/ID token 或无权限过滤 CRUD。Dream 不在 Admin 不可用时回退 PostgreSQL。

权威文档：

- [Dream 消费端交互与数据边界](../../architecture/admin-auth-data-interaction.md)
- [Dream 总体架构](../../architecture/项目架构设计说明.md)
- [Admin 统一契约](https://github.com/glide-the/dream-im-platform/blob/codex/admin-auth-data-provider/docs/architecture/admin-dream-auth-data-contract.md)
- [Admin 数据区域方案](https://github.com/glide-the/dream-im-platform/blob/codex/admin-auth-data-provider/docs/architecture/admin-dream-data-ownership.md)

## 4. 认证和 Device Flow

Admin Better Auth 1.7.4 是 Dream OAuth 的唯一认证中心；Google 使用 `socialProviders.google`。Admin 负责 Dream callback、Account/User 关联、授权页Session、OAuth Provider、RFC 8628、JWT/JWKS、refresh/revoke 和 Dream 主体映射。Admin operator 另由`admin_users/admin_sessions/RBAC`认证授权，不进入Dream OAuth user体系。Dream BFF 保存 opaque handle，Dream Resource Server 校验签名、算法、issuer、audience、时间声明、主体和适用 scope；Dream API 不接受 Google token、OIDC ID token或任意用户 ID header。

Google、Better Auth Session、service JWT、OAuth access/refresh token 与 OIDC ID token 已在契约中分开；同一产品身份不会自动取得 Admin RBAC。CLI/设备客户端是 public client，固定 client secret 不进入制品。Admin 正常库已通过 DTO/Drizzle provisioning 注册 Dream API resource、browser public client、device public client和两条resource link；重复 dry-run 全部为 `unchanged`。

公开 Device 请求已实际返回 `device_code/user_code/verification_uri/expires_in/interval`，首次轮询为 `authorization_pending`，过快复轮询为 `slow_down`；unknown client/resource、外部 `user_id` 和越权 scope 分别 fail closed。用户在正常授权页点击允许后，device grant兑换返回300秒Bearer JWT和refresh；Dream公开`/api/me`完成JWKS/issuer/audience/scope校验并映射到canonical user `7`。refresh正常轮换，旧refresh重放和重复device兑换均返回`invalid_grant`且不签token。另建的未轮换refresh链路经公开revoke后复用返回`invalid_grant`，证明主动撤销；独立Device在页面拒绝后轮询返回`access_denied`，到期后的再次复核返回`expired_token`。设备码和Token未进入回执。[认证数据 ER 与流程图](../../architecture/auth-identity-er-and-flows.md)明确 `identity.user`、Dream canonical user 和 Admin member 分离；本次精确采用创建Dream subject link而没有Admin link，同邮箱未用于自动合并或授权。

## 5. Dream 生产数据库关闭

当前 Dream 生产图不包含 PostgreSQL credential、driver、SQL、ORM、UOW、DDL、自动建表或 SQLite runtime fallback。`server.py` 不加载数据库 URL或创建 pool；历史数据库实现仅位于 `backend/tests/**` 的明确 fixture/harness。部署模板清空旧数据库变量并只投影 Admin base、issuer/resource、service identity 和 BFF cookie secret。

静态关闭门禁与当前完整 backend suite 已通过：`3538 passed, 24 skipped, 615 subtests passed`。本轮进一步在正常服务上验证：Dream Next 进程和 Python 进程均没有 `DATABASE_URL`/PostgreSQL/PG credential 环境键；两进程到正常 PostgreSQL `54329` 的实际 TCP 连接数均为 0；Admin、Dream 页面和 Dream health 分别在 `3000/5173/8765` 返回 `200`。该运行证据证明当前启动实例没有 Dream→PostgreSQL 旁路；完整用户持久化业务仍需登录后公开流程验收。

## 6. 保持的业务语义

- Runner、ThreadFactory、Service、EventBus、SSE、turn/resume/cancel 与 admission/lease 顺序保持在 Dream。
- 资源策略继续区分 `default`、Admin `desired`、Dream `effective`、revision 与 LKG；Agent turn 主路径不查询数据库或远程策略。
- 共享文件系统继续由 Dream 执行路径规范化、owner检查、符号链接/越界拒绝和失败恢复；文件字节不经过 Admin 数据接口。
- `CLAUDE_CODE_TMPDIR={AGENT_CWD}/{thread_id}/.claude-tmp`、真实 Thread workspace、`0700` 与精确 sandbox 放行范围不变。
- Runtime `0.1.10`、SDK `0.2.145`、Plugin CLI 与官方 Claude CLI 分离由生产 Docker build 验证。

## 7. 实现快照与审计提交自动化证据

| 命令/运行 | 工作目录或平台 | 结果 |
| --- | --- | --- |
| Admin [Test Suite 35080308352](https://github.com/glide-the/dream-im-platform/actions/runs/35080308352) | GitHub / Admin `894c8221` | 历史提交 exit `0`；50s，63/63 migrations，8 capabilities，repeat no-op |
| 同一 Admin deterministic job | GitHub / Admin `894c8221` | exit `0`；3m41s，13 config tests、274 files / 2074 tests passed，17 files / 36 tests skipped；ESLint、tsc、Next 16.1.6 build通过 |
| Admin current deterministic suite | Admin工作分支当前树 | exit `0`；277 files / 2091 tests passed、17 files / 36 tests skipped；ESLint、TypeScript、Next production build通过 |
| Admin正常ACL修正与实际角色探针 | Admin `f79a099` + 本机正常 `ink-memory:54329` | exit `0`；物理备份与manifest均`0600`，dry/apply/repeat通过；64 migrations、8个激活门禁 capability、144条策略、Gateway binding与四角色probe通过；AUTH可读credential并写Session/audit，仍不能读Dream表或旧Admin subject link |
| Notion后台DTO/ORM公开读取 | Admin `f79a099` + 正常OAuth/Data API | exit `0`；Repository/Service 17/17、tsc、ESLint通过；公开`client_credentials` token为`200`，`notion.sync-candidates.list`为`200`并返回1个connector，响应没有`*_json`存储字段 |
| Dream退出/Session焦点回归 | Dream `frontend` + 本机Chrome | `node --test app/api/_auth/handlers.test.ts app/_dream/lib/browserSession.test.ts` exit `0`、27/27；真实Chrome退出后只显示登录入口，再次登录经保留的中央Dream SSO返回同一主体；同profile Admin入口仍为独立登录页；自然TTL到期未等待 |
| 正常资源策略/LKG只读验收 | Dream生产Admin client + 正常Admin/PostgreSQL | exit `0`；公开desired为configured revision 4；最新Observer心跳约0.23秒，applied revision、四项effective、effort与desired一致，required-headroom精确，queue dropped为0；未改desired或触发turn |
| Dream [Frontend CI 35112741361](https://github.com/glide-the/im-dream/actions/runs/35112741361) | GitHub / Dream `4018aabd` | exit `0`；1m10s，frozen pnpm install与Next production build通过 |
| Dream [Backend CI 35112741412](https://github.com/glide-the/im-dream/actions/runs/35112741412) | GitHub / Dream `4018aabd` | exit `0`；13m51s，生产 Docker image dry-run通过 |
| Dream BFF/部署焦点 | 本机 Dream `4018aabd` | exit `0`；BFF boundary、Remote SSH env projection、`git diff --check`通过 |
| `.venv/bin/python -m pytest -q tests` | Dream `backend`工作分支当前树 | exit `0`；3538 passed、24 skipped、615 subtests passed |
| Dream OAuth audience与产品边界焦点 | Dream `backend`，当前未提交修复 | exit `0`；81项audience/JWKS合同与117项auth/product边界通过；真实浏览器不再显示`INVALID_TOKEN_RESOURCE` |
| Admin 0063 与 Reflection authority | 本机 Admin 当前树 | exit `0`；具名隔离 PostgreSQL 0000–0063、64 receipts、FK/CHECK/capability/repeat apply通过并清理；正常库64/64、9项发布门槛capability |
| Gateway key rotation DTO/ORM | 本机 Admin 当前树 + 正常服务 | exit `0`；3项service测试、26项相关测试、tsc/diff通过；default dry-run与正式transaction/audit均脱敏，Dream private env原子更新 |
| Product OAuth forwarding | 本机 Dream当前树 + 正常页面 | exit `0`；54项Product/SystemConfig回归；subscription/plans与Free renewal preview/execute返回200，无本地HS256 signer |
| Settings/MCP Luna stage | 本机 Dream `frontend` | exit `0`；101项相关测试、TypeScript、focused ESLint、diff通过；另11项聚焦测试枚举七个Settings入口与OAuth terminal-state policy |
| MCP replacement OAuth | 本机 Dream `backend` + 正常页面 | exit `0`；19项provider-free OAuth/credential/service测试；真实 consent/callback 已完成，reload 使用持久化凭据并返回 41 Tools / 25 Resources / 10 Prompts |
| 文件与真实模型边界 | 正常 Dream Chat、共享 workspace、Gateway | 两次文件上传、登录读取、未登录 `401`、hash/path/symlink 与 `.claude-tmp 0700` 通过；默认模型与 Luna 均因当前周期额度不足返回 `402`，没有 assistant 输出 |
| 正常备份隔离恢复演练 | 本机独占 PostgreSQL 18.1 / `55493` | 历史切换 exit `0`；真实物理备份54→63、8 capabilities、142 ACL、credential/allow/deny、重复apply、`35/1408/10`计数保持；回执SHA `716646a3bbdc4051742c9e82f570c004fb19892fc60a32591d84d890f5064f94`，副本已停止并删除；0063另以具名可删除数据库完整重放 |
| 正常数据库与运行边界只读复核 | 本机正常 `ink-memory:54329` | exit `0`；64 migration receipts、9/9 exact发布门槛capabilities、3个受限LOGIN/NOINHERIT角色、Dream NOLOGIN，4项denied privilege均false；Dream两个进程0个PG键、0条54329连接 |
| Markdown local-link checks | 两仓受影响文档 | exit `0`；最终同步3文件0 missing、Admin架构7文件67 links/0 missing、Dream总览2文件15 links/0 missing |

CI 的 Node 20 action deprecation annotation来自 GitHub runner把旧 action runtime强制到 Node 24；没有项目测试或构建失败。

## 8. 正常切换结果

私有 env/manifest 与备份均为 `0600`，v2 manifest 曾通过实际 Git worktree校验绑定精确 Admin/Dream release heads，并拒绝 commit mismatch、tracked修改及旧v1 manifest。相同物理备份先在独占 PostgreSQL 18.1 完成54→63、角色/ACL、凭据与allow/deny的apply/dry-run/repeat演练，随后本机命名正常数据库使用独立 `--apply --production-approval` 路径完成切换。

2026-09-17 当前只读状态：正常 `ink-memory:54329` 有64个migration receipt和9/9发布门槛 capability；`ink_auth`、`ink_admin_control`、`ink_dream_data` 为受限 `LOGIN NOINHERIT`，`ink_dream_no_db` 为 `NOLOGIN NOINHERIT`，均无superuser/createdb/createrole/replication/bypassRLS。Dream role无CONNECT；AUTH/CONTROL不能读取`chat_thread`或旧`identity.admin_subject_links`；DATA不能读取private JWK。修正后的AUTH/CONTROL明确具备独立Admin credential、Session、audit与RBAC所需最小权限。正常Admin、Dream Next、Dream Python分别监听`3000/5173/8765`并返回200。

执行器仍默认只预检，任何其他部署目标必须独立完成备份、精确目标身份、migration/capability、角色/ACL与allow/deny门禁；不能复用本机回执冒称已激活。

## 9. 真实业务验收状态

| 用户流程 | 技术验证 | 正常真实验收 |
| --- | --- | --- |
| Google登录、新旧主体关联、返回、退出、Session失效 | exact provider-sub adoption、callback、consent、Session/browser-session/refresh与返回及27项退出/并发合同通过 | **登录/关联/返回、当前Dream client真实退出、登录页回退和同主体SSO重入已通过；自然中央Session/handle TTL到期未等待** |
| Dream访问与Admin管理权限隔离 | DTO/RBAC/ACL隔离合同和独立subject-link模型通过 | **Dream历史可读；同一浏览器Admin入口仍为login，已通过** |
| Device批准/拒绝/pending/slow_down/过期/兑换/refresh/revoke | 实际create、pending、slow_down及4类负例通过 | **允许、拒绝、兑换、refresh rotation、旧refresh重放、重复兑换、独立主动revoke与真实access expiry已通过** |
| JWT签名/issuer/audience/expiry/kid/scope/revoke | scalar与真实Better Auth数组、错误resource/额外audience/签名/issuer/expiry/kid/scope deterministic contracts通过 | **真实设备JWT访问Dream及到期后401已通过；refresh family/revoke不伪装为既发JWT即时失效** |
| Run/Thread创建、加载、继续、取消、SSE、历史 | backend/provider-free suites通过；Gateway exact Runtime scopes已rotation | **历史读取、两条新Thread与用户消息持久化、MCP replacement已通过；两种模型均因额度返回402，assistant输出、继续、取消与SSE终态未通过** |
| 资源策略与LKG | 单元/集成合同通过 | **正常公开desired与运行中Observer快照只读对齐：revision 4、四项effective、effort、精确内存组合与新鲜心跳均通过；未修改desired或触发turn** |
| 文件上传/读取/授权/元数据失败恢复 | 路径/DTO/业务合同通过 | **两次上传、登录读取、未登录401、workspace hash/path/symlink与临时目录权限已通过；模型读取结果受额度阻塞，真实metadata故障注入未执行** |
| Admin不可用/超时/拒绝/capability缺失/unknown write | 故障合同通过 | **未执行正常服务故障注入** |
| 数据持久化及Admin后台可见性 | 正常数据库/服务已激活，OAuth catalog已持久化 | **两条Thread、用户消息和Gateway失败回执已正常持久化；独立Admin Session实现和正常ACL均已激活，公开登录由原权限500恢复为明确401；成功后台登录仍需有效Admin自身凭据** |
| Dream运行时无PostgreSQL访问 | 完整源码门禁通过 | **当前正常Next/Python进程0个PG键、0条54329连接，已通过；仍需正向业务流佐证持久化经Admin** |

真实验收使用已指定账户及现有业务实体，只走公开生产入口；本轮产生的 Run、Thread、Gateway request、Token settlement 和失败回执需保留并能在日常 Admin 查询。不得用隔离库、fake provider 或测试账号冒充。

## 10. 完成判定

| 交付项 | 判定 |
| --- | --- |
| 四项目基线 tag/Release | **已证明** |
| Admin/Dream 分支、PR、任务与协调记录 | **已证明** |
| 能力归属、数据库方案与 DTO/ORM 契约 | **已证明** |
| Google OAuth、Device Flow、接口、迁移、时序与交互文档 | **已证明源码/文档存在** |
| Admin 191 operations、Drizzle 64 migrations、9 capabilities | **已证明隔离、CI与正常数据库通过** |
| Dream 全生产数据库入口关闭 | **已证明静态、测试与当前正常进程运行边界通过** |
| Runtime/SSE/LKG/共享文件系统语义 | **LKG与共享文件系统已证明正常运行边界；Runtime/SSE状态机确定性回归通过，真实模型终态仍受402阻塞** |
| 正常数据库 migration/ACL/config/service 切换 | **本机命名正常目标已执行并只读复核；其他部署目标未宣称完成** |
| 真实 Google/Device/Run/Thread/文件/模型验收 | **部分执行：Google采用/登录/返回、Dream client退出/SSO重入、Device完整状态、MCP replacement、文件上传/授权读取/workspace边界及Thread消息持久化通过；模型输出/继续/取消/SSE受额度402阻塞，Admin登录运行路径与ACL已修复但缺有效独立Admin凭据，自然Session TTL到期未等待** |
| 整项任务完成 | **不成立；保持 active** |

剩余顺序为：取得有效Admin自身凭据后复核独立后台成功登录/退出/Session失效 → 由正常Dream账户补足当前周期 Token 额度 → 真实模型文件读取回复、Run/Thread/SSE继续与取消 → metadata故障恢复；自然Dream中央Session/handle TTL到期只在可控时间条件下补验。任何一步失败均区分应用缺陷、外部配置、账户条件与harness问题，不回退Dream直连数据库，也不把Admin与Dream业务用户合并。
