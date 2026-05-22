# Claude Agent 架构文档

**模块目标**：为 Ink & Memory 提供基于 Claude Code SDK 的流式 AI 写作助手后端能力，  
支持多轮对话、会话保活（Flyweight 会话池）、工具确认、SSE 流式输出，  
独立于现有 PolyCLI agent 模块，不与其产生交叉关联。

---

## 1. 目录结构

两层架构，与 Pawkeyland 源模块对应：

```
backend/
├── libs/
│   └── claude_agent_kit/               # Kit 层 ← 迁移自 Pawkeyland libs/claude_agent_kit/
│       ├── __init__.py                 # 公共导出（类型、Runner、Workspace）
│       ├── types.py                    # AgentRunOptions/Result/Callbacks/ToolEventPayload
│       ├── runner.py                   # ClaudeAgentRunner — SDK 封装（合并 agent_runner + sdk_env）
│       ├── workspace.py                # 会话工作区目录管理
│       └── .folder.md
│
└── claude_agent/                       # 应用层 ← 迁移自 Pawkeyland application/claude_agent/
    ├── __init__.py                     # 公共导出（应用层 + kit 层 re-export）供 server.py 使用
    ├── observer.py                     # SessionLifecycleObserver、SessionObserverRegistry
    ├── tool_confirmation_store.py      # ToolConfirmationStore — asyncio.Future 工具确认
    ├── thread_pool.py                  # AgentRunState、AgentRunStatePool、Sweeper — TTL 会话池
    ├── context_builder.py              # ClaudeAgentContextBuilder — 写作会话 system_prompt
    ├── service.py                      # ClaudeAgentService — Phase 1 & 3 业务逻辑
    ├── thread_factory.py               # ClaudeAgentThreadFactory — 四阶段编排入口
    └── .folder.md
```

**单向依赖**：`claude_agent/` → `libs/claude_agent_kit/`，kit 层不依赖应用层。  
**隔离说明**：`claude_agent` 模块与现有 PolyCLI `agent` 会话完全独立，不共享注册表、状态或导入。

---

## 2. API 发布点

所有端点前缀 `/api/claude-agent/*`，在 `server.py` 内直接注册（与现有路由同文件，无子路由模块）。

| Method   | Path                                | Handler                       | 认证 | 描述                             |
|----------|-------------------------------------|-------------------------------|------|----------------------------------|
| `POST`   | `/api/claude-agent`                 | `claude_agent_stream`         | JWT  | SSE 流式聊天，委托 ThreadFactory |
| `GET`    | `/api/claude-agent/chat-history`    | `claude_agent_chat_history`   | JWT  | 按 user_id 加载历史消息          |
| `POST`   | `/api/claude-agent/message-latency` | `claude_agent_message_latency`| JWT  | 上报浏览器延迟指标               |
| `GET`    | `/api/claude-agent/session`         | `claude_agent_session_status` | JWT  | 查询 Thread Session 保活快照     |
| `DELETE` | `/api/claude-agent/session`         | `claude_agent_session_close`  | JWT  | 主动销毁会话                     |
| `POST`   | `/api/claude-agent/tool-confirm`    | `claude_agent_tool_confirm`   | JWT  | 工具人工确认/拒绝                |

---

## 3. 后端分层设计

```
HTTP 层 (server.py)
    ↓  ClaudeAgentRequest / ToolConfirmRequest
ThreadFactory (thread_factory.py)
    ↓  每 session 一把 asyncio.Lock，串行化并发请求
    Phase 1  context_builder  → 组装 system_prompt + 写作上下文
    Phase 2  runner.py        → 创建 ClaudeAgentRunner（cached）
    Phase 3  service.py       → 执行流式对话，写 DB，发 SSE 事件
    Phase 4  (销毁时)          → 触发 SessionObserver
    ↓  AgentRunStatePool (thread_pool.py)
        AgentRunState (Flyweight)
        AgentRunStateSweeper (TTL 清理)
```

### 四阶段生命周期

| 阶段 | 职责 | 触发时机 |
|------|------|----------|
| Phase 1 | 组装 system_prompt、获取近期写作会话上下文 | 每轮请求（首轮完整构建，续轮复用缓存） |
| Phase 2 | 创建 ClaudeAgentRunner（Claude Code SDK 实例）| 首次 session 创建；TTL 过期后重建 |
| Phase 3 | 执行流式对话、持久化消息、发送 SSE 事件 | 每轮请求 |
| Phase 4 | 触发 SessionObserver.on_session_ended | 仅在销毁时（close_thread / TTL 驱逐 / aclose）|

---

## 4. 迁移映射表（Pawkeyland → Ink & Memory）

| Pawkeyland 源路径 | Ink & Memory 目标路径 | 迁移说明 |
|-------------------|-----------------------|----------|
| `application/claude_agent/observer.py` | `backend/claude_agent/observer.py` | 直接迁移，无变化 |
| `application/claude_agent/tool_confirmation_store.py` | `backend/claude_agent/tool_confirmation_store.py` | 直接迁移，无变化 |
| `application/claude_agent/thread_pool.py` | `backend/claude_agent/thread_pool.py` | 简化：移除 pet/persona/mem0/resolved_identity 字段 |
| `application/claude_agent/thread_factory.py` | `backend/claude_agent/thread_factory.py` | 适配：session_id = user_id，移除宠物相关逻辑 |
| `application/claude_agent/context_builder.py` | `backend/claude_agent/context_builder.py` | 重写：用写作会话上下文替换 pet/persona 上下文 |
| `application/claude_agent/service.py` | `backend/claude_agent/service.py` | 大幅简化：移除 pet/persona/mem0/sticker_filter |
| `libs/claude_agent_kit/types.py` | `backend/libs/claude_agent_kit/types.py` | 直接迁移，移除 Pawkeyland 特定注释 |
| `libs/claude_agent_kit/server/agent_runner.py` | `backend/libs/claude_agent_kit/runner.py` | 合并 agent_runner + sdk_env，移除 MCP 子进程（necklace/memory/touch_animation）|
| `libs/claude_agent_kit/server/workspace.py` | `backend/libs/claude_agent_kit/workspace.py` | 简化：移除 skills 符号链接同步，保留工作区骨架 |
| `libs/claude_agent_kit/server/sdk_env.py` | 合并入 `backend/libs/claude_agent_kit/runner.py` | 合并为单文件，直接使用 ANTHROPIC_* 变量 |
| `application/claude_agent/state_builder.py` | _(内联至 thread_pool.py)_ | 代码量极小（111行），直接内联 |

**未迁移内容**（见第 9 节）：

- `libs/claude_agent_kit/server/mcp_server.py` — Pawkeyland 宠物专属 MCP
- `libs/claude_agent_kit/server/necklace_*.py` — 项圈硬件 MCP
- `libs/claude_agent_kit/server/memory_*.py` — Mem0 记忆 MCP
- `libs/claude_agent_kit/server/touch_animation_tool.py` — 动画工具

---

## 5. 配置与环境变量

所有运行时配置通过环境变量解析，不硬编码业务值。  
Ink & Memory 使用 `INK_AGENT_*` 前缀（替换 Pawkeyland 的 `PAWKEYLAND_AGENT_*`）。

### 5.1 Agent SDK 配置

直接在项目根目录 `.env` 中配置 Claude Code SDK 所需的 `ANTHROPIC_*` 变量即可，  
运行时由 `runner._build_sdk_env()` 从 `.env` 加载后传给 SDK 子进程。

| 环境变量（`.env`）| 默认值 | 用途 |
|-------------------|--------|------|
| `ANTHROPIC_API_KEY` | 无 | Claude API Key |
| `ANTHROPIC_BASE_URL` | 无（官方端点）| API Base URL（代理场景使用）|
| `ANTHROPIC_MODEL` | 无（SDK 默认）| 模型名 |

### 5.2 会话保活配置

| 环境变量 | 默认值 | 用途 |
|----------|--------|------|
| `INK_AGENT_TTL_S` | `600` | Thread Session 保活 TTL（秒） |
| `INK_AGENT_SWEEP_INTERVAL_S` | `60` | 后台 Sweeper 清理周期（秒） |
| `INK_AGENT_SSE_KEEPALIVE_S` | `15` | SSE keepalive 注释帧间隔（秒） |

### 5.3 功能配置

| 环境变量 | 默认值 | 用途 |
|----------|--------|------|
| `INK_AGENT_MAX_TURNS` | `100` | 每轮对话最大 Agent turn 数 |
| `AGENT_CWD` | `{tmpdir}/claude-agent-workspaces` | 工作区根目录（绝对路径）|
| `INK_AGENT_CONTEXT_SESSIONS` | `5` | 注入写作上下文的最近会话数 |

---

## 6. 数据流

```
POST /api/claude-agent
    │
    ├─ get_current_user()  ← JWT 认证
    │
    ├─ ClaudeAgentRequest 解析
    │   └─ user_id, message, resume, max_turns, cwd, model
    │
    ├─ claude_agent_thread_factory.run_streaming(request)
    │   │
    │   ├─ Phase 1: context_builder
    │   │   ├─ 查询 database.list_sessions(user_id) → 近期写作会话
    │   │   └─ 拼装 system_prompt（Ink & Memory 写作助手角色）
    │   │
    │   ├─ Phase 2: runner.py
    │   │   └─ ClaudeAgentRunner(session_id, cwd)
    │   │       └─ env: INK_AGENT_API_KEY/BASE_URL/MODEL → ANTHROPIC_*
    │   │
    │   └─ Phase 3: service.py
    │       ├─ runner.run_streaming(opts, callbacks)
    │       │   └─ claude_code_sdk.query() → AsyncGenerator[SDKMessage]
    │       ├─ 写 SSE 事件流
    │       │   ├─ text-delta, text-done
    │       │   ├─ tool-event
    │       │   ├─ message-final
    │       │   └─ finish / error
    │       └─ （可扩展）持久化消息到 DB
    │
    └─ StreamingResponse (text/event-stream)
```

---

## 7. 错误处理

| 场景 | 处理方式 | SSE 事件 |
|------|----------|----------|
| JWT 认证失败 | FastAPI `HTTPException(401)` | — |
| session_id 非法字符 | `ValueError` → `HTTPException(400)` | — |
| SDK 执行错误 | 捕获异常，记录日志 | `error` 事件 |
| 工具确认超时 | `TimeoutError` → 默认拒绝 | `error` 事件 |
| SSE 客户端断连 | `GeneratorExit` → cancel_pending | — |
| TTL 过期 | Sweeper 驱逐，触发 Phase 4 Observer | — |

---

## 8. 测试与验证策略

与现有 `backend/tests/` 保持一致，使用自定义 Python 脚本（无 pytest）。

| 测试文件（建议路径） | 测试内容 |
|----------------------|----------|
| `backend/tests/test_claude_agent.py` | HTTP 端点集成测试（需要 server:8765 和有效 SDK 配置）|
| `backend/tests/ci-smoke.sh` 扩展 | 新增 claude-agent register → stream → close 冒烟 |

---

## 9. 未迁移内容

| 内容 | 不迁移原因 |
|------|-----------|
| Mem0 记忆服务 (`memory_*.py`) | Ink & Memory 无 Mem0 服务，通过 DB 写作会话替代 |
| 项圈 MCP (`necklace_*.py`) | IoT 硬件，Ink & Memory 无此设备 |
| 触摸动画工具 (`touch_animation_tool.py`) | Pawkeyland UI 专属，Ink & Memory 无动画层 |
| 宠物 MCP (`mcp_server.py`) | Pawkeyland 宠物领域专属，与 Ink & Memory 无关 |
| `state_builder.py` | 代码极少（111行），内联至 thread_pool.py |
| `session_files.py` | JSONL 会话文件解析，当前版本通过 DB 替代 |
| `workspace_file_sync.py` | skills 符号链接，当前不引入 skills 机制 |
| `libs/volcresource/cfg.py` | Pawkeyland 专属 volcengine 配置解析 |
| `api/contracts.py` | Pawkeyland 路由契约，Ink & Memory 直接用 Pydantic 在 server.py |

---

## 10. 与现有 agent 模块的隔离说明

| 维度 | PolyCLI agent（现有）| claude_agent（新增）|
|------|----------------------|---------------------|
| 注册方式 | `@session_def(...)` → `/polycli` 挂载 | `@app.post/get/delete(...)` → `/api/claude-agent/*` |
| SDK | PolyCLI / PolyAgent | claude_code_sdk |
| 会话管理 | PolyCLI session registry | AgentRunStatePool（Flyweight）|
| 鉴权 | `auth_callback=auth.verify_access_token` | `Depends(get_current_user)`（同现有 REST 路由）|
| 数据库 | `server.py` 内直接调用 database | `service.py` 内调用 database（只读写作会话）|
| 导入关系 | `claude_agent` **不导入** PolyCLI 任何模块 | PolyCLI 模块 **不导入** claude_agent |
