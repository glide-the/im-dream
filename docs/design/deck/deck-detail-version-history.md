<!-- [Input] Deck/Agent/plugin form APIs, Admin content-version capability, and CozeLoop commit reference. -->
<!-- [Output] Create/update/draft/explicit-commit and folded immutable history interaction contract. -->
<!-- [Pos] Deck detail and content-version functional-unit design. -->
<!-- [Sync] 2026-08-16: make every effective Deck form mutation part of one versioned draft. -->

# Deck 创建、更新与折叠式内容版本记录

## 1. 创建后如何更新

| 项 | 定义 |
|---|---|
| 使用场景 | 用户创建 Deck 后继续填写，或以后从列表再次打开修改 |
| 用户目标 | 随时保存表单，不丢内容；准备好时才生成可追溯版本 |
| 入口 | 创建成功自动弹出；列表名称区/更多菜单重新打开 |
| 页面层级 | `920px` 模态层；头部草稿状态/提交/版本记录；概览、Agents、Claude 插件 |
| 关键操作 | 名称说明、Agent 类型、Agent/Prompt CRUD、图标颜色启停、插件引用、运行绑定 |
| 数据依赖 | 原 CRUD + `draft_revision` + version state/preview/commit/history API |

新建仍先走生产 `POST /api/decks`，返回 `deck_id` 后才打开维护弹窗。新 Deck 是持久草稿 r1，而非只存在
于前端的临时表单；关闭不会删除，重新打开继续编辑。首次提交才生成 v1。

## 2. 哪些表单变更进入草稿修订

| 表单单元 | 纳入 snapshot 的字段/关系 |
|---|---|
| Deck 概览 | name/i18n description、icon、color、enabled、order |
| Agent 类型 | Chat/Dream 与精确 active runtime binding |
| Agents | 新增、删除、名称、Prompt、icon、color、enabled、order、memory config 数据 |
| Claude 插件 | 已验证安装引用、resolved version、digest、enabled、order |

每次有效写入在同一事务先锁 Deck 行，比较旧值，成功后 `draft_revision + 1`。等价 blur/save 不推进修订；
Voice 的运行时 `thread_id` 不是 Deck 表单配置，不进入内容版本。

## 3. 弹窗默认状态

```text
┌──────────────────────────────────────────────────────────────────┐
│ [icon] 剧本创作团队 · 内容 v2 · 草稿 r9                         │
│                         [提交 v3] [版本记录] [×]                 │
├──────────────────────────────────────────────────────────────────┤
│ [概览] [Agents 5] [Claude 插件]                                 │
├──────────────────────────────────────────────────────────────────┤
│ 当前 segment 表单；每项有效保存都进入草稿                       │
└──────────────────────────────────────────────────────────────────┘
```

- 未提交过：`内容版本未提交 · 草稿 rN`，主操作“提交 v1”。
- 已提交且无新修改：`内容 vN`，提交按钮 disabled。
- 已提交后再修改：`内容 vN · 草稿 rN`，主操作“提交 vN+1”。
- capability 503：表单仍可编辑，提交禁用并明确“版本能力尚未部署”，不伪造版本。

## 4. 提交版本确认

点击提交先发送 preview，服务端按最新 vN snapshot 与当前草稿生成分类差异；preview 不写数据库。

```text
┌────────────────────────────────────────────────────┐
│ 基于 v2                                            │
│ 提交「剧本创作团队」为 v3                     [×] │
│ 提交会冻结当前 Deck 表单；历史 Thread 不自动升级。│
├────────────────────────────────────────────────────┤
│ Deck 基础信息                         修改 · name │
│ Agents                               修改          │
│ Claude 插件                          修改          │
├────────────────────────────────────────────────────┤
│ 版本说明（可选） [____________________________]    │
│                                  [取消] [确认 v3] │
└────────────────────────────────────────────────────┘
```

确认携带 `expected_draft_revision + expected_base_version`。事务重新锁 Deck、重算 snapshot/hash并追加
`deck_versions`，随后更新 latest/published revision。取消不发送 commit；409 刷新状态并要求重新 preview；
任何失败回滚，保留原草稿与原 vN。

## 5. 默认折叠版本记录

默认 `aria-expanded=false`，不渲染历史侧栏。展开后桌面在布局流内加入 `300px` 面板，不遮挡主操作；
再次点击、面板收起或 Escape 关闭并恢复触发器焦点。390px 使用相同组件/数据，面板占同一 workspace 全宽。

```text
主编辑区                                     │ 版本记录        [›]
                                             │ 当前 Deck 内容
                                             │ v3 · 已同步
                                             │ ──────────────
                                             │ ● v3 当前
                                             │ ○ v2 调整 Agents
                                             │ ○ v1 首次提交
                                             │ ──────────────
                                             │ 运行插件 v1.1.0
                                             │ [选择运行版本]
```

内容 vN 是主时间线。插件 semver/binding revision 折叠在次级“运行配置记录”内，每次内容 commit 的
snapshot 也固定当时 runtime binding，但二者不互相冒充。

## 6. 状态与异常

| 状态 | 呈现/恢复 |
|---|---|
| state/history loading | 局部 loading；主编辑可继续使用 |
| history empty | “暂无已提交内容版本”；提示从顶部提交 v1 |
| permission denied | 关闭写入口并显示不泄露资源的错误 |
| no changes | 提交禁用；服务端仍以 hash 阻止重复版本 |
| preview/commit conflict | 显示远端最新 revision/version；刷新后重新预览 |
| commit failure | 弹窗保留、草稿保留、旧版本不变，可重试 |
| commit success | 关闭确认层，头部/列表/时间线刷新为 vN |
| 操作冲突 | 行锁 + CAS；绝不生成部分 snapshot |

## 7. 验收标准

1. 保留原创建并弹出逻辑；创建、关闭、重开后均能继续维护。
2. Deck 弹窗所有真实配置表单变更纳入聚合草稿 revision。
3. 首次提交产生 v1；后续修改后提交依次产生 v2/v3，历史不可变。
4. preview/取消零写；冲突/失败保留草稿和已提交版本。
5. 内容版本主轴与运行插件版本清楚分层；版本记录默认折叠。
6. 无 Workflow、Agent 编排、独立 Prompt/Memory 工作台或市场入口。
7. 桌面和 390px 使用同一业务流程，无页面级横向溢出。
