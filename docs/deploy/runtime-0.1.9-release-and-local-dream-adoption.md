<!-- [Input] Runtime canonical original src, same-SHA CI/npm artifacts, and local Dream resolver/startup identity. -->
<!-- [Output] Minimal release/adoption plan, version contract, evidence and rollback. -->
<!-- [Pos] Current Runtime 0.1.9 integration; source changes alone do not prove publication or running-process adoption. -->
<!-- [Sync] 2026-09-13: replace duplicate-source 0.1.8 stage with unique src and CI release. -->

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
不读取真实账号凭据、Notion 内容或用户工作区，不宣称真实用户业务 E2E。

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
四平台 CI、公开 npm、Dream 安装及运行采用仍待对应阶段的实际证据；
0.1.4/0.1.5 历史业务收据不覆盖此实现。
