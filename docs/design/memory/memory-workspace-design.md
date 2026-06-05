> [Input] `backend/libs/claude_agent_kit/server/memory_workspace.py`, `backend/libs/claude_agent_kit/server/workspace.py`, `backend/claude_agent/service.py`
> [Output] Define Memory Workspace design: initialization flow, file structure, per-partition configuration, and agent analysis flow.
> [Pos] design-doc node in `docs/design/memory`
> [Sync] 2026-06-05: initial implementation

# Memory 工作空间设计文档

## 1. 概述

Memory 工作空间（Memory Workspace）是每个 Claude Agent 会话中负责**记忆管理**的专用目录。它通过三类记忆机制（短期、长期、程序性），使 AI 助手能够在跨会话中保持对用户的深度理解。

### 三类记忆

| 类型 | 含义 | 存储位置 | 更新时机 |
|------|------|----------|----------|
| **短期记忆** | 当前会话窗口内的上下文 | 对话上下文（内存） | 实时 |
| **长期记忆** | 超出短期窗口后的摘要信息 | `memory/long_term_memory.md` | 每轮对话后（可配置） |
| **程序性记忆** | 按业务规则写入的结构化记忆 | `memory/procedural/` 目录 | 业务规则触发时 |

---

## 2. 目录结构

```
{AGENT_CWD}/{thread_id}/
├── memory/                            ← Memory 工作空间根目录
│   ├── WORKFLOW.md                    ← 记忆工作流程决策树
│   ├── MEMORY_QUERY_PROMPT.md         ← 7 大类记忆检索提示词
│   ├── MEMORY_Distiller_PROMPT.md     ← 记忆蒸馏专业提示词
│   ├── MEMORY_ANSWER_PROMPT.md        ← 基于记忆的回答提示词
│   ├── DEFAULT_UPDATE_MEMORY_PROMPT.md ← 记忆更新规则（4 种操作）
│   ├── long_term_memory.md            ← 长期记忆存储（运行时生成）
│   └── procedural/                    ← 程序性记忆目录（运行时生成）
│       ├── user_preferences.json      ← 用户偏好
│       ├── important_events.json      ← 重要事件记录
│       └── timeline.json              ← 会话时间线
├── files/                             ← 用户文件区
├── logs/                              ← 执行日志区
├── skills/                            ← Skills 区
├── .claude/                           ← Claude 配置
├── .editor/                           ← EditorState 虚拟索引
└── .mcp.json                          ← MCP 配置
```

---

## 3. 智能体如何创建 Memory 工作空间资源文件

### 3.1 初始化流程

当分析会话通过 `thread_id` 启动时，系统自动执行以下步骤：

```
POST /api/claude-agent/threads
  → build_session_id(request)              # 使用 thread_id 作为 session_id
  → get_or_create_workspace(session_id)    # 创建/恢复工作空间
      → init_workspace(session_id)
          → 创建标准子目录 (files/, logs/, skills/)
          → 同步 .claude/ 模板
          → 初始化 .editor/ 虚拟索引
          → [NEW] init_memory_workspace()  # 初始化 Memory 工作空间
              → 创建 memory/ 目录
              → 从 .claude/memory/ 复制提示词模板文件
              → 上传已存储的程序性记忆文件（若存在）
```

### 3.2 提示词模板文件来源

模板文件从项目根目录 `.claude/memory/` 复制到工作空间：

```
项目根: .claude/memory/WORKFLOW.md
           ↓ 复制（每次 init 刷新）
工作空间: {session_id}/memory/WORKFLOW.md
```

与 `.claude/` 同步逻辑相同：每次 `init_workspace` 刷新模板内容，但**不覆盖**运行时生成的 `long_term_memory.md` 和 `procedural/` 文件。

### 3.3 程序性记忆上传

分析开始时，通过 `thread_id` 从持久化存储中加载已存储的程序性记忆：

```python
# memory_workspace.py — init_memory_workspace()
def init_memory_workspace(workspace: Path, thread_id: str, user_id: int) -> None:
    memory_dir = workspace / "memory"
    memory_dir.mkdir(exist_ok=True)

    # 1. 复制提示词模板（从 .claude/memory/）
    _sync_memory_templates(memory_dir)

    # 2. 上传已存储的程序性记忆（从 DB 或文件存储）
    _restore_procedural_memories(memory_dir, thread_id, user_id)
```

---

## 4. 每个分区的提示词配置 Memory 工作空间

### 4.1 设计原则

每个 **Voice（声音分区）** 可以通过 `memory_workspace_config` JSON 字段，自定义该分区的记忆工作空间行为：

- 覆盖默认的 `MEMORY_QUERY_PROMPT.md` 内容（针对特定业务场景的记忆检索规则）
- 覆盖默认的 `DEFAULT_UPDATE_MEMORY_PROMPT.md` 内容（定义哪些信息值得记录）
- 指定启用的记忆类型（短期/长期/程序性）
- 自定义程序性记忆 schema

### 4.2 Voice memory_workspace_config Schema

```json
{
  "enabled": true,
  "memory_types": ["short_term", "long_term", "procedural"],
  "query_prompt_override": null,
  "update_prompt_override": null,
  "distiller_prompt_override": null,
  "answer_prompt_override": null,
  "procedural_schema": {
    "user_preferences": true,
    "important_events": true,
    "timeline": true,
    "custom_fields": {}
  }
}
```

### 4.3 配置注入流程

```
Voice.memory_workspace_config
  ↓ (via ClaudeAgentRunRequest.memory_config)
  ↓
service.assemble_context()
  ↓
_init_memory_workspace_with_config()
  → 若 config.query_prompt_override 存在，写入 memory/MEMORY_QUERY_PROMPT.md
  → 若 config.update_prompt_override 存在，写入 memory/DEFAULT_UPDATE_MEMORY_PROMPT.md
  → 其余 prompt 文件使用默认模板
```

### 4.4 数据库字段

在 `voices` 表新增迁移列：

```sql
ALTER TABLE voices ADD COLUMN memory_workspace_config TEXT;
-- 存储 JSON，NULL 表示使用默认配置
```

---

## 5. Claude Agent 分析流程

### 5.1 整体流程图

```
用户发起分析请求
  ↓
Phase 1: 上下文组装 (assemble_context)
  ├── 构建 system_prompt（含 Memory 工作流程注入）
  ├── 初始化 Memory 工作空间（init_memory_workspace）
  │   ├── 复制 memory/ 提示词模板
  │   ├── 应用 Voice memory_workspace_config 覆盖
  │   └── 恢复程序性记忆文件
  └── 构建 user_message（含 <memory_context> 块）
  ↓
Phase 3: 执行分析 (execute_session)
  ├── Agent 读取 memory/WORKFLOW.md 了解工作流程
  ├── Agent 读取 memory/MEMORY_QUERY_PROMPT.md 执行记忆检索
  ├── Agent 读取 memory/long_term_memory.md（若存在）
  ├── Agent 读取 memory/procedural/*.json（若相关）
  ├── Agent 生成回应（参考记忆内容）
  └── Agent 更新记忆（根据 DEFAULT_UPDATE_MEMORY_PROMPT.md 决定）
  ↓
分析结束 → 持久化记忆（可选：将 procedural/ 写回 DB）
```

### 5.2 System Prompt 中的 Memory 工作流程注入

在 `context_builder.py` 的 `_SYSTEM_PROMPT_TEMPLATE` 中新增 Memory 工作流程章节：

```
## Memory Workflow

The memory/ directory in your workspace contains memory management rules.
When starting a session:
1. Read memory/WORKFLOW.md for the memory decision tree
2. Read memory/MEMORY_QUERY_PROMPT.md to retrieve relevant memories
3. Use retrieved memories to personalize your responses
4. After significant exchanges, update memories per DEFAULT_UPDATE_MEMORY_PROMPT.md
```

### 5.3 <memory_context> 用户消息块

在 `build_user_message` 中，当 `memory/long_term_memory.md` 存在时，注入：

```xml
<memory_context>
Memory workspace: {cwd}/memory/
Long-term memory summary available: yes
Procedural memory files: user_preferences.json, important_events.json
Read memory/long_term_memory.md for conversation history summary.
Read memory/WORKFLOW.md for memory management instructions.
</memory_context>
```

---

## 6. 安全与隐私

- Memory 文件存储在工作空间内，受路径遍历防护（`resolve_safe_path`）
- 程序性记忆文件不包含完整的对话记录，仅存储结构化摘要
- 用户可通过对话指令要求删除特定记忆（DELETE 操作）
- `memory/procedural/` 目录下的 JSON 文件有预定义 schema，防止随意注入

---

## 7. 改动影响范围

| 文件 | 内容 |
|------|------|
| `backend/libs/claude_agent_kit/server/memory_workspace.py` | 核心 Memory 工作空间初始化和管理 |
| `backend/libs/claude_agent_kit/server/workspace.py` | 在 `init_workspace` 中调用 `init_memory_workspace` |
| `backend/database.py` | 迁移：`voices` 表新增 `memory_workspace_config` 列 |
| `backend/routers/voices.py` | API：expose `memory_workspace_config` 字段 |
| `backend/claude_agent/context_builder.py` | 注入 Memory 工作流程到 system prompt |
| `backend/claude_agent/service.py` | 在 `assemble_context` 中应用 memory_workspace_config |
| `.claude/memory/` | Memory 提示词模板文件目录 |
| `docs/design/memory/` | 本设计文档目录 |
