<!-- [Input] Current Dream Thread, owner-filtered task links, subagent projection, plan store and todo store. -->
<!-- [Output] Product rules for a conditional task-activity icon and separated Todo-style cards. -->
<!-- [Pos] Chat PRD; task creation/runtime ownership remains in docs/prd/claude-agent/task-session.md. -->
<!-- [Sync] 2026-09-28: keep PluginReceiptBadge unchanged and consolidate task activity under the existing Plan/Todo entry. -->

<!-- [Sync] 2026-10-07: include scheduled conversation activity while preserving existing task/agent/plan/todo boundaries. -->
# Chat 任务与进度面板

## 背景与问题

Chat 已有两个不同用途的入口：`PluginReceiptBadge` 显示 Deck、Agent 和插件元信息，`PlanButton` 使用 Todo 形式显示计划与待办。独立任务会话和子智能体属于当前 Thread 的执行活动，不属于 Deck 元信息。把这些内容写入 `PluginReceiptBadge` 会改变既有按钮、弹层和信息边界，也会把四套状态混成一张清单。

本功能扩展原 `PlanButton`，让它成为当前 Thread 的“任务与进度”入口。环境信息按钮、文字、图标、宽度、内容和打开方式保持现有实现。

## 目标与边界

- 当前 Thread 存在定时任务、独立任务会话、子智能体、计划或待办中的任意一项时，显示“任务与进度”图标；五项都不存在且读取成功时不显示；定时任务读取失败时保留入口供重试。
- 点击图标打开沿用旧 Plan/Todo 几何的卡片组。定时任务、独立任务会话、子智能体、计划、待办分别位于独立卡片，不能合并计数或共用状态。
- 独立任务来自当前用户有权读取的 `GET /api/claude-agent/threads/{id}/task-links`，状态来自每项受权详情读取。
- 子智能体复用 `useThreadSubagents` 和现有只读侧栏；计划复用 `useThreadPlan`；待办复用 `useThreadTodos`。
- `PluginReceiptBadge` 继续只显示 Deck、Agent 和插件信息，不接收任务面板属性，也不渲染任务内容。
- 不显示 Claude `session_id`、进程标识、调用键、转录路径或内部取消句柄。
- 目标 Thread 的来源标记保持在首条用户消息上；它与来源 Thread 的任务卡片分别解决返回来源和进入目标的问题。

## 概念与规则

| 模块 | 数据及判断 | 展示与操作 |
| --- | --- | --- |
| 入口可见性 | 定时任务 created/source 或读取失败、`task-links.created.length > 0`、`subagents.exists`、`plan.exists/planMode`、`todos.exists` 取或 | 任意项存在即显示；Thread 切换先清除旧 Thread 的任务关系判断，再读取新 Thread；临时读取失败保留本 Thread 上次成功判断。 |
| 定时任务 | owner-filtered scheduled-task.v2.thread created/source 投影 | 显示名称、周期、定义状态；来源任务另列本次执行状态。点击关闭弹层，再打开与创建消息相同的详情。 |
| 独立任务会话 | owner-filtered `task-links.created` | 独立卡片按服务端顺序显示标题、状态和进入箭头；点击进入目标业务 Thread。 |
| 任务状态 | `pending`、`failed`、`running`、`idle`、`completed`、`state_unknown` | 分别显示待启动、启动失败、运行中、已结束、已完成、状态待核对。完成只能来自服务端已持久化终态；`idle` 不推断业务完成。 |
| 子智能体 | 当前 Thread 的 `useThreadSubagents` 投影 | 独立卡片显示头像和运行/完成摘要；点击关闭面板并打开现有只读侧栏。 |
| 计划 | `useThreadPlan` | 有计划或规划模式时显示独立卡片，保留 Markdown、模式、更新时间和加载完整能力。 |
| 待办 | `useThreadTodos` | 有待办投影时显示独立卡片，保留 pending、in_progress、completed 圆点、owner、blocked_by 和展开更多能力。 |

入口在 Thread 切换、页面重新可见及可见期间按既有刷新节奏读取任务关系和子智能体。面板打开时读取任务详情。读取关系失败时显示重新加载，不把错误解释为空列表；单项详情失败保留标题并显示“状态待核对”。导航或打开子智能体侧栏时先关闭面板。

## 布局与交互

弹层沿用旧 `PlanPanel`：宽度 `min(26rem, calc(100vw - 1.5rem))`，卡片间距 `0.75rem`。每张卡片使用相同的 1rem 圆角、纸面边框、表面背景、阴影和 `0.85rem 1rem` 内边距。

独立任务卡内部使用 Todo 行节奏，但不与 Todo 共用业务状态：运行中为描边圆和中心点，完成为实心圆和勾，待启动、已结束和待核对为空心圆，失败为错误圆；右侧仍显示服务端文字状态。子智能体、计划和待办各自保留原组件语义。点击外部或 Escape 关闭；所有按钮可由键盘操作；窄屏不能产生页面级横向滚动。

定时任务分区位于其他卡片之前，产品规则由[定时任务对话活动 PRD](../scheduled-tasks/conversation-activity.md)所有。

桌面骨架：

```text
Chat 工具栏 [新建] [活动铃铛] [任务与进度]
                              ┌ 活动弹层（自身滚动） ┐
消息流（独立滚动）            │ 定时任务：时钟/名称  │
创建消息 [任务标记]            │ 周期/状态 → 任务详情 │
                              │ 已创建任务 → 会话    │
输入框                        │ 子智能体 → 原侧栏    │
                              │ 计划 / 待办          │
                              └──────────────────────┘
```

窄屏骨架：

```text
┌ Chat 工具栏 [任务与进度] ─────┐
│ ┌ 活动弹层（视口内滚动） ──┐ │
│ │ 定时任务 ▾ 名称/周期/状态 │ │
│ │ 已创建任务 / 子智能体     │ │
│ │ 计划 / 待办              │ │
│ └─────────────────────────┘ │
│ 消息流（独立滚动）           │
│ 输入框                       │
└─────────────────────────────┘
点击定时任务 → 关闭弹层 → 现有全宽详情
```

## 失败反馈与验收

- 未认证或无 Thread 权限时，接口拒绝读取且页面不泄露其他用户的任务。
- 任务关系暂不可用时显示重试；单项状态失败显示“状态待核对”；已成功读取的列表不会因同一次挂载中的临时错误消失。
- 验收分别覆盖：仅定时任务、仅任务会话、仅子智能体、仅计划、仅待办时图标出现；五项均无且读取成功时图标不出现。
- 验收证明 `PluginReceiptBadge` 仍使用原属性合同和原 Deck 元信息弹层，且其中没有任务、子智能体、计划或待办。
- 验收覆盖任务导航、子智能体侧栏、计划/待办内容、刷新、重开、接口失败、桌面、390px、Escape、外部点击、控制台错误和请求失败。

不在本次范围内：改变任务创建/停止协议、改变 `wait_threads` 完成回传、增加新数据库表、替换子智能体详情侧栏、修改 Deck 元信息产品行为。
