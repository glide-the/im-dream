<!-- [Input] A parent Dream Thread creates independent task Threads and needs their outcomes before the parent turn ends. -->
<!-- [Output] Product rules for wait_threads, parent-turn continuation, attention wakeups, timeout and user-input interruption. -->
<!-- [Pos] Current Claude Agent independent-task waiting PRD; implementation is in docs/design/claude-agent/task-session-completion-handoff.md. -->
<!-- [Sync] 2026-09-28: replace background task-result injection and Chat result cards with an in-turn wait_threads contract. -->

# 独立任务等待与父会话继续 PRD

## 背景与问题

用户在当前对话要求 Agent 创建独立 Thread 执行任务，并在目标完成后继续当前工作。`create_thread` 只确认目标 Thread 已创建并开始运行；它不表示目标任务完成。原方案让后台协调器在父轮次结束后插入技术消息，再在对话区显示独立的 `Task result` 卡片。该方案把任务结果变成另一轮隐藏输入，无法复现 Codex App 的可观察交互：父 Agent 主动调用 `wait_threads`，工具保持等待，子任务终态作为同一父轮次的工具回执返回，父 Agent 随后正常生成回复。

## 目标与边界

- 增加模型 Tool `wait_threads`。父 Agent 可等待 1 至 8 个自己有权访问的 Dream Threads；首个目标完成或需要用户处理时返回。
- `create_thread` 保持非阻塞。父 Agent 需要结果时必须显式调用 `wait_threads`，无需页面轮询结果卡片。
- 等待是当前父轮次中的 Tool 调用。目标结果返回后，SDK 继续同一 Claude 父会话的当前轮次，并产生普通 assistant 回复。
- 用户在等待期间向父 Thread 提交新输入时，等待提前结束；消息仍按既有持久队列和单消费者规则处理，等待回执不宣称该消息已消费。
- 前端继续显示 Thread 来源标记和任务清单，便于导航与查看状态；对话消息区不显示独立 `Task result` 卡片，也不显示后台合成的任务结果用户消息。
- 首期保证单 Dream 进程内的实时唤醒。进程重启后可从已保存消息读取目标终态；跨进程实时 owner 通知仍为部署边界。

## 概念与规则

| 概念 | 所有者 | 规则 |
| --- | --- | --- |
| 父轮次 | ThreadFactory、Runner、SDK | `wait_threads` 返回前保持运行；工具回执进入发起调用的同一模型上下文。 |
| 目标 Thread | Admin Chat 与 ThreadFactory | 每个目标拥有独立 Claude 顶层会话、消息历史和运行 owner。 |
| 等待目标 | `wait_threads.targets[]` | 每项包含业务 `threadId` 和可选 `afterCursor`；不得传用户身份、Claude `session_id`、进程或授权句柄。 |
| cursor | Dream host | 由目标状态、最终消息和待处理 Tool 状态生成的不透明值。相同 `afterCursor` 不再次交付同一最终正文。 |
| 完成 | Admin 已保存最终 assistant 消息 | 必须满足 `turnStatus=completed`、非 partial、最终投影版本和最终正文检查；不得根据自然语言或一帧 SSE 判断。 |
| 需要处理 | 目标 Thread 的本进程运行 owner | 目标存在已确认的 pending Tool 请求时唤醒；前端仍由目标 Thread 的既有确认界面处理。 |

`wait_threads` 默认最长等待 120 秒；`timeoutMs=0` 立即返回当前快照。超时返回所有目标的紧凑状态，不生成虚假完成。每个目标的授权或读取失败写入 `errors`，其他目标仍可继续等待。等待结果至少区分：

- `completed`
- `needs_attention`
- `running`
- `starting`
- `idle`
- `failed`
- `state_unknown`

等待结束原因至少区分 `completed`、`needs_attention`、`timeout`、`input_received` 和 `error`。

## 交互流程

1. 父 Agent 调用 `create_thread`，获得目标业务 `thread_id` 和启动状态。
2. 父 Agent 可继续创建或发送其他任务，然后调用 `wait_threads`。
3. Dream host 重新核实每个目标 Thread 的当前用户权限；同一父 Thread 不能等待自己。
4. 目标运行时保持父 Tool 调用打开。目标保存完成消息、出现待处理 Tool、父 Thread 收到新输入或达到 timeout 时返回。
5. 完成回执包含目标 `thread_id`、标题、状态、cursor、最终消息 ID 和最终正文。若 cursor 与 `afterCursor` 相同，最终正文不重复返回，且该旧终态不再次唤醒非零等待。
6. 父 Agent 读取工具回执并输出普通 assistant 消息。刷新页面只恢复普通消息历史和任务导航，不恢复独立结果卡片。

## 失败反馈

- 目标不存在或无权访问：对应目标返回 `THREAD_NOT_FOUND`，不泄露其内容。
- 等待自身：返回 `THREAD_WAIT_TARGET_INVALID`，避免父轮次等待自身结束造成死锁。
- broker、进程 owner 或持久化读取结果不确定：返回明确错误或 `state_unknown`，不自动重发创建/发送请求。
- 前端断开只断开读取；父 SDK 运行和 wait Tool 仍由服务端 owner 管理。用户停止父轮次会走既有 stop 语义并结束 Tool 调用。
- 目标失败或取消立即以 `wait_reason=error`、`status=failed` 和安全错误码结束本次等待，不伪装为完成；父 Agent 可决定读取目标、发送修正或向用户说明。相同失败 cursor 不重复唤醒。

## 验收

- `create_thread → wait_threads → 父 assistant final` 在同一父 Agent 轮次完成，只有一个父 Chat POST，父 Thread 不出现技术结果用户消息或 `Task result` 卡片。
- 目标完成、需要确认、超时、重复 cursor、用户新输入、目标不存在、未授权目标分别得到明确回执。
- 1 至 8 个目标中首个可操作事件结束等待；timeout 返回全部目标快照；单个目标错误不丢弃其他目标。
- 同一目标的已交付 final 使用 `afterCursor` 不重复正文；新的目标轮次产生新 cursor。
- 现有 Thread 锁、资源 admission、消息持久化、SSE、停止、来源导航和任务清单保持生效。

被替换的“后台结果注入与结果卡片”产品稿保存在 [2026-09-28 历史稿](./task-session-completion-result-push-history-2026-09-28.md)。Chat 结果卡片稿也仅作为历史记录保存在 [Chat 历史稿](../chat/task-session-result.md)。
