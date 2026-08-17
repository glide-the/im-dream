<!-- [Input] Deck设计需求.pdf, user Work-settings reference image, and current Settings/Router/DeckManager code. -->
<!-- [Output] Published-clean enabled Deck home plus Settings / Work management interaction contract. -->
<!-- [Pos] Deck home and Work-management functional-unit design. -->
<!-- [Sync] 2026-08-17: restrict both home projections to published-clean enabled Decks,
                         identify system Decks, and keep full inventory in Settings / Work. -->
<!-- [Sync] 2026-08-17: make the Settings/Work shell locale-specific; never combine Chinese and English labels. -->
<!-- [Sync] 2026-08-17: split launcher list into user Available Decks and static System Decks. -->

# Deck 启用入口与 Work 设置工作台

## 1. 现有代码基线

本稿以当前生产代码为约束，不另造第二套 Settings 或 Deck 状态：

- `StoryWorkspaceSettingsPage.tsx` 已拥有 248px Settings 左栏、搜索、桌面/窄屏投影与内容区。
- `storyWorkspacePath.ts`/`story-workspace.tsx` 是 Story Workspace 路由事实来源。
- `DeckManager.tsx` 已拥有真实 Deck CRUD、创建后打开维护弹窗、草稿修订和显式内容版本提交。
- `ConnectorSettingsSection` 与 `ClaudePluginAdminPage` 是资源链接和插件管理的现有实现。
- `updateDeck(deckId, { enabled })` 是 Deck 启停的生产写入口。

因此本期只拆分展示所有权：Deck 主页面消费“已启用、已发布、无草稿变更”的可用投影；草稿、未发布、
停用 Deck 和完整管理进入 Settings / Work。

## 2. 页面与路由层级

```text
/story-workspace/decks
└─ Deck 主页面
   ├─ published-clean enabled 搜索与 Agent 类型筛选
   ├─ 0–14 个正式可用 Deck 正方形快捷图标（系统内置有盾牌角标）
   ├─ Available Decks：用户自建/可维护 Deck
   ├─ System Decks：注册用户默认系统内建 Deck，只展示不可打开
   └─ 设置按钮 → /story-workspace/settings/work

/story-workspace/settings
└─ 现有 Settings
   ├─ 常规
   ├─ 订阅
   ├─ 工作台（中文）/ Work（英文）→ /story-workspace/settings/work
   ├─ AI 模型
   └─ 关于

/story-workspace/settings/work?tab=deck|resources|plugins
└─ Work 右侧内容区
   ├─ Deck
   ├─ 资源链接
   └─ 插件
```

设置按钮一次点击直接进入 `/story-workspace/settings/work`，默认选中 Work 内部 Deck 页签。Deck、资源链接、
插件不是 Settings 左栏的三个条目，而是 Work 右侧内容区内部页签。旧资源/插件深链接保留兼容，渲染时统一落入 Work。

## 3. Deck 主页面

```text
Decks                                              [↻] [创建⌄]

Decks
打开已启用的 Deck，或前往设置继续管理

[⌕ 搜索已启用的 Deck________________________________________]

已启用                                                [设置]
[D1] [D2] [D3] ... [D14]

[全部 16] [Chat 15] [Dream 1]

Available Decks
─────────────────────────────────────────────────────────────
[D1] 用户 Deck 名称 / 说明 / 内容 vN     [D3] 用户 Deck 名称 / 说明

System Decks
─────────────────────────────────────────────────────────────
[D2·系统] 系统内建 Deck 名称 / 说明 / 内容 vN
```

- 两处使用同一 fail-closed 条件：`enabled=true`、`deck_version_capability=true`、`deck_version>0`、
  `deck_version_dirty=false`、`deck_version_status=published`；任一事实缺失都不进入主页面。
- 快捷图标保持 API 顺序并截取前 14 个；下方列表显示满足条件的完整集合。
- 系统内建 Deck 包括服务端 `is_system=true` 或 sharing policy 标记为 `default_initialized` 的注册默认 Deck。
- 系统内建 Deck 在快捷图标右上显示盾牌角标，在 `System Decks` 分组中显示“系统/System”标签；普通 Deck
  进入 `Available Decks` 分组。
- 系统内建 Deck 只展示，不打开维护弹窗，不提供查看、编辑、启停、删除、同步或创建副本入口。
- 每个快捷项是固定 `44×44px` 正方形按钮，内部图形为完整 `24×24px`；桌面间隔 12px，窄屏间隔 8px并按 Story Workspace 侧栏后的实际内容宽度自动换行。
- 设置按钮位于“已启用”标题右上角，是标题行的兄弟动作，不属于图标 `role=list`，页面不显示 `14 / 14` 数字。
- 设置按钮一次点击直达 `/story-workspace/settings/work`。
- 搜索和 Agent 类型页签仅过滤正式可用的下方列表；列表桌面两列、窄屏一列，点击继续进入原 Deck 维护弹窗。
- 主页面 DOM 不存在启用状态筛选、安装动作或 `role=switch`。
- 原创建逻辑保留；创建成功后按返回 `deck_id` 打开同一维护弹窗。
- 0 个 enabled Deck 时仍显示标题右上角设置按钮和诚实空状态。

## 4. Work 设置工作台：桌面

本轮新参考图用于 Deck 主页面的纵向骨架和空间关系；早一张 Work 参考图仍只用于下面右侧 Work 内容区。
两张图都不改变 Settings 左栏样式，也不引入插件市场业务。

```text
┌─ Settings 左栏 248px ─────┬─ Work 右侧内容区 ─────────────────────────────┐
│ ← {返回应用|Back to app}  │ {工作台|Work}                                 │
│ [搜索设置……]              │ 集中管理可在创作工作区使用的 Deck、资源链接与插件 │
│                            │                                               │
│ 个人                       │ [Deck] [资源链接] [插件]                       │
│   常规                     │ ──────────────────────────────────────────── │
│   订阅                     │ Deck                         [↻] [创建⌄]      │
│ ● {工作台|Work}           │ [⌕ 搜索名称或说明________________________]    │
│   AI 模型                  │                                               │
│   关于                     │ [全部 17] [Chat 16] [Dream 1]   [全部状态⌄] │
│                            │                                               │
│                            │ [图标] Deck 名称                 […]  [开关] │
│                            │        说明                                   │
│                            │        Agent · 内容 vN · 草稿 rN · 日期       │
│                            │ ──────────────────────────────────────────── │
└────────────────────────────┴───────────────────────────────────────────────┘
```

### 4.1 Work 页签

- 所有花括号内的中英文只用于设计稿表达语言映射，生产界面始终按当前 locale 二选一显示，禁止出现
  “工作台 / Work”“Language / 语言”一类拼接标题。
- 中文：左栏与页面标题均为“工作台”，页签为“Deck / 资源链接 / 插件”。
- 英文：左栏与页面标题均为“Work”，页签为“Deck / Resource links / Plugins”。
- Settings 左栏、搜索、通用设置、外观、能量条、模型、关于及页面 ARIA 使用同一 i18n 命名空间，
  切换语言即时重算导航搜索与可访问名称，不改变路由或业务状态。

- `Deck`：完整集合、搜索、Agent 类型筛选、启用状态筛选、分页、创建、编辑、更多动作和启停。
- `资源链接`：复用 `ConnectorSettingsSection`，不复制连接器认证与详情状态。
- `插件`：复用 `ClaudePluginAdminPage`，不复制安装、操作进度和卸载状态。
- 页签写入 URL query，刷新和浏览器前进/后退后仍可恢复当前页签。

### 4.2 Deck 启停与版本

- Deck 启停唯一入口是 Work / Deck 行尾 `role=switch`。
- 成功后重新读取服务端列表；失败保持原状态并显示可恢复错误。
- 系统内建 Deck 在 Work / Deck 中同样只展示，不提供行身份打开、更多菜单、开关或删除入口。
- 点击行身份区仍打开完整 Deck 维护弹窗。
- 弹窗内有效表单变更继续推进聚合草稿 revision；显式提交产生不可变内容 v1/v2/vN。
- 内容版本 vN 是主要事实；运行插件 semver 是次级运行事实。

### 4.3 相关对话与删除闭环

- 用户自有 Deck 的行尾“更多”菜单固定提供“相关对话”，与“编辑/同步/删除”处于同一操作层级。
- 点击后按当前 `deck_id` 调用现有 Chat Thread 列表生产接口，复用 Chat 历史预览的信息结构：对话标题、更新时间、逐条删除。
- 默认加载 20 条，存在更多结果时显式“加载更多”；加载、空、失败、删除中均在弹窗内处理，不污染 Work 列表。
- 有相关对话时“删除 Deck”保持禁用，并说明需先删除全部相关对话；逐条删除沿用 Chat 的永久删除确认与 `DELETE /api/claude-agent/threads/{thread_id}`。
- 对话清空后按钮解锁，再进入原有 Deck 删除确认；取消任一步骤均不写入。
- 后端删除事务必须区分三类依赖：`chat_thread` 返回“相关对话”冲突；真正不可变的 runtime snapshot 继续 fail closed；未被 snapshot 使用的普通插件绑定由 Deck 删除事务清理，不能冒充历史对话永久锁死 Deck。

```text
┌────────────────────────────────────────────────────┐
│ Deck 名称                              [×]          │
│ 相关对话                                             │
├────────────────────────────────────────────────────┤
│ 仍有 Chat 对话使用该 Deck，请先删除不再需要的对话。 │
│                                                    │
│ 💬 雨夜开场讨论                 08/17/2026   [删除] │
│ 💬 第二幕人物关系               08/16/2026   [删除] │
├────────────────────────────────────────────────────┤
│ 删除全部相关对话后才能删除 Deck。 [关闭] [删除 Deck]│
└────────────────────────────────────────────────────┘

空状态：
┌────────────────────────────────────────────────────┐
│ 💬 没有相关对话                                    │
│ Chat 历史已不再阻止删除这个 Deck。                 │
│                              [关闭] [删除 Deck]     │
└────────────────────────────────────────────────────┘
```

## 5. Work 设置工作台：窄屏

```text
Settings 顶部分类横向滚动
[常规|General] [订阅|Subscription] [工作台|Work] [AI 模型|AI models] [关于|About]

{工作台|Work}
说明

Work 内部页签独立横向滚动
[Deck] [资源链接] [插件]

[↻] [创建⌄]
[⌕ 搜索________________]
[全部] [Chat] [Dream]
[全部状态⌄]

[图标] Deck 名称       […] [开关]
```

Settings 分类与 Work 页签是两个独立层级；不合并成一个导航条。页面不得产生 document 级横向
溢出，图标、行尾开关和主要操作的触控高度至少 44px。

## 6. 状态与异常

| 状态 | Deck 主页面 | Work / Deck |
|---|---|---|
| 加载 | 页面 loading | 页签内容 loading |
| 0 个正式可用 Deck | 标题右上设置按钮 + “无已发布且无草稿变更 Deck” | 完整列表仍可管理、提交或启用 |
| 超过 14 个正式可用 Deck | 快捷区稳定显示前 14 个；下方列表显示全部合格项 | 完整列表全部可见 |
| 搜索无结果 | 正式可用列表无结果 + 清除筛选；快捷区保持稳定 | 无结果 + 清除筛选 |
| enabled 但未发布/有草稿 | 主页面两处均不显示 | Work 显示真实版本/草稿状态，可继续维护 |
| 启停中 | 不提供启停 | 仅禁用当前行 |
| 启停失败/冲突 | 保持已有投影 | 保持原开关值并提示刷新/重试 |
| 权限不足 | 错误 + 重试 | 不呈现表面成功 |
| 资源/插件失败 | 不影响 Deck 主页面 | 错误局限于对应 Work 页签 |
| 存在相关 Chat | 不受影响 | “更多 → 相关对话”展示预览；Deck 删除禁用，逐条删除后解锁 |
| 相关对话加载失败 | 不受影响 | 保留弹窗与重试，不把未知结果当作空列表 |
| 对话删除失败 | 不受影响 | 保留该行与原 Deck，显示可恢复错误 |
| 仅存在未使用插件绑定 | 不受影响 | 不伪装成历史对话；Deck 删除事务清理绑定后继续 |
| 存在不可变运行快照 | 不受影响 | 即使无 Chat 仍 fail closed，提示真实运行历史冲突 |

## 7. 对应实现与验收

| 功能 | 代码 | 自动化验收 |
|---|---|---|
| 14 个正式可用正方形 Deck | `DeckLaunchPanel`、`isDeckHomeVisible` | 五项资格条件、44×44、设置不在 list 内 |
| 正式可用搜索与列表 | `DeckLaunchPanel` | 排除未发布/有草稿/停用，0 switch；Available Decks/System Decks 分组；系统内建不可打开 |
| 设置直达 Work | `App.handleOpenSettingsFromDeck` | 一次点击 URL 为 `/story-workspace/settings/work` |
| Settings 左栏单一 Work | `StoryWorkspaceSettingsPage` | 左栏有 Work，无独立资源/插件项 |
| Settings/Work 多语言 | `StoryWorkspaceSettingsPage`、`i18n.ts` | zh 仅“工作台”、en 仅“Work”；导航/页签/ARIA 同步切换 |
| Work 三页签 | `StoryWorkspaceSettingsPage`、`settings-work` route | 三页签点击、URL query、刷新恢复 |
| Work / Deck 完整管理 | `DeckSettingsPanel`、`DeckManager surface="settings"` | 搜索/筛选/分页/创建/编辑/启停/冲突 |
| 相关对话删除闭环 | `DeckSettingsPanel`、`chatHistoryApi.ts`、Chat Thread API、`database.delete_deck` | Deck 过滤、预览、逐条确认删除、空状态解锁、事务冲突分类 |
| 资源与插件复用 | 现有 connector/plugin manager | 页签可见且无重复状态 owner |

验收截图保存于 `frontend/output/playwright/story-workspace-chat-first/`：

- `deck-enabled-launcher-wide.png`
- `deck-enabled-launcher-narrow.png`
- `settings-work-deck-wide.png`
- `settings-work-deck-narrow.png`
- `deck-related-conversations-wide.png`
- `deck-related-conversations-narrow.png`
