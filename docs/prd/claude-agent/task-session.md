<!-- [Input] Independent Dream Thread requirement, four Thread Tools, and Chat side-task action. -->
<!-- [Output] Product rules for creating, listing, reading and continuing separate Dream Threads. -->
<!-- [Pos] Claude Agent task-session PRD; technical lifecycle belongs to docs/design/claude-agent/task-session-tools.md. -->
<!-- [Sync] 2026-09-27: link the module-owned Chat queue PRD. -->
<!-- [Sync] 2026-09-27: define four Tool actions and side-chat behavior by business task identity. -->
<!-- [Sync] 2026-09-27: add direct source/target conversation navigation to every persisted task relation. -->
<!-- [Sync] 2026-09-27: record normal-account end-to-end acceptance of all four Tools and independent Claude session ownership. -->
<!-- [Sync] 2026-09-28: replace model task_session_* actions with create/list/read/send Thread actions. -->
<!-- [Sync] 2026-09-28: execute authorized Thread orchestration directly in Auto/full-access mode while preserving manual confirm-each-step. -->
<!-- [Sync] 2026-09-28: add wait_threads and replace automatic result return with parent-turn waiting. -->

# Claude Agent 独立任务会话 PRD

独立任务完成后继续父会话的产品规则见 [`wait_threads` PRD](./task-session-completion.md)。本稿的任务创建与 `read_thread` 不等于等待完成。

## 背景与问题

Agent 需要在当前对话之外创建、查询和继续一个独立任务。当前对话中的排队消息也可以由用户移到侧边聊天。两种入口都必须创建新的 Dream 业务 Thread，并让它拥有独立 Claude 顶层会话；Claude Code 的子代理和任务清单不代表此业务任务。

## 目标与边界

- Agent 使用 `create_thread`、`list_threads`、`read_thread`、`send_message_to_thread`、`wait_threads` 操作业务 Thread；用户使用 Chat 排队卡片的“在侧边聊天中打开”创建独立任务。创建入口共享受权来源关系，读取、发送和等待按当前用户对目标 Thread 的权限执行。
- 每个目标 Thread 显示返回来源对话的导航标记；来源 Thread 在当前轮次结束后显示由它创建的直接任务清单。两端都从服务端持久化关系读取，不解析模型正文。
- 页面和 Tool 结果只展示业务 `task_id`、任务状态、可查看的消息及安全错误。Claude `session_id`、进程 ID、转录路径和内部取消句柄不对外显示。
- 首期按单 Dream 进程 owner 执行运行中控制；其他进程无法确认运行状态时显示“状态待核对”。跨进程控制、任务归档、附件排队不在本期范围。

## 概念与规则

| 操作 | 输入与权限 | 业务结果 |
| --- | --- | --- |
| 创建 | 当前 Agent 轮次身份与来源 Thread 由服务端绑定；模型提供 `prompt` 和可选标题 | 创建唯一来源关系与独立 Thread，非阻塞开始首轮；重复同一调用返回同一 `thread_id`，内部 `task_id` 不进入模型协议 |
| 列表 | 模型可提供查询文本和数量；服务端使用当前身份 | 返回当前用户拥有的 Thread 摘要；列表不启动推理 |
| 读取 | 模型提供业务 `thread_id`；服务端核实目标 Thread 权限 | 返回近期已保存消息及 `starting/running/idle/failed/not_started` 状态；读取不启动推理 |
| 发送 | 模型提供业务 `thread_id` 和消息；同一调用保持同一消息 ID | 运行中进入目标 Thread 队列；空闲且会话可恢复时开始后续轮次；结果不明时不自动重发 |
| 等待 | 模型提供 1 至 8 个业务 `threadId`、可选 cursor 和 timeout | 父 Tool 调用保持运行；首个目标完成或需要处理时返回，超时提供所有快照，新父输入提前结束等待 |
| 停止 | 用户从现有页面/API 操作；服务端复核目标 Thread 权限 | 请求停止当前轮次，只有核实终态后才显示已停止；模型不获得停止 Tool |
| 移至侧边聊天 | 用户选取仍为 `queued` 的卡片；服务端核对 revision | 原 Thread 取消该消息的排队消费，并以相同正文创建新任务的首条输入；侧边显示独立聊天 |

任务状态至少区分 `pending`、`starting`、`running`、`completed`、`idle`、`failed`、`state_unknown` 与停止请求。`completed` 只来自目标最新助手消息的已保存最终投影；创建回执只证明任务和 Thread 已持久化，`starting` 不等于 Claude 已完成首轮。侧边聊天刷新后从服务端读取历史与运行状态。原消息转移后留在原 Thread 的历史记录中，但不再由原 Thread 消费。

## 失败反馈与验收

身份或来源 Thread 权限不足时拒绝读取和写入；Admin schema capability 缺失、启动失败和 owner 丢失时给出可区分的安全错误。消息或启动结果不明时，页面与 Tool 先查询已持久化状态，不自动创建另一个 Thread 或重复发送。Auto 与完全访问模式不为普通创建、发送或取消增加确认弹窗；用户明确选择“每步确认”时，创建和发送继续进入现有工具确认面板。

验收覆盖五个 Thread Tool 的受权操作、旧工具未注册、同一调用幂等、任务与 Thread 一一绑定、首轮独立 Claude 会话、后续会话恢复、运行中排队、父轮次等待、页面停止请求与核实终态、用户侧边转移、来源导航、结束后任务清单、刷新恢复，以及未授权读取、发送和等待。输入卡片的具体视觉和菜单见 [Chat 运行中消息排队 PRD](../chat/queued-input.md)，两端导航见 [Chat 独立任务会话导航 PRD](../chat/task-session-navigation.md)；状态机与 SDK 生命周期见 [独立任务会话设计](../../design/claude-agent/task-session-tools.md)。

2026-09-27 的正常账户验收使用已退役 `task_session_*` 协议，作为底层独立 Claude 会话、排队、恢复和页面停止路径的历史证据。2026-09-28 的后台结果交付验收也只作为历史证据；现行路径要求 `create_thread` 后由父 Agent 调用 `wait_threads`，结果作为同一 Tool 回执继续父轮次。`list_threads`、`read_thread` 和 `send_message_to_thread` 的权限、幂等和队列合同由生产入口的确定性测试覆盖；超过用户 access token 有效期的单个超长来源轮次仍受设计稿所列可续期授权 capability 边界约束。排队卡片侧边创建 Thread 的页面路径保持不变。
