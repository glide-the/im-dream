<!-- [Input] Deck设计需求.pdf, pre-01a00576 maintenance, Admin content versions, and CozeLoop commit UX. -->
<!-- [Output] Active Deck evaluator-style layout with draft/explicit commit and no Workflow. -->
<!-- [Pos] Deck layout, maintenance, and version-management interaction source. -->
<!-- [Sync] 2026-08-17: keep the active layout while limiting the Deck home to
                         published-clean versions and identifying system Decks. -->
# Deck 评估器式交互草稿

> 状态：有效并持续维护。本稿不包含 Workflow。“评估器式”只借鉴 CozeLoop 的草稿、差异预览、
> 显式提交、不可变历史和冲突恢复，不引入评测任务、编排或 Prompt/Memory 工作台。

## 1. 保留、删除、简化、延期

| 结论 | 内容 |
|---|---|
| 保留 | enabled Deck 快速入口；原创建后弹窗；Deck 元数据、Agent 类型、Agent/Prompt CRUD、Claude 插件引用、Chat 交接 |
| 恢复 | `a5f3bf3` 基线的完整 Deck 自有维护，不因布局重构删功能 |
| 新增 | 所有表单写进入 durable draft；preview/confirm 提交 Deck v1/vN+1；不可变内容历史 |
| 删除 | Workflow、Agent 编排、独立 Prompt/Memory 工作台、社区/安装/市场入口 |
| 简化 | 版本管理位于 `920px` 弹窗；右侧 `300px` 默认折叠面板，不建独立工作台 |
| 延期 | 历史 Thread snapshot FK 与 apply receipt；市场分发治理 |

## 2. Deck 启用入口与 Work 管理

```text
Decks                                                [↻] [创建⌄]

Deck
打开已启用的 Deck，或前往设置继续管理

[⌕ 搜索已启用的 Deck________________________________________]

已启用                                                [设置]
[44×44 正方形图标] × 14（系统内置带盾牌角标）

[全部] [Chat] [Dream]
[图标] Deck 名称 / 说明 / 内容 vN    [图标][系统] Deck 名称 / 内容 vN

设置 → /story-workspace/settings/work

Work: [Deck] [资源链接] [插件]
[⌕ 搜索名称或说明__________________________________________]
[全部 17] [Chat 16] [Dream 1]                [全部状态⌄]
[图标] 剧本创作团队                               […] [●]
       覆盖剧情、结构、人物、对白和连续性
       Dream · 5 Agents · 内容 v2 · 草稿 r9 · 运行插件 v1.1.0
```

Settings 是“已启用”标题行的兄弟动作，不属于图标列表，页面不显示数量标签。主页面只搜索和展示
enabled + published + clean Deck，不显示未发布或带草稿 Deck，也没有 switch；完整集合与启停唯一属于 Work / Deck。
内容版本事实来自 capability-backed Deck projection；
插件 semver 可以在 Work 行中同列显示，但必须标明“运行插件”。

## 3. 新建、修改与版本迭代

```text
创建菜单 → POST /api/decks → 返回 deck_id → 打开同一维护弹窗
                                      │
                                      ├─ 编辑任一表单 → 草稿 r2/r3/…
                                      ├─ 预览差异 → 取消（零写）
                                      └─ 确认提交 → Deck v1
                                                           │
                                      后续修改 → 草稿 rN → 提交 v2/v3
```

弹窗头部：

```text
┌──────────────────────────────────────────────────────────────┐
│ [icon] Deck 名称 · 内容 v2 · 草稿 r9                         │
│                         [提交 v3] [版本记录] [×]             │
├──────────────────────────────────────────────────────────────┤
│ [概览] [Agents 5] [Claude 插件]                              │
├──────────────────────────────────────────────────────────────┤
│ Deck Name / Description · Agent 类型 · Agent/Prompt · 插件  │
└──────────────────────────────────────────────────────────────┘
```

## 4. 提交版本状态草图

```text
首次提交                         后续提交
┌──────────────────────┐         ┌──────────────────────┐
│ 首次提交             │         │ 基于 v2             │
│ 提交 Deck 为 v1      │         │ 提交 Deck 为 v3      │
│ + Deck 基础信息      │         │ ~ Agents             │
│ + Agents             │         │ ~ Claude 插件        │
│ [取消] [确认 v1]     │         │ [取消] [确认 v3]     │
└──────────────────────┘         └──────────────────────┘

冲突：草稿已变化，请刷新差异后重新确认（不覆盖）
失败：v2 保持不变，草稿 r9 已保留                    [重试]
成功：已提交 v3；当前草稿与 v3 一致
```

## 5. 默认折叠历史

```text
┌──────────────────── 主编辑区 ────────────────┬── 版本记录 ──┐
│ 概览 / Agents / Claude 插件                  │ 当前内容 v3  │
│                                              │ ● v3 当前    │
│                                              │ ○ v2         │
│                                              │ ○ v1         │
│                                              │ 运行插件 v1.1│
└──────────────────────────────────────────────┴──────────────┘
```

按钮默认收起；桌面侧栏在 layout flow 内，390px 原组件全宽覆盖 workspace。展开/收起零业务写入。

## 6. 数据与并发

- 原表是草稿内容，避免复制 `deck_drafts` 整套数据。
- 每个有效表单写先锁 Deck 聚合根再更新子表并推进 revision。
- commit 事务重新验证权限/CAS，读取完整 snapshot，比较最新 hash，再 append vN。
- 等价保存、取消 preview、历史展开/关闭均不推进 revision/版本。
- 历史 Thread 继续使用原绑定，不因 vN+1 自动升级。

## 7. 验收标准

1. 本稿保持有效，布局与 PDF/IM token 一致。
2. 新建后能继续更新；首次 v1 与后续 vN+1 均有明确入口。
3. 所有 Deck 表单有效变更进入同一草稿 revision。
4. 内容 vN 是主版本记录；运行插件版本只是快照内次级事实。
5. preview/取消零写，冲突/失败不丢草稿或旧版本。
6. 不存在 Workflow、市场或 Coze 详细工作台。
