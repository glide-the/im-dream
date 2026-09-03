<!-- [输入] MCP Apps/OpenAI Apps 官方资料、Codex 历史任务 01a06233-628d-7a83-8d66-5c3185a80613、Dream 0.1.4 与 IM 当前源码。 -->
<!-- [输出] 记录 MCP Apps 支持状态、Runtime 继承证据、能力缺口、候选方案和验证命令。 -->
<!-- [定位] `mcp-apps-integration-strategy.md` 的独立调研证据；不定义产品交互，不授权实现。 -->
<!-- [同步] 2026-09-04：保留官方 bridge 事实，移除调研稿中重复的平台接口对比。 -->

# MCP Apps 支持状态调研

> 调研日期：2026-09-03（Asia/Shanghai）
>
> 结论：Dream `0.1.4` 是普通 MCP Client，不是 MCP Apps Host。IM 当前只能传递和展示普通工具结果。

## 1. 调研对象

| 对象 | 当前版本 |
|---|---|
| Dream 源码 | `/Users/dmeck/project/ink-claude-code-dream` |
| Dream Git | `main@a1296453e463fb6e7b89917262650a60bd9a586c` |
| Dream package | `0.1.4` |
| Dream MCP SDK | `@modelcontextprotocol/sdk` `1.30.0` |
| IM 源码 | `/Users/dmeck/project/ink-dream-memory` |
| Apps SDK UI | `@openai/apps-sdk-ui` `0.2.2` |

Dream 当前工作树有未提交的 Marketplace、设计稿和兼容性测试，但没有 `src/` 或 `runtime/` 业务实现改动。本调研保留这些改动，不把文档或 characterization test 视为 Host 已实现。

## 2. 官方协议边界

MCP Apps `2026-01-26` 稳定规范和 OpenAI 当前文档规定：

- MCP Server 用 `_meta.ui.resourceUri` 把 render tool 与 UI resource 关联。
- Host 用 `resources/read` 读取 `ui://` 资源；浏览器不直接解析 `ui://`。
- MCP Apps bridge 负责 Host/View 初始化、通知、App tool call、消息和 model context。
- 普通 MCP tools 必须在没有 UI 时仍可用。
- OpenAI 专有能力放在 `window.openai`，每项单独检测。
- `@openai/apps-sdk-ui` 是可选组件库，不是 Host bridge。
- AppBridge 构造器接受已连接 MCP `Client` 或 `null`；传 `null` 时 Host 必须手工注册 `oncalltool`、`onreadresource` 等 handlers。
- `client.connect(serverTransport)` 是 Host 到 Server 的 MCP transport；`AppBridge.connect(PostMessageTransport)` 是 Host 到 View 的 iframe transport，两条连接不能混为一谈。
- 数据工具和 render tool 应分开；只有 render tool 关联 UI resource。
- Web Host 的安全加载方式包括不同 origin 的 Sandbox Proxy；sandbox 是 iframe 约束，不是业务参与者。

资料：

- [Add UI to your MCP server](https://developers.openai.com/plugins/build/chatgpt-ui)
- [UI Guidelines](https://developers.openai.com/plugins/concepts/ui-guidelines#overview)
- [`window.openai` reference](https://developers.openai.com/plugins/reference)
- [Apps SDK UI](https://openai.github.io/apps-sdk-ui/)
- [MCP Apps 2026-01-26 stable specification（ext-apps v1.7.5）](https://github.com/modelcontextprotocol/ext-apps/blob/v1.7.5/specification/2026-01-26/apps.mdx)
- [MCP Apps overview](https://modelcontextprotocol.io/extensions/apps/overview)
- [ext-apps v1.7.5 AppBridge constructor/manual example](https://github.com/modelcontextprotocol/ext-apps/blob/v1.7.5/src/app-bridge.ts#L355-L417)
- [ext-apps v1.7.5 AppBridge connect/automatic forwarding](https://github.com/modelcontextprotocol/ext-apps/blob/v1.7.5/src/app-bridge.ts#L1792-L1925)
- [ext-apps v1.7.5 browser basic host](https://github.com/modelcontextprotocol/ext-apps/blob/v1.7.5/examples/basic-host/src/implementation.ts#L251-L276)

`@openai/apps-sdk-ui@0.2.2` package 只导出 CSS、components、hooks、theme 和 helpers。peer dependencies 是 React 18/19 与 Tailwind 4；没有 transport、MCP Client 或 AppBridge export。

`@modelcontextprotocol/ext-apps@1.7.5` 的 `AppBridge` 构造器类型是 `Client | null`。传已初始化 Client 时会自动转发 Server-bound tools/resources/prompts；传 `null` 时 Host 注册 manual handlers。官方 basic host 也证明 Browser Client 可以连接浏览器可达的 Streamable HTTP/SSE，因此“IM Browser 不直连”是本设计的安全策略，不是 SDK 限制。

## 3. Dream 支持状态

| 源码 | 当前行为 | 缺口 |
|---|---|---|
| `/Users/dmeck/project/ink-claude-code-dream/src/cleanroom/mcp/registry.ts:630-633` | MCP Client capabilities 为 `{}` | 没有 Apps capability negotiation |
| 同文件 `:732-750` | 模型工具只投影 name、description、input schema | 不处理 Apps tool visibility 和 UI metadata |
| 同文件 `:753-800` | 支持普通 `tools/call`、`resources/list`、`resources/read` | 能读 resource，但不会建立 App UI |
| `/Users/dmeck/project/ink-claude-code-dream/src/cleanroom/protocol.ts:990-1017` | MCP tool result 被 `JSON.stringify` 后写入普通 `tool_result` | `content`、`structuredContent`、`_meta` 没有独立可见性 |
| 同文件 `:131-155` | `safeMcpEntries` 不保留 tool/resource `_meta` | Host 无法获得 UI 关联信息 |
| `/Users/dmeck/project/ink-claude-code-dream/runtime/core-prune-profile.json:278-284` | `MCP_RICH_OUTPUT` disabled | 当前发行物未包含交互式 MCP rendering |
| `/Users/dmeck/project/ink-claude-code-dream/tests/mcp-apps-compatibility.test.mjs:44-133` | 当前 characterization test 验证 resource/result 元数据可读，但 capabilities 为 `{}`、app-only tool 仍投给模型 | 明确证明普通 MCP 兼容不等于 Apps Host |

Dream 已具备可复用能力：

- MCP Server 配置和连接；
- tool discovery 与调用；
- resource 直接读取；
- PreToolUse、PostToolUse、permission 和 cancel；
- typed stream、assistant/tool result、session transcript 与 resume。

缺少的是 Apps Host 结果分流、UI resource 处理和 App 双向动作，不是重新实现 MCP transport。

## 4. Claude Agent Runtime 继承证据

IM 当前 Runtime 生命周期：

| Runtime 阶段 | 当前入口 | 行为 |
|---|---|---|
| Phase 1：Context Assembly | `/Users/dmeck/project/ink-dream-memory/backend/claude_agent/service.py:1326-1944` | 加载 actor/thread、managed MCP snapshot、workspace、resume，生成 `AgentRunOptions` |
| Phase 2：Runner Creation | `/Users/dmeck/project/ink-dream-memory/backend/claude_agent/thread_factory.py:460-481` | 创建或复用 `ClaudeAgentRunner` |
| Phase 3：Session Start | `/Users/dmeck/project/ink-dream-memory/backend/claude_agent/service.py:1947-2090` | 驱动 runner、发 EventBus/SSE、保存 user/assistant/tool parts |
| Phase 4：Session End | `/Users/dmeck/project/ink-dream-memory/backend/claude_agent/thread_factory.py:597-620` 及 close/TTL 路径 | 清理 Runtime State；Chat 历史保留 |

Runtime 对 MCP 的现有继承链：

1. `service.py:1601-1610` 从 managed MCP loader 取得 Server snapshot。
2. `service.py:1765-1815` 写入 `AgentRunOptions.claude_mcp_servers` 和可信 actor/thread 环境。
3. `agent_runner.py:3400-3455` 合并内部和远程 MCP Server 配置。
4. `agent_runner.py:3457-3495` 创建 `ClaudeAgentOptions`，继续使用现有 PreToolUse/PostToolUse/can_use_tool。
5. `agent_runner.py:3570-3675` 从 SDK `query_stream` 接收消息。
6. `agent_runner.py:4250-4290` 把 `tool_result` 转成 `ToolEventPayload`。
7. `service.py:2791-2863` 把它变成 `tool-output-available`。
8. `service.py:3094-3159` 把工具结果保存成 `tool-invocation` part。
9. `frontend/src/lib/claude-agent-transport.ts:320-422` 转成 AI SDK UIMessage chunk。
10. `frontend/src/components/chat/ToolMessagePart.tsx:168-215` 展示普通工具卡片。

### Runtime 不负责 turn 结束后的页面交互

`/Users/dmeck/project/ink-dream-memory/backend/libs/claude_agent_kit/server/simple_cas_client.py:61-79` 在每次 `query_stream` 内使用：

```python
async with ClaudeSDKClient(options=effective_options) as client:
    await client.query(prompt)
    async for message in client.receive_response():
        yield message
```

`receive_response()` 结束后 `ClaudeSDKClient` 和它内部的 Dream Runtime 进程退出。`AgentRunState.runner` 虽然按 Thread 复用，但 Runner 不是持续 MCP connection。

因此：

- 首次模型 tool call 可以完全走 Claude Agent Runtime；
- UI 显示后发起的 `tools/call` 不能假设原 Runtime/MCP session 仍存在；
- IM Web 首期决定不把 AppBridge 官方自动转发示例中的 MCP `Client` 放进浏览器；浏览器直连 Streamable HTTP/SSE 在网络与安全条件满足时技术上可行，并非规范禁止；
- 后续 App tool call 需要由 Node `PersistentConnectorManager` 持有独立 MCP session 并执行；
- `sendFollowUpMessage` 才重新进入正常 Claude Agent turn。

## 5. IM 支持状态

| 源码 | 当前行为 | 缺口 |
|---|---|---|
| `/Users/dmeck/project/ink-dream-memory/backend/claude_agent/service.py:2791-2863` | 只发送 generic tool input/output | 没有 Agent UI event |
| 同文件 `:3094-3159` | 只持久化 text、reasoning、tool invocation | 没有 Tool UI metadata 与 App instance 绑定 |
| `/Users/dmeck/project/ink-dream-memory/frontend/src/lib/claude-agent-transport.ts:121-151,320-422` | Backend event 只定义普通 tool result | 不能识别 MCP App |
| `/Users/dmeck/project/ink-dream-memory/frontend/src/components/chat/ChatMessageList.tsx:580-680` | 工具结果进入普通 `ToolMessagePart` | 没有 Agent UI surface |
| `/Users/dmeck/project/ink-dream-memory/frontend/package.json:26,49`、`/Users/dmeck/project/ink-dream-memory/frontend/vite.config.ts:120-155` | React `19.1.0`、Vite `8.1.5`，输出普通 SPA bundle | 构建器可承载 Host 插件，但 `frontend/src` 尚无 App iframe/bridge |
| `/Users/dmeck/project/ink-dream-memory/backend/claude_mcp/inventory.py:203-301,630-670` | MCP discovery 使用 request-local `ClientSession` | 不能向 Node 同步现有 socket，也不能支撑 turn 后页面交互 |
| `/Users/dmeck/project/ink-dream-memory/backend/claude_mcp/runtime_snapshot.py:51-185` | 每个 turn 在 Python 内存生成包含明文 transport/credential 的 detached config，但丢弃 server/config/credential revision | 可抽出配置解析逻辑；现有返回值不能直接作为 Node 接口 |
| `/Users/dmeck/project/ink-dream-memory/frontend/src/api/claudeMcpApi.ts:158-169` | Browser 用 IM bearer/cookie 访问 Python API | 当前只有用户→Python 登录态，没有 Browser→Node instance ticket |

Vite 可以构建 IM Shell、iframe controller 和 AppBridge。Web bundle 不能启动 stdio；用户电脑 localhost HTTP 在 CORS、secure context、mixed content、PNA 和认证均允许时技术上可能可达。IM 首期规定 AppBridge 传 `null` 并注册手动 handlers，Browser 只连接 Node，物理 MCP 连接由 Node `PersistentConnectorManager` 持有。`@openai/apps-sdk-ui` 只可能成为某个 View bundle 的依赖。

### 5.1 Managed MCP snapshot loader 不落盘，也不是 Connector

- `/Users/dmeck/project/ink-dream-memory/backend/claude_mcp/service.py:473-475` 的 `get_default_managed_mcp_runtime_snapshot_loader()` 只返回 Python 进程内 singleton 上的 loader。
- `/Users/dmeck/project/ink-dream-memory/backend/claude_mcp/runtime_snapshot.py:1-6` 明确声明这是 in-memory projection，不写文件、不持有 MCP 连接。
- `/Users/dmeck/project/ink-dream-memory/backend/claude_mcp/runtime_snapshot.py:71-102` 每次按 actor/workspace 生成配置；`:136-182` 将 OAuth/header/stdio secret 解密后写入返回 dict。
- `/Users/dmeck/project/ink-dream-memory/backend/claude_mcp/repository.py:54-124` 的原始记录包含 server id、config revision、credential revision 和 credential reference，但 loader 返回值不保留这些 Link 校验字段。
- `/Users/dmeck/project/ink-dream-memory/backend/libs/claude_agent_kit/server/agent_runner.py:409-457` 才将配置写入 `{thread}/.claude-tmp/mcp-config/mcp_*.json`，权限为 `0600`；`:3581-3598` 在 query 前使用，`:3816-3825` 在 turn 结束时删除。
- `/Users/dmeck/project/ink-dream-memory/backend/tests/test_claude_mcp_runtime_snapshot.py:65-90` 对比临时目录 before/after，并验证 loader 返回 Bearer header，证明 loader 本身不落盘。
- `/Users/dmeck/project/ink-dream-memory/backend/libs/claude_agent_kit/server/simple_cas_client.py:57-77` 每次 query 都进入并退出 `ClaudeSDKClient` context；loader 与 service 不持有物理 session。
- `/Users/dmeck/project/ink-dream-memory/backend/claude_mcp/inventory.py:203-301` 的 `McpSdkSessionFactory.open()` 同样是 request-local context。

现有 `/api/claude-mcp/servers` 只返回安全 Server DTO，没有解密 credential、resolved stdio launch config 或 effective workspace override；它也不是 Node service-to-service 接口。当前源码不存在 Node 可调用的配置接口。

目标设计应抽出两种受控投影：

1. 非敏感、带 revision 的有效静态配置；
2. 单 Server、短时、绑定 actor/workspace/server/revisions 和 Node runtime identity 的明文 turn-scoped 配置。

RuntimeSnapshotLoader 继续服务 Claude Agent turn；Node `PersistentConnectorManager` 消费静态配置和 turn-scoped 明文配置，自行建立并持有 MCP session、tool catalog 和 UI resource。明文配置只在 Node 建连内存中使用，不写磁盘、不进入 Browser/日志；重连重新获取。Python 只提供配置，不参与 Apps tool/resource 或 UI 消息。

若目标 MCP Server 依赖 connection-scoped state，Claude Agent session 与 Node session 不一定共享状态。当前源码没有共用连接机制，因此首期必须验证 Server 无连接私有状态或使用共享外部状态；共用连接需单独设计，不能把 Python SDK socket 交给 Node。

## 6. 历史任务

已读取 Codex 任务 `01a06233-628d-7a83-8d66-5c3185a80613`。

| 项目 | 历史任务结果 | 当前复核 |
|---|---|---|
| 环境 | ext-apps npm `1.7.5`、Node `24.13.0`、Claude Code `2.1.220`、Runtime `0.1.4` | Runtime package 仍为 `0.1.4` |
| 可用能力 | 普通 result、structured content、result `_meta`、error、`ui://` resource read | 当前代码仍有普通 tool/resource 能力 |
| 缺口 | capabilities `{}`、app-only tool 暴露、无 UI Host 与双向交互 | 当前源码一致 |
| 未完成 | 没有真实 IM 浏览器闭环；历史记录没有 Dream git SHA | 仍需 PoC |

## 7. 能力差距

| 能力 | 当前状态 | 需要补齐的位置 |
|---|---|---|
| Apps capability negotiation | Dream capabilities `{}` | Node `PersistentConnectorManager` |
| Apps tool visibility | 所有 MCP tools 都可能给模型 | Host 按 `model` / `app` visibility 分流 |
| UI resource 关联 | Tool metadata 被普通投影丢弃；CallToolResult 本身不是 URI 来源 | Apps-aware Tool UI 目录 + server/tool/result 关联合同 |
| UI resource 读取 | Runtime 能读取但 session 随 turn 结束 | Node `PersistentConnectorManager` |
| tool result 双投影 | 无 | CallToolResult 保留模型数据与 fallback，并关联 Tool UI metadata |
| Agent UI surface | 无 | Chat 工具结果挂载点 |
| UI persistence | 无 | 复用现有消息 JSON；具体字段待 PoC，不改 schema |
| AppBridge | 无 | Browser Runtime，使用 `client = null` 和手动 handlers |
| iframe/WebView 容器 | 无 | Browser Runtime + 不同 origin 的 Web iframe 隔离 |
| CSP/origin/network 权限 | 无 Apps 页面策略 | Browser Host 按 UI resource metadata 和 IM policy 收紧 |
| Host → App input/result/context | 无 | Browser AppBridge 标准 notifications/Host context |
| App → Host 消息 | 无 | Browser manual handlers → Node Host |
| App instance/事件 | 无 | Node Apps Host |
| 后端可达 MCP 持久连接 | 只有 Python request-local session | Node `PersistentConnectorManager`；必须与 Server 网络/locality 匹配 |
| Agent worker 本地 MCP | 无持久连接 | Node 必须与 worker 共址；否则另行设计该 locality 的运行时 |
| 用户设备本地 MCP Connector | 无 | Device Connector；网页只能条件性覆盖 localhost HTTP 子集 |
| App `tools/call` | 无 | Browser handler → Node Host policy → Node MCP session |
| follow-up/model context | 无 | 转成新 user turn / 下一 turn 受控上下文 |
| display mode/theme/size | 无 | 前端 Host context |
| loading/error/timeout/cancel/reconnect | 只有普通 Agent tool 状态 | Node instance/generation + Browser 状态机 |
| 多 App/多会话隔离 | 无 | Node 按 actor/thread/server/instance/epoch 隔离 |
| 插件启停、升级、卸载 | 现有插件机制未承载 Apps Host | Node/Browser 同版本 manifest、feature flag、teardown 和 fallback |
| 协议/SDK 版本兼容 | 无 | manifest 范围 + capability negotiation；不兼容 fail closed |
| fallback | 普通结果存在但未与 UI 绑定 | 同一工具结果的普通展示 |
| UI instance lifecycle | 无 | 前端按 thread + toolCall + instance 隔离 |
| audit/日志/诊断 | 只有 tool trace | Node 增加 instance/request/generation correlation，统一脱敏 |

## 8. 方案比较记录

| 方案 | 主要问题 | 判断 |
|---|---|---|
| Dream Runtime 内实现全部 Host | 把浏览器页面生命周期耦合进模型执行 | 不选 |
| AppBridge 自动转发，Browser 创建 MCP Client | 只能覆盖浏览器可达 HTTP，不能启动 stdio，并把 transport/credential/reconnect 放入浏览器 | IM Web 首期不选；非规范禁止 |
| Node Apps Host + Browser AppBridge 插件 | Node 持有 MCP session、resource、instance 和事件；Browser 用手动 handlers | 推荐 |
| 独立 Bridge/Gateway | 增加单独身份、session、部署和追踪边界 | 仅在多 Host 复用或跨网络聚合成为独立需求时考虑；不是 Apps 前提 |
| 直接复用第三方 bridge | 权限、生命周期和版本边界无法直接视为 IM 合同 | 只作实现参考 |
| 只保留普通 fallback | 无交互 UI | 只作降级 |

## 9. 待验证项

1. 产品所说的“本地 MCP”是 IM 后端本地、Agent worker 本地，还是用户设备本地。
2. Node 是否与目标后端/worker stdio 或 localhost MCP 处于同一可达位置。
3. 用户设备本地 MCP 是否属于本期范围；纯网站 + 云端 Node 无法启动用户设备 stdio。
4. Python 配置接口如何输出有效静态配置和单 Server turn-scoped 明文配置，同时保留精确 revisions、最小化 secret 并验证 Node 服务身份。
5. UI resource 缓存与失效依据。
6. Web Host 的独立 Sandbox Proxy origin 如何随 IM 发布。
7. Node Host 权限策略如何继承当前用户、Thread 和 MCP tool 可见性，不让 App 自报身份。
8. IM 平台扩展如何在跨 origin View 内提供，并满足 CSP、完整性和消息校验要求。

## 10. 验证命令

| 命令 | 退出码 | 关键输出 |
|---|---:|---|
| `git -C /Users/dmeck/project/ink-claude-code-dream rev-parse HEAD` | 0 | `a1296453e463fb6e7b89917262650a60bd9a586c` |
| `node -p "require('/Users/dmeck/project/ink-claude-code-dream/package.json').version"` | 0 | `0.1.4` |
| `rg -n 'AppBridge|ui/initialize|window\\.openai' .../ink-claude-code-dream/src .../runtime` | 1 | 无 Apps Host 实现命中 |
| `node --test tests/mcp-apps-compatibility.test.mjs`（Dream） | 0 | `2` tests passed；测试名称明确为“reads an MCP App resource but does not negotiate the Apps UI extension” |
| `npm view @modelcontextprotocol/ext-apps version dist-tags.latest --json` | 0 | 当前 latest 为 `1.7.5` |
| `rg -n 'AppBridge|ui/initialize|...|postMessage|<iframe' frontend/src backend/claude_agent`（IM） | 1 | 产品前端和 Agent 后端没有 Apps Host/iframe bridge 命中 |
| `rg -n 'get_default_managed_mcp_runtime_snapshot_loader|class ManagedMcpRuntimeSnapshotLoader|async def load' backend/claude_mcp backend/claude_agent` | 0 | 命中 service provider、loader 与 Agent `assemble_context` 调用链 |
| `../.venv/bin/python -m pytest tests/test_claude_mcp_runtime_snapshot.py -q` | 0 | `6 passed`；包含 loader 不写临时目录、明文只在返回 snapshot 的断言 |
| `npm view @openai/apps-sdk-ui version repository.url homepage --json` | 0 | `0.2.2`，官方仓库 `openai/apps-sdk-ui` |
| `npm pack @openai/apps-sdk-ui` 并检查 package exports | 0 | 无 bridge/transport export；React 18/19、Tailwind 4 |
| `rg -n '"react"|"tailwindcss"' frontend/package.json` | 0 | React `19.1.0`；无 Tailwind dependency |
| 本地 Markdown link 检查 | 0 | `8` files，`8` local links，`0` broken |
| Playwright + 本机 Chrome 执行 `mermaid.parse()` | 0 | `15` Mermaid blocks，`0` failures |
| `git diff --check` | 0 | 无 whitespace error |
