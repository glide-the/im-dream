<!-- [Input] User-authorized AutoDL target, merged Admin/Dream heads, and direct-host deployment scripts. -->
<!-- [Output] Sanitized command and release evidence for the 2026-09-18 deployment. -->
<!-- [Pos] Cross-project AutoDL release receipt; credentials and business payloads are excluded. -->
<!-- [Sync] 2026-09-18: record fixture-gate repair, Admin-first release, Dream release, public verification, and pruning. -->

# AutoDL 发布回执（2026-09-18）

## Optimized Prompt

将已合并的 Admin `main` 与 Dream `develop` 发布到用户指定的新 AutoDL 实例。公网 origin 只从 AutoDL 注入的 `AutoDLService6006URL` 与 `AutoDLService6008URL` 读取并投影，不使用旧实例或产品域名。先发布 Admin：构建不可变 candidate、16008 冒烟、执行 Admin Drizzle 前向 migration 与 OAuth catalog 协调、原子切换、真实 service-token/capability 和公网验证。再发布 Dream：构建 Python/Next candidate、16006/18765 冒烟、原子切换 6006/8765，并验证 Admin 依赖、公开 health、crawler、Skills 与 plugin artifact。成功后只保留当前应用 release；PostgreSQL、workspace、artifact 和共享文件保持。

同时更新发布测试，使 provider-free projector fixture 不读取 operator `platform.env`；更新中英文 README，把 AutoDL 启动与产品使用放在最前，把恢复步骤移到独立文档。不得记录 SSH、OAuth、数据库或服务 secret。

## 初始状态与设计修正

设备重启后没有 `6006/6008/8765` listener；旧 `current` release 与持久目录存在。AutoDL profile 提供了当前实例的 6006/6008 HTTPS 映射，两端 gitignored `platform.env` 已重新投影。

Admin 与 Dream 的 `test-topology.sh` 原先传入合成 origin 后仍加载 operator `platform.env`，实例切换会覆盖 fixture，导致门禁在真实发布前失败。修复仅让 fixture 显式选择 `/dev/null` 作为 platform file；正常 `prepare-env.sh` 与 deploy 仍读取 operator 配置。

- Admin [PR #25](https://github.com/glide-the/dream-im-platform/pull/25) 合入 `main`；Drizzle migration journal 和 Deterministic checks 均通过。
- Dream [PR #74](https://github.com/glide-the/im-dream/pull/74) 合入 `develop`；仓库未配置该 PR 的远端 checks，本机 `test-topology.sh` 通过后合并。

## 激活结果

| 项目 | Commit | 远端 release | 结果 |
| --- | --- | --- | --- |
| Admin | `3e7a04596088e0f9430467fc3307da26d830fe8c` | `/root/ink-autodl/admin/releases/3e7a04596088.20260918043804` | current；唯一保留 release |
| Dream | `6408059ec215e861d8bc7505379b10882340eb05` | `/root/ink-autodl/dream/releases/6408059ec215-20260918044134` | current + qualified；唯一保留 release |

Admin migration 为 64/64 current，latest `0063_smiling_microbe`。OAuth catalog 将 browser/service client 与三项 resource link 更新到当前 Dream resource，并删除旧实例 resource link。真实 confidential service token 为 200，受保护 capability 为 200。

Dream candidate 通过 16006/18765；正式 listener 为 Next 6006、FastAPI 8765。Admin 6008 与 PostgreSQL 54329 同时运行。两个 screen supervisor 均 detached；旧 dead screen socket 不属于当前进程，不影响 listener。

## 公网与本机验收

| 检查 | 结果 |
| --- | --- |
| Admin `./deploy/autodl-ssh/deploy.sh deploy` | exit 0；candidate、migration、OAuth catalog、service token、capability、本机与公网门禁通过 |
| Dream `./deploy/autodl-ssh/deploy.sh deploy` | exit 0；candidate、Next/FastAPI、Admin 依赖、crawler、Skills、plugin artifact、本机与公网门禁通过 |
| Dream WebUI-6006 `/` | HTTP 200 `text/html` |
| Dream WebUI-6006 `/api/health` | HTTP 200 `application/json`；`status=ok` |
| Dream WebUI-6006 `/auth/options` | HTTP 200 `application/json` |
| Admin WebUI-6008 `/admin/login` | HTTP 200 `text/html` |
| Chrome + project Playwright public auth smoke | exit 0；1 test、9 assertions；原登录卡、Google/Login 入口与 `/auth/options` 200；未登录 `/auth/session` 为预期 401；无 `Unable to check your session`、`BFF_ORIGIN_DENIED`、page error 或 request failure |
| release 清单 | Admin 与 Dream 各只保留上表一个 release；没有长期 `previous`/`candidate` |

浏览器测试使用本机 Chrome 与仓库 `@playwright/test`，没有输入账号、点击 Google、批准权限或写入业务数据；临时 spec 与测试输出已清理。本次仍未执行真实 Google 账号授权、真实模型 turn 或写入业务数据，因此本回执只声明技术发布与公开入口通过。真实业务验收仍须使用正常 Dream/Admin/Gateway/PostgreSQL 与用户指定账户，不能用本次 health/capability 结果代替。
