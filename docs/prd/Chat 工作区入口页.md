
# 1. Chat Dashboard 默认空状态结构草图

> [Sync] 2026-07-08: 资源连接器 Tab 只承载轻量摘要、空态、列表和跳转入口；点击「选择连接器」或连接器卡片进入 Settings「资源链接」，再由 Settings 内 `ConnectorNotionDetailPage` 完成 Notion 单账号认证、统一资源列表搜索 / 分页 / 保存和已挂载来源展示。

对应图片 1：默认没有聊天内容时的首屏。

```txt
┌──────────────────────────────────────────────────────────────────────────────┐
│ App Header                                                                    │
│ ┌──────┐  Chat / 当前模块名称                                      [分享] [更多] │
│ │Icon  │  Chat Dashboard                                                     │
│ └──────┘                                                                      │
└──────────────────────────────────────────────────────────────────────────────┘


                    ┌──────────────────────────────────────────────┐
                    │ Input Dock                                    │
                    │ ┌───┐  输入框 / 创建新会话提示                 │
                    │ │ + │  例如：Ask anything...                  │
                    │ └───┘                              [附件] [模型] [头像] │
                    └──────────────────────────────────────────────┘


                    ┌──────────────┐ ┌──────────────┐
                    │ 聊天历史      │ │ 资源连接器    │
                    └──────────────┘ └──────────────┘


                    ┌──────────────────────────────────────────────┐
                    │                                              │
                    │                                              │
                    │                    Empty Chat State           │
                    │                    ┌────────┐                │
                    │                    │ 图标   │                │
                    │                    └────────┘                │
                    │                    标题文案                  │
                    │                    描述文案                  │
                    │                                              │
                    │                                              │
                    └──────────────────────────────────────────────┘
```

---

# 2. 页面模块拆解

```txt
ChatDashboardPage
├── ChatTopHeader
│   ├── ModuleIcon
│   ├── ModuleTitle
│   ├── ModuleDescription
│   ├── ShareButton
│   └── MoreButton
│
├── ChatInputDock
│   ├── AddButton
│   ├── TextInput
│   ├── AttachmentEntry
│   ├── ModelOrToolEntry
│   └── UserAvatar / SubmitEntry
│
├── WorkspaceTabBar
│   ├── HistoryTab
│   └── ResourceConnectorTab
│
└── MainContentArea
    └── EmptyChatState
        ├── EmptyIcon
        ├── EmptyTitle
        └── EmptyDescription
```

---

# 3. 图片 1 的功能含义

```txt
页面状态：Chat 默认无内容状态

用户可以做的事：
1. 从中间 Input Dock 创建新会话
2. 点击 + 添加附件或资源
3. 通过下方 Tab 切换：
   - 聊天历史
   - 资源连接器
4. 通过右上角分享 / 更多进入辅助操作
```

这里的主视觉重心是 **输入框**。
空状态卡片只是承接“当前还没有对话内容”，不要抢输入框的权重。

---

# 4. 切换到资源连接器后的空状态结构草图

对应图片 2：资源连接器 Tab 下，没有任何资源链接时的状态。

```txt
┌──────────────────────────────────────────────────────────────────────────────┐
│ App Header                                                                    │
│ ┌──────┐  Chat / 当前模块名称                                      [分享] [更多] │
│ │Icon  │  Chat Dashboard                                                     │
│ └──────┘                                                                      │
└──────────────────────────────────────────────────────────────────────────────┘


                    ┌──────────────────────────────────────────────┐
                    │ Input Dock                                    │
                    │ ┌───┐  输入框                                  │
                    │ │ + │  仍然允许创建新对话                       │
                    │ └───┘                         [附件] [工具] [头像] │
                    └──────────────────────────────────────────────┘


                    ┌──────────────┐ ┌──────────────┐      ┌────────┐ ┌────────┐
                    │ 聊天历史      │ │ 资源连接器    │      │ 筛选 ▾ │ │ 排序 ▾ │
                    └──────────────┘ └──────────────┘      └────────┘ └────────┘


                    ┌ - - - - - - - - - - - - - - - - - - - - - - ┐
                    │                                             │
                    │                                             │
                    │                 Resource Empty State         │
                    │                                             │
                    │                ┌────┐ ┌────┐ ┌────┐         │
                    │                │远程│ │本地│ │更多│         │
                    │                └────┘ └────┘ └────┘         │
                    │                                             │
                    │                标题：暂无资源连接器           │
                    │                描述：连接 Notion / 飞书 / CLI │
                    │                     后可在对话中使用资源       │
                    │                                             │
                    │                [前往设置 / 选择连接器]         │
                    │                                             │
                    │                                             │
                    └ - - - - - - - - - - - - - - - - - - - - - - ┘
```

---

# 5. 资源连接器 Tab 页面模块拆解

```txt
ChatConnectorTabView
├── ChatTopHeader
│   ├── ModuleIcon
│   ├── ModuleTitle
│   ├── ModuleDescription
│   ├── ShareButton
│   └── MoreButton
│
├── ChatInputDock
│   ├── AddButton
│   ├── TextInput
│   ├── AttachmentEntry
│   ├── ToolEntry
│   └── UserAvatar
│
├── WorkspaceTabBar
│   ├── HistoryTab
│   └── ResourceConnectorTab(active)
│
├── ConnectorToolbar
│   ├── FilterDropdown
│   └── SortDropdown
│
└── ConnectorContentArea
    └── EmptyConnectorState
        ├── ConnectorTypeIcons
        │   ├── RemoteResourceIcon
        │   ├── LocalResourceIcon
        │   └── AddConnectorIcon
        ├── EmptyTitle
        ├── EmptyDescription
        └── GoToConnectorSettingsButton
```

---

# 6. 核心交互规则

## 默认 Chat 状态

```txt
进入 Chat Dashboard
→ 显示 Chat 模块头部
→ 显示中间 Input Dock
→ 下方默认选中「聊天历史」
→ 主内容区展示空聊天状态
```

## 有对话内容时

```txt
用户发送第一条消息
→ 主内容区从 EmptyChatState 切换为 ChatMessageList
→ 中间输入框视觉权重降低
→ 对话内容区域放大
→ Input Dock 固定在底部或保持主输入位置
```

## 切换到资源连接器

```txt
点击「资源连接器」Tab
→ 主内容区切换为 ConnectorContentArea
→ 如果没有任何资源连接
   → 显示虚线边框空状态
   → 展示远程资源 / 本地资源 / 添加资源图标
   → 展示「前往设置 / 选择连接器」按钮
→ 如果已有资源连接
   → 展示资源列表
   → 点击连接器卡片进入 Settings「资源链接」
   → 不在 Chat 内展示 Notion 认证、资源范围、已挂载来源或关闭连接操作
```

## 进入 Notion 具体配置

```txt
点击「选择连接器」或连接器卡片
→ App 视图切换到 Settings
→ 聚焦「资源链接」区
→ 用户点击 Notion「管理」
→ 进入 ConnectorNotionDetailPage
→ 保留 Notion 认证流程
→ 资源范围使用统一 data_source / page 列表
→ 搜索框与「保存资源」同在操作行
→ 默认每页 10 条，支持上一页 / 下一页
→ 保存后「已挂载来源」立即显示所选来源
```

---

# 7. 资源连接器空状态文案建议

```txt
标题：
暂无资源连接器

描述：
连接 Notion、飞书或本地 CLI 执行器后，你可以在对话中直接调用这些资源。

主按钮：
选择连接器

次级说明：
远程资源用于读取外部知识库，本地资源用于连接当前系统 CLI 执行器。
```

---

# 8. 页面状态枚举

```txt
ChatDashboardState
├── empty_chat
│   └── 默认无对话内容
│
├── active_chat
│   └── 有消息内容，聊天区放大
│
├── connector_empty
│   └── 切到资源连接器，但没有任何资源
│
├── connector_connected
│   └── 已有 Notion / 飞书 / CLI 等资源
│
└── connector_error
    └── 资源认证失效、同步失败、连接不可用
```
