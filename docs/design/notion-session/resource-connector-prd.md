# 资源连接器 — 前端 PRD & ER 设计

Status: Draft  
Updated: 2026-07-04  
Scope: 产品设计 — 资源连接器功能定义、前端页面交互、ER 关系模型

> [Input] `docs/design/notion-session/connector-interaction.md`,
>      `docs/design/notion-session/overview.md`,
>      `docs/design/claude-agent/notion-point/resource-connector-layer-design.md`
> [Output] 资源连接器前端 PRD：功能定义、页面交互设计、ER 模型、不实现清单
> [Pos] resource-connector-prd in `docs/design/notion-session`
> [Sync] 2026-07-04: 初版 — 资源连接器功能定义、页面 PRD、ER 关系设计

---

## 目录

1. [产品定位](#1-产品定位)
2. [功能定义](#2-功能定义)
3. [ER 关系模型](#3-er-关系模型)
4. [页面结构设计](#4-页面结构设计)
5. [交互流程设计](#5-交互流程设计)
6. [状态定义](#6-状态定义)
7. [不实现清单](#7-不实现清单)

---

## 1. 产品定位

### 1.1 是什么

**资源连接器**（Resource Connector）是工作空间上层的多功能交互空间。用户在此创建并管理外部平台资源连接，连接器下方可挂载多个数据源（Database、Page），并在同一空间内发起对话、上传工作空间文件、选择 Decks。

### 1.2 核心价值

- 为 Agent 提供外部平台的结构化背景信息（类似 ChatGPT Projects 的"来源"功能）
- 用户无需反复描述上下文，连接器自动将平台数据同步为 Agent 可读的 `.notion/` 映射

### 1.3 类比理解

| 类比对象 | 对应关系 |
|---------|---------|
| ChatGPT Projects "来源" Tab | 资源连接器的"来源"视图 |
| Slack / Google Drive 连接 | Notion 资源连接器 |
| Projects "聊天" Tab | 资源连接器的对话入口 |
| 上传数据源 / 链接云端硬盘 | 连接器的多资源挂载 |

---

## 2. 功能定义

### 2.1 核心功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 创建资源连接器 | 用户在工作空间中创建一个命名的连接器空间 | P0 |
| 连接外部平台 | 选择平台（Notion）→ 完成 OAuth 认证 | P0 |
| 选择资源 | 用户勾选可访问的 Database 及 Standalone Page | P0 |
| 发起对话 | 在连接器空间内直接 Chat，Agent 自动感知已连接资源 | P0 |
| 查看来源 | 查看已连接的所有资源列表及同步状态 | P0 |
| 上传工作空间文件 | 上传本地文件作为补充背景 | P1 |
| 选择 Decks | 关联已有的 Deck 知识卡片集 | P1 |
| 刷新同步 | 手动触发资源重新同步 | P1 |

### 2.2 连接器空间内的子功能

```
资源连接器空间
  ├── 聊天 Tab        → 在连接器上下文中发起对话
  ├── 来源 Tab        → 管理已连接资源（添加/删除/刷新）
  │     ├── 已连接平台资源（Notion Database/Page）
  │     ├── 上传文件
  │     └── 关联 Decks
  └── 设置           → 连接器名称、删除、权限
```

---

## 3. ER 关系模型

### 3.1 ER 图

```text
users
────────────────────────────────────────────────────────────
 PK  id              INTEGER

        │ 1
        │
        │ N

resource_connectors
────────────────────────────────────────────────────────────
 PK  id              TEXT (UUID)
 FK  user_id         INTEGER → users.id ON DELETE CASCADE
     name            TEXT NOT NULL          ← 连接器显示名称
     platform        TEXT NOT NULL          ← "notion" | "github" | ...
     auth_status     TEXT DEFAULT 'pending' ← "pending" | "authenticated" | "expired"
     config          JSON                   ← 平台配置（notion_home 等）
     last_synced_at  DATETIME NULL
     created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
     updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
────────────────────────────────────────────────────────────
 INDEX: (user_id, updated_at DESC)

        │ 1
        │
        │ N

connector_resources
────────────────────────────────────────────────────────────
 PK  id              TEXT (UUID)
 FK  connector_id    TEXT → resource_connectors.id ON DELETE CASCADE
     resource_type   TEXT NOT NULL          ← "notion_database" | "notion_page" | "file" | "deck"
     external_id     TEXT NULL              ← 平台资源 ID（database_id / page_id）
     title           TEXT NOT NULL          ← 资源显示标题
     metadata        JSON NULL              ← 资源元信息（page_count, schema 等）
     sync_status     TEXT DEFAULT 'synced'  ← "syncing" | "synced" | "error"
     created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
────────────────────────────────────────────────────────────
 INDEX: (connector_id, resource_type)
 UNIQUE: (connector_id, resource_type, external_id)

        │ 1 (resource_type = "notion_database")
        │
        │ N

connector_resource_pages
────────────────────────────────────────────────────────────
 PK  id              TEXT (UUID)
 FK  resource_id     TEXT → connector_resources.id ON DELETE CASCADE
     page_id         TEXT NOT NULL          ← Notion Page UUID
     title           TEXT NOT NULL
     last_edited     DATETIME NULL
     properties_json JSON NULL              ← Row Page 属性值快照
     created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
────────────────────────────────────────────────────────────
 INDEX: (resource_id, last_edited DESC)

        │ 1 (resource_connectors)
        │
        │ N

connector_chat_threads
────────────────────────────────────────────────────────────
 PK  id              TEXT (UUID)
 FK  connector_id    TEXT → resource_connectors.id ON DELETE CASCADE
 FK  thread_id       TEXT → chat_thread.id         ← 复用现有 chat_thread
     created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
────────────────────────────────────────────────────────────
 INDEX: (connector_id, created_at DESC)
```

### 3.2 关系说明

```
users (1) ──→ (N) resource_connectors
                    │
                    ├── (1) ──→ (N) connector_resources
                    │                   │
                    │                   └── (1) ──→ (N) connector_resource_pages
                    │                                    (仅 notion_database 类型)
                    │
                    └── (1) ──→ (N) connector_chat_threads ──→ chat_thread
```

### 3.3 关键约束

| 约束 | 说明 |
|------|------|
| 连接器绑定单用户 | `resource_connectors.user_id` 不可共享 |
| 资源去重 | `(connector_id, resource_type, external_id)` UNIQUE |
| 级联删除 | 删除连接器 → 级联删除所有关联资源和页面索引 |
| chat_thread 复用 | 连接器内的对话复用已有的 `chat_thread` 模型，通过中间表关联 |

---

## 4. 页面结构设计

### 4.1 主页面布局

参考 ChatGPT Projects 页面模式：

```
┌─────────────────────────────────────────────────────────────────┐
│ ◻ [连接器名称]                              [分享] [···]         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ＋  [连接器名称] 中的新聊天       [模型选择 ▾] 🎤 ⚡    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│   [ 聊天 ]  (( 来源 ))                     [最新 ▾] [全部 ▾]    │
│                                                                 │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
│  │                                                           │  │
│  │        🔗  📁  📎                                         │  │
│  │                                                           │  │
│  │     为 Agent 提供更多背景信息                               │  │
│  │                                                           │  │
│  │   上传数据源、链接云端平台或连接 Notion 等应用，             │  │
│  │   为 Agent 提供项目的更深层次背景信息。                      │  │
│  │                                                           │  │
│  │            [ 添加来源 ]                                    │  │
│  │                                                           │  │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 页面组件拆解

| 区域 | 组件 | 说明 |
|------|------|------|
| 顶栏 | ConnectorHeader | 连接器名称（可编辑）、分享按钮、更多菜单 |
| 输入栏 | ChatInputBar | 对话输入框，附带模型选择、语音、发送按钮 |
| Tab 栏 | TabSwitch | "聊天" / "来源" 切换；来源 Tab 含筛选器 |
| 空状态 | EmptySourcePanel | 虚线框引导，3 个图标 + 文案 + "添加来源"按钮 |
| 来源列表 | SourceList | 已添加的资源卡片列表（连接后显示） |
| 聊天列表 | ChatList | 该连接器下的历史对话列表 |

### 4.3 "来源" Tab 详细设计

#### 空状态（无来源时）

居中虚线框区域，显示：
- 平台图标行：Notion 图标 / Google Drive 图标 / 附件图标
- 主文案："为 Agent 提供更多背景信息"
- 副文案："上传数据源、链接云端平台或连接 Notion 等应用，为 Agent 提供项目的更深层次背景信息。"
- CTA 按钮：「添加来源」

#### 有来源时

```
┌─────────────────────────────────────────────────────────────┐
│ [ 聊天 ]  (( 来源 ))                   [最新 ▾] [全部 ▾]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🔗 Notion · ink-and-memory 代办清单    [32 页] [已同步] │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🔗 Notion · 阅读笔记                  [15 页] [已同步] │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📄 产品设计文档.pdf                    [2.1MB] [已上传] │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📦 Deck · 技术方案集                   [12 cards]      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│                     [ ＋ 添加来源 ]                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 筛选器

- **排序**：最新 / 最早 / 名称
- **类型筛选**：全部 / Notion / 文件 / Decks

### 4.4 "聊天" Tab 设计

```
┌─────────────────────────────────────────────────────────────┐
│ [ 聊天 ]  (( 来源 ))                   [最新 ▾] [全部 ▾]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 帮我看看 Notion 代办清单的进度          今天 10:30      │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 总结阅读笔记中关于设计模式的内容         昨天 16:20      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

点击某条对话 → 进入标准聊天页面，Agent 自动 attach 当前连接器的 canonical snapshot。

---

## 5. 交互流程设计

### 5.1 创建资源连接器

```
用户点击 "新建连接器"
    │
    ├─ 弹出 Modal: 输入连接器名称
    │     └─ 确认 → POST /api/connectors {name, platform:"notion"}
    │
    └─ 创建成功 → 跳转连接器主页面（空状态）
```

### 5.2 添加来源（连接 Notion）

```
用户点击 "添加来源"
    │
    ├─ 弹出 ActionSheet / Modal: 选择来源类型
    │     ├── 连接 Notion
    │     ├── 上传文件
    │     └── 关联 Deck
    │
    ├─ (选择 Notion) → 启动认证流程
    │     ├─ POST /api/connectors/:id/auth/login
    │     ├─ 显示验证码 + "打开浏览器确认" 按钮
    │     ├─ 轮询 POST /api/connectors/:id/auth/poll
    │     └─ 认证成功 → 进入资源选择
    │
    ├─ 资源选择 Modal
    │     ├─ 展示 Database 列表（可多选）
    │     ├─ 展示 Standalone Page 列表（可多选）
    │     └─ 确认 → POST /api/connectors/:id/resources/select
    │
    └─ 后端同步 → 来源 Tab 显示新资源卡片
```

### 5.3 发起对话

```
用户在输入栏输入消息
    │
    ├─ 前端创建 chat_thread（复用现有逻辑）
    ├─ 创建 connector_chat_threads 关联
    ├─ 后端 Agent init:
    │     ├─ attach connector 的 canonical snapshot
    │     ├─ 注入 workspace_context（含 Notion 连接器信息）
    │     └─ .notion/ 虚拟索引可读
    │
    └─ Agent 响应（可读取 .notion/ 下的资源数据）
```

### 5.4 上传文件

```
用户点击 "添加来源" → "上传文件"
    │
    ├─ 文件选择器（支持 PDF、TXT、MD、DOCX）
    ├─ POST /api/connectors/:id/files/upload
    ├─ 创建 connector_resources (type="file")
    │
    └─ 文件存储到工作空间文件系统
```

### 5.5 关联 Deck

```
用户点击 "添加来源" → "关联 Deck"
    │
    ├─ Deck 选择列表（用户已有 Decks）
    ├─ POST /api/connectors/:id/resources/select {type:"deck", deck_id}
    ├─ 创建 connector_resources (type="deck")
    │
    └─ 来源 Tab 显示关联的 Deck 卡片
```

---

## 6. 状态定义

### 6.1 连接器状态

| 状态 | 说明 | 前端展示 |
|------|------|---------|
| `pending` | 已创建，未认证 | 显示"未连接"标签 |
| `authenticated` | 认证成功，资源已同步 | 正常展示来源 |
| `expired` | Token 过期 | 显示"需重新认证"提示 |

### 6.2 资源同步状态

| 状态 | 说明 | 前端展示 |
|------|------|---------|
| `syncing` | 正在同步中 | 资源卡片显示 loading |
| `synced` | 同步完成 | 显示"已同步" + 页面数 |
| `error` | 同步失败 | 显示错误提示 + 重试按钮 |

### 6.3 来源类型图标映射

| resource_type | 图标 | 显示格式 |
|--------------|------|---------|
| `notion_database` | 🔗 | "Notion · {title} [{page_count} 页]" |
| `notion_page` | 📝 | "Notion · {title}" |
| `file` | 📄 | "{filename} [{size}]" |
| `deck` | 📦 | "Deck · {title} [{card_count} cards]" |

---

## 7. 不实现清单

防止过度设计，以下内容**明确排除**：

| 排除项 | 原因 |
|--------|------|
| 多人协作同一连接器 | 连接器绑定单用户，后续再扩展 |
| 连接器间数据共享 | 每个连接器独立，不做跨连接器引用 |
| 来源实时搜索/全文索引 | 先依赖列表展示 + Agent 搜索 |
| 来源内容预览 | 先只展示标题和元信息 |
| 来源拖拽排序 | 按时间排序足够 |
| 资源版本对比 | 先做覆盖式全量同步 |
| 连接器模板/克隆 | 无需求支撑 |
| Notion 写回 | 只读访问，不直接写入 |
| 多平台同时连接 | 本期只做 Notion |

---

## 附录 A：API 端点汇总

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/connectors` | GET | 获取用户的连接器列表 |
| `/api/connectors` | POST | 创建资源连接器 |
| `/api/connectors/:id` | GET | 获取连接器详情 |
| `/api/connectors/:id` | PATCH | 更新连接器名称/配置 |
| `/api/connectors/:id` | DELETE | 删除连接器 |
| `/api/connectors/:id/auth/login` | POST | 启动平台认证 |
| `/api/connectors/:id/auth/poll` | POST | 轮询认证状态 |
| `/api/connectors/:id/databases` | GET | 获取可访问的 Database 列表 |
| `/api/connectors/:id/pages` | GET | 获取可访问的 Standalone Page 列表 |
| `/api/connectors/:id/resources` | GET | 获取已连接的资源列表 |
| `/api/connectors/:id/resources/select` | POST | 选择要同步的资源 |
| `/api/connectors/:id/resources/:rid` | DELETE | 移除某个资源 |
| `/api/connectors/:id/sync` | POST | 触发数据同步 |
| `/api/connectors/:id/files/upload` | POST | 上传文件 |
| `/api/connectors/:id/threads` | GET | 获取连接器下的对话列表 |

---

## 附录 B：设计决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 连接器与对话关系 | 内嵌 / 中间表 | 中间表 `connector_chat_threads` | 复用现有 `chat_thread` 模型，不侵入原有表结构 |
| 资源存储 | 平铺在连接器表 / 独立资源表 | 独立 `connector_resources` 表 | 支持多种资源类型，各类型可独立 CRUD |
| 页面索引 | JSON 字段 / 独立表 | 独立 `connector_resource_pages` 表 | Database 下可能有数百个 Row Page，JSON 字段查询性能差 |
| 文件上传 | 连接器内 / 全局文件系统 | 连接器内 + 关联全局文件系统 | 文件生命周期跟随连接器 |
| 前端 Tab 设计 | 单页 / Tab 切换 | "聊天" + "来源" 双 Tab | 参考 ChatGPT Projects，用户无需离开页面即可管理资源 |
