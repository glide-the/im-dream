# Chat Sidebar PRD

> 聊天侧边栏、会话导航、文件入口和设置入口的产品与视觉规范。本文引用 [Color System](<./Color System.md>)，仅更新 PRD，不修改产品代码。

## 1. 文档范围

Chat Sidebar 覆盖对话工作区中的导航、会话列表、状态入口、文件入口、设置入口、折叠态和移动端替代导航。它需要与当前产品已有顶部导航、左侧工具条和纸张式界面保持一致。

旧稿中的“玫瑰金”“高级灰调极简主义”“侧边栏设置 HTML 原型”不作为当前项目规范。

## 2. 设计目标

- 帮助用户快速切换会话、进入文件和设置，不干扰主编辑/聊天区域。
- 在桌面端提供清晰层级，在移动端收敛为顶部或底部轻导航。
- 当前项、hover、focus、折叠、空列表、错误、加载状态都有可验收描述。
- 与 Dashboard、History、Send 共享 [Color System](<./Color System.md>)。

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
| 宽度 | 以内容密度为准，建议 240px 到 280px；可折叠为图标栏。 |
| 背景 | `color.bg.app` 或 `color.bg.surfaceSolid`。 |
| 分隔 | 右边框使用 `color.border.paper`。 |
| 内边距 | 一级容器 16px 到 24px，列表项 8px 到 12px。 |
| 字体 | 导航用系统无衬线，品牌/标题可使用 Georgia/Excalifont 气质。 |

## 5. 组件规范

### 5.1 BrandOrWorkspace

- 显示产品或当前工作区名称，使用 `color.text.primary`。
- 不使用远程头像作为必要设计资产。
- 如需 Logo，保持简单文字或本地图标，避免高饱和块状品牌标。

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

### 5.4 StatusArea

- Ready 使用 `color.state.success` 小图标或文字。
- Syncing 使用 `color.action.link` 或中性色 spinner。
- Error 使用 `color.state.error` 和修复入口。
- 存储、文件保留、权限等策略文案不得硬编码阈值，需引用产品策略。

### 5.5 UserOrUtilityArea

- 设置、账户、退出等低频操作放在底部或折叠菜单。
- 破坏性操作使用 `color.state.danger`，需要确认或撤销路径。

## 6. 折叠态

| 模式 | 规范 |
|---|---|
| 宽侧边栏 | 显示图标、标题、摘要、状态。 |
| 窄侧边栏 | 仅显示图标和 Tooltip。 |
| 隐藏侧边栏 | 主内容全宽，提供顶部按钮呼出。 |

折叠/展开不改变当前会话，不清空滚动位置。Tooltip 使用 `color.bg.surfaceSolid` 和 `color.border.neutral`。

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
- 所有颜色引用 [Color System](<./Color System.md>)。
- 不包含玫瑰金、Tailwind 原型或外部图标依赖作为必要实现。

## 12. 前端实现备注

本 PRD 不要求实现。后续实现应先评估当前 `TopNavBar`、`LeftToolbar`、会话状态组件的复用可能，再决定是否新增 Chat Sidebar 组件。
