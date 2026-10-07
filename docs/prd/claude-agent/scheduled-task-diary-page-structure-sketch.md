<!-- [Sync] 2026-10-06: current Calendar supplement uses selected snapshots and historical creation; preserve preceding task/Chat/history text. -->
<!-- [Input] 现行定时任务 PRD、四张用户参考图和 html-design-workflow Stage 2 结构产物。 -->
<!-- [Output] Calendar/Chat 定时任务列表、结果、编辑和详情侧栏的宽窄屏骨架及滚动/焦点边界。 -->
<!-- [Pos] docs/prd/claude-agent 下的现行页面结构图；正式视觉规范见 docs/design/claude-agent/scheduled-task-diary-page-ui-design.md。 -->
<!-- [Sync] 2026-09-29: v5 将 scheduled run Conversations 收入详情栏，并从通用 TaskSession 列表排除。 -->

<!-- [Sync] 2026-10-04: index the Calendar right-panel tab proposal and preserve the complete preceding text beside this file. -->
# Ink & Memory 定时任务完整交互页面结构草图 v5（现行）

> 2026-10-04 现行补充：[日历右侧页签设计](../calendar/calendar-right-panel-tabs-prd.md)。Calendar 页签结构以新稿为准；本文 Chat 与任务内部结构继续适用。现行日历已采用互斥页签；2026-10-06 Notion 改用当前选择范围的连接器快照，历史展示当日创建、今天更新项单独校验。严格全集不属于用户最新范围，技术验证状态见现行日历回执。改动前的完整原文保存在[历史快照](./scheduled-task-diary-page-structure-sketch-v5-20261004-history.md)。

> 输入：`files/workspace/1_prd_draft.md`、`files/inputs/target_image.png`、`files/inputs/topic.txt` 与 topic 中三张辅助参考图
> 输出用途：为 Stage 3 层级与状态映射、Stage 4 UI 规格提供结构底稿
> 取证边界：参考图只提供空间关系、信息层级和交互形态；图中文字不作为产品能力。本稿不引入分享、麦克风、每月、重复结束、通知、cron 或新的任务协议。

## 1. 结构提炼结论

本轮由五个互相关联、但滚动与状态边界清晰的界面组成：

1. **Calendar 列表态**：透明画布上保留月历、定时任务、Diary 三张独立悬浮纸面；任务纸面顶部是轻量安排入口，下方是两行信息的任务列表。
2. **Calendar 最近结果态**：点击任务行后，只替换任务纸面的正文；月历与 Diary 保持原位。结果正文使用同一 trigger 的 `target_thread_id` 与 `final_message_id`。
3. **编辑 Modal**：从铅笔进入独立模态层；编辑区不在列表内展开，也不改变三张纸面的尺寸。
4. **Chat 任务标记**：`create_scheduled_task` Tool 成功后，在对应助手 turn 内插入可恢复的任务标记卡。
5. **Chat 任务详情侧栏**：点击标记后打开既有右侧栏位置，依次展示任务信息、Conversations、任务周期；普通 Chat 仍可独立滚动和输入。

核心结构规则：

- Calendar 宽屏的左月历固定；右侧“任务 + Diary”卡栈拥有外层滚动。
- 任务纸面正文只有 `LIST` 与 `RESULT(taskId)` 两种互斥模式。
- 编辑 Modal、行尾菜单是覆盖层，不参与 Calendar grid 高度计算。
- Chat 右侧任务详情与文件、TaskSession、子代理等既有侧栏互斥。
- scheduled trigger 复用的 TaskSession 不进入通用 created-task 列表；该执行 Thread 只出现在 H7 Conversations。
- 所有“打开聊天”都使用对应 trigger 的 `target_thread_id`，不使用 source Thread 或最近浏览 Thread 代替。

---

## 2. Calendar 宽屏：列表态

### 2.1 页面结构草图

```text
┌─ C0 Calendar Dialog / transparent canvas / viewport bounded ────────────────────────────────┐
│ C0.1 dimmed application background                                              [C0.2 ×]  │
│                                                                                             │
│ ┌─ C1 Calendar Paper / fixed in desktop column ─────────┐   ┌─ C2 Right Card Stack ───────┐ │
│ │ C1.1 Month navigation                                │   │ ┌─ C3 Scheduled Paper ─────┐ │ │
│ │ [‹]                  2026 年 9 月                 [›] │   │ │ C3.1 Header              │ │ │
│ │                                                       │   │ │ 定时任务             2   │ │ │
│ │ C1.2 Week headings                                    │   │ │ 9 月 29 日 · 需处理 0    │ │ │
│ │ 日      一      二      三      四      五      六    │   │ ├─────────────────────────┤ │ │
│ │                                                       │   │ │ C4 Arrange task          │ │ │
│ │ C1.3 Calendar grid                                    │   │ │ ┌─────────────────────┐ │ │ │
│ │ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐    │   │ │ │C4.1＋ C4.2输入 C4.3↑│ │ │ │
│ │ │    │ │    │ │  1•│ │  2•│ │  3 │ │  4•│ │  5•│    │   │ │ └─────────────────────┘ │ │ │
│ │ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘    │   │ │                           │ │ │
│ │ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐    │   │ │ C5 Task list              │ │ │
│ │ │  6•│ │  7 │ │  8•│ │[ 9•]│ │ 10 │ │ 11 │ │ 12 │    │   │ │ ┌─ C6 task row ─────────┐ │ │ │
│ │ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘    │   │ │ │◉  每日整理笔记   [✎][⋯]│ │ │ │
│ │ …                                                     │   │ │ │   正在运行 · 刚刚       │ │ │ │
│ │                                                       │   │ │ └────────────────────────┘ │ │ │
│ │                                                       │   │ │ ┌─ C6 task row ─────────┐ │ │ │
│ │                                                       │   │ │ │◷  晚间回顾       [✎][⋯]│ │ │ │
│ │                                                       │   │ │ │   每天 21:00 · 明天     │ │ │ │
│ └───────────────────────────────────────────────────────┘   │ │ └────────────────────────┘ │ │ │
│                                                             │ │ C5.1 list empty/loading/   │ │ │
│                                                             │ │       error slot            │ │ │
│                                                             │ └─────────────────────────────┘ │
│                                                             │       transparent gap           │
│                                                             │ ┌─ C10 Diary Paper ──────────┐ │
│                                                             │ │ Diary                 2     │ │
│                                                             │ │ C10.1 diary entries          │ │
│                                                             │ └─────────────────────────────┘ │
│                                                             └─────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 任务行的点击区域

任务行用并列点击目标组成，避免在可点击 `article` 内嵌 button：

```text
┌─ C6 Task Row / one visual row ─────────────────────────────────────────────┐
│ ┌─ C6.1 Main row button ──────────────────────────────┐ ┌────┐ ┌────────┐ │
│ │ C6.1a status icon  C6.1b title                      │ │C6.2│ │ C6.3   │ │
│ │                     C6.1c status/schedule summary   │ │ ✎  │ │  ⋯     │ │
│ └─────────────────────────────────────────────────────┘ └────┘ └────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

- **C6.1**：整块主按钮；点击、Enter、Space 进入 `RESULT(taskId)`。
- **C6.2**：独立编辑按钮；阻止 C6.1 行为，打开 C9 Modal。
- **C6.3**：独立更多按钮；阻止 C6.1 行为，打开 C7 Menu。
- **C6.1a** 只作状态图形并 `aria-hidden`；C6.1c 提供可见文字状态。
- 活动中的 C6 使用整行浅色状态背景；普通 C6 不增加独立阴影。
- **C4.1** 是 `aria-hidden` 的入口识别图标，不响应点击；**C4.2** 是单行输入；**C4.3** 只在非空时可提交到新的 Chat 可编辑草稿。本轮不放置无可复用协议的麦克风。

### 2.3 更多菜单

```text
                                      ┌─ C7 Task Action Menu ──────────┐
                                      │ C7.1  ▷ 立即运行               │
                                      │ C7.2  ↗ 打开聊天 *             │
                                      │ C7.3  ◷ 执行历史               │
                                      │ C7.4  Ⅱ 暂停 / ▷ 恢复          │
                                      ├────────────────────────────────┤
                                      │ C7.5  删除                danger│
                                      └────────────────────────────────┘
                                      * 最新 trigger 有 target_thread_id 时出现
```

C7 是锚定 C6.3 的覆盖层，不占用列表高度。菜单项只调用既有 run/history/pause/resume/delete/thread navigation；不显示分享。

---

## 3. Calendar 宽屏：最近一次运行结果态

点击 C6.1 后，C3 的纸面边界与位置不变，C4/C5 被 C8 替换；C1 与 C10 不重排。

```text
┌─ C0 Calendar Dialog ────────────────────────────────────────────────────────────────────────┐
│ ┌─ C1 Calendar Paper / unchanged ─────────────────────┐   ┌─ C2 Right Card Stack ─────────┐ │
│ │ 月历内容                                              │   │ ┌─ C3 Scheduled Paper ──────┐ │ │
│ │                                                       │   │ │ C8 Result View             │ │ │
│ │                                                       │   │ │ ┌─ C8.1 Result header ───┐ │ │ │
│ │                                                       │   │ │ │[←] ◉ 每日整理笔记       │ │ │ │
│ │                                                       │   │ │ │ 每天 09:00 · 已完成     │ │ │ │
│ │                                                       │   │ │ │                 [✎][⋯] │ │ │ │
│ │                                                       │   │ │ └────────────────────────┘ │ │ │
│ │                                                       │   │ │ ┌─ C8.2 Result scroller ─┐ │ │ │
│ │                                                       │   │ │ │ 9 月 29 日 09:00         │ │ │ │
│ │                                                       │   │ │ │                            │ │ │ │
│ │                                                       │   │ │ │ Markdown final message     │ │ │ │
│ │                                                       │   │ │ │ 精确匹配 final_message_id │ │ │ │
│ │                                                       │   │ │ │ …长正文仅在此区域滚动…    │ │ │ │
│ │                                                       │   │ │ └────────────────────────────┘ │ │ │
│ │                                                       │   │ │ C8.3 Stable action footer      │ │ │
│ │                                                       │   │ │ [打开聊天] *        [重试] ** │ │ │
│ │                                                       │   │ └────────────────────────────────┘ │
│ └───────────────────────────────────────────────────────┘   │      transparent gap               │
│                                                             │ ┌─ C10 Diary Paper / unchanged ───┐ │
│                                                             │ │ Diary entries                    │ │
│                                                             │ └──────────────────────────────────┘ │
│                                                             └─────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────────────────────────┘

* 同一 trigger 有 target_thread_id 时显示。
** history/thread message 读取失败或结果暂不可用时显示。
```

### 3.1 C8 正文互斥状态

```text
C8.2
├─ R0 LOADING         [状态骨架 / polite status]
├─ R1 NEVER_RUN       [尚未运行；显示计划；无打开聊天]
├─ R2 CLAIMED/QUEUED  [正在准备 / 等待执行；显示计划时间]
├─ R3 RUNNING         [正在运行；显示最近更新时间]
├─ R4 SUCCEEDED       [精确 final message 的 Chat Markdown]
├─ R5 FAILED          [可行动错误 + 重试；target Thread 存在时可打开]
├─ R6 STATE_UNKNOWN   [结果待确认 + 刷新；不自动重新运行]
├─ R7 SKIPPED         [已跳过 + 服务端时间范围]
└─ R8 RESULT_MISSING  [结果尚不可用；不得回退其他 assistant message]
```

### 3.2 结果态返回和焦点

- 点击 C8.1 的返回按钮后回到 C5，并把焦点恢复到原 C6.1。
- 打开结果时焦点移动到 C8.1 标题或返回按钮；结果加载文案用 `aria-live=polite`。
- C8.2 是结果正文唯一滚动容器；C8.1 和 C8.3 保持可见。
- C8.3 “打开聊天”关闭 Calendar 后导航至同一 trigger 的 `target_thread_id`。

---

## 4. Calendar 编辑 Modal

C9 位于 Calendar 纸面之上；打开后 C0 内容不重排。Modal 不出现参考图中的每月、重复结束或通知。

```text
┌─ C9.0 Modal Backdrop / traps focus ─────────────────────────────────────────────────────────┐
│                                                                                             │
│          ┌─ C9 Edit Scheduled Task Modal / max-height: viewport ──────────────────┐          │
│          │ C9.1 Header                                                   [C9.2 ×] │          │
│          │ 每天                                                                    │          │
│          │ 编辑定时任务                                                            │          │
│          ├─────────────────────────────────────────────────────────────────────────┤          │
│          │ ┌─ C9.3 Modal body scroller ──────────────────────────────────────────┐ │          │
│          │ │ C9.4 标题                                                           │ │          │
│          │ │ [每日整理笔记……………………………………………………………………………] │ │          │
│          │ │                                                                     │ │          │
│          │ │ C9.5 提示词                                                        │ │          │
│          │ │ ┌─────────────────────────────────────────────────────────────────┐ │ │          │
│          │ │ │ 多行 prompt；长内容只在文本框内部滚动                           │ │ │          │
│          │ │ │                                                                 │ │ │          │
│          │ │ └─────────────────────────────────────────────────────────────────┘ │ │          │
│          │ │ C9.5e field error / optional                                      │ │          │
│          │ │                                                                     │ │          │
│          │ │ C9.6 频率        (●) 单次        ( ) 每天                          │ │          │
│          │ │                                                                     │ │          │
│          │ │ ┌─ C9.7a Once fields (once only) ────────────────────────────────┐ │ │          │
│          │ │ │ 日期 [2026-09-30]  时间 [09:00]  时区 [Asia/Shanghai ⌄]        │ │ │          │
│          │ │ │ 重复本地时刻有歧义时：[UTC+08:00 选项 ⌄]                      │ │ │          │
│          │ │ └─────────────────────────────────────────────────────────────────┘ │ │          │
│          │ │ ┌─ C9.7b Daily fields (daily only) ──────────────────────────────┐ │ │          │
│          │ │ │ 时间 [09:00]                  时区 [Asia/Shanghai ⌄]           │ │ │          │
│          │ │ └─────────────────────────────────────────────────────────────────┘ │ │          │
│          │ │                                                                     │ │          │
│          │ │ C9.8 Form/revision conflict message / optional                     │ │          │
│          │ └─────────────────────────────────────────────────────────────────────┘ │          │
│          ├─────────────────────────────────────────────────────────────────────────┤          │
│          │ C9.9 Stable footer              [暂停 / 恢复]     [取消] [保存]          │          │
│          └─────────────────────────────────────────────────────────────────────────┘          │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Modal 状态

```text
M0 PRISTINE  effective == desired     保存不可用；暂停/恢复按 effective status
M1 DIRTY     effective != desired     保存可用
M2 SAVING    request in flight        表单与动作防重复提交
M3 FIELD_ERR validation failed        desired 保留；错误靠近字段
M4 CONFLICT  revision changed         desired 保留；显示 latest effective 与重新确认
M5 API_ERR   capability/network fail  desired 保留；表单级重试
```

- C9.3 是短视口时的 Modal 内容滚动所有者；C9.1 与 C9.9 固定可达。
- C9.5 文本框可拥有更小的内部滚动，但滚轮到边界后交给 C9.3。
- `once` 与 `daily` 字段互斥；切换规则不生成协议外字段。
- 关闭、Escape 或取消后焦点返回触发该 Modal 的 C6.2 / C8 编辑按钮。
- 保存成功以后端返回 task 替换 effective；冲突不静默覆盖。

---

## 5. Calendar 窄屏与短视口

### 5.1 窄屏单列

```text
┌─ N0 Calendar Dialog / full viewport ──────────────┐
│ [Calendar]                                    [×] │
│ ┌─ N1 Canvas vertical scroller ─────────────────┐ │
│ │ ┌─ C1 Calendar Paper ───────────────────────┐ │ │
│ │ │ 月份 / 星期 / 日期格                     │ │ │
│ │ └───────────────────────────────────────────┘ │ │
│ │            transparent gap                    │ │
│ │ ┌─ C3 Scheduled Paper ──────────────────────┐ │ │
│ │ │ C4 arrange input                          │ │ │
│ │ │ C5 task list  /  C8 result (mutually)     │ │ │
│ │ └───────────────────────────────────────────┘ │ │
│ │            transparent gap                    │ │
│ │ ┌─ C10 Diary Paper ─────────────────────────┐ │ │
│ │ │ diary entries                             │ │ │
│ │ └───────────────────────────────────────────┘ │ │
│ └───────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

### 5.2 响应式关系

| 视口 | 布局 | 主滚动所有者 | 局部滚动 |
| --- | --- | --- | --- |
| 宽屏且高度充足 | C1 左，C2 右；C3/C10 为右侧卡栈 | C2 Right Card Stack | C8.2 结果；C9.3 Modal；prompt textarea |
| 宽屏但高度较短 | 两列不变，C1 高度受限 | C2 外滚动；必要时 C1 自身滚动 | C8.2、C9.3 |
| 窄屏 | C1 → C3 → C10 单列 | N1 透明画布 | C8.2 在结果最大高度内；C9.3 |
| 极窄屏 | 单列；任务行正文收缩 | N1 | 标题与摘要省略；按钮保持触控宽度 |

任何断点都不允许 C3 的内容高度改变 C1 的高度，也不允许页面横向滚动。

---

## 6. Chat：任务标记与右侧详情栏（桌面）

### 6.1 页面结构草图

```text
┌─ H0 Existing Chat Workspace ─────────────────────────────────────────────────────────────────┐
│ ┌─ H1 Conversation Column ─────────────────────────────────┐ ┌─ H4 Scheduled Detail Sidebar ┐ │
│ │ H1.1 Thread header                                      │ │ H5 Sidebar header            │ │
│ │ Chat title                                               │ │ 定时任务                  [×] │ │
│ ├───────────────────────────────────────────────────────────┤ ├──────────────────────────────┤ │
│ │ ┌─ H1.2 Message scroller ───────────────────────────────┐ │ │ ┌─ H4.1 Sidebar scroller ─┐ │ │
│ │ │ user message                                          │ │ │ │ H6 任务信息              │ │ │
│ │ │ assistant turn                                       │ │ │ │ 状态 / 完整 prompt       │ │ │
│ │ │ ├─ assistant Markdown                                │ │ │ ├──────────────────────────┤ │ │
│ │ │ ├─ Tool part                                         │ │ │ │ H7 Conversations         │ │ │
│ │ │ ├─ H2 Scheduled marker group                         │ │ │ │ 创建任务的会话       [›] │ │ │
│ │ │ │ ┌─ H3 Marker button ─────────────────────────────┐ │ │ │ │ 9 月 29 日执行会话    [›] │ │ │
│ │ │ │ │ [◷] 每日整理笔记                   [打开]     │ │ │ ├──────────────────────────┤ │ │
│ │ │ │ │     每天 09:00 · Asia/Shanghai                │ │ │ │ H8 任务周期              │ │ │
│ │ │ │ └───────────────────────────────────────────────┘ │ │ │ │ 频率 / 时间 / 时区       │ │ │
│ │ │ └─ message actions                                  │ │ │ │ 下次执行                 │ │ │
│ │ └───────────────────────────────────────────────────────┘ │ │ └──────────────────────────┘ │ │
│ ├───────────────────────────────────────────────────────────┤ └──────────────────────────────┘ │
│ │ H1.3 Existing Chat composer                              │                                  │
│ └───────────────────────────────────────────────────────────┘                                  │
└───────────────────────────────────────────────────────────────────────────────────────────────┘

* H7 首项使用 task.source_thread_id；后续项只使用拥有 target_thread_id 的 trigger，并按 created_at 倒序。
```

### 6.2 标记卡结构与识别边界

```text
Owning assistant turn
├─ Markdown body
├─ live Tool parts / refreshed message-process detail
├─ H2 marker group (strict create_scheduled_task successes only)
│  ├─ H3 marker button: tool part #1 scheduled_task.id
│  └─ H3 marker button: tool part #2 scheduled_task.id
└─ existing message actions
```

- H3 是单一 button；内部“打开”只是视觉尾标，不形成嵌套 button。
- H3 卡面显示 Tool 成功回执的标题和 once/daily 紧凑摘要。
- H3 点击只把真实 `scheduled_task.id` 交给 H4；H4 随后重读当前 effective。
- 刷新后的 history hydration 与实时 turn 使用同一个 Tool result 识别函数。
- Tool 失败、结果字段不完整或助手正文仅提到任务时，不生成 H3。
- 任务之后被暂停、结束或删除时，历史 H3 仍留在原 turn；H4 告知当前状态。

### 6.3 右侧栏互斥与滚动

```text
Chat side panel slot = exactly one of
├─ NONE
├─ SCHEDULED_TASK(taskId)  -> H4
├─ FILE(existing state)
├─ TASK_SESSION(existing state)
└─ SUBAGENT(existing state)
```

- H1.2 消息列表与 H4.1 详情内容分别滚动；打开 H4 不改变 H1.3 输入区的固定关系。
- H5 关闭后焦点返回打开它的 H3。
- H4 的 API 失败只替换 H4.1 为错误与重试；H1.2 和 H1.3 继续工作。
- H4 为只读详情；本轮不在侧栏复制编辑表单。
- 通用 `CreatedTaskSessionList` 只接收普通 TaskSession；scheduled trigger task session 由 Admin links 查询排除。

---

## 7. Chat：移动端详情 Drawer

```text
┌─ HM0 Chat viewport ─────────────────────────────┐
│ H1 conversation / retained underneath           │
│                                                 │
│ ┌─ HM1 Drawer backdrop ───────────────────────┐ │
│ │ ┌─ H4 Full-height task detail drawer ─────┐ │ │
│ │ │ H5 定时任务                         [×] │ │ │
│ │ ├─────────────────────────────────────────┤ │ │
│ │ │ H4.1 drawer scroller                    │ │ │
│ │ │ H6 任务信息：状态 / prompt              │ │ │
│ │ │ H7 Conversations：source / trigger      │ │ │
│ │ │ H8 任务周期：规则 / 时间 / IANA 时区    │ │ │
│ │ └─────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

- HM1 打开时阻止背景滚动；焦点限制在 H4，Escape/关闭后返回 H3。
- H3 在窄屏保持图标、标题/摘要与尾标；标题和摘要省略，不挤压触控目标。
- 中等宽度沿用现有侧栏策略，可覆盖或按既有最小宽度并列；不同时显示两个侧栏。

---

## 8. 加载、空态、错误与结果缺失结构

### 8.1 Calendar 局部状态

```text
C3 Scheduled Paper
├─ C3.1 header (always retained)
├─ C4 arrange input (LIST mode always retained)
└─ C5 content slot
   ├─ S0 LOADING   [row skeletons + polite status]
   ├─ S1 EMPTY     [尚无定时任务；使用上方安排入口]
   ├─ S2 READY     [C6 rows]
   └─ S3 ERROR     [任务暂时无法读取] [重试]

C8 Result View
├─ C8.1 header/back/actions (always retained)
├─ C8.2 state-specific body R0…R8
└─ C8.3 valid contextual actions
```

Day 请求失败时不把任务数显示为 0；C1 月历与 C10 Diary 继续可用。

### 8.2 Chat 侧栏状态

```text
H4 Scheduled Detail Sidebar
├─ D0 LOADING      [保留 H5 + 详情骨架]
├─ D1 READY        [H6 + H7 + H8]
├─ D2 API_ERROR    [标题快照 + 暂时无法读取 + 重试]
├─ D3 NOT_FOUND    [任务不存在或当前不可访问]
└─ D4 DELETED      [历史标记仍在；详情显示已删除]
```

### 8.3 Tool 标记状态

```text
Tool part
├─ pending/running                    -> 普通 Tool 呈现；无成功 H3
├─ completed + valid success payload  -> 普通 Tool 呈现 + H3
├─ completed + failure                -> 普通 Tool 错误；无 H3
└─ completed + malformed payload      -> 普通 Tool 呈现；无 H3；不阻断 hydration
```

---

## 9. 层级、滚动与焦点总图

### 9.1 覆盖层级

```text
Z4  C9 Edit Modal surface / modal focus trap
Z3  C9 modal backdrop
Z2  C7 anchored task menu
Z1  C1 / C3 / C10 floating papers on transparent C0 canvas
Z0  dimmed application page

Chat 内沿用既有 side panel / drawer 层级，不与 Calendar 同时打开。
```

### 9.2 滚动所有权

| 区域 | 宽屏 | 窄屏 | 禁止影响 |
| --- | --- | --- | --- |
| Calendar 月历 C1 | 默认固定；短高视口才自身滚动 | 随 N1 页面滚动 | 不被任务列表/结果撑高 |
| 右卡栈 C2 | 外层纵向滚动，包含 C3 与 C10 | 不存在独立列 | 不推动 C1 |
| 任务列表 C5 | 随 C2；不另造双滚动 | 随 N1 | 不把背景页作为滚动容器 |
| 结果正文 C8.2 | 自身滚动 | 受最大高度约束后自身滚动 | 头部、操作区、Diary |
| 编辑 C9.3 | Modal 内部滚动 | 同左 | Calendar 三张纸面 |
| prompt C9.5 | 文本框内部滚动 | 同左 | Modal 页脚 |
| Chat messages H1.2 | 自身滚动 | 自身滚动 | Composer H1.3 |
| Chat detail H4.1 | 自身滚动 | Drawer 自身滚动 | Chat messages/composer |

### 9.3 焦点恢复链

```text
Calendar opener -> C0 close -> Calendar opener
C6.1 row -> C8 heading/back -> back -> same C6.1
C6.2 edit -> C9 first field/heading -> close -> same C6.2
C6.3 more -> C7 first enabled item -> Escape/select -> same C6.3
C4 input -> submit -> new Chat draft input (text retained, unsent)
H3 marker -> H5 heading/close -> close -> same H3
```

菜单的上/下/Home/End 只遍历可用项；禁用项不接收焦点。状态不只依赖颜色。

---

## 10. 模块说明索引

| ID | 父级 | 模块 | 结构职责 | 点击/键盘目标 | 数据或协议来源 |
| --- | --- | --- | --- | --- | --- |
| C0 | Root | Calendar Dialog | 透明画布与遮罩 | Escape / C0.2 关闭 | 既有 CalendarPopup |
| C1 | C0 | Calendar Paper | 月份与日期选择 | 月份、日期键盘导航 | Calendar day state |
| C2 | C0 | Right Card Stack | 宽屏任务/Diary 外滚动 | 无直接动作 | CSS layout only |
| C3 | C2 | Scheduled Paper | 列表或结果的稳定纸面 | 无直接动作 | selected day |
| C4 | C3 | Arrange Task | 采集自然语言任务意图 | Enter / 发送进入新 Chat 草稿 | App / Chat draft callback |
| C5 | C3 | Task List | 容纳任务行和局部状态 | 无直接动作 | `getScheduledDay` |
| C6 | C5 | Task Row | 状态、标题、摘要、行尾动作 | 主体查看结果；铅笔；更多 | ScheduledTask + latest trigger |
| C7 | C6 | Action Menu | 既有任务操作集合 | run/chat/history/pause-resume/delete | scheduledTaskApi actions |
| C8 | C3 | Latest Result View | 读取与渲染最新 trigger 结果 | 返回、编辑、更多、重试、打开聊天 | history + actor scoped messages |
| C9 | C0 | Edit Modal | effective→desired 编辑 | 表单、暂停/恢复、保存、关闭 | edit + expected_revision |
| C10 | C2 | Diary Paper | 保留现有日记区域 | 现有 diary 动作 | Diary capability |
| N0 | Root | Narrow Calendar | 窄屏 dialog 边界 | 关闭 | responsive projection |
| N1 | N0 | Canvas Scroller | 窄屏三纸面单列滚动 | 滚动 | CSS layout only |
| H0 | Root | Chat Workspace | 对话与侧栏容器 | 既有 Chat 交互 | ChatView |
| H1 | H0 | Conversation Column | Thread、消息与输入 | 既有 Chat 动作 | Thread/messages/SSE |
| H2 | assistant turn | Marker Group | 将成功任务锚定到 owning turn | 无独立动作 | 实时 Tool parts 或有界 message-process 读取 |
| H3 | H2 | Marker Button | 展示创建快照并选择 task ID | click/Enter/Space 打开详情 | strict Tool success decoder |
| H4 | H0 | Scheduled Detail Sidebar | 展示任务信息、Conversations、任务周期 | 关闭、重试、打开会话 | get task + history |
| H5 | H4 | Sidebar Header | 命名与关闭 | 关闭 | selected task state |
| H6 | H4 | Task Information | 状态、标题、prompt | 只读 | ScheduledTask effective |
| H7 | H4 | Conversations | source 与各 trigger target Thread | 打开精确会话 | task.source_thread_id + ScheduledTrigger |
| H8 | H4 | Task Cycle | once/daily、日期/时间/时区、下次执行 | 只读 | ScheduledTask rule |
| HM1 | H0 | Mobile Drawer | 窄屏任务详情覆盖层 | 关闭、Escape | existing side panel responsive shell |

### 10.1 Calendar 子模块索引

| ID | 父级 | 子模块 | 结构与行为 |
| --- | --- | --- | --- |
| C0.1 | C0 | Dimmed background | 仅提供背景层级；Modal 打开时继续留在更低层 |
| C0.2 | C0 | Dialog close | 关闭 Calendar，并把焦点还给 Calendar opener |
| C1.1 | C1 | Month navigation | 上一月、当前月份、下一月 |
| C1.2 | C1 | Week headings | 七列星期表头 |
| C1.3 | C1 | Calendar grid | 日期选择、任务/日记标记与键盘导航 |
| C3.1 | C3 | Scheduled header | 所选日期、真实任务计数与需处理计数 |
| C4.1 | C4 | Leading plus | 装饰性入口图标，`aria-hidden`，不伪造附件菜单 |
| C4.2 | C4 | Arrange input | 单行自然语言输入；Enter 与 C4.3 等价 |
| C4.3 | C4 | Draft submit | 非空可用；关闭 Calendar 并进入新 Chat 可编辑草稿，不自动发送 |
| C5.1 | C5 | List state slot | 容纳 S0-S3，不移除 C3.1；LIST 模式保留 C4 |
| C6.1 | C6 | Main row button | 点击、Enter、Space 进入 C8 |
| C6.1a | C6.1 | Status icon | 装饰图形，`aria-hidden` |
| C6.1b | C6.1 | Task title | 单行标题，空间不足时省略 |
| C6.1c | C6.1 | Status/plan summary | 可见文字状态；活动 trigger 优先于计划摘要 |
| C6.2 | C6 | Edit button | 打开 C9；不触发 C6.1 |
| C6.3 | C6 | More button | 打开 C7；不触发 C6.1 |
| C7.1 | C7 | Run now | 复用 run action；请求中防重复 |
| C7.2 | C7 | Open Chat | 最新 trigger 有 target Thread 时出现 |
| C7.3 | C7 | History | 打开既有执行历史 |
| C7.4 | C7 | Pause/Resume | 按 effective status 二选一，并携带 revision |
| C7.5 | C7 | Delete | 危险分隔线后；沿用可撤销删除 |
| C8.1 | C8 | Result header | 返回、状态、标题、规则摘要、编辑、更多 |
| C8.2 | C8 | Result scroller | 容纳 R0-R8；成功时用现有 Chat Markdown |
| C8.3 | C8 | Result footer | 条件式打开聊天与重试；不遮挡正文 |
| C9.0 | C0 | Modal backdrop | 阻止背景交互并建立 Modal 焦点范围 |
| C9.1 | C9 | Modal header | 规则类型与“编辑定时任务”标题 |
| C9.2 | C9 | Modal close | 关闭并恢复焦点 |
| C9.3 | C9 | Modal body scroller | 短视口表单滚动所有者 |
| C9.4 | C9.3 | Title field | desired 标题 |
| C9.5 | C9.3 | Prompt textarea | desired prompt；长文本内部滚动 |
| C9.5e | C9.5 | Prompt field error | 对应字段错误，不清空输入 |
| C9.6 | C9.3 | Frequency selector | 只含 once / daily |
| C9.7a | C9.3 | Once fields | 日期、时间、IANA 时区；重复/无效当地时刻要求改用无歧义时刻，不生成候选偏移 |
| C9.7b | C9.3 | Daily fields | 时间与 IANA 时区 |
| C9.8 | C9.3 | Form message | revision 冲突或 API 错误；保留 desired |
| C9.9 | C9 | Modal footer | 暂停/恢复、取消、保存 |
| C10.1 | C10 | Diary entries | 既有日记列表与动作 |

### 10.2 Chat 子模块与状态索引

| ID | 父级 | 子模块/状态 | 结构与行为 |
| --- | --- | --- | --- |
| H1.1 | H1 | Thread header | 保持现有 Thread 标题与动作 |
| H1.2 | H1 | Message scroller | 独立滚动；包含 assistant turn、Tool part 与 H2 |
| H1.3 | H1 | Chat composer | 保持现有输入；侧栏失败不阻断发送 |
| H4.1 | H4 | Sidebar scroller | H6-H8 与 D0-D4 的滚动容器 |
| HM0 | Root | Mobile Chat viewport | H1 留在 Drawer 下方，不参与 Drawer 内容布局 |
| R0-R8 | C8.2 | Result body states | 加载、未运行、准备/排队、运行、成功、失败、待确认、跳过、结果缺失 |
| M0-M5 | C9 | Edit states | pristine、dirty、saving、字段错误、revision 冲突、API 错误 |
| S0-S3 | C5.1 | List states | 加载、空、就绪、错误 |
| D0-D4 | H4.1 | Detail states | 加载、就绪、API 错误、不存在/不可访问、已删除 |
| Z0-Z4 | C0 | Layer levels | 背景、悬浮纸面、菜单、Modal backdrop、Modal surface |

---

## 11. 模式互斥与点击去向矩阵

| 当前区域 | 触发 | 下一状态 / 去向 | 保持不变 |
| --- | --- | --- | --- |
| C3 `LIST` | C6.1 点击 | C3 `RESULT(taskId)` | C1、C10、Calendar grid 尺寸 |
| C3 `RESULT` | C8 返回 | C3 `LIST`，焦点回原任务行 | C1、C10 |
| LIST/RESULT | 编辑 | C9 Modal 覆盖 | 背后模式和滚动位置 |
| LIST/RESULT | 更多 | C7 Menu 覆盖 | 纸面高度 |
| C4 | 提交非空输入 | 关闭 Calendar；打开新 Chat 草稿 | 草稿不自动发送；不直接创建 task |
| C8/C7 | 打开聊天 | 关闭 Calendar；导航至最新 trigger target Thread | 不使用 source Thread 替代 |
| assistant turn | H3 点击 | `SCHEDULED_TASK(taskId)` 侧栏 | 当前 Thread 与输入草稿 |
| H4 | 点击关闭 | side panel `NONE`，焦点回 H3 | Chat 消息滚动位置 |
| H4 | 打开聊天 | 导航至最近 trigger target Thread | 使用精确 target Thread |
| H3 | 打开时已有其他侧栏 | 关闭旧侧栏并只显示 H4 | 不叠加侧栏 |

---

## 12. 禁止扩展的结构

以下元素不进入 Stage 3/4：

- 参考图中的麦克风、分享、推荐分组、分类标签和示例 emoji；
- 每周、每月、cron、重复结束与通知字段；
- Calendar 直接创建任务、自动发送 Chat 草稿；
- 从 assistant 文本或标题猜测 `scheduled_task.id`；
- 用 source Thread、最近 Thread 或最后一条 assistant message 替代 trigger 的关系 ID；
- 新的任务系统、消息 parser、Markdown renderer、Modal 框架或侧栏容器；
- 在页面显示 revision、claim、DTO、schema capability、内部 ID 或原始堆栈。

本结构稿的所有动作都落到现有 Task/Thread/Run/Tool、ScheduledTask API、持久化 Tool part、Thread messages、Chat Markdown、Modal 与侧栏布局。
