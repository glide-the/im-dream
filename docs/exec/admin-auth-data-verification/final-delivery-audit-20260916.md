<!-- [Input] Exact Admin/Dream heads, four published baseline releases, current contracts, CI receipts and private cutover preflight state. -->
<!-- [Output] Requirement-by-requirement delivery status that separates source proof, normal deployment and real business acceptance. -->
<!-- [Pos] Final coordinator audit; it is not a production-approval token and contains no credential or business正文. -->
<!-- [Sync] 2026-09-16: capture source completion and the remaining separately approved normal cutover/acceptance gates. -->

# Admin 统一认证与数据服务最终交付审计

## 结论边界

源码实现、跨项目契约、隔离数据库合同和确定性构建已经完成并在当前分支复核。正常 `ink-memory` 的 `0054–0062`、受限角色/ACL、私有配置激活、正常服务启动，以及真实 Google、Device Flow、Run/Thread、共享文件和模型验收尚未执行。本审计不能用于宣称整项任务完成。

实现快照与审查入口：

| 项目 | 分支 / HEAD | 审查入口 | 状态 |
| --- | --- | --- | --- |
| Admin | `codex/admin-auth-data-provider` / 实现快照 `f7a182ff56a3b47fec23362d1825c43597b7c21d` | [Draft PR #15](https://github.com/glide-the/dream-im-platform/pull/15) | 本地与远端一致，PR `CLEAN` |
| Dream | `codex/dream-admin-auth-data-client` / 实现快照 `dfd380210ccac52b8320b13be0eb63cc9d64f7c1` | [Draft PR #63](https://github.com/glide-the/im-dream/pull/63) | 后续提交仅增加或校正最终审计文档；精确审查 HEAD 与检查结果以 PR 为准，仅保留既存未跟踪 `.pnpm-store/` |

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

Google、Better Auth Session、service JWT、OAuth access/refresh token 与 OIDC ID token 已在契约中分开；同一产品身份不会自动取得 Admin RBAC。CLI/设备客户端是 public client，固定 client secret 不进入制品。源码和 provider-free 错误状态验证已完成，真实 Google 登录与真实 Device Flow 尚未执行。

## 5. Dream 生产数据库关闭

当前 Dream 生产图不包含 PostgreSQL credential、driver、SQL、ORM、UOW、DDL、自动建表或 SQLite runtime fallback。`server.py` 不加载数据库 URL或创建 pool；历史数据库实现仅位于 `backend/tests/**` 的明确 fixture/harness。部署模板清空旧数据库变量并只投影 Admin base、issuer/resource、service identity 和 BFF cookie secret。

静态关闭门禁与完整 backend suite 已通过：`3527 passed, 24 skipped, 615 subtests passed`。此结果证明源码调用图，不代替正常运行时网络证据；运行时最终证据必须在正常 Admin/Dream/Gateway 启动后观察公开入口和连接边界。

## 6. 保持的业务语义

- Runner、ThreadFactory、Service、EventBus、SSE、turn/resume/cancel 与 admission/lease 顺序保持在 Dream。
- 资源策略继续区分 `default`、Admin `desired`、Dream `effective`、revision 与 LKG；Agent turn 主路径不查询数据库或远程策略。
- 共享文件系统继续由 Dream 执行路径规范化、owner检查、符号链接/越界拒绝和失败恢复；文件字节不经过 Admin 数据接口。
- `CLAUDE_CODE_TMPDIR={AGENT_CWD}/{thread_id}/.claude-tmp`、真实 Thread workspace、`0700` 与精确 sandbox 放行范围不变。
- Runtime `0.1.10`、SDK `0.2.145`、Plugin CLI 与官方 Claude CLI 分离由生产 Docker build 验证。

## 7. 实现快照与审计提交自动化证据

| 命令/运行 | 工作目录或平台 | 结果 |
| --- | --- | --- |
| Admin [Test Suite 35075819619](https://github.com/glide-the/dream-im-platform/actions/runs/35075819619) | GitHub / Admin `f7a182f` | exit `0`；63/63 migrations，8 capabilities，repeat no-op |
| 同一 Admin deterministic job | GitHub / Admin `f7a182f` | exit `0`；274 files / 2074 tests passed，17 files / 36 tests skipped；ESLint、tsc、Next 16.1.6 build通过 |
| Dream [Frontend CI 35077514688](https://github.com/glide-the/im-dream/actions/runs/35077514688) | GitHub / 首个审计提交 `f5a56432` | exit `0`；1m2s，Next 16.1.6 compile、TypeScript、3/3 static pages |
| Dream [Backend CI 35077514712](https://github.com/glide-the/im-dream/actions/runs/35077514712) | GitHub / 首个审计提交 `f5a56432` | exit `0`；5m6s，生产 Docker build、Runtime 0.1.10、SDK 0.2.145、Plugin CLI gate通过 |
| `.venv/bin/python -m pytest -q tests` | Dream `backend`，实现代码最终快照 | exit `0`；3527 passed、24 skipped、615 subtests passed |
| Markdown local-link checks | 两仓受影响文档 | exit `0`；最终同步3文件0 missing、Admin架构7文件67 links/0 missing、Dream总览2文件15 links/0 missing |

CI 的 Node 20 action deprecation annotation来自 GitHub runner把旧 action runtime强制到 Node 24；没有项目测试或构建失败。

## 8. 正常切换候选

私有候选目录和 env/manifest 均为 `0600`。候选通过私有回执绑定 Admin 与 Dream 精确审查 HEAD，并在纯文档提交后刷新 Dream 绑定；状态为 `prepared-not-applied`，停机备份完整性已验证。预检快照记录正常库为 54/63 migrations、AUTH/DATA/CONTROL/Dream角色未创建。正常 `3000`、`5173`、`8765`、`54329` 当前均未监听。

执行器默认只预检；实际提交必须同时显式提供 `--apply --production-approval`。本审计未运行 migration、role创建、`ALTER OWNER`、`GRANT/REVOKE`、配置激活或服务启动。

## 9. 真实业务验收状态

| 用户流程 | 技术验证 | 正常真实验收 |
| --- | --- | --- |
| Google登录、新旧主体关联、返回、退出、Session失效 | provider-free contracts/build通过 | **未执行** |
| Dream访问与Admin管理权限隔离 | DTO/RBAC/ACL隔离合同通过 | **未执行** |
| Device批准/拒绝/pending/slow_down/过期/兑换/refresh/revoke | deterministic contracts通过 | **未执行** |
| JWT签名/issuer/audience/expiry/kid/scope/revoke | deterministic contracts通过 | **未执行** |
| Run/Thread创建、加载、继续、取消、SSE、历史 | backend/provider-free suites通过 | **未执行** |
| 资源策略与LKG | 单元/集成合同通过 | **未执行** |
| 文件上传/读取/授权/元数据失败恢复 | 路径/DTO/业务合同通过 | **未执行** |
| Admin不可用/超时/拒绝/capability缺失/unknown write | 故障合同通过 | **未执行正常服务故障注入** |
| 数据持久化及Admin后台可见性 | 隔离PostgreSQL通过 | **未执行正常数据库** |
| Dream运行时无PostgreSQL访问 | 完整源码门禁通过 | **待正常服务网络/credential运行证据** |

真实验收使用已指定账户及现有业务实体，只走公开生产入口；本轮产生的 Run、Thread、Gateway request、Token settlement 和失败回执需保留并能在日常 Admin 查询。不得用隔离库、fake provider 或测试账号冒充。

## 10. 完成判定

| 交付项 | 判定 |
| --- | --- |
| 四项目基线 tag/Release | **已证明** |
| Admin/Dream 分支、PR、任务与协调记录 | **已证明** |
| 能力归属、数据库方案与 DTO/ORM 契约 | **已证明** |
| Google OAuth、Device Flow、接口、迁移、时序与交互文档 | **已证明源码/文档存在** |
| Admin 191 operations、Drizzle 63 migrations、8 capabilities | **已证明隔离与CI通过** |
| Dream 全生产数据库源码入口关闭 | **已证明静态与测试通过** |
| Runtime/SSE/LKG/共享文件系统语义 | **已证明确定性回归通过** |
| 正常数据库 migration/ACL/config/service 切换 | **未执行，需独立批准** |
| 真实 Google/Device/Run/Thread/文件/模型验收 | **未执行** |
| 整项任务完成 | **不成立；保持 active** |

下一阶段只能在正常数据库与ACL独立批准后执行。若批准，顺序固定为备份复核 → `0054–0062` → 角色/ACL与allow/deny probes → 私有配置激活 → Admin/Dream/Gateway启动 → 公开入口真实验收 → Admin可见回执复核；任一步失败即停止后续阶段并保留证据。
