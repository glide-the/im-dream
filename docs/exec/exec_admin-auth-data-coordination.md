<!-- [Input] Actual Git/GitHub/tool receipts from the cross-project coordinator. -->
<!-- [Output] Durable baseline, task, evidence and unresolved dependency record. -->
<!-- [Pos] Execution evidence for stage_admin-auth-data-coordination.md; not an implementation completion claim. -->
<!-- [Sync] 2026-09-14: record successful immutable prereleases, branches and actual project task setup. -->

# Admin 认证与 Dream 数据访问迁移协调回执

## 当前结论

重构前基线发布和项目任务创建成功。两个实施任务正在运行，尚无完整迁移或业务验收结论。
计划见 [协调计划](../stage/stage_admin-auth-data-coordination.md)。

## 基线发布

| cwd | 实际命令 | exit | 关键输出 |
| --- | --- | ---: | --- |
| Dream 原仓库 | `git status --short` / `git rev-parse HEAD` / `git remote -v` | 0 | 仅 `?? repomix-output.xml`；HEAD `7d38715c`；`glide-the/im-dream` |
| Admin 原仓库 | 同上 | 0 | 工作区干净；HEAD `017f3acc`；`glide-the/dream-im-platform` |
| 两仓库，沙箱内 | `git ls-remote --tags origin` / `gh release list --limit 15` | 128 / 1 | SSH port 22 operation not permitted / API 网络失败；不是发布成功 |
| 两仓库，授权网络 | `git ls-remote --heads --tags origin` / `gh release list --limit 30` | 0 | 基线 SHA 在远端 develop/main；无既有 tag/release |
| Dream，授权操作 | `git tag -a v0.1.3-pre-admin-auth-data.20260914 7d38715c1a8f74cb5fb3dcb114320156eaf6b3e6 -m '本次重构前的基线版本: Admin authentication and data API migration'` / `git push origin refs/tags/v0.1.3-pre-admin-auth-data.20260914` | 0 | 远端 new tag |
| Dream | `gh release create v0.1.3-pre-admin-auth-data.20260914 --verify-tag --prerelease --title '本次重构前的基线版本 · Dream 0.1.3' --notes-file /private/tmp/ink-dream-baseline-release-20260914.md` | 0 | [Dream 基线 Release](https://github.com/glide-the/im-dream/releases/tag/v0.1.3-pre-admin-auth-data.20260914) |
| Admin，授权操作 | `git tag -a v0.1.0-pre-admin-auth-data.20260914 017f3acccc57991f0b3771c1c9bb9dd765255b07 -m '本次重构前的基线版本: Admin authentication and data API migration'` / `git push origin refs/tags/v0.1.0-pre-admin-auth-data.20260914` | 0 | 远端 new tag |
| Admin | `gh release create v0.1.0-pre-admin-auth-data.20260914 --verify-tag --prerelease --title '本次重构前的基线版本 · Admin 0.1.0' --notes-file /private/tmp/ink-admin-baseline-release-20260914.md` | 0 | [Admin 基线 Release](https://github.com/glide-the/dream-im-platform/releases/tag/v0.1.0-pre-admin-auth-data.20260914) |
| 两仓库 | `gh release view <tag> --json url,tagName,name,isDraft,isPrerelease` | 0 | 两者 isDraft=false / isPrerelease=true，标题明确为重构前基线 |
| Dream | `git ls-remote origin 'refs/tags/v0.1.3-pre-admin-auth-data.20260914*'` | 0 | annotated tag `1a03400f`，peeled SHA `7d38715c1a8f74cb5fb3dcb114320156eaf6b3e6` |
| Admin | `git ls-remote origin 'refs/tags/v0.1.0-pre-admin-auth-data.20260914*'` | 0 | annotated tag `d389ff23`，peeled SHA `017f3acccc57991f0b3771c1c9bb9dd765255b07` |

Release body 明确列出基线 SHA、计划重构范围和关联项目基线，未声称包含未提交修改或重构完成。

## 分支与真实任务

两次 `git branch <codex-branch> <baseline-SHA>` / `git show-ref --verify` exit 0，均在两个 Release 发布成功之后执行。
`create_thread` 创建 project/worktree 任务，随后 `list_threads` 返回真实 ID 和 active 状态：

- Admin：`01a0a03d-f058-7130-bfa9-71d2bb0bc1c9`，`/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`，`codex/admin-auth-data-provider`。
- Dream：`01a0a03e-02f7-7221-9118-8bf3f6a91cb3`，`/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`，`codex/dream-admin-auth-data-client`。
- 协调：`01a0a039-5eff-7ac1-90bd-2198f14766e7`，实际 `create_goal` 状态 active；原 Dream 仓库独立 `codex/auth-data-coordination` 分支。

任务分别收到项目职责、Prompt Architect 阶段规划、规范契约归属、Luna 验证边界和保持业务语义的完整指令，并交换了真实任务 ID/worktree。
create_thread 的 clientThreadId 仅为初始 setup 回执，不拿它当真实任务 ID。

## 官方资料核验

2026-09-14 已读取 [Google](https://better-auth.com/docs/authentication/google)、[Device Authorization](https://better-auth.com/docs/plugins/device-authorization)、[OAuth Provider](https://better-auth.com/docs/plugins/oauth-provider)、[JWT](https://better-auth.com/docs/plugins/jwt) 官方页面。
Google 使用内置 social provider；OAuth Device path 与 Session Device path 不同。
当前文档页面显示 1.7.4，但 Admin 基线未安装 Better Auth；实现任务必须核验选定安装版本和实际源码，不把最新示例直接当成旧版本接口。

## 未完成与必需条件

- 规范 API/DTO、数据库分离选择、设计评审、代码实现、完整入口关闭证据与技术验证尚未交付。
- 用户已授权现有账户 `dmeck@suoxya.com` 的真实业务验收，允许从公开生产入口发现已有实体和正常配置模型；凭据不进入本记录或任务消息。
- 没有执行真实用户写入、数据库迁移、服务重启；技术 fixture 尚未运行。
- 两个项目已通过协调消息报告实际 goal active；协调目标保持 active，不提前 complete。

## 本机正常服务与设计依赖

`lsof -nP -iTCP:3000 -iTCP:5173 -iTCP:8765 -sTCP:LISTEN` 只发现 node 在 3000 监听。
沙箱 curl 均 exit 7，随后授权网络逐入口核验：

| cwd | 命令 | 单条 exit / 输出 |
| --- | --- | --- |
| Dream 原仓库 | `curl --max-time 5 -sS -i http://127.0.0.1:8765/api/health` | 7，连接失败 |
| Dream 原仓库 | `curl --max-time 5 -sS -I http://127.0.0.1:3000/admin/login` | 0，HTTP 200 |
| Dream 原仓库 | `curl --max-time 5 -sS -I http://127.0.0.1:5173/` | 7，连接失败 |

组合 shell 回执 exit 7 来自最后一个命令；Admin 的 HTTP 200 仅证明现有入口可达，不证明新认证或数据库接口已实现。
实际配置只读脱敏核验显示 Dream Google 配置存在、Admin 未配置 Better Auth/Google；这不授权把 secret 写进项目文件。
目前没有启动或停止任何正常服务，也没有执行真实账户写入或模型调用。

Admin 已安装实际 Better Auth/OAuth Provider `1.7.4` 并报告首版规范路径；全量领域实现、schema/ACL、设备/refresh 原子性和 Gateway 委托仍未完成。
Dream 已形成 108 候选文件、835 SQL 片段与 159 事务候选清单，包含单独标识的显式导入/维护；数字是扫描候选，不能等同生产可达入口或已迁移数量。
协调已把长 turn 委托续期、handle 跨客户端绑定与并发/未知提交恢复列为设计修改要求，两个项目 goal 保持 active。

## Luna 协调文档验证

验证执行者为实际 `luna_test_runner` 子任务 `/root/bootstrap_docs_validation`，仅检查协调文档。
cwd `/Users/dmeck/project/ink-dream-memory`；`git diff --check` exit 0，无输出。
只读 Python 检查首次因 harness regex 转义错误 exit 1，修正 checker 后 exit 0，输出 `CHECKS PASS; failures=0`；不是产品错误，也没有跳过失败断言。
检查覆盖两份新增文件 Input/Output/Pos/Sync、基础结构、相对 Markdown 引用、folder inventory、两个本地 tag peeled SHA 与三个真实任务 ID。
验证前后 `git status --short` exit 0，用户 `repomix-output.xml` 保留；runner 没有修改源码或项目文档，未创建服务、数据库、浏览器或模型调用。
该回执只证明协调文档与本地基线引用通过技术检查；不证明重构实现、数据库分离或真实业务验收完成。
