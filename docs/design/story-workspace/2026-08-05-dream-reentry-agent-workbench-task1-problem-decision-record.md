# Dream 可恢复入口与 Dream Agent 工作台：任务一问题判定记录

> 日期：2026-08-05  
> 性质：问题判定与架构裁决；本记录不包含生产代码实现  
> 后续输入：本记录是 `design_008` 交互设计及后续实现的约束输入

## 1. 判定范围与证据口径

本轮只回答 Dream run 如何重新进入、Dream 页上下文归属、Dream Agent 消息预览、悬浮交互层边界、完整生命周期和本期边界。未修改生产代码。

证据表明，Dream 已经拥有独立发起、隐藏 Agent thread、`.dream` writer、Dream files REST 投影、页面轮询渲染和一次确认链路；但重新进入聚合入口与 Dream 专属消息适配层仍缺位：

- Dream 首页当前只有 Deck 列表和新建入口，发起成功后才跳转 `?run=`，没有既有 run 列表（`frontend/src/components/story-workspace/dream/StoryWorkspaceDreamLaunch.tsx:30-69`）。
- Dream canonical 页面路径是 `/story-workspace/dream`，现有 run deep link 是 `/story-workspace/dream?run=<run_id>`（`frontend/src/router/storyWorkspacePath.ts:20-25,142-157`）；现存 `/story-workspace/runs/:id/execution` 属于执行详情，不是 Dream 业务入口（同文件 `:31-34`）。
- 后端已有发起、单 run、Dream files 和确认端点，但没有 actor-scoped Dream run 聚合端点（`backend/routers/story_workspace.py:1152-1268`）。
- Dream files 读取已经同时校验 run 创建者、workspace owner、隐藏 thread 归属和 thread 工作目录（`backend/services/deck/story_workflow_gateway.py:195-221,735-785`）。
- `.dream` 页面仍以 Dream files REST 作为阶段内容来源并按需轮询（`frontend/src/hooks/story-workspace/useStoryWorkspaceDreamFiles.ts:192-240,297-350`）。
- Claude Agent 通用消息快照会返回持久化的全部 parts（`backend/routers/claude_agent.py:589-603`），其中持久化转换明确包含 reasoning 和工具输入/输出（`backend/claude_agent/service.py:2035-2100`），不能直接作为 Dream 用户可见合同。
- SSE reconnect 只接受当前进程内处于 running 的 thread，并完整重放 EventBus buffer（`backend/routers/claude_agent.py:624-647`；`backend/claude_agent/event_bus.py:60-70,104-166`），没有可直接交给 Dream UI 的稳定消息 cursor 合同。
- 真实验收记录中，外部 run 已写出三个 stage，但 `workflow_runs.status` 仍为 `queued`，且 writer events 和入口聚合仍缺位（`docs/design/story-workspace/2026-08-04-dream-launch-writer-integration-implementation-record.md:356-399,404-414`）。因此不能单独用遗留 run status 判定用户可见生命周期。

## 2. P1 Dream run 的重新进入机制

### 问题

用户退出、刷新、关闭浏览器或重新登录后，没有一个依赖后端持久化事实、可列出并恢复 Dream run 的稳定业务入口。

### 现状证据

- `/story-workspace` 与 `/story-workspace/dashboard` 已统一跳转 Dream 页面（`frontend/src/router/storyWorkspacePath.ts:98-108`）。
- query run deep link 会 actor-scoped 读取单 run；无权或不存在时降级回默认页面并显示提示（`frontend/src/hooks/story-workspace/useRunDeepLink.ts:38-58,119-162`）。
- Dream launch 只有发起入口，成功后写入 query run（`frontend/src/components/story-workspace/dream/StoryWorkspaceDreamLaunch.tsx:61-69`）。
- `workflow_runs` 已持久化 workspace、Deck plugin/version、preflight、隐藏 thread、创建者与创建时间，可支撑查询；当前 schema 还保留旧状态枚举，不能直接映射本期业务状态（`backend/database.py:1152-1194`）。
- 单 run 文件投影已有严格的 owner、Deck/run/thread 间接绑定与文件目录校验（`backend/services/deck/story_workflow_gateway.py:735-785`）。
- 最新真实 run 的三个 stage 已为 r1，但遗留 status 仍为 queued（`docs/design/story-workspace/2026-08-04-dream-launch-writer-integration-implementation-record.md:365-399`）。

### 根因

现有链路只提供“新建 Dream”与“已知 run ID 的单 run 恢复”，没有将 actor-scoped workflow run、preflight/Deck、隐藏 thread、Dream file revisions、确认事实和最近活动时间聚合成 Dream 入口投影。页面因而无法在不知道 run ID 时从后端发现可恢复 run。

### 可选方案

1. 仅依赖 localStorage 保存最后 run。实现简单，但无法覆盖重新登录、换浏览器、清理缓存、权限变化和多 run，否决。
2. 以 Deck 页面为唯一入口。Deck 有业务关联，但会让 Deck 页面成为 Dream 状态 owner，并使跨 Deck 的 run 选择分散，否决。
3. 保留已知 run deep link，不增加发现入口。刷新有效，但关闭后再次进入无法发现 run，否决。
4. 将 `/story-workspace/dream` 升级为 Dream 工作台首页，由后端返回 actor-scoped run 聚合；Deck 和 deep link 只作为辅助导航。该方案保持单一业务 owner，采用。

### 最终决策

唯一 canonical re-entry 入口是：

`/story-workspace/dream`

该页面同时承载“进行中的 Dream”“最近的 Dream”和“发起新的 Dream”。后端新增 actor-scoped Dream run 聚合合同，页面不得从 localStorage 重建 run/thread。

辅助入口与降级规则：

- `/story-workspace/dream?run=<run_id>` 保留为 canonical run deep link；它只选择工作台内的某个 run，不形成第二个业务页面 owner。
- 增加 `/story-workspace/runs/<run_id>` 时，只能做兼容重定向到上述 query deep link；现有 `/runs/<run_id>/execution` 保持技术执行详情语义。
- Deck 页面可提供“继续 Dream/打开 Dream”辅助入口，但必须导航回 canonical Dream 工作台；Deck 页不自行保存或推导 Dream 状态。
- deep link 无权、run 不存在或 run/Deck 绑定不一致时按 404 式不可见处理，回到工作台列表并给出安全提示；不能泄露其他用户是否拥有该 run。

用户可见生命周期不得直接照搬遗留 `workflow_runs.status`，应从持久事实投影：

- `generating`：必需 stage 尚未齐备；显示“Dream Agent 正在创作”。进程内 live status 只增强“正在输出”，不承担恢复真相。
- `waiting_confirmation`：characters/scenes/storyboards 已齐备且 confirmation 未 accepted；显示“等待你修改并确认”。
- `continuing`：confirmation 已 accepted，且 continuation 尚未 dispatched 或同一隐藏 thread 正在产生后续可见输出；显示“Dream Agent 正在继续”。未 accepted 的 initial live turn 始终归 `generating`。
- `recent`：confirmation 已 dispatched 且当前没有 live turn；显示“最近的 Dream”。这不是归档状态，run 仍可再次打开。

多个 run 的选择规则：

1. 先分组展示 `generating`、`waiting_confirmation`、`continuing`，再展示 `recent`。
2. 组内按 durable `last_activity_at` 降序，再按 `created_at`、`run_id` 稳定排序。
3. `last_activity_at` 由后端聚合 thread 更新时间、stage 文件时间/修订和 run 创建时间；浏览器不自行拼接。
4. 没有 query 且只有一个进行中 run 时突出“继续”，但仍保留列表；有多个时不得静默猜选，用户明确选择。
5. 带 run query 时只打开经 actor/Deck/thread 校验的目标 run。

聚合端点建议为 `GET /api/story-workspace/dream-runs`，可选 `deckPluginId` 只做 actor-scoped 服务端过滤。每一项至少包含安全展示所需的 run ID、Deck 标识/名称/锁定版本、workflow 展示名、stage revisions、确认事实、投影 lifecycle、last activity、canonical href；不得返回本地绝对路径、凭证或原始 Agent metadata。

### 影响范围

Story Workspace 后端合同与 gateway、Dream 首页、router/deep-link、Deck 辅助入口、Dream run 列表测试、权限与多 run 测试。

### 验收方式

- 离开、刷新、关闭浏览器和重新登录后，`/story-workspace/dream` 通过服务端事实找到相同 run。
- 外部用户、错误 Deck 或篡改 run/thread 绑定均不可访问。
- 多 run 分组、排序与显式选择符合上述唯一规则。
- 检查 Network/源码，run/thread 恢复不读取 localStorage。

## 3. P2 WorkflowContextBar 的迁移

### 问题

全局 layout 顶部当前拥有 WorkflowContextBar，而 Dream 页内部只有一句活动文案；Deck/run/workflow/status 因而与 Dream Agent 交互割裂，也容易在新增右侧区域后形成双 owner。

### 现状证据

- `StoryWorkspaceLayout` 无条件在页面顶部挂载 WorkflowContextBar（`frontend/src/components/story-workspace/StoryWorkspaceLayout.tsx:23,71-75`）。
- WorkflowContextBar 同时显示 workflow/Deck/run/runtime facts，并拥有开始、取消、重试、审核等旧控制（`frontend/src/components/story-workspace/workflow/WorkflowContextBar.tsx:18-35,55-109`）。
- Dream 页面 masthead 右侧当前只显示 `activity`，无消息或上下文（`frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx:290-299`）；默认文案是“读取 Agent 工作空间”（同文件 `:131`）。
- Dream 页面右侧还承担内容编辑，不能为了 Agent 区域移除编辑能力（同文件 `:390-477`）。

### 根因

WorkflowContextBar 是早期跨页面 run shell；Dream 成为独立 surface 后，Dream Agent 上下文仍留在全局 header，而 Dream 页自己的右侧区域没有统一 view model。若简单复制信息，会出现 layout 和 Dream page 两份 owner 及生命周期漂移。

### 可选方案

1. 保留顶部完整条并在右侧复制。信息重复、状态易漂移，否决。
2. 把整个旧组件搬入右侧。会带入本期禁止的取消、重试、驳回等旧控制，且组件结构不适合消息预览，否决。
3. Dream route 不再挂载旧 WorkflowContextBar；Dream 页以一个 Dream 专属 view model 驱动右侧 Agent 区域，非 Dream route 可继续使用缩减后的全局条。采用。

### 最终决策

- Dream route 从 `StoryWorkspaceLayout` 的顶部 workflow slot 移除完整 WorkflowContextBar。全局顶部只保留产品导航、页面标题/面包屑等全局导航信息。
- 不复用旧组件作为 Dream owner；新增 `StoryWorkspaceDreamAgentRail`（暂定代码名）和唯一 `StoryWorkspaceDreamAgentViewModel`。
- 右侧保留既有内容编辑，在编辑区上方新增轻量 Agent context/preview 区；桌面端形成同一右栏内的“Agent 状态与消息预览 → 当前 stage 编辑”，不是两张重卡片。
- 信息层级：
  1. 第一层：Deck 名称、workflow 展示名、锁定版本；
  2. 第二层：Dream Agent 用户可见状态与最近回复；
  3. 第三层：当前阶段、stage revisions、缩短的 run ID；
  4. 展开技术详情：完整 run ID、必要 runtime snapshot/lock 标识。默认不占据主视觉。
- 不显示“取消/重试/驳回/归档”；不把隐藏 Agent thread 表述为 Chat 产品概念。thread ID 仅允许出现在开发诊断或验收证据。

各阶段右侧主文案：

- waiting/loading：`正在恢复 Dream 工作台…`
- generating/streaming：`Dream Agent 正在创作`，下方显示安全的实时回复预览。
- stage written：`{阶段} 已更新至 r{revision}`；内容本身仍由 Dream files REST 刷新。
- waiting confirmation：`等待你修改并确认`。
- continuing：`Dream Agent 正在根据已确认内容继续`。
- recent/idle：`Dream Agent 已完成本轮输出`，允许重新打开消息历史继续对话。

### 影响范围

StoryWorkspaceLayout 的 Dream route 组合、Dream page 右栏、旧 WorkflowContextBar 的非 Dream 使用边界、响应式布局和集成测试。

### 验收方式

- Dream 页面不存在顶部/右侧重复 Deck、run、status owner。
- 状态切换由单一 Dream view model 驱动。
- 编辑区仍可用；Agent 区没有旧业务失败/重试/驳回/归档按钮。

## 4. P3 Claude Agent 实时消息预览

### 问题

Dream 需要持久快照和实时增量，但通用 Claude Agent API 会暴露全部消息 parts 和原始事件，且 reconnect 只针对当前 running session，无法直接满足安全、去重和恢复合同。

### 现状证据

- 通用快照校验 thread owner 后返回全部持久化 messages（`backend/routers/claude_agent.py:589-603`）。
- 持久化 parts 含 text、reasoning、tool invocation input/output（`backend/claude_agent/service.py:2035-2100`）。
- 成功 turn 会先发 `message-final`，再持久化 assistant，最后发 finish（同文件 `:1379-1406`）。
- EventBus 订阅会重放全部 buffer 再接 live event（`backend/claude_agent/event_bus.py:60-70,104-166`），现有 endpoint 没有 Last-Event-ID/cursor 协议（`backend/routers/claude_agent.py:624-647`）。
- Dream stage 已有独立 REST 投影和轮询判定（`frontend/src/hooks/story-workspace/useStoryWorkspaceDreamFiles.ts:192-240,297-350`），writer events 仍未完成（`docs/design/story-workspace/design_005_dream-module-dataflow-and-sequence.md:361-366`）。

### 根因

通用 Chat transport 的合同面向完整 Chat UI 与调试/工具展示；Dream 需要的是 run-scoped、服务端过滤后的窄合同。直接在浏览器过滤虽能隐藏 UI，却已经把敏感 reasoning/工具参数发送给前端，不满足安全边界。

### 可选方案

1. Dream 直接调用通用 messages/stream，前端过滤。敏感内容已经越过服务端边界，否决。
2. 只轮询 messages。安全适配后可恢复，但没有实时输出体验，否决为唯一方案。
3. 新建 Story Workspace Dream Agent adapter：持久快照 + 服务端 allowlist SSE + terminal snapshot reconciliation。采用。

### 最终决策

新增 run-scoped Dream adapter 合同，底层可复用 `chat_message` 与 Claude Agent EventBus，但浏览器永远不直接持有 thread transport 合同：

- `GET /api/story-workspace/workflow-runs/{run_id}/dream-agent/messages`：返回经过服务端白名单映射的持久快照、active turn 和安全状态；snapshot 不伪造瞬时 stream cursor，首次订阅对当前 active turn 做完整 replay。
- `GET /api/story-workspace/workflow-runs/{run_id}/dream-agent/events`：只发标准化 `assistant_text_delta`、`assistant_message_committed`、`status` 与 keepalive；不得透传原始 SSE frame。
- `POST /api/story-workspace/workflow-runs/{run_id}/dream-agent/messages`：任务四使用的可信发送入口。

安全白名单：

- 用户可见：用户在 Dream 悬浮层主动发送的文本；Dream Agent 的 `assistant` text；`正在输出/已完成本轮输出` 等安全状态摘要。
- 默认排除：系统/launch/confirmation/control 消息、reasoning/thinking、tool invocation、工具输入输出、原始 error/debug event、session path、插件原始参数、凭证和内部 metadata。

加载与重连：

1. 首次进入先取持久化快照并按 message ID 去重显示。
2. 再订阅同 run 当前 turn 的过滤后增量；以服务端 `turn_id + event_ordinal` 作为瞬时事件 identity，客户端维护最近 cursor。
3. 现有 bus 完整 replay 可能重复，因此 adapter 必须过滤 `<= cursor` 的事件；不能把该责任推给渲染组件。
4. 收到 committed/finish 或连接中断时重新获取持久快照，以持久 message ID 对齐并替换临时 streaming message。
5. idle/进程重启/TTL 淘汰时，持久快照仍完整；连接采用有上限退避并再次快照，不把 `not_found` 映射为业务失败。
6. 页面本地 draft 不参与消息 merge；消息更新不得覆盖未确认内容。

如果实现阶段无法在不修改底层通用 bus 合同的前提下提供跨进程 cursor，最低合格降级是：每次重连重新取 snapshot、对当前 turn 全量 replay 做 `turn_id + event_ordinal` 去重、terminal 再取 snapshot；不得声称现有通用 stream 已经原生支持无遗漏 cursor。

`.dream` writer 仍以 Dream files REST polling 为阶段事实来源；Agent stream 只能显示回复与安全状态，不能提高 stage revision、替换 stage 内容或触发确认资格。

### 影响范围

Story Workspace 后端消息 adapter、contracts、run/thread 权限解析、前端 snapshot/SSE hooks、消息 allowlist 测试、重连/去重测试。

### 验收方式

- 首屏先出现持久 assistant 快照，随后增量追加。
- 重连/完整 replay 不重复，terminal snapshot 不丢消息。
- 响应 payload 与运行时 DOM 均不含 reasoning、工具参数或调试事件。
- Agent 消息变化不改变 stage revisions 或本地 draft。

## 5. P4 Dream Agent 悬浮交互层

### 问题

需要借鉴 ChatWidgetUI 的悬浮、展开、收起与输入体验，但不能把通用 Chat 产品合同或隐藏推理展示带入 Dream。

### 现状证据

- ChatWidgetUI 已具备 collapsed/expanded、autoscroll、输入和 processing 防重复交互（`frontend/src/components/ChatWidgetUI.tsx:92-113,131-184,424-485`）。
- 它还包含打开 Chat 的产品入口，并渲染 persisted/streaming thinking（同文件 `:220-246,289-325,358-402`），不能直接复用为 Dream UI。
- Dream 页本身是独立页面并根据 stage 文件逐步渲染、编辑和一次确认（`frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx:301-326,328-477`）。

### 根因

ChatWidgetUI 把通用 thread、Chat 导航和完整消息 parts 作为组件合同；Dream 需要以 run 为业务主体，服务器解析隐藏 thread，并只暴露安全消息 view model。

### 可选方案

1. 直接挂 ChatView/ChatWidgetUI。破坏 Dream 独立 surface 并暴露不安全 parts，否决。
2. fork 整个 Chat 组件。短期快但会复制 transport owner 和行为，否决。
3. 复用底层通用 transport/流解析思想，经 Dream adapter 映射后创建专属 rail/dialog。采用。

### 最终决策

组件边界：

- `StoryWorkspaceDreamAgentAdapter`：run-scoped snapshot、SSE、send；服务器解析可信 thread/Deck/context。
- `StoryWorkspaceDreamAgentViewModel`：唯一消息、status、unread、open/close、send 状态 owner。
- `StoryWorkspaceDreamAgentRail`：收起态状态、最近一至三条安全回复、未读提示、打开入口。
- `StoryWorkspaceDreamAgentDialog`：展开态消息历史、实时输出、输入、发送、关闭/收起。

禁止 import 或运行时挂载 `ChatView`；不得通过客户端新建普通 Chat thread。允许复用底层 SSE parser、纯消息 text renderer 或通用 focus helper，但只能经 Dream adapter 输入安全 DTO。

可信发送：客户端只提交 `run_id` path、纯文本和幂等 key；服务端 actor-scope 读取 run，再解析持久 `source_voice_thread_id`、Deck/preflight/runtime lock 和 Dream context。客户端提交的 threadId、Deck ID、workspace path 或 plugin 参数即使出现也不得被信任。自由输入只在 confirmation 已 dispatched 且没有 live turn 的 `recent` 阶段开放；生成中、等待确认、确认中和继续执行中只允许查看消息，不能以自由消息绕过一次确认。快速连续点击同一幂等 key 通过持久 claim 只取得一个 active dispatch，不生成新 thread。

交互与布局：

- 桌面端：悬浮层锚定 Dream 右栏，宽度上限约 420px，高度上限 `min(70vh, 720px)`，不得遮住底部确认主操作；阴影克制，视觉上是纸面工作台延伸。
- 窄屏：降级为底部 sheet/近全屏 dialog，保留安全边距和软键盘可见输入；正文不可产生水平溢出。
- 显式点击预览后才把焦点放入 dialog；Escape 关闭并把焦点还给触发区域。
- dialog 提供可访问名称；窄屏 modal 使用 `aria-modal=true` 和焦点约束，桌面非模态悬浮层保留 `role=dialog`。
- 新 assistant 内容使用 `aria-live=polite`；流式 token 不逐 token 抢读，按消息/节流片段播报。
- Enter 发送、Shift+Enter 换行；发送中按钮禁用并以幂等 key 防重复 dispatch。

### 影响范围

Dream 专属 adapter/view model/rail/dialog、StoryWorkspaceDreamPage 布局、CSS、键盘与无障碍测试、runtime ChatView absence 测试。

### 验收方式

- 收起态可看状态、最近回复和未读；点击打开完整 Dream Agent 交互。
- Escape 关闭、焦点归还；窄屏无严重遮挡或溢出。
- 发送继续使用同一 run/thread，快速发送不重复。
- 源码与运行时组件树均不含 ChatView。

## 6. P5 完整生命周期与 truth ownership

### 完整生命周期

1. 用户在 canonical Dream 工作台选择 Deck 并发起 Dream。
2. 后端持久化 workflow run、preflight/Deck/runtime binding 和隐藏 Agent thread 绑定。
3. 同一 Dream Agent 执行 `write_dream_run`，再依次写 characters、scenes、storyboards stage。
4. Dream files REST 投影读取 `.dream` 文件；页面按 revisions 渐进渲染。
5. Dream Agent adapter 同时提供安全消息快照与实时增量；它不改变 stage 内容。
6. 用户离开页面。
7. 用户从 `/story-workspace/dream` 重新进入并通过后端聚合选择原 run。
8. 页面并行恢复 actor-scoped run/Deck 绑定、Dream files revisions、确认事实、消息快照，再订阅消息增量。
9. 用户编辑形成页面本地 draft；新的 Agent message 不覆盖 draft。
10. 用户一次确认；服务端持久 claim，并在同一隐藏 thread 上继续执行。
11. 页面继续通过 Dream files REST 恢复后续 stage revision，通过 Dream Agent adapter 显示安全回复。

现有确认投影已经同时返回 accepted/dispatched/canConfirm（`backend/services/deck/story_workflow_gateway.py:771-785`）；本次不得引入第二套确认 owner。

### truth ownership

| 事实 | 唯一 owner | 其他层职责 |
|---|---|---|
| run 身份、创建者、workspace、Deck/runtime/preflight/thread 绑定 | 后端 workflow run 与持久绑定事实 | re-entry API 做 actor-scoped 投影；前端只消费 |
| Dream run/index/stage 内容与 revisions | `.dream` 文件（物理映射） | Dream files REST 校验、投影；页面轮询渲染 |
| 确认 accepted/dispatched | 既有持久 confirmation claim/fact | Dream files response 投影并控制一次确认 |
| Dream Agent 用户可见消息历史 | `chat_message` 中经 Dream allowlist 映射的持久消息 | snapshot API 投影；UI 不读取原始 parts |
| 实时 token/turn 状态 | Claude Agent EventBus 的瞬时 delivery | Dream SSE adapter 过滤、排序和去重；terminal 回到持久快照 |
| 隐藏 Agent thread | 技术连续性与执行 transport | 服务器从 run 解析；不得成为用户可见 Chat 会话 |
| 页面未确认修改 | 当前页面本地 draft | 仅当前编辑会话 owner；stage revision 冲突时提示，不被消息覆盖 |
| REST API | 权限校验与上述事实的投影/传输 | 不是第二个内容或生命周期 owner |

该边界延续既有设计中“Dream 文件是内容真相源、writer events 缺位时 REST 轮询”的结论（`docs/design/story-workspace/design_006_dream-protocol-dir-mapping.md:446-448`），并保持隐藏 thread 只作为技术实现（同文件 `:81-84`）。

### 影响范围

任务二的数据流图、前后端合同、实现测试和最终验收证据。

### 验收方式

- 任一事实在设计和代码中只有一个 owner。
- 消息增量不修改 stage revision，本地 draft 不被快照/增量覆盖。
- 恢复后 run、stage、确认与消息都来自各自持久来源，而非浏览器猜测。

## 7. P6 本期边界

### 问题

重新进入与消息交互容易被误扩展为通用 Chat 或旧 workflow 状态机。

### 最终决策

本期明确不做：

- 将 Dream 改造成 Chat 页面或直接挂载 ChatView；
- 展示模型隐藏推理、内部 chain-of-thought、凭证、敏感工具参数或原始调试事件；
- 新增业务驳回、业务失败、人工重试或内容归档状态；
- 画布式编辑器；
- 视频制作模块；
- 与当前 Dream run 无关的通用聊天中心；
- 仅依赖浏览器本地状态的 run/thread 恢复；
- 用 Agent message stream 取代 `.dream` stage writer/REST truth；
- 在本期修正遗留 WorkflowRun 全状态机，除非是安全读取与投影所必需。

旧 WorkflowContextBar 确有 cancel/retry/review 控制（`frontend/src/components/story-workspace/workflow/WorkflowContextBar.tsx:82-109`），因此不能原样搬进 Dream Agent 区域。既有设计也已经明确本期不增加失败、重试、驳回与归档业务流程（`docs/design/story-workspace/design_007_dream-business-module-interaction.md:326-338`）。

### 验收方式

- UI 文案、DOM、路由与 API 不出现上述新增业务流程。
- 消息 payload 不包含禁止内容。
- `backend/database.py` 不发生修改，且没有新增 DDL。

## 8. 任务二的强制输入

任务二必须以以下裁决为固定输入，不得重新制造平行 owner：

1. canonical re-entry 是 `/story-workspace/dream`；query run 是同页 deep link，Deck 是辅助入口。
2. 新增 actor-scoped Dream run 聚合；多 run 显式选择，分组后稳定排序。
3. Dream route 移除顶部完整 WorkflowContextBar；右侧 Dream Agent rail 与编辑区共存，并由单一 Dream view model 驱动。
4. Dream 消息使用服务端 allowlist 的“持久快照 + 过滤增量 + terminal reconciliation”。
5. 悬浮层是 Dream 专属 adapter/view model/component，不挂 ChatView，不新建普通 Chat thread。
6. `.dream` stage、持久 Agent message、EventBus、隐藏 thread和本地 draft 各自保持唯一 truth ownership。
7. UI 保持暖纸张、浅纸面分区、细分隔线和克制阴影；不得呈现外部客服插件风格。
8. 本期不扩展业务失败、驳回、人工重试或归档状态机。

## 9. 本轮结论

P1-P6 均已完成唯一裁决。任务一没有写入生产代码；仅新增本问题判定记录。下一步应以本记录创建 `design_008`，先固定信息架构、消息/恢复时序、truth ownership、桌面与窄屏线框，再进入实现。
