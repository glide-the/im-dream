# 资源连接器 — 前端 PRD

Status: Draft  
Updated: 2026-07-08
Scope: 产品设计 — 资源连接器前端功能定义、页面交互设计

> [Input] `docs/design/notion-session/connector-interaction.md`,
>      `docs/design/notion-session/overview.md`,
>      `docs/design/claude-agent/notion-point/resource-connector-layer-design.md`
> [Output] 资源连接器前端 PRD：功能定义、页面交互设计、交互流程、状态定义
> [Pos] resource-connector-prd in `docs/prd/notion-session`
> [Sync] 2026-07-04: 从 `docs/design/notion-session/resource-connector-prd.md` 拆分，前端 PRD 独立管理
> [Sync] 2026-07-07: Chat 入口页成为主落点，历史对话与连接器工作台下沉到输入框下方，嵌入式 `ResourceConnectorPage` 负责连接器管理。
> [Sync] 2026-07-08: Connector 入口迁移到 Settings 的资源链接区，Chat 仅保留轻量摘要面板与跳转 CTA。
> [Sync] 2026-07-08: 修复设置页「管理」交互——不再原地展开，改为导航到独立的 `ConnectorNotionDetailPage`（面包屑：设置 › 资源链接 › Notion 具体配置页面）；顶部导航栏与移动端底部导航栏移除单独的 `Connector` 入口，比对《链接器概念的交互设计稿》骨架屏核实 Chat 入口页布局（图标/描述/分享/更多、聊天文本框、历史与连接器切换栏）与现状一致。

---

## 目录

1. [产品定位](#1-产品定位)
2. [功能定义](#2-功能定义)
3. [页面结构设计](#3-页面结构设计)
4. [交互流程设计](#4-交互流程设计)
5. [状态定义](#5-状态定义)
6. [不实现清单](#6-不实现清单)
7. [API 端点汇总](#7-api-端点汇总)

---

## 1. 产品定位

### 1.1 是什么

**资源连接器**（Resource Connector）是 Settings 中的资源链接管理入口。用户从顶部或移动端导航进入 Settings（Settings 页面本身仍在顶部导航栏和移动端底部导航栏），再到资源链接区管理 Notion / 飞书 / 本地 CLI 执行器等外部资源；Chat 页面只保留一个轻量摘要面板和跳转 CTA，不再承载完整管理流程。

> 当前重构只落地 Notion 资源连接器的 Settings 管理页与 Chat 轻量入口；上传工作空间文件、Deck 关联等扩展能力保留为后续迭代，不作为本轮前端实现范围。

### 1.2 核心价值

- 为 Agent 提供外部平台的结构化背景信息（类似 ChatGPT Projects 的"来源"功能）
- 用户无需反复描述上下文，连接器自动将平台数据同步为 Agent 可读的 `.notion/` 映射

### 1.3 类比理解

| 类比对象 | 对应关系 |
|---------|---------|
| ChatGPT Projects "聊天" Tab | Chat 入口页的输入框 + 历史对话面板 + 轻量 connector 摘要 |
| Slack / Google Drive 连接 | Notion 资源连接器 |
| ChatGPT Projects "来源" Tab | Settings 中的资源链接管理页 |
| 上传数据源 / 链接云端硬盘 | Settings 里的多资源挂载 |

---

## 2. 功能定义

### 2.1 核心功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 创建资源连接器 | 用户在工作空间中创建一个命名的连接器空间 | P0 |
| 连接外部平台 | 选择平台（Notion）→ 完成 OAuth 认证 | P0 |
| 选择资源 | 用户勾选可访问的 Database 及 Standalone Page | P0 |
| 发起对话 | 在 Chat 入口页发起对话，Agent 自动感知已连接资源 | P0 |
| 查看来源 | 查看已连接的所有资源列表及同步状态 | P0 |
| 上传工作空间文件 | 上传本地文件作为补充背景 | 后续迭代 |
| 选择 Decks | 关联已有的 Deck 知识卡片集 | 后续迭代 |
| 刷新同步 | 手动触发资源重新同步 | P1 |

### 2.2 连接器空间内的子功能

```
资源链接区（Settings）
  ├── 远程资源链接
  │     ├── Notion 管理入口（点击「管理」页面级导航到具体配置页面）
  │     └── 飞书占位
  ├── 本地资源链接
  │     └── CLI 执行器占位
  └── Notion 具体配置页面（ConnectorNotionDetailPage，独立导航页）
        └── ResourceConnectorPage（page mode）
```

---

## 3. 页面结构设计

### 3.1 主页面布局

参考 Settings 资源链接区 + Chat 轻量摘要面板的双层布局：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Settings view（资源链接索引）                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 资源链接区（远程资源 / 本地资源）                        │    │
│  │   Notion（管理 → 跳转下方独立页面）· 飞书 · CLI 执行器占位│    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │ 点击「管理」= 页面级导航（替换整个视图）
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           Settings view（ConnectorNotionDetailPage）             │
│                                                                 │
│  设置 › 资源链接 › Notion 具体配置页面   ← 面包屑导航             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Notion 具体管理页（ResourceConnectorPage page mode）    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> 「管理」触发的是 App 级页面导航（`showNotionConnectorDetail=true`），不是在资源链接卡片内原地展开；`ConnectorNotionDetailPage` 会替换掉 Settings 里 Energy Bar / AI 模型配置等其它分区，只保留面包屑 + Notion 管理页本身。

### 3.2 页面组件拆解

| 区域 | 组件 | 说明 |
|------|------|------|
| 资源链接入口 | ConnectorSettingsSection | 承载远程 / 本地资源索引卡片，「管理」触发 `onOpenNotionDetail` 页面导航 |
| Notion 具体配置页面 | ConnectorNotionDetailPage | 面包屑导航 + 复用 `ResourceConnectorPage` page mode，替换整个 Settings 视图 |
| 轻量摘要面板 | ConnectorLandingPanel | Chat 中的 Connector 摘要 + Settings CTA；不做创建 / 认证 / 资源选择 |
| Notion 管理页内容 | ResourceConnectorPage | 复用现有 page mode 继续做创建 / 认证 / 来源管理 |
| 入口跳转 | ConnectorLandingPanel（Chat） | 跳转按钮打开 Settings 资源链接区并自动聚焦；顶部导航栏与移动端底部导航栏不再单独展示 `Connector` 入口 |

> `ResourceConnectorPage` 作为 Notion 的 page mode 管理页保留；Chat 入口仅保留摘要和 CTA，不再直接承载完整工作台。

### 3.3 资源链接首页（Settings）

> 本节后续的空状态、Tab 与来源列表布局内容保留旧版嵌入式方案的归档，现行实现以 `ConnectorSettingsSection` / `ConnectorLandingPanel` / `ResourceConnectorPage` page mode 为准。

#### 空状态（无连接器或无来源时）

居中虚线框区域，显示：
- 平台图标行：Notion 图标 / Google Drive 图标 / 附件图标
- 主文案："为 Agent 提供更多背景信息"
- 副文案："上传数据源、链接云端平台或连接 Notion 等应用，为 Agent 提供项目的更深层次背景信息。"
- CTA 按钮：「添加来源」

#### 有来源时

```
┌─────────────────────────────────────────────────────────────┐
│ [ 历史对话 ]  [ 连接器 ]              [最新 ▾] [全部 ▾]      │
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

> 下列 Tab 设计保留为旧嵌入式方案的历史归档，不作为本次 Settings-managed 入口的主实现路径。

### 3.4 "历史对话" Tab 设计（归档）

```
┌─────────────────────────────────────────────────────────────┐
│ [ 历史对话 ]  [ 连接器 ]              [最新 ▾] [全部 ▾]      │
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
> 归档说明：现行实现不再将连接器工作台挂在 Chat 下方；Chat 只保留轻量摘要面板。

---

## 4. 交互流程设计

### 4.1 创建资源连接器

```
用户在 Chat 页面切换到 "连接器" Tab
    │
    ├─ 点击 "新建连接器"
    │
    ├─ 弹出 Modal: 输入连接器名称
    │     └─ 确认 → POST /api/connectors {name, platform:"notion"}
    │
    └─ 创建成功 → 跳转连接器主页面（空状态）
```

### 4.2 添加来源（连接 Notion）

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
    └─ 后端同步 → 连接器面板显示新资源卡片
```

### 4.3 发起对话

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

### 4.4 关联 Deck

```
用户点击 "添加来源" → "关联 Deck"
    │
    ├─ Deck 选择列表（用户已有 Decks）
    ├─ POST /api/connectors/:id/resources/select {type:"deck", deck_id}
    ├─ 创建 connector_resources (type="deck")
    │
    └─ 连接器面板显示关联的 Deck 卡片
```

---

## 5. 状态定义

### 5.1 连接器状态

| 状态 | 说明 | 前端展示 |
|------|------|---------|
| `draft` | 已创建，未开始配置 | 空状态 CTA（“新建连接器/连接 Notion”） |
| `pending` | 已创建或已发起认证，未完成会话认证 | 显示"待认证"标签 + 验证码 |
| `authenticating` | 认证进行中（浏览器未确认或轮询进行） | 显示 verification code + `打开浏览器确认` |
| `authenticated` | 认证成功，尚未完成 sync | 显示“已认证”并进入资源选择 |
| `synced` | 认证成功并完成资源同步 | 正常展示来源 |
| `expired` | Token 过期 | 显示"需重新认证"提示 |
| `stale` | 当前快照不新鲜（有更新可用） | 显示快照版本与 `立即刷新` |
| `error` | 认证 / 同步发生报错 | 显示错误 banner + 重试按钮 |
| `connector_unavailable` | 连接器后端服务不可用 | 显示全局降级提示 + 重试入口 |

### 5.2 资源同步状态

| 状态 | 说明 | 前端展示 |
|------|------|---------|
| `pending` | 已选资源，等待 Sync 开始 | 资源卡片显示 `待同步` |
| `syncing` | 正在同步中 | 资源卡片显示 loading |
| `synced` | 同步完成 | 显示"已同步" + 页面数 |
| `stale` | 资源页已过期 | 显示 `请刷新` |
| `error` | 同步失败 | 显示错误提示 + 重试按钮 |
| `missing` | 当前快照未包含该条资源（未 materialized） | 显示 `暂不可用` + `重新刷新` |

### 5.3 来源类型图标映射

| resource_type | 图标 | 显示格式 |
|--------------|------|---------|
| `notion_database` | 🔗 | "Notion · {title} [{page_count} 页]" |
| `notion_page` | 📝 | "Notion · {title}" |
| `file` | 📄 | "{filename} [{size}]" |
| `deck` | 📦 | "Deck · {title} [{card_count} cards]" |

---

## 6. 不实现清单

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

## 7. API 端点汇总

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

## 附录：设计决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 前端入口设计 | Settings / 轻量摘要 | Settings 资源链接区 + Chat 轻量摘要面板 | 入口与管理分离，避免 Chat 承担完整工作台 |
| 文件上传 | 连接器内 / 全局文件系统 | 连接器内 + 关联全局文件系统 | 文件生命周期跟随连接器 |

---

## 相关文档

- ER 关系模型设计：[`docs/design/notion-session/resource-connector-er.md`](../../design/notion-session/resource-connector-er.md)
- 交互方案设计：[`docs/design/notion-session/connector-interaction.md`](../../design/notion-session/connector-interaction.md)
- 总览设计：[`docs/design/notion-session/overview.md`](../../design/notion-session/overview.md)
