<!-- [Input] Runtime 0.1.10 release CI, public npm artifacts, Dream resolver/plugin installer, and local screenwriting-skills operation. -->
<!-- [Output] Version, publication, adoption, validation, failure and rollback evidence for the plugin-management repair. -->
<!-- [Pos] Current Runtime 0.1.10 release and local Dream adoption receipt; 0.1.9 remains immutable history. -->
<!-- [Sync] 2026-09-15: record Runtime publication and Dream plugin-management adoption. -->

# Runtime 0.1.10 插件管理修复与 Dream 接入

## 背景与目标

Admin 已登记并批准 `screenwriting-skills`，Dream 选择插件后在 marketplace
同步阶段返回 `CLAUDE_PLUGIN_INSTALL_FAILED`。操作回执显示已安装 Runtime
`0.1.9` 的 headless 入口只接受 print、Python SDK stream-json 或 MCP
management，因而在创建 ready artifact 之前以 exit 2 拒绝 `plugin` argv。

Runtime `0.1.10` 恢复原始源码中的非交互 plugin/marketplace Commander 注册和
处理函数。Dream 默认插件安装边界复用 Agent 的 manifest-qualified resolver，
并在安装前执行 `plugin --help`；版本输出成功但管理命令缺失时立即失败。
真实安装随后暴露 Admin `0.1.0` 与 Dream 对同一目录的排序差异：Admin 按完整
POSIX 路径排序，Dream canonical digest 按路径组件排序。Admin `0.1.1` 已统一
为组件排序；Dream 只为已经不可变的 `0.1.0` entry 重算旧顺序，内容字节必须
完整匹配，artifact 身份仍使用 canonical digest。本次不新增 Schema、安装协议、
HTTP 控制通道或 Agent turn 状态机。

## 原子版本面

| 对象 | 版本 |
| --- | --- |
| Runtime selector 与四个平台包 | `0.1.10` |
| Admin control plane | `0.1.1` |
| Dream backend / uv virtual project | `0.1.4` |
| Dream frontend | `0.0.4` |
| Python SDK（不变） | `0.2.145` |
| CLI compatibility（不变） | `2.1.241 (Claude Code)` |
| API schema（不变） | `2.0.0` |

## 发布证据

- Runtime PR [#26](https://github.com/glide-the/ink-claude-code-dream/pull/26)，merge commit `70043df073f065f9b375cefdb4a2aa7f140d3fd9`。
- [Runtime CI](https://github.com/glide-the/ink-claude-code-dream/actions/runs/34942254270) 通过。
- [四平台资格与五包聚合](https://github.com/glide-the/ink-claude-code-dream/actions/runs/34942254287) 全部通过；每个平台均执行真实 SDK、MCP 与本地 Marketplace plugin 生命周期合同。
- [npm 自动发布](https://github.com/glide-the/ink-claude-code-dream/actions/runs/34943560980) 最终成功；两个早期 attempt 的上传已被 registry 接受，但可见性窗口分别在 darwin-arm64、linux-arm64 超时，公开后只重跑同一资格归档。
- 公开 selector integrity 为 `sha512-QlpFq6CvcA2DRudLgJgaQMc5aP7MfJJ5CADY7rbgraTGq0FAF+VJx8VvK/6xFpHb+FgZOCgjlXqmS0nOUIjzuQ==`；平台 integrity 分别为 darwin-arm64 `sha512-bwb3BrIdcNxcUyPFwoUup2QCGkKfun5L/rvmfrz11w1gydPkGj/Dy6n+j/T9BXYYfFvwFWG0f1EKjn2PMYCgCw==`、darwin-x64 `sha512-GbvGTyrxJ0L0+JLuAW0wCvi/1Q2X2TxHMPySFhw61xTzVahjaIKPgQBGEE12im3C40lxyXLjiC0go7PxIOgRwA==`、linux-arm64 `sha512-79AWiXfnbcBpz0MhyBnWgoZje57Xa30PCuP6J6Yj3vMmeSgjv+8fbJe/LRf84ApK6rAnc4pEEBc+Znrx8KzhHQ==`、linux-x64 `sha512-Q0aOjtgfFE6vY21cj+Zrco0wDGm0aWRTCqDN282aYy6NqETd7hiGZX3yMs485ov/ybqQY2KusGVJhqGfZqgv+g==`。
- 公开 registry acceptance 的 wheel 与 sdist 都解析 SDK `0.2.145`、CLI `2.1.241`、Runtime `0.1.10`、`pluginManagement: true`；公开 darwin-arm64 包通过 Dream 完整本地 Marketplace pipeline。
- Admin digest 修复由 [dream-im-platform PR #14](https://github.com/glide-the/dream-im-platform/pull/14) 合并为 `69a14aeb60c5b4d59987486d00fe2d4fc3bfc367`；版本为 `0.1.1`，完整单测 `690 passed`。
- Dream [CI PR #59](https://github.com/glide-the/im-dream/pull/59) 合并为 `36d503a86f474ef9c8f3e6d1495dcc56b01ad9ff`，修正默认 `develop` 分支此前未被 pull-request workflow 监听的问题。

## Dream 执行规则与失败处理

1. `resolve_claude_binary()` 默认调用 `sdk_env.resolve_claude_cli_path()`，继续验证精确版本、entrypoint、manifest、capabilities 与 selector/platform digest。
2. `INK_CLAUDE_CLI_PATH` 只接受绝对、存在且可执行的 plugin-only override；非法值不回退 ambient `claude`。
3. 安装前依次验证 `--version` 与 `plugin --help`。管理入口缺失时 operation 进入 error，不运行 marketplace 或 install，也不创建 ready artifact。
4. 正常流程仍为 Admin approved entry → revision/digest 校验 → marketplace add/update → plugin install → CLI registry/cache containment → immutable artifact → Deck 选择 → workspace pack → SDK `--plugin-dir`。
5. marketplace、install、registry、manifest 或 digest 任一失败均保留 operation 回执；重试重新执行现有校验，不修改旧制品。
6. 新 Admin revision 与 Dream canonical digest 都按路径组件排序；只对已持久化的 Admin `0.1.0` entry 计算旧的完整相对路径顺序。批准值必须等于其中一个完整内容摘要，artifact 与 Deck 始终保存 canonical 值。

## 本机业务验收合同

本轮只通过现有 Dream 设置页重试已登记的
`screenwriting@screenwriting-skills`。操作由 Dream plugin service 写入正常
PostgreSQL operation/installation 记录，并由同一页面消费状态；不创建 Agent
turn，也不改写故事资产。

| 概念/事实 | Source of truth | 写入或同步模块 | 可见消费者 | 预期影响 |
| --- | --- | --- | --- | --- |
| Admin approved plugin entry、revision 与 digest | 现有 Admin PostgreSQL 记录 | Admin 已完成登记；Dream 只读取并校验 | Dream Plugins 选择与安装步骤 | 保持不变 |
| Marketplace 同步与 plugin install operation | Dream PostgreSQL operation/installation | Dream plugin service 调用 manifest-qualified Runtime CLI | Dream Plugins operation 与 installation 状态 | 由旧 error 创建一次新的 retry，并到达 ready |
| Deck/plugin selection | Dream Deck plugin 配置 | Dream 设置页在 ready 后选择 | Dream Work > Plugins | 本轮不改变；只证明插件可安装 |
| Project、Episode 与 canonical artifacts | 现有 story workspace 文件及投影 | Agent 与 after-turn Hook | Story、Episode、Execution 页面 | 不在范围 |
| Run-private `.dream` publication 与 shared conversation | 现有 Run/Thread 状态 | host Hook 与 ClaudeAgentService | Dream 文件 API 与 Chat/Dream 历史 | 不在范围 |

成功条件是可见重试动作产生新的 operation，最终页面显示插件可用/ready，且
backend 日志确认进程使用 Runtime `0.1.10`。旧 error operation 保留供复核，
不通过 SQL、文件改写或替代服务伪造结果。

2026-09-15 本机验收结果：

- Admin 同步远端默认分支为 commit `50825325b3940a17f032129851f5c83382863000` 并批准 `screenwriting`；旧 Runtime failure、remote commit drift 与摘要排序 failure operation 均保留。
- 可见系统 Chrome 从 Work → Plugins → 从 Marketplace 添加选择 `screenwriting@screenwriting-skills`，operation `cop_27d25716ff29427a9675b5e52057413e` 到达 ready；幂等复验 operation `cop_e9f526390ec94b83b14d5d5b268f4c43` 同样 ready。
- installation `cpi_b31de00a4ad24c7d8bb003496b523ba0` 为 `screenwriting` `2.0.0`、79 files、canonical artifact digest `sha256:dcd191119b9291af1a19a0a11ffa27e0c9f479b2d0e7648e09a29c726fe6697c`。
- 操作证据记录实际 argv `plugin install screenwriting@screenwriting-skills`、CLI `2.1.241 (Claude Code)`、exit `0`，以及不可变 Admin `0.1.0` digest `sha256:7d25311159c29e60f8d9cf05360383527880431448af52087b6363a42d8c925c` 与当前完整目录旧顺序摘要相等。
- headed Playwright 正常业务旅程及 operation API 断言退出 `0`，`1 passed (9.2s)`；未创建 Agent turn、Project、Episode、Run 或 Gateway 请求。

## 验收范围与回退

Provider-free 测试覆盖 resolver、非法 override、版本成功但管理命令失败、实际
本地 Marketplace install、artifact、Deck pack、SDK launch 与 uninstall。
本机业务验收通过现有 Dream/Admin/PostgreSQL 路径选择
`screenwriting@screenwriting-skills`，保留正常 operation/installation 供 Admin
复核。该业务验收不读取或公开凭据、Workspace 正文或模型对话。

Dream 最终 plugin、resolver、Docker、版本、server 与 registry verifier 合同为
`180 passed, 6 skipped, 31 subtests passed`。前端使用 Node 24、Corepack 与
`pnpm@10.28.1` 完成 frozen install 和 Next production build；`develop` PR
执行 Linux backend image 与 frontend build GitHub CI。backend image 内部复验
SDK、Runtime manifest、package-root `cli.js` 和 `plugin --help`，不调用已经失效且
试图自行建表的旧 smoke harness。20 个变更 Markdown 文件的本地相对链接
全部可解析，`git diff --check` 通过。Admin `pnpm test:run` 为 112 files /
690 tests，TypeScript 与目标 ESLint 通过。

回退时恢复上一已验证 Dream 提交与匹配 Runtime 安装并只重启操作者拥有的
Dream backend；不得覆盖已发布 npm 版本、选择 ambient CLI 或把 `0.1.9` 的
失败回执标记为 ready。Docker 与远程环境需要各自的独立构建和运行验收。
