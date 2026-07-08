# Chat Dashboard PRD

> 对话工作台首页的产品与视觉设计规范。本文引用 [Color System](<./color_system/README.md>)，并与前端实现保持同步。
> **[Sync] 2026-06-09**: Chat 输入区的权限切换受 Settings「应如何批准 IM」控制；完全访问开启时隐藏「逐步确认」并显示「完全访问」。
> **[Sync] 2026-06-13**: 完全访问只隐藏全局逐步确认入口；`AskUserQuestion` / `mcp__user__ask_user` 仍显示问答确认窗口。
> **[Sync] 2026-06-09**: ChatPanel 在用户上滑离开消息底部时，于 AIInputDock 上方显示悬浮「滚动到底部」箭头；点击后平滑回到底部并恢复自动贴底。
> **[Sync] 2026-06-28**: 历史对话入口改为右侧历史面板；面板打开即加载默认历史，标题栏搜索按钮打开居中搜索弹窗。搜索弹窗只负责检索和切换会话，不显示「新聊天」入口。
> **[Sync] 2026-07-08**: 依据《Chat 工作区入口页》与《连接器具体配置页面结构草图》重写 Chat 主工作区：以居中 `ChatInputDock` + `WorkspaceTabBar` 为准，历史与资源连接器都在主内容区切换，旧的侧边历史入口不再作为主路径。
> **[Sync] 2026-07-08**: 修正资源连接器入口策略：Chat 只承载轻量 `ResourceConnectorTabPanel`，点击「选择连接器」或连接器卡片必须进入 Settings 的「资源链接」区；Notion 具体配置页由 Settings 内的 `ConnectorNotionDetailPage` 承载。

## 1. 文档范围

Chat Dashboard 是用户进入对话工作区后的首屏，用于创建新会话、查看聊天历史、查看资源连接器摘要，并承载底部 / 居中的输入 Dock。

本次版本以 `docs/prd/Chat 工作区入口页.md` 为首屏草图，以 `docs/prd/notion-session/连接器具体配置页面结构草图.md` 为连接器下钻页草图。Chat 不再以右侧历史侧栏作为主要入口，`WorkspaceTabBar` 成为唯一的主内容切换器。

模型配置（主题、AI 模型、系统提示词、工作区模式）与资源链接管理仍位于独立的 Settings 页面，参见 [Settings PRD](<./Settings.md>)。Chat 里的资源连接器 Tab 不实现 Notion 认证、资源选择或同步配置。

## 2. 设计目标

- 保持“暖纸张、手写、安静工具台”的产品气质。
- 让用户在首屏立即理解：**先输入、再切换内容区**。
- 让 `聊天历史` 与 `资源连接器` 共享同一 Chat 工作区框架，但资源连接器在 Chat 中只展示摘要、空态与跳转入口。
- 让连接器的认证、资源选择、同步和关闭操作统一进入 Settings 的「资源链接」区，避免 Chat 内出现第二套配置流程。
- 明确空状态、加载态、错误态与已连接态，尤其是连接器 Tab 的空 / 骨架 / 异常表现。
- 页面不出现外层垂直滚动；历史列表、消息流、连接器列表各自内部滚动。

## 3. 页面布局

```txt
ChatDashboardPage
├── ChatTopHeader
│   ├── ModuleIcon
│   ├── ModuleTitle
│   ├── ModuleDescription
│   ├── ShareButton
│   └── MoreButton
├── CenterStage
│   ├── ChatInputDock（主视觉锚点）
│   │   ├── AddButton
│   │   ├── TextInput
│   │   ├── AttachmentEntry
│   │   ├── ModelOrToolEntry
│   │   └── UserAvatar / SubmitEntry
│   ├── WorkspaceTabBar
│   │   ├── HistoryTab（default）
│   │   └── ResourceConnectorTab
│   └── MainContentArea
│       ├── HistoryTabPanel
│       │   ├── EmptyChatState
│       │   ├── HistorySkeletonList
│       │   ├── HistoryThreadList
│       │   └── ChatMessageList
│       └── ResourceConnectorTabPanel
│           ├── ConnectorToolbar
│           ├── ConnectorEmptyState
│           ├── ConnectorListSkeleton
│           ├── ConnectorList
│           └── ConnectorErrorState
└── ScrollToBottomButton（仅 active_chat）
```

### 3.1 布局原则

| 区域 | 桌面端规范 | 移动端规范 |
|---|---|---|
| 页面画布 | `color.bg.app`，`height: 100%`，`overflow: hidden` | 全高，禁止外层滚动 |
| `ChatTopHeader` | 顶部固定信息条，显示模块信息、分享和更多 | 维持单行或双行压缩，不隐藏分享 / 更多 |
| `ChatInputDock` | 页面中心视觉重心，初始位于内容区上半部居中 | 首屏优先可见，保持足够点击面积 |
| `WorkspaceTabBar` | 位于输入框正下方，固定仅两项：`聊天历史` / `资源连接器` | 横向胶囊按钮，可横向压缩但不换组 |
| `MainContentArea` | 位于 Tab 下方，内部独立滚动 | 占满剩余高度，内部滚动 |
| `ConnectorToolbar` | 右上对齐筛选 / 排序 | 移动端可折叠为单行 dropdown |
| `ScrollToBottomButton` | 悬浮于输入 Dock 上方，只在 `active_chat` 出现 | 同桌面端，避开安全区 |

### 3.2 与旧结构的关系

- `WorkspaceTabBar` **取代** 旧的 `HistorySidePanel` 作为主历史入口。
- `MoreButton` 不再承担“打开历史对话”的主职责；它只保留分享之外的溢出操作（例如工作区相关辅助动作）。
- 历史与连接器都在 `MainContentArea` 内切换，避免“主内容区 + 右侧历史抽屉”双入口并存。

## 4. 组件层级与功能描述

### 4.1 `ChatTopHeader`

- 左侧展示 `ModuleIcon`、`ModuleTitle`、`ModuleDescription`。
- 右侧固定展示 `ShareButton` 与 `MoreButton`。
- `MoreButton` 仅承载非主流程附加操作，不应再包含“历史对话主入口”。

### 4.2 `ChatInputDock`

- 页面初始主视觉重心。
- `AddButton` 负责添加附件或资源入口；发送第一条消息后可继续保留，但视觉权重下降。
- 在 `empty_chat` 与 `connector_empty` 下都保持可用，用户无需离开当前 tab 即可新建对话。

### 4.3 `WorkspaceTabBar`

- 固定只有两个 tab：`HistoryTab`、`ResourceConnectorTab`。
- 默认选中 `HistoryTab`。
- 切 tab 时只切换 `MainContentArea`，不重排 Header 和 Input Dock。
- 文案使用中文：`聊天历史` / `资源连接器`。

### 4.4 `HistoryTabPanel`

- 默认状态承载 `EmptyChatState`。
- 若用户已有历史但未进入当前线程，可显示 `HistoryThreadList`。
- 进入某个线程或发送首条消息后，切换为 `ChatMessageList`。
- `ChatMessageList` 维持现有滚动到底部箭头逻辑：用户离开底部时显示 `ScrollToBottomButton`。

### 4.5 `ResourceConnectorTabPanel`

```txt
ResourceConnectorTabPanel
├── ConnectorToolbar
│   ├── FilterDropdown
│   └── SortDropdown
└── ConnectorContentArea
    ├── ConnectorEmptyState
    │   ├── ConnectorTypeIcons（远程资源 / 本地资源 / 更多）
    │   ├── EmptyTitle：暂无资源连接器
    │   ├── EmptyDescription：连接 Notion / 飞书 / CLI 后可在对话中使用资源
    │   └── SelectConnectorButton（主 CTA）
    ├── ConnectorList
    │   └── ConnectorCard（名称 / 描述 / 状态 / 更新时间）
    └── ConnectorErrorState
```

- 空态采用**虚线边框容器**，不可退化为纯文本。
- `SelectConnectorButton` 的主文案统一为 `选择连接器`；点击后必须打开 Settings 页面并聚焦「资源链接」区。
- 点击 `ConnectorCard` 后进入同一 Settings 资源链接路径；若用户继续点击 Notion「管理」，再进入 Settings 内的 `ConnectorNotionDetailPage`。

## 5. 状态设计

### 5.1 主状态枚举

| 状态 | 设计要求 |
|---|---|
| `empty_chat` | 默认落在 `HistoryTab`，主内容区显示空聊天状态；空状态不得抢过 `ChatInputDock` 的视觉权重。 |
| `active_chat` | 有消息内容时，`ChatMessageList` 成为主要内容区；`ScrollToBottomButton` 在用户离开底部时出现。 |
| `connector_empty` | 切到 `ResourceConnectorTab` 但没有任何资源连接器时，显示虚线空态、三枚资源类型图标、标题“暂无资源连接器”、描述文案和 CTA。 |
| `connector_connected` | 有连接器时显示 `ConnectorToolbar` + `ConnectorList`，卡片内展示状态 badge、名称、描述、最近同步信息。 |
| `connector_error` | 连接器列表读取失败、认证失效或同步失败时，在 tab 内容区内显示错误卡和重试入口，不影响 Header / Input Dock。 |

### 5.2 首次加载骨架屏

| 场景 | 要求 |
|---|---|
| `HistoryTab` 首次加载 | 使用 `HistorySkeletonList`：3~5 条纸面行块骨架，占位标题、摘要和时间；**禁止**只显示“加载历史中...”。 |
| `ResourceConnectorTab` 首次加载 | 显示 `ConnectorToolbar` 的 pill 骨架 + 2~3 个连接器卡片骨架；若尚未拿到列表结果，不得提前显示空态文案。 |
| 连接器空态预载 | 若接口返回为空，再从骨架切换到虚线空态卡；空态不是加载占位。 |

### 5.3 连接器空态文案

```txt
标题：暂无资源连接器
描述：连接 Notion / 飞书 / CLI 后可在对话中使用资源
主按钮：选择连接器
辅助图标：远程资源 / 本地资源 / 更多
```

## 6. 色彩与视觉规范

| 元素 | Token | 说明 |
|---|---|---|
| 页面背景 | `color.bg.app` | 暖纸张背景。 |
| 主内容纸面 | `color.bg.paper` | 历史列表、连接器列表、消息区承载层。 |
| 空状态 / 卡片 | `color.bg.surface` | 虚线空态卡、连接器卡片。 |
| 边框 | `color.border.paper` | 保持棕灰纸张质感。 |
| 主文案 | `color.text.primary` | 标题、当前操作。 |
| 正文 | `color.text.body` | 描述与摘要。 |
| 链接 / 发送 | `color.action.link` | 小面积使用。 |
| 错误态 | `color.state.error` | `connector_error`、发送失败。 |

## 7. 暗色模式适配

- 背景切换到 `color.bg.app` 的 Dark 值，保留暖黑纸张感。
- `WorkspaceTabBar`、连接器卡片、虚线空态、输入 Dock 都沿用统一的纸面语义色，不引入高饱和品牌色。
- `ScrollToBottomButton`、状态 badge、MoreMenu 在暗色模式下只提升对比度，不改变信息层级。

## 8. 可访问性与响应式

- `WorkspaceTabBar` 必须支持键盘切换和可见 focus。
- 空状态、错误态、加载态都需要文本说明。
- 连接器空态中的三枚图标不得成为唯一语义来源；标题 / 描述必须同时存在。
- 移动端输入 Dock 不遮挡 `MainContentArea` 的最后一条内容。
- `ScrollToBottomButton` 必须提供明确 `aria-label` / `title`。

## 9. 验收标准

- Chat Dashboard 与《Chat 工作区入口页》保持一致：**居中输入框 → `WorkspaceTabBar` → `MainContentArea`**。
- 历史入口不再以右侧历史面板作为主路径；`WorkspaceTabBar` 是唯一主切换。
- `ResourceConnectorTabPanel` 的空态具备虚线边框、三枚资源类型图标、标题、描述和 CTA。
- `HistoryTab` 与 `ResourceConnectorTab` 首次加载都使用骨架屏，而不是纯文本 loading。
- `connector_empty` / `connector_connected` / `connector_error` 三种连接器态互斥且切换清晰。
- 点击连接器卡片后进入 Settings 的「资源链接」区，而不是在 Chat 内原地展开复杂配置。

## 10. 任务解决方案设计稿（2026-07-08）

### 10.1 Chat 连接器跳转错位

| 项 | 方案 |
|---|---|
| 根因 | Chat 侧曾把 `ConnectorLandingPanel` 的 CTA / 卡片接入 Chat 内 `ConnectorConfigPage`，与最新设计稿“资源连接器空态点击跳转设置页链接器功能选择位置”不一致。 |
| 最小修复 | `ConnectorLandingPanel` 继续展示 toolbar、骨架、虚线空态和连接器卡片；所有选择动作统一调用 App 层 `openConnectorSettings()`。 |
| 非目标 | 不在 Chat 中实现认证、资源选择、同步、关闭连接或 Notion 详情页下钻。 |
| 验收 | 点击「选择连接器」或连接器卡片后进入 Settings，并滚动 / 聚焦到 `ConnectorSettingsSection`。 |

### 10.2 Chat 骨架屏

| 项 | 方案 |
|---|---|
| 根因 | 旧实现容易退化为文本 loading，弱化了设计稿里的黑色 / 暗色骨架结构。 |
| 最小修复 | 保留 `SkeletonList` / `ConnectorToolbarSkeleton`，在列表结果返回前不显示空态文案。 |
| 非目标 | 不新增全局 skeleton 系统，不重写 ChatPanel 消息流。 |
| 验收 | 历史和连接器首次加载均有结构化占位。 |

### 10.3 暗色主题

| 项 | 方案 |
|---|---|
| 根因 | Chat / Settings / Decks 的局部组件存在硬编码浅色背景或白字色。 |
| 最小修复 | 替换确定影响暗色模式的硬编码浅色面为语义 token 或 `color-mix()`。 |
| 非目标 | 不引入新的主题框架，不重做色彩系统。 |
| 验收 | 暗色模式下页面背景、卡片、边框、按钮和文本均使用可读的语义色。 |

## 11. 前端实现备注（2026-07-08 对齐稿）

- Chat 首页的首要视觉锚点是 `ChatInputDock`，不是 marketing hero，也不是右侧历史侧栏。
- 历史对话与资源连接器共用 `WorkspaceTabBar`，推荐实现成稳定的 content switch，而不是 overlay / drawer。
- `MoreButton` 可保留，但不得与 `WorkspaceTabBar` 重复提供“历史主入口”。
- 长对话中的到底部箭头逻辑继续保留，与本轮布局对齐不冲突。
