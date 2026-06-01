# 笔记标签（labels）与跨 Session 协作检索设计方案

Status: Implemented  
Updated: 2026-05-31  
Scope: `user_sessions.labels` 属性 + `mcp__user__get_sessions_range` MCP 工具，支持 Agent 跨日期检索历史笔记

---

## 目录

1. [背景与目标](#1-背景与目标)
2. [数据库变更](#2-数据库变更)
3. [API 变更：POST /api/sessions](#3-api-变更post-apisessions)
4. [近期 Session 上下文格式变更](#4-近期-session-上下文格式变更)
5. [`mcp__user__get_sessions_range` MCP 工具](#5-mcpuserget_sessions_range-mcp-工具)
6. [env var 注入路径](#6-env-var-注入路径)
7. [数据流：Agent 跨 Session 检索](#7-数据流agent-跨-session-检索)
8. [实现文件索引](#8-实现文件索引)

---

## 1. 背景与目标

### 1.1 场景

用户写日记时，会用主题标签（如 `["孤独", "成长"]`）标注每篇笔记。Agent 在与用户的对话中需要能够：

- 在**近期**对话上下文中感知用户写作主题的分布；
- 当用户提及某个可能记录在三天前的主题或事件时，能**按需检索**更早的历史 session；
- 根据检索结果中的 `labels` 和 `excerpt` 定位相关内容，并在回复中引用。

### 1.2 设计目标

| 目标 | 说明 |
|------|------|
| 标签持久化 | `user_sessions.labels` 存储 JSON 数组字符串，可为空 |
| 近期上下文可见性 | 系统提示的近期条目块携带 `sessionId` 和 `labels`，Agent 无需额外工具即可看到最近三天主题 |
| 历史按需检索 | `get_sessions_range` MCP 工具支持按日期范围检索超出三天窗口的 session |
| 最小开销 | 工具仅在用户明确涉及历史内容时调用，不影响每轮对话性能 |

---

## 2. 数据库变更

### 2.1 新增列

`user_sessions` 表新增 `labels` 列（TEXT，JSON 数组，可空）：

```sql
ALTER TABLE user_sessions ADD COLUMN labels TEXT;
```

列格式：`'["孤独","成长"]'`（`json.dumps(list, ensure_ascii=False)` 序列化）。

### 2.2 运行时迁移

`init_db()` 中在 `create_tables()` 之后立即执行迁移：

```python
# Migration: add labels column for Agent-note collaboration (2026-05-31).
try:
    db.execute("ALTER TABLE user_sessions ADD COLUMN labels TEXT")
except Exception:
    pass  # 列已存在时静默跳过
```

已存在的数据库在下次启动时自动完成迁移，无需手动操作。

### 2.3 `save_session` 变更

```python
def save_session(
    user_id: int,
    session_id: str,
    editor_state: dict,
    name: str = None,
    created_at: Optional[Union[str, datetime]] = None,
    labels: Optional[list] = None,   # ← 新增
):
```

`labels` 序列化为 JSON 字符串后写入数据库。`ON CONFLICT` 更新策略：
```sql
labels = COALESCE(excluded.labels, user_sessions.labels)
```
即：若调用方显式传入 `labels`，则更新；否则保留已有值。

### 2.4 `list_sessions_in_range` 新函数

```python
def list_sessions_in_range(
    user_id: int,
    start_date: str,   # YYYY-MM-DD，含
    end_date: str,     # YYYY-MM-DD，含
) -> list[dict]:
```

查询 `user_sessions WHERE user_id = ? AND DATE(updated_at) BETWEEN ? AND ?`，返回列表，每项含 `id`、`name`、`labels`（已解析为 list）、`date`、`excerpt`（`editor_state_json` 的首行文字）。

---

## 3. API 变更：POST /api/sessions

### 请求体

```json
{
  "session_id": "string",
  "name": "optional string",
  "editor_state": { ... },
  "labels": ["可选", "标签", "列表"]
}
```

`labels` 字段为可选列表；若未传入则数据库保留已有值。

### 响应

无变更，仍返回 `{"success": true}`。

---

## 4. 近期 Session 上下文格式变更

### 4.1 加载范围

`_load_recent_sessions_block` 改为仅加载**最近三天**（由常量 `_RECENT_SESSIONS_DAYS = 3` 控制）的 session，使用新函数 `_fetch_recent_sessions`，底层调用 `database.list_sessions_in_range`。

旧函数 `_fetch_sessions` 保留以兼容其他调用路径。

### 4.2 条目格式

旧格式：
```
### {date} — {title}
{excerpt}
```

新格式：
```
### {date} — sessionId:{session_id}, {labels}: {title}
{excerpt}
```

示例：
```
### 2026-05-30 — sessionId:abc123, 孤独,成长: 今天的感悟
今天的会面让我...
```

- `sessionId` 让 Agent 在调用 `get_sessions_range` 后能够对应到系统提示中已知的 session；
- `labels` 为逗号拼接字符串（空 labels 时为空字符串，格式变为 `, :`，仍合法）。

---

## 5. `mcp__user__get_sessions_range` MCP 工具

### 5.1 概述

用于检索**三天前**的历史 session，供 Agent 在用户提及某主题时按需拉取。工具运行在 `user` MCP stdio 子进程（与 `touch_animation` 同一进程）。

### 5.2 工具 Schema

```json
{
  "name": "get_sessions_range",
  "description": "按日期范围检索用户的历史日记 session，用于发现三天前的内容。返回匹配 session 的 id、title、labels 和 excerpt，供 Agent 根据主题定位相关笔记。仅在用户提到可能早于近期条目的主题或事件时调用此工具。",
  "input_schema": {
    "type": "object",
    "properties": {
      "start_date": {
        "type": "string",
        "description": "查询起始日期（含），格式 YYYY-MM-DD"
      },
      "end_date": {
        "type": "string",
        "description": "查询截止日期（含），格式 YYYY-MM-DD"
      }
    },
    "required": ["start_date", "end_date"]
  }
}
```

### 5.3 返回值

工具返回 JSON 字符串：

```json
{
  "sessions": [
    {
      "id": "sess-abc123",
      "name": "今天的感悟",
      "labels": ["孤独", "成长"],
      "date": "2026-05-20",
      "excerpt": "今天的会面让我..."
    }
  ]
}
```

出错时返回 `{"error": "<message>", "sessions": []}`。

### 5.4 `user_id` 读取方式

工具在 MCP stdio 子进程中运行，通过环境变量 `INK_AGENT_USER_ID` 获取当前用户 ID（trusted subprocess 上下文，无需认证）：

```python
user_id_str = os.getenv("INK_AGENT_USER_ID")
```

### 5.5 注册位置

工具在 `mcp_server.py::create_user_mcp_server()` 中注册（与 `touch_animation` 并列）：

```python
mcp_types.Tool(
    name=GET_SESSIONS_RANGE_TOOL_NAME,
    description=GET_SESSIONS_RANGE_TOOL_SPEC.description,
    inputSchema=GET_SESSIONS_RANGE_TOOL_SPEC.input_schema,
)
```

`DEFAULT_ALLOWED_TOOLS` 中同步添加 `mcp__user__get_sessions_range`。

### 5.6 系统提示中的 Workflow 说明

`_SYSTEM_PROMPT_TEMPLATE` 新增 `## Session Retrieval Workflow` 章节：

```
The recent entries block below only covers the last 3 days of journal sessions.
When the user mentions a topic, theme, or past memory that may be recorded in older entries,
use `mcp__user__get_sessions_range` to search further back:

1. Estimate the date window based on the user's context clues (e.g. "last month", "春节").
2. Call `get_sessions_range(start_date, end_date)` — dates in YYYY-MM-DD format.
3. Scan the returned `labels` and `excerpt` fields to identify sessions relevant to the topic.
4. Reference those sessions by their `sessionId` when replying to the user.

Only call this tool when the user's message suggests they are referring to events or themes
that predate the visible recent entries.  Do not call it on every turn.
```

---

## 6. env var 注入路径

`user_id` 通过以下路径注入 MCP 子进程：

```
ClaudeAgentService.assemble_context
  → run_options.mcp_env["INK_AGENT_USER_ID"] = str(request.user_id)

agent_runner.run_streaming(mcp_env=...)
  → mcp_servers["user"] = _user_mcp_stdio_config(extra_env=mcp_env)
      → McpStdioServerConfig.env = _stdio_env(extra_env=extra_env)
          → env["INK_AGENT_USER_ID"] = mcp_env["INK_AGENT_USER_ID"]

sessions_tool.handle_get_sessions_range()
  → os.getenv("INK_AGENT_USER_ID")
  → database.list_sessions_in_range(user_id, start_date, end_date)
```

---

## 7. 数据流：Agent 跨 Session 检索

```
用户发送："你还记得我去年写过关于孤独的那篇文章吗？"
     │
     ├─ 系统提示近期条目块（最近三天）
     │      → 无匹配条目（超出三天窗口）
     │
     └─ Agent 判断需要检索历史内容
            │
            ↓
     mcp__user__get_sessions_range(start_date="2025-01-01", end_date="2025-12-31")
            │
            ├─ MCP 子进程（user_mcp_stdio）
            │      handle_get_sessions_range(arguments)
            │        → os.getenv("INK_AGENT_USER_ID")
            │        → database.list_sessions_in_range(user_id, start, end)
            │        → 返回 JSON: {"sessions": [...]}
            │
            └─ Agent 扫描返回的 labels 和 excerpt
                   → 定位 sessionId:"sess-old", labels:["孤独","成长"]
                   → 在回复中引用该 session 内容
```

---

## 8. 实现文件索引

| 文件 | 变更内容 |
|------|---------|
| `backend/database.py` | `user_sessions` 新增 `labels` 列；运行时迁移；`save_session` 新增 `labels` 参数；新增 `list_sessions_in_range`、`_parse_labels` 函数 |
| `backend/routers/sessions.py` | `POST /api/sessions` 接受并转发 `labels` 字段 |
| `backend/claude_agent/context_builder.py` | `_SESSION_ENTRY_TEMPLATE` 加入 `sessionId` 和 `labels`；`_load_recent_sessions_block` 改用三天窗口；新增 `_fetch_recent_sessions`；系统提示新增 `## Session Retrieval Workflow` |
| `backend/libs/claude_agent_kit/server/sessions_tool.py` | **新增文件**：`GET_SESSIONS_RANGE_TOOL_SPEC`、`handle_get_sessions_range` |
| `backend/libs/claude_agent_kit/server/mcp_server.py` | `create_user_mcp_server` 注册 `get_sessions_range` 工具；`call_tool` 分派逻辑 |
| `backend/libs/claude_agent_kit/server/agent_runner.py` | `DEFAULT_ALLOWED_TOOLS` 新增 `mcp__user__get_sessions_range`；`_user_mcp_stdio_config` 支持 `extra_env` 透传；`run_streaming` 调用时传入 `mcp_env` |
| `docs/design/claude-agent.md` | §7 新增笔记标签与跨 Session 协作检索设计摘要 |
| `docs/design/claude-agent/claude-agent-context-assembly.md` | §3 更新近期 session 加载范围说明与新格式描述 |

### 8.1 相关文档

- [claude-agent-context-assembly.md](./claude-agent-context-assembly.md) — `assemble_context` 管道与系统提示生成
- [edit-point/workspace-switch.md](./edit-point/workspace-switch.md) — `switch_editor` 工具设计（与本功能协同：Agent 先检索 session，再切换上下文）
- [edit-point/mcp-tools.md](./edit-point/mcp-tools.md) — Editor MCP 工具目录（写工具）
