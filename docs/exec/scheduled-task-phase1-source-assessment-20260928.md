<!-- [Input] Notion「近期需求」、Claude Code restored-src、Codex Round52 语义恢复源码，以及当前 Dream/Admin 工作树。 -->
<!-- [Output] 定时任务闭环阶段一的问题界定、源码证据、能力分类和后续实现边界。 -->
<!-- [Pos] docs/exec 的只读架构调研回执；不代表部署验收或产品设计定稿。 -->
<!-- [Sync] 2026-09-28: 记录四处源码状态、Notion 读取、六类调度边界和 Dream/Admin 接线缺口。 -->

# 定时任务闭环阶段一：问题与源码架构判断

## 背景与问题

Notion「近期需求」提出把计划与日记区分，允许会话通过 Tool 创建任务，并在日记的对应日期显示任务卡片、进度和关联会话；还希望研究提醒、定时数据处理，以及类似 Codex 的跨会话状态查询和控制。原文在主页面，两个指定锚点单独读取为空块，见下文“来源与状态”。本阶段判断的是源码能否承载这些行为，不定义产品页面最终布局，也不修改应用代码。

**判断：Claude Code 恢复源码具有定时提示与本地任务列表能力，但它们本身不等于 Ink & Memory 的长期业务任务系统。** Dream 现有跨会话 Tool 和 Admin 持久化关系可复用；长期调度、每次触发的执行记录、日记投影与多实例领取仍需要 Dream/Admin 的业务层。当前任务结果协调器尚未接入正常服务启动，因此即使源码已有结果回传逻辑，也不能称为已闭环。依据见各节。

## 来源、规则与工作树状态

以下短名均指绝对路径，后文 `短名/相对路径:行号` 可以还原为准确文件位置。

| 短名 | 源码根目录 | Git 状态，2026-09-28 读取 |
| --- | --- | --- |
| D | `/Users/dmeck/.codex/worktrees/e044/ink-dream-memory` | detached `HEAD`，`391ecf46`，调查前 `git status --porcelain=v1` 为 0 行。 |
| A | `/Users/dmeck/project/ink-admin-memory` | `codex/dream-agent-thread-queue-admin`，`a109d8b`，72 行未提交状态；本报告引用的 `chatThreadRepository.ts`、`chatThreadService.ts`、`dream.ts` 有修改，`taskSessionResultRepository.ts` 尚未跟踪。它们是候选工作树事实，不是已发布 capability 的证据。 |
| C | `/Users/dmeck/project/claude-code-sourcemap/restored-src` | 所属 Git 根为 `/Users/dmeck/project/claude-code-sourcemap`，`main`、`a8a678c`，0 行未提交状态。恢复源码仅用于能力判断，不能证明 Dream 当前所装 Runtime 已包含同一版本能力。 |
| X | `/Users/dmeck/project/Codex-Original-Functionality-Round52-Delivery` | `main`、`e3fe334`，3307 行未提交状态；本报告引用的 `src/main/automations`、`src/shared/automations`、`src/renderer/automations` 范围为 0 行未提交状态。它是交互和调度参考，不是 Dream 目标仓库。 |

已读取 D 的 `AGENTS.md`、`Agent.md`、根及受影响目录 `.folder.md`、`docs/rules/README.md`、四个 `.cursor/rules/*.mdc`，并读取 A 的 `AGENTS.md`、根及相关目录规则。D 的 `Agent.md` 要求完成时核对文档路径及 `git diff --check`；D 的 `AGENTS.md` 和 A 的 `AGENTS.md` 规定共享 PostgreSQL 结构只能由 A 的 Drizzle 前向迁移和 capability 管理。本次只写本报告及 `docs/exec/.folder.md`。

Notion 连接器 `notion_fetch` 在 2026-09-28 成功读取[主页面「近期需求」](https://app.notion.com/p/3d630b7547c380939b7ef1e16a886b6f)，返回页面正文、图片引用和最近编辑时间 `2026-09-28T13:03:00.025Z`；未返回截断标记。对锚点 `3da30b7547c3802a8d9ecce47e772e7e`（「任务管理模块设计」）及 `3e930b7547c3805baff8da765e02c861`（「关于任务系统设计」）分别调用 `notion_fetch`，均返回 `<blank-page>This page is blank and has no content.</blank-page>`。因此需求文字取自主页面，不把两个空子块当成另有细则；主页面的截图未用于推导后端合同。

## 概念与规则：五种不同对象

| 对象 | 已有源码含义 | 阶段一裁决 |
| --- | --- | --- |
| Claude Code `TaskCreate/TaskUpdate/TaskList/TaskGet` | `C/src/tools/TaskCreateTool/TaskCreateTool.ts:18-32,80-90` 接收标题、描述、状态等；`C/src/utils/tasks.ts:70-88,199-230,284-301` 将任务清单按会话或团队标识放在 Claude 配置目录的 JSON 文件。Dream 通过 `D/backend/libs/claude_agent_kit/server/sdk_env.py:905-941` 把该清单定位到线程工作区，并在 `D/backend/libs/claude_agent_kit/server/agent_runner.py:374-385` 放行这些工具。 | 这是 Agent 回合内的计划和待办元数据；没有用户、日记日期、触发规则和每次执行历史，不可直接充当业务任务表。 |
| Claude Code `CronCreate/CronList/CronDelete` | `C/src/tools/ScheduleCronTool/CronCreateTool.ts:27-40,82-140` 接收本地五段 cron、提示词、重复与 `durable`；`CronListTool.ts:63-79` 列举，`CronDeleteTool.ts:61-84` 删除。 | 原生定时**提示**。默认 `durable=false`，仅会话内存；即使设为 true，也只是把定义写入项目文件。 |
| Dream `chat_task_session` | `A/packages/db/src/schema/dream.ts:681-703` 存源 Thread、目标 Thread、初始消息、启动状态；`A/app/lib/dream/chatThreadRepository.ts:279-334` 原子建目标 Thread 和关联记录。`D/backend/routers/claude_agent.py:2007-2026` 的 `thread.create` 调用此路径。 | 已有独立业务会话关系，但目前没有计划时间、重复规则、下次触发或执行序号。 |
| Dream `workflow_runs` | `A/packages/db/src/schema/dream.ts:902-959` 记录工作流输入、状态、重试来源和工作区；`D/backend/services/admin_data/run_data.py:28-57,174-187` 校验并提供 create/retry/cancel/fail。 | 它是 Story Workspace 的工作流执行，不等于 Chat 任务关系或定时定义；只有任务实际发起该工作流时才应建立关联。 |
| Codex Round52 Automation | `X/src/shared/automations/contracts.ts:7-46` 区分 `cron` 与 `heartbeat`；`X/src/main/automations/automation-service.ts:274-317,445-465` 保存定义并向 App Server 发起新 Thread 或既有 Thread 的 turn。 | 可参考状态语义与交互，但不能复制其本地 SQLite/桌面进程存储到 Dream。 |

## Claude Code 定时、恢复与跨会话能力

1. **原生持久调度定义与进程内计时必须分开。** `C/src/utils/cronTasks.ts:74-82,91-139,165-181,194-218` 把 durable 定义存于 `<project>/.claude/scheduled_tasks.json`，并在重启时可读回；`C/src/utils/cronScheduler.ts:142-179,396-459` 用文件观察器和进程内间隔计时触发。`checkTimer.unref()` 明示不会为任务单独保持进程存活（`C/src/utils/cronScheduler.ts:456-459`）。`C/src/hooks/useScheduledTasks.ts:84-122` 将触发提示排入当前会话；`C/src/cli/print.ts:2696-2734` 在受门控的 SDK/打印模式也需正在运行的进程。**推论：文件可在退出后保留，退出期间并无这个计时器运行。**
2. **恢复不是任意历史时刻补齐。** `C/src/utils/cronScheduler.ts:184-227` 在初次加载时把错过的一次性任务交给 `onMissed` 或提示并移除；重复任务由下一次检查触发，随后从当前时间计算下次时间，并写回 `lastFiredAt`（`C/src/utils/cronScheduler.ts:253-276,315-324,358-369`）。这不是有执行记录的逐次补偿队列，也没有结果持久化。`C/src/entrypoints/agentSdkTypes.ts:330-356` 给出宿主守护进程接口说明，但恢复源码中的 `watchScheduledTasks` 函数体明确抛出 `not implemented`；不能据此声称该公开入口可直接使用。
3. **同机同目录的去重不是 Dream 的分布式领取。** `C/src/utils/cronTasksLock.ts:100-172` 用排他文件创建和进程标识处理多个 Claude 会话，非持有者按 `C/src/utils/cronScheduler.ts:406-435` 轮询接管。这约束的是同一目录可见的本地文件，不是跨 Dream 实例、跨节点、Admin 事务及用户权限的领取协议。`C/src/utils/cronScheduler.ts:347-377` 也明确只对文件任务应用锁，内存任务各会话独立。
4. **远程定时是另一个外部系统。** `C/src/skills/bundled/scheduleRemoteAgents.ts:174-193,324-341` 的 `/schedule` Skill 通过远程 trigger Tool 操作 Anthropic 云端会话；源码声明它不是本地 cron，依赖远程会话权限和账户。它不能替代 Ink & Memory 本机真实账户、Admin 持久化和日记任务关系。
5. **原生跨会话交互有范围。** `C/src/tools/AgentTool/AgentTool.tsx:87-99,141-162` 可启动子 Agent；`C/src/tools/SendMessageTool/SendMessageTool.ts:800-868` 对已登记子 Agent 排队、从停止状态或磁盘 transcript 恢复；`C/src/tools/AgentTool/resumeAgent.ts:63-78,197-264` 是以 Agent ID 读取 transcript 后重新启动。这不是对任意 Dream 用户 Thread 的授权状态查询或控制。Dream 已通过自己的宿主 Tool 桥接补上部分业务能力，见下节。

**Dream 当前 Runtime 兼容性限制。** Dream 正常启动使用自身解析的 `ink-claude-code-dream`，`D/backend/server.py:351-363` 在不可用时拒绝启动；`D/backend/libs/claude_agent_kit/server/agent_runner.py:365-385` 的默认工具表有 Task 工具和五个 Dream Thread Tool，却没有 `CronCreate/CronList/CronDelete`。因此恢复源码的 Cron 工具只能作为参考，阶段二必须先对 Dream 实际 Runtime/SDK 版本的工具可用性作只读资格确认，不能把它当成当前已开放给 Dream Agent 的产品功能。

## Codex Round52 参考的准确适用范围

`X/src/main/automations/automation-service.ts:244-260,274-285,289-317` 在桌面主进程读写 `automations/<id>/automation.toml` 与状态数据库；`X/src/main/automations/automation-service.ts:70-102` 使用本机 SQLite。`X/src/main/automations/automation-state-database.ts:101-136` 包含自动化与执行记录表；`X/src/entries/main-runtime.ts:346-347,828-830` 创建并启动桌面调度器；`X/src/main/automations/automation-service.ts:481-492` 每分钟检查到期任务。运行时，`cron` 新建 Thread 并启动 turn，`heartbeat` 对既有 Thread 启动 turn（`X/src/main/automations/automation-service.ts:445-465`）；执行结果随 `turn/completed` 进入待查看状态（同文件 `385-393`）。界面已有列表、历史、下一次时间、创建与更新（`X/src/renderer/automations/automation-center-view.tsx:68-105,128-152`）。

它的本地 `#running` 只防止同一进程重入（`X/src/main/automations/automation-service.ts:481-492`），未构成 PostgreSQL 多实例领取。`runNow` 在发起 Thread/turn 之前先推进 `lastRunAt` 和 `nextRunAt`（同文件 `335-345`），而 `runDue` 捕获运行错误（同文件 `396-403`）；**推论：直接照搬会让部分启动失败缺少可重领的到期记录。** Dream 需要明确的执行记录与失败状态。Codex 使用 SQLite 是其桌面本地架构事实；D/A 的共享 schema 规则禁止把它复制成 Dream 运行时数据库。

当前 Codex App 的 `automation_update` 工具合同也把 `heartbeat` 定义为附着既有任务的主动跟进、把 `cron` 定义为单独运行的新任务；这与 X 的 `cron` 新 Thread、`heartbeat` 既有 Thread turn 的源码一致。Codex 原生界面在本次调查中不可直接读取，因此只将工具合同与 X 源码作为语义参考，不把界面细节当成已观察事实。X 的 `parseAutomationRrule` 只读取频率、间隔、星期、小时和分钟，未解析 `TZID`（`X/src/shared/automations/automation-schedule.ts:38-68`）；`nextCalendarOccurrence` 使用本机 `Date` 的日历字段构造触发时间（同文件 `86-103`）。因此这份参考源码不能证明明确的用户时区、夏令时转换或严格恰好一次的执行语义。

## Dream/Admin 现状：Task、Thread、Run、Tool、turn、恢复与错误

| 边界 | 源码依据与行为 | 尚缺什么 |
| --- | --- | --- |
| 公开 Thread/turn | `D/backend/routers/claude_agent.py:1402-1420` 建 Thread；同文件 `938-959,984-1007,1350-1385` 鉴权后经唯一 `POST /api/claude-agent` 与 `run_streaming` 启动或重连；`D/backend/claude_agent/thread_factory.py:350-366,400-455` 按 Thread 锁拥有一个 turn。 | 定时触发必须复用这条已授权入口/Factory 行为，不自行复制 turn 状态机。 |
| Tool 与跨会话 | `D/backend/libs/claude_agent_kit/server/thread_tool.py:21-124,201-241` 严格定义五个 Tool 并通过私有 Broker；`D/backend/routers/claude_agent.py:1945-2000,2007-2159,2290-2422` 在宿主侧重新授权、建独立会话、列/读/发/等。运行中的消息经队列，空闲消息经同一 `claude_agent_stream(resume=True)`。 | 这已回答 Notion 的跨会话查询与发送疑问；Tool 集合没有面向另一 Thread 的停止、暂停或定时任务管理操作。新增何种控制需先定义用户权限和状态语义，无须预设修改 Claude 核心协议。 |
| 任务关系与结果 | `A/packages/db/src/schema/dream.ts:682-738` 的 `chat_task_session` 与 `chat_task_result` 是两类记录；`A/app/lib/dream/chatThreadRepository.ts:279-395` 负责关系和启动状态；`D/backend/routers/claude_agent.py:1869-1942` 基于目标最终消息判断完成并启动独立 Thread。`D/backend/claude_agent/task_result_coordinator.py:36-100,181-204,228-282` 设计了 Admin claim 后由原 Factory 恢复来源 Thread。 | `rg -n 'TaskResultCoordinator|task_result_coordinator' backend` 只命中协调器自身及测试，`D/backend/server.py:351-395` 的正常启动仅见 Factory 与其他 worker；`D/backend/tests/test_server_claude_agent.py:2734-2735` 还断言没有相应启动函数。结论是**协调器源码存在但正常服务尚未接线**，不能报告自动回传已运行。 |
| 持久化与多实例 | `A/app/lib/dream/chatThreadRepository.ts:223-277` 对输入队列做状态和 revision 检查；`A/packages/db/src/schema/dream.ts:663-678` 约束状态；`A/app/lib/dream/taskSessionResultRepository.ts:126-168,179-250` 使用 `SKIP LOCKED`、事务锁、revision、唯一索引及授权核对处理结果领取。`A/app/lib/dream/chatThreadService.ts:27-37,40-57` 验 scope 与 capability。 | 可复用的是状态变更和数据库领取的**模式**，不能把结果领取直接冒充到期时间领取。A 工作树未提交，且未验证实际数据库已发布这些 capability。 |
| SSE 与取消 | `D/backend/routers/claude_agent.py:1690-1714` 仅对运行中 turn 允许 EventBus 重连；`D/backend/claude_agent/event_bus.py:62-81,111-146,185-202` 缓冲与扇出；`D/backend/routers/claude_agent.py:2617-2653` 公开 stop 和 delete，`D/backend/claude_agent/thread_factory.py:1031-1084` 的 stop 只取消当前进程持有的后台任务。 | 实时 SSE 不承担长期任务状态存储；跨实例 stop 不能靠一个进程内 Factory 快照推断已取消，必须让业务任务状态与运行 turn 取消分开。 |
| Claude Session 恢复 | `D/backend/claude_agent/service.py:2091-2115` 通过 Admin 绑定和本地 transcript 查找判断能否 resume；缺失或不一致有明确错误。成功 turn 的消息与 session ID 由 `D/backend/claude_agent/service.py:2876-2898,3024-3055` 持久化。 | 定时任务的“按时启动一次”不等于已有 Thread 的 Claude transcript 可恢复；若目标 Thread 需要新建还是继续，需在业务任务定义中表达，不能靠 `resume` 猜测。 |
| Workflow Run | `A/packages/db/src/schema/dream.ts:902-959` 和 `D/backend/services/admin_data/run_data.py:28-57,140-187` 形成工作流 Run 的独立状态与 Admin 操作。 | 执行记录可关联真实 Run，但不要新增第二套 workflow_run 状态机，也不要把 `chat_task_session.launch_status` 伪装成 Run 结果。 |

前端现有复用点：`D/frontend/app/_dream/components/chat/TaskActivityContent.tsx:61-103,116-149` 显示来源 Thread 创建的任务及状态；`TaskSessionSidebar.tsx:14-79` 复用 ChatPanel 查看目标会话；`PlanPanel.tsx:1-7,40-46` 汇总计划、待办、独立任务和子 Agent。它们目前绑定当前 Thread 的任务关系，不提供日记按日期的定时任务定义与每次执行视图。不要把现有活动弹层的“任务”与 Notion 的日记任务卡片当成同一个已完成页面。

## 能力分类与下一阶段边界

| 需求行为 | 分类 | 可复用 / 必新增 / 不应新增 |
| --- | --- | --- |
| 会话内提醒、运行中的提示触发 | **Claude Code 原生支持，但 Dream 当前开放情况未证实** | 可参考 `CronCreate` 与 `createCronScheduler`；Dream 默认工具表未列 Cron 工具（`C/src/tools/ScheduleCronTool/CronCreateTool.ts:27-40,117-140`；`C/src/utils/cronScheduler.ts:456-459`；`D/backend/libs/claude_agent_kit/server/agent_runner.py:365-385`）。不得把文件写入等同于全天候服务。 |
| 退出后按时运行、周期重试、多实例只执行一次 | **可组合，但必须有业务调度层** | 在 A 的 Drizzle 中先建前向 schema 和 capability，再由 Dream 独立 provider/worker 领取到期定义并复用公开 Chat turn；保存每次执行、失败、重试与实际 Thread/Run 标识。可参照 A 的事务领取模式，不能复用 C 的文件锁或 X 的本地 SQLite（`A/app/lib/dream/taskSessionResultRepository.ts:126-168,179-250`；`C/src/utils/cronTasksLock.ts:100-172`；`X/src/main/automations/automation-service.ts:70-102`）。 |
| 会话创建、查询、发送、等待独立任务 | **Dream 已组合实现；Claude Code 原生子 Agent 能力范围较窄** | 复用五个 Thread Tool、Admin `chat_task_session` 与同一 Factory；先补齐结果协调器接线和 capability 验证，再评价完整闭环（`D/backend/libs/claude_agent_kit/server/thread_tool.py:21-124`；`D/backend/routers/claude_agent.py:2007-2159,2290-2422`；`D/backend/claude_agent/task_result_coordinator.py:36-100`）。 |
| 日记中按日期展示任务计划、进度、子任务与执行结果 | **可组合，但需要业务投影与页面** | 以用户授权的任务定义、触发日与执行记录产生卡片；复用 Chat 任务关系、状态查询、侧边 ChatPanel，不读取 Claude 配置目录中的任务 JSON 作为日记数据（`A/packages/db/src/schema/dream.ts:682-738`；`D/frontend/app/_dream/components/chat/TaskActivityContent.tsx:61-103`；`C/src/utils/tasks.ts:199-230`）。 |
| 对任意独立 Claude 会话施加 CLI 内部实时控制 | **只有明确需要绕过宿主公开入口时才属于核心协议扩展** | 现有 Dream 状态查询、消息、等待及公开 stop 足以构成当前需求的宿主层方案；如果未来需求明确要由 CLI 直接操纵另一个进程的内部状态，才评估 Runtime 协议变更。现阶段**不应新增 Claude Code 核心协议、Dream 私有控制通道或第二套 SSE/turn 状态机**（`D/backend/routers/claude_agent.py:2002-2159,2617-2639`；`D/backend/claude_agent/thread_factory.py:350-366,1031-1084`）。 |

### 风险与待验证事实

1. **源码与部署分离。** C 是恢复源码，X 是语义恢复参考；A 有未提交的 schema/operation 变更。报告不能证明当前本机或线上 Dream 的 Runtime 工具能力、Admin capability 或结果 worker 已生效。依据见工作树状态、`D/backend/server.py:351-395` 与 `D/backend/libs/claude_agent_kit/server/agent_runner.py:365-385`。
2. **时间语义需要业务定义。** Notion 只明确“按每天对话区分”和“当天存在定时任务则显示”，未写时区变更、错过触发、重复任务对应哪一天及用户可见的失败状态。C 的一次性补发与重复任务当前时刻重算是一种实现行为（`C/src/utils/cronScheduler.ts:184-227,315-324`）；X 的本机 `Date` 日历运算也不足以推出用户时区、夏令时或恰好一次语义（`X/src/shared/automations/automation-schedule.ts:38-68,86-103`）。这些都不能直接包装成产品规则。
3. **结果与错误必须落在持久记录。** Codex 参考源码的运行前推进时间、Dream 进程内状态和 EventBus 均不能独自证明一次触发已完成（`X/src/main/automations/automation-service.ts:335-345`；`D/backend/claude_agent/thread_pool.py:333-375`；`D/backend/claude_agent/event_bus.py:62-81`）。阶段二应明确任务定义、触发实例、关联 Thread/Run、结果、失败与未知状态的转换条件和验收。
4. **权限与结构所有权。** 定时 worker 不能以系统提示词或本地 JSON 绕过用户授权；缺少 Admin Drizzle capability 时应停止该功能的写入/派发。依据 `A/app/lib/dream/chatThreadService.ts:27-57`、`D/backend/routers/claude_agent.py:957-959`、D/A 的 `AGENTS.md`。

## 本阶段执行与验证

除本报告与目录清单的文档写入外，只执行 `git status`、`rg`、`nl`、`cat`、`find` 等只读源码检查及 Notion 读取；没有启动服务、调用模型、写数据库或运行真实业务测试。`python3 - <<'PY'` 对文内 `D/A/C/X` 源码引用按绝对根还原，逐项检查文件存在和所引首行号，并确认本报告列入 `docs/exec/.folder.md`：exit 0，`checked 84 source references; report inventory entry: True; errors: 0`。`git diff --cached --check`：exit 0，无输出。由于本阶段没有应用代码变更，未运行功能测试；文中的“已实现”均指所列当前工作树源码，运行状态按上述限制单独标记。
