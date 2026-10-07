<!-- [Input] 1_prd_draft.md、../inputs/target_image.png、topic.txt、现行 PRD 及 CalendarPopup DOM/CSS。 -->
<!-- [Output] 桌面与 1024/430/390px 结构、右侧纸面承载、留白和原滚动 owner 的阶段2建议。 -->
<!-- [Pos] 顺序设计阶段2过程证据；不替代 PRD 骨架或正式交互稿，不拥有生产代码。 -->
<!-- [Sync] 2026-10-06: 按实际 64rem 断点保存结构；以连续 opaque 浅纸平面承载透明页签与可见焦点。 -->
# 阶段2：Calendar 右侧无边框结构草图

## 背景与问题

读取[阶段1](./1_prd_draft.md)、[原规则图](../inputs/target_image.png)、[任务输入](../inputs/topic.txt)与[现行 PRD](../../../../prd/calendar/calendar-right-panel-tabs-prd.md)。PDF 第5页 §5.4 表达轻纸面、多留白、普通内容无卡片；输入不是 Calendar 页面截图，不从图中推导新的业务模块。只调整右侧 workspace，左月历、业务状态、操作入口及 Modal 沿用现状。

## 结构草图与宽度

草图线条仅表示模块范围，不代表生产界面出现边框。

### 1440px：沿用左右结构

```text
┌ A1 Calendar 原透明画布 ──────────────────────────────────────┐
│                                                    A2 关闭 │
│ ┌ D1 原左月历纸面 ─────────┐  ┌ B1 页签浅纸平面 ──────────┐ │
│ │ 月份导航 / 日期格         │  │ [◷ 定时任务]  ▤  N         │ │
│ │ 日记标记 / 原尺寸         │  ├ B2 标题与原状态/操作 ──────┤ │
│ │                          │  │ 当日任务       数量/原操作 │ │
│ │                          │  │                           │ │
│ │                          │  │ B3 当前栏目正文            │ │
│ │                          │  │ C1 原安排输入/状态/分组    │ │
│ │                          │  │                           │ │
│ │                          │  │ C2 透明行：标题 / 副文字   │ │
│ │                          │  │    原行内操作，行间留白   │ │
│ └──────────────────────────┘  └───────────────────────────┘ │
│ B4 tooltip/菜单保留定位；编辑/历史 Modal 保留原覆盖关系       │
└────────────────────────────────────────────────────────────┘
```

B1 与 B2/B3 是连续浅纸底，图中接缝不是分割线。右側没有外框、静态阴影或大圆角轮廓；B2 与正文之间靠留白分层。左月历 D1 的边框、圆角及阴影不在本轮范围。

### 1024px：沿用原 64rem 断点堆叠

```text
┌ A1 原 Calendar 画布 / 外层滚动 ─────────────────┐
│                                      A2 关闭 │
│ ┌ D1 原左月历，置于上方 ─────────────────────┐ │
│ │ 月份导航 / 日期格 / 原日记标记             │ │
│ └───────────────────────────────────────────┘ │
│ ┌ B1 sticky 页签浅纸平面 ────────────────────┐ │
│ │ [◷ 定时任务]  ▤  N                         │ │
│ ├ B2 标题、计数与原操作；允许换行 ────────────┤ │
│ │ B3 正文：C1 原输入/状态/组标题              │ │
│ │          C2 透明内容行及原行内操作          │ │
│ └───────────────────────────────────────────┘ │
│ B4 原 tooltip/菜单与覆盖 Modal               │
└──────────────────────────────────────────────┘
```

当前 `@media (max-width: 64rem)` 在 1024px 已进入单列，不为本轮改成双列；月历大小、Modal 限宽及断点不变。1024px 的左右结构说法需由主 Agent 同步阶段1与现行 PRD。

### 430 / 390px：沿用原 40rem 窄屏布局

```text
┌ A1 视口内原 Calendar / 外层滚动 ────────────┐
│                                    A2 关闭│
│ ┌ D1 原月历纸面 ─────────────────────────┐ │
│ │ 月份导航 / 日期格 / 原标记              │ │
│ └────────────────────────────────────────┘ │
│ ┌ B1 sticky 页签浅纸平面 ─────────────────┐ │
│ │ ◷  ▤  [N Notion]                       │ │
│ ├ B2 标题                      原刷新 ────┤ │
│ │    数量/时间；长状态可换行              │ │
│ │                                        │ │
│ │ B3 正文：C1 创建/编辑组或原安排输入      │ │
│ │          C2 图标 标题                   │ │
│ │                 副文字 / 原操作         │ │
│ └────────────────────────────────────────┘ │
│ B4 tooltip 视口内；原 Modal 与焦点陷阱      │
└───────────────────────────────────────────┘
```

430 和 390px 不引入额外断点。原视口 margin/padding 与左月历不变；右侧 B1/B2/B3 使用相同水平内距。长标题与状态换行，操作保持触达；不通过隐藏操作、缩小月历或横向扩宽增加空间。

## 模块与原 owner 对应

| ID | 现有 DOM / selector | 结构与 owner |
| --- | --- | --- |
| A1 | `.calendar-popup-modal` / `.calendar-popup` | 保留现有画布与尺寸；窄屏原外层滚动。 |
| A2 | 原 `.modal-toolbar--default` / close | 保留原关闭入口、位置与可访问名称。 |
| D1 | `.calendar-popup__calendar` | 左月历完整保持现状，日期选择 owner 为 CalendarPopup。 |
| B1 | `.calendar-popup__workspace` 内 `.calendar-popup__tabs` | 复用 tablist 与手动激活状态；透明 tab 放在 opaque 浅纸面上。 |
| B2 | `.calendar-popup__section-heading` / `.calendar-popup__card-header` | 无分割线，标题和状态/操作保持原 DOM；右侧 header 与正文水平对齐。 |
| B3 | `.calendar-popup__workspace-scroll` > 当前 `.calendar-popup__section` / `.calendar-popup__card-body` | 原唯一 tabpanel、hidden/inert 与各栏目状态 owner 不变。 |
| C1 | `.calendar-popup__arrange` / 原 alert、hint / `.calendar-popup__notion-group h4` | 输入、恢复及分组原顺序不变，以垂直留白区分；控件保留功能边界。 |
| C2 | `.calendar-popup__task` / `__diary` / `__notion-group li` / `__undo-row` | 普通内容透明行，无外框、静态阴影、分割线；保留当前标识及所有行内操作。 |
| B4 | `__tab-wrap [role='tooltip']` / 原菜单与 task editor/history Modal | 保留定位、Portal owner、功能外观和焦点陷阱；不纳入普通面板去边框规则。 |

## 留白、承载与阶段3参数

| 项目 | 建议参数 / 实现边界 |
| --- | --- |
| 右侧承载 | `.calendar-popup__workspace` 保持 transparent。B1 tabs 与当前 section 同用 opaque `--color-bg-paper`，接触处不留透明缝隙：workspace gap 设为 0，由 B1/B2 内距产生间距。两处 border/radius/box-shadow 均为 0。不是新增卡片或容器组件。 |
| B1 横向对齐 | 桌面 tabs、heading、body 均为 1.5rem 水平内距；<=40rem 同为 1rem。1024px 沿用原非 40rem 水平内距，不修改原 Modal/月历留白。 |
| B1 到 B2 | tabs 建议上内距 .75rem、下内距 .5rem；标题上内距 1rem，使 tab 到标题由空白分隔。tab 最小 2.75rem 命中区保留。 |
| B2 到 B3 | header 不再 border-bottom；body 上内距建议 1rem，左右与 header 对齐，原正文下内距保留。header 高度允许按长标题/状态自然增高。 |
| C1 / C2 | 标题到组内正文 .75rem；分组之间 1.5rem；普通行之间建议 .75rem，不累加已有行 padding 造成重复大留白。阶段3按任务事实、日记摘要、Notion 时间决定具体间距。 |
| 文字层级 | 沿用现有主标题 1.1rem、任务标题 1rem、Notion 分组 .94rem、状态/时间 .77–.82rem 及原字体；用字重和间距分层，不新增字体或强调色。 |
| tab 状态 | 未选 tab background transparent；选中 tab 使用 `--color-bg-active` 圆角浅底、图标和名称，hover 用 `--color-bg-hover`。基底是 opaque paper；不将半透明 Token 直接叠在未知背景上。 |
| focus / 对比度 | 原 tab focus outline 使用 `--color-border-focus`，保留 inset -3px；行/输入 focus 不取消。实际主题、hover/selected 合成颜色和真实背景须在视觉验证测量，不在设计阶段声明对比度通过。 |
| 滚动 | 桌面原当前 section 独立滚动，B1 在其滚动范围外；header 沿用 section 内正常流，不新增 sticky。<=64rem 原 `.calendar-popup` 整体滚动，section height:auto/overflow:visible，B1 sticky top:0 沿用并保持 opaque 背景。任务结果、Modal 子滚动不改。 |

使用当前 `.calendar-popup__workspace` 作用域覆盖右侧，避免改动 `.calendar-popup__calendar` 及 `.calendar-popup-task-editor/history`。现有窄屏规则会重新赋予 section 圆角/阴影，因此阶段4必须在两个原断点同时落实右侧去边框，不能仅修改桌面规则。

## 待后续落实

连续 opaque paper 承载 B1+B2/B3 是为透明未选页签、sticky 及焦点提供确定背景的建议，需主 Agent 同步阶段1/现行 PRD；workspace 本身仍透明。阶段3据此确定文字和行层级，阶段4写入正式设计稿并独立评审。此文件只交付结构建议，未写生产代码、未跑测试、未声明视觉或业务验收通过。
