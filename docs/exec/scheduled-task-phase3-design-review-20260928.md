<!-- [Input] 阶段一 dd79b5e8、阶段二 420bad49、Notion 主页面/空锚点访问回执、Dream/Admin/Codex/Claude 源码和本机 Admin 数据库只读检查。 -->
<!-- [Output] 定时任务设计逐项评审、范围裁决、实施前置顺序及需求—设计—实现—测试追踪矩阵；不宣称功能已经实现。 -->
<!-- [Pos] docs/exec 的独立设计评审回执；现行规范和阶段二原文分别保存在 ../design/claude-agent/ 的两个文件。 -->
<!-- [Sync] 2026-09-28: 核对正常 Admin capability 与 Dream 受权入口，保留一次/每日、暂停恢复、手动运行和删除旅程，收敛未证实的参考行为。 -->

# 定时任务设计独立评审

评审日期：2026-09-28。先在干净工作树以 git merge --ff-only 衔接 420bad49，包含阶段一 dd79b5e8。本次只修改 Dream 文档。阶段二设计的[完整原文](../design/claude-agent/scheduled-task-loop-interaction-design-20260928-phase2-history.md)单独保存；[现行设计](../design/claude-agent/scheduled-task-loop-interaction-design.md)承载下面的范围裁决。

## 结论

**收敛后实施。** 本次已经把设计收敛成一次与每日两种规则、新建独立 Thread、Tool 创建、日期卡片、编辑 revision、暂停/恢复、手动运行、软删除/撤销及逐次历史。产品目标可以通过 Admin Drizzle 前向扩展和 Dream 受权应用服务接线实现；没有证据表明必须扩展 Claude Code 核心协议。**当前本机尚不能启用调度**：正常 Admin 数据库缺少定时任务表和精确 capability，Dream 后台也没有可在浏览器令牌过期后合法调用的 Chat 应用服务入口。这是实施顺序和发布门槛，不能误写成永久无法实施，也不能跳过后宣称已闭环。

## 证据范围

下表的 D 为本仓库，A 为 /Users/dmeck/project/ink-admin-memory，C 为 /Users/dmeck/project/claude-code-sourcemap/restored-src，X 为 /Users/dmeck/project/Codex-Original-Functionality-Round52-Delivery。行号来自 2026-09-28 的工作树；A 的 main 为 bef4c27，工作树干净。C 为恢复源码，X 是参考重建源码，均不能证明当前 Dream 运行进程的能力。Notion 主页面和两个空锚点的读取结果、具体入口见[阶段一回执](./scheduled-task-phase1-source-assessment-20260928.md)；本次网页入口无法再次访问，因此没有把空锚点填成新需求。

| 检查项 | 证据及判断 | 现行设计处理 |
| --- | --- | --- |
| 退出后真正定时触发 | C/src/utils/cronTasks.ts:74-82,190-218 持久化文件；C/src/utils/cronScheduler.ts:456-459 的计时器仍在进程内，C/src/entrypoints/agentSdkTypes.ts:350-355 的 watchScheduledTasks 抛出 not implemented。D/backend/libs/claude_agent_kit/server/agent_runner.py:365-385 未默认开放 Cron Tool。单靠 Claude Cron **不能**满足目标。 | Admin 定义/触发持久化，Dream 独立 worker 领取；不引用 Claude Cron 文件作为业务记录。 |
| Task、Thread、Run、Tool 复用 | A/packages/db/src/schema/dream.ts:681-703 是 chat_task_session；:902-959 是 workflow_runs。D/backend/routers/claude_agent.py:2007-2026、2116-2163 的 Thread Tool 已创建/发送目标 Thread，D/backend/libs/claude_agent_kit/server/thread_tool.py:21-124 定义模型面。 | 定义与触发新建；实际执行关联已有 TaskSession 和 Chat 消息，Run 仅有真实 Workflow Run 时关联。 |
| 公开 turn/resume/cancel/SSE | D/backend/routers/claude_agent.py:938-959、1350-1385 是 POST /api/claude-agent 的鉴权、准备及 Factory 路径；:2617-2653 是既有 stop/delete；D/backend/claude_agent/thread_factory.py:350-365、400-455 持有单 Thread owner；D/backend/claude_agent/event_bus.py:62-81 是当前轮次流。 | 保持普通入口和状态机；调度只通过同一受权应用服务发起，SSE 不作长期结果库。 |
| 后台能否直接复用现有入口 | D/backend/routers/claude_agent.py:939-944 依赖 get_current_user 和 get_admin_request_auth，:1034-1040 要求 AdminRequestActor；:1896-1916 当前子任务启动在**活跃用户轮次**内直接调用路由函数。D/backend/services/admin_data/request_auth.py:213-225 从 access token 建 actor，:257-265 再建 turn delegation。现有代码**没有**数日后后台取得同等授权的入口。 | 将公开路由与 worker 接到同一个经过身份、Thread、模型、Deck、持久化和资源校验的应用服务；Admin 按触发颁用途限定服务授权。未完成前不启用 worker；技术测试必须走该生产服务与公开 DTO。 |
| 身份、权限与持久化 | A/app/lib/dream/chatThreadRepository.ts:279-333 已有受权且幂等的目标 Thread/首条消息事务。A/app/lib/dream/notionConnectorHandler.test.ts:93-114 可见既有定时服务身份与用户身份分离的参考模式，但不是 Chat 调度授权的现成接口。 | 派发前重新核对用户、来源 Thread、模型与 Deck；按触发 ID 幂等，不能长期存浏览器令牌或伪造用户上下文。 |
| Codex App 证据界限 | 当前 automation_update 工具合同区分 cron 新任务与 heartbeat 既有任务；X/src/shared/automations/contracts.ts:8,33-46、X/src/main/automations/automation-service.ts:445-465 与之相符。X 同文件 :481-492 是本地进程轮询；:335-345 在派发前推进时间。原生界面、一次规则、用户时区、夏令时、多实例恰好一次均无可核实证据。 | 只用其 cron/heartbeat 作为参考；本产品一次/每日、时区、失败规则明确标为设计决策。 |
| CalendarPopup 与导航 | D/frontend/app/_dream/components/CalendarPopup.tsx:36-48,58-97,165-183 目前读取笔记；D/frontend/app/_dream/components/chat/ChatView.tsx:333-337 的 task_thread 仅初次挂载读取。 | 日期查询新增受权卡片；App 明确导航到 ChatView/既有侧栏，不依赖地址栏刷新。 |
| default、desired、effective、revision | 阶段二原文:37,82 要求三份完整配置与多个 revision 同事务持久化；没有异步应用阶段的业务证据。 | default 是未保存建议，desired 是提交输入，effective 是唯一已提交定义；仅 effective 与 revision 持久化。事务失败保持原值，编辑/暂停/恢复/删除做预期 revision 比较。 |
| 时间、停机、并发与失败 | 阶段二原文:39-41 给出一次、日/周/月、夏令时、补跑及跳过规则，但这些是设计决策。A/app/lib/dream/chatThreadRepository.ts:223-277 的输入队列有 revision；它不负责定时领取。 | 首期一次+每日；固定 IANA 时区、确定夏令时、单次延迟领取、每日仅最近一次补发、Admin 原子领取、按触发 ID 对账；未知结果不盲目重发。 |
| 状态、用户反馈与影响 | 阶段二原文:63-69 的定义/触发/Thread 分层正确；软删除撤销、手动运行、状态待核对属于用户当前完整旅程。 | 保留编辑、暂停恢复、手动运行、软删除撤销与历史；不增百分比进度、第二套 Run/SSE、额外确认弹窗。 |
| 重复实现与未来假设 | D/frontend/app/_dream/components/chat/TaskActivityContent.tsx:61-103 和 TaskSessionSidebar.tsx:14-79 已有来源 Thread 的活动入口；D/backend/routers/claude_agent.py:2007-2159 有五个 Thread Tool。 | 复用组件、TaskSession 和 Chat turn；周/月、继续当前 Thread、CollectionsView 与跨实例停止另列后续，不混入本轮门槛。 |

## Admin Drizzle 与正常数据库只读结果

A/main 的 drizzle/meta/_journal.json 最后是 0068；A/drizzle/0068_cool_psylocke.sql:5-29 建立的是 chat_task_result，非定时定义/触发。A/packages/db/src/schema/dream.ts:681-738 同样只有 chat_task_session 与 chat_task_result。对 A/drizzle/*.sql、A/drizzle/contracts、A/app/lib/dream 及 schema/dream.ts 的定时任务结构/操作搜索，没有本功能的定义、触发或精确 capability。Notion connector 已有 scheduled sync 字样，属于另一业务域，不代表 Chat 定时任务已经发布。

本机 .env.local 的 DREAM_DATA_DATABASE_URL 只在脚本内部读取；先将 URL 数据库名与 SELECT current_database() 比对，再 BEGIN READ ONLY 查询 drizzle.schema_capabilities 和 pg_tables 中名称包含 schedule/automation 的记录。结果：数据库为 ink-memory，capability registry 存在，匹配的 capability 为 []、public 表为 []；事务 COMMIT，脚本 exit 0。首次 sandbox 查询 connect EPERM；经只读网络权限批准后同一查询成功。没有修改数据库、服务或账户。这个检查仅证明**本机当前数据库**没有本功能；其他部署须各自核验。Admin Drizzle 先提交前向 migration 与精确 capability，发布并验证目标数据库，再部署 Dream 消费者和页面；缺 capability 时定时功能 fail closed，普通 Chat 继续原路径。

## 范围裁决与实施清单

| 能力 | 裁决 | 理由 |
| --- | --- | --- |
| 一次、每日，Tool 创建，新 Thread，每次记录，日记日期卡片 | 首期必须 | 同时覆盖按时执行、周期表达和用户查看真实会话。 |
| 编辑及 revision、暂停恢复、手动运行、软删除撤销 | 首期必须 | 完整业务旅程需验证暂停不触发、恢复按新计划触发、立即运行与删除后停用；状态和历史必须可核对。 |
| 用户时区、夏令时、停机恢复、并发领取、幂等、状态待核对 | 首期必须 | 决定实际触发和用户可见日期；不是可以留给浏览器或 Claude Cron 的实现细节。 |
| 每周/每月、继续现有 Thread、CollectionsView 卡片、跨实例实时停止、子任务树编辑 | 后续独立决策 | 当前目标可由一次+每日和新 Thread 完整验证；增加这些路径会扩大授权、时间和导航合同。 |

按顺序实施：① Admin Drizzle expand、受权 DTO、精确 capability 和目标数据库核验；② 公开 Chat 路由与后台共享的受权应用服务及触发限定授权；③ Tool、领取 worker、幂等 TaskSession/Thread 派发与结果对账；④ CalendarPopup 日期投影和既有 Chat 导航；⑤ 隔离数据库技术合同与浏览器完整旅程；⑥ 若另行要求真实业务测试，按 AGENTS.md 在正常服务、正常数据库和用户指定账户执行。每步都可在缺前置时停止，不用 Dream runtime DDL、环境标签分支、假用户或内部分叉入口。Admin capability 缺失属于第一步的待实施事项，而非拒绝开始实现的永久阻塞。

## 需求—设计—实现—测试追踪矩阵

| 需求 | 现行设计 | 实现目标及当前状态 | 必须验证 |
| --- | --- | --- | --- |
| Agent 创建一次或每日计划 | “创建、配置和版本” | Admin 定义/DTO 与 Dream create_scheduled_task；**待实施** | Tool 身份、字段错误、幂等、单次/每日下一时刻。 |
| 真正到期启动 Claude Code 会话 | “到期恢复和权限”“实施顺序” | Admin claim/服务授权、Dream worker/共享 Chat 应用服务；**待实施** | 公开生产 DTO、假模型完整派发、真实 Thread/首条消息/final、双 worker 去重。 |
| 日期任务卡片及会话入口 | “用户交互” | CalendarPopup 日期 DTO、App→ChatView 导航；**待实施** | 有/无笔记、未来每日、时区日期、刷新后历史、点击真实 Thread。 |
| 修改计划与并发版本 | “创建、配置和版本”“时间” | Admin 单份 effective + revision CAS；**待实施** | 编辑成功 revision 增加，冲突保持旧 effective，已领取快照不变。 |
| 暂停、恢复、手动运行、删除 | “时间、日期与状态”“用户交互” | Admin 状态操作及手动触发；**待实施** | 暂停后不触发，编辑后恢复按新计划，手动运行不推迟计划，删除后不触发，撤销可见历史。 |
| 停机恢复与失败反馈 | “到期恢复和权限”“失败反馈” | Admin 触发对账和安全错误码、Dream worker；**待实施** | 单次延迟、每日最近一次、崩溃前后不重复模型轮次、未知状态和重试反馈。 |
| 不回归现有业务 | “目标与边界”“失败反馈与影响” | 复用现有 TaskSession、ThreadFactory、Chat/SSE；**未改代码** | 普通 turn/resume/cancel、wait_threads、TaskActivity、笔记和 Workflow Run 回归。 |

## 本轮验证边界

本轮没有执行功能测试或真实模型调用，也没有创建 Run/Thread。现行稿是实施设计，不是已发布功能；隔离数据库验收计划不得当成真实业务完成证据。

- 在 Dream 工作树执行 Python 文档检查（对 git diff 与未跟踪 Markdown 的相对链接及最近 .folder.md 清单逐项验证）：exit 0，markdown_files=8、relative_links=44、errors=0。检查发现两份 README 原有 session-info.md 链接失效，已改为现行 task-activity.md 后重跑通过。
- 用 cmp -s 比对历史稿与 git show 420bad49:docs/design/claude-agent/scheduled-task-loop-interaction-design.md：exit 0，历史原文逐字保留。
- git diff --check：exit 0，无输出。没有启动服务、运行模型或写业务数据库。
