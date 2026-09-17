<!-- [Input] User-authorized AutoDL deployment, merged Admin/Dream commits, existing direct-host scripts, and task 01a05775-b5b2-7362-b388-fa23be380eab. -->
<!-- [Output] Deployment plan and append-only evidence for the 2026-09-17 unified auth/data release. -->
<!-- [Pos] Cross-project AutoDL release receipt; secrets and business payloads are excluded. -->
<!-- [Sync] 2026-09-17: record the activated Admin/Dream releases, public auth recovery, legacy Dream credential adoption, browser acceptance, and final pruning evidence. -->

# AutoDL 统一认证与数据接口发布回执

## Optimized Prompt

以合并后的 Admin `main` 与 Dream `develop` 精确 commit 发布统一认证和 DTO/ORM 数据接口版本。先核对远端主机、数据目录、当前链接、端口和公网映射；Admin 先发布，唯一执行 Drizzle 前向 migration，并验证 Better Auth、Admin 页面、数据库 capability 与 Dream 数据接口。Dream 后发布，只消费 Admin API，保留 Agent Runtime、SSE、线程工作区和共享文件系统。两个项目都先构建不可变 candidate，在隔离端口验证候选，再原子切换。切换或验证失败时仅在本轮内恢复仍存在的旧应用；所有本机和公网验收通过后删除旧 release 和临时链接，不保留长期回滚版本。不得打印或提交 SSH、OAuth、数据库及服务密钥。

保持不变：Admin/Dream 用户域不合并；Dream 无 PostgreSQL 凭据、SQL、ORM 或 migration；共享根目录、`.claude-tmp`、权限、符号链接边界、turn/resume/cancel 与资源策略语义不变。失败时停止下游发布，记录命令、退出码、候选与 current 指向，不删除数据库或共享业务数据。

验收：PR 已合并，两个本地默认分支 fast-forward 到远端；Admin migration/capability、本机 `6008` 与公网登录通过；Dream 候选 `16006/18765`、正式 `6006/8765`、公网 health、crawler、内置 Skills、默认 Plugin 与 Admin 依赖通过；远端只保留最终 current release。

## 初始证据

- 远端主机：`autodl-container-ylgygfuaq4-2c9ee25f`。
- 设备重启后 screen 与 `6006/6008/8765` 均未运行；release 链接与持久数据盘仍存在。
- 发布顺序：Admin → migration/capability → Dream → 跨服务公开入口。
- 部署前发现旧 AutoDL 脚本仍要求不存在的 local-core `0.1.9`；当前源码要求已发布 Runtime `0.1.10`。发布脚本改为安装并校验 npm `0.1.10`，不降级源码或复用远端 `0.1.4`。
- 第一次 Dream 构建在切换前被主动终止，因为运行配置仍使用旧产品域名。当前发布只从环境注入 SeetaCloud 6006/6008 HTTPS 映射；MCP Apps sandbox route 从 Dream origin 派生并依靠 opaque iframe origin 隔离，不再要求第三个公网域名。中止时 `current` 未切换，未删除持久数据。
- 第二次候选完成 Python SDK 0.2.145 与 Next 构建后，被旧发布断言拒绝：backend discovery 按既有生产合同把 npm wrapper 解析为 package-root `cli.js`，脚本却仍期待 wrapper 文件名。断言已与 backend Docker 门禁统一为 `cli.js` + `ink-claude-code-dream` 父目录；该次未创建 candidate、未切换 current。
- `524b408fb438-20260917142657` 已通过隔离冒烟并切换，随后暴露验证器缺口：旧 `resolve_default_deck_plugin_ref()` 已改为必须接收 Admin 返回的 installation DTO，而无用户委托身份的发布脚本仍空参调用；同时 shell 条件上下文吞掉了该非零状态。验证器现改为逐项校验持久 content-addressed plugin artifact store，并对全部门禁显式返回失败；默认 Deck 选择留给登录后的 reconcile 业务验收。
- 发布结果在实际执行后追加；本段不声明部署成功。

## 最终发布结果

| 项目 | 已激活 release | 代码 commit | 公开入口 |
| --- | --- | --- | --- |
| Admin | `/root/ink-autodl/admin/releases/88d4507faeff.20260917145247` | `88d4507faeff01f0a7be939f1f78a15d2eee810a` | `https://uu115767-uaq4-2c9ee25f.bjb2.seetacloud.com:8443` |
| Dream | `/root/ink-autodl/dream/releases/8adf3bee9fcb-20260917150112` | `8adf3bee9fcb343845c7cc02a1238a3c8b9065f9` | `https://u115767-uaq4-2c9ee25f.bjb2.seetacloud.com:8443` |

Admin 先完成 64/64 Drizzle migration，最新 journal 为 `0063_smiling_microbe`；随后恢复三个受限数据库角色、配置 OAuth browser/device/service client，并以真实 `client_credentials` 令牌验证受保护 capability。Dream 在该门禁通过后发布。两个项目的 `current` 均指向上表唯一 release，`previous`、`candidate` 均不存在，release 目录中没有保留旧应用版本；PostgreSQL、共享文件、workspace 和 artifact store 保留。

合并与 CI 证据：

- Admin [PR #22](https://github.com/glide-the/dream-im-platform/pull/22) 合入 `main`；Deterministic checks 与 Drizzle migration journal 均通过。
- Dream [PR #69](https://github.com/glide-the/im-dream/pull/69) 与 [PR #70](https://github.com/glide-the/im-dream/pull/70) 合入 `develop`；两次 `build-check` 均通过。Next 在 direct-host 环境会把 Route Handler 请求 URL 规范化为内部 loopback；修复仅在明确配置为 HTTP loopback 的内部代理模式接受任意 loopback 端口，外部 origin 仍要求精确公开 Origin，mutation 仍执行公开 Origin 与 CSRF 检查。

## 认证与身份兼容回执

恢复数据库中指定邮箱原先只有一条 active Dream canonical 用户和 bcrypt credential，不存在 Better Auth Dream subject/account/link，也不存在 Admin subject link。发布期 `auth:adopt-legacy-credential` 先 inspect 并固定源行 SHA-256，再 dry-run 得到 `action=create`，最后以 `--apply --production-approval` 在一个 Drizzle 事务中创建 Dream subject、credential account 与 subject link。回执为 `dream_subject_created=true`、`credential_account_created=true`、`admin_membership_created=false`、`legacy_rows_modified=0`；重复 dry-run 为 `already-complete`。这一步只让旧 Dream 密码进入 Admin 提供的 Dream 认证域，不修改 canonical 用户或业务外键，也不授予 Admin 管理身份。

独立 Admin operator 使用 Admin 专用恢复命令替换密码、撤销 21 个旧 Admin Session 并写入脱敏审计；公开 `/api/admin/auth/login` 返回 200，测试 Session logout 返回 200。Dream 身份在该事务中保持不变。密码、hash、Session cookie 和 token 均未写入本回执。

公开 Dream 密码登录的真实浏览器验收依次通过：Dream 原登录卡输入现有 Dream 凭据 → Admin consent 页面 → 单次“允许” → 返回 Dream `/story-workspace/chat` → `/auth/session` 200 且包含已认证用户 → `/auth/logout` 200 → 再查 Session 为 401。测试会话已退出，业务用户、正文和共享文件未清理或改写。

Google 只执行了不消耗真实账号授权的入口检查：Dream 公开表单 POST 到 Admin 后返回 Google `accounts.google.com`，`redirect_uri` 精确为 `https://uu115767-uaq4-2c9ee25f.bjb2.seetacloud.com:8443/api/auth/callback/google`。本次没有重复执行真实 Google 账号登录。

## 最终验证回执

| 命令或入口 | 工作目录 | 结果 |
| --- | --- | --- |
| `./deploy/autodl-ssh/deploy.sh verify` | Admin | exit 0；真实 service token 200、受保护 capability 200、本机端口/screen/公网映射通过 |
| `./deploy/autodl-ssh/deploy.sh verify` | Dream | exit 0；Next、MCP Apps build、crawler、内置 Skills、plugin artifact、Admin 依赖、screen 和公网映射通过 |
| Dream `/`、`/api/health`、`/auth/options` | AutoDL 公网 | 均为 200；未登录 `/auth/session` 为预期 401 |
| Chrome + Playwright 公开登录卡 smoke | `frontend` | exit 0；1 test、9 assertions；未发现 `Unable to check your session`、`BFF_ORIGIN_DENIED`、page error 或 request failure |
| 公开 Dream 密码登录、consent、callback、Session、logout | AutoDL 公网 | exit 0；Session 200，logout 200，退出后 401 |
| 当前 Dream 进程日志切片 | AutoDL | `ADMIN_SERVICE_AUTH_UNAVAILABLE=0`、`BFF_ORIGIN_DENIED=0`、resource snapshot write failure=0、confirmation reconciliation failure=0 |

当前进程仍周期性记录 `Notion scheduled sync failed safely: code=connector_sync_failed`。该错误由 Notion 后台 connector 的独立失败隔离产生，没有进入登录、Agent turn、Session 或本次 Admin 数据接口门禁；它不是本次公开认证发布的失败，但仍代表 Notion connector 在当前实例没有完成外部授权/同步验收。
