# Claude Agent 前端主动停止交互方案

> **版本**: 2026-06-25 v1 — 最小实现稿  
> **关联代码**:
> - `frontend/src/components/chat/ChatPanel.tsx` — 停止按钮动作与前端流中断
> - `frontend/src/components/chat/AIInputDock.tsx` — 停止中按钮状态
> - `backend/routers/claude_agent.py` — `POST /api/claude-agent/threads/{thread_id}/stop`
> - `backend/claude_agent/thread_factory.py` — 当前 turn 取消与完成确认
> - `backend/claude_agent/service.py` — 取消路径的部分消息持久化与 SSE 收尾

> Stop 仍是拥有 active turn 的
> **[Sync 2026-08-11 / current deployment boundary]** Stop 仍是拥有 active turn 的
> `ClaudeAgentThreadFactory` 进程内控制操作。active-turn registry、`/status`、pending
> confirmation Future 和 HTTP stream routing 都没有迁入 Redis。Redis EventBus 只为
> 已知 `(session_id, turn_id)` 共享事件 replay/writer/单终态，不能定位或取消另一个
> Worker/Pod 的 task。当前 backend Dockerfile 启动单个 uvicorn worker，Cloud Run
> backend 固定 `--max-instances=1`，因此当前 Stop 契约成立；未来放宽部署并发前必须
> 先增加分布式 owner discovery/routing/Stop/confirmation 设计与验收。另，Stop 响应
> 不确定时的当前 UI 契约是保持输入锁并 status+reconnect，不能因为本地 reader 已
> abort 就宣称 cancelled。

## 1. 问题判断

当前“前端无法主动停止 Agent”的根因不是 Claude SDK session ID 持久化本身，而是 2026-06-09 的 SSE 重连设计改变了断线语义：

1. `ChatPanel` 的停止按钮只调用 AI SDK `stop()` 并 abort 本地 reconnect fetch。
2. `ClaudeAgentThreadFactory.run_streaming()` 在客户端断开时只 `unsubscribe` 当前 SSE reader。
3. 后台 `state.bg_task` 会继续执行 `ClaudeAgentService.execute_session()`，以便刷新页面或切换会话后可以通过 `GET /threads/{id}/stream` 重连。
4. 因此前端“停止生成”只停止了本地消费流，没有向后端表达“用户要终止当前 turn”。

应处理的位置：

| 层 | 处理方式 |
|---|---|
| 前端 Chat UI | stop 按钮同时中断本地流并调用后端 stop API |
| 后端 Route | 校验 thread 属于当前用户后转发停止请求 |
| ThreadFactory | 取消当前 `bg_task`，不删除 chat thread |
| Service | 在 `CancelledError` 路径 flush 已收集 assistant parts，并发布 SSE 收尾 |
| DB 持久化 | 沿用现有 `_persist_partial_assistant`，不新增表或状态列 |

## 2. 目标与非目标

目标：

| 目标 | 方案 |
|---|---|
| 前端可主动停止正在运行的 Agent | 新增拥有鉴权和 thread 所有权校验的 stop API |
| 不破坏 SSE 重连 | 普通断线仍只 unsubscribe；只有 stop API 会 cancel 后台 turn |
| 保留已生成内容 | 复用 `_persist_partial_assistant` 保存部分 assistant parts |
| 避免消费者挂住 | 取消路径发布 `finish` 和 sentinel，关闭 EventBus reader |
| 保持最小改动 | 不新增全局任务队列、durable cancellation 表、Redis replay 或复杂状态机 |

非目标：

| 非目标 | 原因 |
|---|---|
| 删除 Claude SDK session / chat thread | 停止当前 turn 不等于删除会话 |
| 关闭所有用户会话 | stop API 只作用于当前 thread |
| 持久化“stopping/stopped”业务状态 | 当前需求只需要实时控制；权威历史仍是 `chat_message` |
| 替换 EventBus 重连架构 | 重连是现有目标能力，停止应作为显式控制命令加入 |

## 3. 交互方案

### 3.1 前端状态

| 状态 | 触发 | UI |
|---|---|---|
| `running` | `useChat.status` 为 `submitted/streaming` 或 reconnect 中 | 显示停止按钮 |
| `stopping` | 用户点击停止，stop API 请求未返回 | 停止按钮禁用，显示加载图标，输入保持不可发送 |
| `stopped` | history/status 恢复证明当前主 turn 已 idle/terminal | 停止按钮消失，恢复输入 |
| `failed/uncertain` | stop API 非 2xx、超时、响应畸形或 `running=true` | 保持输入锁；立即读取 status 并重连当前 thread stream，直到权威 idle/terminal 后才声明 cancelled |

前端点击停止时执行：

1. abort 当前 reconnect fetch。
2. 调用 AI SDK `stop()` 中断当前浏览器流消费。
3. `POST /api/claude-agent/threads/{thread_id}/stop`。
4. API 返回后触发一次 thread message reload，让 UI 看到部分持久化结果。

并发点击处理：`stopping` 为 true 时停止按钮禁用，重复点击不发第二个请求。

### 3.2 后端 API

```http
POST /api/claude-agent/threads/{thread_id}/stop
Authorization: Bearer <token>
```

响应：

```json
{
  "ok": true,
  "thread_id": "thread-id",
  "stop_requested": true,
  "running": false,
  "lifecycle": "idle"
}
```

语义：

- `404`: thread 不存在或不属于当前用户。
- `200 + stop_requested=false`: thread 当前没有运行中的 in-memory turn，接口保持幂等。
- `200 + stop_requested=true`: 已向当前 turn 发出取消请求。
- `running=true`: 后端已请求取消，但在配置的等待窗口内任务尚未完全退出。

等待窗口由 `INK_AGENT_STOP_WAIT_S` 配置，默认值在 ThreadFactory 层集中定义，避免在路由或前端硬编码策略。

### 3.3 SSE 与持久化

取消路径沿用 `execute_session()` 的 `CancelledError` 分支：

1. 调用 `_persist_partial_assistant()` 保存已收集的 reasoning/tool/text parts。
2. 向 EventBus 发布 `finish`，`finishReason="stop"`。
3. 发布 sentinel `None` 关闭所有 active/reconnect reader。
4. `_run_turn_task()` finally 清理 `turn_context/event_bus/bg_task` 并把 lifecycle 从 `running` 标为 `idle`。

不发布 `error`，因为用户停止是预期操作，不应显示为失败。

## 5. 验收标准

1. 点击 Chat 输入框停止按钮会调用后端 stop API，而不是只 abort 浏览器流。
2. 后端运行中的 `bg_task` 被取消，`GET /threads/{id}/status` 不再持续返回 `running=true`。
3. 取消过程中已产生的 assistant parts 会以 `metadata.is_partial=true` 保存。
4. SSE active/reconnect reader 收到 `finish` 后结束，不再靠 keepalive 挂起。
5. 未运行时调用 stop API 返回 200，且 `stop_requested=false`。
6. 不影响普通断线重连：没有调用 stop API 的 tab 切换、刷新、网络断开仍保持后台 turn 可重连。
