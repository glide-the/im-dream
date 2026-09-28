<!-- [Input] 2026-09-29 现行日记日期弹窗 PRD/UI/系统设计、Agent.md 前置门禁，以及定时任务前后端与浏览器测试源码。 -->
<!-- [Output] 代码先于 PRD 情况下的独立设计评审、P0 关闭结果、剩余 P1/部署风险和“需求—PRD—系统设计—当前实现—测试”追踪矩阵。 -->
<!-- [Pos] 定时任务日记日期弹窗的独立实施门禁；不替代 PRD、UI 设计、系统设计或阶段四技术回执。 -->
<!-- [Sync] 2026-09-29: 生产页面、移动入口和四条浏览器旅程关闭首次评审 P0；保留首次评审快照，正常 capability 发布与真实业务验收仍独立。 -->
<!-- [Sync] 2026-09-29: 复评确认 exhausted、A3 diary-only、claim/prepare 与文档导航已经收敛，设计结论升级为可直接实施。 -->
<!-- [Sync] 2026-09-29: 首次评审 html-design-workflow 正式产物与既有实现，结论为收敛后实施。 -->

# 定时任务日记日期弹窗 PRD 独立评审（2026-09-29）

## 1. 结论

**评审结论：可直接实施（设计基线）。**

现行 PRD、UI 设计和系统设计已经回答“用户如何在日记日期内查看和管理定时任务”，并覆盖创建、展示、计划或手动触发、共享 Chat 执行、历史、配置操作、重启、并发和未知结果。首次评审要求收敛的三项已经闭合：`exhausted` 不再允许编辑，A3 首期只展示日记标记且月摘要后置，`claim`/`prepare` 返回值与真实 DTO 一致。系统设计仍完整保留四张业务时序图和两张状态图。

当前工作树已经按该设计关闭首次评审的页面与浏览器测试 P0：日期摘要按日记、任务和需处理项分别计数，任务分组位于日记之前；编辑使用最新 effective/revision 处理冲突；`state_unknown` 禁止盲目新建运行；删除使用原位撤销；桌面和 390×844 移动入口、菜单键盘与目标 Thread 导航均有生产组件 E2E。这个结论仍不代表正常数据库 capability 已发布，也不代表真实账户、真实模型或部署验收完成。

## 2. 评审快照与边界

- 首次评审源码基线：`d15b918ff5d11bb194bad027f49d649fa06eb087`。当前复核基线：`29ad545d` 加 2026-09-29 日记页 PRD/UI 工作树改动，均位于 detached worktree。
- 首次评审只修改评审文档；其后实现阶段修改 `CalendarPopup`、`scheduledTaskApi`、i18n、移动 Calendar 入口、E2E 与受影响目录文档。本节保留两个时点，避免把首次发现改写成当时已完成。
- `html-design-workflow` 的 Stage 1–4 产物已由正式 PRD/UI 文档建立现行合同；本评审核对合同内容，不把原型等同生产实现。
- 当前关闭结论使用 fixture 浏览器测试、Dream 后端测试和隔离 PostgreSQL 跨仓旅程；这些属于技术验收，不描述为正常账户真实业务验收。

## 3. 前置门禁判断

| 门禁项 | 证据 | 判断 |
| --- | --- | --- |
| 代码先于 PRD 的补救流程 | [`Agent.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/Agent.md:117) 要求先有 PRD；第 126–128 行要求独立评审并记录剩余差距 | 历史顺序无法改变；现已完成 PRD、交互设计、独立评审和差距记录，可进入实施 |
| 页面信息架构 | PRD 定义 B1 日期摘要、B2 定时任务、C1 日记，并固定“日期摘要 → 定时任务 → 日记”，见 [`scheduled-task-diary-page-prd.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-prd.md:84)；生产实现见 [`CalendarPopup.tsx`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:665) | 设计与代码满足 |
| 完整流程与业务时序 | 系统设计四张时序图起于 [`70`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:70)、[`116`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:116)、[`195`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:195)、[`269`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:269) | 创建展示、触发执行、配置操作、重启并发均完整 |
| 状态与恢复 | 系统设计定义状态图和触发状态图起于 [`330`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:330)、[`351`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:351) | 后端状态机与页面关键操作满足；长驻弹窗自动刷新仍为 P1 |
| DTO、权限、幂等与并发 | 系统设计在第 136–143 行区分 claim/prepare，在第 368–379 行定义数据和接口边界 | 与当前 DTO/operation 对齐 |
| 响应式和可访问性 | PRD 第 272–305 行；UI 设计第 670–712 行；移动入口见 [`App.tsx`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/App.tsx:1829) | 390×844 单列、dialog、焦点、日期网格与菜单键盘旅程通过 |
| 新评审导航 | PRD、UI、系统设计分别链接本文 | 链接完整；本轮同步为“最小纵向切片技术验收通过” |

## 4. 设计符合性与范围判断

### 4.1 已形成可实施合同

1. **日期内查看和管理。** 任务在日记之前，日期摘要分别计数，历史属于具体任务卡，见 [`scheduled-task-diary-page-prd.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-prd.md:93) 与第 106–112 行。
2. **创建到结果闭环。** 时序一、二连接 Chat Tool、Admin 持久化、日期读取、领取、TaskSession/Thread、Claude turn 与 final 核对，见 [`scheduled-task-loop-interaction-design.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:67) 与第 113 行。
3. **配置操作。** 时序三按真实 operation 定义编辑、暂停、恢复、立即运行、删除、撤销和 revision 冲突，见 [`scheduled-task-loop-interaction-design.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:192)。
4. **重启、并发和未知结果。** 时序四覆盖双 worker、start 前退出、start 回执丢失、续租失败和 `state_unknown` 对账，见 [`scheduled-task-loop-interaction-design.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:266)。
5. **页面状态具体。** UI 设计包含页面结构、组件合同、默认/编辑/历史/删除撤销/局部错误、宽窄屏和键盘行为，见 [`scheduled-task-diary-page-ui-design.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-ui-design.md:30)、第 652–712 行。

### 4.2 三项设计收敛复核

1. **`exhausted` 语义已经统一。** PRD 明确 `exhausted` 仅允许立即运行、查看历史、删除，第 154 行禁止编辑并要求重新排期新建定义；见 [`scheduled-task-diary-page-prd.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-prd.md:140) 与第 154、208、250–255 行。UI 菜单和组件合同一致，见 [`scheduled-task-diary-page-ui-design.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-ui-design.md:509) 与第 550、662–663 行。系统正文、时序、状态图和验收均拒绝 exhausted 编辑，见 [`scheduled-task-loop-interaction-design.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:58)、第 253、325、334–346、397–399 行。**首次矛盾已闭合。**
2. **A3 首期 diary-only，月摘要后置。** PRD 的非目标、功能、技术建议和后续事项分别在 [`56`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-prd.md:56)、[`120`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-prd.md:120)、[`335`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-prd.md:335)、[`377`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-prd.md:377) 固定该范围。UI 原型与规范没有任务菱形，见 [`scheduled-task-diary-page-ui-design.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-diary-page-ui-design.md:59)、第 712、1355 行。系统设计第 410 行把 owner-filtered 月摘要 operation 留作后续。**首次缺口已闭合，没有为首期新增月接口。**
3. **claim/prepare DTO 表述已修正。** 系统时序中 claim 只返回 `trigger + claim_id`，prepare 才返回 `authority_token + authority_expires_at`，见 [`scheduled-task-loop-interaction-design.md`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/docs/design/claude-agent/scheduled-task-loop-interaction-design.md:136) 与第 141–143 行。真实 [`ClaimScheduledTriggerResultDTO`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/services/admin_data/scheduled_task_data.py:141) 只有 `trigger`、`claim_id`；[`PrepareScheduledTriggerResultDTO`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/services/admin_data/scheduled_task_data.py:151) 才有授权与到期时间。**设计与 DTO 对齐。**
4. **图表和评审链接仍完整。** 系统设计精确包含四个 `sequenceDiagram`（第 70、116、195、269 行）和两个 `stateDiagram-v2`（第 330、351 行）；三份现行设计均链接本文。不存在因收敛删除正常流程、失败分支或状态转换的情况。

### 4.3 范围没有过度设计

- 创建入口仍在 Chat Tool，日期弹窗不新增第二个创建入口。
- 复用 `CalendarPopup`、`scheduledTaskApi`、现有 Chat 导航和 Admin operation，不建立平行页面、任务模型或状态机。
- 页面不计算 `next_run_at`，不从 SSE、缓存或浏览器存储推断终态。
- 首期只支持单次和每日；月摘要、周/月/Cron、继续原 Thread 和运行中远程取消均后置。
- `state_unknown` 使用后端持久事实并限制盲目重跑，没有引入推断百分比或浏览器补偿调度。

## 5. 首次评审 P0 差距（历史快照，已关闭）

以下 P0-1 至 P0-6 保留首次评审原始发现，便于复核“为什么修改”。它们描述的是 `d15b918f` 时点，不再代表当前工作树。当前关闭证据如下：

| 首次差距 | 当前关闭证据 | 验证 |
| --- | --- | --- |
| P0-1 信息架构 | [`CalendarPopup.tsx`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:665) 按日期摘要、任务、日记渲染；无任务时省略任务组 | E2E 第 278–287、390–397 行 |
| P0-2 状态与未知结果 | 卡片区分 definition 和最近 trigger；`state_unknown` 禁用立即运行并提供核查路径 | E2E 第 339–367、376–387 行 |
| P0-3 desired/effective/revision | 编辑从 effective 建草稿，revision 冲突保留 desired 并展示 latest effective | E2E 第 289–301 行 |
| P0-4 操作与反馈 | 主操作、更多菜单、原位撤销、确定失败和 outcome unknown 分流 | E2E 第 303–334、376–387 行 |
| P0-5 响应式与可访问性 | production `Modal`、日期 grid、菜单键盘、焦点恢复、移动 Calendar 入口和单列 CSS | E2E 第 339–373 行 |
| P0-6 正式旅程 | 重写为四条 production-shaped API/组件旅程 | `4 passed (15.4s)` |

### P0-1：核心信息架构仍与 PRD 相反

- 当前 [`CalendarPopup`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:642) 只显示日记计数；第 682 行先渲染日记，到第 796 行才渲染任务，没有 B1/B2/C1 分组。
- 最小改动：在现有弹窗内重排为日期摘要、定时任务、日记，并分别显示日记数、任务数和需处理数；任务失败不应阻断日记。

### P0-2：状态层级和未知结果操作不足

- [`displayTriggers`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:108) 默认渲染单日返回的全部 trigger；第 153 行只按定义状态显示立即运行，`state_unknown` 不会禁止新请求；第 162 行仅把未知结果当一行文字。
- [`i18n.ts`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/i18n.ts:1365) 把定义 `active` 写为“待执行”，没有区分定义已启用与最近执行状态。
- 最小改动：默认只显示最近执行摘要，完整历史二级展开；按触发状态派生可用操作并禁止 `state_unknown` 盲目重跑。

### P0-3：编辑没有完成 default/desired/effective/revision 交互

- 卡片草稿只在组件初始化时从 task 取值；revision 冲突在 [`actOnTask`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:222) 重读 latest 后只显示通用错误，没有标记 desired 与 effective 差异。
- 请求层只保留错误码，见 [`scheduledTaskApi.ts`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/api/scheduledTaskApi.ts:53)；路由 DTO 错误统一为 `SCHEDULE_INPUT_INVALID`，见 [`claude_agent.py`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/routers/claude_agent.py:1484)。当前单次表单还在 [`CalendarPopup.tsx`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:141) 暴露任意偏移分钟。
- 最小改动：每次进入编辑都以最新 effective 建 default 并复制 desired；冲突保留 desired、展示 latest effective 差异和明确重试路径；用可验证候选替代任意 DST 偏移输入。

### P0-4：操作层级、删除撤销和结果不明反馈仍是旧交互

- [`CalendarPopup.tsx`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:148) 把编辑、暂停/恢复、立即运行、删除和历史作为等权按钮；第 155 行删除后仍保留完整卡片；第 128 行没有为空的 `next_run_at` 显示原因。
- [`actOnTask`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:224) 虽保存稳定 `manual_request_key`，页面没有区分确定失败与 `outcome_unknown`。
- 最小改动：按 B4/B5 分主次操作，删除成功改原位撤销条，解释无下次时刻，并在原请求结果明确前保留同一 key 和“正在确认”状态。

### P0-5：响应式和可访问性没有落实

- 根遮罩没有 dialog 语义、可读标题、焦点约束、Escape 或焦点恢复，内层却是 `role="presentation"`，见 [`CalendarPopup.tsx`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:389)。
- 左栏固定 460px，见第 420–425 行；没有中窄屏单列、日期网格键盘语义、明确关闭按钮或包含任务标题的操作名称。
- 最小改动：按 UI 合同实现对话框、显式关闭、焦点进入/环回/恢复、Escape 分层、日期键盘导航和窄屏单列。

### P0-6：E2E 仍验证旧页面

- [`scheduled-task-calendar.spec.ts`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/e2e/scheduled-task-calendar.spec.ts:26) 的 Trigger 只有 `failed | succeeded`；第 183–226 行仅跑 1440×900 的旧旅程。
- 测试没有断言任务先于日记、A3 无任务标记、分别计数、`exhausted` 无编辑、`state_unknown` 禁止重跑、冲突差异、Thread 导航、窄屏、键盘、焦点、局部失败或删除撤销条。
- 最小改动：继续走生产组件/API，补桌面、窄屏、键盘和各关键状态旅程；不得复制 reducer 或放宽断言。

## 6. P1 差距与部署风险

1. **A3 已关闭。** 当前月份日期只来自日记，且 E2E 第 287 行断言仅有任务的日期没有日记标记。
2. **历史分页未消费 cursor。** 后端支持 `before_created_at`，见 [`scheduled_task_data.py`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/services/admin_data/scheduled_task_data.py:110)；前端 [`getScheduledHistory`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/api/scheduledTaskApi.ts:75) 只发送 limit。
3. **客户端 action 类型已关闭。** `scheduledTaskApi` 分开 `ScheduledDefinitionAction`、`ScheduledRunAction` 和对应 result，页面按 operation 消费。
4. **卡片仍缺自动刷新策略。** 日期读取只随日期、时区或本地 refresh nonce 触发；页面长时间停留时 queued/running 不会自动进入终态。首期保留明确手动核查，后续可在仅有非终态 trigger 时做有界刷新。
5. **展示时区已关闭。** 初始化、今天标记和任务读取共用传入的 IANA timezone。
6. **Thread 导航已关闭。** E2E 第 331–334 行验证关闭弹窗、进入 Chat 并消费精确目标 Thread ID。
7. **DST 歧义候选仍缺上游合同。** 当前编辑可提交 IANA timezone 与本地日期/时间，但 Admin 没有返回歧义候选供用户选择；遇到非法或无法解释的输入必须 fail closed，不能由浏览器猜 UTC 偏移。
8. **正常 capability 仍是启用门槛。** 隔离跨仓旅程已经通过；正常目标 PostgreSQL capability 未证明已发布。真实账户、真实模型和部署验收不能由 fixture 或隔离库替代。
9. **交付归位尚未完成。** Dream 当前 PRD/UI 纵向切片尚未提交；Admin 实现在 detached worktree `9ed8fc0`，尚未进入 Admin `main` 或正式交付分支。

## 7. DTO 与 operation 对齐检查

| 合同 | 设计 | 当前实现 | 结论 |
| --- | --- | --- | --- |
| 单次/每日 rule | 系统设计第 40–52 行 | [`ScheduledRuleDTO`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/services/admin_data/scheduled_task_data.py:25)；[`ScheduledRule`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/api/scheduledTaskApi.ts:8) | 对齐 |
| definition / trigger 状态 | 系统设计第 325–366 行 | [`ScheduledTaskDTO`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/services/admin_data/scheduled_task_data.py:42)；[`ScheduledTriggerDTO`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/services/admin_data/scheduled_task_data.py:56) | 对齐 |
| 日期、历史与 mutation | `scheduled-task.day/history/edit/pause/resume/delete/restore/run` | operation 注册见 [`scheduled_task_data.py`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/services/admin_data/scheduled_task_data.py:219)；路由见 [`claude_agent.py`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/routers/claude_agent.py:1450) | 对齐；历史分页 cursor 后置 |
| 领取与准备 | claim 返回 trigger/claim_id；prepare 返回资产、授权和到期时间 | DTO 见 [`141`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/services/admin_data/scheduled_task_data.py:141)、[`151`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/services/admin_data/scheduled_task_data.py:151)；worker 在 [`_poll`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/claude_agent/scheduled_task_coordinator.py:74) 与 [`_dispatch`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/claude_agent/scheduled_task_coordinator.py:165) 消费 | 设计与实现对齐 |
| start / finish / reconcile | 模型前绑定 turn；合法 final 才 succeeded；未知结果对账 | [`_dispatch`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/claude_agent/scheduled_task_coordinator.py:223) 与第 254–260 行；operation 第 232–234 行 | 对齐 |
| `exhausted` 编辑 | UI 隐藏，服务端拒绝，重新排期新建 | 当前 UI 隐藏编辑；Dream 透传 Admin edit operation | 页面与服务端合同对齐；移动 E2E 锁定菜单不显示编辑 |

## 8. “需求—PRD—系统设计—当前实现—测试”追踪矩阵

| 需求 | PRD | 系统设计 | 当前实现 | 当前测试 | 评审状态 |
| --- | --- | --- | --- | --- | --- |
| Chat Tool 创建单次/每日任务 | 第 49–57 行 | 时序一第 67–109 行 | [`_ThreadToolTurnProvider._perform`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/routers/claude_agent.py:2108) | [`test_scheduled_tool_uses_current_turn_grant_and_stable_call_key`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/tests/test_scheduled_task_consumer.py:55) | 技术合同已覆盖 |
| 选中日期展示任务与日记 | 第 84–112、124–129 行 | 时序一第 95–106 行 | [`CalendarPopup`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/frontend/app/_dream/components/CalendarPopup.tsx:665) | E2E 第 278–287、390–397 行 | 已覆盖顺序、分组、计数和无任务日期 |
| A3 首期 diary-only、月摘要后置 | 第 56、120、335、377 行 | 第 410 行 | 月份日期只来自日记数据 | E2E 第 287 行 | 对齐并锁定 |
| 到期领取并执行 Claude turn | 验收第 397–399 行 | 时序二第 113–190 行 | [`ScheduledTaskCoordinator._poll`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/claude_agent/scheduled_task_coordinator.py:74)、[`_dispatch`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/claude_agent/scheduled_task_coordinator.py:165) | [`probe_scheduled_task_http`](/Users/dmeck/.codex/worktrees/5671/ink-dream-memory/backend/tests/probe_scheduled_task_http.py:207) | 隔离技术覆盖；正常 capability 待发布 |
| 查看最近状态与完整历史 | 第 131–143、180–190 行 | 时序二/三 | 卡片显示最近状态并按需展开历史 | E2E 第 317–321、363–364 行 | 首屏和历史展开已覆盖；分页后置 |
| exhausted 禁编辑、重新排期新建 | 第 140、154、208、250–255 行 | 第 253、325、334–346 行 | UI 隐藏编辑 | E2E 第 339–364 行 | 页面合同已覆盖 |
| 打开真实目标 Thread | 第 141、184 行 | 时序三第 259–263 行 | `CalendarPopup` 请求 App 切换真实 Thread | E2E 第 331–334 行 | 精确 Thread ID 已覆盖 |
| 编辑 desired 并采用 effective/revision | 第 145–154、248–255 行 | 时序三第 212–256 行 | 编辑草稿、CAS 冲突和 latest effective 差异 | E2E 第 289–301 行 | 已覆盖 |
| 暂停、恢复、立即运行、删除、撤销 | 第 156–178 行 | 时序三第 216–247 行 | 主操作与更多菜单复用真实 API | E2E 第 303–329 行 | 已覆盖 |
| 失败与 `state_unknown` | 第 211–236 行 | 时序二第 147–180、时序四第 289–316 行 | UI 禁止未知状态盲重跑；网络结果不明保留 manual key | E2E 第 310–315、339–387 行；后端 renew/reconcile 测试 | 已覆盖关键分支 |
| 重启、并发、重复触发 | 第 397–399 行 | 时序四第 266–317 行 | worker claim/start/finish/reconcile | 隔离跨仓旅程验证 dedupe、due-once、restart；86 条后端测试通过 | 技术验收通过；正常 capability 待发布 |
| 普通日记不受任务错误影响 | 第 192–198、223–236 行 | 时序一失败分支 | 任务读取和日记读取分离 | E2E 第 282–286、390–397 行 | 已覆盖 |
| 响应式和可访问性 | 第 272–305 行 | UI 设计第 670–712 行 | Modal、移动入口、单列布局、grid/menu 键盘和焦点恢复 | E2E 第 339–373 行 | 已覆盖首期关键合同 |

## 9. 实施与验证回执

| 命令 | 退出码 | 关键结果 |
| --- | ---: | --- |
| `cd frontend && pnpm exec tsc --noEmit --incremental false` | 0 | 最新 UI 类型检查通过 |
| `cd frontend && pnpm build` | 0 | Next.js production build、TypeScript、页面数据与静态页面生成通过 |
| `pnpm exec eslint app/_dream/App.tsx app/_dream/components/CalendarPopup.tsx e2e/scheduled-task-calendar.spec.ts` | 0 | 0 error；`App.tsx` 仅保留 14 条既有 hooks warning |
| `E2E_WEB_BASE=http://127.0.0.1:55173 pnpm exec playwright test e2e/scheduled-task-calendar.spec.ts --reporter=line --workers=1` | 0 | `4 passed (15.4s)`；桌面、移动、结果不明 request key、无任务日期 |
| `PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest==9.1.1 --with pytest-asyncio python -m pytest backend/tests/test_scheduled_task_consumer.py backend/tests/test_session_projection_broker.py backend/tests/test_thread_tool.py backend/tests/test_claude_agent_service.py backend/tests/test_claude_agent_thread_input_queue.py -q` | 0 | `86 passed, 9 subtests passed` |
| `PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest==9.1.1 --with pytest-asyncio python -m pytest backend/tests/test_server_claude_agent.py -q` | 0 | `95 passed, 4 subtests passed`；普通 Chat 回归 |
| `pnpm exec playwright test app/_dream/components/chat/__tests__/ChatStopControl.test.ts app/_dream/components/chat/__tests__/ThreadInputQueue.test.ts app/_dream/components/chat/__tests__/ThreadInputQueueCard.browser.test.ts --reporter=line --workers=1` | 0 | `8 passed`；队列合并回归 |
| `pnpm exec playwright test app/_dream/components/chat/__tests__/ChatDreamReconnect.test.ts app/_dream/components/chat/__tests__/ChatQueuedSend.test.ts --reporter=line --workers=1` | 0 | `2 passed`；reconnect/queued send 回归 |
| `node /private/tmp/run-scheduled-current-proof.mjs` | 0 | 隔离 PostgreSQL migration、manual dedupe、due-once、restart 均 passed；随机数据库已清理 |
| `python3 /private/tmp/check_scheduled_markdown_links.py docs/design/claude-agent/scheduled-task-diary-page-prd.md docs/design/claude-agent/scheduled-task-diary-page-ui-design.md docs/design/claude-agent/scheduled-task-loop-interaction-design.md docs/exec/scheduled-task-diary-prd-review-20260929.md` | 0 | `checked 4 markdown files: all local links exist` |

正常数据库发布与真实业务验收按第 6 节保留为独立门禁。

## 10. 最终裁决

- **PRD/UI 是否足够具体：** 是。IA、操作、状态、错误、响应式和可访问性已经形成可实施合同。
- **业务交互时序是否完整：** 是。四张业务时序图和两张状态图完整保留正常流程、失败分支、并发和恢复。
- **三项首次评审问题是否关闭：** 是。`exhausted`、A3 diary-only/月摘要后置、claim/prepare DTO 均已统一。
- **是否与 DTO/operation 对齐：** 是。定义、触发、revision、manual key、claim/prepare/start/finish/reconcile 均可逐项映射。
- **是否过度设计：** 否。月摘要和更复杂周期已后置，首期复用现有 Task/Thread/Run/Tool/事件与持久化路径。
- **当前最小纵向切片是否完成：** 是。首次评审 P0 已由生产页面和相称测试关闭。
- **技术验收是否完成：** 是。前端、后端、普通 Chat 回归、隔离跨仓旅程、最新 production build 和文档引用检查均有通过回执。
- **发布与真实业务验收是否完成：** 否。正常 PostgreSQL capability、Admin 提交归位、真实账户/模型和部署均未被本回执证明。
- **剩余产品项：** 历史分页、非终态有界刷新和 DST 歧义候选属于后续合同，不阻塞当前单次/每日最小纵向切片的技术验收。
