<!-- [输入] Dream 当前 SDK/Runtime resolver、SDK main、原始模块 Runtime manifest、五包制品和真实业务回执。 -->
<!-- [输出] 记录自有 Python SDK 与原始模块 Runtime 的接口配对、问题修复、发布门和回滚合同。 -->
<!-- [定位] Dream 当前 SDK × Runtime 兼容性真相源；历史官方/恢复源码组合只作回归背景。 -->
<!-- [同步] 2026-08-30：更新为 SDK 0.2.144 × Runtime 0.1.4 正式 registry 配对、Notion Bash sandbox、workflow 回执和 fresh install。 -->
<!-- [同步] 2026-08-25：兼容合同限定为 Agent 执行面；MCP Resources 管理面不再解析或启动 CLI。 -->
<!-- [同步] 2026-09-13：当前配对为 SDK 0.2.145 × 已发布 Runtime 0.1.9；按通用产品设计原则同步发布状态、模块职责和验收边界。 -->

# Claude Agent SDK 与原始模块 Runtime 兼容性报告

> 当前结论：Dream 继续通过上游公共 `cli_path` 接口使用自有 SDK distribution；0.1.9 Runtime 实际编译原始模块，不需要在 Dream 中复制 Claude Agent、MCP 或 transport 状态机。不同版本的测试和发布回执不能替代当前制品验证。

## 背景、目标与概念规则

Dream 需要独立发布的 SDK 和 Runtime 支持既有 Chat、工具审批、Notion 与历史续聊。目标是维持公共 `cli_path`、JSONL 和业务数据合同，而不是复制 SDK 或新增执行框架。默认版本由依赖文件和 resolver 固定；用户请求表达运行意图，实际采用由安装制品校验与进程启动回执证明。失败保留当前已验证安装，不自动回退到未校验 CLI。各层影响与完整业务验收见下文。

## 1. 当前配对

| 层 | 当前身份 | 兼容合同 |
| --- | --- | --- |
| Python distribution | `ink-claude-dream-agent-sdk==0.2.145` | 唯一提供 `claude_agent_sdk` import |
| SDK PyPI 固定 | `ink-claude-dream-agent-sdk==0.2.145` | Dream 精确版本；`uv.lock`/`requirements.txt` 固定 wheel/sdist SHA-256，Docker 强制 `--require-hashes` |
| SDK 源码/发布身份 | `0.2.145` distribution metadata + checked archive hashes | 发布来源由 SDK 仓库维护；Dream 不用 import 目录猜包身份 |
| SDK 上游源码 | commit `542fefb3b94be87760b2513fff889b91bb5b6672` | 上游 tree `1c86f3a…` 为 API 基线；下游仅 `_version.py` 记录 distribution 版本 `0.2.145`，其余源文件保持一致 |
| SDK → CLI 注入 | `ClaudeAgentOptions.cli_path` | 复用上游 transport/process launcher |
| Runtime npm selector | source contract `@glide-the/ink-claude-code-dream@0.1.9` | package-root `cli.js` 选择 darwin/linux × arm64/x64 平台包；manifest 配对 SDK `0.2.145` |
| Runtime release state | `0.1.9` 已发布 | 同 SHA 四平台资格、五包公开归档 integrity、全新安装和本机 Dream 启动身份均有回执，见当前发布/接入记录 |
| Runtime 对外版本 | `2.1.241 (Claude Code)` | Dream 所需 argv/JSONL/management 兼容标识，不是官方全产品声明 |
| Runtime 实现 | 原始模块 `src`，入口 `src/entrypoints/cli.tsx` | 默认构建实际编译它；headless/MCP 兼容变换在构建层，不维护第二套运行实现 |
| Runtime 原始源码结构 | 唯一 `src`，1,902 文件/35 模块目录 | 原始目录/模块/内容/权限摘要不变；重复 `restored-src` 删除，provenance 保留；Anthropic 版权不改 |
| Runtime 编译器 | Bun `1.4.0` | 四个 native standalone 已分别通过同 SHA 资格；每次升级仍须验证对应宿主和制品，不能复用其他版本结论 |
| official 回滚 | Docker `2.1.241` | 仅绝对 `CLAUDE_CODE_CLI_PATH` 显式选择 |

SDK 的 distribution 名改变，公共 Python namespace 不改变。因此 `.venv/.../site-packages/claude_agent_sdk` 是正确安装路径；判断实际包来源应读取 distribution metadata，而不是根据 import 目录名猜测。

## 2. 启动与 fail-closed

Dream 启动门验证：

1. distribution 名和版本精确为自有 SDK；
2. official `claude-agent-sdk` 不并存；
3. 公共 API 与 message types 完整；
4. 默认 Runtime 的 manifest、capabilities、checksum 和 executable 可用；
5. 不合格时抛出 Runtime unavailable，不回退 bundled/ambient CLI。

Runtime 解析顺序：调用方 `cli_path` → 绝对 `CLAUDE_CODE_CLI_PATH` → PATH 自有 selector → fail closed。该顺序仅适用于 Agent turn；MCP Resources management 已迁移到 Dream PostgreSQL 与标准 MCP SDK，不解析或启动 CLI。Agent turn 的 `mcp_servers` 由同一数据库事实来源生成，避免出现第二份配置。

## 3. 必须保持的接口

| 接口 | SDK 侧 | Runtime 侧 | Dream 影响 |
| --- | --- | --- | --- |
| argv/env/cwd | options serialization | 参数解析和路径校验 | Workspace、sandbox、模型/Gateway |
| JSONL streaming | typed message parser | system/assistant/stream/result frames | 首 Token、SSE、持久化 |
| 双向 control | request/response transport | permission、hook、interrupt | 工具确认和 cancel |
| session/resume | `resume` option | transcript/session store | 同 Thread 多轮 |
| tools | SDK tool/result types | Provider/tool loop | 文件、Bash、MCP、Skill |
| MCP | `mcp_servers`、status | stdio/HTTP/OAuth/Resources | Resources 与 Agent turn |
| extensions | plugin dirs、hooks | plugin/Skill/hook loader | Deck 扩展和 artifact |
| errors | SDK exceptions | 安全 DTO、exit semantics | UI 终态和诊断 |

## 4. Dream 分发能力边界

npm Runtime 门要求 14 项 Dream 发布能力；local-core 有单独 13 项 portable baseline。当前 `0.1.9` 的通过状态见发布回执；以下能力是每次升级都必须验证的合同，不能因其他版本通过而省略：

- `protocol.streaming`
- `protocol.control.bidirectional`
- `session.resume`
- `transcript.jsonl`
- `workspace.cwd`
- `tmpdir.thread-local`
- `sandbox`
- `sandbox.notion-cli`
- `mcp.stdio`
- `mcp.http`
- `mcp.oauth`
- `mcp.management.identity`
- `extensions.plugins`
- `lifecycle.cancel`

Provider streaming、tool loop、PreToolUse/permission、Gateway `apiKeyHelper` 和普通 Agent/Task 工具是上述协议/扩展能力的必需实现。原始产品模块仍保留在 src，现有 headless profile 按图证明裁剪交互/remote/team/IDE 产品面；共享依赖暂缓项不按目录名删除。

## 5. 本轮发现并修复的协议问题

### 5.1 PreToolUse allow 重复确认

旧候选在 PreToolUse 明确返回 allow 后仍调用 `can_use_tool`。Dream 的 callback 不持有原 tool id，因而产生第二个 UUID 工具卡：真实调用已经成功，但 UI 还有一个重复 pending confirmation。

当前合同：

- PreToolUse `allow`：只执行原始 tool call，不进入第二层 permission callback。
- 无决定：按正常 permission policy 继续。
- `deny`：不执行工具。

focused regression 8/8 通过；真实 Comfy 两轮各只有一个精确 `get_server_info` 工具调用和一个确认。

### 5.2 OAuth refresh token 被旧投影覆盖

旧候选 refresh 成功后只更新 Runtime 私有缓存，Dream `.credentials.json#mcpOAuth` 仍保留旧 refresh token。新 Runtime 进程无条件 hydrate 旧投影，覆盖刚旋转的 token，下一次 refresh 返回 `invalid_grant`。

当前合同：

- 私有 token 存在时禁止旧投影覆盖。
- refresh 提交完成后原子更新 Dream 投影。
- 不可恢复 `invalid_grant` 删除两处旧 token 并进入 `needs-auth`。
- discovery/DCR 超时后禁止迟到异步写重新创建凭据。

provider-free OAuth 6/6、management + OAuth 9/9 通过，并覆盖两个 Runtime 进程连续 token rotation。

### 5.3 Gateway `apiKeyHelper`

Runtime 复用 SDK `--settings` inline JSON/文件合同，安全执行 Dream server-owned `apiKeyHelper`：绝对 executable、无 shell、权限/超时/退出码/输出长度/单行 token 校验，token 仅内存 TTL 缓存且不进入日志。请求同时携带 subject bearer token 与 Gateway service header。

### 5.4 opaque 模型输出能力

旧 Runtime 无法按 alias 名称识别 `deepseek-v4-pro`，因此走 unknown 模型的 32,000 默认值，
即使认证 Admin 目录已声明 `max_output_tokens=384000`。当前 Dream 从最终选中的
`GatewayModel` 投影 server-owned `INK_CLAUDE_CODE_MODEL_MAX_OUTPUT_TOKENS`；CLI 将它作为
opaque alias 的默认值和上界，仍由统一 Messages builder 负责首轮、Tool Use、retry、resume
与 compaction 后请求。浏览器、用户 env、workspace 和 ambient parent env 均不能覆盖。

## 6. 当前发布与验证状态

SDK `0.2.145`、Runtime `0.1.9` 的精确归档摘要、同 SHA 四平台 CI、五包 registry 回下载、全新安装和本机采用见[发布与本机 Dream 接入记录](../../deploy/runtime-0.1.9-release-and-local-dream-adoption.md)。本报告定义兼容规则，执行记录保存命令、制品身份和实际结果；不把历史版本的组件数、许可证或测试数量用作当前制品结论。

selector 的 Node 范围是 `>=22 <25`，平台包包含 standalone binary，运行时不要求用户安装 Bun。Windows、musl、未知 arch 和交叉选择不满足当前平台合同，解析失败不得自动选择其他平台。

## 7. 完整业务验收与影响范围

升级前评估 SDK 公共 API、Runtime 启动、Gateway 模型请求、工具审批、MCP 连接、Notion env、历史存储及取消行为。测试覆盖正常账号的新会话、两轮续聊、SSE/持久化、普通工具、Notion 只读 CLI、MCP Apps 首次加载/按钮调用/刷新历史，以及缺配置、缺会话、拒绝审批和取消。制品 smoke 不能代替真实模型或真实 Notion 验收。

当前发布、安装和运行采用有独立回执；用户报告的真实模型/Notion 验收与 provider-free 制品测试分开记录。MCP Apps SDK 消息转换和批准调用关联的最新修复范围及正常 Chat 复验见[本机恢复记录](../../exec/mcp-apps/local-startup-recovery.md)。每份回执只证明其明确记录的版本、路径和业务范围，不扩大为所有外部服务/OAuth 或公开 App 生产启用。

## 8. 许可证与发布边界

0.1.9 的实际实现是唯一原始 `src`；重复 `restored-src` 已删除。原始源码进入构建，copyright/source-derived SBOM 如实保留；selector MIT 不重新许可这些模块。用户已确认公开 npm 来源授权，技术资格仍须对应实际制品证据。

不同制品的许可证、构建摘要与业务验收不能互相替代。SDK PyPI 和 Runtime npm 分开发布；Dream 依赖和锁固定 SDK `0.2.145` 与 Runtime `0.1.9`。当前公开归档和本机采用已验收，未来升级仍须同 SHA 资格与对应版本 registry 校验。AutoDL local-core 是独立制品，本次未部署远程环境。

完整的版本准备、可复现构建、OIDC 发布、registry smoke、Dream 锁文件更新和回滚命令见
[`docs/deploy/claude-sdk-runtime-packaging-and-integration.md`](../../deploy/claude-sdk-runtime-packaging-and-integration.md)。

## 9. 回滚与升级

回滚使用预检过的绝对 `CLAUDE_CODE_CLI_PATH`，不改变 Dream 业务代码、SDK API、Schema、Thread ID、Workspace 或 transcript 格式。

任何 SDK 或 Runtime 升级都必须原子验证：

1. SDK upstream tree 与 distribution metadata；
2. npm Runtime 的 14 项 capability、package-root entrypoint、manifest 和 checksum；AutoDL/local-core 则验证自身 nested entrypoint、13 项 portable baseline 与 qualification/checksum；
3. JSONL/permission/tool/resume/sandbox 差分；
4. MCP stdio/HTTP/OAuth/Resources/management；
5. 五包可复现、SBOM/license/no-map；
6. Dream 真实账号的新会话、两轮、SSE、tool、refresh/resume 和 Gateway 记录；
7. registry fresh install。

任一失败即保留当前内容寻址 release 和官方绝对路径回滚，不修改 Dream 业务状态机。
