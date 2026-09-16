<!-- [Input] Exact Admin/Dream heads, four published baseline releases, current contracts, CI receipts and private cutover preflight state. -->
<!-- [Output] Requirement-by-requirement delivery status that separates source proof, normal deployment and real business acceptance. -->
<!-- [Pos] Final coordinator audit; it is not a production-approval token and contains no credential or business正文. -->
<!-- [Sync] 2026-09-16: reconcile exact legacy Google adoption, successful real return and Better Auth audience compatibility repair. -->
<!-- [Sync] 2026-09-16: reconcile the audit with the applied normal cutover, live no-PostgreSQL proof, OAuth catalog and partial real auth/Device receipts. -->
<!-- [Sync] 2026-09-16: add exact Admin/Dream release binding and physical-backup isolated cutover rehearsal evidence. -->

# Admin 统一认证与数据服务最终交付审计

## 结论边界

源码实现、跨项目契约、隔离数据库合同和确定性构建已经完成并在当前分支复核。本机命名正常 `ink-memory` 已从 54 个 migration receipt 前向升级到 63 个，受限角色/ACL、私有配置、OAuth client/resource catalog 和正常 Admin/Dream 服务已经激活。Google Cloud 已保存本地与生产 Admin callback；精确旧 `provider_sub` 主体采用通过 release-only DTO/Service/Drizzle 事务完成，真实 Google callback、Admin consent和返回Dream成功，同一主体没有Admin membership。真实Better Auth双受众JWT暴露的`INVALID_TOKEN_RESOURCE`也已通过封闭受众规则修复并在浏览器复验。完整 Device approve/deny/exchange/refresh/revoke、退出/Session失效、Run/Thread/SSE、共享文件和真实模型验收仍未完成，本审计不能用于宣称整项任务完成。

实现快照与审查入口：

| 项目 | 分支 / HEAD | 审查入口 | 状态 |
| --- | --- | --- | --- |
| Admin | `codex/admin-auth-data-provider` / `8d67958759f3afdc5b17dbc219a8602a84ded76d` | [Draft PR #15](https://github.com/glide-the/dream-im-platform/pull/15) | 本地、远端分支与 PR head 一致；最新提交增加 DTO→Drizzle OAuth catalog provisioning |
| Dream | `codex/dream-admin-auth-data-client` / `960aeb1499201373f2441c9e3b4b3d4585f61f67` | [Draft PR #63](https://github.com/glide-the/im-dream/pull/63) | 本地、远端分支与 PR head 一致；前后端 CI 全绿；仅保留既存未跟踪 `.pnpm-store/` |

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

Admin Better Auth 1.7.4 是唯一应用认证中心；Google 使用 `socialProviders.google`。Admin 负责 callback、Account/User 关联、Session、OAuth Provider、RFC 8628、JWT/JWKS、refresh/revoke 和主体映射。Dream BFF 保存 opaque handle，Dream Resource Server 校验签名、算法、issuer、audience、时间声明、主体和适用 scope；Dream API 不接受 Google token、OIDC ID token或任意用户 ID header。

Google、Better Auth Session、service JWT、OAuth access/refresh token 与 OIDC ID token 已在契约中分开；同一产品身份不会自动取得 Admin RBAC。CLI/设备客户端是 public client，固定 client secret 不进入制品。Admin 正常库已通过 DTO/Drizzle provisioning 注册 Dream API resource、browser public client、device public client和两条resource link；重复 dry-run 全部为 `unchanged`。

公开 Device 请求已实际返回 `device_code/user_code/verification_uri/expires_in/interval`，首次轮询为 `authorization_pending`，过快复轮询为 `slow_down`；unknown client/resource、外部 `user_id` 和越权 scope 分别 fail closed。设备码和 Token 未进入回执。真实Google登录、Session/browser-session/refresh lineage与Dream返回已通过；完整用户批准/拒绝、兑换、refresh/revoke仍待执行。[认证数据 ER 与流程图](../../architecture/auth-identity-er-and-flows.md)明确 `identity.user`、Dream canonical user 和 Admin member 分离；本次精确采用创建Dream subject link而没有Admin link，同邮箱未用于自动合并或授权。

## 5. Dream 生产数据库关闭

当前 Dream 生产图不包含 PostgreSQL credential、driver、SQL、ORM、UOW、DDL、自动建表或 SQLite runtime fallback。`server.py` 不加载数据库 URL或创建 pool；历史数据库实现仅位于 `backend/tests/**` 的明确 fixture/harness。部署模板清空旧数据库变量并只投影 Admin base、issuer/resource、service identity 和 BFF cookie secret。

静态关闭门禁与完整 backend suite 已通过：`3527 passed, 24 skipped, 615 subtests passed`。本轮进一步在正常服务上验证：Dream Next 进程和 Python 进程均没有 `DATABASE_URL`/PostgreSQL/PG credential 环境键；两进程到正常 PostgreSQL `54329` 的实际 TCP 连接数均为 0；Admin、Dream 页面和 Dream health 分别在 `3000/5173/8765` 返回 `200`。该运行证据证明当前启动实例没有 Dream→PostgreSQL 旁路；完整用户持久化业务仍需登录后公开流程验收。

## 6. 保持的业务语义

- Runner、ThreadFactory、Service、EventBus、SSE、turn/resume/cancel 与 admission/lease 顺序保持在 Dream。
- 资源策略继续区分 `default`、Admin `desired`、Dream `effective`、revision 与 LKG；Agent turn 主路径不查询数据库或远程策略。
- 共享文件系统继续由 Dream 执行路径规范化、owner检查、符号链接/越界拒绝和失败恢复；文件字节不经过 Admin 数据接口。
- `CLAUDE_CODE_TMPDIR={AGENT_CWD}/{thread_id}/.claude-tmp`、真实 Thread workspace、`0700` 与精确 sandbox 放行范围不变。
- Runtime `0.1.10`、SDK `0.2.145`、Plugin CLI 与官方 Claude CLI 分离由生产 Docker build 验证。

## 7. 实现快照与审计提交自动化证据

| 命令/运行 | 工作目录或平台 | 结果 |
| --- | --- | --- |
| Admin [Test Suite 35080308352](https://github.com/glide-the/dream-im-platform/actions/runs/35080308352) | GitHub / Admin `894c8221` | exit `0`；50s，63/63 migrations，8 capabilities，repeat no-op |
| 同一 Admin deterministic job | GitHub / Admin `894c8221` | exit `0`；3m41s，13 config tests、274 files / 2074 tests passed，17 files / 36 tests skipped；ESLint、tsc、Next 16.1.6 build通过 |
| Admin auth/catalog focus + current build | 本机 Admin `8d679587` | exit `0`；Vitest 19/19、setup-env 3/3、env check、TypeScript、focused ESLint、Next production build通过；catalog repeat dry-run全部 `unchanged` |
| Dream [Frontend CI 35093209489](https://github.com/glide-the/im-dream/actions/runs/35093209489) | GitHub / Dream `960aeb14` | exit `0`；1m4s，frozen pnpm install与Next production build通过 |
| Dream [Backend CI 35093209484](https://github.com/glide-the/im-dream/actions/runs/35093209484) | GitHub / Dream `960aeb14` | exit `0`；14m52s，生产 Docker image dry-run通过 |
| Dream BFF/部署焦点 | 本机 Dream `960aeb14` | exit `0`；BFF boundary 7/7、Remote SSH env projection、`git diff --check`通过 |
| `.venv/bin/python -m pytest -q tests` | Dream `backend`，实现代码最终快照 | exit `0`；3527 passed、24 skipped、615 subtests passed |
| Dream OAuth audience与产品边界焦点 | Dream `backend`，当前未提交修复 | exit `0`；81项audience/JWKS合同与117项auth/product边界通过；真实浏览器不再显示`INVALID_TOKEN_RESOURCE` |
| 正常备份隔离恢复演练 | 本机独占 PostgreSQL 18.1 / `55493` | exit `0`；真实物理备份54→63、8 capabilities、142 ACL、credential/allow/deny、重复apply、`35/1408/10`计数保持；回执SHA `716646a3bbdc4051742c9e82f570c004fb19892fc60a32591d84d890f5064f94`，副本已停止并删除 |
| 正常数据库与运行边界只读复核 | 本机正常 `ink-memory:54329` | exit `0`；63 migration receipts、8/8 exact capabilities、3个受限LOGIN/NOINHERIT角色、Dream NOLOGIN，4项denied privilege均false；Dream两个进程0个PG键、0条54329连接 |
| Markdown local-link checks | 两仓受影响文档 | exit `0`；最终同步3文件0 missing、Admin架构7文件67 links/0 missing、Dream总览2文件15 links/0 missing |

CI 的 Node 20 action deprecation annotation来自 GitHub runner把旧 action runtime强制到 Node 24；没有项目测试或构建失败。

## 8. 正常切换结果

私有 env/manifest 与备份均为 `0600`，v2 manifest 曾通过实际 Git worktree校验绑定精确 Admin/Dream release heads，并拒绝 commit mismatch、tracked修改及旧v1 manifest。相同物理备份先在独占 PostgreSQL 18.1 完成54→63、角色/ACL、凭据与allow/deny的apply/dry-run/repeat演练，随后本机命名正常数据库使用独立 `--apply --production-approval` 路径完成切换。

2026-09-16 当前只读状态：正常 `ink-memory:54329` 有63个migration receipt和8/8发布门槛 capability；`ink_auth`、`ink_admin_control`、`ink_dream_data` 为受限 `LOGIN NOINHERIT`，`ink_dream_no_db` 为 `NOLOGIN NOINHERIT`，均无superuser/createdb/createrole/replication/bypassRLS。Dream role无CONNECT；AUTH/CONTROL不能读取`chat_thread`；DATA不能读取private JWK。正常Admin、Dream Next、Dream Python分别监听`3000/5173/8765`并返回200。

执行器仍默认只预检，任何其他部署目标必须独立完成备份、精确目标身份、migration/capability、角色/ACL与allow/deny门禁；不能复用本机回执冒称已激活。

## 9. 真实业务验收状态

| 用户流程 | 技术验证 | 正常真实验收 |
| --- | --- | --- |
| Google登录、新旧主体关联、返回、退出、Session失效 | exact provider-sub adoption、callback、consent、Session/browser-session/refresh与返回通过 | **登录/关联/返回已通过；退出和Session失效待执行** |
| Dream访问与Admin管理权限隔离 | DTO/RBAC/ACL隔离合同和独立subject-link模型通过 | **Dream历史可读；同一浏览器Admin入口仍为login，已通过** |
| Device批准/拒绝/pending/slow_down/过期/兑换/refresh/revoke | 实际create、pending、slow_down及4类负例通过 | **批准/拒绝/兑换/refresh/revoke待执行** |
| JWT签名/issuer/audience/expiry/kid/scope/revoke | scalar与真实Better Auth数组、错误resource/额外audience/签名/issuer/expiry/kid/scope deterministic contracts通过 | **真实登录JWT数组已验证；revoke待Device/退出流程** |
| Run/Thread创建、加载、继续、取消、SSE、历史 | backend/provider-free suites通过 | **未执行** |
| 资源策略与LKG | 单元/集成合同通过 | **未执行** |
| 文件上传/读取/授权/元数据失败恢复 | 路径/DTO/业务合同通过 | **未执行** |
| Admin不可用/超时/拒绝/capability缺失/unknown write | 故障合同通过 | **未执行正常服务故障注入** |
| 数据持久化及Admin后台可见性 | 正常数据库/服务已激活，OAuth catalog已持久化 | **用户Run/Thread/Gateway/settlement正向回执待登录** |
| Dream运行时无PostgreSQL访问 | 完整源码门禁通过 | **当前正常Next/Python进程0个PG键、0条54329连接，已通过；仍需正向业务流佐证持久化经Admin** |

真实验收使用已指定账户及现有业务实体，只走公开生产入口；本轮产生的 Run、Thread、Gateway request、Token settlement 和失败回执需保留并能在日常 Admin 查询。不得用隔离库、fake provider 或测试账号冒充。

## 10. 完成判定

| 交付项 | 判定 |
| --- | --- |
| 四项目基线 tag/Release | **已证明** |
| Admin/Dream 分支、PR、任务与协调记录 | **已证明** |
| 能力归属、数据库方案与 DTO/ORM 契约 | **已证明** |
| Google OAuth、Device Flow、接口、迁移、时序与交互文档 | **已证明源码/文档存在** |
| Admin 191 operations、Drizzle 63 migrations、8 capabilities | **已证明隔离、CI与正常数据库通过** |
| Dream 全生产数据库入口关闭 | **已证明静态、测试与当前正常进程运行边界通过** |
| Runtime/SSE/LKG/共享文件系统语义 | **已证明确定性回归通过** |
| 正常数据库 migration/ACL/config/service 切换 | **本机命名正常目标已执行并只读复核；其他部署目标未宣称完成** |
| 真实 Google/Device/Run/Thread/文件/模型验收 | **部分执行：Google采用/登录/返回/RBAC隔离和Device pending/slow-down/负例通过；其余未完成** |
| 整项任务完成 | **不成立；保持 active** |

剩余顺序为：完成真实模型消息的浏览器动作时确认 → Run/Thread/SSE继续/取消与Admin可见回执 → Device approve/deny/exchange/refresh/revoke → 文件流程与故障恢复 → 退出/Session失效。任何一步失败均区分应用缺陷、外部配置、账户条件与harness问题，不回退Dream直连数据库。
