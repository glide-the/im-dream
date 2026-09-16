<!-- [Input] Actual Dream public routes, Admin contract v0.1, existing harnesses and authorized real account. -->
<!-- [Output] Cross-project impact matrix and separate technical/real-business acceptance gates. -->
<!-- [Pos] Coordinator acceptance plan; test receipts belong in exec_admin-auth-data-coordination.md and project reports. -->
<!-- [Sync] 2026-09-14: assess complete flows before implementing or running cross-project acceptance. -->

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
当前正常 Admin 3000 可达，Dream 5173/8765 未启动；新认证与领域 capability 尚未发布，完整验收待实现。

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
