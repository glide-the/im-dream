# Notion Device 资源连接器 — 交互方案设计

Status: Draft  
Updated: 2026-06-22  
Scope: 设计 — 智能体创建工作空间 Notion Device 资源连接器的完整交互流程

> [Input] `docs/design/notion-session/overview.md`,
>      `docs/design/claude-agent/edit-point/workspace-adapter.md`,
>      `docs/design/claude-agent/edit-point/workspace-context.md`,
>      `docs/design/claude-agent/edit-point/workspace-switch.md`
> [Output] 定义用户从创建资源连接器到 Agent 消费 `.notion/` 映射的完整业务交互流程
> [Pos] connector-interaction-doc in `docs/design/notion-session`
> [Sync] 2026-06-21: 初始设计 — 资源连接器交互方案
> [Sync] 2026-06-22: 修正核心概念声明 — 依据 Notion API Reference 区分 Database/Row Page/Standalone Page/Block

---

## 目录

1. [问题分析](#1-问题分析)
2. [核心概念声明](#2-核心概念声明)
3. [业务交互流程](#3-业务交互流程)
4. [资源连接器创建流程](#4-资源连接器创建流程)
5. [数据同步至 `.notion/` 映射](#5-数据同步至-notion-映射)
6. [Agent 对话消费流程](#6-agent-对话消费流程)
7. [ntn api 集成设计](#7-ntn-api-集成设计)
8. [时序图](#8-时序图)
9. [与 workspace-adapter 模式的映射关系](#9-与-workspace-adapter-模式的映射关系)
10. [不实现清单](#10-不实现清单)

---

## 1. 问题分析

### 1.1 现状评估

`overview.md` 已定义四层抽象（认证层、数据层、操作层、任务层）及 `.notion/` 虚拟索引机制，但**缺少以下关键设计**：

| 缺失项 | 影响 |
|--------|------|
| 用户创建资源连接器的交互流程 | 前端无法落地 |
| Database 选择与 PageID 映射 | Agent 无法定位用户可访问的数据 |
| `ntn api v1/search` 集成路径 | 同步任务无实现方案 |
| Agent 对话中如何触发 `.notion/` 同步 | 数据新鲜度无保障 |

### 1.2 设计边界

本文档仅覆盖**交互方案设计**，不涉及代码实现。实现细节参考 `overview.md`。

---

## 2. 核心概念声明

> 参考：[Notion API — Database](https://developers.notion.com/reference/database)

| 概念 | 定义 | 关系 |
|------|------|------|
| **Resource Connector（资源连接器）** | 连接外部平台资源到 ink-and-memory 工作空间的抽象实体 | 一个用户可拥有多个连接器 |
| **Database** | Notion 中定义属性 Schema（列/字段）的特殊对象。可以是 full-page database 或 inline database（内嵌于某个 Page 中）。Database 本身不包含内容块，仅定义 properties schema | 一个连接器可关联多个 Database |
| **Page（页面）** | Notion 中的内容单元。分为两类：① **Database Row Page** — parent 为 database，属性值遵循所属 Database 的 schema；② **Standalone Page** — parent 为 workspace 或另一个 page，与 Database 无关联 | 一个 Database 下可包含多个 Row Page；Standalone Page 独立存在 |
| **PageID** | Page 的唯一标识（UUID）。无论是 Database Row Page 还是 Standalone Page，均拥有独立的 PageID | — |
| **Block** | Notion 中的最小内容单元（段落、标题、列表等）。Page 由 Block 组成；Database 不直接包含 Block | Page 的 children |
| **`.notion/` 映射文件** | 工作空间内的虚拟索引目录，缓存连接器同步的数据 | 与连接器数据层强关联 |
| **ntn api** | Notion 官方 CLI 提供的 API 直调命令 | 自动处理 Auth/Version 头 |

### 2.1 Notion 对象层次（API 视角）

```
Workspace
  ├── Database (定义 properties schema)
  │     └── Page (Database Row — 属性值遵循 schema)
  │           └── Block (段落/标题/列表等内容块)
  └── Page (Standalone — 独立页面，无 Database 关联)
        ├── Block (内容块)
        └── Database (Inline — 内嵌数据库，parent 为此 Page)
              └── Page (Database Row)
```

### 2.2 资源连接器映射层次

```
Resource Connector (资源连接器)
  ├── Database (用户选定的数据库)
  │     └── Page (Database Row)
  │           └── .notion/pages/<page_id>.json
  └── Standalone Page (独立页面，通过 v1/search 发现)
        └── .notion/pages/<page_id>.json
```

---

## 3. 业务交互流程

### 3.1 全局流程概览

```
用户创建资源连接器
    │
    ├─ 选择认证平台服务 (Notion)
    │
    ├─ 完成 ntn login 认证
    │
    ├─ 用户选择可访问的 Database 及 Standalone Page
    │     └─ 后端通过 ntn api v1/search 分别获取 database 和 page 列表
    │
    ├─ 后端同步数据层
    │     └─ 将选定 Database 的 Row Page 及 Standalone Page 清单写入 .notion/ 映射文件
    │
    └─ 用户 Chat 对话
          │
          ├─ 同步资源连接器的平台信息到 .notion/ 映射文件
          │
          └─ 同步常用 notion-cli skill 到工作空间
```

### 3.2 流程阶段定义

| 阶段 | 触发者 | 输出 | 存储位置 |
|------|--------|------|---------|
| 1. 创建连接器 | 用户（前端） | connector 实体 | 数据库 `resource_connectors` 表 |
| 2. 认证 | 用户（浏览器确认） | ntn token | `NOTION_HOME/` |
| 3. Database 及 Page 选择 | 用户（前端列表） | 选定的 database_id 及 standalone page_id 列表 | `resource_connectors.databases` / `.selected_pages` |
| 4. 数据同步 | 后端（自动） | Database Row Page + Standalone Page 清单 | `.notion/index.json` |
| 5. 对话消费 | Agent（PreToolUse） | 页面内容 | `.notion/pages/<id>.json` |

---

## 4. 资源连接器创建流程

### 4.1 前端交互步骤

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 选择平台                                             │
│                                                             │
│   [Notion]  [GitHub]  [Google Drive]  ...                   │
│     ↓                                                       │
│ Step 2: 认证                                                 │
│                                                             │
│   "正在连接 Notion..."                                       │
│   验证码: VAF-HWY                                           │
│   [打开浏览器确认] ← 用户点击                                 │
│     ↓                                                       │
│ Step 3: 选择 Database 及 Standalone Page                     │
│                                                             │
│   Databases:                                                │
│   ☑ ink-and-memory 代办清单                                  │
│   ☑ 阅读笔记                                                │
│   ☐ 项目管理看板                                             │
│                                                             │
│   Standalone Pages:                                         │
│   ☑ 产品设计文档                                             │
│   ☐ 个人日记                                                 │
│   [确认选择]                                                 │
│     ↓                                                       │
│ Step 4: 同步完成                                             │
│                                                             │
│   "已同步 2 个数据库，共 47 个页面"                           │
│   [完成]                                                     │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 API 设计

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/connectors` | POST | 创建资源连接器 |
| `/api/connectors/:id/auth/login` | POST | 启动 ntn login 认证 |
| `/api/connectors/:id/auth/poll` | POST | 轮询认证完成状态 |
| `/api/connectors/:id/databases` | GET | 获取可访问的 database 列表 |
| `/api/connectors/:id/pages` | GET | 获取可访问的 standalone page 列表 |
| `/api/connectors/:id/resources/select` | POST | 用户选择要同步的 database 和 standalone page |
| `/api/connectors/:id/sync` | POST | 触发数据同步 |

### 4.3 数据模型

```
resource_connectors
├── id: UUID
├── user_id: FK → users
├── platform: "notion"
├── auth_status: "pending" | "authenticated" | "expired"
├── config: JSON
│     ├── notion_home: string
│     ├── selected_databases: string[]  ← 用户选定的 database_id 列表
│     └── selected_pages: string[]      ← 用户选定的 standalone page_id 列表
├── last_synced_at: timestamp
├── created_at: timestamp
└── updated_at: timestamp
```

---

## 5. 数据同步至 `.notion/` 映射

### 5.1 同步触发时机

| 时机 | 触发方式 | 同步范围 |
|------|---------|---------|
| 连接器创建完成 | 自动 | 全量：选定 Database 的 Row Page + Standalone Page |
| 用户进入对话 | workspace init 时检测 | 增量：距上次同步有变更的页面 |
| Agent 对话中显式请求 | Agent 调用 sync skill | 按需：指定 database 或 page |

### 5.2 `.notion/` 映射文件结构（扩展）

```
.notion/
├── README.md                    ← Agent 引导说明
├── connector.json               ← ★ 连接器元信息
├── index.json                   ← 所有已同步 Page 列表
├── databases.json               ← 选定的 Database 元信息
├── databases/
│     ├── <db_id_1>.json         ← Database 1 的 Page 清单
│     └── <db_id_2>.json         ← Database 2 的 Page 清单
└── pages/
      └── <page_id>.json         ← 单页内容（lazy load）
```

### 5.3 `connector.json` 内容

```json
{
  "connector_id": "conn-abc123",
  "platform": "notion",
  "auth_status": "authenticated",
  "selected_databases": [
    {
      "database_id": "db-001",
      "title": "ink-and-memory 代办清单",
      "page_count": 32
    },
    {
      "database_id": "db-002",
      "title": "阅读笔记",
      "page_count": 15
    }
  ],
  "selected_standalone_pages": [
    {
      "page_id": "page-xyz",
      "title": "产品设计文档"
    }
  ],
  "last_synced_at": "2026-06-21T14:00:00Z"
}
```

### 5.4 `databases/<db_id>.json` 内容

> Database 下的每个 Page 是一个 Row Page，其属性值遵循该 Database 的 properties schema。

```json
{
  "database_id": "db-001",
  "title": "ink-and-memory 代办清单",
  "properties_schema": {
    "Name": { "type": "title" },
    "Status": { "type": "select" },
    "Due": { "type": "date" }
  },
  "pages": [
    {
      "page_id": "page-aaa",
      "title": "用户认证模块重构",
      "last_edited": "2026-06-20T10:30:00Z",
      "status": "In Progress"
    },
    {
      "page_id": "page-bbb",
      "title": "前端组件优化",
      "last_edited": "2026-06-19T08:00:00Z",
      "status": "Done"
    }
  ],
  "synced_at": "2026-06-21T14:00:00Z"
}
```

---

## 6. Agent 对话消费流程

### 6.1 Agent 感知资源连接器

当用户进入对话时，`<workspace_context>` 中注入连接器状态信息：

```
Notion Device Connector:
  Status: authenticated
  Databases: 2 (ink-and-memory 代办清单, 阅读笔记)
  Total Pages: 47
  Last Synced: 2026-06-21T14:00:00Z

  Read .notion/connector.json for connector details.
  Read .notion/index.json for page listing.
  Read .notion/databases/<db_id>.json for database-specific pages.
```

### 6.2 Notion CLI Skill 同步

资源连接器创建成功后，自动同步常用 notion-cli skill 到工作空间 `skills/` 目录：

| Skill 文件 | 用途 |
|------------|------|
| `skills/notion-search.md` | 通过 ntn api 搜索 Notion 内容 |
| `skills/notion-page-read.md` | 读取指定页面完整内容 |
| `skills/notion-db-query.md` | 查询指定 Database 下的页面 |

各 Skill 文件的完整设计详见：[`skills/`](./skills/) 目录

- [`skills/notion-search.md`](./skills/notion-search.md) — 搜索 Notion 内容
- [`skills/notion-page-read.md`](./skills/notion-page-read.md) — 读取页面完整内容
- [`skills/notion-db-query.md`](./skills/notion-db-query.md) — 查询 Database 下的页面

---

## 7. ntn api 集成设计

### 7.1 核心命令映射

| 业务需求 | ntn api 命令 | 调用时机 |
|---------|-------------|---------|
| 获取 Database 列表 | `ntn api v1/search filter:='{"property":"object","value":"database"}'` | 连接器创建 Step 3（Database 选择） |
| 获取 Standalone Page 列表 | `ntn api v1/search filter:='{"property":"object","value":"page"}' page_size:=100` | 连接器创建 Step 3（Page 选择） |
| 获取 Database 下的 Row Page | `ntn api v1/databases/<db_id>/query` | 数据同步阶段 |
| 获取 Data Source 列表 | `ntn api v1/search filter:='{"property":"object","value":"data_source"}'` | 连接器初始化 |

### 7.2 后端封装

```python
# 概念设计 — 不是实现代码
class NotionAPIBridge:
    """封装 ntn api CLI 调用，统一错误处理与超时管理。"""

    async def search(self, filter_obj: dict, page_size: int = 100) -> dict:
        """调用 v1/search 端点。"""
        ...

    async def list_databases(self) -> list[dict]:
        """获取用户可访问的所有 Database。"""
        ...

    async def list_standalone_pages(self) -> list[dict]:
        """获取用户可访问的 Standalone Page（非 Database Row）。"""
        ...

    async def query_database(self, database_id: str) -> list[dict]:
        """查询指定 Database 下的 Row Page 列表。"""
        ...
```

### 7.3 错误处理策略

| 错误类型 | 处理方式 |
|---------|---------|
| Token 过期 | 标记 connector.auth_status = "expired"，提示用户重新认证 |
| ntn CLI 不可用 | 返回友好错误，建议用户安装 ntn |
| API 限流 | 指数退避重试，最多 3 次 |
| 网络超时 | 使用缓存数据，标记 stale |

---

## 8. 时序图

### 8.1 资源连接器创建完整流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Front as 前端
    participant Back as 后端
    participant CLI as ntn CLI
    participant Notion as Notion API

    User->>Front: 创建资源连接器
    Front->>Back: POST /api/connectors {platform:"notion"}
    Back-->>Front: {connector_id, status:"pending"}

    User->>Front: 开始认证
    Front->>Back: POST /api/connectors/:id/auth/login
    Back->>CLI: ntn login --no-browser
    CLI-->>Back: verificationUrl + code
    Back-->>Front: {verificationUrl, code}
    User->>Notion: 浏览器确认
    Front->>Back: POST /api/connectors/:id/auth/poll
    Back->>CLI: ntn login poll
    CLI-->>Back: exit 0 (认证成功)
    Back-->>Front: {auth_status:"authenticated"}

    Front->>Back: GET /api/connectors/:id/databases
    Back->>CLI: ntn api v1/search filter:=database
    CLI->>Notion: POST /v1/search
    Notion-->>CLI: database list
    CLI-->>Back: JSON
    Back-->>Front: [{database_id, title}, ...]

    Front->>Back: GET /api/connectors/:id/pages
    Back->>CLI: ntn api v1/search filter:=page
    CLI->>Notion: POST /v1/search
    Notion-->>CLI: standalone page list
    CLI-->>Back: JSON
    Back-->>Front: [{page_id, title}, ...]

    User->>Front: 选择 Database 及 Standalone Page
    Front->>Back: POST /api/connectors/:id/resources/select
    Back->>Back: 存储选定的 database_id 及 page_id 列表

    Back->>CLI: ntn api v1/databases/<db_id>/query (per db)
    CLI->>Notion: POST /v1/databases/:id/query
    Notion-->>CLI: row page list
    CLI-->>Back: JSON
    Back->>Back: 写入 .notion/ 映射文件（databases/ + pages/）
    Back-->>Front: {synced:true, database_count:2, page_count:47}
```

### 8.2 Agent 对话中同步 `.notion/` 流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Agent as Claude Agent
    participant Hook as PreToolUse Hook
    participant Cache as NotionCache
    participant CLI as ntn CLI

    User->>Agent: "帮我看看 Notion 代办清单"
    Agent->>Agent: 检查 workspace_context 中的连接器信息
    Agent->>Hook: Read .notion/connector.json
    Hook->>Cache: get connector metadata
    Cache-->>Hook: connector info
    Hook-->>Agent: connector.json 内容

    Agent->>Hook: Read .notion/databases/db-001.json
    Hook->>Cache: check db-001 cache
    alt 缓存过期或缺失
        Hook->>CLI: ntn api v1/databases/db-001/query
        CLI-->>Hook: page list JSON
        Hook->>Cache: 更新缓存
    end
    Cache-->>Hook: database pages
    Hook-->>Agent: db-001.json 内容

    Agent-->>User: "代办清单中有 32 个页面，最近编辑的是..."
```

---

## 9. 与 workspace-adapter 模式的映射关系

### 9.1 模式对称性

本设计严格遵循 `workspace-adapter.md` 确立的虚拟索引模式：

| workspace-adapter 模式 | Notion Connector 对应实现 |
|------------------------|--------------------------|
| `.editor/` 虚拟索引 | `.notion/` 虚拟索引 |
| `editor_state` 内存快照 | `notion_cache` 内存缓存 |
| `EDITOR_RESOURCES` 映射表 | `NOTION_RESOURCES` 映射表 |
| PreToolUse 拦截 Read | PreToolUse 拦截 Read（相同机制） |
| `switch_editor` 切换上下文 | `switch_editor(device="notion")` 切换设备 |
| workspace init 初始化 `.editor/` | workspace init 初始化 `.notion/`（条件：已认证） |

### 9.2 与 workspace-context 的集成

参考 `workspace-context.md` 的 `<workspace_context>` 块设计，Notion 连接器信息作为新的上下文段落注入：

```
<!-- workspace_context 中新增段落 -->
Notion Device (.notion/):
  Connector: authenticated | 2 databases | 47 pages
  Read .notion/index.json for full page listing.
  Read .notion/databases/<db_id>.json for per-database view.
```

### 9.3 与 workspace-switch 的集成

参考 `workspace-switch.md` 的 PostToolUse 钩子模式，Notion 设备切换复用相同的 `switch_editor` 工具，仅扩展参数（详见 `overview.md` 第 6 节）。

---

## 10. 不实现清单

防止过度设计，以下内容**明确排除**：

| 排除项 | 原因 |
|--------|------|
| 多平台资源连接器统一框架 | 先只做 Notion，后续再抽象 |
| 实时 WebSocket 数据推送 | 轮询 + 按需加载足够 |
| 页面内容全文索引/搜索 | 直接用 `ntn api v1/search` |
| 双向写回 Notion | 写操作冲突策略未定义 |
| 连接器权限分级（只读/读写） | 本期仅只读 |
| 前端可视化 Database Schema | 先仅展示标题列表 |
| 自动检测 Schema 变更 | 先做全量同步 |
| 多用户共享同一连接器 | 连接器绑定单用户 |

---

## 附录 A：设计决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 数据通道 | Notion SDK / ntn CLI | ntn CLI | 复用已有 CLI 认证，零额外依赖 |
| 同步方式 | 实时 / 定时 / 按需 | workspace init + 按需 | 避免后台常驻进程，简化部署 |
| 映射存储 | 数据库 / 文件系统 | `.notion/` 虚拟索引 | 与 `.editor/` 模式对称，Agent 直接可读 |
| Database 发现 | 硬编码 / 用户选择 | 用户选择 | 用户决定哪些数据对 Agent 可见 |
| PageID 同步 | 全量 / 增量 | 全量（本期） | 实现简单，后续可优化 |
