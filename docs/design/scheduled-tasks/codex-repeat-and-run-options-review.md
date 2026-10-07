<!-- [Input] Codex repeat PRD、正式设计、html-design-workflow 四阶段产物、现有 v2 实现与 Codex 客户端恢复代码。 -->
<!-- [Output] 实施前独立符合性/过度设计复评、R1—R6 收敛回执与需求—设计—实现—测试追踪矩阵。 -->
<!-- [Pos] scheduled-tasks 本轮设计门禁；实现栏在代码和验证完成前保持“待实施”。 -->
<!-- [Sync] 2026-10-07: 最终复评 R1—R6 全部闭合，设计门禁结论为可直接实施。 -->

# Codex 风格周期与高级运行选项：独立实施前评审

## 1. 复评结论

**结论：可直接实施。**

PRD 与正式设计已经闭合 R1—R6：

- migration 明确替换永久 target Thread 唯一约束；
- 存量 null 模型与首次 v3 编辑必选模型的兼容边界明确；
- 页面和 Tool 只提交结构化 rule，Admin 单点生成 canonical RRULE；
- 源 Thread 删除沿用现有 `ON DELETE CASCADE`；
- source resume 最终进入 `ClaudeAgentThreadFactory.run_streaming()` 的 per-session 原子 admission。
- 同源 open trigger 冲突由 Admin claim/manual-run 事务直接写入 `failed/SCHEDULE_SOURCE_THREAD_BUSY`、推进计划并返回 idle，不向 Coordinator 派发。

没有发现需要增加新系统、额外业务状态或关键产品决策的阻塞项。所有代码和测试仍为待实施，不得把本评审称为功能验收。

## 2. 证据核对

### 2.1 已有能力与复用路径

| 结论 | 证据 | 评审 |
|---|---|---|
| v2 已有持久化 definition、revision、trigger、lease、恢复游标 | Admin `packages/db/src/schema/dream.ts:708-795`；`chatScheduledTaskService.ts` 的 `claimOneV2`、`prepareOne`、`startOne`、`finishOne` | 直接扩展现有表与 operation version，未提出第二套 scheduler。 |
| 当前 trigger 经 TaskSession 新建 Thread | Admin `chatScheduledTaskService.ts:473-519`；Dream `scheduled_task_coordinator.py:188-311` | `new_thread_each_run` 直接复用；`source_thread` 通过同一 turn 入口扩展 nullable TaskSession。 |
| 普通请求按用户模型目录解析 alias | Dream `backend/routers/claude_agent.py:1271-1289` | 定时执行继续复用 resolver，不把未验证 alias 直接交给 Runtime。 |
| Tool 的 source Thread 由宿主捕获 | Dream `_ThreadToolTurnProvider._perform`，`backend/routers/claude_agent.py:2248-2277` | `source_thread_id` 和 Tool 默认模型保持服务端所有权。 |
| ThreadFactory 有最终原子入口 | Dream `backend/claude_agent/thread_factory.py` 的 `ClaudeAgentThreadFactory.run_streaming` | 设计已明确 source scheduled turn 不能用一次 `accepting_input()` 查询替代该入口。 |
| Codex 恢复代码有五类 schedule mode 与受限 RRULE | `src/shared/automations/contracts.ts` 的 `AutomationScheduleMode`；`automation-schedule.ts:38-166` | 五类菜单、每小时整点、工作日/每周结构有代码证据。 |
| Codex 有新会话和继续会话两条生产入口 | `src/main/automations/automation-service.ts:445-466` | 本项目统一为 `run_thread_mode` 是用户明确要求的产品适配。 |
| Codex heartbeat 的模型为 null | `automation-service.ts:213-220, 461-466` | 本项目允许 source Thread 选模型是明确的产品差异，正式设计已标注。 |

### 2.2 文档交付门禁

| 检查项 | 结果 | 证据/意见 |
|---|---|---|
| PRD 业务目录 | 通过 | `docs/prd/scheduled-tasks/codex-repeat-and-run-options.md`。 |
| 背景、目标、概念规则 | 通过 | PRD 第 1—3 节。 |
| 桌面与窄屏骨架 | 通过 | PRD 第 5.1—5.3 节包含主要区域、弹层和滚动范围。 |
| 正常业务时序 | 通过 | 正式设计第 5.1 节覆盖保存、claim、两种 Thread 路径、模型和结果跳转。 |
| 异常与恢复时序 | 通过 | 第 5.2 节明确由 Admin claim 事务写 failed、推进 `next_run_at` 并返回 idle；Coordinator 不取得 claim、不派发。 |
| 编辑时序与状态图 | 通过 | 第 5.3、6 节覆盖 optimistic revision、trigger 快照和恢复状态。 |
| default/desired/effective/revision | 通过 | PRD 第 3.1 节；workflow 第 3 阶段第 4 节。 |
| html-design-workflow 四阶段 | 通过 | `workspace/1_prd_draft.md` 至 `4_ui_design.md` 均存在，正式正文已吸收骨架和规则。 |
| Mermaid 可渲染性 | 文本审查通过，渲染待验证 | 4 个 Mermaid fenced block 的参与者、分支和状态语义一致；实施验证仍需运行仓库 Mermaid render 检查。 |

## 3. R1—R6 收敛回执

| 编号 | 复评状态 | 修订证据 | 尚需动作 |
|---|---|---|---|
| R1 target Thread 唯一约束 | 已闭合 | 设计 3.4、7.1 明确 drop `uq_chat_scheduled_trigger_target_thread`，分别建立 new-thread 历史唯一和 source-thread open 唯一。 | 实现 migration 与连续两次 source 历史/并发测试。 |
| R2 同源冲突事务结果 | 已闭合 | PRD 3.3、6 与设计 3.4、5.2、8 明确 Admin 在 claim/manual-run 事务内写 failed 历史、推进计划、返回 idle 且禁止热循环。 | 实现同源 scheduled/manual、多实例竞争的事务与集成测试。 |
| R3 legacy null model | 已闭合 | PRD 3.4；设计 3.2、5.1、9 明确存量 null 沿用原默认解析，首次 v3 编辑必须选 exact alias。 | 实现 DTO/claim/prepare/Coordinator 的 legacy 分支与迁移测试。 |
| R4 结构化 rule 与 RRULE 所有权 | 已闭合 | PRD 3.2；设计 3.3、7.2：公开 DTO 是 `once/interval/daily/hourly/weekly`，Admin 唯一生成 canonical RRULE，不向前端/Dream 暴露 raw RRULE。 | 实现同一 Admin parser/serializer/next-run。 |
| R5 source Thread 删除 | 已闭合 | PRD 3.3；设计 7.1、9 明确沿用 `ON DELETE CASCADE`，删除源聊天同时删除任务和 trigger 历史。 | 增加 FK 行为和页面刷新回归。 |
| R6 source resume admission | 已闭合 | PRD 3.3、6；设计 3.4、5.1、8、9 明确 `ClaudeAgentThreadFactory.run_streaming()` 是最终 per-session 原子 admission，输入始终绑定 trigger。 | 实现并测试普通 turn 与 scheduled turn 竞态。 |

## 4. 目标符合性与过度设计判断

### 4.1 五类周期

设计用受限结构化规则表达“每小时、每天、工作日、每周、自定义”，同时保留一次性和每 N 分钟/小时。每小时 `00` 分有 Codex 恢复代码依据；工作日明确为周一至周五且不推断法定节假日。Admin 负责 canonical RRULE，前端和 Dream 不复制 serializer。

**判断：目标符合，没有引入通用 cron、节假日引擎或工作流编排器。**

### 4.2 Thread 模式

`new_thread_each_run` 复用 TaskSession；`source_thread` 复用现有消息、Thread、Turn、resume、ThreadFactory 和持久化入口。历史 source trigger 允许共享 target Thread，open trigger 仍受数据库约束。

**判断：架构方向、schema 约束和冲突事务语义已经闭合。**

### 4.3 模型选择

模型列表复用 Gateway/Admin 目录，新建/编辑保存 exact alias，trigger 领取时快照，执行时重新做用户可调用性校验。存量 null 是明确的兼容分支；用户首次 v3 保存后进入完整快照语义。

**判断：目标符合，没有隐式 fallback 或新模型目录。** legacy null 代表既有语义，不应在 UI 中伪装成已固定模型。

### 4.4 Task、Thread、Run、resume、cancel 与事件流

设计不修改普通 Chat admission、resume、cancel、SSE 和工具确认。scheduled execution 继续用 trigger 记录，模型执行继续走 Claude Agent 生产入口，source resume 不能绕过 ThreadFactory。

**判断：保持现有状态机和公开入口，没有复制 parser、reducer、SSE 或 Runtime session。**

### 4.5 无业务价值状态、技术常量和未经证实规则

- `Editing/Saving/Conflict/Effective` 是 UI/配置状态，`claimed/running/state_unknown` 是既有执行状态，均有输入、转换和失败行为。
- 正安全整数、alias 长度、轮询周期仍是协议技术边界，没有被写成面向用户的产品配额。
- 月度、节假日、结束次数、项目、强度、归档被明确列为非目标，没有为未来假设增加抽象。
- v3 operation 是保持 v1/v2 contract hash 的兼容扩展；实现必须共用既有 service/state machine，不能复制一套处理器。
- source 删除和 legacy 模型规则现已有现行 schema/既有行为依据，不再是无法验证假设。

## 5. 需求—设计—实现—测试追踪矩阵

> 本文是实施前复评。`设计状态` 只表示文档规则是否闭合；全部 `实现状态` 均为“待实施”，测试栏是验收要求，不代表已经运行或通过。

| ID | 需求 | 设计落点 | 设计状态 | 实现状态 | 必须验证 |
|---|---|---|---|---|---|
| T1 | 重复菜单含每小时、每天、工作日、每周、自定义 | PRD 3.2、4、5；设计 3.3、4 | 已闭合 | 待实施 | 前端组件/E2E 检查顺序、选择、摘要、编辑回显。 |
| T2 | 每 10 分钟持续执行 | PRD 3.2；设计受限 `MINUTELY` | 已闭合 | 待实施 | Admin next-run 覆盖连续多次、漏跑合并、重启恢复。 |
| T3 | 每小时自然整点 | PRD 3.2；Codex `automationScheduleToRrule` | 已闭合 | 待实施 | `BYMINUTE=0` 边界、整点前后与时区。 |
| T4 | 每天/工作日/每周按 IANA 当地日历运行 | PRD 3.2；设计 3.3 | 已闭合 | 待实施 | DST 缺失/重复、跨日、周序、服务器时区无关。 |
| T5 | 自定义支持一次、分钟/小时、多个星期 | PRD 3.2、5；workflow Stage 4 | 已闭合 | 待实施 | 结构化 DTO、非法组合、保存/回显、窄屏 sheet。 |
| T6 | 关闭开关后在源聊天继续 | PRD 3.3；设计 5.1 source 分支 | 已闭合 | 待实施 | 同一 source Thread 连续两次成功、消息/Turn/trigger 关联、结果定位。 |
| T7 | 开启开关后每次新建聊天 | PRD 3.3；设计 5.1 new 分支 | 已闭合 | 待实施 | 每个 trigger 唯一 TaskSession/Thread，历史和详情跳转。 |
| T8 | 多任务不得并发写同一 source Thread | PRD 3.3；设计 3.4、5.2、8 | 已闭合 | 待实施 | 两 task 同时到期、manual run、普通 turn 竞争、多实例 claim；失败历史且无热循环。 |
| T9 | 模型从可调用目录选择 | PRD 3.4；设计 4、7.4 | 已闭合 | 待实施 | loading/empty/error/unavailable、exact alias、权限过滤。 |
| T10 | 模型随 revision/trigger 快照 | PRD 3.1、3.4；设计 3.2 | 已闭合 | 待实施 | 编辑前后 trigger 使用各自 alias；失效失败且无 fallback。 |
| T11 | 存量 v1/v2 不改变原行为 | PRD 3.3、3.4；设计 3.2、9 | 已闭合 | 待实施 | v2→v3 migration、legacy null model、new-thread 与历史完整性。 |
| T12 | 保存使用 desired/effective/revision | PRD 3.1、4；设计 4、5.3、6 | 已闭合 | 待实施 | 冲突保留 desired；成功以完整回执替换 effective。 |
| T13 | 暂停、恢复、删除、立即运行、历史继续工作 | PRD 1、6、7；设计 6、10 | 已闭合 | 待实施 | 全生命周期；进行中 trigger 使用旧快照完成。 |
| T14 | source Thread 删除语义 | PRD 3.3；设计 7.1、9 | 已闭合 | 待实施 | FK cascade、列表/详情刷新、无失主 definition。 |
| T15 | 进程重启后恢复且不重复 | PRD 3.2；设计 5.2、6 | 已闭合 | 待实施 | lease、`state_unknown`、reconcile、相同 input/turn 与不重放。 |
| T16 | 普通 Chat、resume、cancel、SSE 不回归 | 设计 2.2、9、10 | 已闭合 | 待实施 | 普通 turn、Tool 会话、resume、cancel、SSE 回归。 |
| T17 | 自动笔记工具策略保持原规则 | PRD 2.2；设计 9 | 已闭合 | 待实施 | scheduled auto write 与普通 manual/auto/none 回归。 |
| T18 | capability 缺失 fail closed | PRD 2.2、6；设计 7、8 | 已闭合 | 待实施 | v3 缺失时显示不可用，不建表、不降级 timer。 |
| T19 | 桌面/窄屏滚动和焦点符合骨架 | PRD 5；workflow Stage 2/4 | 已闭合 | 待实施 | 桌面正文滚动、固定 header/footer；390×844、安全区、焦点返回。 |
| T20 | 文档、Mermaid 与矩阵一致 | PRD 7；设计 10；本评审 | 已闭合 | 待实施 | Markdown 清单、引用、Mermaid render、`git diff --check`。 |

## 6. 实施准入

R1—R6、PRD 骨架、正式交互图、状态语义和测试矩阵已经闭合，可以进入实现。若实现发现 `ClaudeAgentThreadFactory.run_streaming()` 无法在同一生产入口原子接纳 source scheduled turn，则将 source 模式标记为核心 admission 能力阻塞，不能用非原子查询或绕过锁完成。
