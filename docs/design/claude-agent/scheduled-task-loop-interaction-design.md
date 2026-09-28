<!-- [Input] docs/exec 下阶段评审、docs/prd/claude-agent 下正式页面 PRD/骨架图、现有 Chat/CalendarPopup、Admin Drizzle 和 Notion 主页面证据。 -->
<!-- [Output] 首期单次与每日定时任务的交互、业务时序、执行、配置版本、失败反馈及可验证的实施门槛。 -->
<!-- [Pos] Claude Agent 定时任务现行设计；阶段二原文保存在 scheduled-task-loop-interaction-design-20260928-phase2-history.md。 -->
<!-- [Sync] 2026-09-29: 日记页最小纵向切片和四条生产组件 E2E 关闭评审 P0；正常 capability 发布与真实业务验收仍独立。 -->
<!-- [Sync] 2026-09-29: 补齐历史游标、可见页面非终态有界观察和 DST fail-closed 页面合同。 -->
<!-- [Sync] 2026-09-29: 同步独立复评结论为“可直接实施（设计基线）”。 -->
<!-- [Sync] 2026-09-29: 链接正式日记页 PRD/UI 设计，补充创建展示、触发执行、页面操作、并发恢复四张业务时序图及定义/触发状态图。 -->
<!-- [Sync] 2026-09-28: 独立评审后保留单次/每日、暂停/恢复及 revision 验收，改为单份有效配置，并将后台受权执行接线和 Admin capability 作为实施前置条件。 -->
<!-- [Sync] 2026-09-28: Dream Tool、DTO、共享 Chat Factory、日历卡片和隔离到期/手动旅程通过技术验收；正常数据库部署与真实业务验收仍独立。 -->

# 定时任务闭环：首期交互与执行设计

## 文档导航

- [日记日期弹窗 PRD](../../prd/claude-agent/scheduled-task-diary-page-prd.md)
- [日记日期弹窗页面骨架图](../../prd/claude-agent/scheduled-task-diary-page-structure-sketch.md)
- [日记日期弹窗 UI 设计与原型](./scheduled-task-diary-page-ui-design.md)
- [2026-09-29 日记页独立复评与实现关闭回执](../../exec/scheduled-task-diary-prd-review-20260929.md)
- [2026-09-28 阶段三评审（历史阶段）](../../exec/scheduled-task-phase3-design-review-20260928.md)
- [阶段一源码判断](../../exec/scheduled-task-phase1-source-assessment-20260928.md)

设计日期：2026-09-28。Notion「近期需求」主页面要求 Agent 建任务并在日记日期中显示任务卡片与关联会话；两个指定锚点单独读取为空。阶段二的[完整原文](./scheduled-task-loop-interaction-design-20260928-phase2-history.md)仅供历史对照，不作为本稿以外的现行实施范围。

> **当前门禁：最小纵向切片技术验收通过。** Dream Tool、worker、CalendarPopup、移动入口、普通 Chat 回归和隔离 PostgreSQL 跨仓旅程已有通过回执。正常 PostgreSQL capability 发布、Admin 提交归位、真实账户/模型及部署验收仍是独立交付门禁。

页面产品行为以[日记日期弹窗 PRD](../../prd/claude-agent/scheduled-task-diary-page-prd.md)为准，结构分区与状态展开见[页面骨架图](../../prd/claude-agent/scheduled-task-diary-page-structure-sketch.md)，视觉、响应式、无障碍和可运行评审原型见[日记日期弹窗 UI 设计](./scheduled-task-diary-page-ui-design.md)。本稿负责跨 Chat Tool、Dream、Admin、PostgreSQL、ThreadFactory 和 Claude Runtime 的系统行为；四份现行文档必须保持同一 operation、状态与失败语义。

## 背景与问题

实施前，Thread Tool 已可创建独立 Chat Thread，Chat 任务活动区可打开来源关系，CalendarPopup 只显示笔记。Claude Code 原生 Task 清单和 Cron 文件没有提供 Dream 退出后持续触发、逐次持久记录和日期卡片。Codex App 工具合同与 Round52 源码只证明其参考实现的部分语义；不能推出本产品的单次计划、时区、恢复或授权规则。

## 目标与边界

首期完成一条可验收的业务旅程：用户在已认证 Chat 中指定提示词与时间，Agent 通过宿主 Tool 创建**单次或每日**任务；Admin 保存计划，Dream 到期领取并启动一个新的独立 Thread；CalendarPopup 按选中日期展示计划、执行状态和真实 Thread 入口。active/paused 定义可编辑，exhausted 只能立即运行、查看历史和删除；暂停、恢复、删除及撤销删除遵循各自状态规则。浏览器关闭和 Dream 重启不删除计划。

首期只支持新建独立 Thread，周期只支持每天同一本地钟点。继续原 Thread、每周/每月重复、运行中远程停止、CollectionsView 投影和子任务树编辑待独立需求与验收证据明确后再设计。已有普通 turn/resume/cancel、输入队列、SSE、wait_threads、Story Workspace workflow_runs 和现有任务活动入口保持原语义。

### 实现与验收状态

Dream 的 `create_scheduled_task` Tool 只接受标题、提示词和单次/每日规则；宿主从当前轮次注入来源 Thread、用户和调用 ID，以当前受权 `server-persistence` grant 调用 Admin 创建操作。Dream 的日历只通过同源接口读取 Admin 日期、定义和历史，并以 `expected_revision` 执行允许状态下的编辑、暂停、恢复、删除和撤销删除；立即运行使用独立请求键。exhausted 编辑必须被 UI 隐藏并由服务端拒绝，重新排期创建新定义。页面在失败时保留卡片并提供重试，成功后从 Admin 重读，不在浏览器计算触发时刻。

Dream 独立 worker 以服务凭据领取触发，用 `sta_` 解析当前用户与领取范围，再派生目标 Thread 限定的 `server-persistence` 和 `gateway-cli` grant。worker 通过公开 Chat 应用服务完成 Thread、系统配置、Deck、Workflow、模型和 Gateway 前置读取，随后调用 Admin `scheduled-trigger.start` 绑定同一 turn ID，才开始共享 ThreadFactory 流。最终状态使用该 turn 的固定最终消息 ID 请求 Admin 验证；启动回执不确定时只以原请求 ID 重取，仍不确定则对账；续租失败及运行结果无完成证据均进入 `state_unknown`/对账路径。普通 Chat 的轮次、SSE 和取消流程不变。

本仓库的 provider-free 合同测试验证 DTO capability、Tool 授权、启动先于模型与续租失败反馈。[阶段四技术回执](../../exec/scheduled-task-phase4-consumer-receipt-20260928.md)记录了命名隔离 PostgreSQL 上 Admin Drizzle 0069–0072、真实 Admin HTTP、Dream Tool/公开入口、到期与手动触发、假模型以及单独的本机 Chrome 日历交互阶段。这些技术测试不代表真实账户或真实模型验收。目标数据库未发布四项精确 capability 时，定时读写和领取停止，普通 Chat 继续运行。

## 概念与规则

| 对象 | 所有者和必要字段 | 判断条件 |
| --- | --- | --- |
| 定义 | Admin：ID、用户、来源 Thread、标题、提示词、一次/每日规则、IANA 时区、下次 UTC 时刻、状态、revision | 单次只产生一个计划触发；每日可逐日触发；两者都没有默认执行时刻。 |
| 触发 | Admin：定义 ID、种类（计划或手动）、计划 UTC 时刻或手动请求键、定义 revision 快照、领取标识与期限、状态、错误码、目标 TaskSession/Thread/输入消息/最终消息 ID | 同一定义和计划时刻最多一条计划触发；同一手动请求键最多一条手动触发；领取重试不产生第二个目标轮次。 |
| 独立任务关系 | 既有 chat_task_session | 每次实际派发沿原子建目标 Thread 与首条消息的既有语义；定时定义本身不是 TaskSession。 |
| 轮次和结果 | 既有 Chat 持久消息、ThreadFactory 与 Service | 只有该轮次最终消息已提交，触发才可标成功；SSE 帧与浏览器连接状态不是结果。 |

### 创建、配置和版本

宿主 Tool `create_scheduled_task` 已实现。模型只传标题、提示词、单次本地日期时间或每日本地钟点，以及 IANA 时区；宿主从当前受权轮次取得用户、来源 Thread 和 Tool 调用 ID。缺少明确规则或时区时返回字段错误，请 Agent 向用户补齐；不得取服务器本地时区。创建时对时区、未来时间、用户及来源 Thread 权限、精确 schema capability 和幂等调用键作校验。成功回执包含任务 ID、原规则中的当地时间、下一次 UTC 时间、时区、状态和 revision；不加第二次确认弹窗。

配置语义分别是：default 为界面尚未保存的建议，例如当前账户时区；desired 为用户本次提交、尚待校验的输入；effective 为 Admin 成功提交且调度者可读取的定义；revision 为每次成功编辑、暂停、恢复、删除或撤销删除后递增的并发版本。首期没有异步审批或应用配置阶段，因此 **Admin 只持久化一份 effective 定义和一个 revision**。校验失败时 desired 留在当前编辑界面，effective 与 revision 不变；不存在三份完整配置同事务落库的业务理由。触发记录引用领取时的 revision、计划时刻与启动所需内容，后续编辑不改写已领取的输入。页面带预期 revision 修改；冲突返回最新定义供用户重试。立即运行不修改计划时刻或定义 revision。

scheduled-task.edit 只接受 active 或 paused 定义。exhausted 是单次计划已完成的终态，不允许修改标题、提示词或规则来重新排期；用户需要新时间时由 Chat Tool 创建新的定义。exhausted 的定义级操作只有立即运行、查看历史和删除。

## 用户交互流程

1. 已认证用户在 Chat 指定提示词和明确时间；Tool 保存成功后 Agent 复述当地时间、时区与任务入口。Tool 不获得模型传入的用户 ID、Claude session ID 或凭据。
2. CalendarPopup 保留笔记列表；选中日期出现受权任务卡片，只有任务没有笔记时仍显示任务。卡片包含标题、计划时间、时区、待执行或执行状态、延迟与错误说明。执行真正建立 Thread 后才显示“打开会话”；点击后由 App 到 ChatView 的明确导航参数打开既有 ChatPanel/TaskSessionSidebar，不能仅修改已挂载页面的地址栏。
3. active/paused 定义可编辑标题、提示词或规则；暂停、恢复、软删除或撤销删除都带预期 revision，并刷新服务端返回的 effective 定义与下一次时刻。暂停后不再产生后续触发；编辑暂停中的规则后，恢复按新 revision 计算下一次计划。exhausted 不可编辑，重新排期必须新建定义，但允许显式手动运行、查看历史或删除。删除不停止已经领取的轮次，历史触发仍可查询。历史满页时以最旧 `created_at` 调用既有 `before_created_at` 游标追加，并按 trigger ID 去重。立即运行使用请求幂等键创建手动触发，返回该触发状态，不推迟每日计划；paused/deleted 定义不能手动运行。查询失败显示“任务暂不可用”与重试，不把失败响应渲染为空日。
4. 页面重开从 Admin 查询定义、触发和目标 Thread。若模型轮次需要既有工具确认，卡片引导进入该 Thread；SSE 只用于当前可订阅轮次，断线后仍以持久记录显示结果。匿名日记不提供服务端定时任务入口。
5. 选中日期存在 `claimed`、`queued` 或 `running` 时，页面只在浏览器可见且前次读取已结束后进行有界刷新；进入终态、切换日期、页面隐藏或达到观察上限即停止。`state_unknown` 依赖 Admin 对账与用户手动核查，不以无限轮询或新 trigger 替代。

### 业务时序一：Chat Tool 创建并在日记日期展示

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant Chat as Chat 界面
    participant Agent as Claude Agent
    participant Host as Dream Tool Host
    participant Admin as Admin 定时任务服务
    participant DB as PostgreSQL
    participant Diary as 日记日期弹窗

    U->>Chat: 说明标题、提示词、单次/每日当地时间与时区
    Chat->>Agent: 进入现有受权 turn
    Agent->>Host: create_scheduled_task(title, prompt, rule)
    Host->>Host: 校验严格字段；注入当前用户、来源 Thread、tool_call_id
    Host->>Host: 由来源消息与 tool_call_id 生成稳定 create_request_key
    Host->>Admin: scheduled-task.create(source_thread_id, create_request_key, title, prompt, rule)
    Admin->>Admin: 校验 dream:write、精确 capability、用户与来源 Thread
    alt 校验通过
        Admin->>DB: 事务写 effective 定义、revision=1、next_run_at
        DB-->>Admin: 唯一 create_request_key 保证重放返回同一任务
        Admin-->>Host: 任务 ID、rule、next_run_at、status、revision
        Host-->>Agent: Tool 成功回执
        Agent-->>Chat: 复述当地时间、IANA 时区与任务入口
        Chat-->>U: 显示创建结果
        U->>Diary: 打开日历并选择日期
        Diary->>Admin: 经 Dream 同源受权入口调用 scheduled-task.day(date, timezone)
        Admin->>DB: 按当前用户读取定义与当日触发
        DB-->>Admin: effective 定义和持久触发记录
        Admin-->>Diary: tasks + triggers
        Diary-->>U: 按“日期摘要 → 定时任务 → 日记”展示
    else rule 字段、当地时间或时区无效
        Admin-->>Host: 422 + 稳定字段错误；不写定义
        Host-->>Agent: 创建失败
        Agent-->>U: 说明缺失字段并请求修正
    else capability、认证或来源 Thread 校验失败
        Admin-->>Host: 401/403/503 + 安全错误码；不写定义
        Host-->>Agent: 定时任务暂不可用
        Diary-->>U: 任务区显示登录/暂不可用与重试，日记区继续可用
    end
~~~

## 系统执行流程

### 业务时序二：到期或立即运行进入共享 Chat 执行链

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant Diary as 日记日期弹窗
    participant Worker as Dream ScheduledTaskCoordinator
    participant Admin as Admin 定时任务服务
    participant DB as PostgreSQL
    participant Factory as ThreadFactory / Chat Service
    participant Runtime as Claude Runtime

    alt 用户立即运行
        U->>Diary: 点击“立即运行”
        Diary->>Admin: 经 Dream 调用 scheduled-task.run(manual_request_key)
        Admin->>DB: 以 manual_request_key 幂等创建手动触发
        Admin-->>Diary: trigger ID 与持久状态/已有未结束触发
        Diary-->>U: 显示正在准备或已有执行状态
    else 计划到期
        Note over Admin,DB: active 定义的 next_run_at 已到数据库当前时间
    end

    Worker->>Admin: scheduled-trigger.claim(request_id)
    Admin->>DB: 以数据库时间、事务锁、唯一约束领取计划或手动触发
    DB-->>Admin: trigger + claim_id
    Admin-->>Worker: 唯一领取结果

    Worker->>Admin: scheduled-trigger.prepare(trigger_id, claim_id)
    Admin->>DB: 幂等创建或复用 TaskSession、目标 Thread、首条输入和 sta_ 授权
    Admin-->>Worker: prepared + task_session + authority_token + authority_expires_at
    Worker->>Admin: scheduled-trigger.authority.resolve(sta_)
    Admin-->>Worker: 用户、来源/目标 Thread 与限时用途
    Worker->>Factory: 共享 Chat 应用服务前置校验（Thread、配置、Deck、Workflow、模型、Gateway）
    alt start 前前置校验确定失败
        Worker->>Admin: scheduled-trigger.finish(status=failed, error_code=SCHEDULE_PREFLIGHT_FAILED)
        Admin-->>Diary: failed
        Diary-->>U: 显示可行动失败说明；未来计划不受影响
    else 前置校验通过
        Note over Worker,Factory: 此时只得到响应生成器，尚未启动模型
        Worker->>Admin: scheduled-trigger.start(trigger_id, claim_id, target_turn_id)
        alt start 回执不确定
            Worker->>Admin: 用原 request_id 重放 start；仍不确定则 scheduled-trigger.reconcile
            Admin->>DB: 核查 target_turn_id 绑定；不生成新 turn
            Admin-->>Diary: 已证实状态或 state_unknown
            Diary-->>U: 显示“正在核查执行结果”；不允许盲目再次运行
        else start 已确认
            Admin->>DB: 持久绑定同一 target_turn_id
            Admin-->>Worker: running
            Worker->>Factory: 开始消费共享响应流
            Factory->>Runtime: 启动同一 Thread 的 Claude turn
            loop turn 执行期间
                Worker->>Admin: scheduled-trigger.renew(trigger_id, claim_id)
                Admin-->>Worker: 新 lease 期限
            end
            Runtime-->>Factory: 模型事件与最终结果
            Factory->>DB: 通过既有 Chat persistence 提交该 turn 最终消息
            Factory-->>Worker: owner completion
            alt 合法 final 已提交且 lease 有效
                Worker->>Admin: scheduled-trigger.finish(status=succeeded, final_message_id)
                Admin->>DB: 核对 final 属于目标 Thread 和 target_turn_id 后结算
                Admin-->>Diary: 后续 day/history 查询返回 succeeded
                Diary-->>U: 显示“已完成”与真实“打开会话”入口
            else 续租失败或最终结果不能确认
                Worker->>Admin: scheduled-trigger.finish(status=state_unknown) / reconcile
                Admin->>DB: 核查 turn 绑定、输入和最终消息
                Admin-->>Diary: 已证实终态或 state_unknown
                Diary-->>U: 显示“正在核查执行结果”；不允许盲目再次运行
            end
        end
    end
~~~

### 到期恢复和权限

Dream 独立后台 worker 仅调用 Admin 的受限领取操作；Admin 使用数据库时间、事务锁、唯一约束和领取期限原子领取。单次计划在服务恢复后仍未领取、定义仍 active 时领取一次，并显示实际启动晚于计划时刻。每日计划在停机恢复时仅领取最近一次已到期时刻；更早未执行时刻记为跳过范围，不逐次补跑，随后计算下一次未来时刻。同一定义有未结束触发时不并发启动第二轮，新的到期时刻记为跳过并推进计划。跨实例竞争只有一个领取者能创建或更新同一触发；进程中断后先按触发 ID 查询 TaskSession、Thread、输入消息和 final，再重领未派发项或将无法判断的项置为 state_unknown。不能承诺外部模型调用绝对恰好一次。

后台派发须有 **Admin 签发且限定触发 ID、用户、来源与目标 Thread、期限和用途的服务端授权**。发起前重新校验用户与 Thread 关系、模型和 Deck 权限、定义状态及授权期限；不能保存创建时的浏览器 OAuth token 待日后使用。权限或 capability 缺失时停止派发、保存安全错误码，普通 Chat 不受调度 worker 故障影响。Admin 只管理持久化与授权；Dream 不执行运行时建表、SQLite 回退或基于部署环境名称的业务分支。

### 业务时序三：日记页修改任务与处理 revision 冲突

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant Diary as 日记日期弹窗
    participant Dream as Dream 受权 API
    participant Admin as Admin 定时任务服务
    participant DB as PostgreSQL
    participant Chat as 既有 Chat 导航

    U->>Diary: 选择日期
    Diary->>Dream: GET scheduled-tasks/day
    Dream->>Admin: scheduled-task.day
    Admin->>DB: 读取 effective、revision 与当日 triggers
    DB-->>Admin: effective、revision 与当日 triggers
    Admin-->>Dream: 日期 DTO
    Dream-->>Diary: 日期数据

    alt 编辑（仅 active/paused）
        U->>Diary: 修改 desired 草稿并保存
        Diary->>Dream: POST /{id}/edit + expected_revision
        Dream->>Admin: scheduled-task.edit
    else 暂停
        U->>Diary: 点击暂停
        Diary->>Dream: POST /{id}/pause + expected_revision
        Dream->>Admin: scheduled-task.pause
    else 恢复
        U->>Diary: 点击恢复
        Diary->>Dream: POST /{id}/resume + expected_revision
        Dream->>Admin: scheduled-task.resume
    else 立即运行
        U->>Diary: 点击立即运行
        Diary->>Dream: POST /{id}/run + 稳定 manual_request_key
        Dream->>Admin: scheduled-task.run
    else 删除
        U->>Diary: 点击删除
        Diary->>Dream: POST /{id}/delete + expected_revision
        Dream->>Admin: scheduled-task.delete
    else 撤销删除
        U->>Diary: 点击撤销
        Diary->>Dream: POST /{id}/restore + expected_revision
        Dream->>Admin: scheduled-task.restore
    end

    Admin->>DB: 校验当前用户、定义状态、expected_revision 或手动请求键
    alt revision 匹配或手动请求键首次/重放
        DB-->>Admin: 提交并返回 effective、新 revision/next_run_at 或同一 trigger
        Admin-->>Dream: 成功响应
        Dream-->>Diary: 服务端确认的任务或触发
        Diary->>Dream: 重读 day；需要时 GET /{id}/history
        Dream->>Admin: scheduled-task.day / scheduled-task.history
        Admin-->>Dream: 最新持久事实
        Dream-->>Diary: 最新日期/历史 DTO
        Diary-->>U: 就地更新卡片、撤销条或执行历史
    else expected_revision 已过期
        DB-->>Admin: SCHEDULE_REVISION_CONFLICT + 最新定义
        Admin-->>Dream: 409 + 稳定错误码
        Dream-->>Diary: 冲突响应
        Diary-->>U: 保留 desired 草稿并标记差异，禁止本地覆盖 latest effective
    else exhausted 编辑、paused/deleted 立即运行或其他校验失败
        Admin-->>Dream: 稳定错误码；effective/revision 不变
        Dream-->>Diary: 操作失败
        Diary-->>U: 卡片内说明未生效并提供适用重试
    end

    opt 某条 trigger 已有 target_thread_id
        U->>Diary: 点击“打开会话”
        Diary->>Chat: 使用现有导航打开该目标 Thread
        Chat-->>U: 展示持久消息和当前运行状态
    end
~~~

### 业务时序四：双 worker、重启与未知结果对账

~~~mermaid
sequenceDiagram
    autonumber
    participant A as Worker A
    participant B as Worker B / 重启后 Worker
    participant Admin as Admin 定时任务服务
    participant DB as PostgreSQL
    participant Factory as ThreadFactory / Chat Persistence
    participant Diary as 日记日期弹窗

    par 两个实例同时轮询
        A->>Admin: scheduled-trigger.claim(request A)
        B->>Admin: scheduled-trigger.claim(request B)
    end
    Admin->>DB: 数据库时间 + 行锁/唯一约束竞争
    DB-->>Admin: 只向一个请求返回 trigger + claim_id
    Admin-->>A: 获得领取（示例）
    Admin-->>B: 空领取；不得创建第二触发
    A->>Admin: scheduled-trigger.prepare(trigger_id, claim_id)
    Admin->>DB: 幂等创建/复用同一 TaskSession、Thread 与输入

    alt start 前进程退出
        Note over A: 未绑定 target_turn_id，不存在模型启动证据
        B->>Admin: lease 到期后 claim / scheduled-trigger.reconcile
        Admin->>DB: 按 trigger_id 检查 prepared 资产和 start 绑定
        DB-->>Admin: 复用同一 TaskSession/Thread/输入
        Admin-->>B: 可继续原触发；禁止新建重复输入
    else start 已提交但回执丢失或进程退出
        A->>Admin: scheduled-trigger.start(固定 target_turn_id, 原 request_id)
        Admin->>DB: start 可能已提交
        B->>Admin: scheduled-trigger.reconcile(trigger_id)
        Admin->>DB: 核对 target_turn_id、持久输入和 final_message_id
        alt 已找到同一 turn 的合法 final
            DB-->>Admin: succeeded
            Admin-->>Diary: 已完成
        else 可证明前置失败且模型未启动
            DB-->>Admin: failed
            Admin-->>Diary: 执行失败
        else 不能证明是否启动或完成
            DB-->>Admin: state_unknown
            Admin-->>Diary: 结果核查中
            Diary-->>Diary: 禁用盲目再次运行；保留已有会话入口
        end
    else 运行时 lease 续租失败
        Factory-->>A: owner 仍按共享 Chat 生命周期收束
        A->>Admin: scheduled-trigger.finish(state_unknown, SCHEDULE_RENEW_FAILED)
        Admin->>DB: 保存未知终态并等待 reconcile
        Admin-->>Diary: state_unknown
    end
~~~

## 状态与转换

### 时间、日期与状态

单次任务在保存时将用户指定的本地时刻与 IANA 时区解析为唯一 UTC 时刻。所选本地时刻不存在时以 `SCHEDULE_LOCAL_TIME_MISSING` 拒绝；夏令时造成两个 UTC 候选且未选择偏移时以 `SCHEDULE_OFFSET_REQUIRED` 拒绝，旧偏移不匹配时以 `SCHEDULE_OFFSET_INVALID` 拒绝。当前 Admin 合同未返回候选列表，CalendarPopup 因此保留 desired 草稿、分别说明原因并要求改用无歧义时刻，不能在浏览器猜偏移。未来若提供候选选择，必须由 Admin 返回可验证候选后再扩展 DTO。每日规则保存本地钟点和固定 IANA 时区：某天该钟点不存在则跳过这一天，重复出现时取较早的第一次；Admin 计算下一个 UTC 时刻，Dream 不自行计算。当前账户时区变化不重写已保存计划；CalendarPopup 以其当前展示时区将计划 UTC 时刻分组到日期，卡片同时显示任务原时区。每日未来日期从规则只读投影，不预建无穷触发记录。**这些是本产品的设计决策**，不是 Codex App 的已证实行为。

定义可从 active 暂停为 paused，再恢复为 active；软删除后成为 deleted，撤销后恢复删除前的 active、paused 或 exhausted，并按原规则重算未来计划。单次计划领取后成为 exhausted，撤销删除也不重新安排该计划；exhausted 不可编辑，重新排期必须新建定义。每日定义领取后仍为 active，并推进下一次 UTC 时刻。暂停或删除阻止后续尚未领取的触发，不停止已经领取的轮次；恢复从当前数据库时间计算下一次未来时刻，暂停期间的日子不补发。active/paused 编辑更新 revision 与下一次时刻，旧 revision 已领取的轮次按快照继续。手动立即运行适用于 active 或 exhausted 定义，创建独立手动触发，不改变计划时刻；如果已有该定义的未结束触发，返回该触发状态，不启动第二轮。paused 或 deleted 定义不可手动运行。触发从 claimed，经目标首条消息持久化为 queued、轮次开始为 running，最终已提交则为 succeeded；确定失败为 failed；无法确定是否已启动或完成则为 state_unknown。租约到期只触发对账，不自动判失败或重发模型轮次。卡片只显示这些持久事实，不显示推断百分比。

### 定义状态图

~~~mermaid
stateDiagram-v2
    [*] --> active: scheduled-task.create
    active --> active: scheduled-task.edit / scheduled-task.run
    paused --> paused: scheduled-task.edit
    exhausted --> exhausted: scheduled-task.run / 查看历史
    active --> paused: scheduled-task.pause
    paused --> active: scheduled-task.resume（从数据库当前时间重算）
    active --> exhausted: 单次计划被领取
    active --> deleted: scheduled-task.delete（记录删除前状态）
    paused --> deleted: scheduled-task.delete（记录删除前状态）
    exhausted --> deleted: scheduled-task.delete（记录删除前状态）
    deleted --> active: scheduled-task.restore（删除前为 active）
    deleted --> paused: scheduled-task.restore（删除前为 paused）
    deleted --> exhausted: scheduled-task.restore（删除前为 exhausted）
~~~

scheduled-task.run 只创建或重放手动触发，不改变定义 revision、status 或 next_run_at。scheduled-task.edit 仅接受 active/paused；pause、resume、delete、restore 也必须符合定义状态。上述定义 mutation 都必须匹配 expected_revision，成功后 revision 递增；exhausted 编辑返回稳定错误，effective 与 revision 不变。

### 触发状态图

~~~mermaid
stateDiagram-v2
    [*] --> claimed: scheduled-trigger.claim 或 scheduled-task.run
    [*] --> skipped: 更早错过时刻或同定义已有未结束触发
    claimed --> queued: scheduled-trigger.prepare 持久化目标 Thread 与输入
    claimed --> failed: start 前前置校验确定失败
    claimed --> state_unknown: prepare/start 结果无法确认
    queued --> running: scheduled-trigger.start 绑定 target_turn_id
    queued --> state_unknown: start 回执无法确认
    running --> succeeded: scheduled-trigger.finish 核对合法 final
    running --> failed: scheduled-trigger.finish 记录确定失败
    running --> state_unknown: 续租失败或完成证据不足
    state_unknown --> succeeded: scheduled-trigger.reconcile 找到合法 final
    state_unknown --> failed: scheduled-trigger.reconcile 证明失败
~~~

state_unknown 是持久执行事实，不能由页面映射为 failed，也不能触发新的模型 turn。scheduled-trigger.reconcile 只核对原 trigger、TaskSession、Thread、turn 和 final；无法得出确定结论时保持 state_unknown。

## 数据及接口影响

1. **Admin expand。** 先在 Admin Drizzle 提交定义、触发、计划时刻与手动请求键唯一约束、领取与审计字段，发布精确 capability 和受权 DTO（创建、日期查询、编辑、暂停、恢复、软删除、撤销、立即运行、领取和结果对账）；在正常目标数据库核实 capability 后 Dream 才启用此功能。2026-09-28 的只读检查显示本机 Admin 数据库没有定时任务表或 capability，当前不可启用派发；这项前置可以在实施阶段完成。
2. **统一受权执行接线。** 公开 `POST /api/claude-agent` 和后台 worker 共用 `claude_agent.py` 的 Chat 应用服务，依次校验目标 Thread、系统配置、Deck/Voice、Workflow 和模型。worker 只根据 Admin 的 `sta_` 授权派生目标 Thread 限定的两种 `idg_` grant，先以 `scheduled-trigger.start` 保存 turn ID，再进入原 ThreadFactory、资源 admission、Service 和消息持久化。普通公开 SSE 仍在响应被消费时懒启动 Factory；后台路径使用完成句柄等待 owner 结束。
3. **调度与页面。** Dream Tool 创建后由独立 worker 从 Admin 领取；Admin 以触发 ID 幂等创建 TaskSession/Thread/首条消息。worker 使用已提交的同一 turn 的 final 请求 Admin 结算，不从 SSE 或最近消息推断完成。CalendarPopup 经受权日期 DTO 投影，复用现有 Chat 导航。日期卡片和 worker 都不能从 Claude Task JSON、Cron 文件、SSE 缓存或浏览器存储构造业务事实。

| 接口或数据 | 执行模块与读写边界 |
| --- | --- |
| 定义、触发、TaskSession、领取与审计 | Admin Drizzle 0069–0072 及 `scheduled-task.*` / `scheduled-trigger.*` 操作；Dream 没有 SQL 或 runtime DDL。 |
| Tool 请求 | `thread_tool.py` 只接收标题、提示词和 once/daily 规则；`session_projection_broker.py` 转发到当前轮次 host，由当前 grant 注入身份与来源 Thread。 |
| 日期、详情、历史和修改 | Dream `GET /api/claude-agent/scheduled-tasks/day`、`GET /{task_id}`、`GET /{task_id}/history`、`POST /{task_id}/{action}`；浏览器同源请求带会话 Cookie 与 `x-ink-csrf`，Next BFF 解析会话后向 Dream 注入 `Authorization: Bearer`，Dream 验证当前用户并以其 OAuth 凭据调用 Admin。浏览器不保存 `idg_` 或 `sta_`。 |
| 目标轮次与最终消息 | Dream `scheduled_task_coordinator.py` 及共享 Chat Service/ThreadFactory；Admin `scheduled-trigger.start/finish/reconcile` 核对同一 turn。 |

## 异常与失败反馈

| 条件 | 后端处理 | 用户可见结果 |
| --- | --- | --- |
| 时间无效、缺时区、revision 冲突 | 拒绝写入；保留 effective | 指出字段或提供最新定义，编辑内容留在界面。 |
| Admin、数据库或精确 capability 不可用 | 停止定时任务读写与领取 | 显示暂不可用和重试；不显示“已安排”。 |
| 权限撤销、来源 Thread 不可访问、授权到期 | 派发前拒绝并记录失败 | 显示无法访问关联会话或任务未启动。 |
| Gateway、Runtime、模型、工具确认异常 | 按真实消息和 final 对账；保存安全错误码 | 显示失败、需要处理或状态待核对，并可打开已有目标 Thread。 |
| Dream 重启、并发领取、网络结果不明 | 按触发 ID 对账；不盲目重复模型调用 | 保留计划、执行历史和明确的不确定状态。 |

## 兼容性与影响范围

已有 Chat、Thread Tool、wait_threads、输入队列、SSE、Story Workspace Run 和笔记功能不改变。旧 TaskSession 或 Claude Cron 文件不自动导入。Admin 前向 migration → 精确 capability 验证 → Dream 双版本兼容消费 → 技术与正常业务验收 → 后续 contract 的顺序不能倒置。缺少 capability 时仅定时操作和领取失败，普通 Chat 继续运行。

## 测试和验收标准

技术合同在明确命名且核对身份的隔离 PostgreSQL、受控时钟和假模型上，通过**公开生产 DTO、真实 Tool 协议与同一 Chat 应用服务**核验：创建幂等、单次与每日触发、夏令时缺失与重复时刻、时区日期投影、暂停后不再触发、暂停期间编辑计划并在恢复后按新 revision 触发、exhausted 编辑被拒绝且重新排期创建新定义、编辑与领取竞争、revision 冲突、手动运行不推进计划、删除后不领取与撤销后的新计划、停机后每日只补最近一次、双 worker 竞争、创建 Thread 前后以及 final 前后的崩溃对账。必须断言一次触发最多一条 TaskSession/输入消息，未知结果不会重发；普通 turn/resume/cancel/SSE、现有任务活动区和笔记弹窗不回归。

浏览器旅程从用户 Chat 创建单次或每日任务开始，选择有笔记、无笔记及仅有任务的日期，确认 A3 只有日记标记，查看状态、编辑 active/paused、验证 exhausted 无编辑且仅可立即运行/查看历史/删除，再覆盖暂停、恢复、手动运行、删除、撤销并打开实际 Thread；刷新后历史仍在。隔离库与假模型结果仅为技术验证。若用户另行要求真实业务或真实模型验收，按仓库 AGENTS.md 使用正常 Dream、Admin、Gateway、真实 PostgreSQL、指定现有账户及公开入口，并保留 Admin 可查询的 Run/Thread/Gateway/结算/失败记录。

| 验收点 | 当前状态与证据 |
| --- | --- |
| Admin schema、到期/手动唯一性、租约和 final 核对 | 隔离 PostgreSQL 的 Admin 集成测试与[阶段四技术回执](../../exec/scheduled-task-phase4-consumer-receipt-20260928.md)；正常数据库 capability 发布仍待部署。 |
| Dream Tool、公开日期/历史/修改、到期和手动触发、Factory 最终消息 | 隔离 Admin HTTP 与 Dream 探针通过；实际到达下一 UTC 整分钟后产生 `kind=scheduled` 触发，模型替身共调用两次。 |
| 日历卡片、操作与笔记兼容 | 本机 Chrome fixture 阶段通过；该阶段拦截同源 API，未与隔离 Admin HTTP 同一浏览器进程串行执行。 |
| 普通 Chat、resume/cancel、SSE 与工具回归 | Dream 定向回归与 broker 测试通过；真实模型和正常账户验收未执行。 |

## 非目标与后续事项

每周、每月及更多周期表达需要各自的重复规则、错过时刻和夏令时验收；继续原 Thread 需要长期服务授权与恢复/队列权限的额外证明。运行中跨实例停止和 CollectionsView 投影需各自说明用户目标，再进入实施范围。A3 月历任务/需处理标记等待 Admin-owned、owner-filtered 的月摘要 operation，浏览器不得通过逐日调用 scheduled-task.day 拼出月摘要。阶段二原文的其余规则不随本稿自动生效。
