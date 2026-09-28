<!-- [Input] docs/exec/scheduled-task-phase1-source-assessment-20260928.md、当前 CalendarPopup/Chat 任务组件、Admin Chat/TaskSession/Thread 合同与 Notion「近期需求」。 -->
<!-- [Output] 定时任务创建、日记按日期查看、逐次执行和失败恢复的产品与系统设计合同；本文不是已实现状态或部署验收。 -->
<!-- [Pos] docs/design/claude-agent 的现行定时任务闭环设计；独立任务会话与等待行为仍由 task-session-tools.md、task-session-completion-handoff.md 定义。 -->
<!-- [Sync] 2026-09-28: 依据阶段一证据定义时间、状态、授权、Admin Drizzle 与 Dream 复用路径，并区分现有入口和待实现卡片。 -->

# 定时任务闭环：交互与执行设计

设计日期：2026-09-28。依据为[阶段一源码判断](../../exec/scheduled-task-phase1-source-assessment-20260928.md)、[独立任务会话设计](./task-session-tools.md)、[父轮次等待设计](./task-session-completion-handoff.md)及 [Chat 任务活动设计](./task-activity-popover.md)。[Notion「近期需求」主页面](https://app.notion.com/p/3d630b7547c380939b7ef1e16a886b6f)提出 Tool 建任务，以及日记按日期展示任务卡片、进度和关联会话；两个指定锚点单独读取为空块。Codex Round52 源码和当前 `automation_update` 工具合同仅作为语义参考：其 `cron` 每次创建新任务，`heartbeat` 继续既有 Thread；原生界面无法直接核对，单次计划、时区及夏令时规则没有得到证明。下述具体时间和失败规则均为**本设计决策**，不是对 Codex 行为的陈述。

## 背景与问题

当前 Dream 的 `create_thread`、`list_threads`、`read_thread`、`send_message_to_thread`、`wait_threads` 已提供独立业务 Thread 与父轮次内等待；Chat 的 `PlanPanel` 和 `TaskActivityContent` 展示当前 Thread 的任务、子智能体、计划和待办。`CalendarPopup` 是真实存在的笔记日历弹窗，右侧按选定日期列出笔记，`CollectionsView` 也有日期时间线；两处都**没有**定时任务定义、逐次执行或任务卡片。Notion 提到的“笔记弹窗任务模块”是目标界面，不是当前已经交付的模块。

Claude Code 的 Task 清单和 Cron 文件只服务于其自身会话；Dream 当前 `agent_runner.py` 的 `DEFAULT_ALLOWED_TOOLS` 没有向用户开放 Cron 工具。本机只读核对显示 `ink-claude-code-dream --version` 为 `2.1.241 (Claude Code)`，`backend/pyproject.toml` 声明 SDK `0.2.145`；这些信息不能证明当前运行服务的精确 Runtime manifest/capability，也不改变未开放 Cron 的事实。进程内计时和 SSE 订阅不能保证退出后触发，也不能记录每次执行。阶段一调查中的后台 `TaskResultCoordinator` 描述已由现行 `wait_threads` 设计取代；定时触发不得重新引入来源 Thread 技术消息或结果卡片。应让长期计划、每次触发和真实 Chat 执行各有明确记录，并从同一受权业务数据生成日记卡片。

## 目标与边界

1. 用户在当前 Chat 中请 Agent 通过新的宿主 Tool 创建一次或周期任务，得到明确的时间、时区、目标会话和下一次执行信息。用户可从日记日期卡片查看、编辑、暂停、恢复、删除和立即运行。
2. 每个到期时刻由服务端领取，关联唯一的触发记录；实际模型轮次沿用 Admin Chat 持久化、Dream ThreadFactory、输入队列、`POST /api/claude-agent` 背后的 `run_streaming` 执行路径和现有 SSE，不另建模型状态机。
3. 日期卡片展示计划、当前状态、最近一次结果及其真实 Thread；在当前 Thread 有来源关系时，原 Chat 任务活动入口仍可打开相应独立任务会话。用户离开页面、浏览器关闭或 Dream 进程重启后，定义和执行历史仍可查询。
4. 第一可实施切片包含 Tool 创建、Admin 定义与触发记录、Dream 后台领取、现有 Chat 执行、`CalendarPopup` 日期卡片及卡片管理操作。`CollectionsView` 的同一日期投影可在后续接入，不需要先建设新的日记页面。

本设计不改变 Claude Code Runtime 的内部 Cron、`TaskCreate` 清单、现有 `wait_threads` 语义或 Story Workspace 的 `workflow_runs`。它不建立通用工作流编辑器、独立任务运行状态机、Dream 数据库或按部署环境名称分叉的业务路径。

## 概念与规则

| 概念 | 持久化与身份 | 规则 |
| --- | --- | --- |
| 定时任务定义 `schedule` | Admin PostgreSQL 中的用户、来源 `thread_id`、标题、提示词、目标模式、时间规则与配置版本 | 一份定义可以产生多次触发；它不是 Claude `TaskCreate` 清单，也不是现有 `chat_task_session.task_id`。 |
| 触发记录 `occurrence` | Admin 中的 `schedule_id`、计划时刻、来源配置 revision、触发种类、领取和结果字段 | 一个计划时刻最多一条计划触发；“立即运行”另建手动触发，不改下次计划时间。 |
| 独立任务 `TaskSession` | 现有 `chat_task_session.task_id`、来源 Thread、目标 Thread | 仅“新建 Thread”模式的每次触发创建一条关系；定时定义与每次独立任务为一对多。 |
| Chat `Thread` 与轮次 | Admin Chat 保存消息及会话绑定；Dream ThreadFactory 持有运行 owner | “新建 Thread”每次触发有新目标 Thread；“继续当前 Thread”把输入排入创建时绑定的来源 Thread，并在该 Thread 串行执行。一个触发对应一次拟发起的用户输入，不能把 SSE 帧当作完成。 |
| `Run` | 仅当该轮次确实进入已有 Story Workspace 工作流时关联其真实 `workflow_runs.id` | 普通 Chat 定时任务的 `run_id` 为空；不得为了卡片显示伪造 Run 或复用工作流状态字段。 |

**创建与默认值，均为本设计决策。** 新 Tool 暂命名 `create_scheduled_task`，模型只提交标题、要执行的提示词、一次时刻或周期规则、时区及可选目标模式；宿主从当前已认证轮次取得用户、来源 Thread 和 Tool 调用 ID，模型不能提供用户身份或授权凭据。默认目标为“每次新建 Thread”，默认启用；创建没有默认的执行时刻，用户未给出可确定的时间时 Tool 先请用户补齐。默认时区取 Admin 已保存的用户 IANA 时区偏好，浏览器时区只可作为表单建议；偏好不存在或不是有效 IANA 时区时必须明确选择，不能按服务器本地时区猜测。周期由“每天”“每周指定星期”“每月指定日期”表达；这三种是首期交互范围，不作为技术配额。每月没有所选日期时跳过该月，不挪到月末。只有用户明确要在原会话继续时才选“继续当前 Thread”，并在保存时绑定当前受权 Thread。

**配置版本。** `default` 是创建界面的未保存建议：新 Thread、启用、用户偏好时区；`desired` 是用户最近一次请求保存的完整定义；`effective` 是 Admin 已校验并写入 PostgreSQL、供领取事务读取的完整定义及 `next_due_at`；`revision` 是定义每次成功编辑、暂停、恢复、删除后的单调递增版本。Admin 在同一事务中校验权限、配置、预期 revision，写入 desired、effective、effective revision 和下次计划时刻；成功回执只在提交后报告“已生效”。校验、capability 或事务失败时四者均不变，页面保留编辑内容并显示可重试原因。后台派发故障只改变触发记录，不倒退有效配置。触发记录保存领取时的配置快照及 revision；随后编辑不篡改已经开始的执行。`runNow` 不改定义 revision 或计划时刻。

**时间。** 一次任务保存用户选定的本地日期、时间和 IANA 时区，并解析为唯一 UTC 时刻。创建和编辑时若计划时刻已过去，提示重新选将来时间；服务端以数据库时间校验。周期规则保存本地钟点、IANA 时区和重复字段，Admin 负责计算下一 UTC 时刻，Dream 不独立推算。账户时区以后变化不自动修改已保存规则；编辑时可显式改时区，并预览新的下一次时间。夏令时使某个本地钟点不存在时，周期跳过该本地日期；重复的本地钟点取较早的第一次，并在详情中展示 UTC 偏移以便核对。一次任务若选到不存在的本地钟点则拒绝保存；若同一钟点重复，表单显示两个偏移并让用户选择一个。所有时间计算、日期查询与测试使用 IANA 时区数据库；不能从 Codex 本机 `Date` 行为推导本产品规则。

**错过、并发与去重。** 一次任务在服务恢复后若尚未领取且定义仍启用，领取一次并标记“延迟启动”；周期任务不逐次补跑停机期间所有时刻，只对恢复时最近的到期时刻创建一次触发，并在记录中保存被略过的次数与时间范围。按计划时刻、定义 ID 唯一化计划触发，定义 revision 不参与唯一键，避免编辑同一时刻重复发起。每个定义最多有一个正在领取、排队或运行的触发；周期任务的后续到期时刻记录为“本次跳过：前次仍在执行”，推进下一时刻；一次任务遇到已有手动触发时保留到期状态，待活动触发结束后仍只领取一次。不同定义可以并发，但同一 Thread 的轮次始终遵守现有输入队列、Factory 锁和资源 admission。手动立即运行在已有活动触发时返回该触发状态，不启动第二轮；服务端用请求幂等键防重复点击和请求重放。这里的目标是每个触发最多启动一个业务轮次；外部模型调用与进程崩溃之间不能承诺绝对恰好一次，结果不明时先对账而非盲目重发。

## 用户交互流程

1. 用户在 Chat 中说出内容与时间，Agent 调用 `create_scheduled_task`。Tool 回执给出标题、一次或周期、时区、目标模式、下一次本地时间、状态和业务 `schedule_id`。Agent 用自然语言简要告知用户，不附加第二次确认弹窗。
2. 用户打开已有 `CalendarPopup` 并选择日期。右侧保留当前笔记列表，新增同一天的“任务”卡片组；没有笔记但有任务时仍显示任务，不再显示“当天没有内容”。日历格对笔记与任务分别给出可辨认标记。初始接入点是 `CalendarPopup` 受权日期查询和右侧卡片，不能把 `CollectionsView` 的历史图片时间线当成已存在的任务模块。
3. 卡片显示标题、计划时间及规则、时区、启用或暂停状态、最近触发的文字状态、实际开始与完成时间；进度只用服务端已保存的“待执行、排队、运行中、已结束、失败、状态待核对”等事实，不由提示词或百分比推断。发生执行后才显示“打开会话”；新建 Thread 模式打开本次目标 Thread 的既有 `TaskSessionSidebar`/ChatPanel，继续 Thread 模式打开已绑定的 Chat Thread。`CalendarPopup` 通过 `App.tsx` 的导航回调切到 Chat，并向 `ChatView` 传递目标 Thread 与打开侧栏的请求；现有 `task_thread` 查询参数只在 `ChatView` 初次挂载时读取，不能单靠改写地址栏完成已挂载页面的导航。若实际产生子任务，沿现有 `task-links` 展示其数量和入口；没有关系时不画空子任务树。
4. 用户从卡片编辑标题、提示词、日期或周期、时区和目标模式，保存时带预期 revision；成功后立即显示新的下一次时间。暂停与恢复直接保存，无额外确认；暂停阻止尚未领取的未来触发，不停止正在运行的轮次。删除采用保留历史的软删除，并提供同页撤销操作；已经运行或失败的记录仍能从历史访问。立即运行独立增加手动触发，不推迟周期计划；若定义已暂停，页面先说明需恢复后才可立即运行。一次计划完成计划触发后标为“已执行”，仍允许用户显式立即运行形成新手动记录。
5. 卡片中的“停止当前执行”只在确有运行轮次且服务能定位 owner 时调用现有 Thread stop；停止请求和已确认终态分开显示。删除或暂停计划不隐含停止当前轮次。页面重开从 Admin 读取定义与触发历史，SSE 仅用于当前可订阅轮次的实时内容，断线后按持久记录刷新。

日期归属以日记弹窗当前展示的用户时区为准：Admin 将触发 UTC 时刻投影为该时区的日期，卡片同时显示定义的固定时区。未来周期卡片从有效规则计算所选日期的计划时刻，不预建无穷触发记录；历史卡片从实际触发记录取得。用户改变日记展示时区后重新查询并分组，不能仅改浏览器文字而保持旧日期归属。日期投影不依赖是否存在笔记 Session。

## 系统执行流程

1. **创建或修改。** Dream 宿主 Tool 或受权页面请求进入严格 DTO；Admin 从认证主体与来源 Thread 关系校验所有权、目标模式、IANA 规则、capability 和 revision，按 Tool 调用 ID 或页面请求键幂等写入。Admin Drizzle 是定义、触发记录、索引、约束和 capability 的唯一结构来源。
2. **到期领取。** Dream `server.py` 的独立后台 worker 使用受限服务身份调用 Admin 命名的到期领取操作。Admin 用数据库时间、行锁与 `SKIP LOCKED` 在事务中检查 effective 状态、revision、`next_due_at`、未结束触发和唯一约束；原子写入触发记录、领取租约与下一时刻。多实例只允许持有当前 fencing revision 的领取者更新该触发。worker 的轮询间隔是运维配置，不是用户可见的产品时刻或精度承诺。
3. **派发授权。** Admin 从触发记录中已保存的用户、来源 Thread、目标和内容生成限定此触发的服务端执行授权；每次发起前重新验证用户仍可访问目标 Thread、定义未在领取前被暂停或删除、服务授权未过期及现有模型/Deck 权限。不能持有创建时捕获的浏览器 OAuth token 等待数天，不能让 Agent 通过提示词自行充当授权。权限被撤销或 capability 缺失时停止派发并保存失败原因；不可用时不得在 Dream 临时建表。
4. **真正执行。** “新建 Thread”以触发 ID 作为幂等来源，复用现有 Admin `chat_task_session` 的原子目标 Thread/首条消息创建与 Dream 首轮执行；触发记录关联新 `task_id`、`thread_id`、消息 ID。“继续当前 Thread”向已绑定 Thread 复用现有 Admin 输入队列，运行时按保存的 Claude session ID 正常 resume。两种模式最终都进入 `POST /api/claude-agent` 背后同一个已授权 Chat turn 服务、ThreadFactory、admission、Service 持久化和 SSE/EventBus；worker 调用共享应用服务入口，不新增 Dream HTTP、消息队列、shell、restart 或 kill 控制通道，也不伪造浏览器请求。前台用户手动向该 Thread 发消息仍走原 `POST /api/claude-agent`。
5. **结果与恢复。** 触发记录只在确切的输入消息被消费、对应轮次 final 已写入 Admin 后标为成功，并保存最终消息 ID；错误、停止、权限拒绝分别保存安全错误码与可操作说明。进程重启后，新 worker 根据租约和 Admin 中的触发、TaskSession、Thread、消息 ID 对账：未派发可重新领取；已建 Thread 或已入队则沿原幂等 ID 继续观察；无法判定模型是否启动时标为“状态待核对”并停止自动重发。后台异常不得传播到无关 Agent turn。父来源 Thread 不会因后台定时任务完成而自动恢复；活跃父轮次只在它主动调用现行 `wait_threads` 时等待子 Thread。

## 状态与转换

| 对象 | 状态及转换条件 | 页面表达 |
| --- | --- | --- |
| 定义 | `active → paused → active` 由受权用户 CAS 写入；一次计划触发建立后 `active → exhausted`；软删除使任意非删除状态 `→ deleted`，撤销恢复至删除前状态并重新计算未来计划。 | 启用、已暂停、已执行、已删除；编辑成功以返回的 effective revision 为准。 |
| 触发 | 到期领取形成 `claimed`；目标消息持久化后 `queued`；对应轮次开始后 `running`；Admin final 提交后 `succeeded`，明确启动/执行错误为 `failed`，已确认停止为 `cancelled`；存在派发证据但结果不明为 `state_unknown`。与活动触发冲突的计划时刻记 `skipped`，不启动轮次。 | 待启动、排队、运行中、已结束、失败、已停止、状态待核对、已跳过；错误详情提供重试读取或立即运行入口。 |
| Chat Thread | 继续使用现有 `starting/running/idle/failed` 等受权状态和消息 final；它不是定义状态。 | Thread 空闲不代表定时定义完成；一次调用的 final 不代表周期定义停止。 |

领取租约过期不是 `failed` 的充分条件。恢复程序先核对相同触发 ID 是否已创建 TaskSession、Thread、消息和最终回复，再决定重领、继续观察或 `state_unknown`。暂停、编辑、删除与领取并发时，Admin 事务顺序决定：领取先提交则本轮按旧 revision 继续，配置先提交则旧 revision 不再领取。日记卡片必须显示这个差别。

## 数据及接口影响

| 所有者 | 必要新增或复用 |
| --- | --- |
| Admin Drizzle | 前向 migration 增加定义与触发记录、唯一计划时刻和手动请求键、owner/Thread 外键、revision/CAS、领取租约及受限 capability；生成 SQL、journal、snapshot 和精确 capability，先发布 expand，再让 Dream 消费，后续回填/校验/contract 分阶段进行。现有 `chat_task_session`、Chat 消息和 `workflow_runs` 不改作定义表。 |
| Admin 领域服务 | 严格 DTO 与命名操作：创建、查询日期/详情、CAS 修改、暂停/恢复、软删除/撤销、立即运行、claim、派发回执、结果对账；用户操作取 OAuth 主体，后台领取取用途限定服务身份，所有写入在事务中完成并留审计。Route Handler 只编排请求。 |
| Dream | Tool broker 注册 `create_scheduled_task`；独立调度 provider/worker 经 Admin DTO 领取，使用现有 Chat Thread/TaskSession 创建、输入队列、Factory 和 Service。缺 capability 时只禁用调度读写与派发并返回明确错误，不影响普通 Chat turn；不得加入运行时 DDL、SQLite 回退或环境名判断。 |
| 前端 | `CalendarPopup` 按所选日期读取受权任务投影并渲染卡片；`App.tsx` 将卡片会话动作交给已有 Chat 导航，`ChatView` 接收明确的目标 Thread/侧栏请求并复用 `TaskSessionSidebar`/ChatPanel，`TaskActivityContent` 继续只显示当前 Thread 的来源关系。匿名日记的本地记录保持原行为，但没有服务端身份时不展示或创建定时任务。新增接口 helper、翻译和可操作错误；不把 Agent 的 Task JSON、SSE 缓存或浏览器 localStorage 当成任务来源。 |

这些是实现目标而非已存在的 API 或 capability。真实字段名与操作名应在 Admin DTO 评审后固定，Dream 只能依赖已经发布的精确 capability，不得依据 Admin Drizzle 全局最新 head 猜测可用性。

拟定的数据合同至少包含：定义 ID、owner、来源 Thread、目标模式及绑定 Thread、标题与执行提示、一次/周期规则及 IANA 时区、desired/effective 配置、各自 revision、`next_due_at`、删除前状态；触发 ID、种类（计划或手动）、`planned_at`、配置 revision 快照、领取租约与 fencing 值、状态、错误码、TaskSession ID、目标 Thread ID、输入消息 ID、可空的真实 Run ID、开始/完成时间和跳过摘要。标题和时间进入日期摘要，提示词只在受权详情和编辑接口返回。Admin 查询日期使用 `date=YYYY-MM-DD` 与 `view_timezone`，返回该日计划投影及实际触发，附定义 revision 和最近一次执行状态；未来周期投影不产生写入。创建/修改返回 effective 定义与下次本地/UTC 时间；立即运行返回触发 ID 和当前状态；claim 只向有调度权限的 Dream 服务返回执行所需字段与限时授权。所有接口在查询和写入时校验 owner，跨用户 ID 返回不泄露资源存在性的错误。

## 异常与失败反馈

| 条件 | 服务端处理 | 用户可见反馈 |
| --- | --- | --- |
| 缺时区、非法或不存在的本地时刻 | 创建/编辑不写入；返回字段错误和可选有效时间 | “请选择时区”或“该时间在所选时区不存在，请选其他时间”。 |
| revision 冲突、同一请求重放 | 冲突返回最新定义；相同幂等键返回原结果 | 保留编辑内容并提供“刷新后重试”；重放不产生第二任务。 |
| Admin/PostgreSQL/capability 不可用 | 停止写入和领取，不使用文件或本地数据库代替 | 列表读取失败显示“任务暂不可用，重试”；不能显示空列表或“已启动”。 |
| 权限撤销、目标 Thread 删除或认证到期 | 派发前重新校验；不得沿用旧浏览器 token，触发记失败 | 显示“无法访问关联会话”，提供进入任务详情或重选目标的操作。 |
| 模型配额、Gateway、Runtime 或工具确认阻塞 | 保留确切 Thread/消息和错误码；需要用户参与时沿现有 Thread 确认入口 | 卡片显示失败或“需要处理”，点击打开对应会话；不把超时描述为成功。 |
| 进程重启、跨实例 owner 不明、SSE 断开 | Admin 对账后继续、失败或标 `state_unknown`；EventBus 不作长期记录 | “状态待核对”并可刷新；停止未获 owner 确认时只显示“停止请求已提交”。 |

## 兼容性与影响范围

普通手动 Chat、现有 `create_thread` 与 `wait_threads`、原任务活动弹层、日记笔记列表、Story Workspace Run、Deck/模型资源策略均沿用原业务语义。调度首次启用必须先具备 Admin 前向 migration 与精确 capability，再部署 Dream 消费端和前端日期卡片；旧 Dream 遇到新表只忽略，新 Dream 遇到缺失 capability 拒绝定时功能。历史 `chat_task_session` 不回填为定时定义，原来 Claude Cron 文件不自动导入。用户改时区、定义修改、删除和升级后均保留旧触发的原始配置快照与实际 Thread 关联。

当前源码只证明单进程 Factory 的运行 owner 和已持久化消息路径；跨 Dream 实例停止正在运行的轮次需要现有 owner 路由进一步验证。本设计可以先让到期领取与持久化对账跨实例成立，但不能在 owner 路由未完成时对页面承诺跨实例立即停止。Admin 0068 等候选或未部署 capability 的当前工作树状态也不能当作正常数据库已经可用；实现时以发布和数据库检查为准。

## 测试和验收标准

1. **合同与时间：**对同一 Tool 调用 ID、页面请求键、计划时刻重放，Admin 只留一份定义或触发；一次、每日、每周、每月缺日、时区改动、夏令时不存在与重复钟点、编辑 revision 冲突均有确定结果。可控 clock 验证停机恢复时一次补发一次、周期只补最近到期时刻、运行中跳过后续时刻，且下次时间正确。
2. **执行与恢复：**在明确命名的隔离 PostgreSQL 与假模型上，通过生产 Admin DTO、Dream Tool/后台 worker、公开 Chat 执行入口核对新 Thread 每次一条 TaskSession，继续模式复用原 Thread 与输入队列；同时领取、多实例租约过期、崩溃发生在建 Thread 前后和 final 前后时，不重复启动轮次且能查询 `state_unknown`。普通 Chat 路径与 `wait_threads` 回归通过。
3. **权限与失败：**缺精确 capability、跨用户 Thread、被撤销用户/目标、过期授权、Gateway 拒绝、模型失败和停止 owner 不明都 fail closed；任务详情不暴露提示词以外的凭据、Claude session ID 或数据库内部字段。故障后普通 Agent turn 仍可用。
4. **页面：**浏览器从真实 `CalendarPopup` 选择有笔记、无笔记和有未来周期的日期，均显示正确任务卡；点击实际 Thread、编辑、暂停、恢复、软删除/撤销、立即运行及错误重试均可操作。当前 Chat 任务弹层、既有笔记打开、窄屏和键盘操作回归通过。日期卡片从授权 DTO 刷新，断开 SSE 后不丢历史。
5. **验收证据分层：**上述隔离库与假模型只算技术合同验证。若另行要求“真实业务测试”或真实模型验收，必须按仓库 `AGENTS.md` 使用本机正常 Dream、Admin、Gateway、真实 PostgreSQL、用户指定的现有账户与业务实体，经公开入口发起，并保留正常 Admin 可查的 Thread、Gateway 请求、结算和失败记录；不得把隔离回执报告为真实业务完成。

## 非目标与后续事项

- 不复制 Codex 本地 SQLite、Automation 桌面进程或 Claude Code 的 `scheduled_tasks.json`；不把其尚未证实的单次、时区和界面行为当作产品事实。
- 不做任意历史时刻逐次补跑、不做通用 cron 表达式编辑器、不自动恢复来源 Thread、不根据自然语言推断任务完成、不建立第二套 SSE、输入队列或 workflow Run 状态机。
- 待验证：正常数据库的 Admin migration/capability 发布状态、Dream 实际 Runtime/SDK 的工具资格、跨实例运行 owner 与停止路由、用户时区偏好在公开创建入口的读取方式。验证结果可能调整接线细节，但不得降低本稿的权限、持久化和时间语义。
