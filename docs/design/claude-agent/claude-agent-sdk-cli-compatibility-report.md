<!-- [输入] Dream 当前 SDK/Runtime resolver、SDK main、clean-room Runtime manifest、五包制品和真实业务回执。 -->
<!-- [输出] 记录自有 Python SDK 与 clean-room Claude Runtime 的接口配对、问题修复、发布门和回滚合同。 -->
<!-- [定位] Dream 当前 SDK × Runtime 兼容性真相源；历史官方/恢复源码组合只作回归背景。 -->
<!-- [同步] 2026-08-30：更新为 SDK 0.2.144 × Runtime 0.1.4 正式 registry 配对、Notion Bash sandbox、workflow 回执和 fresh install。 -->
<!-- [同步] 2026-08-25：兼容合同限定为 Agent 执行面；MCP Resources 管理面不再解析或启动 CLI。 -->

# Claude Agent SDK 与 clean-room Runtime 兼容性报告

> 当前结论：Dream 已通过上游公共 `cli_path` 接口使用自有 SDK distribution 和 clean-room Runtime，不需要在 Dream 中复制 Claude Agent、MCP 或 transport 状态机。

## 1. 当前配对

| 层 | 当前身份 | 兼容合同 |
| --- | --- | --- |
| Python distribution | `ink-claude-dream-agent-sdk==0.2.144` | 唯一提供 `claude_agent_sdk` import |
| SDK PyPI 固定 | `ink-claude-dream-agent-sdk==0.2.144` | Dream 精确版本；`uv.lock`/`requirements.txt` 固定 wheel/sdist SHA-256，Docker 强制 `--require-hashes` |
| SDK 源码/发布身份 | `v0.2.144@fa10c9ef04ec006d9dcf0a88b1b35dab4ef4723b` | 不可变 tag；发布 run `32874352449` 成功 |
| SDK 上游源码 | commit `542fefb3b94be87760b2513fff889b91bb5b6672` | `src/` 与 MIT 上游 tree `1c86f3a…` 空差异 |
| SDK → CLI 注入 | `ClaudeAgentOptions.cli_path` | 复用上游 transport/process launcher |
| Runtime npm selector | `@glide-the/ink-claude-code-dream@0.1.4` | 选择 darwin/linux × arm64/x64 平台包；manifest 配对 SDK `0.2.144` |
| Runtime Git 固定 | release `main@0ebafe95db22101cf77db2c27e73b561d3af37a6` | qualification `33306855166`、publish `33306940462` 成功 |
| Runtime 对外版本 | `2.1.241 (Claude Code)` | Dream 所需 argv/JSONL/management 兼容标识，不是官方全产品声明 |
| Runtime 实现 | 仓库自有 `src/cleanroom/`，MIT | 不读取、编译或打包恢复源码和旧派生 bundle |
| Runtime 编译器 | Bun `1.4.0` | 生成四个 native standalone；运行时不依赖 ambient Bun |
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

## 4. clean-room 能力边界

Runtime manifest 精确声明 13 项 Dream 发布能力：

- `protocol.streaming`
- `protocol.control.bidirectional`
- `session.resume`
- `transcript.jsonl`
- `workspace.cwd`
- `tmpdir.thread-local`
- `sandbox`
- `mcp.stdio`
- `mcp.http`
- `mcp.oauth`
- `mcp.management.identity`
- `extensions.plugins`
- `lifecycle.cancel`

Provider streaming、tool loop、PreToolUse/permission、Gateway `apiKeyHelper` 和普通 Agent/Task 工具是上述协议/扩展能力的必需实现。Remote Control、team/swarm、IDE/TUI、voice、SSH remote、browser product tool、updater、feedback 和增强 telemetry 不在 clean-room 生产图。

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

## 6. 五包与安装

| 包 | npm registry tgz SHA-256 |
| --- | --- |
| selector | `97c4dc3ab99280073e5322efe66beab81661115ec6ac98a2930e34237ca694de` |
| darwin-arm64 | `67e414cefcb44c04785533c208dae01add482af80b7b25e572f29b671a128bed` |
| darwin-x64 | `d3b5a4a54df1a3278fc406f85f1bddf462d2c77875325afef8ef52c4f053b4a4` |
| linux-arm64 | `f88f6ae79b45d4ac8edf16cd727e0d4d862c947c9a8d098beb140e4ca6a17b02` |
| linux-x64 | `9c4bc25e2e84fca5c4014a777623d391ce31568be8ef3642a16253b81c972fad` |

selector 的 Node 支持范围是 `>=22 <25`。平台包包含 standalone binary，运行时不要求用户安装 Bun。Windows、musl、未知 arch 和交叉选择 fail closed。

所有 tarball 包含 CycloneDX 1.5 SBOM、22 个依赖组件、MIT 根许可证、依赖许可证摘要、notices、manifest 与 checksum；源、stage、tgz 和 fresh install 均拒绝 `.map`。

五包已经按四个平台包优先、selector 最后的顺序公开发布。公共 registry metadata 均为 `0.1.4`/MIT；全新安装只选择当前 Darwin ARM64 平台包，并通过两个 CLI alias、SDK/Runtime manifest 配对、`sandbox.notion-cli` 与零 `.map` 验证。表中摘要是匿名 `npm pack` 的 registry 验收文件，且本次与 qualification 五包 SHA-256 一致；publish job 下载并复验 same-SHA 制品后直接发布，没有重新构建。

## 7. 验证结果

| 验证层 | 结果 |
| --- | --- |
| SDK 完整测试 | 1500 passed，5 skipped；CI 0 fail |
| SDK registry 安装 | 正式 PyPI wheel SHA `50801104…85ca56`；全新 Python 3.12 安装/import 版本 `0.2.144`；Dream `.venv` 无 Git `direct_url.json` |
| Dream SDK/Runtime 接入 | 版本/环境/Docker/请求聚焦 `101 passed, 16 subtests passed`；唯一 distribution provider 正确 |
| Runtime 完整测试 | release CI/qualification `130 total, 125 passed, 5 conditional external-fixture skips, 0 fail` |
| Runtime lint | exit 0 |
| 四平台可复现 | 两轮 clean build，4 executables + 5 tgz + aggregate SHA256SUMS `cmp` 相同 |
| package verifier | SBOM/license/checksum/native magic/Dream manifest/no-map 全通过 |
| registry fresh install | 0.1.4 selector + darwin-arm64；两个 alias `--version`、manifest/attestation/`sandbox.notion-cli` 配对、no-map 全通过 |
| Messages 请求参数 | 最终 transport fixture 与 Dream 真实 Gateway 均证明 model/capability-bounded `max_tokens`、显式 effort 的 `output_config.effort`、未配置时省略和 `stream:true`；修复后 `deepseek-v4-pro` 首轮/resume 为 2 次 `max_tokens=384000`/effort `low` |
| 真实 IM | 真实账号、Admin/Gateway/PostgreSQL、Chrome Comfy OAuth、两轮 tool call、刷新 resume、Logout/Remove：`1 passed (2.3m)` |

## 8. 许可证与发布边界

clean-room Runtime 不是恢复源码改名包。公共构建输入只含仓库自有 MIT 源码和兼容许可证依赖；restricted-source scan 在源、Git inventory 和 tarball 中零命中。因此发布判断由该 clean-room 源、SBOM、第三方许可证和实际 registry 门决定。

恢复源码和旧派生 bundle仍只可作为本地历史研究/black-box 对比，不得进入公共包。删除 LICENSE、NOTICE 或 source map 不能改变一段受限实现的来源；本轮采用的是替换核心实现，而不是删除一个文件。

SDK PyPI 和 Runtime npm 分开授权、分开发布。SDK `0.2.144` 已由 SDK 项目通过 Trusted Publisher 先发 TestPyPI、后发正式 PyPI，并逐字节复验 wheel/sdist；Runtime `0.1.4` 由 Runtime 项目按平台包先于 selector 完成，并通过公开 registry fresh download/install 回验。本次 npm 使用仅包含五个 Runtime 包读写权、无 organization 权限的 granular token fallback；GitHub `npm` Environment 的 `NPM_TOKEN` 与 npm token 按用户要求保留，本地明文副本已清除。Dream 的 Python 依赖只指向 PyPI SDK，npm 只承载独立 CLI/Runtime；AutoDL local-core 仍是不可公开分发的独立制品。

完整的版本准备、可复现构建、OIDC 发布、registry smoke、Dream 锁文件更新和回滚命令见
[`docs/deploy/claude-sdk-runtime-packaging-and-integration.md`](../../deploy/claude-sdk-runtime-packaging-and-integration.md)。

## 9. 回滚与升级

回滚使用预检过的绝对 `CLAUDE_CODE_CLI_PATH`，不改变 Dream 业务代码、SDK API、Schema、Thread ID、Workspace 或 transcript 格式。

任何 SDK 或 Runtime 升级都必须原子验证：

1. SDK upstream tree 与 distribution metadata；
2. Runtime 13 项 capability、manifest 和 checksum；
3. JSONL/permission/tool/resume/sandbox 差分；
4. MCP stdio/HTTP/OAuth/Resources/management；
5. 五包可复现、SBOM/license/no-map；
6. Dream 真实账号的新会话、两轮、SSE、tool、refresh/resume 和 Gateway 记录；
7. registry fresh install。

任一失败即保留当前内容寻址 release 和官方绝对路径回滚，不修改 Dream 业务状态机。
