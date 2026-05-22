> **迁移来源**: Pawkeyland docs/app/design/Claude Code Runtime 服务入参与SSE响应报文整理.md
> **Ink & Memory 适配**: API 端点路径一致（`POST /api/claude-agent`）；necklace/pet 相关字段已在 Ink & Memory 版本中移除。

# pet-agent 服务入参与SSE响应报文整理

> 目标服务：`POST /api/claude-agent`
> 配套接口：`POST /api/claude-agent/tool-confirm`
> 代码依据：`server.py`、`server.py（路由定义内）`、`backend/claude_agent/service.py`、`backend/claude_agent/thread_factory.py`、`backend/claude_agent/context_builder.py`、`（Ink infrastructure/necklace_gateway.py Memory 中不适用）`
> 关联设计稿：
> - `docs/app/design/claude-agent上下文拼接设计.md`
> - `docs/app/design/ClaudeAgentService 模块设计.md`
> - `docs/app/design/Claude Agent SDK 交互式工具时序图.md`
> - `docs/app/design/LLM驱动动画事件图设计方案.md`

## 1. 背景与目标

Pawkeyland 已将 Claude Agent 业务迁移到 pet-agent 链路，当前主入口为 `POST /api/claude-agent`。现有信息分散在模块设计、上下文拼接、动画事件图和代码实现中，下游很难一次性拿到稳定的请求协议与 SSE 报文口径。

本文目标是把 pet-agent 业务服务的两类协议整理为一份可直接消费的设计真相源：

1. HTTP 入参协议：调用方可以传什么，哪些字段会被服务层归一或覆盖。
2. SSE 响应协议：服务会按什么顺序推送什么事件，每个事件包含哪些字段。

## 2. 范围界定

### 2.1 本文覆盖

- `POST /api/claude-agent` 的请求体契约、默认值、校验与服务层归一规则。
- `POST /api/claude-agent/tool-confirm` 的请求/响应契约。
- Claude Agent SSE 通道的传输约定、事件全集、事件顺序和字段语义。
- `pet_info`、`runtime`、硬件状态、`long_term_profile` 在服务层中的实际消费方式。

### 2.2 本文不覆盖

- 已下线旧聊天入口的协议细节。
- 前端如何渲染各类 SSE 事件。
- Claude SDK 内部消息原文格式。
- `onFinish` 后续 DB 落库扩展；当前服务尚未实现该部分。

## 3. 方案摘要

- pet-agent 业务主入口定义为 `POST /api/claude-agent`，输出 `text/event-stream`，每个 SSE frame 只写 `data: {json}\n\n`，事件类型由 JSON 内的 `type` 字段标识，不额外写 `event:` 行。
- 请求模型是“强约束外层字段 + 弱约束上下文字典”的混合模式：外层字段由 `ClaudeAgentRequest` 明确约束，`pet_info` 与 `runtime` 保持开放字典，但服务层只消费其中少数字段。
- 请求中不再传入 `conversation_id`；服务层以 `(user_id, persona_id)` 为键查询 DB 展开会话续接。首轮 情况 Runner 自动生成新 `session_id`，`onFinish` 后绑定到 `chat_session`。
- SSE 事件分为 4 类：元数据类（`message-metadata`）、文本/思考类（`text-*` / `reasoning-*`）、工具类（`tool-*`）、结束/错误类（`finish` / `error`）。
- Runner 注册 `PreToolUse` hook。`tool_choice=auto` 时 hook 只记录工具输入并立即放行，保证动画和 necklace 工具由 Agent 自主调用；`tool_choice=manual` 时才进入 `on_tool_confirmation_request` 侧路等待前端确认。

## 4. 详细设计

### 4.1 服务边界与入口

pet-agent 业务服务在当前仓库中由以下两个 HTTP 入口组成：

| 接口 | 作用 | 响应类型 |
|---|---|---|
| `POST /api/claude-agent` | 启动 Claude Agent 一轮会话，并持续输出 SSE 事件 | `text/event-stream` |
| `POST /api/claude-agent/tool-confirm` | 对交互工具（动画事件、问答等）的待确认调用做批准/拒绝 | `application/json` |

其中：

- `server.py` 负责把 HTTP 请求映射为 `ClaudeAgentRunRequest`，并把 SSE 出流委托给 `ClaudeAgentThreadFactory.run_streaming`。
- `backend/claude_agent/thread_factory.py` 是 SSE 入口（Factory 模式），驱动 Phase 1（`service.assemble_context`）+ Phase 2（`create_agent_runner`）+ Phase 3（`service.execute_session`）+ Phase 4（`_fire_session_ended`），并维护每会话 `asyncio.Lock`、`AgentRunStatePool` 享元、10 分钟 TTL 清扫器。
- `backend/claude_agent/service.py` 在 Phase 1 / Phase 3 内完成上下文构建、pet-agent 调用和 SSE 事件出流；`run_streaming` 入口已删，对外只暴露 `assemble_context` + `execute_session` + `confirm_tool`。
- `backend/claude_agent/context_builder.py` 负责把宠物信息、运行时和显式诊断 `long_term_profile` 覆盖拼进 prompt；正式长期记忆由 Mem0 memory MCP 按需召回。

### 4.2 `POST /api/claude-agent` 入参契约

#### 4.2.1 顶层字段

| 字段 | 类型 | 默认值 | 必填 | 说明 |
|---|---|---:|---|---|
| `message` | string | `""` | 否 | 用户本轮输入文本；允许为空，但不建议业务侧省略。 |
| `resume` | bool | `true` | 否 | 是否复用此子物的已有 Claude session / workspace。 |
| `tool_choice` | string | `"auto"` | 否 | 工具模式；当前设计口径为 `auto` / `none`。 |
| `user_id` | string | `""` | 否 | 用户标识；与 `pet_id` 共同为会话查询键。 |
| `pet_id` | string | `""` | 否 | 孠物标识；与 `user_id` 共同为会话查询键，也用于角色记录加载和硬件状态查询。 |
| `pet_info` | object | `{}` | 否 | 孠物资料扩展字典。 |
| `runtime` | object | `{}` | 否 | 运行时扩展字典。 |
| `long_term_profile` | string/null | `null` | 否 | 用户长期画像文本；不传则不注入 `[long_term_profile]` 块。 |
| `cwd` | string/null | `null` | 否 | agent 子进程工作目录；不传时回退到按 `"{user_id}__{persona_id}"` 派生的 workspace 目录。 |
| `model` | string/null | `null` | 否 | 模型覆盖。 |
| `max_turns` | integer | `10` | 否 | 本轮 agent 最大 turn 数。 |

> 当前正式 HTTP 合同不暴露客户端 `system_prompt` 字段；Claude Agent system prompt 由服务端 `pet_persona` 和 `prompts/agent/*` 组装。若旧调用多传该 extra 字段，Python 请求模型会忽略，路由不会转发给 Agent。

#### 4.2.2 顶层校验与派生规则

- `user_id`、`pet_id` 不能包含 `/`、`\`、`..`，避免 workspace 路径逃逸。
- `user_id` 和 `pet_id` 都为空时，不应作为正式业务调用。
- 当前实现不会强制校验 `message` 非空，因此调用方需要自行保证业务输入完整。

#### 4.2.3 `pet_info` 的实际消费字段

`pet_info` 是开放字典，但当前服务主要消费以下字段：

| 字段 | 用途 |
|---|---|
| `pet_id`, `persona_id`, `pet_name`, `pet_gender`, `pet_age`, `pet_species`, `pet_breed`, `profile`, `mbti` | 服务端已持久化 persona / pet 快照；`profile`、`mbti`、名称、物种和品种进入 voice-only `character_card`。兼容保存的示例字段不进入 `pet_info` 或 prompt；独立 per-persona prompt 字段已退休 |
| `pet_id`, `pet_species` / `species` / `pet_type` | 仅用于生成 necklace MCP 子进程 env，不进入 system/user prompt |

#### 4.2.4 `runtime` 的实际消费字段

`runtime` 同样是开放字典；`curr_time` 不再进入 app user prompt，而是被服务端合并进 SDK `<runtime_context>` content block。未传 `curr_time` 时，服务端按 `PAWKEYLAND_CHAT_SESSION_TIMEZONE` 生成本地时间。其它运行态键不进入当前链路。

| 字段 | 用途 |
|---|---|
| `curr_time` | 注入 SDK `<runtime_context>` 的 `Local time` |
| 其它键 | 当前正式 Agent prompt 不消费；实时硬件事实由 necklace MCP 工具按需读取 |

### 4.3 服务层归一规则

`POST /api/claude-agent` 在进入 Claude runtime 之前，会依次经过以下归一流程：

1. 真实宠物聊天先用业务 `pet_id` 查询已有 `pet_persona`；不存在则返回 `404`，要求先走 `/api/character/create`。
2. 若查询成功，服务端从 `pet_persona` hydrate `persisted_pet_info`，并整体替代请求体 `pet_info`；正式调用不依赖客户端传入的人设字段。
3. 路由只接收显式 `long_term_profile` 诊断覆盖，并构建 `ClaudeAgentRunRequest`。
4. `ClaudeAgentService.assemble_context`（由 `ClaudeAgentThreadFactory._run_lifecycle` 在 Phase 1 调用）以 `(user_id, persona_id)` 为键执行 `load_conversation_by_persona(user_id, persona_id)`，获取 `claude_session_id`；首轮 `thread_id=None`，Runner 自动生成。后续轮直接命中 `AgentRunState` 享元缓存的 `system_prompt` / `cwd` / `persisted_pet_info` / `mem0_user_id` / `resolved_identity`，不再重新构建。
5. `ClaudeAgentContextBuilder.system_prompt()` 生成最终 `system_prompt`：
   - 拼接 `prompts/agent/system_base.txt`、`system_tools.txt`、`system_policies.txt`、`pet_persona` voice-only character/style blocks、虚拟角色策略和 `long_term_profile`。
6. `ClaudeAgentContextBuilder.user_message()` 生成最终 `user_message`：
   - `[user_message]`
7. Runner 追加 SDK `<runtime_context>` content block，承载 UTC Date、本地时间、时区、模型、最大 turn、session id 和 resume 状态。
8. `_mcp_env_for_request()` 把当前业务 `pet_id`、物种和 petType 写入 necklace MCP env；这些值不拼进 prompt。
9. 若 `cwd` 为空，则回退到 `get_or_create_workspace("{user_id}__{persona_id}")` 返回的隔离工作目录。
10. `onFinish` 后，将 Runner 返回的 `session_id` 通过 `upsert_conversation_by_persona(user_id, persona_id, ...)` 写入 `chat_session` 表。

### 4.4 请求报文示例

```json
{
  "message": "你现在在干嘛？",
  "resume": true,
  "tool_choice": "auto",
  "user_id": "17",
  "pet_id": "4706",
  "runtime": {
    "curr_time": "2026-05-06 20:00:00"
  },
  "long_term_profile": "用户下班后通常会来和我聊天。",
  "max_turns": 10
}
```

### 4.5 SSE 传输协议

#### 4.5.1 传输层约定

- HTTP 响应头：
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `X-Accel-Buffering: no`
- 每个事件都序列化为一行 `data: {json}\n\n`。
- 当前实现不写 `event:` 字段，因此客户端必须读取 `data` 内 JSON 的 `type` 字段来分发事件。
- 流开始时一定先发一条 `message-metadata`。
- 流正常结束时一定发 `finish`；异常结束时发 `error` 后关闭流，通常不会再补 `finish`。

#### 4.5.2 事件全集

| `type` | 触发时机 | 关键字段 | 备注 |
|---|---|---|---|
| `message-metadata` | 流开始 | `toolChoice`, `sessionId` | 第一条事件。 |
| `message-metadata` | 工具进度 / 结果补充 | `unstableData` | 作为复用事件承载 `tool_progress` 与 `session_result`。 |
| `message-metadata` | 流结束前 | `toolChoice`, `toolCount`, `sessionId` | 最终元数据。 |
| `text-start` | 文本块开始 | `id` | `id` 为服务端生成的块 ID。 |
| `text-delta` | 文本增量 | `id`, `delta` | 与最近一次 `text-start` 对应。 |
| `text-end` | 文本块结束 | `id` | 与最近一次 `text-start` 对应。 |
| `reasoning-start` | 思考块开始 | `id` | 来源于 `thinking_delta` / `thinking`。 |
| `reasoning-delta` | 思考增量 | `id`, `delta` | 仅在服务开启 thinking 输出时出现。 |
| `reasoning-end` | 思考块结束 | `id` | 与最近一次 `reasoning-start` 对应。 |
| `tool-input-start` | 工具调用开始 | `toolCallId`, `toolName` | auto/manual 都会出现。 |
| `tool-input-available` | 工具输入完整 | `toolCallId`, `toolName`, `input` | 动画事件时 `input` 通常含 `act/duration/interaction`。 |
| `tool-approval-request` | 交互工具等待确认 | `approvalId`, `toolCallId` | 上层配置了 `on_tool_confirmation_request` 时出现。 |
| `tool-output-available` | 工具结果返回 | `toolCallId`, `output` | 当前未附 `toolName`。 |
| `finish` | 正常完成 | `finishReason` | 当前实现固定为 `"stop"`。 |
| `error` | 任意异常 | `errorText` | 可能来自 service 内部，也可能由路由层兜底。 |

#### 4.5.3 条件字段

部分工具事件在 auto 模式下还可能附带以下可选字段：

| 字段 | 所在事件 | 说明 |
|---|---|---|
| `title` | `tool-input-start`, `tool-input-available` | 来自 `ToolEventPayload.title` |
| `providerExecuted` | `tool-input-start`, `tool-input-available`, `tool-output-available` | 标记工具是否由 provider 直接执行 |

注意：

- `tool-input-start` / `tool-input-available` 由 `on_tool_confirmation_request()` 直接生成，当前不会补 `title` 与 `providerExecuted`。
- 若运行时收到 `tool_result` 却没收到对应 `tool-input-start`，服务会自动补一组空 `input` 的起始事件，保证前端事件顺序稳定。

### 4.6 SSE 顺序规则

#### 4.6.1 普通文本流

```text
message-metadata(initial)
text-start
text-delta*
text-end
message-metadata(final)
finish
```

#### 4.6.2 带工具调用的 auto 模式

```text
message-metadata(initial)
text-*
tool-input-start
tool-input-available
tool-output-available
text-*
message-metadata(final)
finish
```

#### 4.6.3 带工具确认的交互模式

```text
message-metadata(initial)
tool-input-start
tool-input-available
tool-approval-request
POST /api/claude-agent/tool-confirm
tool-output-available        # 仅批准后才会出现
message-metadata(final)
finish
```

### 4.7 典型 SSE 报文示例

#### 4.7.1 流开始

```text
data: {"type":"message-metadata","toolChoice":"auto","sessionId":"u_001__pet_001"}

```

#### 4.7.2 交互工具确认三连

```text
data: {"type":"tool-input-start","toolCallId":"toolu_01","toolName":"AskUserQuestion"}

data: {"type":"tool-input-available","toolCallId":"toolu_01","toolName":"mcp__user__touch_animation","input":{"act":"playing","duration":6300,"interaction":{"type":"choice","choices":[{"id":"pat_head","label":"摸摸头"},{"id":"handshake","label":"握手"},{"id":"hug","label":"抱一抱"}]}}}

data: {"type":"tool-approval-request","approvalId":"2bde...","toolCallId":"toolu_01"}

```

#### 4.7.3 工具进度复用 `message-metadata`

```text
data: {"type":"message-metadata","unstableData":{"type":"tool_progress","toolCallId":"toolu_01","toolName":"Bash","elapsedTimeSeconds":12}}

```

#### 4.7.4 正常结束

```text
data: {"type":"message-metadata","toolChoice":"auto","toolCount":1,"sessionId":"u_001__pet_001"}

data: {"type":"finish","finishReason":"stop"}

```

### 4.8 `POST /api/claude-agent/tool-confirm` 契约

#### 4.8.1 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `tool_call_id` | string | 是 | 待确认工具调用 ID，对应 SSE 中的 `toolCallId`。 |
| `approved` | bool | 是 | 是否批准执行。 |
| `reason` | string/null | 否 | 拒绝或补充说明。 |
| `answers` | object/null | 否 | 动画事件或问答工具的结果回传。 |

`answers` 当前常见承载：

- `trigger`: `auto` / `tap` / `choice`
- `choiceId`: 仅 `trigger="choice"` 时出现
- `elapsedMs`: 动画已播放时长

#### 4.8.2 成功响应

```json
{
  "success": true,
  "tool_call_id": "toolu_01",
  "approved": true
}
```

#### 4.8.3 错误语义

- 若 `tool_call_id` 不存在或已超时，返回 `404`，错误信息为 `No pending tool confirmation found`。
- `approved=false` 时，SSE 主流不会立刻报 HTTP 错；是否继续输出后续文本由 Claude runtime 基于 deny 结果决定。

### 4.9 当前实现中的兼容性与边界

- `pet_info` 与 `runtime` 都是开放对象，便于前端增量扩展；但真正稳定可依赖的只有本文列出的已消费字段。
- `long_term_profile` 可由调用方显式覆盖；未传时不注入本地长期画像，正式长期记忆由 Mem0 memory MCP 按需召回。
- `tool-output-available` 事件当前没有 `toolName` 字段；客户端若需要展示工具名，应缓存前序 `tool-input-start`。
- `finishReason` 当前硬编码为 `"stop"`，暂未区分 `max_turns`、用户取消、工具拒绝等细粒度完成原因。

## 5. 验收标准

- `docs/app/design/` 中存在单一设计稿，完整描述 pet-agent 服务的请求契约、归一规则和 SSE 报文。
- 文档明确区分“调用方可传字段”和“服务层实际消费字段”。
- 文档明确给出 `on_tool_confirmation_request` 交互工具确认徧路协议，而不是只描述主 SSE 流。
- 下游读取本文后，无需反查源码即可实现：
  - `POST /api/claude-agent` 请求组装
  - SSE 事件分发
  - `POST /api/claude-agent/tool-confirm` 回调提交

## 6. 风险与依赖

- 依赖 `server.py（路由定义内）`、`server.py`、`backend/claude_agent/service.py`、`backend/claude_agent/thread_factory.py` 的当前实现；若这些文件后续改动，本文必须同步更新。
- `conversation_id` 已从请求入参中删除。会话续接通过 `(user_id, persona_id)` 查 DB 获取 `claude_session_id` 实现，不再依赖调用方传入的外部会话标识。
- `pet_id` 命中数据库记录时会覆盖请求体 `pet_info`，如果调用方误以为请求体优先，容易在联调时产生“字段传了但没生效”的错觉。
- `runtime` 是开放字典，下游若依赖未列出的隐式键，会造成文档与实现再次漂移。
- 硬件状态查询有超时和 fallback 行为，因此同一请求在不同环境下可能注入不同丰富度的上下文，但不影响 SSE 协议本身。

## 7. 关键决策记录

| 日期 | 决策 | 原因 | 影响 |
|---|---|---|---|
| 2026-05-06 | 将 pet-agent 业务服务口径统一收敛到 `POST /api/claude-agent` + `POST /api/claude-agent/tool-confirm` | 这两条接口共同构成可执行的 Claude Agent 业务协议 | 下游不再需要同时查找模块设计稿与任务文档 |
| 2026-05-06 | 以“代码当前行为”而非旧设计草案作为本文最终口径 | 相关设计稿存在演进，只有代码能代表真实协议 | 文档中显式写入 `pet_info` 覆盖、tool 事件条件字段等实现细节 |
| 2026-05-06 | 将 `pet_info` / `runtime` 定义为“开放字典 + 已消费字段清单” | 顶层模型未对其做强 schema 限制 | 保留扩展性，同时给下游稳定依赖面 |
