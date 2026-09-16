<!-- [Input] Actual Git/GitHub/tool receipts from the cross-project coordinator. -->
<!-- [Output] Durable baseline, task, evidence and unresolved dependency record. -->
<!-- [Pos] Execution evidence for stage_admin-auth-data-coordination.md; not an implementation completion claim. -->
<!-- [Sync] 2026-09-15: retain launch75 first failures,974 continuation/308 recovery/19 preservation and active goals. -->

# Admin 认证与 Dream 数据访问迁移协调回执

## 当前结论

重构前基线发布和项目任务创建成功。两个实施任务正在运行，尚无完整迁移或业务验收结论。
计划见 [协调计划](../stage/stage_admin-auth-data-coordination.md)。
原始脱敏验证记录已保存为项目文件，见 [证据索引](admin-auth-data-verification/.folder.md)。私有fixture配置没有进入项目目录。

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

## 用户追加 DTO/ORM 约束

用户要求数据库迁为接口时遵从 DTO/ORM 设计。协调已向两个真实项目任务传达业务 DTO/ORM 分层与显式映射要求：Admin 使用严格 Zod DTO、领域服务、类型化 Repository/Drizzle ORM，Dream 使用统一客户端与 Pydantic DTO 校验。
具体 DTO、权限、原事务、幂等和 capability 必须逐操作落地；当前设计中的 operation 输入说明仍需进一步补齐，不能以远程数据库函数或泛型 JSON 代替契约。

## 追加 Runtime / Python SDK 发布回执

已先读取两仓库 AGENTS、根目录合同、README/实际发布规范与 workflow 触发条件。
Runtime 当前 HEAD `d9c16304330b393c86e650926b191c0cfeaf0bf2`，版本 `0.1.9`，远端 main 精确匹配；`AGENTS.md`、`docs/design/.folder.md` 的既有未提交改动未进入 tag。
SDK 当前 HEAD `d6b87f14549c01f921c664fe525ba986b4ac8d88`，版本 `0.2.145`，远端 main 精确匹配，工作区干净；原不可变 source tag `v0.2.145` 指向 `00c45c69c4781567d3a2651b9d85495d425081a4`，没有移动。
两仓库 `Agent.md` 缺失，Runtime `CLAUDE.md` 也缺失；读取实际存在的发布合同，未伪造缺失文件。两仓库没有本轮 tag/release 自动 npm/PyPI 发包入口，未执行 workflow dispatch 或制品上传。

| cwd | 实际命令 | exit / 关键输出 |
| --- | --- | --- |
| `/Users/dmeck/project/ink-claude-code-dream` | `git tag -a v0.1.9-pre-admin-auth-data.20260914 d9c16304330b393c86e650926b191c0cfeaf0bf2 -m '本次重构前的基线版本: Admin authentication and data API migration'` / `git push origin refs/tags/v0.1.9-pre-admin-auth-data.20260914` | 0，new tag |
| 同上 | `gh release create v0.1.9-pre-admin-auth-data.20260914 --verify-tag --prerelease --title '本次重构前的基线版本 · Runtime 0.1.9' --notes-file /private/tmp/ink-runtime-baseline-release-20260914.md` | 0，[Runtime 基线 Release](https://github.com/glide-the/ink-claude-code-dream/releases/tag/v0.1.9-pre-admin-auth-data.20260914) |
| 同上 | `gh release view v0.1.9-pre-admin-auth-data.20260914 --json url,tagName,name,isDraft,isPrerelease` / `git ls-remote origin 'refs/tags/v0.1.9-pre-admin-auth-data.20260914*'` | 0，isDraft=false/isPrerelease=true；tag `969b89f3`、peeled SHA `d9c16304330b393c86e650926b191c0cfeaf0bf2` |
| `/Users/dmeck/project/ink-claude-dream-agent-sdk-python` | `git tag -a v0.2.145-pre-admin-auth-data.20260914 d6b87f14549c01f921c664fe525ba986b4ac8d88 -m '本次重构前的基线版本: Admin authentication and data API migration'` / `git push origin refs/tags/v0.2.145-pre-admin-auth-data.20260914` | 0，new tag |
| 同上 | `gh release create v0.2.145-pre-admin-auth-data.20260914 --verify-tag --prerelease --title '本次重构前的基线版本 · Python SDK 0.2.145' --notes-file /private/tmp/ink-sdk-baseline-release-20260914.md` | 0，[Python SDK 基线 Release](https://github.com/glide-the/ink-claude-dream-agent-sdk-python/releases/tag/v0.2.145-pre-admin-auth-data.20260914) |
| 同上 | `gh release view v0.2.145-pre-admin-auth-data.20260914 --json url,tagName,name,isDraft,isPrerelease` / `git ls-remote origin 'refs/tags/v0.2.145-pre-admin-auth-data.20260914*'` | 0，isDraft=false/isPrerelease=true；tag `342c050f`、peeled SHA `d6b87f14549c01f921c664fe525ba986b4ac8d88` |

两份 Release 均注明重构前基线、package version 与源码 tag 的区分、commit、范围和另外三仓库关联基线；不宣称新的 registry 制品或重构完成。
发布后 Runtime 原两份改动仍在，SDK 工作区仍干净；只有 Git tag/release 新增，没有 stage/commit/源码/版本修改。

## Luna 第二轮协调文档验证

新增业务影响矩阵、DTO/ORM 约束和 Runtime/SDK 基线后，复用 `/root/bootstrap_docs_validation` 执行第二轮，只读项目状态与文档。
cwd `/Users/dmeck/project/ink-dream-memory`；`git status --short`、`git diff --check` 均 exit 0。
实际 checker 在执行前写入 `/private/tmp/ink-auth-bootstrap-validation/check-round2.py`；首次执行 exit 1，原因是 harness 猜测的两个仓库路径不存在。只读发现实际 Runtime/SDK 路径后修正 checker，未调整断言或项目文件。
最终实际命令 `python3 /private/tmp/ink-auth-bootstrap-validation/check-round2.py` exit 0，输出 `CHECKS PASS; failures=0`。
检查覆盖三份协调/业务矩阵文档头、相对引用、folder inventory、凭据字面量缺失、四个基线 peeled SHA、SDK 原 `v0.2.145` 不变以及四仓库用户改动保留。
完整命令和 stdout 保存在 `/private/tmp/ink-auth-bootstrap-validation/receipt.md`；没有执行源码测试、数据库、迁移、网络、浏览器、服务、部署或真实业务验收，没有产生需清理的项目资源。

## 实施设计评审状态

Admin 任务报告已恢复 Better Auth password signin/signup，并以 bcrypt/Admin scrypt 兼容既有账户；Google 不再新增邮箱验证门槛。0054 仍是未发布、未应用的 candidate，已修正 schema 创建、snapshot 和真实 capability ledger 描述符；本记录不是数据库 replay 回执。
Admin 首批配置/Token 测试 15 项通过，Dream 首批统一客户端/JWT 边界测试 44 项通过，均由各任务 Luna 执行；原始项目验证回执由实施任务交付，尚不代表领域生产入口已经替换。
仍待核验：旧主体显式映射、真实 DTO/ORM 领域 API、schema/ACL 分离、长 turn 委托、Gateway 身份、全部 Dream 数据入口语义关闭和完整技术/真实业务验证。

## 主任务隔离迁移准备与基线重放

cwd `/Users/dmeck/project/ink-dream-memory`；`initdb --version` / `pg_ctl --version` exit 0，显示18.1。
初次 `python3 /private/tmp/ink-auth-migration-validation/prepare.py` exit 1；诊断 `initdb ...` exit 1，实际错误为 libpq 目录没有 postgres server程序。这是harness工具前置失败，不是 migration 或业务缺陷。
只读发现 Admin 已安装 `@embedded-postgres/darwin-arm64@18.1.0-beta.16` 完整native runtime后修正harness，最终同一prepare命令 exit 0。
本轮隔离库 `ink_auth_data_codex_test_792494523a17`，回环端口51534，数据目录 `/private/tmp/ink-auth-data-migration-20260914-792494523a17/postgres`；current_database/current_user/address/port/data_directory逐项匹配。
54项SQL字节与已提交基线017f3acc精确一致，复制的历史journal停在0053，不包含正在修改的0054 candidate。

`python3 /private/tmp/ink-auth-migration-validation/replay-baseline.py` exit 0；它在cwd `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory` 调用 `node scripts/migrate-provider-managed-accounts.mjs`，child exit 0。
Provider preflight、expand/dry-run/apply/contract和最终check全部走原有runner；随机测试credential只存在0600私有配置。
关键输出：`appliedCount=54,targetCount=54,availableCount=54,pendingTags=[]`，latest0053；catalog断言identity尚不存在且canonical users表存在。
完整脱敏输出：`/private/tmp/ink-auth-migration-validation/baseline-replay-receipt.json`；历史SHA：`/private/tmp/ink-auth-migration-validation/baseline-history-sha256.json`；目标身份：`/private/tmp/ink-auth-migration-validation/prepare-receipt.json`。
没有迁移正常数据库、没有执行真实账户或模型业务。新0054、既有业务schema分离/ACL、旧用户adoption/并发/partial-drift仍待后续验证；本轮独立集群暂保留供这些阶段使用，结束时只清理此归属明确的集群。首次失败的临时目录也只清理本轮创建项。

## 0054 首轮真实隔离失败与回滚

Admin提供的冻结候选SQL SHA256 `2dd4cf10f42d985ccbaa3ec2c413b70264b01963ee7942d39127709eb91f59c0` 已精确匹配；source/snapshot/descriptor固定后执行 `python3 /private/tmp/ink-auth-migration-validation/replay-candidate.py`。
两个harness前置失败分别为inet::text带`/32`与重用candidate history时误读baseline journal，均在写candidate之前失败；修正为host(inet_server_addr())和读取独立baseline_history，没有降低身份/历史断言。
随后正常 child `node packages/db/dist/migrate.js` exit 1，PostgreSQL `42830`：oauthClient被clientId外键引用时，所需unique index尚未创建。此项是实际DDL建约束顺序缺陷，已交Admin唯一migration owner修复未发布/未应用候选，历史0000..0053不变。
回滚只读核验 exit 0：ledger仍54、identity_absent=true、dream_absent=true、auth_capability_absent=true，没有candidate部分提交。
实际输出 `/private/tmp/ink-auth-migration-validation/candidate-0054-receipt.json`；回滚证明 `/private/tmp/ink-auth-migration-validation/candidate-0054-failure-rollback-proof.json`。尚未通过新候选replay，不将静态schema测试替代实际迁移。

## 主任务 Thread/message 实施与首轮验证

计划见 [Thread/message领域计划](../stage/stage_admin-chat-thread-domain.md)。主任务在Admin实施task worktree新增chatThreadDto/Repository/Service及定向测试，通用handler/receipt/registry/delegation由Admin任务接入。
14个具体操作覆盖Thread create/get/list/search/delete/bind/voice/title/session和message persist/list/page/process/latest。每操作strict Request/Response DTO，owner从Admin验证principal/delegation派生；message insert+touch与通用receipt同事务，不移动Runtime/公开产品投影。
ORM bigint采用读::text、参数化::bigint，不将canonical ID经Number；cursor保留PG微秒ISO，tuple和NULL tail保留原keyset索引行为。
Luna首轮cwd `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`：vitest exit1因`.vite-temp`写权限，测试未执行；tsc exit2发现自有nullable静态类型问题；focused eslint exit0。已显式补nullable投影并请求仅失败vitest/tsc重跑；不改Wire schema或断言。
首轮完整命令回执 `/private/tmp/ink-auth-thread-validation/receipt.md`。生产消费替换和ORM运行合同尚未验证，不声称Thread数据迁移完成。

## 0054 修复后的隔离通过回执

Admin唯一owner只将两个既有unique index移至FK创建前；未发布候选source/snapshot/descriptor定义不变，旧0000..0053未编辑。重新冻结SQL SHA256 `7f15a2abea185c506ddee69ea639d237a69d98f427eae215122038c7c5a3bf24`。
cwd `/Users/dmeck/project/ink-dream-memory`；实际命令 `python3 /private/tmp/ink-auth-migration-validation/replay-candidate-fixed.py` exit0。
child cwd729f Admin，普通升级/重复/并发使用 `node packages/db/dist/migrate.js`；fresh全历史使用 `node scripts/migrate-provider-managed-accounts.mjs`，全部成功子调用exit0。
18张表/189字段的schema、类型、notNull与snapshot/descriptor精确一致；命名索引/FK/unique/check存在，ledger=55且candidate hash只1条，schema capability version1/hash `1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3` 精确匹配。
验证旧54prefix升级、重复执行不重复收据、两个并发migrator单次提交、空库0000..0054正常orchestrator重放。
partial-drift隔离库预置未知identity schema后runner按预期exit1；断言ledger仍54、dream schema不存在、新capability不存在，未掩盖漂移或部分提交。
raw命令/输出 `/private/tmp/ink-auth-migration-validation/candidate-0054-fixed-receipt.json`；catalog证明 `/private/tmp/ink-auth-migration-validation/candidate-0054-fixed-catalog-proof.json`。
该结果不证明旧用户映射/ACL/全部业务schema分离、OAuth完整业务或真实模型验收，正常PG仍未修改。

## Thread/message focused rerun

Luna cwd729f Admin；`pnpm exec vitest run app/lib/dream/chatThreadDto.test.ts --configLoader runner --cache false --reporter default` exit0，1file/11tests passed；`pnpm exec tsc --noEmit --incremental false` exit0。
loader/cache/reporter调整仅用于避开harness受限写目录，生产Vitest配置与业务断言未修改。先前focused ESLint exit0，此轮无新风险不重复运行。
原始回执 `/private/tmp/ink-auth-thread-validation/rerun-receipt.md`。Admin任务已接通14操作handler/registry，长turn/receipt绑定、真实ORM运行和Dream adapter集成仍待完成。


## 用户要求的原目录→任务 worktree 同步（2026-09-14）

Admin原main新增ca681ce9e3199ac67180d891bab9aea671424c34；9个pricing-sync/UI/docs/E2E文件与worktree认证实现不相交，实际`git merge --ff-only ca681ce9e3199ac67180d891bab9aea671424c34` exit0并保留该commit身份。Dream原目录本轮基线后的20个文档文件同步到ef6e，`docs/exec/.folder.md`两处新增索引/同步记录三方合并保留双方全部条目，目标独有实现不变。原未跟踪repomix导出在检查期间被移除，未将其恢复。

Luna实际执行`python3 /private/tmp/ink-worktree-sync-20260914-validate.py`，cwd原Dream，exit0：149项byte/preservation检查、两边Markdown库存与本地链接、JSON解析、冻结0054/0055以及两目标`git diff --check`通过。原目录没有被同步操作暂存、提交或清理。后置回执/计划追加随后逐字节镜像到Dream目标。参见[原始验证回执](admin-auth-data-verification/worktree-sync-validation.md)、[hash审计](admin-auth-data-verification/worktree-sync-receipt.json)与[本轮计划](../stage/stage_worktree-sync_20260914.md)。整体任务仍待全部生产迁移与真实业务验收。


## 0055冻结隔离replay与公开Thread合同推进

0055 primary命令`python3 /private/tmp/ink-auth-migration-validation/replay-candidate-0055.py` cwd729f exit0；16columns、exactcap/ledger56、upgrade/repeat/concurrent/fresh/partialdriftrollback通过，creation SQLNULL缺口需后续0056前向修复，未改冻结0055。详见[raw receipt](admin-auth-data-verification/candidate-0055-receipt.json)与[catalog/缺口](admin-auth-data-verification/candidate-0055-catalog-proof.json)。

ThreadRoute503真实失败为服务误引用0032旧cap摘要，原0033早已前向更新同名v1，owned服务严格引用已发布0033摘要并保留exactgate。后续invalid-input correlation失败确认为harness漏真实client必发X-Request-Id，补header而不改预期。Luna`python3 /private/tmp/ink-auth-thread-validation/run-contract.py` cwd729f exit0、59路由assertions，owner/CAS/消息重放/并发收据审计/final/process/microsecond/NULL技术验证通过，后续补全14operation覆盖待fresh结果。参见[实际通过](admin-auth-data-verification/thread-public-contract-protocol-fix.md)和前序原始失败回执；正常库/Google/model业务仍未执行。


字段数量校正：0055/0056 runtime_delegations真实catalog与descriptor为16列（原10+新增6），raw JSON proof各自明确columns16。0055脚本旧stdout文字和早期协调消息误写17，原raw回执保留；验收断言逐字段比较真实集合，并未以错误数量改预期。后续说明以16为准，不重跑已通过检查。

## 0056、受限角色与完整 Thread 接口技术回执

0056 在本轮明确命名、端口和 data_directory 已核验的隔离 PostgreSQL 中 upgrade、repeat、两次并发、全新 replay 和 partial-schema 失败回滚均通过，ledger57、唯一0056记录及精确 capability 已验证。54–56冻结SQL未改；runtime_delegations实际16列。ACL runner 默认dry-run、apply、repeat退出0，140条声明式权限操作；16次实际角色访问尝试符合允许/拒绝预期，Dream CONNECT 与数据库/schema/table/function权限全部为false。受控注册函数的真实成功/失败业务验证另设阶段，不能把catalog EXECUTE检查当成成功注册。

Luna真实执行公共 Thread/message 所有14个operation、93条路由断言，通过普通隔离连接和受限AUTH/DATA连接两轮验证。受限轮的owner URL仅在harness核验目标身份和只读audit count，未设置为生产AUTH/DATA环境变量；业务路由使用受限连接。所有原始失败回执保留，并分别记录schema digest修复与harness correlation header修复。具体命令、cwd、exit和输出见本目录verification索引。此结果是隔离技术验证；完整Dream生产数据域关闭、真实Google和本机正常账户/模型验收仍未完成。


## 冻结58、注册adoption与Editor/Deck技术验证（2026-09-15）

0057/58 在已命名本轮隔离库通过升级、重复、两个并发migrator、全新Provider-aware orchestrator replay及两类partial rollback；ledger59，delegation18列/Editor7列与capability精确匹配。3合法purpose、6 SQL23514拒绝和仅绑定Editor grant的cascade通过。54–58冻结SQL没有变更。初次后续psql标量harness失败与修正范围单列记录，不重跑已通过迁移。

主任务 `node --import tsx /private/tmp/ink-auth-migration-validation/registration-adoption-validation.mts` cwd729f退出0：37条实际断言验证受限Auth公开注册/登录、受控canonical registration、显式manifest+共同密码证明的旧canonical/Admin/Google source关联及重复/冲突整事务回滚。source函数为provider-free，不是Google登录验收；原PK/hash/provider_sub/history关系保留。

主任务 `python3 /private/tmp/ink-auth-migration-validation/run-editor-contract.py` cwd729f退出0，原生产8个Session/Editor operations、103断言通过。AUTH/DATA实际受限roles，owner URL仅harness身份/只读receipt audit及本轮自有grant/session expiry-corrupt故障注入；purpose隔离、Session owner、NULL/微秒、并发单receipt/audit、加密原token回收、过期原renew回执不恢复新授权、撤销和删除cascade通过。

Deck19候选DTO/Service/typed Repository已实现；实际Python源模型/canonical/snapshot/hash/diff3PASS、28focusedPASS、定向lint0、完整`pnpm exec tsc --noEmit --pretty false --incremental false`退出0。原literal/enum空白接受差异与harness发现/tsbuildinfo写失败保留；公共Route/受限数据库合同及Dream生产消费尚待接线验证。纯序列化helper后续扩展的confirmation guard另设阶段，不能把上述旧PASS当作扩展后的验收。

新增raw文件与解释均在[verification库存](admin-auth-data-verification/.folder.md)。所有结果为隔离技术验证；全Dream生产DB访问关闭、物理业务schema/ACL正式rollout、真实Google、正常本机账户与模型验收仍未执行。四基线发布和worktree同步已核验，任务/goal保持active。


## 0059 与 Deck 19 项最终隔离回执（2026-09-15）

0059升级/重复/并发/全新/漂移rollback、旧版本关系保持和lossless canonical证明通过；原append-only UPDATE55000与mismatched INSERT23514分别核验，正常数据库未变更。Deck19operation/246公开Route断言、完整无缓存types与定向lint退出0；纯codec39 focused及新增confirmation源对照1PASS，stored guard后的Thread14/93实际受限回归通过。原失败/修复范围、fresh隔离身份与raw命令详见[verification库存](admin-auth-data-verification/.folder.md)。

Workflow context、raw user-turn与确认接口正在准备完整FK隔离fixture；refs/runtime及其余数据域、全Dream生产访问关闭与正常本机Google/账户/模型验收尚未完成。两个真实任务与协调goal继续active。


## Workflow 新增公开上下文与确认回执（2026-09-15）

Luna实际公开5接口族通过18上下文、14确认用例和170断言，受限AUTH/DATA roles；source JSON/标题原事务、grant新context限制与终态末次持久化、stored lease/claim保护和权限拒绝均验证。原fixture completed转换55000与合法取消终态remaining范围保留，正常数据库/模型未调用。完整Run及其他剩余域继续active。见[170回执](admin-auth-data-verification/workflow-public5-context-confirmation.md)和[阶段记录](../stage/stage_admin-workflow-user-message-validation.md)。


## Runtime 数据与完整 Run 公开验证（2026-09-15）

Admin refs/Voice runtime6公开合同104与Run5/21cases/163断言均实际通过；原OAuth-only401/403、Run UTC投影失败及source12/最小40修复证据保留。Manifest模型UnicodeWhiteSpace与Pythonstrip来源校正29unit/42actualsourcecases通过，不改公开schema/hash/原业务算法。Preferences19focused与新publicharness type/lint通过、具名隔离fixture准备完成，公开2待真实回执。规范Registry60增加已注册Preflightread1+Preferences2，不代表100生产候选文件关闭。所有真实Google/normal账户实体模型验收、其它未闭合域与完整启动仍active。见[Run阶段](../stage/stage_admin-workflow-run-validation.md)、[Deck阶段](../stage/stage_admin-deck-voice-domain.md)、[Preferences阶段](../stage/stage_admin-user-preferences-domain.md)。


## Preferences 公开交付（2026-09-15）

Admin2ops/78公开断言实际通过，strict5字段/NULL并发合并/rawJSON/firstlogin和serverconfig隔离/OAuthscope+idg拒绝/原request receipt-audit恢复。实际Registry60两个hash与DTO已交Dream；无新migration。见[78回执](admin-auth-data-verification/user-preferences-public78.md)。本轮阶段技术验证通过；其他全域与normal Google/现有账户实体模型验收仍active，任务和goal不标complete。


## 协调文档与 worktree 镜像验证（2026-09-15）

Luna对归档前82份证据和9篇阶段计划的91路径执行逐byte/SHA镜像、Markdown路径/头、JSON与凭据字面量检查，退出0、failures=0；两工作目录diff检查退出0。Admin 0000..0059实际60文件聚合SHA保持已冻结值。见[原回执](admin-auth-data-verification/coordinator-docs82-mirror91.md)。本回执归档增加第83个证据文件，不将归档后的库存冒称为先前82项验证候选。


## 0060 与 Social9 当前阶段（2026-09-15）

0060 expand、六实际迁移子命令、九列catalog和15实际角色查询通过，保留aggregate preSQL和RESTRICT23001及ACL harness失败/范围校正，正常数据库未动。见[本轮migration阶段](../stage/stage_admin-workflow-preflight-request-migration.md)。Social9实际DTO/ORM/注册69、25focused和修复后的wholetype通过，具名新fixture准备0，公开九操作230断言与原source22通过；旧60契约/hash不变，已交付Dream消费。见[Social阶段](../stage/stage_admin-social-friendship-domain.md)。Dream全部生产DB关闭与真实Google/正常账户实体/模型回执仍未达成，goal维持active。


108份证据和12份计划共120路径的Luna文档/镜像/Markdown/JSON/凭据字面量检查通过0，旧60SQL aggregate不变；[原回执](admin-auth-data-verification/coordinator-docs108-mirror120.md)在该轮核验后归档，不冒称它位于原108库存。完整PF新具名target只clone本轮技术facts、冻结0060/ACL0且源摘要不变；[完整PF阶段](../stage/stage_admin-workflow-preflight-public-validation.md)该轮仅完成target，后续公开应用结果见下面的PF分层补验记录。

## PF 分层补验更新（2026-09-15）

当前状态：首次完整24合同退出1且原首failed历史保留；补验完整命令仍退出1，在read-passed-active原事实自然过期时停止，已越过前置执行/源码/并发/replay及checking/failed读取断言。后续8剩余读取74断言、原权限末段11断言、四类故障96断言、原结果恢复与初始UOW回滚44断言、三阶段真实COMMIT后中断及父恢复54断言全部通过。不能把分层补验报告为原24一次全通过。Dream全部生产入口关闭及真实Google/正常账户实体/模型仍未达成，goal active。

全部坚持DTO→Service→typed Repository→Drizzle，AUTH/DATA用受限连接，Dream无数据库fallback。四类fault96、恢复44、三阶段父恢复54、剩余read74、权限尾段11的命令/退出码与原失败回执已归档；49新增公开文件在55私有配置/86实际secret值及9pattern类别检查零命中后写入，credential_source仅生产枚举canonical/admin，实际password proof仍参与检查。见[公开PF阶段](../stage/stage_admin-workflow-preflight-public-validation.md)、[fault](../stage/stage_admin-workflow-preflight-fault-validation.md)、[原请求恢复](../stage/stage_admin-workflow-preflight-recovery-validation.md)。生产PF验证冻结本轮结束后释放，Admin继续必要sharedRun码点兼容与create/retry接入，消费端清单与真实验收仍active。


## Run72 注册与首轮公开合同

规范目录实际增加 `workflow-run.create/retry`，72 项；原 70 项完整描述符、Preflight receipt、special delegation artifact 未变。新增注册47项、request/stored source2项、bounded receipt1项，新Route2/source clock/retry1与类型/lint先前通过。新增 remaining harness 首次全typecheck退出2，原因是 PATH-only env 与 Next ProcessEnv 类型，生产运行时不应继承 secret/NODE_ENV；Admin负责类型修正，原失败保留。

主协调创建新owned `_run72` target，51534/独立data_directory/ledger61/ACL0，原 `_preflight61` 技术source 125表摘要不变、无migration replay。28cases/10receipt准备成功38setup检查；prepare中旧Voice不等于Thread、未注册旧操作名、旧binding/PF clone列、源日期序列化、固定错误hash/active fingerprint唯一约束和普通Thread grant上下文失败分别保留，更正均在主fixture脚本，未改生产约束或业务预期。已成功seed走公开Thread/message/PF/Run/fail/cancel，正常业务数据库不变。

首次Luna `python3 /private/tmp/ink-auth-migration-validation/run-run72-public-contract.py` cwdAdmin729f退出1，停在readonly错误码：实际共享Auth `ACCESS_SCOPE_REQUIRED`，主fixture误写领域 `DREAM_SCOPE_REQUIRED`。六个前置成功流程已越过全source/20INSERT/consumption/two transitions/原response replay/concurrency/protected-state断言；harness未发出总数，不虚构。主协调另外只读checkpoint六项原完整static fields、单receipt/audit、newRun两transition、旧ID与精确Run/Thread scope通过，12表snapshot私下保存。

remaining scope将SELECT核验六项完整originals而不重复acceptedPOST，补22denials与10receipt；仅修正共享Auth码。三个尚未执行的时效用例另准备同input_hash/frozen facts的新request/currentPF，原full fixture、已接受ID/time/body/expecteds及旧signed期限不改，范围须在回执中列明。新Run事务fault/unknown COMMIT恢复尚未执行。全Dream SQL关闭、正常Google/设备provider/真实账户实体模型/Admin可见回执仍pending，三个真实task/goal active。

Run72后续实际：whole类型校正0（仅erased ProcessEnv cast，不继承NODE_ENV/secret，也不改registered canonical runtime）；Luna remaining22/10GET/230PASS0，六原完整results保留。主SELECT后置六results/八核心表byte exact，三新未执行PF各11 frozen fields equal；正常业务未动。原 full exit1保留；新Run事务fault/unknown COMMIT仍继续。

Run72故障恢复实际：九项事务失败全16表rollback equal、一次实际final COMMIT loss通过原GET/replay恢复，业务68PASS；原wrapper因maincleanup helper scope exit1保留，独立cleanup SELECT3PASS0、trigger/function0。生产代码未为harness失败改动。72短窗口释放，Admin继续独立source/claim/finish；文档归档/引用校验继续，整体goal active。

Run72共42个新公开回执在65私有配置/112实际secret值及9pattern扫描零命中后归档，source与目标只合并本协调增量；原退出1、remaining230与atomic68/cleanup3分开记录。详见[Run阶段](../stage/stage_admin-workflow-run-validation.md)、[原子恢复](../stage/stage_admin-workflow-run-create-recovery-validation.md)和[证据索引](admin-auth-data-verification/.folder.md)。

Run72文档最终Luna真实命令 `python3 /private/tmp/ink-coordination-docs-validation/validate-run72-new42-220.py` cwd原Dream退出0，41proof/42new/220inventory/5own镜像/273本地引用、failures空；临时review仅修范围措辞为22denied+10receipt/230，未加inventory或重跑。Dream当前consumer HEAD `a5119546`，前置 `f4ccb7dd` publicPFread、`9cf4609f` shared-file Thread owner Admin；当前48 SQL-bearing/513 literal/16 driver-import仍为候选扫描而非全运行关闭。

后续launch actualApplication NULL Agent fingerprint第一source退出1保留，未注册candidate只修omitNULL key；affected实际source2+GET24/type/lint/AST/diff0。实际注册75前三个新增source.ensure/dispatch.claim/finish SHA和old72 FULL descriptor/PFreceipt/delegation parity都由主读raw确认，postregistration Route3+Receipt7/10及全type/lint/diff0。主准备 `_launch75` 技术目标命令0/ACL0，source `_run72`125表before/after exact，明确owner/loopback51534/datadir/capability证明，无migration replay/正常PG改动；完整fixture/public/components/fault/Runtime/real仍pending。具体设计与实际回执路径在[launch组件计划](../stage/stage_admin-dream-launch-component-validation.md)。

主协调同期独立实现尚未注册 `workspace-default.ensure` DTO/typed Repo/Service/source adapter/policy，原最早owned Workspace行为和legacy text IDs保留，canonical bigint string、actor初始化并发锁、原receipt当前owner/nullscope验证、result/audit同UOW；不动冻结75共享模块/migration。Luna实际unit20+source1/21、全type/ownedlint/PythonAST/diff均退出0，raw已审核；source实际helper固定DB结果/UUID捕获参数与commit/rollback，无SQL执行。原默认Workspace路由SQL、producer注册与public concurrency/UOW/consumer仍pending，详见[默认Workspace计划](../stage/stage_admin-default-workspace-domain.md)。所有goal仍active，完整真实Google/现有账户实体/模型/Admin日常可见验收均未执行。

launch75完整公开首轮实际退出1停在actor_id query：全局身份边界400 USER_OVERRIDE_FORBIDDEN先于route闭集404，属于harness预期层级错误；仅首个Source已提交，其余37无receipt，主任务17表/原source/receipt检查点保留。恢复harnessguard首轮未收录测试退出1与两轮type退出2均保留，6guard通过、静态supplement type/lint/diff0；没有修改生产授权或放宽运行时DTO。

随后Luna实际 `python3 /private/tmp/ink-auth-migration-validation/run-launch75-public-continuation.py` cwd Admin729f EXIT0，37 remaining cases/skipaccepted1/prepared38/21 original GET/974 assertions/protected17，实际应用+entireensure、claim commit-before-captured-turn和独立finish通过。Root primary实际 `python3 /private/tmp/ink-auth-migration-validation/run-launch75-atomic-recovery.py` 同cwd EXIT0/308，11选择性事务fault全17表rollback，3实际最终COMMIT后单次响应丢失分别GET200/replay200/fullsource与original scopes/time/result恢复、receipt/audit各1无重复；清理11组自有trigger/function PASS、activeobjects none。Root随后SELECT-only `run-verify-launch75-preservation.py` EXIT0/19，原Source/Thread/fullreceipt与8全无关表及其它旧rows exact保留。75冻结窗口已释放Admin，下一步默认Workspace注册及failure候选接线/消费者继续。详见[组件](../stage/stage_admin-dream-launch-component-validation.md)和[事务恢复](../stage/stage_admin-dream-launch-recovery-validation.md)。

独立未注册failure source7/domain17/originalGET18（受影响POST17+GET18共35）及wholetype/lint/AST相关gate真实0；保留原FAILED Run先提交再metadata独立提交/no-op/currentowner/source/µs语义。candidate检查不当作注册/公开业务通过。完整Dream剩余生产SQL、SystemConfig/启动/health等、全启动Runtime及正常Google/设备/现有账户实体模型/Admin日常可见回执仍pending，整体goal保持active。

本轮43份新公开回执（42候选+disclosure proof）经74份0600私有来源、121个实际secret值/编码形式与9类凭据模式零命中核验后归档；原full EXIT1/两轮type EXIT2保留，37/21/974与11fault+3realCOMMIT/308和preservation19分别记录。仅合并本协调文档增量，原用户/其它Agent文件不触碰；整体goal继续active。


## Workspace76与独立用户SystemConfig候选

默认Workspace76独立公开契约实际347/14POSTcases/22originalGET/protected17 exit0，primary selectedWorkspace/receipt/auditINSERT faults3加real finalCOMMITloss90 exit0、cleanup3×2/none；SELECT preservation159 exit0，旧source125表完整行/firstprep17/5positive original全部保留。首次fixture主任务scope error exit1保留，continuation16setup/17exact0，不reset已接受数据。Root与producer均读安全raw，76窗口释放；正常账户/Provider/model/Runtime/FS不进入技术回执。见默认Workspace公开计划。

Root userSystemConfig9独立新文件（strict10 normalized字段/typedRepo/Service/pureCodec/unit/source/policy/handoff）首轮25=unit24+source1批14、whole type/lint/AST2/diff0；原get/save参数/JSON精度/close/commit实际对照，row锁合并只config/updated_at，5Prefs/first-login独立，未注册或接fixed map。actual Thread/Run reader与全部生产消费者仍待实际接入，不能当全SystemConfig或全Dream PostgreSQL关闭。完整正常Google/设备provider/指定现有账户实体/模型/Admin日常可见回执未执行，整体goal继续active。

本轮最终21公开候选与summary proof共22份，84份本轮自有0600私有来源、177个实际secret值及其JSON/URL/base64编码、9类凭据pattern零命中后归档；首次19-file proof作为历史文件保留。所有新增证据verbatim/SHA一致，协调own docs只增量合并，用户/其它Agent dirty无覆盖、Git无mutation。


## Failure77与Thread SystemConfig候选

Failure77公开续接实际完成：Luna network retry exit0/556，stored originals6、denied POST16、Original GET27、positive POST replay0、protected17。Root atomic recovery exit0/126，metadata UPDATE/receipt INSERT/audit INSERT三处503全回滚，实际final-COMMIT loss为503→GET200→replay200且单metadata/receipt/audit；final preservation exit0/293，old125/prepublic non-target125/postpublic17/positive6及Run/PF/transition/binding历史保留，自有fault0。原public/continuation/sandbox failures及partial287/editor6均保留，不重写为成功。

Root Thread SystemConfig reader候选复用严格Thread DTO、ChatThreadRepository current-owner SELECT和User SystemConfig mandatory codec/helper。最终Thread18、cache-free type0、ownedlint0；移除额外UPDATE row lock以避免共享grant并发升级风险，未改变上游binding/Run authority。仍未注册或做公开验收。

本轮最终53候选与scan proof共54份，在107份owned0600私有来源、410个实际secret值及1499种JSON/URL/base64形式和9类pattern零命中后归档。前两次scanner false-positive失败原样归档；selector标签排除不排除JWT/idg/DSN/password/secret。正常Google、指定账户实体、Gateway/真实模型、Runtime/FS和Dream全入口无PG仍未完成，整体goal active。

## Story Workspace Registry114 Catalog 切片

Admin在Registry111冻结前缀后增加`story-workspace-catalog.workspace/read/patch`三个业务操作。Zod DTO、Service、typed Drizzle Repository、OAuth权限、单UOW写回执/审计、thin handler、operation artifact和original receipt入口已实现；read没有receipt。公开`artifact_available`从canonical `artifact_status`派生，兼容物理列不进入Drizzle模型，无新DDL或migration。三个hash为`3fbd32dd7343ae5008d7f71f2475db1b022a95060f2544b9dfbea606af894965`、`317ed15c2f827c44099e0641693d3dcf09bc01186e26586a9b2281226faa142b`、`0ef2cc94d01d488c46a9872efb389b43890e9267460705ebee33ac5ab47180cd`，Registry114完整SHA为`dc80b77410aac58528dde77578154d9848d9dfc3bf55de4a35c8c315a81af704`。

Dream以strict Pydantic RootModel consumer替换`story_workspace.py`的11个Workspace/Story/Character/Scene公开catalog入口，移除该组路由的database导入、SQL/helper/transaction路径，并保留原公开DTO、过滤、排序、分页、详情关系、present-field patch和错误反馈。Admin focused8files/28tests、whole240files/1913tests、lint、type和Next build通过；Dream本切片focused49tests通过。隔离PostgreSQL harness应用62个Admin Drizzle migration，restricted executor下6/6所有权、关系、幂等、rollback和ACL用例通过并清理自有cluster。首次harness只因fixture缺少现有artifact identity完整字段失败，补全合法artifact bundle后重跑通过，未放宽生产约束。Admin whole首轮1912pass/1fail发现并纠正了canonical Drizzle不得加入`artifact_available`布尔影子列；最终公开值只从`artifact_status`派生。

Dream扩展Story suite实际724pass/35fail/3skip、exit1。本切片直接导致的旧`story_workspace.database` patch测试已更新并进入49项通过；其余失败为旧auth override的401、legacy SQLite Chat fixture缺当前`history_final_text`列和缺少本机vendor episode artifacts。失败按实际保留，没有恢复Dream数据库依赖或调整业务预期；后续全业务/harness阶段继续处理。

corrected source-only扫描读取543模块，得到79个production entry、50个SQL模块、454个SQL literal、28个driver/database import模块、52个legacy helper call、392个connection/transaction call、29个Admin consumer模块与132个operation name，parse errors为空。相对Registry111减少1个SQL模块、9个literal、1个driver/import模块、1个legacy helper和11个connection/transaction call；其余候选、完整真实Google/设备/指定账户业务/模型/Admin日常可见性验收仍未完成，goal保持active。
