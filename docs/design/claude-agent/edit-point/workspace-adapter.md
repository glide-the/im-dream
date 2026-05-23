# EditorState 工作空间文件系统适配器

Status: Draft  
Updated: 2026-05-23  
Scope: Design only — 不含实现代码

---

## 目录

1. [设计背景](#1-设计背景)
2. [工作空间目录结构](#2-工作空间目录结构)
3. [文件格式规范](#3-文件格式规范)
4. [适配器职责与接口](#4-适配器职责与接口)
5. [同步策略](#5-同步策略)
6. [读写路径分离](#6-读写路径分离)
7. [与工作空间文件系统的集成](#7-与工作空间文件系统的集成)

---

## 1. 设计背景

### 1.1 问题

Claude Agent 需要"读取"当前文档内容才能进行分析、建议和修改。当前 EditorState 仅存在于：
- 前端内存（EditorEngine 维护）
- 后端数据库（`/api/sessions` 持久化的 JSON blob）

这两处 Agent 均无法直接访问（数据库不可直接读，前端内存更不可达）。

### 1.2 解决方案

引入 **SessionWorkspaceAdapter**：在每次 EditorState 变更后，将状态以结构化文件的形式同步到 Claude Agent 的工作空间文件系统（`AGENT_CWD`）。Agent 通过 `read_file` 原生能力读取文档内容，无需新增 API。

**核心思路：**
```
EditorState（内存）
    ↓ SessionWorkspaceAdapter.sync()
工作空间文件系统（{AGENT_CWD}/{userId}/document/）
    ↑ Claude Agent read_file
```

---

## 2. 工作空间目录结构

在现有工作空间结构的基础上，新增 `document/` 子目录：

```
{AGENT_CWD}/
  └── {userId}/                        ← 用户工作空间根
      ├── .claude/                     ← Claude 配置（现有）
      ├── .mcp.json                    ← MCP 服务配置（现有）
      ├── files/                       ← 用户上传文件（现有）
      ├── logs/                        ← Agent 执行日志（现有）
      ├── skills/                      ← Skills（现有）
      └── document/                    ← ★ 新增：EditorState 镜像
            ├── manifest.json          ← 文档元数据 + 片段有序列表
            ├── segments/              ← 各片段文件
            │     ├── {cellId}.txt     ← 文本片段（纯文本）
            │     └── {cellId}.json    ← 组件片段（JSON）
            └── comments/             ← 已应用评论文件
                  └── {commentorId}.json
```

---

## 3. 文件格式规范

### 3.1 `manifest.json` — 文档总览

Agent 读取文档的入口文件，包含会话元数据和片段有序列表。

```json
{
  "sessionId": "sess-uuid-xxxx",
  "createdAt": "2026-05-23T08:00:00.000Z",
  "selectedState": "平静",
  "lastSyncedAt": "2026-05-23T08:30:12.345Z",
  "segments": [
    {
      "id": "cell-001",
      "type": "text",
      "file": "segments/cell-001.txt",
      "length": 48
    },
    {
      "id": "cell-002",
      "type": "widget",
      "widgetType": "chat",
      "file": "segments/cell-002.json"
    },
    {
      "id": "cell-003",
      "type": "text",
      "file": "segments/cell-003.txt",
      "length": 62
    }
  ],
  "commentCount": 3,
  "commentsDir": "comments/"
}
```

### 3.2 `segments/{cellId}.txt` — 文本片段

```
今天的天空很蓝，我想起了那个夏天的午后。风吹过院子里的老树，
叶子哗哗作响，像是在说什么秘密的话。
```

纯文本文件，UTF-8 编码，无额外格式包装。Agent 可直接 `read_file` 获取完整文本。

### 3.3 `segments/{cellId}.json` — 组件片段

```json
{
  "id": "cell-002",
  "type": "widget",
  "widgetType": "chat",
  "data": {
    "voiceId": "voice-azure",
    "messages": [
      { "role": "assistant", "content": "这段文字让我想到了……" },
      { "role": "user", "content": "你觉得这个比喻怎么样？" }
    ]
  }
}
```

### 3.4 `comments/{commentorId}.json` — 评论

```json
{
  "id": "cmt-uuid-xxxx",
  "phrase": "风吹过院子里的老树",
  "comment": "这个意象很有力量，树的沉默与风的流动形成了对话。",
  "voiceId": "voice-azure",
  "voice": "Azure",
  "icon": "🌙",
  "color": "#4A90D9",
  "appliedAt": 1716451812345,
  "computedAt": 1716451800000,
  "feedback": null,
  "chatHistory": [
    {
      "role": "assistant",
      "content": "这个意象很有力量，树的沉默与风的流动形成了对话。"
    },
    {
      "role": "user",
      "content": "我想让这段更有节奏感，你有什么建议吗？"
    },
    {
      "role": "assistant",
      "content": "可以考虑在"老树"和"叶子"之间加一个短句停顿……"
    }
  ]
}
```

---

## 4. 适配器职责与接口

### 4.1 SessionWorkspaceAdapter

适配器负责将 EditorState 快照单向同步到工作空间文件系统。

**核心职责：**
1. 在 EditorEngine `notifyChange()` 之后（或防抖后）触发同步
2. 将 EditorState 中的 cells 逐一写入 `segments/` 对应文件
3. 将已应用的 commentors 写入 `comments/` 对应文件
4. 更新 `manifest.json`
5. 清理已删除的 cell/commentor 对应文件

**接口概念（设计层面）：**

```typescript
interface SessionWorkspaceAdapter {
  // 全量同步当前 EditorState 到文件系统
  sync(state: EditorState, workspacePath: string): Promise<void>;

  // 增量同步单个 cell（Engine 方法调用后触发）
  syncCell(cell: Cell, workspacePath: string): Promise<void>;

  // 增量同步单个 commentor（评论应用后触发）
  syncCommentor(commentor: Commentor, workspacePath: string): Promise<void>;

  // 删除文件（cell 或 commentor 被移除后）
  removeCell(cellId: string, workspacePath: string): Promise<void>;
  removeCommentor(commentorId: string, workspacePath: string): Promise<void>;
}
```

### 4.2 工作空间路径解析

用户的工作空间路径基于现有工作空间设计（见 [`../workspace-filesystem.md`](../workspace-filesystem.md)）：

```
workspacePath = {AGENT_CWD}/{userId}
documentPath  = {workspacePath}/document/
```

与现有的 `get_or_create_workspace(session_id)` 集成：`document/` 目录在工作空间初始化时一并创建，或在首次同步时按需创建。

---

## 5. 同步策略

### 5.1 触发时机

| 触发点 | 同步类型 | 说明 |
|--------|---------|------|
| EditorEngine `notifyChange()` 后 | 防抖增量同步（1s） | 人类键入时频繁触发，避免每次按键都写文件 |
| 会话保存成功（`saveSessionToDatabase` 后） | 全量同步 | 确保文件系统与 DB 数据一致 |
| Agent MCP 工具写操作执行后 | 立即增量同步 | Agent 写入后立即可读，保证后续 `read_file` 的一致性 |
| 会话加载（`loadState` 后） | 全量同步 | 从 DB 恢复状态后同步到文件 |

### 5.2 增量 vs 全量

- **增量同步**：仅写入变更的 cell/commentor 文件，更新 `manifest.json` 的 `lastSyncedAt`
- **全量同步**：重写所有文件，清理孤立文件（已删除 cell 对应的文件），重建 `manifest.json`

### 5.3 失败处理

同步失败（如文件系统写入错误）：
- 记录错误日志，不阻塞 EditorEngine 主流程（副作用，非关键路径）
- 保留重试队列，下次触发时补偿同步
- 同步失败不影响 Agent 通过 MCP 只读工具获取数据（MCP 工具直接从 EditorState 内存读取）

---

## 6. 读写路径分离

```
Agent 读取文档内容：
  ┌─ 方式 A（推荐）: read_file("document/manifest.json")
  │                  read_file("document/segments/cell-001.txt")
  │                  → 直接读工作空间文件（无 MCP 调用开销）
  │
  └─ 方式 B: 调用 MCP 工具 list_segments / read_segment
             → MCP Server 从 EditorState 内存读取（最新状态，无文件延迟）

Agent 修改文档内容：
  └─ 唯一路径: 调用 MCP 工具 write_segment / delete_segment
               → PreToolUse 拦截 → 人类确认 → EditorEngine 执行 → 适配器同步文件
               ⚠️ 禁止直接写文件（写文件不经过 EditorEngine，状态不一致）
```

**设计约束：**
- `document/` 目录对 Agent 的文件系统权限：**只读**（write_file 操作应被 MCP 工具权限配置阻止）
- 所有写操作必须通过 MCP 工具路径，以确保：
  1. 经过人类确认
  2. 经过 EditorEngine 的状态校验（能量门控、类型约束等）
  3. 触发 React 订阅者重新渲染

---

## 7. 与工作空间文件系统的集成

现有工作空间结构（见 [`../workspace-filesystem.md`](../workspace-filesystem.md)）在 `init_workspace` 时创建 `files/`, `logs/`, `skills/` 三个子目录。新增 `document/` 作为第四个标准子目录：

```python
# workspace.py 扩展（设计层面）
WORKSPACE_DIRS = {
    "files": "files",
    "logs": "logs",
    "skills": "skills",
    "document": "document",          # ★ 新增
    "document_segments": "document/segments",   # ★ 新增
    "document_comments": "document/comments",   # ★ 新增
}
```

`document/` 目录的初始状态为空（无 `manifest.json`），首次同步时由适配器写入。
