<!-- [Input] Existing Chat navigation, history/search and the priority activity PRD. -->
<!-- [Output] Current sidebar entry, mutual exclusion, history/search, original deletion and responsive boundaries. -->
<!-- [Pos] Existing Chat sidebar contract; activity rules and page skeletons are owned by docs/prd/chat/priority-activity.md. -->
<!-- [Sync] 2026-10-07: retain complete pre-activity history and align the current activity entry without changing unrelated navigation. -->

# Chat Sidebar PRD

> 聊天侧边栏、会话导航、文件入口和设置入口的产品与视觉规范。本文引用 [Color System](<./color_system/README.md>)，并与前端实现保持同步。
> **[Sync] 2026-06-28**: 当前 ChatView 不再使用左侧 rail/展开侧栏；历史对话由右上角「更多」菜单打开右侧 HistorySidePanel，搜索由面板标题栏按钮打开居中 HistorySearchDialog。
<!-- [Sync] 2026-10-09: 中文 Deck 导航名称为思维模式；英文 Decks 与既有导航行为保留。 -->
> 中文导航中的 Deck 产品名称统一为“思维模式”，概念和页面骨架见[思维模式 PRD](./deck/thinking-modes.md)。本文历史图示及英文 Decks 原文保留，代码与路由名称不变。

> **[Sync] 2026-09-18**: Story Workspace 在移动端改用底部 Chat、Dream、Decks、More 导航；More 展开层承载 Writing、Timeline、Analysis、主题、设置和账户。桌面端侧边栏语义不变。
> **[Sync] 2026-09-29**: 当前 Thread 的用户消息刻度属于 Chat 消息阅读区，详见[轮次导航 PRD](./chat/turn-navigation.md)；右侧历史面板仍负责 Thread 切换。

> **[Sync] 2026-10-07**: 新建旁铃铛打开右侧活动视图，顶部优先级与日期历史的现行产品规则/骨架见[Chat 活动视图 PRD](./chat/priority-activity.md)，业务图见[正式交互设计](../design/claude-agent/priority-activity-sidebar.md)。本次设计草案等待独立评审与实施；旧入口、16rem 面板等完整原文保存在[原侧栏历史稿](<./Chat Sidebar pre-priority-activity-20261007-history.md>)。

## 1. 文档范围

Chat Sidebar 覆盖对话工作区中的活动与历史面板、文件入口和移动端替代导航。当前 Chat 工作区不再使用左侧固定 rail；新建旁铃铛直接打开右侧活动视图，若保留「更多 → 历史对话」，指向同一面板。文件仍通过原菜单打开 FileSidebar。活动、文件、子智能体、独立任务会话与定时任务详情一次只显示一个，当前 Thread 任务与进度职责不变。

当前 Thread 内的用户消息刻度位于消息滚动区左缘，不是全局会话侧边栏；其悬浮摘要与消息定位由[轮次导航 PRD](./chat/turn-navigation.md)定义。

旧稿中的“玫瑰金”“高级灰调极简主义”“侧边栏设置 HTML 原型”不作为当前项目规范。

## 2. 设计目标

- 帮助用户快速切换会话、进入文件和设置，不干扰主编辑/聊天区域。
- 在桌面端提供清晰层级，在移动端收敛为顶部或底部轻导航。
- 当前项、hover、focus、折叠、空列表、错误、加载状态都有可验收描述。
- 与 Dashboard、History、Send 共享 [Color System](<./color_system/README.md>)。

## 3. 布局结构

```
ChatSidePanels
├── ChatTopActions（新建 / 活动铃铛 / 原任务与进度 / 更多）
├── MoreMenu（原工作空间 / 分享；历史入口指向同一活动面板）
├── ActivitySidebar（建议、未实现；20rem右侧面板 / 窄屏覆盖抽屉）
│   ├── Header（活动 / 历史搜索 / 刷新 / 关闭）
│   └── 唯一body列表滚动区
│       ├── 优先级（今日任务 / 五分钟Chat / 五分钟Dream）
│       ├── 四项显示菜单入口与来源独立恢复
│       └── 原日期SessionList及分页、独立删除
├── HistorySearchDialog（原ChatView内联居中弹窗）
│   ├── SearchInput
│   └── SearchResultList / GroupedDefaultHistory
└── 原FileSidebar / 子智能体 / TaskSessionSidebar / ScheduledTaskDetailSidebar
    （与活动侧栏互斥）
```

## 4. 桌面端规范

| 区域 | 规范 |
|---|---|
| 宽度 | 活动面板复用 FileSidebar 的 `20rem`；不同时展示旧 `16rem` 历史列。 |
| 背景 | 右侧业务面板使用 `color.bg.paper`。 |
| 分隔 | 右侧业务面板左边框使用 `color.border.paper`。 |
| 活动/历史入口 | 新建旁铃铛打开右侧活动面板；兼容历史入口指向同一面板，桌面占用布局宽度。 |
| 内边距 | 一级容器 16px 到 24px，列表项 8px 到 12px。 |
| 字体 | 导航用系统无衬线，品牌/标题可使用 Georgia/Excalifont 气质。 |

## 5. 组件规范

### 5.1 MoreMenu Entrypoints

- MoreMenu 位于 Chat 主界面右上角，由「更多」图标按钮触发。
- 工作空间与分享继续作为原菜单中的低频入口；新建旁活动铃铛为直接入口，历史菜单项如保留则指向同一活动面板。
- 历史对话使用 `IconClock`，工作空间使用 `IconFolder`，分享使用 `IconShare`。
- 菜单项 hover 使用 `color.bg.surface`，不使用高饱和填充。

### 5.2 Panel Header

| 状态 | 视觉 |
|---|---|
| 默认 | `color.text.secondary`，透明背景。 |
| Hover | 背景轻微加深，文本变为 `color.text.primary`。 |
| Active | 炭黑文本、左线/下划线或浅底选中，不使用橙色填充。 |
| Focus | 可见边框或 ring。 |
| Disabled | 降低对比并显示原因。 |

- 活动面板头部左侧显示「活动」，右侧显示原历史搜索、刷新和关闭按钮；标题固定。
- 搜索打开原 HistorySearchDialog，不在侧栏内渲染输入框；关闭搜索回到面板搜索按钮。
- 关闭按钮只关闭活动，不改变当前会话，并停止本功能刷新、归还铃铛焦点。

### 5.3 SessionList

- 会话标题一行截断；默认历史侧栏不展示搜索摘要。
- 当前会话使用 `color.border.focus` 或 `color.text.primary` 强化。
- Chat 列表没有跨 Thread 运行或未读字段，本次不添加推断徽标；任务触发状态与 Dream 业务阶段按活动 PRD 的真实字段显示。
- 打开活动时分别读取原日期历史与优先级来源；加载、来源失败和分页失败独立显示，错误不转为成功空。
- 日期历史空列表显示「暂无会话」，不在面板内重复新建入口；优先级空态与筛选空态按活动 PRD 表达。
- 保留原独立删除按钮及 `handleDeleteThread`：鼠标 hover 或键盘 focus 可达，点击阻止行导航；删除当前会话仍按原行为清空当前 Chat 工作区。近期 Chat 因优先级去重移出日期组时可复用同一回调，不新增删除机制或确认。

### 5.4 HistorySearchDialog

- 点击活动面板头部的原搜索按钮打开居中弹窗。
- 顶部为无边框搜索输入和关闭按钮；输入为空时显示按时间分组的默认历史列表。
- 弹窗不显示「新聊天」入口；新建会话只由 Chat 顶部「新建」按钮负责。
- 输入后搜索 thread 标题和持久化对话正文；结果显示对话图标、标题、命中摘要和日期。
- 无结果显示「未找到匹配会话」。
- 点击结果关闭弹窗并切换会话。

### 5.5 StatusArea

- Ready 使用 `color.state.success` 小图标或文字。
- Syncing 使用 `color.action.link` 或中性色 spinner。
- Error 使用 `color.state.error` 和修复入口。
- 存储、文件保留、权限等策略文案不得硬编码阈值，需引用产品策略。

### 5.6 UserOrUtilityArea

- 设置、账户、退出等低频操作放在底部或折叠菜单。
- 破坏性操作使用 `color.state.danger`，需要确认或撤销路径。

## 6. 历史面板与搜索交互设计

### 6.1 活动面板中的历史

| 模式 | 规范 |
|---|---|
| 打开 | 点击新建旁活动铃铛后右侧展开，独立读取历史及三个优先级来源；兼容历史菜单项指向同一面板。 |
| 关闭 | 再点铃铛或头部关闭；不清空当前会话；停止本功能刷新并归还焦点，不自动恢复旧侧栏。 |
| 默认列表 | 复用当前用户 Thread 的日期组与分页；在优先级实际显示的 Chat 不重复出现在日期组，关闭相应筛选后回到原组。 |
| 当前会话 | 右侧显示 `color.action.link` 小圆点。 |
| 删除 | 原独立按钮与 handleDeleteThread 保留；日期历史和近期 Chat 复用同一行为，不与行导航同时触发。 |
| 加载/空态 | 首次加载、成功空与失败区分；分页失败保留已加载行并提供重试，不写成全部已显示。 |

### 6.2 HistorySearchDialog

| 区域 | 规范 |
|---|---|
| 触发 | 活动面板标题栏中的原历史搜索按钮。 |
| 头部 | 搜索输入 + 关闭按钮；打开时输入框清空并聚焦。 |
| 默认内容 | 输入为空时展示按时间分组的默认历史，不展示新建入口。 |
| 搜索内容 | 输入后显示匹配 thread；摘要来自标题或对话正文命中片段。 |
| 关闭 | 点击关闭、Esc 或遮罩关闭。 |

面板和弹窗开关不改变当前会话，不清空消息列表滚动位置。

## 7. 移动端适配

- Story Workspace 不保留竖向侧栏，底部导航固定展示 Chat、Dream、Decks 和 More，同时保留文字标签和当前页语义。
- More 展开层提供 Writing、Timeline、Analysis、主题、设置和账户；选择路由后关闭展开层。
- 主内容使用完整视口宽度，底部预留导航和安全区高度，不得产生水平滚动或遮挡 Chat 输入区。
- 活动面板沿用 App/useMobile 的既有小于768px或移动设备判定，使用覆盖抽屉；390px验证尺寸下全宽，不把主Chat压缩为第二列。固定标题与唯一body列表滚动，背景点击、滚动与焦点隔离，关闭后恢复。
- HistorySearchDialog 在移动端接近全屏，保留搜索输入和关闭按钮。
- 抽屉打开时使用 `color.bg.overlay` 遮罩。
- 关闭活动后输入 Dock 恢复原位置与可操作状态；覆盖抽屉打开时背景输入暂不接收操作，不改变草稿或发送状态。

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
- MoreMenu、搜索、关闭、删除等图标按钮必须提供 Tooltip 或 aria-label。
- 当前项需要同时通过语义状态和视觉表达。
- 会话列表的时间、未读、错误不能只靠颜色。

## 11. 验收标准

- 活动铃铛、20rem侧栏、显示菜单、来源恢复与窄屏抽屉按[活动视图 PRD](./chat/priority-activity.md)及[正式交互设计](../design/claude-agent/priority-activity-sidebar.md)验收；当前设计草案不代表实现或独立评审完成。
- 首次打开显示历史及各来源真实加载/结果；失败可重试，已有行保留，关闭/隐藏后不提交旧响应。
- HistorySearchDialog 不显示「新聊天」入口。
- 默认、hover、active、focus、disabled、loading、error、empty 状态均可验收。
- 所有颜色引用 [Color System](<./color_system/README.md>)。
- 不包含玫瑰金、Tailwind 原型或外部图标依赖作为必要实现。

## 12. 前端实现备注（2026-05-29 本轮）

**`VerticalNav` 组件已从 `ChatView.tsx` 移除。** 侧边栏功能已重新分配：

- 活动/历史入口 → `ChatView.tsx` 新建旁活动铃铛 → 同一个右侧活动面板；兼容「更多→历史对话」指向相同目标
- 历史搜索入口 → 活动面板标题栏原搜索按钮 → ChatView内联 `HistorySearchDialog` 产品弹窗
- 文件/工作空间入口 → 「更多」菜单 → 右侧 `FileSidebar`
- 新建对话 → 右上角常驻「新建」按钮

`VerticalNav.tsx` 文件保留在代码库中但不再被 `ChatView.tsx` 引用，可在后续需要时复用其展开/折叠 + 内联线程列表的实现模式。

当前 Chat 工作区已无左侧固定导航栏；活动、文件、子智能体、独立任务会话与定时任务详情作为互斥右侧临时工作面板。新增活动打开、刷新、筛选及行导航只读取或导航；用户主动点击的现有独立删除仍沿用原接口与权限，既有其他业务能力不因本次文档同步移除。
