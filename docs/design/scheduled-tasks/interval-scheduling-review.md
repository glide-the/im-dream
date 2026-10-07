<!-- [Input] Updated scheduled-task PRD/formal design, workflow evidence, Dream scheduled dispatch/tool-permission code, Admin v1 contracts/schema/migration, and restored Codex/Claude source evidence. -->
<!-- [Output] Final independent goal-fit, overdesign, capability, state, permission, UI, and traceability review with an implementation-ready gate. -->
<!-- [Pos] Mandatory independent review for interval scheduling and scheduled note-tool execution; this file does not change product or implementation contracts. -->
<!-- [Sync] 2026-10-07: record the completed Admin, Dream, UI, deterministic browser and real-business validation evidence. -->
<!-- [Sync] 2026-10-07: review the scheduled tool-only completion receipt against the existing final projection contract. -->
<!-- [Sync] 2026-10-07: confirm snapshot, scheduled-deny, and persistent unknown-reconcile contracts and open implementation. -->

# 分钟间隔调度与定时会话工具审批独立评审

## 1. 评审范围与基线

本轮复核更新后的 [PRD](../../prd/scheduled-tasks/interval-scheduling-and-note-tools.md) 与[正式设计](./interval-scheduling-and-tool-approval.md)，并对照 `workflow-20261007/` 四份过程稿、Dream 当前 scheduled dispatch/Runner、Admin v1 DTO/service/schema/migration，以及正式设计记录的 Codex/Claude 恢复源码。过程稿继续作为设计过程证据，现行产品规则以 PRD 和正式设计为准。

实施后的系统保留 once/daily、Admin PostgreSQL 持久化、revision CAS、open trigger 唯一约束、claim lease/reconcile、独立 TaskSession/Thread/Turn 和真实 Chat Factory 入口，并已经增加 interval、scheduled Editor target、v2 capability、持久 unknown 重查游标及 server-owned scheduled approval policy。Admin 先发布 0075/0076 migration 和完整 v2 capability，Dream 再双版本消费；真实业务 E2E 已证明新能力没有退回浏览器 timer 或第二套会话入口。

Codex 恢复源码只用于证明产品表达有 `MINUTELY`/`intervalMinutes` 先例。正式设计已记录源码根、commit `e3fe334` 和既有来源评估文档，没有把其本机 `Date`、本地存储或单进程行为当成 PostgreSQL 多实例领取、IANA 时区和持久结果的实现保证。

## 2. 七项重点复核

| 复核项 | 结论 | 已解决内容 | 剩余收敛点 |
|---|---|---|---|
| Editor target 捕获、快照、授权链 | 已闭合 | 目标只从公开 Chat 入口已校验的 `editor_state.id` 捕获；纯 Chat 为 `null`；prompt、浏览器后续状态和最近打开记录不能改写。scheduled claim/manual run 在 trigger 插入事务中冻结 snapshot；prepare 只按 snapshot 复查 owner/存在性，authority 返回 snapshot，coordinator 据此创建 `editor-stdio` delegation、加载 Editor state 并注册 Editor MCP。删除、越权或加载失败均 fail closed。 | 按 owner、删除、授权失效、snapshot 不漂移和纯 Chat 无 Editor MCP 的测试实施。 |
| v1 hash 保留与 `.v2` operations | 已闭合 | 0069 的 `dream.chat-scheduled-task.v1`、17 个 operation 名称、输入输出 hash 和 once/daily 行为保持不变；Admin additive migration 发布 v2 capability 和独立 `.v2` operation 集，Dream 在兼容窗口双版本消费，旧合同只在后续 contract 阶段另行评审。 | 实现时 v1 serializer/claim 必须继续过滤新字段与 v2-only definition，测试固定原 descriptor/hash；不能因为共用 service 而改变 v1 输出 shape。 |
| scheduled exact override 顺序与 immediate deny | 已闭合 | 正式设计已把实际工具集合、`tool_choice=none`、Editor/Dream/workspace/network/actor/schema/call-ID guard、exact override、既有低敏感分类、scheduled unresolved deny 按顺序写清；scheduled 忽略 full access 扩权，`can_use_tool` 网络请求 fail closed，public body 不能注入 policy。server-owned、线程安全 violation marker 记录 `SCHEDULE_TOOL_APPROVAL_REQUIRED` 或 `SCHEDULE_NETWORK_APPROVAL_REQUIRED`；coordinator 在 assistant final 前读取 marker，并以 `failed` 为优先终态。 | 测试必须证明 SDK deny 后模型继续输出 final 也不能把 trigger 改成 `succeeded`。 |
| `state_unknown` 节流重查 | 已闭合 | trigger 持久化 `unknown_recheck_at`，partial index 只覆盖到期 unknown；v2 claim 在普通 dispatch 前用 `FOR UPDATE SKIP LOCKED` 原子领取、先推进游标并返回 `action='reconcile'`。worker 只调用持久结果 reconcile，不重放模型；final/明确失败收敛到终态并清空游标，无证据则保留已推进游标。长期 unknown 继续占用 open trigger，后续到期点累计 skipped。 | 用双 worker、worker 重启、重复 poll 和三种 reconcile 结果验证一个节流窗口只重查一次。 |
| skipped `min/max` | 已闭合 | 无 open trigger 时只执行最近到期点，更早范围记为 `old next_run_at .. scheduled_at - interval`；已有 open trigger 时用最早 `skipped_from_at` 与最晚 `skipped_through_at` 累积，并把当前最新 due 点计入跳过范围；`next_run_at` 严格推进到数据库 `now` 之后。 | 实现 SQL 要对 nullable 旧值使用 `COALESCE`，唯一索引冲突转换为幂等 open-trigger 分支；用双 worker 和跨多个间隔测试锁定。 |
| Calendar 骨架、单一滚动与编辑弹窗 | 已闭合 | PRD 正文已有桌面 Calendar 左月历/右当日内容骨架和窄屏顺序；右侧任务、错误、日记共用一个滚动容器，月历卡不随内容增长。Chat 详情只有一个正文滚动区，历史分页追加到该区；Chat 与 Calendar 共用一个编辑弹窗语义，不再出现第二套内联编辑表面。 | 浏览器验收需覆盖长历史分页、窄屏 sheet、无横向滚动、焦点返回和 Calendar 固定月历高度。 |
| once/daily/interval 与配置状态 | 已闭合 | default 是未创建，desired 是未保存草稿，事务提交后立即成为 effective 并增加 revision；没有异步 apply/LKG。interval 创建、active 编辑、恢复用数据库时钟，后续沿旧 `next_run_at` 格点推进；pause/edit/delete 不取消已绑定 turn。 | v2 回归必须证明 once/daily 的 DST、once exhausted、manual run 和 revision 行为未改变。 |

## 3. 目标适配、普通 Chat 与 capability 判断

### 3.1 目标适配

设计保持一个 scheduler、一套 trigger 状态机、一个 Chat/Claude Agent Factory 和现有 EventBus/SSE/持久化入口。interval 只是 rule/time/claim 的新分支；自动笔记写入只增加 Editor target snapshot、目标绑定 runtime 和内部精确审批覆盖。该拆分直接服务“每隔 N 分钟运行并写入创建时当前笔记”，没有把通用 cron、工作流或审批平台塞入本期。

### 3.2 普通 Chat 回归边界

`ToolApprovalPolicy` 只由 scheduled composition root 注入，默认不存在；普通 public request DTO 不接受该字段。普通 Chat 继续使用现有 `auto/manual/none`、full access、确认 Future 和 `can_use_tool` 规则。实现时应把 scheduled 分支放在不可绕过 guard 之后、普通低敏感分类之前，并用默认 `None` 保证现有调用方与 RunOptions 序列化不变。

scheduled Editor target 为 `null` 时，不创建 `editor-stdio` delegation、不加载 Editor state、不注册 Editor MCP；这使纯 Chat 定时任务仍能产出普通会话结果，同时不会把 exact auto 变成无目标写入能力。

### 3.3 Schema 所有权与 fail closed

正式设计已符合共享 schema 合同：Admin Drizzle 先做 additive migration、CHECK/index/capability/operation contract；Dream 不建表、不使用 Alembic/SQLite/runtime DDL，不依赖 Drizzle head。缺少完整 v2 capability 或任一 v2 operation 时，interval 与 scheduled Editor target fail closed，前端不退回浏览器 timer；v1 once/daily 兼容路径仍可用。

Admin 已发布 v2 capability，Dream 只在 capability 与完整 operation 集匹配时启用 interval/Editor target；缺失时仍 fail closed。Dream 没有新增 migration、runtime DDL、自动建表或 SQLite fallback。

## 4. 最终实施合同复核

1. **快照边界明确。** scheduled claim 与 manual run 在 trigger 插入事务中复制 `target_editor_session_id_snapshot`；prepare 只读取、重新校验并返回 snapshot，不从 definition 或环境回填。
2. **拒绝终态明确。** scheduled policy context 的 violation marker 是 server-owned 且线程安全；PreToolUse manual/unresolved deny 与 `can_use_tool` deny 写稳定 safe error code。coordinator 先读 marker，再判断 final；marker 存在时调用 `finish(failed, code)`。
3. **unknown 恢复明确。** `unknown_recheck_at`、partial index、数据库时钟、`FOR UPDATE SKIP LOCKED`、claim `dispatch/reconcile/idle` action 和终态清空游标形成持久、多实例安全的重查入口；reconcile 不启动模型。

三项与第 8 节代码影响、正常/异常时序和发布顺序一致，并已按 Admin migration/capability → Dream 双版本 consumer → Frontend/UI → 回归与真实链路验收的顺序落地。

## 5. 反过度设计评审

应保留的最小增量是：Admin v2 interval rule、definition/trigger Editor target、unknown 重查游标、现有 trigger 的 skipped 范围、内部 scheduled approval context，以及既有 UI/API union 的 interval 分支。

本期不应增加 RRULE 存储、cron 编辑器、第二套 scheduler/Run/SSE/reducer、Dream runtime DDL、SQLite fallback、消息队列、restart/kill/shell 控制通道、浏览器倒计时、用户可编辑的通用审批矩阵、跨重启人工审批对象、异步 desired/effective/LKG 或按部署环境名称分叉的行为。workflow 中相关探索继续保留为过程证据，不进入现行产品合同。

## 6. 需求—设计—实现—测试追踪矩阵

| 需求 | PRD/设计落点 | 实现证据 | 测试证据 | 状态 |
|---|---|---|---|---|
| once/daily 不回归 | PRD 3.1–3.2、7；设计 3.1、7、10 | Admin v1 operations/hash 原样保留，v2 serializer 与 claim 复用既有时间算法 | Admin 5 项 PostgreSQL 合同测试；Dream 335 项受影响测试 | 已完成 |
| interval 创建、编辑、恢复 | PRD 2、3.2、4、7；设计 3.1–3.2、5 | Admin 0075 schema、v2 DTO/service；Dream Tool/route；Frontend union/editor | 合同测试覆盖边界；Calendar 12 项；真实 E2E 从 1 分钟编辑为 10 分钟并暂停 | 已完成 |
| 持久化重启与 unknown 恢复 | PRD 2.1、3.2–3.3、6；设计 3.2、3.5、6 | `next_run_at`、lease、`unknown_recheck_at`、`dispatch/reconcile/idle` 均在 PostgreSQL | PostgreSQL 集成测试覆盖迁移、claim、reconcile；Dream coordinator 回归通过 | 已完成 |
| 一个 open trigger、重复领取与 skipped 累积 | PRD 3.3；设计 3.2、6 | 原有 partial unique index 保留；v2 原子推进 interval 并累积 skipped 范围 | PostgreSQL 集成测试覆盖 open trigger、skip 与重新领取 | 已完成 |
| 绑定创建时目标笔记 | PRD 2.2、3.4、4、6；设计 3.1、4、8–9 | definition 保存 target，trigger 同事务保存 snapshot；authority 与 `editor-stdio` 只使用 snapshot | Admin authority/delegation 集成测试；真实 E2E 自动写入 session `ff20bf30-0d65-4afa-98cb-91d5ad55af4a` | 已完成 |
| 两项 Editor 写工具自动执行 | PRD 3.4、7；设计 3.3–4、8 | `ToolApprovalMode = Literal["auto", "manual"]`；scheduled policy 对 `write_segment`、`insert_widget` 配置 `auto` | Runner 定向测试；真实 E2E 无确认框且出现成功 `write_segment` Tool 结果 | 已完成 |
| manual/未知/network 拒绝并使运行失败 | PRD 3.4、6；设计 3.3、6、8–9 | PreToolUse/can-use guard 写线程安全 violation；coordinator 以稳定错误码结束 trigger | Runner/coordinator 测试覆盖 manual、unresolved、network 和模型继续输出情形 | 已完成 |
| 普通 Chat、resume、cancel、SSE 无回归 | PRD 1–2、3.4、7；设计 2、3.3、11 | scheduled policy 仅由 coordinator 注入，public DTO 不接受；默认 `None` | Dream 335 项受影响测试含普通 Agent/route/session 回归；Chat 浏览器回归 6 项 | 已完成 |
| v1/v2 schema ownership 与 fail closed | 设计 2、3.4、8、10 | 0075/0076 与 capability/17 个 `.v2` operations 全部由 Admin Drizzle 管理；Dream 无 DDL | 隔离 PostgreSQL 77/77 migration、5/5 合同测试；缺 capability 定向测试 | 已完成 |
| Chat/Calendar 响应式 UI | PRD 4–6；设计 8–9；workflow 四阶段稿 | Chat marker/右侧详情、Calendar 浮层双卡、独立滚动、编辑弹窗、结果/打开聊天均复用现有组件 | Chat 浏览器回归 6 项；Calendar Chrome 12 项；真实 E2E 两张截图 | 已完成 |
| 真实 TaskSession/Thread/Turn 与结果入口 | PRD 2.1、4、7；设计 4、6 | coordinator 继续走 `_claude_agent_stream_impl`、Admin start/finish 与现有 history route | 真实 task `cddd3087-3307-42d3-b9c5-7ad942c76d9d`、trigger `99cd7b30-63bc-435b-bf0b-7139b27a1923`、Thread `4e38964a-8edb-41d2-8f4e-f7d0b3b587cf` 均可查 | 已完成 |
| 成功工具调用后无模型 final text | PRD 3.3、6–7；设计 3.6、4、9、11 | 仅 scheduled 成功工具结尾追加固定完成回执；Admin final/turn 校验没有放宽 | service 定向测试与真实 final message `ebc9dd51-c119-5c02-a690-7fe3b84e2657` 通过 | 已完成 |

## 7. 实施与验证回执

### 7.1 Admin schema、协议和构建

- `node scripts/run-chat-scheduled-task-contract.mjs`：退出码 0；隔离 PostgreSQL migration `77/77`；`5 passed`；`scheduled_chat_contract=passed`。
- `corepack pnpm build`：在排除主工作区历史 `output/` 产物的临时同源副本中退出码 0；DB package、Next 编译、TypeScript、20 个静态页面和 route trace 全部完成。主工作区直接运行时，产品源码已完成 webpack 编译，但 TypeScript 通配符读入旧 `output/admin-pr-20261007/.../provider-routing.config.ts` 后失败；该文件不是本轮改动，未删除或改写。

### 7.2 Dream/backend 与 Frontend 静态回归

- `../.venv/bin/python -m pytest tests/test_admin_request_auth.py tests/test_claude_agent_runner.py tests/test_claude_agent_service.py tests/test_scheduled_task_consumer.py tests/test_server_claude_agent.py -q`：退出码 0；`335 passed, 1 skipped, 183 subtests passed`。
- `corepack pnpm exec tsc --noEmit`：退出码 0。
- `corepack pnpm build`：在不影响正在运行开发服务的临时同源副本中退出码 0；Next webpack、TypeScript、静态页面和 route trace 全部完成。
- `corepack pnpm exec eslint e2e/scheduled-task-real.spec.ts`：退出码 0。
- Chat marker 与 lazy process 两个 Playwright 文件：退出码 0；`6 passed`。
- `E2E_WEB_BASE=http://127.0.0.1:5173 pnpm exec playwright test e2e/scheduled-task-calendar.spec.ts --reporter=line --workers=1`：退出码 0；`12 passed`。

### 7.3 真实业务 E2E

命令：

```bash
INK_REAL_SCHEDULED_TASK_QA=1 \
INK_REAL_SCHEDULED_TASK_WEB_BASE=http://localhost:5173 \
INK_REAL_SCHEDULED_TASK_ACTOR_EMAIL=dmeck@suoxya.com \
corepack pnpm exec playwright test e2e/scheduled-task-real.spec.ts --reporter=line --workers=1
```

退出码 0，`1 passed (1.9m)`。使用现有账户 `dmeck@suoxya.com` 和正常 Dream/Admin/Gateway/PostgreSQL，完整覆盖：新建笔记、Chat Tool 创建 interval、消息内任务标记、右侧详情、到点 trigger、自动 Editor 写入、无确认框、运行结果与 Thread 导航、Calendar 编辑为 10 分钟、暂停及 revision 3。测试保留正常业务记录与截图供复核。

文档验证同时检查 8 份现行/过程 Markdown 的相对链接和代码围栏，并用本机 Chrome 实际渲染正式设计的 3 个时序图和 1 个状态图；结果为 `mermaid_render=ok:4`。

## 8. 已纠正的旧判断与测试问题

1. 旧稿把关键词或单进程 timer 当成持久调度依据；现行设计明确结论为“可复用会话能力，但需要 Admin 持久调度层”。
2. 初版 Calendar 把内容撑开并采用线框式单容器；现行 UI 使用悬浮分卡和右侧单独滚动区。
3. 初版 Chat 展示 conversation 列表；现行 UI 在原回复后显示任务标记，点击打开包含任务信息、会话和任务周期的右侧栏。
4. 首轮真实 E2E 的保存监听把请求体标题塞进 response predicate，并与异步 New Session reset 竞争；已改为等待空白状态、保存后独立校验 payload，避免 8 分钟假超时。
5. scheduled 工具成功但模型没有 final text 时曾留下 `state_unknown`；现在仅为成功 scheduled tool-only turn 持久化最小完成回执，错误、拒绝和取消不会被升级为成功。

## 结论

可直接实施；本轮已经按评审后的最小纵向切片实施，并通过确定性测试、生产构建和真实业务 E2E。
