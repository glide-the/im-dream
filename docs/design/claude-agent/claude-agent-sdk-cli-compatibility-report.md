<!-- [输入] Dream 当前 SDK/Runtime resolver、SDK main、clean-room Runtime manifest、五包制品和真实业务回执。 -->
<!-- [输出] 记录自有 Python SDK 与 clean-room Claude Runtime 的接口配对、问题修复、发布门和回滚合同。 -->
<!-- [定位] Dream 当前 SDK × Runtime 兼容性真相源；历史官方/恢复源码组合只作回归背景。 -->
<!-- [同步] 2026-08-30：更新为 SDK 0.2.144 × Runtime 0.1.4 正式 registry 配对、Notion Bash sandbox、workflow 回执和 fresh install。 -->
<!-- [同步] 2026-08-25：兼容合同限定为 Agent 执行面；MCP Resources 管理面不再解析或启动 CLI。 -->
<!-- [同步] 2026-09-13：当前源码合同为 SDK 0.2.145 × 未发布 Runtime 0.1.9 package-root selector；保留 0.1.4 历史发布证据。 -->

# Claude Agent SDK 与原始模块 Runtime 兼容性报告

> 当前结论：Dream 继续通过上游公共 `cli_path` 接口使用自有 SDK distribution；0.1.9 Runtime 实际编译原始模块，不需要在 Dream 中复制 Claude Agent、MCP 或 transport 状态机。旧 clean-room 发布/业务证据只适用于原版本。

## 1. 当前配对

| 层 | 当前身份 | 兼容合同 |
| --- | --- | --- |
| Python distribution | `ink-claude-dream-agent-sdk==0.2.145` | 唯一提供 `claude_agent_sdk` import |
| SDK PyPI 固定 | `ink-claude-dream-agent-sdk==0.2.145` | Dream 精确版本；`uv.lock`/`requirements.txt` 固定 wheel/sdist SHA-256，Docker 强制 `--require-hashes` |
| SDK 源码/发布身份 | `0.2.145` distribution metadata + checked archive hashes | 发布来源由 SDK 仓库维护；Dream 不用 import 目录猜包身份 |
| SDK 上游源码 | commit `542fefb3b94be87760b2513fff889b91bb5b6672` | `src/` 与 MIT 上游 tree `1c86f3a…` 空差异 |
| SDK → CLI 注入 | `ClaudeAgentOptions.cli_path` | 复用上游 transport/process launcher |
| Runtime npm selector | source contract `@glide-the/ink-claude-code-dream@0.1.9` | package-root `cli.js` 选择 darwin/linux × arm64/x64 平台包；manifest 配对 SDK `0.2.145` |
| Runtime release state | `0.1.9` main CI release candidate | 来源授权由用户确认，本机 full qualification 通过；四 target/公开 registry 待同 SHA 证据，0.1.4 回执只属历史 |
| Runtime 对外版本 | `2.1.241 (Claude Code)` | Dream 所需 argv/JSONL/management 兼容标识，不是官方全产品声明 |
| Runtime 实现 | 原始模块 `src`，入口 `src/entrypoints/cli.tsx` | 默认构建实际编译它；headless/MCP 兼容变换在构建层，平行 `src/cleanroom` 已退出 |
| Runtime 原始源码结构 | 唯一 `src`，1,902 文件/35 模块目录 | 原始目录/模块/内容/权限摘要不变；重复 `restored-src` 删除，provenance 保留；Anthropic 版权不改 |
| Runtime 编译器 | Bun `1.4.0` | 原始模块 darwin-arm64 编译已验证；四个 native standalone 仍需分别资格化，不因旧实现通过而视为通过 |
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

npm Runtime 门要求 14 项 Dream 发布能力；local-core 有单独 13 项 portable baseline。当前原始源码候选不能因为旧实现通过就宣称这些门全部已通过：

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

## 6. 已发布 0.1.4 五包历史证据

| 包 | npm registry tgz SHA-256 |
| --- | --- |
| selector | `97c4dc3ab99280073e5322efe66beab81661115ec6ac98a2930e34237ca694de` |
| darwin-arm64 | `67e414cefcb44c04785533c208dae01add482af80b7b25e572f29b671a128bed` |
| darwin-x64 | `d3b5a4a54df1a3278fc406f85f1bddf462d2c77875325afef8ef52c4f053b4a4` |
| linux-arm64 | `f88f6ae79b45d4ac8edf16cd727e0d4d862c947c9a8d098beb140e4ca6a17b02` |
| linux-x64 | `9c4bc25e2e84fca5c4014a777623d391ce31568be8ef3642a16253b81c972fad` |

selector 的 Node 支持范围是 `>=22 <25`。平台包包含 standalone binary，运行时不要求用户安装 Bun。Windows、musl、未知 arch 和交叉选择 fail closed。

所有 tarball 包含 CycloneDX 1.5 SBOM、22 个依赖组件、MIT 根许可证、依赖许可证摘要、notices、manifest 与 checksum；源、stage、tgz 和 fresh install 均拒绝 `.map`。

这张表只记录 `0.1.4`：五包已经按四个平台包优先、selector 最后的顺序公开发布。公共 registry metadata 均为 `0.1.4`/MIT；全新安装只选择当前 Darwin ARM64 平台包，并通过两个 CLI alias、SDK/Runtime manifest 配对、`sandbox.notion-cli` 与零 `.map` 验证。它不能为 `0.1.9` 的 package-root selector 提供摘要或发布授权。

## 7. 验证结果与当前候选边界

| 验证层 | 结果 |
| --- | --- |
| SDK 完整测试 | 1500 passed，5 skipped；CI 0 fail |
| SDK registry 安装（历史） | 正式 PyPI wheel SHA `50801104…85ca56`；全新 Python 3.12 安装/import 版本 `0.2.144`；Dream `.venv` 无 Git `direct_url.json` |
| Dream SDK/Runtime 接入 | 版本/环境/Docker/请求聚焦 `101 passed, 16 subtests passed`；唯一 distribution provider 正确 |
| Runtime 完整测试 | release CI/qualification `130 total, 125 passed, 5 conditional external-fixture skips, 0 fail` |
| Runtime lint | exit 0 |
| 四平台可复现 | 两轮 clean build，4 executables + 5 tgz + aggregate SHA256SUMS `cmp` 相同 |
| package verifier | SBOM/license/checksum/native magic/Dream manifest/no-map 全通过 |
| registry fresh install | 0.1.4 selector + darwin-arm64；两个 alias `--version`、manifest/attestation/`sandbox.notion-cli` 配对、no-map 全通过 |
| 当前 0.1.9 候选 | 唯一原始 src 默认构建，本机六项 full qualification、两遍一致打包/npm smoke 已通过；四 target/公开 registry/运行采用待新证据，真实用户业务不属此 provider-free 回执 |
| Messages 请求参数 | 最终 transport fixture 与 Dream 真实 Gateway 均证明 model/capability-bounded `max_tokens`、显式 effort 的 `output_config.effort`、未配置时省略和 `stream:true`；修复后 `deepseek-v4-pro` 首轮/resume 为 2 次 `max_tokens=384000`/effort `low` |
| 真实 IM | 真实账号、Admin/Gateway/PostgreSQL、Chrome Comfy OAuth、两轮 tool call、刷新 resume、Logout/Remove：`1 passed (2.3m)` |

## 8. 许可证与发布边界

0.1.9 的实际实现是唯一 canonical 原始 src；重复 restored-src 与旧平行 cleanroom 已删除。原始源码进入构建，copyright/source-derived SBOM 如实保留；selector MIT 不重新许可这些模块。用户已确认公开 npm 来源授权，技术资格仍须对应实际制品证据。

旧 0.1.4 clean-room 源码、MIT 五包及其发布/业务/内存证据留作历史；它们不能用于资格化不同实现。删除 LICENSE、NOTICE 或 source map 不能改变原始来源。

SDK PyPI 和 Runtime npm 分开授权、分开发布。当前 Dream 依赖文件与锁固定 SDK `0.2.145`；Runtime `0.1.4` 的历史发布已通过公开 registry fresh download/install 回验。`0.1.9` 不能复用旧 workflow 或 token 回执，必须在新资格和用户授权后独立发布。Dream 的 Python 依赖只指向 PyPI SDK，npm 只承载独立 CLI/Runtime；AutoDL local-core 仍是不可公开分发的独立制品。

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
