<!-- [Input] Chat queued-input PRD, current Thread queue, SDK session lifecycle, and server-owned actor delegation. -->
<!-- [Output] Thread Tool and side-thread architecture, state transitions, auth boundaries, and acceptance. -->
<!-- [Pos] Current Claude Agent task-session design; product card behavior is owned by docs/prd/chat/. -->
<!-- [Sync] 2026-09-27: link the module-owned Chat queue PRD after its folder move. -->
<!-- [Sync] 2026-09-28: add wait_threads as the parent-turn completion contract and retire background result injection. -->
<!-- [Sync] 2026-09-28: replace the four model task_session_* tools with create/list/read/send Thread tools; keep Admin relations and queue ownership. -->
<!-- [Sync] 2026-09-27: define four task-session tools and queued-message transfer to independent top-level Claude sessions. -->
<!-- [Sync] 2026-09-27: expose owner-filtered source/created relations for Chat navigation without a new schema. -->
<!-- [Sync] 2026-09-27: record normal-account real-model acceptance of create/get/send/stop and side-thread transfer. -->
<!-- [Sync] 2026-09-28: separate short-turn Tool acceptance from the unverified OAuth-expiry behavior of long-running source turns. -->

# 独立任务会话与 Tool 设计

任务创建后的完成等待见 [`wait_threads` 设计](./task-session-completion-handoff.md)。本稿的 `read_thread` 是即时读取；需要在同一父轮次取得结果时使用 `wait_threads`。

产品规则见 [Claude Agent 独立任务会话 PRD](../../prd/claude-agent/task-session.md)；Chat 卡片的视觉和菜单见 [Chat 运行中消息排队 PRD](../../prd/chat/queued-input.md)，来源标记与任务清单见 [Chat 独立任务会话导航 PRD](../../prd/chat/task-session-navigation.md)。

## 背景与问题

现有 Dream Thread 已有运行中持久化输入队列。此前模型暴露的 `task_session_create/get/send/stop` 以 `task_id` 操作独立任务，无法按 Thread 语义列出、读取和继续已有会话。Chat 卡片的“在侧边聊天中打开”仍需要受权任务来源关系；Claude 子代理或 TaskCreate 清单不代表独立 Thread。

## 目标与边界

每个由来源会话创建的 `task_id` 唯一绑定一个新 Dream `thread_id`；模型以业务 `thread_id` 列出、读取和发送至当前用户有权访问的 Thread。新 Thread 首轮启动 SDK 不传 `resume`，从 init 回执保存该 Thread 自己的 Claude `session_id`。Tool 只收业务 Thread ID 与内容，身份、来源 Thread、调用幂等键由服务器当前轮次注入。首期仅承诺单 Dream 进程 owner；跨进程路由、定时调度和子代理不在本次范围。

## 概念与规则

| 概念 | 所有者 | 行为 |
| --- | --- | --- |
| 任务记录 | Admin PostgreSQL | `task_id` 绑定 owner、来源 Thread、新 Thread 与创建调用键；提供受权查询。 |
| 输入消息 | Admin Chat | `message_id` 去重、队列排序与状态持久化；目标 Thread 复用既有队列。 |
| Claude 会话 | SDK 与 Admin Thread | init 提供真实 ID；后续输入沿用保存的 `session_id`，不接受 Tool 指定。 |
| 运行 owner | Dream ThreadFactory | 每 Thread 最多一个消费者；不同 Thread 可并发，仍受既有 admission 约束。 |

Admin 新增只读 `task-session.links` 操作，输入当前业务 `thread_id`，先校验当前认证用户拥有该 Thread，再返回可选直接来源关系和该 Thread 创建的直接任务数组。查询只投影业务 Thread ID、任务 ID、标题、创建时间和已持久化启动结果；不读取 Claude 会话或运行进程。Dream 的公开 Thread 路由继续通过 `AdminChatData` 调用该操作，前端只在当前轮次结束后刷新创建任务数组；刷新、重连和点击导航都不触发模型调用。

原 Thread 队列消息转侧边时，Admin 在同一事务中比较 `revision`、将 `queued → cancelled`、创建任务及目标 Thread；随后 Dream 独立派发首条输入。派发失败可按 `task_id` 查询失败或待核对状态，不将原消息放回队列。`selected/dispatching/consumed/cancelled/failed/state_unknown` 都不可转移。

## Tool 协议

| Tool | 模型参数 | 结果 |
| --- | --- | --- |
| `create_thread` | `prompt`, optional `title` | 仅在用户要求独立会话时幂等创建来源关系及新 Thread，非阻塞启动首轮；返回 `thread_id` 和启动状态，内部 `task_id` 只用于导航与完成交接。 |
| `list_threads` | optional `query`, `limit` | 通过 Admin owner 过滤的列表或搜索操作返回当前用户的 Thread 摘要，不启动推理。 |
| `read_thread` | `thread_id` | 先检查目标 Thread 权限，再返回已保存消息及明确的运行状态，不启动推理。运行中不把旧助手回复当成本轮结果。 |
| `send_message_to_thread` | `thread_id`, `prompt` | 先检查目标 Thread 权限，再进入既有运行中排队或空闲恢复路径；同一调用 ID 不重复保存。 |
| `wait_threads` | `targets[{threadId, afterCursor?}]`, optional `timeoutMs` | 保持当前父 Tool 调用，等待最多 8 个目标中首个已保存完成或需要处理的事件；超时返回全部快照，新父输入提前结束等待。 |

旧四个 `task_session_*` 名称不再注册为模型 Tool，也不列入 Runtime 权限名单。停止保留现有页面/API 操作。Round52 同时描述标题、置顶和归档；Admin 当前有受权修改标题操作，但没有置顶、归档的 Chat capability，本轮仅增加当前可验证的五个 Thread Tool，不注册其余名称。Round52 的项目目标与模型覆写参数属于 Codex App 合同，不映射成 Dream 参数。

Tool 子进程只接收当前轮次私有 broker capability；主进程持有已认证 actor 与来源 Thread，核实权限、任务关系和授权有效期。模型不能传入用户 ID、Claude `session_id`、进程句柄或授权凭据。Admin schema capability 缺失时拒绝任务写入，不在 Dream 建表。

当前宿主 Tool provider 捕获来源轮次开始时的浏览器 OAuth actor；只有新的同一用户工具确认请求才会刷新它。Admin access token 的 300 秒有效期意味着来源轮次运行超过该时长且没有确认时，Thread Tool 可能无法访问 Admin。目标能力应使用可续期的、当前用户和来源 Thread 绑定的服务端授权，并在每次 `read_thread`、`send_message_to_thread` 或 `wait_threads` 时重新核实目标 Thread owner；不能让来源 grant 直接读取或写入任意目标 Thread。该能力未完成前，短时真实业务回执不能证明超长轮次、前端断连后的 Tool 可用性。

## 失败与恢复

创建/转移采用服务端幂等键；结果不明时按该键查询，不自动再次派发。页面刷新读取 Admin 任务与消息，不把前端断连判作停止。进程重启后保存的 `session_id` 允许既有 Thread 经受权恢复，但运行 owner 丢失时停止或主动引导需报告 `state_unknown`，不得宣称已中断。模型 Tool 请求不得绕过 Thread 锁、admission、权限、消息持久化或事件流。

## 目标符合性评审

必须实现 Admin 来源关系和受权四个 Thread Tool、侧边转移、同一 Runtime/Thread 队列入口、幂等、状态查询、来源导航和结束后任务清单。可延后跨进程 owner 路由、置顶、归档、任务树和附件排队。明确不实现分布式队列、远程控制平面、模型停止工具、shell 停止和额外确认弹窗。现有 `dream.chat-task-session.v2` 已包含创建来源关系字段，因此本次不新增 migration；capability 缺失时 Dream 对创建和关系读取 fail closed，不能假报成功。

验收覆盖任务与 Claude 会话一一对应、五个 Thread Tool 的身份权限和幂等、运行中发送、父轮次等待、默认队列、页面停止终态、侧边转移竞争、刷新恢复、跨 Thread 并发和 capability 缺失。自动化合同测试走生产 DTO、隔离数据库和 fake SDK。现行等待合同的独立验收见 [`wait_threads` 设计](./task-session-completion-handoff.md)。
