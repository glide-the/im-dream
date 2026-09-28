<!-- [Input] create_thread source relations, Chat Thread navigation, and the two user layout references. -->
<!-- [Output] Product rules for source markers and the source conversation's created-task list. -->
<!-- [Pos] Chat module PRD; task ownership and SDK lifecycle remain in ../claude-agent/task-session.md. -->
<!-- [Sync] 2026-09-27: define bidirectional task-session navigation and settled-turn list visibility. -->
<!-- [Sync] 2026-09-27: place the target Thread source action above its first user bubble. -->
<!-- [Sync] 2026-09-27: place the compact created-task list inside the settled assistant reply before message actions. -->
<!-- [Sync] 2026-09-27: mark the assistant-reply list layout historical after the shell information-card consolidation. -->

# Dream Chat 独立任务会话导航 PRD

> 当前展示位置：目标 Thread 的来源标记仍在首条用户消息上方；来源 Thread 的已创建任务清单位于顶部[任务与进度面板](./task-activity.md)。以下创建清单位于助手回复的方案原文保留为历史布局记录，不作为现行验收标准。

## 背景与问题

当前对话可以通过 `create_thread` 或排队消息的“在侧边聊天中打开”创建独立 Thread。目标对话需要返回来源对话的入口，来源对话需要汇总本轮创建的任务；这些导航依赖服务端任务关系，不能依赖模型正文里临时写出的 `task_id`。

## 目标与边界

- 目标 Thread 的首条用户消息气泡上方显示来源导航标记，点击后跳转到来源 Thread。
- 来源 Thread 的 Agent 轮次结束后，在当前最后一条助手回复正文与复制／分享操作栏之间显示该 Thread 创建的任务清单；每行可跳转到对应目标 Thread。
- Agent Tool 创建与排队消息转侧边聊天使用同一份 `chat_task_session` 关系和相同界面。
- 页面只显示标题、业务关系、创建时间和可执行导航；不显示 Claude `session_id`、进程、转录路径、内部调用键或用户身份。
- 本期不增加任务树页面、任务排序编辑、跨用户分享、跨进程运行控制或新的任务状态机。

## 概念与规则

| 概念 | 服务端判断 | 页面行为 |
| --- | --- | --- |
| 来源标记 | 当前 `thread_id` 等于任务关系的目标 Thread，且关系属于当前认证用户 | 在首条用户消息的右对齐容器中、气泡上方显示“由另一项任务创建”；点击后进入 `source_thread_id` |
| 创建任务清单 | 当前 `thread_id` 等于一个或多个任务关系的 `source_thread_id`，且关系属于当前认证用户 | 当前主轮次结束后，附在最新一条助手文本回复的操作栏上方，按创建时间展示；每行显示任务标题和“打开聊天” |
| 轮次运行中 | Dream 当前 Thread 的运行状态由现有 Runtime 状态和 SSE 确认 | 暂不显示来源 Thread 的新清单，避免把尚未完成的 Tool 调用显示成最终结果；目标 Thread 的来源标记仍可显示 |
| 启动失败 | Admin 任务关系 `launch_status=failed` | 清单保留该任务并显示“启动失败”，允许打开目标 Thread 查看已保存的首条消息和错误反馈 |
| 状态待核对 | 关系读取失败或响应字段不完整 | 不猜测关系；保留当前聊天，不把错误当成空清单，提供紧凑的重新加载操作 |

关系查询必须先校验当前用户对当前 Thread 的所有权，再按同一用户过滤来源与目标关系。前端刷新或重连只重新读取关系，不重新创建任务、不发送消息。一个目标 Thread 只显示一条直接来源关系；来源 Thread 可以按创建时间显示多条直接子任务。

## 布局与交互

```text
Chat 消息滚动区
├─ 现有消息列表
│  └─ 首条用户消息（仅目标 Thread）
│     ├─ SourceMarker：关系图标 + 来源标题 + 返回箭头
│     └─ 用户消息气泡
└─ 最新助手回复（仅来源 Thread 且当前轮次已结束）
   ├─ 回复正文
   ├─ CreatedTaskList：标题“此对话创建的任务” + 数量；TaskRow × N
   └─ 现有复制／分享等消息操作栏
```

来源标记使用弱化文字和透明按钮表面，与首条用户消息共用右对齐容器，置于气泡上方，不遮盖气泡。若首条消息尚未进入当前分页，或当前没有用户文本消息，列表顶部暂时保留同一个导航入口；加载到首条消息后，入口移入该消息容器，不重复显示。任务清单使用助手回复的可用宽度，放在正文和操作栏之间；标题区与任务行保持紧凑，按钮维持至少 44px 点击尺寸。窄屏上任务标题可以截断，状态和“打开聊天”仍保持可见，整行不能产生横向滚动。当前消息列表没有可放置清单的助手文本时，在列表末尾显示同一份清单，不丢失导航。键盘焦点、Enter/Space 激活和清晰焦点框必须可用。

视觉样稿见 [task-session-navigation-visual.html](./task-session-navigation-visual.html)。样稿只表达层级、密度与响应式行为；生产实现继续复用 `ChatPanel`、当前 Thread 选择和侧边任务聊天组件。

## 失败反馈与验收

未认证、无 Thread 权限或关系不属于当前用户时，接口返回既有认证/404 边界，页面不得泄露标题或 Thread ID。读取暂时失败时显示“任务关系暂时无法读取”和“重新加载”，不影响消息、输入框或停止操作。

验收至少覆盖：Tool 创建目标 Thread 后标记位于首条用户消息容器、气泡上方；标记跳回来源 Thread；分页尚未包含首条消息时仍有入口且不重复；来源轮次结束后清单位于最新助手回复的操作栏上方并与回复等宽；点击行进入正确目标 Thread；启动失败任务仍可查看；运行中暂不显示新增清单；刷新和 SSE 重连恢复同一关系；无关系时不占位；未授权关系不可读取；桌面与 390px 窄屏无溢出。
