<!-- [Input] Deck设计需求.pdf reference images, IM tokens, Deck CRUD, and content-version capability. -->
<!-- [Output] Implemented published-clean desktop/narrow visual hierarchy and low-fidelity state sketches. -->
<!-- [Pos] Deck UI visual source of truth. -->
# Deck UI 视觉与布局规范

## 1. 视觉结论

Work 参考图的插件设置语言限定在 Settings / Work 右侧内容区；本轮 Deck 参考图只提供主页面骨架：
大标题、说明、宽搜索、已启用标题行、正方形快捷图标和下方两列内容。两者都不复制参考产品的品牌皮肤、
市场分类或安装动作。Work 使用连续浅色画布、1px 分隔线、宽松列表行和行尾开关。Deck 主页面沿用 IM 外壳。
编辑器为 `920px` 弹窗，
而非宽屏工作台；只保留一个外层阴影。IM 的米白背景、深棕正文、纸张边框和现有字体 token 保持不变。

CozeLoop 只提供“草稿、显式提交、版本身份、变更影响、乐观锁冲突”的参考。本页没有 Workflow、
Prompt 工作台、Memory 工作台、市场或发布入口；Agent Prompt 仍是 Deck 自有 Agent 字段。

## 2. Deck 首页

```text
┌────────────────────────────── 840 ──────────────────────────────┐
│ Decks                                             [↻] [Create⌄] │
│                                                                  │
│ Decks                                                            │
│ Open an enabled Deck, or continue management in Settings         │
│                                                                  │
│ [⌕ Search enabled Decks_______________________________________]   │
│                                                                  │
│ Enabled                                                   [设置] │
│ [icon] × 14（44×44；12px 间隔）                                 │
│                                                                  │
│ [All 16] [Chat 15] [Dream 1]                                    │
│ Available Decks                                                  │
│ ──────────────────────────────────────────────────────────────── │
│ [icon] Deck name / version      [icon] Deck name / draft         │
└──────────────────────────────────────────────────────────────────┘
```

快捷区只消费 enabled + published + clean 投影并截取 14 个；每个 item 固定为 `44×44px` 正方形，内部 SVG 为 `24×24px`。
Settings 位于标题右上角且不进入 `role=list`，页面不渲染数量标签。搜索、Agent 类型筛选和下方两列
列表同样只消费这一正式可用投影，点击列表进入维护弹窗；主页面不渲染草稿、状态筛选和 switch。系统 Deck
用快捷图标盾牌角标和列表“系统/System”标签区分。内容版本来自真实 capability-backed 字段，不推断后端没有的版本。

## 3. Deck 维护弹窗

```text
┌────────────────────────────── 920 ──────────────────────────────┐
│ [icon] 剧本创作团队   内容 v2 · 草稿 r9 [提交 v3][版本记录][×] │
├─────────────────────────────────────────────────────────────────┤
│ [概览] [Agents 5] [Claude 插件]                                 │
├─────────────────────────────────────────────────────────────────┤
│ Deck 信息                                                       │
│ [Deck Name________________] [Deck Description________________]  │
│                                                                 │
│ Agent 类型                                                      │
│ ( ) 普通 Chat Agent        (●) Dream Agent                      │
└─────────────────────────────────────────────────────────────────┘
```

- “概览”维护名称、说明和 Agent 类型；Deck 启停只在 Work / Deck 行尾完成。
- “Agents”是 `220px` 主列表 + 详情；保留新增、启停、名称、图标、颜色、Prompt、删除和 Chat 交接。
- “Claude 插件”使用扁平分隔行选择 ready/digest 固定的安装引用。
- 创建仍是 `POST /api/decks` 成功后弹出同一维护弹窗；该服务端记录就是 durable draft，不是前端临时页。

### 3.1 Work 的相关对话弹窗

- 入口只在用户 Deck 行的“更多”菜单中，不增加常驻列或新的 Settings 分类。
- 弹窗沿用 Chat 历史预览的扁平行：左侧消息图标，中间单行标题与更新时间，右侧弱化删除操作。
- 仍有对话时底部“删除 Deck”禁用；清空后保持同一弹窗并解锁，避免用户丢失操作上下文。
- 窄屏沿用同一列表和数据；隐藏逐条删除按钮的文字但保留图标、aria-label 与触控目标，不产生横向溢出。

## 4. 默认折叠的版本记录

默认不渲染历史面板。点击顶部“版本记录”后，桌面在同一弹窗
右侧增加 `300px` 面板，主内容缩窄但关键按钮仍可见：

```text
┌────────────────────── 主内容 ─────────────────┬── 300 ──────────┐
│ 概览 / Agents / Claude 插件                   │ 版本记录       [›]│
│                                               │ 当前内容 v3      │
│                                               │ ● v3 当前        │
│                                               │ ○ v2             │
│                                               │ ○ v1             │
│                                               │ ──────────────── │
│                                               │ 运行插件 v1.0.1  │
│                                               │ [选择运行版本]   │
└───────────────────────────────────────────────┴──────────────────┘
```

再次点击、点击面板收起按钮或按 Escape 只收起面板，焦点返回触发按钮；不会关闭整个 Deck。加载、空、
失败和冲突均在面板内恢复，主编辑区保持可用。内容 vN 是主轴；运行绑定历史保持次级折叠。

## 5. 精确版本选择确认

```text
┌──────────────── 选择运行版本 ────────────────┐
│ 精确版本；服务端重验权限、兼容性和 revision │
│ ( ) Drama Forge  v1.0.1  [当前] [published] │
│ (●) Drama Forge  v1.1.0         [published] │
│                                             │
│ v1.0.1 → v1.1.0                            │
│ 新增能力 0 项 · 移除能力 0 项               │
│ 只影响下一次运行；历史和当前运行保持原版本。│
│                            [取消] [确认切换] │
└─────────────────────────────────────────────┘
```

确认请求必须携带精确 plugin id/version、`expected_binding_revision` 与 `apply_to=next_run`。取消零写入；
409 显示当前 revision 并要求刷新后重选；失败保留原活动绑定。

## 6. 390px 窄屏

窄屏复用相同 DOM、数据和状态机：Deck 快捷图标保持 44×44px 并以 8px 间隔按侧栏后的实际内容宽度自动换行，下方列表从两列收为一列；Settings 分类与 Work 页签分别横向
滚动；Work 列表隐藏次要元数据但保留名称、说明、菜单和 switch；编辑器占满视口；
Agents 列表横向滚动后显示详情；版本面板在弹窗 workspace 内覆盖主内容并保留明确收起按钮。它不是另一套
路由或业务流程。文档级 `scrollWidth <= clientWidth + 1`，关键按钮最小高度 40–44px。

## 7. 状态与验收

| 状态 | 表现 | 恢复/约束 |
|---|---|---|
| 默认 | 版本按钮 `aria-expanded=false`，面板和请求均不存在 | 点击后加载 |
| 加载 | 面板显示“正在读取版本记录” | 主编辑可继续使用 |
| 空 | “暂无已提交内容版本” | 引导顶部提交 v1，不补造 |
| 失败/权限不足 | 可恢复错误与重试；不泄露原始响应 | 原绑定不变 |
| 内容提交成功 | 当前 vN、草稿状态、时间线同步刷新 | snapshot 不可变 |
| 并发冲突 | 显示服务端 current revision | 刷新、重选、重新确认 |
| 系统 Deck | 允许查看历史，隐藏选择版本 | 只读 |
| 市场/Workflow | 不存在入口、状态、占位或请求 | 延期/排除 |

实现验收截图位于：

- `frontend/output/playwright/story-workspace-chat-first/deck-enabled-launcher-wide.png`
- `frontend/output/playwright/story-workspace-chat-first/deck-enabled-launcher-narrow.png`
- `frontend/output/playwright/story-workspace-chat-first/settings-work-deck-wide.png`
- `frontend/output/playwright/story-workspace-chat-first/deck-version-history-wide.png`
- `frontend/output/playwright/story-workspace-chat-first/deck-version-history-narrow.png`
- `frontend/output/playwright/story-workspace-chat-first/deck-popup-agent-maintenance-wide.png`
