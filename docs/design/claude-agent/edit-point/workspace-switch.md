# 工作空间上下文切换设计方案

Status: Implemented  
Updated: 2026-06-01  
Scope: 智能体在单次对话中切换 `.editor` 工作空间上下文的完整设计与实现

---

## 目录

1. [背景与问题](#1-背景与问题)
2. [设计方案概述](#2-设计方案概述)
3. [工具定义：switch_editor](#3-工具定义switch_editor)
4. [数据流：PostToolUse 钩子切换机制](#4-数据流posttooluse-钩子切换机制)
5. [与现有 write 工具的对比](#5-与现有-write-工具的对比)
6. [时序图](#6-时序图)
7. [实现文件索引](#7-实现文件索引)

---

## 1. 背景与问题

### 1.1 场景

用户在一次对话中希望让智能体跨越多个文档编辑会话（`user_sessions`）工作：

- 先处理会话 A 的文档，再切换到会话 B 继续处理
- 无需中断当前对话线程，直接发送"切换到另一篇文章"的指令

### 1.2 现有架构的局限

当前 `.editor/` 虚拟索引机制（见 [workspace-adapter.md](./workspace-adapter.md)）在对话开始时由
`AgentRunOptions.editor_state` 确定文档上下文，整个对话轮次内固定不变：

```
AgentRunOptions.editor_state（对话开始时快照）
    ↓
PreToolUse 钩子（agent_runner.py）
    ↓
.editor/cells.json  →  临时文件（editor_state 的切片）
```

若要在单次对话中切换到另一个会话的文档，需要一种机制动态更新 `AgentRunState.editor_state`
飞享元缓存，让后续的 `.editor/` 读取自动看到新内容。

---

## 2. 设计方案概述

### 2.1 核心思路

引入 **`switch_editor` MCP 工具**：

| 组件 | 职责 |
|------|------|
| `editor_tool.py` 中的 MCP 处理器 | **空操作（no-op）**：仅返回 `{"ok": true}` |
| `agent_runner.py` 中的 `PostToolUse` 钩子 | **实际切换逻辑**：读取工具参数 → 从数据库加载新 `editor_state` → 通过 `opts.editor_state_setter` 更新飞享元 |
| `AgentRunOptions.editor_state_setter` | **写入通道**：由 `service.py` 注入，绑定到 `AgentRunState.with_editor_state()` |

### 2.2 为何选用 PostToolUse 而非 PreToolUse

- `PreToolUse` 在工具执行前触发，可以修改输入或拒绝执行。但切换上下文是一个"确认已完成"的动作，
  语义上应在工具返回成功后再更新状态。
- `PostToolUse` 在工具执行并返回结果后触发，是执行副作用（如状态更新）的标准位置。
- 与现有写工具的 `tool_result` 回调中的 `editor_state` DB-reload 逻辑模式一致
  （见 `service.py::_make_tool_event_cb`）。

### 2.3 为何 MCP 处理器是空操作

- 真正的切换逻辑（数据库查询 + 飞享元写入）发生在 `agent_runner.py`（主进程），
  而不是 MCP 子进程。
- MCP 子进程中没有对 `AgentRunState` 飞享元的引用，无法直接修改它。
- 空操作处理器的存在只是为了满足 MCP 工具协议：Claude 需要看到一个合法的工具调用结果，
  才能确认切换已生效。

---

## 3. 工具定义：switch_editor

### 3.1 工具名称

```
mcp__editor__switch_editor
```

### 3.2 Schema

```json
{
  "name": "switch_editor",
  "description": "切换当前对话的工作空间上下文至指定会话。调用成功后，智能体通过 .editor/ 路径读取的内容将来自新的目标会话文档。此操作不修改任何文档内容；状态切换在服务端由 PostToolUse 钩子异步完成，无需用户确认。",
  "input_schema": {
    "type": "object",
    "properties": {
      "editor_session_id": {
        "type": "string",
        "description": "要切换到的目标会话 ID（user_sessions.id from /api/sessions）。切换后智能体将在该会话的文档上下文中继续工作。"
      }
    },
    "required": ["editor_session_id"]
  }
}
```

### 3.3 MCP 处理器返回值

MCP 子进程的 `_switch_editor()` 处理器始终返回：

```json
{"ok": true, "switched": true, "editor_session_id": "<target_session_id>"}
```

实际状态切换由主进程 `PostToolUse` 钩子完成。

### 3.4 权限矩阵

| 模式 | 行为 |
|------|------|
| auto | 自动执行，无需用户确认 |
| manual | 自动执行，无需用户确认 |

> `switch_editor` **不在** `_ALWAYS_CONFIRM_TOOL_NAMES` 中，因为上下文切换不修改文档内容，
> 无需人类审批。

---

## 4. 数据流：PostToolUse 钩子切换机制

```
智能体调用：mcp__editor__switch_editor(editor_session_id="sess-new")
    │
    ├─ PreToolUse hook：不做特殊处理，允许工具执行
    │
    ├─ MCP 子进程（editor_tool.py）
    │      _switch_editor("sess-new")
    │      → 返回 {"ok": true, "switched": true, "editor_session_id": "sess-new"}
    │
    └─ PostToolUse hook（agent_runner.py::_post_tool_use_hook）
           ├─ 检测到 tool_name == "mcp__editor__switch_editor"
           ├─ 从 tool_input 提取 editor_session_id = "sess-new"
           ├─ asyncio.to_thread(load_editor_state_from_db, "sess-new")
           │      → database.get_db().execute("SELECT editor_state_json ... WHERE id = ?")
           │      → 返回新 editor_state dict
           └─ opts.editor_state_setter(new_state)
                  → state.with_editor_state(new_state, state.editor_user_id)
                  → AgentRunState.editor_state = new_state（飞享元已更新）

下次 .editor/ 读取时：
    PreToolUse hook
        live_editor_state = opts.editor_state_getter()   ← lambda: state.editor_state
                          = new_state                     ← 已切换的新上下文
        → 临时文件填充新会话的内容
        → 智能体读到新文档
```

### 4.1 飞享元更新链

```
opts.editor_state_setter(v)          # service.py 注入的 lambda
  → state.with_editor_state(v, uid)  # AgentRunState 飞享元写入
    → state.editor_state = v

opts.editor_state_getter()           # agent_runner.py PreToolUse 读取
  → state.editor_state               # 已是新值
```

---

## 5. 与现有 write 工具的对比

| 特性 | write_segment / delete_segment 等 | switch_editor |
|------|----------------------------------|---------------|
| 是否修改文档内容 | ✅ 是 | ❌ 否 |
| 是否需要用户确认 | 🔐 必须确认 | ✅ 自动执行 |
| state 更新时机 | `tool_result` 回调（service.py） | `PostToolUse` 钩子（agent_runner.py） |
| state 更新方式 | `state.editor_state = fresh_state`（直接赋值） | `opts.editor_state_setter(new_state)`（通过注入的 setter） |
| MCP 处理器职责 | 实际修改数据库中的文档内容 | 空操作，仅返回 ok |
| 钩子类型 | PreToolUse（确认） + tool_result（DB 刷新） | PostToolUse（DB 加载 + 飞享元写入） |

---

## 6. 时序图

```mermaid
sequenceDiagram
    participant Agent as Claude Agent
    participant PreHook as PreToolUse Hook<br/>(agent_runner.py)
    participant MCP as Editor MCP 子进程<br/>(editor_tool.py)
    participant PostHook as PostToolUse Hook<br/>(agent_runner.py)
    participant DB as Database
    participant State as AgentRunState<br/>（飞享元缓存）

    Agent->>PreHook: switch_editor(editor_session_id="sess-new")
    Note over PreHook: 不在 _ALWAYS_CONFIRM_TOOL_NAMES 中<br/>直接允许（auto 模式）
    PreHook->>Agent: { permissionDecision: "allow" }

    Agent->>MCP: 执行 switch_editor("sess-new")
    MCP-->>Agent: {"ok": true, "switched": true, "editor_session_id": "sess-new"}

    Agent->>PostHook: tool_name="mcp__editor__switch_editor", tool_input={...}
    PostHook->>DB: asyncio.to_thread(load_editor_state_from_db, "sess-new")
    DB-->>PostHook: new_editor_state (来自 user_sessions WHERE id = "sess-new")
    PostHook->>State: opts.editor_state_setter(new_editor_state)
    Note over State: state.editor_state = new_editor_state<br/>飞享元已更新

    Agent->>PreHook: Read(.editor/cells.json)
    Note over PreHook: live_editor_state = opts.editor_state_getter()<br/>= state.editor_state = new_editor_state
    PreHook->>Agent: 临时文件（填充 new_editor_state 内容）
    Note over Agent: 现在看到的是 sess-new 的文档内容 ✓
```

---

## 7. 实现文件索引

| 文件 | 变更内容 |
|------|---------|
| `backend/libs/claude_agent_kit/server/editor_tool.py` | 新增 `SWITCH_EDITOR_TOOL_NAME` 常量、`switch_editor` 工具 spec、`load_editor_state_from_db` 公开函数、`_switch_editor()` 空操作处理器；`handle_editor_write_tool` 分派 |
| `backend/libs/claude_agent_kit/types.py` | `AgentRunOptions` 新增 `editor_state_setter` 字段 |
| `backend/libs/claude_agent_kit/server/agent_runner.py` | 新增 `_SWITCH_EDITOR_MCP_TOOL_NAME` 常量；在 `run_streaming` 闭包内定义 `_post_tool_use_hook`；在 `ClaudeCodeOptions.hooks` 中注册 `PostToolUse` |
| `backend/claude_agent/service.py` | `assemble_context` 向 `AgentRunOptions` 注入 `editor_state_setter` lambda |
| `docs/design/claude-agent/edit-point/workspace-switch.md` | 本设计文档 |

### 7.1 相关文档

- [workspace-adapter.md](./workspace-adapter.md) — `.editor/` 虚拟索引读取机制
- [mcp-tools.md](./mcp-tools.md) — 写工具目录与确认流程
- [editor-state-lifecycle.md](./editor-state-lifecycle.md) — `editor_state` 生命周期
