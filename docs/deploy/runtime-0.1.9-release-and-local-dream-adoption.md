<!-- [Input] Runtime canonical original src, same-SHA CI/npm artifacts, and local Dream resolver/startup identity. -->
<!-- [Output] Minimal release/adoption plan, version contract, evidence and rollback. -->
<!-- [Pos] Current Runtime 0.1.9 integration; source changes alone do not prove publication or running-process adoption. -->
<!-- [Sync] 2026-09-13: record operator-confirmed real model/Notion E2E and subsequent requested backend stop without restarting. -->

# Runtime 0.1.9 发布与本机 Dream 接入

## 判断与交互方案

Runtime 是同一套原始模块，不维护第二套实现。保留唯一 `src`，删除重复
`restored-src`；原始目录、模块、权限和 1,902 个文件的内容摘要保持不变。
来源提交 `a8a678cb6244e6770e1e421767ff0987a1d95549`、原始 subtree
`7640f58ea271eb60952ebdbe0dfa173fc96ebe30` 与库存摘要记录在 Runtime
`runtime/source-provenance.json`，只读 `source:verify` 拒绝重复源码目录。

既有 GitHub CI 对 main 的同一 SHA 运行四个平台的真实构建、SDK/MCP/OAuth、
Dream MCP 管理与 Notion/模型能力进程合同。只发布这些被验证的 tarball，
先四个平台包、后 selector；npm registry integrity 必须逐包与原始归档匹配。
用户已确认公开发布与本机 Dream；保留 Anthropic 版权，selector MIT 不重许可原始模块。

各阶段分别报告：源码完成、CI 资格完成、npm 发布完成、安装完成、Dream 运行采用。
不把 source pin、CLI 兼容输出或本地测试冒充后续状态。实际失败时保留验证门禁，
修复原因后重跑；不增加 UI、确认弹窗、部署框架、数据库或业务状态机。

## 原子版本面

| 对象 | 版本 |
| --- | --- |
| Runtime selector、四个平台包、Dream resolver、Docker、AutoDL repository pin | 0.1.9 |
| Dream backend 项目与 uv virtual project | 0.1.3 |
| Dream frontend 项目 | 0.0.3 |
| Python SDK（不变） | 0.2.145 |
| CLI/协议兼容标识（不变） | 2.1.241 (Claude Code) |
| API schema（不变） | 2.0.0 |

Dream 不复制 Runtime 源码、SDK transport 或 MCP 状态机。兼容适配复用
Runtime 原 compiler 的 source-bound 内存变换，不修改 canonical 原始文件；
它消费已有 server-owned Notion 与 model/effort carrier，命令 hook 和 stdio MCP
不得继承 Notion 私密字段。原有 workspace/TMPDIR、安全拒绝和 LKG 行为不变。

启动身份修复只移除 cli.js 文件名误判，继续依赖已经验证的 shared resolver；
测试使用 workspace 外的 native C fake ntn，避免为 shell-script shadow 放宽生产策略。
Linux hosted CI 的 AppArmor userns 前提只在一次性 job 准备、bwrap preflight 并恢复，
不修改本机 Dream、远程或生产安全配置。

## 执行和验收

1. 合并 Runtime scoped PR，等待同 SHA 四平台资格和自动 npm 发布。
2. 匿名下载五个精确版本归档并验证 integrity；从公开 registry 全新安装。
3. 更新正常 PATH 上的 Runtime 安装，验证两个 alias、package-root `cli.js`、
   相邻 manifest、SDK 配对、14 项 npm capability、selector/platform 摘要和零 `.map`。
4. 合并 Dream 精确 pin、项目版本、测试、Docker/deploy 与双语文档，安全快进本机项目。
5. 核对本机后端的 cwd、命令和进程所有权，只重启其服务。关联重启后的 PID/启动时间
   与该进程输出的 resolver 身份，记录 Runtime 的精确 package version、路径和 manifest/摘要；
   与公开制品匹配，并对同一安装路径执行无真实凭据的既有 Runtime/MCP smoke。health 只证明
   服务可用；这些证据证明启动选用的 Runtime，不冒充一次真实用户/model turn。

`CLAUDE_CODE_CLI_PATH` 仅用于经明确评审的绝对路径回滚，不能掩盖旧 PATH 安装。
AutoDL 修改仅同步仓库版本合同，本次不操作任何远程环境。Docker daemon 不可用时
如实记录未运行镜像验证，不伪装构建成功。所有协议测试使用本地 fake provider，
不读取真实账号凭据、Notion 内容或用户工作区；这些自动化测试不宣称真实用户业务 E2E。
用户另行完成的真实业务验收与此技术范围分别记录，见下文。

## 目标审查与回退

这套方案只替换双树校验、修复既有发布链路并更新既有 resolver/安装/进程，
每项修改均服务于“去歧义、发布、Dream 实际使用”。不保留平行 Runtime，
不升级 SDK/前端依赖、不改 Admin-owned schema，不属于架构重设计。

删除的 Runtime 重复源码可从 Git `a40037a` 恢复，原始参考仓库不修改。
回退使用上一已验证提交/安装树并重启明确拥有的后端；不覆盖 npm 版本、
不把旧实现收据重新绑定到新制品，Dream pin 和安装必须一致。

## 证据状态

Runtime PR [#19](https://github.com/glide-the/ink-claude-code-dream/pull/19) 已合并。
本机 Darwin ARM64 六项 full qualification、两遍字节一致打包和干净 npm smoke 通过；
bundle SHA-256 `c8188a9249574352327ed8fde4b1703c9b389cc1a83d8d601beb44103bace675`，
artifact-tree SHA-256 `cf28677c948855bc372881fdd4f1791fa5b077701318adfb893d10c544a227bc`。
同 SHA `820be726b5c9011a493bbb14a84a97fe548d58bd` 的
[四平台资格与五包聚合](https://github.com/glide-the/ink-claude-code-dream/actions/runs/34710677422)
已经全部通过。CI 原始五归档下载后经 `verify-npm-tarball.mjs` 再验，
exact five-package inventory 和零 `.map` 均通过。
[自动发布](https://github.com/glide-the/ink-claude-code-dream/actions/runs/34711405353)
遇到新包 registry 可见性超过 30 秒核验窗口；只允许在既有公开摘要与原归档
相等后重试同一 run，保留 main/qualification SHA 和原始制品，不重建已占用版本。
发布 run 的 attempt 5 已成功，五包 `0.1.9` 全部公开，selector `latest=0.1.9`。
匿名下载的每个归档与原 CI 字节完全相等，registry SHA-512 integrity 也逐包相等：

| 包（均为 `@glide-the/ink-claude-code-dream` 前缀） | 公开归档 SHA-256 |
| --- | --- |
| selector | `b8bc59639e269a885d3b9ad781381acbce146da7a194f935d32f33f9ed58ca6a` |
| `-darwin-arm64` | `448b8be16ef9c6e1388b7975d1050286d6c9346444d003a3666476eaa88ed3cc` |
| `-darwin-x64` | `70f27a95c857bc107fc3c456bbc5c65532907f3bf6643562982e38df352824dd` |
| `-linux-arm64` | `465b04f451a2d60e8f1eb90666f1027e42a57a16e7f7c957c9f6d7f72b678bce` |
| `-linux-x64` | `7dfe4be34832fa5da493a25570c82505002ea6e219b310269426f9715c55af64` |

公开 SDK wheel SHA-256 `9e16643718e4c2eb62ba2bef43a79b83a683f0291e083a61ccb027e47516a34e`，
sdist SHA-256 `09251798ca9648678ad85c1c3d90248f6e05eeed78a4a3e82c6fa8ea62b65eb8`；
官方摘要、元数据和零 map 均通过。复用现有 registry verifier 函数完成两个 Python
3.12.9 独立安装、五包公开获取/校验、隔离 npm 安装和两个 SDK/CLI probe，均通过。
唯一 SDK provider 为 `ink-claude-dream-agent-sdk`，没有安装官方 SDK distribution；
`ClaudeAgentOptions`、`ClaudeSDKClient`、`query` API 和 exact CLI banner 均符合合同。
这些是 provider-free 制品检查，不转发 registry/model 凭据，也不调用真实模型。

正常 PATH 安装已验收为 `0.1.9`，两个 alias 都解析到同一个 npm package-root
`@glide-the/ink-claude-code-dream/cli.js`。公开文档不记录具体主机安装路径。
selector 和实际选中的 Darwin ARM64 payload 共 76 个文件逐字节匹配原公开 CI 归档，
14 项 capability 和零 map 均通过。实际 native core SHA-256 为
`e680a4d90fcd26a65d1fa820860a37ad5f96fbcb25c79e8f87ad3b706273a3cb`，
selector release manifest SHA-256 为
`712aaaf5228f664ff1a99c6cfab424ce96aa11fac9fd0af9b3f6f0839979d64a`，
native artifact manifest SHA-256 为
`60b8b0797a788c69a00a641c722bc9b9adf60e1758632069a889edda5b43e79f`。

Dream 代码回归 151 passed / 17 subtests，无失败或跳过；额外对已安装公开 Runtime
运行 `backend/tests/test_claude_agent_notion_cli_runtime.py`：1 passed / 0 skipped。
该合同通过真实 ClaudeAgentRunner、SDK 和 sandbox 执行测试 native ntn，
只使用本地 fake provider、凭据和测试工作区，不访问真实 Notion。

核对所有权/cwd/启动时间后，只优雅停止并重启任务拥有的本机后端。
当时新进程的 cwd 与配置的 Dream backend 项目目录一致，复核仍存活；
`/api/health` 返回 `ok` / `0.1.3`。逐进程 PID、启动时间、主机路径和日志
仅保存在本机私有验收记录，不随公开仓库发布。
该进程启动身份为 `cli_mode=dream_runtime`、`cli_runtime_release=0.1.9`、
`sdk_version=0.2.145`、`sdk_cli_compatibility_version=2.1.241`，cli_path 为上面的
正常 PATH selector，无显式覆盖。启动代码提交为 `77dae52f`；后续提交只补文档。
这证明本机服务启动选用了新 Runtime，配合同安装的 CLI/native/sandbox 合同通过，
不冒充一次真实用户/model turn。Docker daemon 未启动，因此未运行镜像构建；
AutoDL/远程生产环境未操作，SDK/依赖锁/API schema 未升级。

旧 `0.1.5` selector 与 native 安装树已在本机任务专用目录备份，未删除；
具体回退路径只记录在本机私有验收记录。
0.1.4/0.1.5 历史业务收据不覆盖此实现。源码清理、方案审查、公开发布、
本机安装和实际后端启动采用均完成；当前交付见
[Dream PR #52](https://github.com/glide-the/im-dream/pull/52)。

## 后续用户验收与进程状态

2026-09-13，用户明确确认已验证真实用户模型对话及真实 Notion 端到端流程。
这项结果来自用户验收，不是上述 fake provider/隔离测试推导出的自动化业务回执；
本次仅记录结论，不读取、复制或公开真实对话、Notion 内容、账号或凭据。

在此前启动采用完成后，任务启动的本机 Dream 后端已按用户要求优雅停止并确认
退出。上述 health/身份是当时的启动验证，不意味着服务现在仍运行；后续文档和
Runtime 发布工具收尾不重新启动服务、不重新安装或重发 `0.1.9`。Docker 镜像
构建仍未验收，远程环境未操作。项目版本和 SDK/Runtime 配对保持不变。
