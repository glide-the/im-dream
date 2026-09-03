<!-- [输入] MCP Apps 稳定规范、@mcp-ui/client AppRenderer、IM Claude Agent/MCP 与 Next.js 目标边界。 -->
<!-- [输出] 定义 IM 接入 MCP Apps 的产品流程、最小架构、阶段与验收。 -->
<!-- [定位] MCP Apps 主设计；连接、客户端扩展、iframe 和源码证据由同目录专项文档维护。 -->
<!-- [同步] 2026-09-04：Host 渲染统一复用 AppRenderer，Browser 通过 Node 受控 MCP transport 访问上游 Server。 -->

# MCP Apps 与 IM Agent UI 设计

> 状态：设计评审稿，未实现
>
> 结论：当前 Dream 不是 MCP Apps Host。IM 采用 `@mcp-ui/client` 的 `AppRenderer`，不自建 App View renderer、iframe controller 或 AppBridge 封装；Browser MCP Client 只连接 Next Node Apps Runtime 暴露的受控 MCP transport，Node `PersistentConnectorManager` 再连接真实 MCP Server。Python 只提供 Node 建连配置，不参与页面交互。

配套文档：

- [源码与协议调研](./mcp-apps-support-research.md)
- [Node 受控 MCP Transport 与连接同步](./mcp-apps-node-runtime-bridge.md)
- [`window.im` 客户端平台扩展](./mcp-apps-client-host-communication.md)
- [`AppRenderer` iframe 交互](./mcp-apps-iframe-interaction.md)
- [Dream 前端 Next.js 迁移评估](./dream-frontend-node-framework-migration-assessment.md)

## 1. 背景与问题

Dream 当前可以让 Claude Agent Runtime 调用 MCP Server 模块提供的工具，并在 Chat 中显示普通工具结果，但没有 MCP Apps Host 的能力协商、UI resource 读取、iframe 渲染和双向交互。

MCP Server 仍是一个模块：它提供工具、资源和业务结果。支持 MCP Apps 的工具通过 descriptor 中的 `_meta.ui.resourceUri` 指向 `ui://` HTML resource；普通 `CallToolResult` 继续提供模型可见数据和无 UI 客户端的 fallback。

此前设计把资源读取、AppBridge、iframe 和 Browser/Node 消息分别实现了一遍。`AppRenderer` 已经完成这些 Host 侧职责，因此 IM 只需要提供一个连接到受控 Node MCP 端点的 Client，以及 IM 自己的权限和页面集成。

## 2. 目标与边界

### 2.1 目标

- 沿用 Claude Agent Runtime 现有的首次工具选择和 `tools/call`。
- 在已完成工具结果的位置挂载 `AppRenderer`。
- Browser 不接触真实 MCP 地址、OAuth token、headers、stdio command 或 env。
- Node 过滤并代理 Browser 发出的 MCP tools/resources 请求。
- App 页面可以继续调用同一 MCP Server 的授权工具，也可以通过 `ui/message` 请求新的 Agent turn。
- 不支持 Apps、插件关闭或页面失败时继续显示同一次普通 tool result。

### 2.2 非目标

- 不实现一套替代 `AppRenderer` 的 iframe/AppBridge runtime。
- 不新增 Session Start 阶段，不改变 Claude Agent turn、resume、cancel 或 SSE 语义。
- 不把 Python 改成 UI resource 服务、Apps session owner 或前端消息代理。
- 不新增独立 Bridge/Gateway 服务。
- 不借 Next.js 迁移重构无关 Agent、Thread、EventBus、模型调用或数据库。

## 3. 概念与规则

### 3.1 最小概念

| 概念 | 在 IM 中的含义 |
|---|---|
| MCP Server 模块 | 提供 tools、`ui://` resource 和业务结果。 |
| App resource | MCP Server 经 `resources/read` 返回的 `text/html;profile=mcp-app` 文档；HTML 可包含已打包的 JS/CSS。 |
| Browser MCP Client | 浏览器中声明 UI extension capability 的 MCP SDK Client；只连接 IM Node 受控端点，不连接真实 Server。 |
| 受控 MCP transport | Browser Client 使用的标准 Streamable HTTP transport；目标是 IM Node 的同源、已认证 MCP 端点。 |
| `PersistentConnectorManager` | Node 内的上游连接管理器；按用户、workspace 和 Server 隔离连接，并执行权限过滤和代理。 |
| `AppRenderer` | `@mcp-ui/client` 提供的 React Host 组件；负责发现/读取 App resource、创建 AppBridge、挂载隔离 iframe，并传递 tool input/result。 |
| `window.im` | App 页面可选的 IM 平台接口；兼容 `window.openai` 的字段和方法，但不替代 MCP Apps 标准 bridge。 |

`App resource` 是 Server 提供的页面内容，不是 IM 要构建的新 bundle runtime。`@openai/apps-sdk-ui` 只是 App 作者可选的页面组件库；Host 渲染复用的是 `@mcp-ui/client/AppRenderer`。

### 3.2 主链路

```mermaid
flowchart LR
    U["用户"] --> A["Claude Agent Runtime<br/>现有 tools/call"]
    A <--> S["MCP Server 模块"]
    A --> R["IM Chat 工具结果"]
    R --> AR["Next Client Component<br/>Browser Client + AppRenderer"]
    AR <-->|"标准 MCP Streamable HTTP"| N["Next Node Apps Runtime<br/>受控 MCP 端点"]
    N <--> C["PersistentConnectorManager"]
    C <--> S
    AR --> V["App 页面"]
    V --> U
```

流程只有两段：

1. Claude Agent Runtime 按现有方式调用 MCP 工具，把 tool name、input、完整 `CallToolResult` 和 tool call identity 交给 Chat。
2. Next Client Component 创建 Browser MCP Client，连接 Node 受控 MCP 端点，并把 Client 与工具数据传给 `AppRenderer`；后续 descriptor 查询、`resources/read`、iframe 和页面工具调用都沿同一 MCP Client 完成。

Browser 发起的是到 IM 网站 Node 端点的连接，不是到真实 MCP Server 的连接。真实 Server 的 URL、stdio 配置和凭证不进入 Browser：Python 是 managed MCP 配置与凭证的事实源，Node 仅在建连和使用上游连接期间以内存保存 Python 签发的短时单 Server 建连配置。

### 3.3 与 Claude Agent Runtime 的继承

```mermaid
sequenceDiagram
    actor U as 用户
    participant A as Claude Agent Runtime
    participant S as MCP Server 模块
    participant B as Browser Client + AppRenderer
    participant N as Node Apps Runtime

    U->>A: 正常 Chat 消息
    A->>S: tools/call
    S-->>A: CallToolResult
    A-->>B: 现有工具结果<br/>server、tool、call、input、result
    B->>N: Client.connect(受控 Streamable HTTP transport)
    N->>S: 建立或复用受控上游 MCP 连接
    B->>N: tools/list / resources/read(ui://...)
    N->>S: 权限过滤后代理请求
    S-->>N: Tool descriptor / App resource
    N-->>B: 标准 MCP 响应
    B->>B: AppRenderer 创建 AppBridge 和 iframe
    B-->>U: 展示可交互页面
```

继承规则：

- Session Start、工具选择和首次调用仍由 Claude Agent Runtime 负责。
- UI URI 来自 Tool descriptor，不从 `CallToolResult` 猜测。
- Chat 工具结果需要持久化 `serverRef`、上游原始 tool name、`toolCallId`、tool input 和完整 `CallToolResult`；当前工具事件只稳定提供 tool name/call/input/output，`serverRef` 与完整 MCP result envelope 是实施缺口。
- `serverRef` 只是 Browser 选择受控 Node MCP endpoint 的不可信路由参数；Node 必须根据当前 IM 登录用户和 workspace 重新验证该 Server 已启用。`toolCallId` 只关联 Chat 结果和诊断，不作为授权凭证、MCP session 标识或上游连接选择条件。
- `AppRenderer` 使用独立的 Browser MCP Client 获取 descriptor 和 resource，但不重复执行创建页面的原始工具调用。
- App 内 `tools/call` 是页面局部交互，不触发模型。
- App 发出 `ui/message` 时，IM 才把消息提交给现有 Chat ingress，开始新的 Agent turn。
- `content` / `structuredContent` 始终保留，作为模型输入和失败 fallback。

若目标 Server 把业务状态只保存在 Agent Runtime 的某条物理连接里，Browser 经 Node 建立的新 MCP session 可能看不到该状态。首期只接入不依赖连接私有状态的 Server；其他 Server 需先完成共享状态验证。

### 3.4 页面内工具调用

```mermaid
sequenceDiagram
    actor U as 用户
    participant V as App 页面
    participant AR as AppRenderer
    participant C as Browser MCP Client
    participant N as Node Apps Runtime
    participant S as MCP Server 模块

    U->>V: 点击、筛选或提交
    V->>AR: tools/call
    AR->>C: 自动转发
    C->>N: 标准 MCP 请求
    N->>N: 校验登录用户、workspace、Server 和 tool scope
    N->>S: tools/call
    S-->>N: CallToolResult
    N-->>C: 标准 MCP 响应
    C-->>AR: 调用结果
    AR-->>V: tools/call response
    V-->>U: 局部更新
```

Node 是最终权限边界。Browser 中的 capability、按钮禁用和 AppRenderer callback 只能改善体验，不能替代 Node 的授权检查。

### 3.5 状态模型

| 状态 | 进入条件 | 用户反馈 | 恢复 |
|---|---|---|---|
| `unavailable` | 客户端或工具没有 Apps 能力 | 普通 tool result | 无需恢复 |
| `disabled` | 功能开关或 Server 配置关闭 | 普通 tool result | 启用后影响后续加载 |
| `connecting` | Browser Client 连接 Node MCP 端点 | 工具结果位置显示骨架 | 失败后降级 |
| `loading` | Browser Client 建连，AppRenderer 查询 descriptor、读取 resource 并挂载 iframe | 原工具结果保持可见，App 区域显示加载状态 | `onError` 或超时后降级 |
| `ready` | App 页面已经呈现且可操作 | 展示 App；不把私有初始化回调作为前提 | 可关闭或继续操作 |
| `interacting` | 页面请求执行中 | 只在当前控件显示进行中 | 成功或失败后回到 ready |
| `degraded` | transport、resource 或 iframe 失败且有 fallback | 显示普通结果和重试 | 重新建立 Client 并重新挂载 |
| `closed` | 用户关闭、Thread 切换、登出或插件停用 | 折叠为普通结果 | 重开时新建 Client/View |

配置的 `default`、`desired`、`effective` 和 `revision` 只描述 Apps 是否可用；它们不扩展 MCP Apps wire protocol。Node 仅在配置和 credential revision 有效时接受 Browser MCP session。

## 4. 架构与职责

| 模块 | 负责 | 不负责 |
|---|---|---|
| Claude Agent Runtime | 首次工具选择、调用和结果进入 Chat | App iframe 和页面后续交互 |
| Next Client Component | 创建 Browser MCP Client、挂载 AppRenderer、loading/fallback、标准 Host callbacks | 上游凭证和真实 MCP 地址 |
| `AppRenderer` | descriptor/resource 获取、AppBridge、iframe、标准 Host/View 消息、tool input/result | IM 用户授权和上游连接配置 |
| Node Apps Runtime | 暴露受控 MCP Streamable HTTP 端点；校验身份/scope；调用 Connector | DOM、iframe、App 页面构建 |
| `PersistentConnectorManager` | 建立、复用、重连和关闭上游 MCP session；过滤 tools/resources；隐藏凭证 | 浏览器 UI 和 Agent 推理 |
| Python Config Provider | 为 Node 提供当前 Server 的受控建连配置 | Apps UI、MCP 请求转发和前端事件 |
| MCP Server 模块 | tools、resources、App HTML 和业务状态 | IM 页面、用户身份和 Thread 权限 |

## 5. 方案选型

| 方案 | 结论 | 原因 |
|---|---|---|
| 自建 iframe/AppBridge Host runtime | 拒绝 | 与 AppRenderer 的 resource、bridge、iframe 和生命周期能力重复 |
| `AppRenderer` + Browser Client 直连真实 MCP | 拒绝 | 暴露真实地址/认证，且无法统一支持 Node-local stdio/localhost Server |
| `AppRenderer` + Node 受控 MCP transport + PersistentConnectorManager | **选择** | 复用标准 Host renderer，同时把真实连接、身份和安全过滤留在 Node |
| 独立 Bridge/Gateway 服务 | 暂不引入 | 当前 Next Node 已能承担受控 MCP 端点；没有额外产品边界需求 |
| 只显示普通 tool result | 保留为 fallback | 保证不支持 Apps 或加载失败时仍可完成任务 |

AppRenderer 作为 IM Apps 插件的浏览器依赖集成；`PersistentConnectorManager` 和受控 MCP 端点是同一插件在 Node 侧的服务。插件化不改变 Dream 核心的首次工具调用，只扩展工具结果的展示分支。

## 6. 分阶段交付

| 阶段 | 范围 | 可观察验收 | 回滚 |
|---|---|---|---|
| Phase 0 | Next.js compatibility shell；一个 Node 可达的官方示例 Server；Browser Client；受控 Streamable HTTP 端点；AppRenderer | render tool 完成后出现 App；`resources/read` 经 Node；浏览器无真实 Server URL/credential；普通工具保持原样；选定的 AppRenderer 版本能执行所需 sandbox/CSP policy | 关闭 Apps flag，显示普通结果 |
| Phase 1 | 只读/低风险工具、完整 fallback、关闭/重开 | Agent turn 结束后页面仍可读；资源或 iframe 失败显示同一次结果；Thread 切换后旧页面不可调用 | 禁用 AppRenderer 挂载 |
| Phase 2 | 受控页面 `tools/call`、`ui/message`、OAuth 恢复；可选 `window.im` 兼容适配层 | 每次调用在 Node 校验当前用户/workspace/Server；拒绝不触发上游；`ui/message` 创建新 turn；未实现的兼容成员不暴露 | 回到只读 |
| Phase 3 | 多 App/多 session、版本治理、审计和插件升级 | 多用户与多 Thread 不串请求；不兼容版本 fail closed；可按 tool call 追踪；插件可独立禁用 | 回滚插件版本 |

## 7. 测试与 Go / No-Go

必须验证：

- 官方示例 App 经 Browser Client → Node transport → MCP Server 完成 initialize、tools/list、resources/read 和 iframe 初始化；
- 页面内 `tools/call` 由 AppRenderer 自动转发，但 Node 对未授权 Server/tool 拒绝且不访问上游；
- tool result 事件能提供稳定 `serverRef`、原始 tool name、`toolCallId`、input 和完整 `CallToolResult`；
- 普通工具、无 `_meta.ui.resourceUri` 的工具和不支持 Apps 的客户端只显示原结果；
- resource MIME 错误、CSP 拒绝、iframe 超时、Node 断线、上游断线和 OAuth 失效均可降级；
- Browser 请求、日志和页面中不出现上游 MCP 地址、OAuth token、headers 或 stdio env；
- Next Node 重启后 Browser 能重新连接；旧请求不能进入新页面；
- AppRenderer、MCP SDK 与 ext-apps 的版本组合通过官方 demo 和 ui-inspector 合同测试。
- 当前 `AppRenderer@7.1.1` 未通过公共 prop 暴露初始化完成回调，且其实现未应用 `SandboxConfig.permissions`；Phase 0 必须升级到已修复版本或完成上游修复验证，不能把类型声明当成已执行的安全策略。

本节 Go/No-Go 只控制 MCP Apps 阶段发布，不撤销 Next.js 迁移决策。

Go：官方示例 App 和目标首期 Server 通过上述链路；Node 端点能根据现有登录态、workspace 和经验证的 `serverRef` 选择唯一上游 Server；Browser 无凭证；sandbox/CSP policy 可验证；fallback 完整。

No-Go：必须让 Browser 取得真实 Server 地址或凭证；当前工具结果无法稳定定位上游 Server；Node 无法在请求到达上游前实施权限过滤；或目标 Server 依赖 Agent 物理连接私有状态。
