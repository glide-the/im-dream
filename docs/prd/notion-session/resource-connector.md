# 资源连接器 — 前端 PRD

Status: Draft  
Updated: 2026-07-08
Scope: 产品设计 — 资源连接器前端功能定义、页面交互设计

> [Input] `docs/prd/Chat 工作区入口页.md`,
>      `docs/prd/notion-session/连接器具体配置页面结构草图.md`,
>      `docs/design/notion-session/connector-interaction.md`,
>      `docs/design/notion-session/overview.md`,
>      `docs/design/claude-agent/notion-point/resource-connector-layer-design.md`
> [Output] 资源连接器前端 PRD：功能定义、页面交互设计、交互流程、状态定义
> [Pos] resource-connector-prd in `docs/prd/notion-session`
> [Sync] 2026-07-04: 从 `docs/design/notion-session/resource-connector-prd.md` 拆分，前端 PRD 独立管理
> [Sync] 2026-07-07: Chat 入口页成为主落点，历史对话与连接器工作台下沉到输入框下方，嵌入式资源视图负责连接器管理。
> [Sync] 2026-07-08: 入口描述曾短暂偏离 Chat 主工作区，本稿已回收为 Chat `WorkspaceTabBar` 主入口，并撤销仅摘要化的连接器路径表述。
> [Sync] 2026-07-08: Notion 详情页统一采用 `ConnectorConfigPage` 结构与 `资源连接器 > Notion Connector` 面包屑；详情层级、状态词汇、骨架屏说明与两份最新草图重新对齐。

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

**资源连接器**（Resource Connector）是 Chat 工作区中的一级工作台视图。用户进入 Chat Dashboard 后，先看到居中的 `ChatInputDock`，其下方通过 `WorkspaceTabBar` 在 `聊天历史` 与 `资源连接器` 之间切换；点击某个连接器后，再进入该连接器的独立详情页 `ConnectorConfigPage` 完成认证、来源选择与同步管理。

> 本期只落地 Notion Connector 的完整详情页；飞书与本地 CLI 执行器仍保留为入口级占位，不展开完整配置流。

### 1.2 核心价值

- 在 **不离开 Chat 工作区心智** 的前提下完成资源连接、认证与来源选择。
- 让用户先在 Chat 内感知“可供对话使用的资源”，再按需下钻到 `ConnectorConfigPage` 进行细配置。
- 为 Agent 提供结构化外部背景信息，并将其同步为统一的 `.notion/` canonical snapshot 读取入口。

### 1.3 类比理解

| 类比对象 | 对应关系 |
|---------|---------|
| ChatGPT Projects 聊天主页面 | `ChatInputDock` + `WorkspaceTabBar` + `MainContentArea` |
| ChatGPT Projects 来源入口 | Chat 内 `ResourceConnectorTabPanel` |
| Slack / Google Drive 连接器详情 | `ConnectorConfigPage` |
| 数据源选择 / 索引配置 | `ResourceSourceSection` |

---

## 2. 功能定义

### 2.1 核心功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 连接器主入口 | 用户在 Chat 页面通过 `WorkspaceTabBar` 进入 `资源连接器` 视图 | P0 |
| 连接外部平台 | 在 Notion Connector 详情页发起 OAuth / CLI 认证 | P0 |
| 选择资源 | 用户勾选可访问的 Database 与 Standalone Page | P0 |
| 查看来源状态 | 在 Chat 的连接器 Tab 查看当前连接器列表、筛选、排序与异常态 | P0 |
| 发起对话 | 在 Chat 中继续提问，Agent 自动感知已连接资源 | P0 |
| 刷新同步 | 在详情页或后续卡片操作中触发同步 | P1 |
| 上传工作空间文件 | 后续迭代，不在本轮详情页实现 | 后续迭代 |
| 选择 Decks | 后续迭代，不在本轮详情页实现 | 后续迭代 |

### 2.2 组件与页面范围

```txt
ChatDashboardPage
  ├── ChatTopHeader
  ├── ChatInputDock
  ├── WorkspaceTabBar
  │     ├── HistoryTab
  │     └── ResourceConnectorTab
  └── MainContentArea
        ├── HistoryTabPanel
        └── ResourceConnectorTabPanel
              ├── ConnectorToolbar
              ├── ConnectorEmptyState / ConnectorList
              └── ConnectorCard → ConnectorConfigPage

ConnectorConfigPage
  ├── TopNavigation
  ├── ConnectorHeader
  ├── ConnectorOverviewSection
  ├── StrategySection（[暂不实现] 占位）
  ├── ResourceSourceSection
  └── ConnectionStateCard
```

---

## 3. 页面结构设计

### 3.1 Chat 主入口布局

`资源连接器` 的主入口直接位于 Chat 页面，而不是独立设置页。

```txt
┌──────────────────────────────────────────────────────────────────────────────┐
│ ChatTopHeader                                                                │
│ [Icon] Chat Dashboard                                           [分享] [更多] │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                    ┌──────────────────────────────────────┐                  │
│                    │ ChatInputDock                        │                  │
│                    │ [+] Ask anything...        [附件][模型][头像] │                  │
│                    └──────────────────────────────────────┘                  │
│                                                                              │
│                    ┌──────────────┐ ┌──────────────┐                         │
│                    │ 聊天历史      │ │ 资源连接器    │                         │
│                    └──────────────┘ └──────────────┘                         │
│                                                                              │
│                    MainContentArea                                           │
│                    ├─ HistoryTabPanel（默认）                                │
│                    └─ ResourceConnectorTabPanel（切换后）                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Chat 内 `ResourceConnectorTabPanel`

当用户切换到 `资源连接器` Tab：

```txt
ResourceConnectorTabPanel
├── ConnectorToolbar
│   ├── FilterDropdown
│   └── SortDropdown
├── ConnectorContentArea
│   ├── ConnectorEmptyState
│   │   ├── ConnectorTypeIcons（远程资源 / 本地资源 / 更多）
│   │   ├── EmptyTitle：暂无资源连接器
│   │   ├── EmptyDescription：连接 Notion / 飞书 / CLI 后可在对话中使用资源
│   │   └── SelectConnectorButton
│   └── ConnectorList
│       └── ConnectorCard（名称 / 简介 / 状态 / 最近同步）
└── ConnectorCard click
    └── Navigate → ConnectorConfigPage
```

> `ConnectorToolbar` 即使在空状态下也保留位置；加载时显示骨架占位，空态时显示真实筛选 / 排序控件。

### 3.3 `ConnectorConfigPage` 详情页

点击某个连接器卡片后进入独立详情页：

```txt
┌────────────────────────────────────────────────────────────────────┐
│ ← 资源连接器 > Notion Connector                                     │
├────────────────────────────────────────────────────────────────────┤
│ ConnectorHeader                                                    │
│ [连接器图标] Notion Resource Connector                  [查看链接器设计稿] [关闭连接] │
│            Notion 远程资源连接器说明                                │
│            [未认证 / 认证中 / 已连接 / 同步中 / 同步失败 / 已关闭]    │
├────────────────────────────────────────────────────────────────────┤
│ ConnectorOverviewSection                                           │
│  图标 / 描述 / 状态 / 设计稿 / 连接控制                             │
├────────────────────────────────────────────────────────────────────┤
│ StrategySection [暂不实现]                                          │
│  当前版本暂不开放策略配置                                            │
├────────────────────────────────────────────────────────────────────┤
│ ResourceSourceSection                                              │
│  资源选择 / 来源列表                                       [+ 添加] │
│  ├─ 未认证：禁用态 + 虚线空说明                                      │
│  └─ 已认证：数据库 → 页面树（可展开 / 选择）                         │
├────────────────────────────────────────────────────────────────────┤
│ ConnectionStateCard                                                │
│  ⚠ 授权 / 同步状态                                         [开关]   │
└────────────────────────────────────────────────────────────────────┘
```

### 3.4 组件表

| 区域 | 组件 | 说明 |
|------|------|------|
| Chat 主切换条 | `WorkspaceTabBar` | Chat 级唯一主切换，固定只有 `HistoryTab` / `ResourceConnectorTab` 两项 |
| Chat 历史内容 | `HistoryTabPanel` | 默认承载空聊天态、历史列表、会话切换后的消息流 |
| Chat 连接器内容 | `ResourceConnectorTabPanel` | 承载筛选排序、空态、连接器列表与错误提示 |
| 连接器详情页 | `ConnectorConfigPage` | 点击连接器后进入的独立配置页 |
| 顶部导航 | `TopNavigation` | 固定使用 `← 资源连接器 > Notion Connector` |
| 连接器头部 | `ConnectorHeader` | 图标 / 名称 / 描述 / 状态 badge / 设计稿按钮 / 关闭连接 |
| 连接器概览 | `ConnectorOverviewSection` | 行级概览卡，展示状态、设计稿链接和关闭动作 |
| 策略占位 | `StrategySection` | 明确标注 `[暂不实现]` |
| 来源列表 | `ResourceSourceSection` | 未认证时禁用说明；已认证时展示 database → page 展开树 |
| 底部状态卡 | `ConnectionStateCard` | 解释“为什么当前页面受限”并提供开关 |

---

## 4. 交互流程设计

### 4.1 进入资源连接器

```txt
用户进入 Chat Dashboard
    │
    ├─ 默认选中 HistoryTab
    │   └─ MainContentArea 显示 EmptyChatState 或历史 / 当前会话
    │
    └─ 点击 ResourceConnectorTab
        ├─ 先显示 ConnectorToolbar
        ├─ 无连接器 → ConnectorEmptyState
        └─ 有连接器 → ConnectorList
```

### 4.2 创建 / 进入 Notion Connector

```txt
用户位于 ResourceConnectorTabPanel
    │
    ├─ 点击「选择连接器」
    │   └─ 打开连接器选择入口（本期重点为 Notion）
    │
    ├─ 点击 Notion Connector 卡片
    │   └─ 页面级导航到 ConnectorConfigPage
    │
    └─ ConnectorConfigPage 顶部显示：← 资源连接器 > Notion Connector
```

### 4.3 认证与资源选择

```txt
用户进入 ConnectorConfigPage
    │
    ├─ 未认证
    │   ├─ ConnectorHeader / ConnectorOverviewSection 可查看
    │   ├─ ResourceSourceSection 禁用并显示「请先完成 Notion 授权」
    │   └─ ConnectionStateCard 解释当前限制原因
    │
    ├─ 点击认证入口
    │   ├─ POST /api/connectors/:id/auth/login
    │   ├─ 展示验证码 / 打开浏览器确认
    │   └─ POST /api/connectors/:id/auth/poll
    │
    └─ 已认证
        ├─ 展示 database 列表
        ├─ 点击数据库 → 展开 page tree
        ├─ 勾选页面 / 数据库
        └─ POST /api/connectors/:id/resources/select → POST /api/connectors/:id/sync
```

### 4.4 关闭连接

```txt
用户点击 ConnectorHeader / ConnectorOverviewSection 中的「关闭连接」
    │
    ├─ 弹出二次确认
    │   ├─ 说明关闭后将停止对话中调用该连接器
    │   └─ 说明已选来源保留但不可继续同步
    │
    ├─ 确认关闭
    │   ├─ 状态改为「已关闭」
    │   ├─ ResourceSourceSection 改为禁用态
    │   └─ ConnectionStateCard 显示关闭原因与恢复入口
    │
    └─ 取消关闭 → 保持原状态
```

### 4.5 发起对话

```txt
用户回到 ChatInputDock 输入消息
    │
    ├─ 前端创建 / 继续 chat_thread
    ├─ Agent attach 当前 connector 的 canonical snapshot
    └─ 对话可读取 `.notion/` 内对应资源
```

---

## 5. 状态定义

### 5.1 Chat 工作区状态

| 状态 | 说明 | 前端展示 |
|------|------|---------|
| `empty_chat` | 默认历史视图且没有任何对话内容 | `HistoryTabPanel` 显示空聊天态；输入框保持主视觉 |
| `active_chat` | 已有当前会话消息 | `ChatMessageList` 放大，输入区保留在底部 |
| `connector_empty` | 切到 `ResourceConnectorTab` 且无连接器 | 虚线边框空态 + 远程资源 / 本地资源 / 更多图标 + CTA |
| `connector_connected` | 至少已有一个连接器 | 列表卡片 + 筛选 / 排序工具栏 |
| `connector_error` | 连接器读取失败或状态异常 | 在 `ResourceConnectorTabPanel` 内显示错误卡和重试入口 |

### 5.2 连接器详情状态词汇

| 状态词 | 触发条件 | 详情页表现 |
|--------|----------|------------|
| `未认证` | 尚未完成认证 | `ResourceSourceSection` 禁用；`ConnectionStateCard` 解释需先授权 |
| `认证中` | 已发起认证，等待用户确认或轮询 | 显示验证码、浏览器确认提示与轮询反馈 |
| `已连接` | 认证成功且可读取当前连接器配置 | `ConnectorHeader` / `ConnectorOverviewSection` 显示正常态 |
| `同步中` | 已选择资源并触发同步 | 状态 badge 与资源列表行显示 loading |
| `同步失败` | 同步任务失败 | 保留已有资源展示并提供重试 |
| `已关闭` | 用户确认关闭连接 | 保留历史资源记录但禁用操作，提示不可在对话中调用 |

### 5.3 资源同步状态

| 状态 | 说明 | 前端展示 |
|------|------|---------|
| `pending` | 已选择资源，等待 sync 开始 | 列表行显示 `待同步` |
| `syncing` | 正在同步中 | skeleton / spinner + 状态文案 |
| `synced` | 同步完成 | 显示最近同步时间、页面数 |
| `stale` | 当前快照过旧 | 提示 `刷新同步` |
| `error` | 同步失败 | 显示错误提示 + 重试按钮 |
| `missing` | 当前 snapshot 未包含该资源 | 显示 `暂不可用` + 重新同步入口 |

---

## 6. 不实现清单

防止过度设计，以下内容**明确排除**：

| 排除项 | 原因 |
|--------|------|
| 多人协作同一连接器 | 连接器绑定单用户，后续再扩展 |
| 连接器间数据共享 | 每个连接器独立，不做跨连接器引用 |
| 来源内容预览 | 本轮只做标题、状态、层级选择 |
| 来源拖拽排序 | 先做筛选 / 排序即可 |
| 资源版本对比 | 先做覆盖式同步 |
| 连接器模板 / 克隆 | 无需求支撑 |
| Notion 写回 | 本期只读 |
| 多平台完整详情页 | 本期只做 Notion |

---

## 7. API 端点汇总

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/connectors` | GET | 获取用户的连接器列表 |
| `/api/connectors` | POST | 创建资源连接器 |
| `/api/connectors/:id` | GET | 获取连接器详情 |
| `/api/connectors/:id` | PATCH | 更新连接器名称 / 配置 |
| `/api/connectors/:id` | DELETE | 删除或关闭连接器 |
| `/api/connectors/:id/auth/login` | POST | 启动平台认证 |
| `/api/connectors/:id/auth/poll` | POST | 轮询认证状态 |
| `/api/connectors/:id/databases` | GET | 获取可访问的 Database 列表 |
| `/api/connectors/:id/pages` | GET | 获取可访问的 Standalone Page 列表 |
| `/api/connectors/:id/resources` | GET | 获取已连接资源列表 |
| `/api/connectors/:id/resources/select` | POST | 选择要同步的资源 |
| `/api/connectors/:id/resources/:rid` | DELETE | 移除某个资源 |
| `/api/connectors/:id/sync` | POST | 触发同步 |
| `/api/connectors/:id/threads` | GET | 获取连接器关联的对话列表 |

---

## 附录：设计决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 主入口位置 | Chat / 独立设置页 | Chat `WorkspaceTabBar` | 让资源选择保持在对话工作区心智内 |
| 详情页导航 | 内嵌展开 / 独立下钻 | `ConnectorConfigPage` | 复杂配置与 Chat 入口解耦 |
| 详情页组件树 | 自定义散装模块 / 草图组件树 | 复用 `TopNavigation`~`ConnectionStateCard` 命名 | 与草图和后续实现保持一一对应 |
| 文件上传 | 连接器内 / 全局文件系统 | 后续迭代再定 | 本轮只聚焦远程资源连接 |

---

## 相关文档

- 交互方案设计：[`docs/design/notion-session/connector-interaction.md`](../../design/notion-session/connector-interaction.md)
- 总览设计：[`docs/design/notion-session/overview.md`](../../design/notion-session/overview.md)
- UI 设计稿：[`docs/prd/notion-session/resource-connector-ui-design.md`](./resource-connector-ui-design.md)
