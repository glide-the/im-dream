# Chat Dashboard PRD

> 对话工作台首页的产品与视觉设计规范。本文引用 [Color System](<./color_system/README.md>)，并与前端实现保持同步。

## 1. 文档范围

Chat Dashboard 是用户进入对话工作区后的首屏，用于创建新会话、查看当前对话状态、进入历史记录、管理附件入口，并承载底部输入 Dock。

本次更新删除旧稿中的独立 Tailwind HTML 原型、外部头像、橙色主视觉和灰色营销式 Hero，改为与 Ink & Memory 当前纸张式界面统一。

模型配置（主题、AI 模型、系统提示词、工作区模式）已迁移至独立的 Settings 页面，参见 [Settings PRD](<./Settings.md>)。Chat 页面不再渲染模型配置侧边栏。

## 2. 设计目标

- 保持"暖纸张、手写、安静工具台"的产品气质。
- 让用户在首屏立即理解：当前是否有会话、能否输入、可否上传文件、如何新建对话。
- 将快捷入口、状态反馈和输入区放在同一视觉层级内，避免首页变成营销页。
- 为 Light/Dark 模式共用同一语义 token。
- 页面不出现外层垂直滚动；消息流内部自行滚动。

## 3. 页面布局

```
ChatDashboard（height: 100%，overflow: hidden）
├── FloatingActionBar（右上角绝对定位，zIndex: 20）
│   ├── NewChatButton（新建对话）
│   └── MoreMenu（下拉菜单）
│       ├── 历史对话（切换 RecentChatFlyout）
│       ├── 工作空间（切换 FileSidebar）
│       └── 分享（复制当前页 URL）
├── RecentChatFlyout（历史浮层，右上角下方弹出）
├── MainArea（flex: 1，flex-direction: column，overflow: hidden）
│   ├── QuickActions（flexShrink: 0，未开始对话时显示）
│   │   ├── 继续写作
│   │   ├── 总结笔记
│   │   ├── 整理大纲
│   │   ├── 发现关联
│   │   ├── 写作灵感
│   │   └── 回顾反思
│   └── ChatPanel（flex: 1，minHeight: 0，overflow: hidden）
│       ├── ChatMessageList（有消息或错误后加载，flex: 1，overflowY: auto）
│       └── AIInputDock（flexShrink: 0）
└── FileSidebar（右侧文件侧边栏，可收起）
```

| 区域 | 桌面端规范 | 移动端规范 |
|---|---|---|
| 页面画布 | `color.bg.app`，`height: 100%`，`overflow: hidden` | 全高，禁止外层滚动 |
| FloatingActionBar | 绝对定位右上角，透明背景，按钮 hover 显示 `color.bg.surface` 轻底色；不占布局流 | 保持紧凑，不换行 |
| MoreMenu 下拉 | `color.bg.surfaceSolid` + `color.border.paper` + `color.shadow.medium`，圆角 `0.85rem`；点击外部透明蒙层关闭 | 同左 |
| 快捷入口 | 2 到 3 列纸面卡片，`flexShrink: 0` | 纵向列表或横滑 |
| ChatPanel | `flex: 1`，`minHeight: 0`，消息流内部滚动 | 单列，左右留 16px 内边距 |
| 输入 Dock | 底部 sticky，宽度与消息流对齐 | 固定底部，避开系统安全区 |

## 4. 组件层级

### 4.1 FloatingActionBar

- 绝对定位于 MainArea 右上角（`top: 0.65rem, right: 0.75rem`），`zIndex: 20`，不占用布局流。
- 常驻两个按钮：**新建对话**（`IconPlus` + 文字"新建"）和 **更多**（`IconMoreHorizontal`）。
- 按钮默认透明背景，hover 时显示 `color.bg.surface` 轻底色，颜色从 `color.text.secondary` 过渡到 `color.text.primary`，`0.14s ease`。
- 新建对话按钮：创建中时显示"创建中"并禁用，`color.text.muted` + 降低透明度。

### 4.1.1 MoreMenu 下拉菜单

- 点击「更多」按钮弹出，点击外部透明蒙层（`position: fixed, inset: 0`）关闭。
- 容器：`color.bg.surfaceSolid`、`color.border.paper`、`color.shadow.medium`，圆角 `0.85rem`，`padding: 0.35rem`。
- 菜单项从上到下：
  - **历史对话**（`IconClock`）：切换 RecentChatFlyout；激活态显示 `color.bg.surface` 底色。
  - **工作空间**（`IconFolder`）：切换右侧 FileSidebar；激活态显示 `color.bg.surface` 底色。
  - 分隔线（`color.border.paper`）
  - **分享**（`IconShare`）：复制当前页 URL，点击后文案变为"已复制链接"。
- 每个菜单项高 `2.2rem`，圆角 `0.55rem`，左侧图标 + 文字。

### 4.1.2 RecentChatFlyout

- 由 MoreMenu 中「历史对话」入口触发，弹出于 FloatingActionBar 下方（`right: 0.75rem, top: 3.25rem`），绝对定位，不推挤主内容。
- 使用 `color.bg.surfaceSolid`、`color.border.paper`、`color.shadow.medium`，圆角 `1.25rem`。
- 标题"最近聊天"，下方展示线程列表：当前线程右侧显示 `color.action.link` 小圆点；点击后切换会话并关闭浮层。
- 空状态显示"暂无会话"。

### 4.2 QuickActions

快捷指令应与 Ink & Memory 笔记系统场景一致：

| 快捷指令 | 说明 | 颜色 |
|---|---|---|
| 继续写作 | 从当前段落继续扩展，保持原有语气与风格 | `color.state.success` |
| 总结笔记 | 提炼核心观点，生成简洁的笔记摘要 | `color.state.warning` |
| 整理大纲 | 将零散想法重组为清晰的结构化大纲 | `color.voice.blue` |
| 发现关联 | 找出笔记之间的联系与隐藏的共同主题 | `color.voice.purple` |
| 写作灵感 | 基于当前主题，提供创意角度与扩展方向 | `color.voice.pink` |
| 回顾反思 | 引导反思已有笔记，提出思考问题与行动建议 | `color.voice.green` |

- 卡片使用 `color.bg.surface` 或 `color.bg.surfaceSolid`。
- 图标颜色来自 `color.voice.*` 或 `color.state.*`，只用于图标/徽标。
- 卡片 hover 可增加 `color.shadow.soft`，位移不超过 3px。
- 不使用 3D 翻转、强 glow、渐变装饰。
- **触发后隐藏**：用户点击任意快捷指令卡片或在输入框发送第一条消息后，QuickActions 区域立即隐藏，MainArea 只显示 ChatPanel（消息流 + 输入 Dock）。新建会话（New Chat）后恢复显示。

### 4.3 ChatPanel + AIInputDock

- ChatPanel 占剩余所有高度（`flex: 1`，`minHeight: 0`），内部消息列表独立滚动。
- 默认空会话不渲染空的消息纸面容器；只有已有消息、发送后产生消息或错误需要展示时，才加载 ChatMessageList 区域。
- AIInputDock 在 ChatPanel 内部 sticky，不触发外层滚动。
- 视觉沿用 [Chat Send](<./Chat Send.md>)：纸面容器、柔和边框、底部操作行。
- `Ask Ink & Memory…` placeholder 使用 `color.text.muted`。

## 5. 色彩与视觉规范

| 元素 | Token | 说明 |
|---|---|---|
| 页面背景 | `color.bg.app` | 暖纸张背景。 |
| 主内容纸面 | `color.bg.paper` | 消息和输入承载层。 |
| 卡片/浮层 | `color.bg.surface` | 快捷入口、状态摘要。 |
| 边框 | `color.border.paper` | 保持棕灰纸张质感。 |
| 主文案 | `color.text.primary` | 标题、当前操作。 |
| 正文 | `color.text.body` | 消息预览。 |
| 链接/发送 | `color.action.link` | 小面积使用。 |
| 工具步骤 | `color.state.warning` | 只用于左线、徽标或命令提示。 |

## 6. 状态设计

| 状态 | 设计要求 |
|---|---|
| 空状态 | 显示可输入的提示、快捷入口和 Add 入口；不显示虚构数据，也不显示空白消息纸面容器。 |
| 对话已触发 | 用户点击快捷指令或发送第一条消息后，QuickActions 区域隐藏，MainArea 仅展示 ChatPanel（消息流 + 输入 Dock）；页面不刷新、不跳转。 |
| 加载态 | 消息区显示低对比 skeleton 或 pulse；输入区保持可见但根据能力禁用发送。 |
| 错误态 | 使用 `color.state.error` 加明确错误文本；提供重试入口。 |
| 禁用态 | 按钮使用 `color.disabled.bg`，光标和说明同步变化。 |
| 选中态 | 当前快捷入口或当前会话使用炭黑文本/边框加强。 |
| 悬停态 | 背景轻微加深或阴影增强，0.2s ease。 |

## 7. 暗色模式适配

- 背景切换到 `color.bg.app` 的 Dark 值，保留暖黑纸张感。
- 卡片和输入 Dock 使用 `color.bg.paper`/`color.bg.surface` 的 Dark 值。
- Terminal 可保持更深背景，但边框和标题栏需符合 Dark 模式对比度。
- 不使用霓虹橙作为暗色模式品牌色。

## 8. `image.png` 用途

`docs/prd/image.png` 当前是聊天工作台视觉参考，展示了暖灰页面、白色消息气泡、工具步骤、Terminal 和底部输入 Dock。本轮不覆盖该图片。

建议后续若更新图片，应保持：

- 暖纸张背景和纸面输入 Dock。
- 工具步骤使用细线提醒，不放大为高饱和主视觉。
- Terminal 深色块与正文纸面形成清晰层级。
- `New Chat` 顶部操作保持轻量。

## 9. 可访问性与响应式

- Dashboard 所有按钮必须支持键盘 Tab 顺序和可见 focus。
- 空状态、错误态、加载态需要有文本说明。
- 快捷卡标题和描述不得依赖颜色区分。
- 移动端输入 Dock 不遮挡消息末尾内容。

## 10. 验收标准

- Dashboard PRD 不再包含可复制 HTML 原型、Tailwind 配置或外部头像依赖。
- 所有颜色描述均引用 [Color System](<./color_system/README.md>) token。
- Light/Dark、空/加载/错误/禁用/选中/悬停状态均有明确要求。
- Chat 页面无外层垂直滚动，消息区自行滚动。
- 模型配置侧边栏已从 Chat 页面移除，迁移至 [Settings PRD](<./Settings.md>)。
- 快捷指令与笔记系统场景一致，不含业务销售类内容。
- `image.png` 被保留为视觉参考，未被覆盖。

## 11. 前端实现备注（2026-05-29 本轮）

- `ChatView.tsx`：移除独立 `VerticalNav` 侧边栏组件；改为右上角 `position: absolute` 浮动按钮区，常驻「新建对话」和「更多」两个按钮。
- **FloatingActionBar**：`zIndex: 20`，按钮默认透明，hover 显示 `color.bg.surface`，无固定高度状态栏。
- **MoreMenu**：「更多」按钮点击弹出下拉菜单，包含历史对话、工作空间、分享三项；使用 `position: fixed` 透明蒙层关闭。
- **RecentChatFlyout**：由「更多 → 历史对话」触发，绝对定位于右上角下方（`right: 0.75rem, top: 3.25rem`）；`threadSidebarOpen` 状态控制显隐。
- **FileSidebar**：由「更多 → 工作空间」触发，右侧可收起面板，`fileSidebarOpen` 状态控制。
- `ChatPanel.tsx`：消息区背景改为 `color.bg.app`，移除边框，保持页面统一底色。
- `AIInputDock.tsx`：全面对齐颜色系统 token；发送/工具选择按钮激活态改用炭黑（`color.text.primary`）；停止按钮改用 `color.state.danger`；阴影改为 `color.shadow.soft`；附件按钮文案改为"附件"。
- `const.ts`：快捷指令保持笔记系统场景。
- `ChatPanel.tsx` / `ChatMessageList.tsx`：消息列表和输入 Dock 填满 Chat 主区域宽度。

后续如新增 Dashboard 组件，先抽取共享 token/样式，再落地模块。
