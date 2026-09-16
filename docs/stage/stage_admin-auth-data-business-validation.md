<!-- [Input] Actual Dream public routes, Admin contract v0.1, existing harnesses and authorized real account. -->
<!-- [Output] Cross-project impact matrix and separate technical/real-business acceptance gates. -->
<!-- [Pos] Coordinator acceptance plan; test receipts belong in exec_admin-auth-data-coordination.md and project reports. -->
<!-- [Sync] 2026-09-16: record runtime configuration projection, build evidence and the remaining normal-database capability gate. -->
<!-- [Sync] 2026-09-17: record real Codex stream diagnosis, Admin compatibility fix and the remaining allowance gate. -->
<!-- [Sync] 2026-09-17: record the real Device delegated-user plus rotated Dream service-key Gateway canary. -->
<!-- [Sync] 2026-09-17: close Deck detail empty/raw legacy Memory projection parity and record two-sided regression. -->
<!-- [Sync] 2026-09-17: record a normal-session public Deck list/detail read through the current Admin consumer. -->
<!-- [Sync] 2026-09-17: record normal-session Thread create/list/history/status, terminal SSE and idempotent stop with restricted-role persistence proof. -->
<!-- [Sync] 2026-09-17: record the pre-change identity-domain review and normal-session read-only DTO/BFF acceptance across migrated data domains. -->

# Admin 认证与 Dream 数据迁移业务验证计划

## 背景与问题

认证迁移同时影响 HTTP、SSE、WebSocket、Agent 工具、后台同步和持久化。
扫描候选包括 108 个文件、835 SQL 字符串片段和 159 事务线索；候选数量不表示可达生产入口或闭合数量。
原 `run-dream-cloned-production-e2e.mjs`、`run-dream-real-model-clone.mjs` 等 clone harness 不符合本轮真实业务协议，不能用其结果替代正常 Admin 可见的真实验收。

## 目标与边界

技术验证使用确定性、provider-free 与隔离 harness，执行交给 Luna；实现、迁移、破坏性验证和真实用户/模型由主任务处理。
真实验收使用本机正常 Dream、Admin、Gateway 与正常 PostgreSQL，已有账户 `dmeck@suoxya.com`，从公开接口选择已有 Deck 等实体和正常模型。
用户已授权该账户业务验收范围；凭据不进入任务消息、版本库、日志、报告或浏览器 URL。
保留本轮 Thread/Run/Gateway/结算回执，正常用户创建的新 Thread/Run 可以用于 continue/cancel，避免修改无关历史正文。
本轮 migration/backfill/破坏性执行仍仅限身份已核验的具名隔离数据库；正常数据库缺少新 capability 时不能以临时 DDL 绕过。

## 概念与规则

- 技术通过、隔离跨项目通过、真实 Google、真实业务、真实模型分别记录状态。
- API DTO 与 ORM entity 分离；DTO 显式投影 bigint/时间/null/页码，Admin 的 Repository/ORM 负责查询、权限、锁、事务与收据。
- 原 UOW 的 early return 不提交；多实体更新不可拆成无一致性 HTTP 操作。
- 未收到响应不证明 rollback；未知提交恢复必须复用原请求 ID，非幂等操作不得盲目换 ID 重试。
- 浏览器只有同源 BFF handle，Google/Session/ID token 不直接用于 Dream API；服务身份与用户委托分别校验。
- Agent 长 turn 使用 Admin 所有且绑定 subject/thread/run/scope/client 的委托能力或规范续期，不因短 token 到期丢失持久化。
- Runtime、SSE、EventBus、admission/lease、LKG 与共享 FS 边界保持原语义。

## Optimized Prompt: 完整影响评估与验收准备

You are the primary cross-project acceptance owner. Using verified baseline source and the canonical Admin contract, assess every actual Dream user and background flow before executing acceptance. Read public routers, AuthContext/BFF, Agent service/runtime, resource policy/sink, workspace file routes, Notion/MCP/Deck/Plugin/Story modules and existing validation scripts. Record each flow's modules, DTO/repository/permission impact, exact public production entry, success and failure/recovery criteria. Owner: coordinator for this matrix and real-user/model acceptance; Admin owns database/auth implementation and its canonical contract; Dream owns consuming DTO clients and product/runtime behavior; Luna owns deterministic and provider-free isolated execution. Keep plan changes limited to this file and affected folder inventories; no production schema/config/account mutation in this planning round. Distinguish schema/API/deployment capabilities, preserve stable business IDs and exact filesystem/lease/LKG semantics, and reject clone harnesses as real acceptance. Use authorized existing account through the normal service; discover existing entities and normal model selections through public APIs without exposing credentials or transcripts. Cover Google return/logout/mapping, RBAC isolation, Device/refresh/JWT, thread/run lifecycle and SSE, permissions, every migrated data domain, filesystem metadata recovery, Admin failure/idempotency and static plus runtime no-PG proof. Expected receipts include cwd/command/exit/assertions/artifacts and Admin-visible business identifiers. Run no migrations outside a proven named disposable database. If normal deployment lacks new capabilities, record the actual gate and continue unaffected technical work. Never assert full completion while a mandatory flow lacks evidence.

USER REQUIREMENT:
Re-test complete affected business flows after the cross-project migration, following DTO/ORM layering, normal real-business topology and isolated technical-test boundaries.

## 影响范围与验证矩阵

以下是待执行标准，全部状态初始为待实现/待验证；不是通过回执。
技术/隔离执行由 Luna 返回实际命令。真实模型调用选择正常 Admin catalog 模型，在 harness 中显式记录模型与调用次数，不新增产品配额。

| 用户流程 | 受影响模块与公开入口 | 数据与权限 / DTO-ORM 边界 | 验证方式 | 成功标准 | 失败与恢复路径 |
| --- | --- | --- | --- | --- | --- |
| 密码与 Google 登录、返回原页面 | AuthContext/BFF；Admin auth sign-in/social/callback；旧 auth.py/oauth.py 兼容退役 | 原 users/Google sub → 显式主体映射；独立 Session 与业务权限 | 技术/隔离 + 正常真实账户 + 真实 Google 单独记录 | 已有账户 PK/关联不重建；相对 return_to 恢复 | state/issuer/PKCE/redirect 校验失败不建 handle；同邮箱冲突不任意关联 |
| 退出、Session 过期、用户禁用 | BFF/handle/revoke/Admin principal | handle、OAuth grant 与管理员映射分别校验 | 技术/隔离；真实退出只影响本轮登录 | cookie 清除，grant/handle 按规范失效 | 明确已发 JWT 生效窗口和适用即时状态边界，失效要求登录 |
| Dream 与 Admin 权限隔离 | Dream principal；Admin Session/RBAC 管理入口 | 同一认证主体不等于管理员，实体权限独立 | 技术/隔离 + 正常账户 | Dream 可用、无显式管理 membership 则管理拒绝 | 不按相同邮箱或 client scope 提升 RBAC |
| Device 创建、批准、拒绝、过期 | Admin `/api/auth/device/code`、授权页、`/api/auth/oauth2/token` | public client，无固定 secret；resource/scopes/subject | 技术/隔离 + 正常设备授权 | 授权页显示 client/scope/resource，得到目标 OAuth access token | pending/slow_down/denied/expired/invalid_client，不返回 Session token |
| Device 重复与并发兑换 | Admin 插件与领域事务 | code 单次消费、poll 间隔、row lock/receipt | 隔离合同并发 | 一个成功消费，无重复 grant/副作用 | consumed 不复活，重试按原错误与 interval |
| Refresh/轮换/重放 | Admin OAuth、encrypted handle、Dream BFF | 绑定 client/resource/grant；每 handle 串行 | 技术/隔离 + 正常登录必要刷新 | 旧 token 转 used，新 token 原子建立 | expired/replayed/unknown response 按规范恢复或重新登录 |
| JWT/JWKS Resource Server | Dream 成熟 verifier；Admin JWKS | signature/algorithm/typ/issuer/audience/time/sub/scope | 确定性库测试与隔离 API | 正确目标 access token 接受，缓存复用 | 缺失/错误签名/issuer/aud/过期/未知 kid/ID token 拒绝；受限刷新不逐请求取 key |
| Thread 创建、加载、消息与历史 | [claude_agent.py](../../backend/routers/claude_agent.py) `/threads`、`/messages`、`chat-history` | owner；typed thread/message DTO，immutable envelope、final projection/keyset | 技术/隔离 + 正常账户公开入口 | 新 Thread/消息可加载，顺序与游标保持 | 他人实体拒绝，冲突 409；重试不重复消息 |
| turn/continue/stop/SSE 与工具确认 | `/api/claude-agent`、thread `/stream`、`/stop`、`tool-confirm` | Admin persist/run delegation；Dream service/EventBus/Runtime | 隔离 fake provider + 正常真实模型 | Runtime 仍在 Dream；继续/取消/历史可见，正常 Admin 请求结算可查 | 长 turn 凭据续期；错误/取消保存原状态，unknown persist 不发已提交成功事件 |
| Story Workflow preflight/create/retry/cancel/guidance | [story_workspace.py](../../backend/routers/story_workspace.py) workflow-preflights/workflow-runs/dream-runs | workspace/story/run/thread/token 组合事务与 CAS | 技术/隔离 + 正常已有 Deck 新 Run | 单次 launch、不重建已有实体，状态与原接口一致 | 重复消费/并发状态冲突保持原失败，不拆 run-thread 事务 |
| Story 索引与 episode 文件 | workflow-run dream-files/episodes/story-index/reconcile | Admin 关系与索引；Dream FS/Runtime 产物处理 | 技术/隔离 + 已有实体只读 | PK/关系、正文、artifact Run/version 匹配 | metadata 失败恢复不覆盖历史正文，过期 revision 明确冲突 |
| Deck/Voice 及版本/Plugin 绑定 | `/api/decks`、[deck_versions.py](../../backend/routers/deck_versions.py)、Deck service | owner、draft/version/revision、删除依赖同事务 | 技术/隔离；真实使用已有 Deck，不随意删除 | snapshot/refs 原子，原公开 DTO 与产品行为一致 | CAS 冲突、仍有运行依赖时拒绝删除 |
| Claude Plugin/Marketplace/runtime materialization | [claude_plugins.py](../../backend/routers/claude_plugins.py)、install/catalog/reconcile | Admin 元数据/lineage/locks；Dream packer/FS/Runtime | 技术/隔离，真实只选择已有已授权插件 | digest/receipt/install 关系保持；Runtime 不移入 Admin | revoked 不复活，未知安装结果按原 operation 恢复 |
| MCP server/auth/discovery/import/App 设置 | claude_mcp repository/service/runtime；Next MCP Apps adapter | credentials encrypted，exact revision CAS，owner，deny default apps | 技术/隔离；真实已配置 connector 可用时验收 | 现有配置与授权不丢，server-owned runtime snapshot | capability/secret/权限缺失 fail closed，禁止PG/CLI管理事实后备 |
| Notion connector/snapshot/选择/后台同步 | notion/store/credentials、mount/resource/定时入口 | connector owner/scope/已提交 snapshot；Admin credential repository | 技术/隔离；真实已有授权可用时执行 | snapshot 与 thread mount/选择保持，Dream 拉取执行留原模块 | 后台服务限定范围，不按任意 user_id 越权；失败不污染 snapshot |
| note/session/preferences/report/timeline/friendship | sessions/preferences/reports/pictures/friends/reflections | owned DTO，invite requester/receiver，batch 原事务 | 技术/隔离，真实已有数据读取及本轮允许操作 | 原范围过滤、显示、注册默认关系不重复 | 无权限/过期 invite/关系冲突明确失败 |
| Product/model catalog/Gateway 计费主体 | admin_product/admin_gateway、公开 Product/Gateway | canonical/平台投影、entitlement、价格快照；Admin token authority | 技术/隔离 + 正常模型调用/Admin查询 | 模型与 Token 结算保持原权限，主体映射稳定 | 余额/授权/模型禁用按原业务失败，不从客户端注入身份或模型能力 |
| 资源 policy/observer | resource_policy、resource_postgres_sink、agent_factory | Admin desired；Dream default/effective/revision/LKG；content-free observer DTO | 确定性/隔离 background | higher合法rev replace；同rev同值仅diagnostics，内存组合精确 | invalid/rollback/unavailable保持 LKG，背景错误不传播 turn，既有 lease 不变 |
| workspace 上传、读取、预览与下载 | [workspace.py](../../backend/routers/workspace.py) `/api/workspace/files*` | Admin thread/entity授权；Dream realpath/no-symlink/root/删除范围 | 技术/隔离 + 本轮正常 Thread 文件 | 同一授权路径，Markdown/图片/ZIP 可读，metadata 关联正常 | 越界/符号链接拒绝，metadata未知提交按原key恢复，不删除无关文件 |
| `.claude-tmp` 与 Workspace Mode | SDK spawn、workspace/sandbox/env composition | `{AGENT_CWD}/{thread_id}/.claude-tmp`，真实目录与 `0700` | focused 技术合同 + 真实 Runtime 可用时回执 | 关闭 Workspace 不启用 cwd/context/sidebar；精确 sandbox 放行 | symlink/outside/thread mismatch启动前拒绝；不放行整个tmp |
| Admin 不可用/超时/权限/能力/重复写 | 所有新 Admin 客户端与领域操作 | strict DTO + service/user delegation + atomic receipts | provider-free 隔离故障注入 | 明确失败、同键同值复用、同键异值409、并发不重复写 | timeout不假定rollback，无PostgreSQL后备路径 |
| schema/API/ACL 与无 PostgreSQL 生产路径 | capability/health/startup/background/tool/Runtime env/deploy | Admin Drizzle；受限schema/角色；Dream无DSN/driver/SQL路径 | 代码与调用链清单复查 + 隔离运行公开入口拦截 DB driver/network | 每实际入口映射具体DTO/Repository，正常运行没有PG连接或凭据注入 | 缺 capability/ACL fail closed；无记录/一次关键词扫描不证明关闭 |

## 验收证据与依赖状态

每条回执记录候选 commit、cwd、命令、exit、断言结果、数据身份/资源归属与限制；真实证据只保存本轮业务标识与脱敏聚合，不保存密码、Token 或用户正文。
静态候选需逐项标识生产可达、显式 importer/维护或非 DB 同名调用，不能把 false positive 数量包装为已迁移数量。
schema 分离需 catalog/ACL 和 Drizzle 前向 migration 实证；新 `dream.operation_receipts` 一张表不等于全部 Dream 数据分离。
真实回执必须在正常 Admin 可查询 Run/Thread/Gateway request/Token settlement，clone-only 结果不采纳。

2026-09-17 正常Dream公开Agent链已验证到托管Codex：credential按Admin broker规范刷新后，上游返回HTTP 200和合法Responses SSE body，但缺少`Content-Type`。旧Gateway在parser之前返回502并留下Admin可见`settlement_failed/usageUnknown`。Admin已实现仅限Codex adapter、body存在、类型头为空的兼容规则；其他Provider仍fail closed，当前完整Admin回归277 files/2097 tests、类型、lint与build通过。该正常失败请求预留75,006 Token，当时当前周期剩余24,994，不足以启动同样完整turn；系统没有人工改usage或释放未知用量预留的接口，本轮未改订阅、Allowance或账本。

同日追加小额真实Gateway canary：现有Dream用户Session通过公开RFC 8628 Device Flow批准public client，仅申请`messages:create`与Dream resource；无refresh的300秒用户token和已轮换的Dream canonical-subject service key同时通过Gateway，公开`/v1/messages`返回200，请求`req_b912a4968bbc464fb66bf4b656a7aa6d`记录11 input/5 output tokens。公开Product usage将其标记为`completed/settled`，reserved85/consumed16/released69；当前总额100,000、原未知请求仍预留75,006、已消费16、剩余24,978。该回执验证用户委托主体与服务client分离，并实测修复后的headerless Codex Responses路径；没有创建Admin Session。access token revoke返回400且无refresh token，文档按最长300秒自然失效记录，不虚报即时撤销。临时脚本/context server已删除/停止，未输出code、token、key或正文。模型产生的新消息、continue、运行中cancel、live SSE与Workflow Run仍待额度和既有Deck binding条件满足后执行，小额canary不能替代该业务旅程。

### 正常 Thread 创建、历史与终态控制回执（2026-09-17）

- 复用本机正常Dream Browser Session调用公开`GET /api/claude-agent/threads?limit=50`返回200，共16个Thread；仅读取ID、时间与消息角色元数据。五个历史Thread存在assistant消息，其中`e6fd4e39-ce5f-4887-b585-1f508933b60a`通过当前Admin DTO消费者读取6条`user/assistant`交替历史，未读取或记录正文。
- 对该历史终态Thread调用公开`GET .../stream`返回409 `Thread is not running`；调用公开`POST .../stop`返回200、`ok=true`、`stop_requested=false`。这验证终态SSE失败反馈和取消幂等性，不冒充运行中断流或真实运行中取消。
- 同一历史Thread以`limit=2`遍历三页，三页各返回一组`user/assistant`，共6个不同message ID；前两页`has_more=true`且带cursor，末页`has_more=false/next_cursor=null`，跨页无重复。携带首屏`latest_message_id`重读返回200、空messages、`unchanged=true`；非法cursor返回400，未知Thread的messages与stop均返回404。只记录ID、角色、时间和状态，没有读取正文。
- 通过公开`POST /api/claude-agent/threads`创建并保留无模型验收Thread `1326f102-0db5-41e6-b8ec-8d0ef874e6cc`，返回200；随后公开列表包含该ID，消息读取200且为0条，状态读取200、`running=false/lifecycle=not_found`，重复stop返回200且`stop_requested=false`。没有发送用户消息、启动Runtime、调用模型、删除Thread或改变历史正文。
- Admin worktree使用正常`.env.local`中的受限`DREAM_DATA_DATABASE_URL`执行参数化只读查询，exit0，`public.chat_thread`精确返回1行、ID匹配且标题匹配；命令未打印DSN、用户ID、Token或正文。这是Admin持久化补充证据，业务写入本身只经过公开Dream生产入口。
- 刷新正常订阅公开页面后仍显示总额100,000、已消费16、当前可用24,978，和已知75,006未知用量预留一致。没有修改Allowance、账本或模型上限。
- 现有唯一Deck `86512acd-abc9-44d1-af72-ea5a60af225d`的公开plugin-binding读取返回200、revision0、binding null；因此本轮没有修改既有Deck配置来伪造Workflow Run。真实Preflight/Run create/read/cancel仍是独立待验收项。
- 使用合法格式但不存在的ID调用公开Run GET、Run cancel与Preflight GET均返回404。Run GET/cancel按既有`WORKFLOW_RUN_ROUTE_ERRORS`产品兼容映射返回`AGENT_EXECUTION_FAILED`，Preflight返回`WORKFLOW_PERMISSION_DENIED`；当前源码和回归测试明确冻结该映射，因此不是运行版本漂移。该负向回执证明公开身份/capability/DTO路径启用，但不能替代成功Run。
2026-09-16 初始启动检查确认 `3000`、`5173`、`8765` 与正常 `54329` 均未监听；随后本轮拥有的 Admin `pnpm dev` 启动 `3000` 与正常内嵌 PostgreSQL `54329`，用于只读状态探测。Docker daemon 未运行，但 Compose `config --quiet` 不依赖 daemon 且已用于配置渲染。Admin 主仓库配置将 `/Users/dmeck/project/ink-admin-memory/.ink-memory/postgres` 定义为正常数据目录。监听于 `51534` 的数据库是此前具名隔离 migration harness，不能用于真实验收，也不属于本轮清理范围。

### 真实业务执行概念与影响简报（2026-09-16）

- **业务对象**：通过已授权账户的公开 Dream 页面/API 读取其已有 Deck、Story Workspace 与 Thread 候选；只为本轮创建新的 Thread/Run/消息和共享文件产物，已有正文、订阅、余额、权限与历史记录保持不变。
- **执行链**：浏览器登录与会话由 Admin Better Auth 提供；Dream BFF 仅保存 opaque handle。Dream backend 执行 Runtime、SSE、文件操作和业务编排，通过 strict Pydantic DTO 调用 Admin；Admin Zod DTO、Service 与 typed Drizzle Repository 完成权限、锁、事务和 PostgreSQL 持久化。
- **文件边界**：真实文件仍写入规范化后的共享 workspace，数据库只保存授权后的元数据与业务关系；`.claude-tmp` 保持在线程真实目录内且权限为 `0700`，禁止符号链接和越界路径。
- **变更影响**：正常数据库只进行普通用户流程产生的业务写入。本轮不运行 migration、backfill、DDL 或破坏性清理；若正常库缺少当前 capability，公开服务必须 fail closed，并把缺少的 migration/capability 作为真实验收部署门禁记录。
- **回执范围**：保留本轮 Admin 可查询的 Thread/Run、Gateway request、Token settlement 与文件元数据标识；报告仅记录 ID、状态和脱敏计数，不保存口令、Token、Provider secret 或用户正文。
- **失败恢复**：Admin 不可用、超时、权限拒绝、capability 缺失或 unknown commit 均不得回退 Dream PostgreSQL；幂等写复用原 receipt/request ID，非幂等写不盲目重试。浏览器、backend 或 Runtime 失败时仅停止本轮启动的进程，保留正常数据回执供复核。

工作树运行配置从现有本机配置派生，但必须删除 Dream 的 `DATABASE_URL` 和旧本地认证 authority，仅注入 Admin base URL、issuer/resource、服务身份与正常 workspace 路径。主仓库旧 `backend/.env` 仍含 PostgreSQL 凭据，不能直接传给重构后的 Dream 进程；本轮将以无 PostgreSQL 环境启动并用运行时网络证据复核。

## 运行配置闭环修复规划（2026-09-16）

### Optimized Prompt:

You are the cross-project runtime-configuration owner. Close the discovered gap between the implemented Admin Better Auth/Dream DTO services and the checked-in environment setup contract. Evidence: the committed Admin application now starts through Webpack, but the normal `.env.local` predates unified authentication; public auth/JWKS/capability routes therefore return structured `AUTH_NOT_CONFIGURED`, and the normal database ledger is read-only verified at 0053 while code requires 0054–0062. Update Admin configuration allowlists, examples, render/validation logic and deployment templates so every server-only authentication/data role, BFF service registration, issuer/resource, Google provider, token encryption, device client and delegation policy key is explicit, validated and never printed. Update Dream frontend/backend examples and startup documentation so the same service ID/secret, issuer/resource, BFF callback/cookie and Admin base URL are represented without a PostgreSQL credential. Preserve Admin-only SQL/ORM/transaction ownership, Better Auth as sole authority, Dream Runtime/SSE/shared-filesystem behavior, existing database data and all user secrets. Do not run normal-database migrations, ACL changes, backfill or account adoption in this subtask. Missing Google credentials, limited-role DSNs, gateway binding or physical capability must fail closed with a named error. Validate configuration generation in a disposable directory, run TypeScript/lint/build-focused checks, restart only the owned Admin process, and verify that compile-time 500 is gone while undeployed schema/config remains a truthful 503. Record exact commands and redacted results; never place passwords, tokens, DSNs or OAuth secrets in logs, commits or reports.

USER REQUIREMENT:
Continue the Admin unified authentication/database API and Dream consumer migration with DTO/ORM layering, production-safe configuration and verifiable business acceptance.

### 范围、依赖与验收

| 项目/责任 | 修改与依赖 | 保持不变 | 验收 |
| --- | --- | --- | --- |
| Admin | `.env` allowlist/render/check、示例、部署模板、启动文档；依赖现有 auth/data config parser 与 0054–0062 capability | 不自动迁移、不生成 Google secret、不回显服务 credential，不把 DTO/事务移回 Dream | 临时目录 setup/check；缺配置有具体错误；正常启动进入结构化边界 |
| Dream | frontend/backend 示例及启动说明；依赖 Admin 注册的 client/origin/callback/resource | 无 `DATABASE_URL`、无本地 Session/Token authority；Runtime/SSE/FS 不变 | 配置键成对、secret 仅服务端、静态 no-PG 与 build/typecheck |
| 协调 | 记录正常库 ledger、当前端口/进程和真实验收 gate | 不把隔离测试冒充真实业务 | normal schema/config 缺失保持 pending，已通过技术证据独立列出 |

正常流程为 Admin 读取三个显式数据库角色 DSN、构造 Better Auth/OAuth/JWKS、验证 Dream service 与 callback，再由 Dream BFF 获取 opaque handle、backend 用同一服务身份调用 strict DTO API。配置缺失、URL/origin 不匹配、credential 不一致或 schema capability 缺失时，在任何用户业务写入前返回结构化 503；不会回退 Dream PostgreSQL，也不会以默认用户 ID、固定 secret 或测试环境标签绕过。

### 运行配置闭环实际回执（2026-09-16）

- Admin `pnpm test:config` exit `0`：Node 配置合同 `9/9`，Remote SSH env 投影与 AutoDL topology 均通过；覆盖 mode `0600`、外部配置缺失 fail closed、service secret 保留、三个 distinct database role、Dream resource/callback 同源与错误 origin 拒绝。
- Admin 使用临时、无真实 secret 的 env 执行本地和 Remote SSH `docker compose ... config --quiet`，两项 exit `0`；没有启动容器。`pnpm exec eslint scripts/setup-env.mjs scripts/setup-env.test.mjs`、`pnpm exec tsc --noEmit` 与 `pnpm build` 均 exit `0`，Next.js `16.1.6` Webpack 构建完成。
- Dream `deploy/remote-ssh/test-env-projection.sh` 与 `deploy/autodl-ssh/test-topology.sh` exit `0`；FastAPI/Next 获得同一注册 service ID/secret、exact Admin `/api/auth` issuer、Dream `/api` resource 与 `/auth/callback`，BFF cookie secret 独立，投影中无 PostgreSQL 配置。
- Dream 本地和 Remote SSH Compose 使用临时 env 执行 `config --quiet` 均 exit `0`；根/Remote backend 对遗留 DB env 写入空 tombstone，本机/Docker preflight 发现非空 `DATABASE_URL` 时拒绝启动。临时 `backend/.env`、`frontend/.env.local` 与渲染 env 已删除。
- Dream shell syntax、local/docker dry-run preflight、frontend `pnpm exec tsc --noEmit` 与 `pnpm run build` 均 exit `0`；Next.js `16.1.6` Webpack 构建列出实际 BFF/auth/device/token routes。首次把部署命令误从 `frontend/` 执行导致路径不存在 exit `127`，修正 cwd 后同组命令 exit `0`；该失败属于命令 harness，不是产品失败。
- 正常 Admin 服务通过 Webpack 后 `/admin` 可返回页面，认证/bootstrap/JWKS/capability 在旧主仓库配置下返回结构化 `503`，不再是编译 `500`。只读 migration ledger 为 applied `54` / target `63`，最新 `0053_rare_lenny_balinger`，`0054`–`0062` 共九项 pending。本轮没有在正常数据库运行 migration、ACL、backfill 或写入验收。

上述回执证明配置和部署代码可生成一致的 DTO/ORM 边界，不能替代真实 Google、正常账户、Device Flow、Run/Thread 或真实模型验收。正常部署仍需由运维提供 Google credentials、三个受限角色 DSN、Gateway binding、业务 policy JSON，并在允许的发布窗口完成 Admin Drizzle `0054`–`0062` 与 ACL 后才能继续公开业务写入。

## 发布顺序与回滚

Admin expand/API/认证 → Dream兼容消费 → 隔离 backfill/validate → 评审正常部署所需条件 → contract。
不在当前计划阶段迁移正常 PostgreSQL；不可用环境记录具体缺口并继续不依赖该环境的技术验证。
没有完整必需回执时 goal 保持 active；任何真实 Google/业务/模型未执行都单独说明。

## 认证边界确定性回归规划（2026-09-15）

### Optimized Prompt:

You are the bounded deterministic authentication regression runner. Validate the frozen Admin Better Auth 1.7.4 composition and Dream same-origin BFF without editing code or starting services. In Admin729f run exactly the thirteen `app/lib/auth/*.test.ts` files covering ES256 access token/JWKS claims, service identity, subject adoption, password, configuration, browser transaction/session, redirect, capability and delegation boundaries. In Dream ef6e frontend run exactly the five `_auth` API test files plus browserSession.test.ts, covering state/PKCE/issuer/callback, opaque handle cookie, CSRF/origin, refresh serialization, logout/session expiry, proxy/runtime credential selection and explicit legacy410 routes. Reuse installed dependencies; do not download, access network, database, Google, real account or provider. Preserve all concurrent dirty work. Return exact commands, cwd, exit code, test/file counts, failures and skipped coverage in separate new receipts. A deterministic pass does not count as real Google, Device Flow public exchange, normal business or full build acceptance.

USER REQUIREMENT:
继续完成Admin统一认证和Dream消费接入；每项必须有可核验回执，真实与隔离验收分开。

本轮保持不变：Admin是唯一认证/Token authority；Dream BFF不保存Google/Session authority；Google token、ID token和任意user header不进入Dream业务API；Admin管理权限与Dream产品权限分离。失败时保留原测试输出，不改预期掩盖错误。

## 确定性认证回归实际结果

首次Luna命令均未收集测试：Admin因sandbox无权写worktree `node_modules/.vite-temp` exit1，Dream因frontend未安装Vitest exit254；两项作为harness失败保留。修正只改变执行器：Admin使用`/private/tmp` Vite cache并保留原setup/alias，实际13文件75/75 exit0；Dream测试本身使用`node:test`，通过已安装tsx ESM loader执行，Luna实际5文件40/40、skip0 exit0。Root先行单独运行未重复的`retired-auth.test.ts`实际13/13、skip0 exit0。合计不能写作一次128项门禁；三个通过回执分别保留。

这些结果覆盖确定性的Admin token/subject/service/session/config/delegation/password边界及Dream PKCE/state/issuer/opaque handle/CSRF/refresh/logout/proxy/legacy410。未连接真实Google、RFC8628 token endpoint、正常本机服务或真实账户，不能据此标记真实认证验收完成。

## Deck detail legacy Memory兼容回执（2026-09-17）

Admin `DeckVoiceRepository`已停止在读取时解析或规范化`memory_workspace_config`，严格DTO按原字节携带nullable/raw text；Dream既有`voice_projection._parse_voice_row`保持唯一产品兼容语义：empty text保留、合法JSON解析、非法非空JSON映射为null。该读取无Dream数据库fallback、无read retry、无写入修复，也没有改变Deck/Voice DTO schema或operation capability。

Admin聚焦2 files/18 tests、完整provider-free 278 files/2106 tests、TypeScript、定向ESLint和production build均exit0；Dream公开Deck detail provider-free路由37 tests exit0。文档5 files相对链接0 missing，两个worktree diff check通过。该回执关闭已知empty-Memory兼容差异；真实账户Deck读取仍归入完整正常业务旅程，不由provider-free测试代替。

同日正常公开读取复用现有Dream Browser Session：`GET /api/decks`返回200和1个既有Deck，`GET /api/decks/86512acd-abc9-44d1-af72-ea5a60af225d`返回200、相同外层ID、5个Voice，五项Memory均投影为产品object。该读取只走Dream BFF/API→Admin DTO路径，没有数据库直连、写入、模型调用或正文输出。真实行不包含empty text，因此该canary与55项producer/consumer确定性兼容测试分别证明正常部署路径和边界值，不能互相替代。

## 用户业务域复核与迁移数据只读回执（2026-09-17）

- 业务修改前先复核认证设计和实现：Admin Better Auth/OAuth Provider 是 Authorization Server；Dream browser/device 是 public client；Dream server 是 confidential client；Dream user 是 user token 的 delegated subject/resource owner；Admin operator 只存在于独立 `admin_users/admin_sessions/RBAC` 域。`client_credentials` 只标识 Dream server，不把每个 Dream user 注册成 client。相同邮箱不复制或合并密码、Session、角色与管理权限。
- 聚焦边界验证：Admin login/guard/service identity/OAuth catalog 7 files、35 tests；Dream strict Pydantic request auth/service token 109 tests；Dream Next BFF 23 tests，全部 exit0。源码与测试没有发现需要修改的认证业务偏差，因此本轮没有为增加改动量重写登录实现。
- 复用当前正常 Dream Browser Session，通过同源公开入口读取18组数据，全部HTTP 200：个人资料、偏好、Session、图片、报告、好友请求/关系、Product context/plans/usage/models、Gateway models、Plugin installations/marketplace、MCP capability/servers、Connector与Notion capability。仅记录顶层字段和数量，没有保存正文、prompt、文件内容、Token、secret、DSN或私有文件名。
- Browser向`/api/me`主动注入伪造`Authorization`、私有service header和`X-User-Id`后仍返回正常Session主体的公开DTO；BFF没有转发调用方控制的身份头。该检查证明Browser只消费HttpOnly handle，user/service bearer均由服务端边界生成。
- Dream迁移读取域的provider-free回归8 files、198 tests全部通过。前端第一次用`node --test`执行Playwright文件因extensionless import失败，第二次用`tsx --test`因在Node runner中加载Playwright test失败；改用仓库规定的Playwright runner后暴露2个旧测试预期：绝对API URL和Browser Bearer。生产代码已经正确使用同源Cookie/CSRF，所以只修正测试和目录合同；最终5 files、33/33 tests、exit0。
- Luna在最终未提交树只读复跑：同一Playwright 33/33、TypeScript、完整backend 3535 passed/24 skipped/615 subtests、lint 0 errors/17既有warnings、Next production build、PostgreSQL运行路径边界6/6、AutoDL topology与Remote DTO/BFF projection均exit0；未访问数据库、浏览器、账户、网络或secret。
- 本回执没有发起模型turn、Run写入、外部Provider discovery、订阅/Deck/Plugin/MCP/Notion配置变化或数据库直连。Product models返回空列表而Gateway models返回9项；当前Product context没有entitlement，严格DTO与现有合同测试均通过，因此不把该差异擅自改成产品缺陷。独立Admin管理登录已在后续Session TTL配置回执中通过；完整模型turn、Workflow成功Run和自然Dream中央Session/handle TTL仍保持单独门禁。
