<!-- [Input] A source Dream Thread creates an independent task Thread and expects its completed result in the source conversation. -->
<!-- [Output] Product rules for child-task completion, source notification, Agent continuation, and visible failure states. -->
<!-- [Pos] Historical task-result push PRD; superseded by task-session-completion.md. -->
<!-- [Sync] 2026-09-28: preserve the superseded background result injection and result-card product rules. -->
<!-- [Sync] 2026-09-27: define result handoff separately from task creation and navigation. -->
<!-- [Sync] 2026-09-28: source continuation preserves the Thread-bound Deck/Voice selection and reports a failed context read before SDK submission. -->
<!-- [Sync] 2026-09-28: normal-account real-model acceptance verifies 0068 result delivery; server task-result turns ignore browser-cached Editor state without erasing it for later user turns. -->

# 独立任务完成后返回来源对话 PRD（历史稿）

> 本稿不再是现行产品规范。当前行为见 [`wait_threads` PRD](./task-session-completion.md)。

## 背景与问题

用户在来源对话里要求 Agent 创建独立会话，让新会话查询今天的 Notion 笔记，并把结果返回当前对话。`create_thread` 会创建新 Thread，`read_thread` 只在调用瞬间读取状态。来源 Agent 可以在新 Thread 结束前完成自己的回复，因此仍需要独立的完成事件和结果投递，不能只留下“稍后返回”的承诺。

2026-09-27 对 `dmeck@suoxya.com` 的正常数据库做只读核对：来源 Thread `a9ad292c-5d1c-4ee0-b7e7-214f802b6cab` 创建任务 `41869865-9e53-4fbc-af28-793fbd079d4f`，目标 Thread `58537f5d-a827-4907-986e-647fd5eb2201`。来源回复于 14:59:37 UTC 完成；目标的最终助手消息于 15:00:03 UTC 保存，元数据 `turnStatus=completed`。目标已得到 Notion 查询结果；来源没有后续消息。本文不复制笔记正文。

## 目标与边界

- 模型通过 Tool 创建的独立任务完成后，来源对话自动出现一条带任务标题、结果摘要和“打开任务会话”的通知；用户无需手动调用 `get`、刷新或留在页面。
- 来源 Agent 可在原 Claude 会话上消费任务完成结果并继续回应用户。该动作由服务端任务结果队列领取，进入现有 ThreadFactory 锁与 admission 路径；不得另建 Claude 会话或抢占当前轮次。
- 来源 Thread 绑定 Deck/Voice 时，后续轮次沿用该 Thread 当前绑定的配置；配置读取或权限校验失败时不得启动 SDK，也不得退化为无 Deck 的回复。
- 服务端任务结果续跑不继承进程内缓存的浏览器 Editor 快照。该快照只属于显式携带或继承它的普通用户轮次；任务结果轮次跳过 Editor 上下文，但不清除缓存，后续普通用户输入仍可继续使用。
- 用户消息与任务结果分开标记。任务结果必须由服务端根据任务关系和目标轮次终态生成，模型文本“已经完成”不构成完成证据。
- 同一个目标轮次的完成结果最多投递一次。来源 Thread 停止当前轮次、浏览器断开或 Dream 重启，不删除未投递结果；结果不确定时显示待核对，不自动重发给 SDK。
- 普通 Chat 侧边任务是否回传结果由创建入口的产品规则明确设定，默认只做导航；模型 Tool 创建且用户要求“返回当前对话”的任务默认回传。后续可让用户在卡片中开启回传，不在本期增加确认弹窗。

## 概念与规则

| 概念 | 判断和所有者 | 用户可见行为 |
| --- | --- | --- |
| 任务关系 | Admin 保存 `task_id`、来源与目标 `thread_id`、创建入口和回传约定 | 两个对话均可导航 |
| 目标轮次终态 | Dream 收到 SDK 终态，并在 Admin 保存该轮最终助手消息 | 目标显示“已完成”或明确失败；`starting` 仅代表已请求启动 |
| 完成通知 | Admin 以 `(task_id, target_turn_id)` 去重，保存目标最终消息 ID、来源 Thread 和交付状态 | 来源显示一条独立的任务结果卡片，链接到目标 |
| 来源 Agent 续跑 | Admin 为结果生成来源输入与受限授权；Dream 按来源 Thread 的现有锁、admission 和 SDK 恢复合同消费结果 | Agent 根据任务结果给出后续回复；没有授权或 owner 时保持通知待处理 |

任务通知状态为 `pending`、`dispatching`、`delivered`、`failed`、`state_unknown`。`pending` 表示完成结果已保存但尚未派发；`dispatching` 表示来源输入已被唯一消费者领取；`delivered` 仅在来源 SDK 回执和消息持久化都成功后成立；`failed` 表示可确认未送入 SDK；`state_unknown` 表示超时、进程失联或回执不完整，禁止自动二次派发。页面把通知状态与目标任务状态分别展示，不把“已创建”“已启动”当作“已完成”。

## 交互与失败反馈

1. 来源 Agent 创建任务后可以结束当前回复。清单显示“进行中”，不承诺已返回结果。
2. 目标轮次完成时，Admin 在保存最终助手消息的同一事务中持久化结果通知。来源页面即使曾断开，也可通过受权状态查询恢复通知卡片。
3. 来源正在生成时，通知默认等待现有 Thread 锁；当前轮次自然结束后消费。若来源空闲，服务端用原 `session_id` 开启一个后续轮次。两个 Thread 可以并发，但每个 Thread 仍只有一个消费者。
4. 目标失败、取消、没有最终助手消息、权限失效或结果状态不确定时，页面显示相应状态并保留导航，不捏造摘要。用户可打开目标 Thread 查看详情。
5. 用户停止来源轮次只停止该轮次；已持久化的任务结果仍在来源待处理列表。用户停止目标轮次不把 `stop_requested` 当作结果终态。

## 验收

- 使用现有认证账户经公开入口创建来源与目标 Thread，目标完成后来源收到且只收到一条结果卡片；刷新、重连、重复回执不增加副本。
- 来源正在运行、空闲和进程重启三种情况下，任务结果不丢失；只有核实 SDK 消费后才标记 `delivered`。
- 目标失败、取消、空回复、来源被删除、授权过期、跨进程 owner 不可用分别给出安全状态；不得以用户身份伪造任务结果。
- 未授权账户不能读取目标结果、通知或启动来源续跑；`read_thread` 与其他 Thread Tool 的身份和幂等合同保持有效。
- 浏览器和服务端自动化覆盖完整任务链，不以单个 2xx 或一帧 SSE 判断成功。

2026-09-28 已使用正常运行的 Admin、Dream、前端、`ink-memory` 数据库和现有账户 `dmeck@suoxya.com` 完成可见 Chat 真实模型验收：`create_thread` 创建独立目标 Claude 会话，目标终态生成 0068 结果，来源以原 Claude 会话续跑并保存最终回复，页面显示结果卡片、来源标记和双向任务导航。测试保留本轮 Thread、Run 与日志供正常 Admin 复核；未读取或复制外部 Notion 正文。

技术方案与当前缺口见 [独立任务结果交接设计](../../design/claude-agent/task-session-completion-handoff.md)。
