<!-- [Input] html-design-workflow Stage 1 PRD、目标截图、主题说明、现行 CalendarPopup 结构。 -->
<!-- [Output] Calendar 月历与右侧独立 Scheduled tasks / Diary 纸张卡片的现行桌面、窄屏和状态骨架。 -->
<!-- [Pos] 现行 Calendar PRD 的结构图附件；产品规则见同目录 PRD，视觉细节见 docs/design/claude-agent。 -->
<!-- [Sync] 2026-09-29: 右栏改为无共享外框的布局容器，任务与日记成为同级独立纸张卡；旧骨架移入 history。 -->

# Calendar 日记日期弹窗：独立任务卡与日记卡页面骨架

## 文档导航

- [现行 PRD](./scheduled-task-diary-page-prd.md)
- [正式 UI 设计](../../design/claude-agent/scheduled-task-diary-page-ui-design.md)
- [旧版共享工作区骨架（历史）](./history/scheduled-task-diary-page-structure-sketch-v1-20260929.md)

## 1. 结构判断

目标结构的核心不是在现有右侧大面板里增加两条边框，而是取消该大面板的可见表面：右栏只作为无背景、无边框、无阴影的纵向布局与滚动容器。`Scheduled tasks` 与 `Diary` 是其中两个同级、各自闭合的 Paper Cream `section/card`。两卡之间露出 Warm Canvas 间隙，因此从轮廓上可以直接识别为两个业务区域。

选中日期是两卡共享的页面上下文，但不重新形成第三张大卡。宽屏和窄屏使用同一业务顺序：月历 → 日期上下文 → Scheduled tasks 卡 → Diary 卡。

## 2. 桌面宽屏结构草图

```text
┌────────────────────────────── A1 Calendar dialog ──────────────────────────────┐
│ A2 Calendar                                                       [A3 Close ×] │
│                                                                                │
│ ┌────────────── B1 Month calendar paper ──────────────┐  C1 Detail card stack │
│ │ B2 [‹]             September 2026              [›] │  (layout only: no     │
│ │                                                    │   visible outer frame)│
│ │ B3  Sun  Mon  Tue  Wed  Thu  Fri  Sat             │                       │
│ │        1    2    3    4    5                      │  C2 Today              │
│ │    6   7    8    9   10   11   12                 │                       │
│ │   13  14   15   16   17   18   19                 │  ┌─ D1 Scheduled tasks card ──────────────┐
│ │   20  21   22   23   24   25   26                 │  │ D2 Scheduled tasks                D3 1 │
│ │   27  28  [29]  30                                 │  ├─────────────────────────────────────────┤
│ │        • diary marker                              │  │ D4 task-local state / task list          │
│ │                                                    │  │ ┌─ D5 Scheduled task row ──────────────┐ │
│ └────────────────────────────────────────────────────┘  │ │ Morning review  [Enabled]       [⋮] │ │
│                                                        │ │ Daily 09:00 · Asia/Shanghai         │ │
│                    C3 Warm Canvas gap                    │ │ Next / recent run                   │ │
│                    between sibling cards                │ │ [Run now] [Pause] [Open thread ↗]   │ │
│                                                        │ └─────────────────────────────────────┘ │
│                                                        └─────────────────────────────────────────┘
│                                                                         C3 gap
│                                                        ┌─ E1 Diary card ─────────────────────────┐
│                                                        │ E2 Diary                          E3 2 │
│                                                        ├─────────────────────────────────────────┤
│                                                        │ E4 diary-local state / diary list       │
│                                                        │ ┌─ E5 Current diary row ──────────────┐ │
│                                                        │ │ 02:16 PM  [Current note]   [Delete] │ │
│                                                        │ │ Untitled                           │ │
│                                                        │ └─────────────────────────────────────┘ │
│                                                        │ ┌─ E6 Diary row ──────────────────────┐ │
│                                                        │ │ 01:14 AM                  [Delete] │ │
│                                                        │ │ Untitled                           │ │
│                                                        │ └─────────────────────────────────────┘ │
│                                                        └─────────────────────────────────────────┘
└────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 桌面结构约束

1. A1 负责弹窗边界；B1 是左侧月历纸面；C1 只是右栏布局/滚动容器。C1 不绘制同时包围 D1 与 E1 的背景、边框、圆角或阴影。
2. C2 只说明当前选中日期，不显示混合的“日记数 / 任务数 / 需处理数”。任务数量归 D3，日记数量归 E3，需处理反馈归 D1。
3. D1 与 E1 是 DOM 和视觉上的同级 `section`，各有完整外轮廓。C3 必须露出弹窗的 Warm Canvas，不能用共享分隔线模拟两卡。
4. D2/D3 与 D4、E2/E3 与 E4 分别由各自卡片内部的完整横向分隔线隔开。
5. D1 和 E1 按内容自然增高，不强制等高。C1 统一承载纵向滚动，B1 保持可见。
6. D5 展开编辑或历史时只增加 D1 的高度；E1 仍作为独立兄弟卡保留在其后，不被覆盖或禁用。

## 3. 窄屏单列结构草图

```text
┌────────────── A1 Calendar dialog / narrow viewport ───────────────┐
│ A2 Calendar                                           [A3 ×]     │
│                                                                  │
│ ┌──────────── B1 Month calendar paper ─────────────────────────┐ │
│ │ B2 [‹]              September 2026              [›]          │ │
│ │ B3 Sun Mon Tue Wed Thu Fri Sat                               │ │
│ │       1   2   3   4   5                                    │ │
│ │   6   7   8   9  10  11  12                                │ │
│ │  13  14  15  16  17  18  19                                │ │
│ │  20  21  22  23  24  25  26                                │ │
│ │  27  28 [29] 30                                             │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ C2 Today                                                         │
│                                                                  │
│ ┌─ D1 Scheduled tasks card ────────────────────────────────────┐ │
│ │ D2 Scheduled tasks                                     D3 1 │ │
│ ├──────────────────────────────────────────────────────────────┤ │
│ │ D4                                                        │ │
│ │ ┌─ D5 Scheduled task row ────────────────────────────────┐ │ │
│ │ │ Morning review                         [Enabled] [⋮]   │ │ │
│ │ │ Daily 09:00 · Asia/Shanghai                         │ │ │
│ │ │ Next / recent run                                  │ │ │
│ │ │ [Run now                       ]                    │ │ │
│ │ │ [Pause]                           [Open thread ↗]   │ │ │
│ │ └──────────────────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                        C3 Warm Canvas gap                         │
│ ┌─ E1 Diary card ──────────────────────────────────────────────┐ │
│ │ E2 Diary                                               E3 2 │ │
│ ├──────────────────────────────────────────────────────────────┤ │
│ │ E4                                                        │ │
│ │ ┌─ E5 Current diary row ────────────────────────────────┐ │ │
│ │ │ 02:16 PM  [Current note]                   [Delete] │ │ │
│ │ │ Untitled                                           │ │ │
│ │ └──────────────────────────────────────────────────────┘ │ │
│ │ ┌─ E6 Diary row ────────────────────────────────────────┐ │ │
│ │ │ 01:14 AM                                  [Delete] │ │ │
│ │ │ Untitled                                           │ │ │
│ │ └──────────────────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 3.1 窄屏结构约束

1. 顺序固定为 B1 → C2 → D1 → C3 → E1；不创建移动端专用数据或第二套交互。
2. D1、E1 占满可用内容宽度，并始终保留各自四周边界；C3 仍清楚可见。
3. D5 的事实字段和操作可以换行，主操作可占一整行；不得产生横向滚动。
4. E5/E6 第一行放时间、当前笔记标识与删除入口，第二行放标题。删除入口不得与打开日记的点击区域合并。
5. 弹窗内容纵向滚动；卡头与自己的正文保持在同一卡片，不抽成共享吸顶标题。

## 4. 两张卡片的局部状态骨架

### 4.1 Scheduled tasks：加载、错误与空态

```text
┌─ D1 Scheduled tasks card ───────────────────────────────────────┐
│ D2 Scheduled tasks                          D3 Loading / ? / 0 │
├────────────────────────────────────────────────────────────────┤
│ D4a Loading: task-shaped loading feedback                      │
│                               or                               │
│ D4b Error: Tasks are temporarily unavailable.       [Retry]   │
│                               or                               │
│ D4c Empty: No scheduled tasks for this day.                    │
└────────────────────────────────────────────────────────────────┘

                    C3 Warm Canvas gap

┌─ E1 Diary card (unchanged and interactive) ────────────────────┐
│ E2 Diary                                                   E3 2│
├────────────────────────────────────────────────────────────────┤
│ E4 / E5 / E6 remain visible; entries can open or be deleted.   │
└────────────────────────────────────────────────────────────────┘
```

- 已认证用户选中日期后，D1 始终存在；加载、失败、成功为空和有数据只替换 D4 的内容。
- D4b 的错误与 Retry 完全属于 D1。它不替换 C1、不遮挡 E1，也不把 E3 变成未知。
- 未认证时可以不渲染 D1；E1 与既有日记能力不受影响。

### 4.2 Scheduled task：编辑与历史展开

```text
┌─ D1 Scheduled tasks card ───────────────────────────────────────┐
│ D2 Scheduled tasks                                          D3 1│
├────────────────────────────────────────────────────────────────┤
│ ┌─ D5 Scheduled task row ─────────────────────────────────────┐ │
│ │ task summary / actions                                     │ │
│ ├─ D6 Expanded editor OR D7 Expanded run history ─────────────┤ │
│ │ fields, revision conflict and local validation              │ │
│ │ OR trigger rows, pagination, actionable run feedback        │ │
│ └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

- D6、D7 是 D5 的内部展开区域，不成为 C1 中的第三张分类卡。
- revision 冲突、DST 错误、执行结果待核查、自动刷新暂停等反馈出现在 D5/D6/D7 的发生位置。
- 删除成功后的原位撤销条仍占据原 D5 位置。

### 4.3 Diary：空态与条目态

```text
┌─ E1 Diary card ─────────────────────────────────────────────────┐
│ E2 Diary                                                   E3 0│
├────────────────────────────────────────────────────────────────┤
│ E4a No diary entries for this day.                             │
└────────────────────────────────────────────────────────────────┘

┌─ E1 Diary card ─────────────────────────────────────────────────┐
│ E2 Diary                                                   E3 1│
├────────────────────────────────────────────────────────────────┤
│ E4b ┌─ E5 Current diary row ─────────────────────────────────┐ │
│     │ time + [Current note]                       [Delete]   │ │
│     │ title                                                  │ │
│     └─────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

E1 在 0 条日记时仍保留完整卡头、分隔线和内容区。E5 的绿色细边/浅底只表达当前日记状态，`Current note` 文本提供非颜色线索。

## 5. 模块索引

| 编号 | 模块 | 层级/位置 | 结构职责 |
| --- | --- | --- | --- |
| A1 | Calendar dialog | 页面最外层 | 焦点、关闭和弹窗内容边界 |
| A2 | Dialog title | A1 顶部 | 标识 Calendar |
| A3 | Close control | A1 顶部末端 | 关闭弹窗并回焦入口 |
| B1 | Month calendar paper | 桌面左栏 / 窄屏首段 | 独立月历纸面 |
| B2 | Month navigation | B1 顶部 | 切换月份并显示当前月份 |
| B3 | Date grid | B1 正文 | 选择日期，显示今天/选中/日记标记 |
| C1 | Detail card stack | 桌面右栏 / 窄屏接在月历后 | 只负责布局和滚动，不提供可见外框 |
| C2 | Selected date context | C1 顶部 | 给 D1、E1 提供共享日期上下文，不混合计数 |
| C3 | Warm Canvas gap | D1 与 E1 之间 | 暴露背景并分开两个完整外轮廓 |
| D1 | Scheduled tasks card | C1 第一张同级卡 | 独立 Paper Cream 任务分类容器 |
| D2 | Scheduled tasks title | D1 卡头 | 标识任务分类 |
| D3 | Task count | D1 卡头末端 | 只显示任务数量或任务局部的 loading/unknown |
| D4 | Task card body | D1 分隔线下方 | 容纳加载、错误/重试、空态或任务列表 |
| D4a | Task loading | D4 互斥状态 | 显示任务请求进行中 |
| D4b | Task error | D4 互斥状态 | 提供可行动错误说明与重试 |
| D4c | Task empty | D4 互斥状态 | 说明当日没有任务 |
| D5 | Scheduled task row | D4 内容态 | 展示任务事实、状态、操作和最近执行 |
| D6 | Task editor | D5 内部 | 编辑 desired、处理校验/revision 冲突 |
| D7 | Run history | D5 内部 | 展示 trigger 历史、分页与打开会话 |
| E1 | Diary card | C1 第二张同级卡 | 独立 Paper Cream 日记分类容器 |
| E2 | Diary title | E1 卡头 | 标识日记分类 |
| E3 | Diary count | E1 卡头末端 | 只显示当日日记数量 |
| E4 | Diary card body | E1 分隔线下方 | 容纳日记空态或列表 |
| E5 | Current diary row | E4 内容态 | 时间、当前笔记标识、标题、打开和删除 |
| E6 | Diary row | E4 内容态 | 时间、标题、打开和删除 |

## 6. 语义与滚动树

```text
A1 dialog
├── A2 heading + A3 close
└── Calendar layout
    ├── B1 section[month calendar]
    │   ├── B2 navigation
    │   └── B3 grid
    └── C1 div[detail card stack, scroll container, no visual surface]
        ├── C2 selected-date context
        ├── D1 section[aria-labelledby=D2]
        │   ├── header: D2 + D3
        │   ├── divider
        │   └── D4: D4a | D4b | D4c | list(D5)
        ├── C3 layout gap
        └── E1 section[aria-labelledby=E2]
            ├── header: E2 + E3
            ├── divider
            └── E4: empty | list(E5, E6)
```

D1 与 E1 的 DOM 顺序等于视觉顺序。任务错误使用 D4b 的 `alert`；数量更新属于各自卡头的 polite live region。打开日记与删除日记保持两个可独立聚焦的控制。

## 7. 结构验收清单

- [ ] 桌面结构可同时识别 B1 月历、D1 Scheduled tasks 卡和 E1 Diary 卡。
- [ ] C1 没有同时包围 D1、E1 的可见背景、边框、圆角或阴影。
- [ ] D1、E1 是同级独立 section，各自具备标题、计数、完整分隔线和正文。
- [ ] C3 显示 Warm Canvas 间隙，两卡轮廓不会连接成一张大卡。
- [ ] 任务加载、错误/重试、空态和列表都只出现在 D4；D1 在已认证成功选中日期后不因 0 条任务消失。
- [ ] 任务失败时 E1 仍显示，日记仍可打开和删除。
- [ ] D6 编辑、D7 历史及所有任务局部反馈在 D5/D1 内展开。
- [ ] 日记为 0 条时 E1 仍保留完整卡片；有条目时 E5/E6 遵循两行信息结构。
- [ ] 窄屏按 B1 → C2 → D1 → E1 单列排列，无横向滚动。
- [ ] 自动化结构断言可验证 D1/E1 的不同父卡片、各自 heading 关系和 C1 无表面样式，而非只断言两个标题文本存在。
