<!-- [Input] User-requested Codex.app task semantics, current once/daily scheduled-task behavior, and html-design-workflow evidence. -->
<!-- [Output] Current PRD for minute-interval schedules, task navigation, and scheduled-session note writes. -->
<!-- [Pos] Product source of truth for scheduled-task behavior across Chat and Calendar. -->
<!-- [Sync] 2026-10-07: define the visible completion receipt used when a successful scheduled turn ends after tools without model final text. -->
<!-- [Sync] 2026-10-07: bind scheduled note writes to the current Editor Session and close interval/recovery/UI semantics after independent review. -->

# 定时任务：分钟间隔与自动笔记工具 PRD

## 1. 背景与问题

当前定时任务可以创建一次性计划和每天固定时间计划，但无法表达“每隔 10 分钟检查一次”。Chat 中已经可以通过 `create_scheduled_task` 创建任务，Admin 已负责持久化定义、抢占、去重和恢复，Dream 已复用现有 TaskSession、Thread、Turn 与 Claude Agent 生产入口执行每次触发。

现有 Claude Agent 的 `tool_choice=auto` 表示模型可以自主选择已暴露工具；它没有授予写操作执行权限。编辑器写工具仍会进入前端确认链。定时任务在无人值守时无法完成用户已经在任务定义中明确委托的笔记写入。

本次将分钟间隔加入现有任务规则，并为定时任务启动的会话增加服务端拥有的逐工具审批策略。普通 Chat 的工具确认行为保持现状。

## 2. 目标与边界

### 2.1 目标

- Chat 自然语言可创建“每隔 N 分钟”任务，包含“每隔 10 分钟”。
- Calendar 和任务详情可正确展示、编辑、暂停、恢复、删除、立即运行和查看 interval 任务。
- 定时定义、下一次执行时间和运行历史持久化在 Admin PostgreSQL；进程重启后继续调度。
- 同一任务任意时刻最多一个 open trigger，避免重复并发。
- 定时会话可自动执行明确允许的笔记写入工具；删除、问答、Shell 和其他写操作继续要求人工确认并在无人确认时失败。
- 每次触发继续创建独立 TaskSession、Thread 和 Turn，历史结果可打开对应 Chat。

### 2.2 边界

- 本期规则为 `once`、`daily`、`interval`；不增加 cron 编辑器、每周/月历法或通用工作流编排。
- `interval_minutes` 是正安全整数。10 分钟是用户输入示例，不是硬编码配额或默认值。
- interval 按绝对分钟间隔运行；`time_zone` 用于创建上下文和页面展示，不因夏令时改变间隔长度。
- 不新增 Dream 数据表、runtime DDL、消息队列、第二套 Run 或第二套会话状态机。
- 不允许浏览器、任务 prompt、Deck、Plugin、workspace 或用户环境覆盖定时会话工具审批策略。
- 从带笔记上下文的 Chat 创建任务时，服务端捕获该次请求已校验的当前 Editor Session 作为目标笔记；纯 Chat 创建的任务不隐含笔记目标。目标标识由 Admin 持久化，prompt、浏览器后续状态和“最近打开”记录不能改写它。
- 自动写入只作用于上述目标笔记；目标曾存在但后来删除、越权或无法加载时，本次运行失败，不选择其他笔记。没有目标的纯 Chat 任务可以正常产出会话结果，但不注册 Editor 工具。

## 3. 概念与规则

### 3.1 配置语义

| 概念 | 定义 |
|---|---|
| default | 尚未创建任务。表单可显示示例占位，但不产生隐含规则。 |
| desired | 用户在编辑弹窗内尚未保存的草稿。 |
| effective | Admin 事务成功提交的任务定义；调度器只读取此定义。 |
| revision | effective 定义的正整数版本；编辑、暂停、恢复、删除、还原使用 expected revision 比较。 |

保存成功即产生新的 effective revision。本期不增加单独的 desired 存储或异步“配置应用”状态。

### 3.2 调度规则

| kind | 输入 | 下一次执行 |
|---|---|---|
| `once` | `local_date`、`local_time`、`time_zone`、必要时的重复时刻偏移 | 指定未来本地时刻；完成后进入 `exhausted`。 |
| `daily` | `local_time`、`time_zone` | 每个当地日一次；缺失的夏令时时刻跳过，重复时刻选择现行既有规则。 |
| `interval` | `interval_minutes`、`time_zone` | 创建、编辑或恢复时以数据库时钟为起点，`next_run_at = now + interval`；后续沿持久化时间格推进。 |

interval 服务恢复规则：若恢复时已经错过多个时间点，只为最近一个到期点创建一次 trigger；更早的到期范围写入该 trigger 的 `skipped_from_at` / `skipped_through_at`，下一次时间推进到当前时间之后。

### 3.3 并发与重复触发

open trigger 指 `claimed`、`queued`、`running`、`state_unknown`。数据库唯一约束保证一个任务最多一个 open trigger。新到期点遇到 open trigger 时不启动第二个 Claude turn，只推进 `next_run_at`，并以最早的 `skipped_from_at` 和最晚的 `skipped_through_at` 累积跳过范围。暂停、编辑和删除只影响后续 claim，不取消已经绑定的 turn。

`state_unknown` 不重放模型。worker 按服务端固定节流周期重新读取目标 Thread 的持久化终态：找到对应 final 后转为 `succeeded`，找到明确失败证据后转为 `failed`，仍无证据则更新时间并保持 `state_unknown`，页面提供“打开聊天”。长期 unknown 继续占用一个 open trigger，因此后续到期点只累计 skipped 范围。

定时 turn 可能在工具成功后不再生成自然语言正文，例如用户明确要求“只写入笔记”。此时 Dream 在持久化同一 assistant turn 时追加服务端完成回执“任务已执行完成。”，保留工具输入与结果，并生成现有 final projection。该回执只用于已经由 Claude Runtime 判定成功、且没有非空 final text 的 scheduled turn；工具拒绝、Runtime 错误和取消不得使用该回执变成成功。Calendar 最近结果和“打开聊天”均读取这条持久结果。

### 3.4 工具暴露与审批

CLI `tools`、MCP server 注册和 Dream 当前的 `allowed_tools` 共同决定实际可用工具集合；`tool_choice` 决定普通 turn 的产品模式；PreToolUse / `can_use_tool` 决定一次调用是否执行。三个判断彼此独立，`tool_choice=auto` 不等于自动执行写工具。

| 会话来源 | 工具 | 审批枚举 | 行为 |
|---|---|---|---|
| 普通 Chat | 全部已暴露工具 | 继续使用 turn 的 `auto/manual/none` | 保持现有前端确认语义。 |
| 定时任务 | `mcp__editor__write_segment` | `auto` | 在现有 Editor Session/权限校验通过后自动替换笔记片段。 |
| 定时任务 | `mcp__editor__insert_widget` | `auto` | 在现有 Editor Session/权限校验通过后自动新增笔记内容组件。 |
| 定时任务 | `mcp__editor__delete_segment` | `manual` | 无人值守 turn 立即拒绝，本次运行失败。 |
| 定时任务 | `mcp__editor__reply_to_comment` | `manual` | 无人值守 turn 立即拒绝，本次运行失败。 |
| 定时任务 | `AskUserQuestion`、`mcp__user__ask_user` | `manual` | 无人值守 turn 立即拒绝，不等待不可恢复的内存确认。 |
| 定时任务 | `Bash`、外部 MCP 写工具及未列出的写操作 | `manual` | 无人值守 turn 进入确认分支时立即拒绝；不扩大执行范围。 |

服务端策略是现有 `auto` 分类器上的精确覆盖：两个 Editor 工具为 `auto`，明确敏感工具为 `manual`；未命中的只读工具仍使用现有低敏感分类，任何最终落入确认分支的调用在定时 turn 中立即拒绝。Editor Session ID、actor、Thread、Admin delegation、输入 schema、workspace、network 与 Dream surface 拒绝均先于自动覆盖。定时 turn 忽略浏览器 full access 的扩大效果，`can_use_tool` 网络请求也直接 fail closed。

## 4. 用户交互流程

1. 用户在 Chat 输入“每隔 10 分钟检查项目进度，并把摘要写入当前笔记”。
2. Claude 调用 `create_scheduled_task`，rule 为 `interval`、`interval_minutes=10`、当前 IANA 时区。
3. 创建成功后，assistant turn 显示任务标记卡，包含标题、`每 10 分钟` 和“打开”。
4. 点击标记卡，在桌面右侧打开任务详情；窄屏打开全高 sheet。
5. 详情展示任务信息、运行周期、状态、下一次运行、最近结果与 Conversations。
6. 点击编辑，用户可在同一弹窗切换单次、每天、间隔；间隔模式显示正整数分钟输入。
7. 到期时系统创建新的执行 Thread；允许的笔记写工具无需确认，其他工具按 `manual` 处理。
8. 用户点击某次运行查看结果，点击“打开聊天”进入该 trigger 的 `target_thread_id`。
9. 暂停后不创建新 trigger；恢复后从恢复时数据库时钟重新计算下一次 interval。

## 5. 页面信息架构与骨架

### 5.1 桌面

```text
┌──────────────────────── Chat（独立滚动） ───────────────────────┬──────── 任务详情（独立滚动） ────────┐
│ 对话消息                                                       │ [时钟] 任务标题              [关闭] │
│                                                               │ 每 10 分钟 · 已开启                  │
│ ┌─ assistant 结果 ──────────────────────────────────────────┐ │                                        │
│ │ 已创建定时任务                                             │ │ 任务信息                               │
│ │ ┌ [时钟] 项目进度检查      每 10 分钟        [打开] ┐      │ │  提示词 / 状态 / 下次运行              │
│ │ └──────────────────────────────────────────────────┘      │ │                                        │
│ └───────────────────────────────────────────────────────────┘ │ 任务周期                               │
│                                                               │  类型：间隔    每隔：10 分钟           │
│ 输入区固定在 Chat 底部                                        │                                        │
│                                                               │ Conversations                          │
│                                                               │  最近结果摘要            [打开聊天]    │
│                                                               │  历史运行列表                           │
└───────────────────────────────────────────────────────────────┴────────────────────────────────────────┘
                                                    编辑弹窗覆盖详情区或居中显示
                                    ┌─────────────────────────────────────────┐
                                    │ 间隔 / 标题 / 提示词                     │
                                    │ 频率 [每隔]  [10] [分钟]                │
                                    │ 重复结束 [永不]                          │
                                    │                         [暂停] [保存]    │
                                    └─────────────────────────────────────────┘
```

Chat 列与任务详情列各自滚动。任务详情只有一个正文滚动区，历史分页追加到该区域；不再增加 Conversations 内部嵌套滚动。详情高度变化不得撑高相邻 Chat 或 Calendar。

### 5.2 Calendar 桌面

```text
┌──────── Calendar 弹层（固定视口） ───────────────────────────────────────────┐
│ ┌──────── 月历卡（不随右栏增长） ────────┐  ┌──── 当日内容（单一外滚动） ────┐ │
│ │  <       2026 年 10 月        >       │  │ 今天 · 2 篇                    │ │
│ │  日 一 二 三 四 五 六                  │  │                                │ │
│ │  日期格 / 任务与日记圆点               │  │ 定时任务                        │ │
│ │                                       │  │ ┌ 每 10 分钟检查项目   [•••] ┐ │ │
│ │                                       │  │ └ 下次运行 / 最近状态         ┘ │ │
│ │                                       │  │                                │ │
│ │                                       │  │ 日记                            │ │
│ │                                       │  │ ┌ 12:00 当前笔记  Untitled ┐   │ │
│ └───────────────────────────────────────┘  │ └──────────────────────────┘   │ │
│                                            └────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
```

左右两张卡悬浮分离。右侧 section 自身纵向滚动，月历卡保持固定；任务列表、错误反馈和日记都在右侧同一个滚动容器内。

### 5.3 窄屏

```text
┌────────────────────────── Chat ──────────────────────────┐
│ 消息流（页面滚动）                                       │
│ ┌ [时钟] 项目进度检查                                   │
│ │ 每 10 分钟                                  [打开]    │
│ └───────────────────────────────────────────────────────┘
│                                                         │
│ 输入区固定                                               │
└─────────────────────────────────────────────────────────┘

点击“打开”后：
┌────────────── 全高任务详情 sheet（自身滚动） ─────────────┐
│ [返回]  项目进度检查                         [更多]      │
│ 状态 / 下次运行                                          │
│ 任务信息                                                 │
│ 任务周期：每隔 10 分钟                                   │
│ 最近结果                                                 │
│ Conversations                                            │
│ 运行历史                                                 │
│ [编辑] [立即运行]                                        │
└─────────────────────────────────────────────────────────┘
```

Calendar 窄屏按顺序显示月历卡和当日内容卡；当日内容卡自身滚动，任务行与日记行保持分卡样式，不把月历高度随内容撑开。

## 6. 状态与反馈

- 创建/保存成功：任务卡和详情使用服务端返回的 effective definition。
- `SCHEDULE_REVISION_CONFLICT`：保留用户草稿，刷新最新 definition，提示用户重新保存。
- capability 缺失：显示“定时任务暂不可用”和重试；不降级为进程内 timer。
- 工具需要人工确认但定时会话无人处理：本次 turn 记录明确失败结果；任务定义保持 active，后续仍按计划触发。
- Editor Session/权限缺失：显示本次运行无法写入目标笔记，并提供“打开聊天”查看原因。
- `state_unknown`：不重复执行同一次 turn；worker 节流重查持久化结果，页面持续提供对应 Chat 入口。
- 成功的定时 turn 只有工具结果、没有模型正文：显示“任务已执行完成。”，并允许打开对应 Chat 查看完整工具过程。

## 7. 验收标准

- Chat Tool 可以创建 `interval_minutes=10` 的任务并收到严格回执。
- Admin 重启与 Dream 重启后，任务仍从持久化 `next_run_at` 恢复。
- 到期后创建一个真实 TaskSession/Thread/Turn；同任务无并发重复执行。
- 仅含成功工具调用的定时 turn 仍落库为 `succeeded`，最近结果显示服务端完成回执；失败或拒绝不得被该回执掩盖。
- 定时会话自动允许 `write_segment` 和 `insert_widget`，普通 Chat 相同工具仍按现有确认策略。
- 定时会话不会自动允许 delete、comment reply、AskUserQuestion、Bash 或未知写工具。
- Calendar/Chat 任务卡、详情、编辑和历史正确展示“每 10 分钟”。
- 编辑 revision 生效、暂停不触发、恢复重新计划、删除不触发、立即运行保留既有语义。
- 完整回归覆盖普通 Chat、Tool 发起 Thread、resume、cancel、SSE 与普通工具确认。

## 8. 关联设计与过程证据

- 正式交互设计：[interval-scheduling-and-tool-approval.md](../../design/scheduled-tasks/interval-scheduling-and-tool-approval.md)
- 设计评审：[interval-scheduling-review.md](../../design/scheduled-tasks/interval-scheduling-review.md)
- html-design-workflow 产物：[workflow-20261007](../../design/scheduled-tasks/workflow-20261007/)
- 既有 Calendar/日记范围稿保留在 `docs/prd/claude-agent/scheduled-task-diary-page-prd.md`，不作为本次 interval 与工具审批规则的当前来源。
