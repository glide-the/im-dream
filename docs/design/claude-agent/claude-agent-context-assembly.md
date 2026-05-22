> **迁移来源**: Pawkeyland docs/app/design/claude-agent上下文拼接设计.md — 路径和环境变量已适配 Ink & Memory 工程规范。

# Claude Agent 上下文拼接设计

> **迁移来源**: Pawkeyland docs/app/design/claude-agent上下文拼接设计.md — 路径和环境变量已适配 Ink & Memory 工程规范。

> 当前状态：2026-05-12 实现对齐版。本文是设计参考；接口字段真源仍以 `../api-calling-guide.md` 为准，上下文运行真源以 `../chat-context-assembly-flow.md` 为准。

> [Sync] 2026-05-12: Thread Session 享元化后，上下文拼接成为 Phase 1 (Context Assembly) 的唯一职责，由 `ClaudeAgentService.assemble_context` 统一持有；`system_prompt` / `cwd` 在首轮组装后回写到 `AgentRunState` 享元，续轮短路复用。`user_message` / `AgentRunOptions` / `AgentStreamingCallbacks` / `_TurnContext` 仍每轮重建并由 Phase 4 销毁。详见 [claude-agent-thread-session-patterns.md](./claude-agent-thread-session-patterns.md)。

## 1. 当前入口

Claude Agent 主链路只有 `POST /api/claude-agent`。HTTP 请求不暴露客户端 prompt 字段，不接收 `conversation_id`，也不接收 `history` / `chat_history`。

会话键路由：

```text
user_id
  -> chat_session(user_id)
  -> claude_session_id（续接 ID）
```

> _(Pawkeyland 原文中的 `pet_persona` / `pet_id` 路由链，属于 Pawkeyland 专属，Ink & Memory 中不适用)_

## 2. 上下文构建职责

实现文件：`backend/claude_agent/context_builder.py`（被 `backend/claude_agent/service.py::ClaudeAgentService.assemble_context` 调用）。

构建器只产出两个字符串：

| 输出 | 消费方 | 说明 |
|---|---|---|
| `system_prompt` | `AgentRunOptions.system_prompt` | 会话级规则、语气、工具规则、媒体策略 |
| `user_message` | `AgentRunOptions.user_message` | 本轮原始用户文本；UTC Date、模型、session 和本地时间等运行态由 SDK runtime context content block 承载 |

`ClaudeAgentService.assemble_context()` 在 Phase 1 内部完成拼接、构造 `AgentRunOptions` / 5 个 `AgentStreamingCallbacks` / `_TurnContext`，并把全部组件发布到享元 `AgentRunState`；Phase 3 (`execute_session`) 再把 carrier 中的 `runner` / `opts` / `callbacks` 交给 `backend/claude_agent/runner.py::ClaudeAgentRunner`。

### 2.1 享元短路（Thread Session 模式）

`ClaudeAgentService.assemble_context` 用三层级解析顺序处理 intrinsic 字段，首轮构建后写回 `AgentRunState`，续轮短路：

| 字段 | 三层解析顺序（从优先级高到低） | 享元写回点 |
|---|---|---|
| `state.system_prompt` | ① 享元已缓存；② `_context_builder.system_prompt(...)` | 首轮 → `state.system_prompt` + `state.agent_contract_version` |
| `state.cwd` | ① 享元已缓存；② `request.cwd` 显式覆盖；③ `get_or_create_workspace(workspace_key)` | 首轮 → `state.cwd` |

> _(Pawkeyland 原文中还包含 `state.resolved_identity` / `state.persisted_pet_info` / `state.mem0_user_id` 的享元字段，属于 Pawkeyland 专属，Ink & Memory 中不适用)_

> **bare Service 调用**（`state is None`）：每次都走重建分支；不写回（每次调用独立）。

### 2.2 每轮重建的 extrinsic 字段

| 字段 | 构造时机 | 销毁时机 |
|---|---|---|
| `state.user_message` | Phase 1 内 `_context_builder.user_message(...)` | Phase 4 finally |
| `state.callbacks` | Phase 1 内构造 `AgentStreamingCallbacks` 5 闭包（绑定 `state.turn_context` 内累加器） | Phase 4 finally |
| `state.run_options` | Phase 1 内构造 `AgentRunOptions(thread_id, cwd, system_prompt, tool_choice, ...)` | Phase 4 finally |
| `state.turn_context` | Phase 1 内 `_TurnContext(queue, accumulators, latency tracker, pending_confirmation_ids, ...)` | Phase 4 finally |

> _(Pawkeyland 原文中 `_TurnContext` 还包含 `sticker filter`，属于 Pawkeyland 专属，Ink & Memory 中不适用)_

> "Phase 4 finally" 指每轮 `_run_lifecycle.finally`。它**不**触发 Phase 4 (Session End) 观察者钩子 —— 后者由 `_fire_session_ended` 在 `close_thread` / TTL Sweeper / `aclose` 三条 State 销毁路径上各发一次。

## 3. system_prompt 拼接顺序

当前顺序固定为：

```text
prompts/agent/system_base.txt
prompts/agent/system_tools.txt
prompts/agent/system_policies.txt
<long_term_profile>...</long_term_profile>
```

前三个文件是稳定政策前缀，放在动态 memory 之前，以便大模型服务复用更长的 prefix cache。

> _(Pawkeyland 原文中还包含 `<character_card>` / `<virtual_character>` 块，属于 Pawkeyland 专属，Ink & Memory 中不适用)_

### 3.1 `system_base.txt`

定义 Ink & Memory AI 助手的身份、输出节奏、事实核源、共情边界和情绪价值策略。

### 3.2 `system_tools.txt`

定义 Agent 工具边界，包括允许使用的 MCP 工具列表及零参数只读意图工具的调用规范。

> _(Pawkeyland 原文中包含 `mcp__user__touch_animation` / `mcp__necklace__*` 等宠物专属工具，属于 Pawkeyland 专属，Ink & Memory 中不适用)_

### 3.3 `system_policies.txt`

定义输出格式规范、工具策略和 text 情绪协同规则。

> _(Pawkeyland 原文中包含动画 act 枚举、贴纸枚举、`[sticker:sticker_id]` token 合同，属于 Pawkeyland 专属，Ink & Memory 中不适用)_

### 3.4 `long_term_profile`

来源优先级：

1. 请求显式传入 `long_term_profile`，仅调试/Demo 使用；
2. 服务端按 `user_id` 从记忆服务读取；
3. 没有则不注入。

长期画像是半静态上下文，放在 `system_prompt`，不重复塞入每轮 `user_message`。

> _(Pawkeyland 原文中从 `PetMemoryService` 按 `user_id + pet_persona` 读取，Ink & Memory 简化为按 `user_id` 读取)_

## 4. user_message 拼接

模板文件：`prompts/agent/user_message.txt`。

当前模板只有一个占位符：

```text
<user_turn>
{user_message_block}
</user_turn>
```

构建器填充：

```text
[user_message]
{本轮用户文本}
```

UTC Date、模型、最大 turn、session id 和 resume 状态由 SDK message builder 的 `<runtime_context>` content block 提供；服务端还会把 `curr_time` 和会话时区写进同一个 block，不在 app prompt 中重复注入。

以下内容不会进入 `user_message`：

- `long_term_profile`
- `user_id`
- 任何外部实时 JSON 原始数据

> _(Pawkeyland 原文中还排除了 `pet_persona.profile` / `pet_id` / necklace 上游原始 JSON / `[宠物硬件实时状态]`，属于 Pawkeyland 专属，Ink & Memory 中不适用)_

## 5. 实时外部信息

当前实现不在每轮请求前预取外部状态，也不把 `live_context` 直接拼入 prompt。

实时事实只通过 MCP 工具按需进入模型上下文。工具返回时，只有实际出现的字段能作为事实来源；`ok=false`、`error=no_data` 时，不存在可引用事实，模型只能用不确定表达。

> _(Pawkeyland 原文中实时硬件事实通过 necklace MCP 读取 `PAWKEYLAND_AGENT_PET_ID` / `PAWKEYLAND_AGENT_PET_SPECIES` / `PAWKEYLAND_AGENT_PET_TYPE`，属于 Pawkeyland 专属，Ink & Memory 中不适用)_

## 6. 会话与 workspace

服务层以业务 `user_id` 作为稳定会话键：

```text
workspace_key = session_id = "{user_id}"
```

`session_id` 同时用作 **进程内 Thread Session 享元键**（`AgentRunStatePool` 的 key）与 **workspace 目录键**（`get_or_create_workspace(session_id)`）。

> _(Pawkeyland 原文中为 `session_id = "{user_id}__{persona_id}"`，Ink & Memory 简化为单 user_id)_

默认工作目录：

```text
get_or_create_workspace(workspace_key)
```

如果请求显式传 `cwd`，仅调试/内部用途会覆盖默认 workspace。

`chat_session.claude_session_id` 是 Claude SDK 续接 ID。首轮不传 `thread_id`，由 Runner 创建；可续接时下一轮传入 `claude_session_id`。

服务端会拒绝复用这些历史 session：

- 最新 assistant 消息为空；
- 历史消息包含已移除工具名；
- `agent_contract_version` 与当前版本不一致；
- 开启日切分且最新 session 已跨本地自然日。

### 6.1 三种 sessionId 的语义对比

| 名称 | 取值 | 生命周期 | 作用 |
|---|---|---|---|
| `session_id`（Thread Session 享元键 = workspace_key） | `f"{user_id}"` | TTL（默认 600 s）keepalive；`close_thread` / TTL Sweeper / `aclose` 三条路径销毁 | `AgentRunStatePool` 的 key；`asyncio.Lock` 的 key；`get_or_create_workspace` 的输入 |
| `claude_session_id`（DB 字段，SDK 续接 ID） | Claude SDK `AgentRunResult.session_id`（首轮 SDK 自动分配，由 `_persist_conversation` 写入 `chat_session.claude_session_id`） | 与 `chat_session(user_id)` 行同生命周期；跨进程 / 跨重启稳定 | Phase 1 决策 `should_resume` / `thread_id_for_agent` 的真源；`AgentRunOptions.thread_id` 续轮的实际取值 |
| `workspace_key`（同 `session_id`） | 同上 | 与 `session_id` 同寿 | `backend/claude_agent/workspace.py::init_workspace` 的输入；`{AGENT_CWD}/{workspace_key}/` 物理目录 |

> 享元 `state.runner` / `state.system_prompt` / `state.cwd` 与 `claude_session_id` 互为正交：享元销毁 ≠ DB 续接失效；DB rollover ≠ 享元失效。详见 [claude-agent-session-persistence.md §10.6](./claude-agent-session-persistence.md#106-失效与重建场景)。

## 7. AgentRunOptions 当前入参

`ClaudeAgentService` 最终传给 Runner 的关键字段：

| 字段 | 来源 |
|---|---|
| `thread_id` | 可续接时为 `chat_session.claude_session_id`，首轮为 `None` |
| `user_message` | `ClaudeAgentContextBuilder.user_message()` |
| `system_prompt` | `ClaudeAgentContextBuilder.system_prompt()` |
| `resume` | 是否存在可用 `thread_id` |
| `model` | 请求模型字段，仅在服务端配置允许时有效 |
| `cwd` | 请求 `cwd` 或 `get_or_create_workspace(workspace_key)` |
| `max_turns` | 请求字段，默认 10 |
| `tool_choice` | 请求字段 `tool_choice`，仅接受 `auto`（默认）或 `none` |

> _(Pawkeyland 原文中还包含 `mcp_env`（宠物 ID、物种、petType），属于 Pawkeyland 专属，Ink & Memory 中不适用)_

## 8. 输出归一化

Agent 原始流经 `ClaudeAgentService` 转成 SSE 事件。最终 `message-final.normalizedPayload` 包含：

| 字段 | 说明 |
|---|---|
| `text` | 完整 assistant 文本 |
| `tool_call_count` | 本轮工具调用数量 |
| `claude_session_id` | 本轮 SDK session |
| `agent_contract_version` | 当前 Agent runtime/tool contract 版本 |
| `parts` | 持久化用的流式事件副本，不含 `finish` / `error` / `message-metadata` / `message-final` |

> _(Pawkeyland 原文中还包含 `sticker_tokens` / `segments` / `animation_events` 字段，属于 Pawkeyland 专属，Ink & Memory 中不适用)_

## 9. 与历史设计的差异

这些旧设计已经不代表当前实现：

| 旧说法 | 当前实现 |
|---|---|
| `conversation_id` 由调用方传入 | 已移除；以 `user_id` 查 session |
| 客户端可传 `system_prompt` | HTTP 合同不暴露；extra 字段被忽略 |
| 每轮预取硬件状态并拼入提示词 | 已移除；实时事实由零参数 MCP 工具按需读取 |
| `get_pet_status` / `get_long_term_memory` / `update_long_term_memory` Agent 工具 | 未实现为聊天工具；长期画像由服务端读取后放入 system prompt |
