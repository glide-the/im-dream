# Chat Sidebar PRD

> 聊天侧边栏、会话导航、文件入口和设置入口的产品与视觉规范。本文引用 [Color System](<./color_system/README.md>)，并与前端实现保持同步。

## 1. 文档范围

Chat Sidebar 覆盖对话工作区中的导航、会话列表、状态入口、文件入口、设置入口、折叠态和移动端替代导航。Chat 工作区内的侧栏使用主题自适应折叠图标栏；展开面板和业务内容保持 Ink & Memory 的纸张式界面。

旧稿中的“玫瑰金”“高级灰调极简主义”“侧边栏设置 HTML 原型”不作为当前项目规范。

## 2. 设计目标

- 帮助用户快速切换会话、进入文件和设置，不干扰主编辑/聊天区域。
- 在桌面端提供清晰层级，在移动端收敛为顶部或底部轻导航。
- 当前项、hover、focus、折叠、空列表、错误、加载状态都有可验收描述。
- 与 Dashboard、History、Send 共享 [Color System](<./color_system/README.md>)。

## 3. 布局结构

```
ChatSidebar
├── BrandOrWorkspace
├── PrimaryNav
│   ├── Dashboard
│   ├── Chats
│   ├── Files
│   └── Settings
├── SessionList
│   ├── Pinned/Recent group
│   └── ChatSessionItem
├── StatusArea
│   ├── Sync/Ready/Error
│   └── Storage/File hints
└── UserOrUtilityArea
```

## 4. 桌面端规范

| 区域 | 规范 |
|---|---|
| 宽度 | 默认窄栏 4rem；展开后约 12rem；会话历史面板展开宽度约 18rem。 |
| 背景 | 导航窄栏使用 `color.bg.app`；展开业务面板使用 `color.bg.paper`。 |
| 分隔 | 导航窄栏和业务面板均使用 `color.border.paper`。 |
| 折叠态历史 | 会话历史入口打开 rail 右侧浮层，浮层不占用主内容布局宽度。 |
| 内边距 | 一级容器 16px 到 24px，列表项 8px 到 12px。 |
| 字体 | 导航用系统无衬线，品牌/标题可使用 Georgia/Excalifont 气质。 |

## 5. 组件规范

### 5.1 BrandOrWorkspace

- 折叠态显示本地图标；点击用于展开/收起侧栏。
- 展开态显示工作区标签，使用 `color.text.primary`。
- 不使用远程头像作为必要设计资产。
- 如需 Logo，保持简单文字或本地图标，避免高饱和块状品牌标。
- 当前图标集使用 `IconGrid`、`IconFolder`、`IconClock`、`IconUser`，避免因参考图替换为不符合产品气质的新图标。

### 5.2 PrimaryNav

| 状态 | 视觉 |
|---|---|
| 默认 | `color.text.secondary`，透明背景。 |
| Hover | 背景轻微加深，文本变为 `color.text.primary`。 |
| Active | 炭黑文本、左线/下划线或浅底选中，不使用橙色填充。 |
| Focus | 可见边框或 ring。 |
| Disabled | 降低对比并显示原因。 |

### 5.3 SessionList

- 会话标题一行截断，保留最近消息摘要和时间。
- 当前会话使用 `color.border.focus` 或 `color.text.primary` 强化。
- 未读或进行中状态使用小徽标，不使用大面积背景色。
- 空列表显示“暂无会话”与新建入口。
- 会话历史面板顶部包含搜索框；搜索过滤当前线程标题，不改变当前会话。

### 5.4 StatusArea

- Ready 使用 `color.state.success` 小图标或文字。
- Syncing 使用 `color.action.link` 或中性色 spinner。
- Error 使用 `color.state.error` 和修复入口。
- 存储、文件保留、权限等策略文案不得硬编码阈值，需引用产品策略。

### 5.5 UserOrUtilityArea

- 设置、账户、退出等低频操作放在底部或折叠菜单。
- 破坏性操作使用 `color.state.danger`，需要确认或撤销路径。

## 6. 折叠态与展开态交互设计

### 6.1 折叠态（4rem 窄轨，默认状态）

| 模式 | 规范 |
|---|---|
| 窄侧边栏 | 默认 4rem，仅显示图标；鼠标悬浮显示 Tooltip（`color.bg.surfaceSolid` + `color.border.neutral`）。 |
| 新建对话 | 点击 `+` 图标直接创建新线程，不展开侧边栏。 |
| 文件入口 | 点击文件夹图标打开右侧文件侧栏，不展开侧边栏。 |
| **折叠态历史浮层** | 点击时钟图标后，在 rail 右侧弹出 `最近聊天` 浮层（position absolute，不占主内容布局宽度）；再次点击关闭；点击浮层外部关闭。 |
| 历史浮层内容 | 仅展示线程标题（一行截断）；当前会话右侧显示 `color.action.link` 小圆点；点击线程直接切换会话并关闭浮层。 |
| 展开侧边栏 | 点击网格/品牌图标按钮展开侧边栏，切换为展开态。 |

折叠态浮层规范：`color.bg.surfaceSolid`、`color.border.paper`、`color.shadow.medium`；圆角 `1.35rem`；空状态显示"暂无会话"。

### 6.2 展开态（16rem 宽轨）

| 区域 | 规范 |
|---|---|
| 头部 | 左：品牌网格图标；右：折叠按钮（收回窄轨）；不显示文字标题，保持简洁。 |
| 新建对话按钮 | 全宽主操作按钮，带 `+` 图标，颜色 `color.action.link`；创建中显示禁用态。 |
| **内联历史列表** | 展开态直接在侧边栏内显示所有线程（可滚动 flex: 1 区域），无需浮层。当前线程高亮（`color.bg.paper` 底色 + `color.border.paper` 边框）；每条线程右侧有删除图标，hover 时显示。 |
| 搜索 | 已移除（简化交互；如需恢复，在列表顶部添加带图标的搜索输入框）。 |
| 底部 | 已移除用户区/文件按钮（由折叠态图标负责）。 |

折叠/展开不改变当前会话，不清空消息列表滚动位置。

## 7. 移动端适配

- 不固定 280px 侧栏。
- 优先使用顶部轻导航、底部 tab 或抽屉。
- 抽屉打开时使用 `color.bg.overlay` 遮罩。
- 输入 Dock 始终优先于侧栏入口，不被遮挡。

## 8. 色彩规范

| 场景 | Token |
|---|---|
| 侧栏背景 | `color.bg.app`、`color.bg.surfaceSolid` |
| 分隔线 | `color.border.paper` |
| 导航默认 | `color.text.secondary` |
| 导航 active | `color.text.primary`、`color.border.focus` |
| 状态 ready | `color.state.success` |
| 状态 error | `color.state.error` |
| 文件提示 | `color.text.muted`、必要时 `color.state.warning` |

## 9. 暗色模式

- 背景切换为暖黑纸面，不使用冷黑侧栏。
- Active 状态使用反色炭黑 token 或边框，而不是霓虹橙。
- Tooltip、菜单和抽屉必须与主内容保持层级区分。

## 10. 可访问性

- 所有导航项可键盘访问。
- 折叠图标必须提供 Tooltip 和 aria-label。
- 当前项需要同时通过语义状态和视觉表达。
- 会话列表的时间、未读、错误不能只靠颜色。

## 11. 验收标准

- Sidebar 的展开、折叠、隐藏、移动端抽屉均有设计要求。
- 默认、hover、active、focus、disabled、loading、error、empty 状态均可验收。
- 所有颜色引用 [Color System](<./color_system/README.md>)。
- 不包含玫瑰金、Tailwind 原型或外部图标依赖作为必要实现。

## 12. 前端实现备注（2026-05-29 本轮）

**`VerticalNav` 组件已从 `ChatView.tsx` 移除。** 侧边栏功能已重新分配：

- 历史对话入口 → `ChatView.tsx` 右上角「更多」下拉菜单 → `RecentChatFlyout` 浮层
- 文件/工作空间入口 → 「更多」菜单 → 右侧 `FileSidebar`
- 新建对话 → 右上角常驻「新建」按钮

`VerticalNav.tsx` 文件保留在代码库中但不再被 `ChatView.tsx` 引用，可在后续需要时复用其展开/折叠 + 内联线程列表的实现模式。

当前 Chat 工作区已无左侧固定导航栏，页面全宽交给 ChatPanel 和内容区。
