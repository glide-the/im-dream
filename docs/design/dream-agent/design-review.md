# Dream Agent 正式设计与实施证据审查

> 当前审查结论：**R39 修改后接受（设计 ACCEPT，修正实现待完成）**。R5 的
> 设计接受和 R8/R10 的实施复审作为历史记录保留；R17–R26 已完成
> 其已记录范围的本地门禁，R32 补齐了可见 Chromium。R26 后独立复审发现两个“未来
> 验证可假阳性”缺口；R28 已用 128 个测试 + 37 个 subtest 关闭，且未
> 调用 provider、未改 runtime/runner。独立复审随后以 19 个定向测试返回
> ACCEPT，无新假阳性、泄漏或 blocker，也未调用 provider。R35 又对
> B01–B21 全业务交互设计完成正式审查并接受。R39 根据业务方代码审查重新打开
> context assembly、Observer 所有权、DTO、Artifact 合同和 Workflow 状态设计，
> 阻断性设计问题已修正；旧实现证据不能替代本轮代码落地与复验。

## 审查元数据

| 项目 | 结果 |
|---|---|
| Review ID | `DREAM-CONVERGENCE-2026-01` |
| 当前复审轮次 | `R35`，包含 R32 可见浏览器与 B01–B21 业务理解审查 |
| 代码基线 | `platform@a506c83d5fa9a07d37afa10b2fb947c05c9c7408` |
| 参考分支 | `story-workspace@eedde940a3af1695aee7cf6ca5a63efab7c15a11` |
| 设计快照 | 2026-08-12 未提交工作区中的 `docs/design/dream-agent/**` |
| 历史结论 | `R5`：设计 ACCEPT；`R8`：实施复审 ACCEPT；`R10`：Observer 补充修改后接受 |
| 本次方式 | 当前源码反证 + B01–B21 覆盖审查 + 22 张 Mermaid 真解析 + 链接/格式门禁 |
| R35 最终结论 | **修改后接受 → ACCEPT** |
| 生产实现状态 | **已完成并通过当前授权的本地门禁（含 R32 headed）** |
| 发布许可 | **未授予；无 staging/canary/不可变回滚/load 证据** |

本审查严格区分当前源码事实、已执行的本地/克隆证据和未执行的部署
证据。历史章节中的“尚未实现/未验证”只描述 R5/R8/R10 当时状态，
不得用它否定后文 R27/R28 的当前结论，也不得把本地 PASS 升格为生产发布。

## R5 Prompt Architect 记录（历史）

| 项目 | 记录 |
|---|---|
| 当前轮次目标 | 独立复审原 `DR-001`～`DR-009`，只更新本审查文件；确认所有 P0/P1 是否已成为可直接实现、可测试、无第二套 runtime 的契约。 |
| 优化后的执行提示词 | 完整重读 `docs/design/dream-agent/**`，将每个原 Required change 映射到精确规范位置和当前代码证据；逐项给出 `CLOSED/OPEN` 与未验证内容。重点对抗检查现有 Dream-files `threadId`、ChatPanel 唯一 live owner、服务端确认 policy、三个 adapter caller、Coordinator 全出口清理、protected runner、共享可见性、Stop 真实性及完整验证 gate。仅当全部 P0/P1 无设计歧义时接受并授权生产实现。 |
| 检查/修改范围 | 检查全部 Dream Agent 新设计文档及相关当前源码；只修改 `docs/design/dream-agent/design-review.md`，不修改生产代码或其他文档。 |
| 完成标准 | 9 项原阻断逐项有规范位置、当前证据、关闭判断和未验证事实；正式结论明确区分实现授权与发布许可。 |
| 实际结果 | `DR-001`～`DR-009` 全部 `CLOSED`；没有新增 P0/P1 设计阻断。生产实现、迁移删除、测试和真实浏览器验证均尚未执行。 |

## 一、R5 复审核验的当时代码事实（历史）

以下事实用于证明设计修订针对真实 seam，而不是把 Proposed 行为误记为现状：

- 现有 actor-scoped Dream-files 前端解析已经要求非空 `threadId`：
  `frontend/src/hooks/story-workspace/useStoryWorkspaceDreamFiles.ts:178-193`。
- `ChatPanel` 已是 live Chat owner：
  `frontend/src/components/chat/ChatPanel.tsx:285-315` 创建 transport 并调用
  `useChat`，`:484-568` 处理 reconnect，`:588-612` 是当前 Stop 不确定性缺口。
  `frontend/src/components/chat/ChatView.tsx:711-796` 负责 history/status/recovery
  装配。
- 当前确认链路仍只有 Future，没有 server-owned policy：
  `backend/claude_agent/tool_confirmation_store.py:44-141`；
  `backend/claude_agent/service.py:2238-2308` 已做到 Future register-before-publish，
  但重复判断仍只按 tool ID；`backend/routers/claude_agent.py:965-997` 在 ownership
  后直接转发浏览器 decision。`backend/claude_agent/thread_factory.py:150-187,
  397-430` 已持有 server-side active turn 和可信 Dream provenance，可作为精确
  identity 的权威来源。
- 审查基线中的旧 adapter 有三个生产调用方，且职责不同：
  `backend/services/story_workspace/dream_launch_infrastructure.py:813`、
  `backend/services/story_workspace/dream_confirmation_service.py:889`、
  `backend/services/story_workspace/dream_agent_message_service.py:1891`；最后一项
  已迁移为 `backend/services/story_workspace/dream_internal_command_service.py`。
- 当前 factory 已是 EventBus、turn task、lock 和退出清理 owner：
  `backend/claude_agent/thread_factory.py:150-230,473-520,559-612`。Coordinator
  必须附着在该生命周期，而不能另建 runtime owner。
- 当前共享私有行过滤位于
  `frontend/src/lib/story-workspace-guidance.ts:47-66`；
  `frontend/src/components/chat/ChatView.tsx:401-404` 仍可能给空 parts 合成空 text，
  所以零可见 parts 规则确实需要实现。
- `backend/libs/claude_agent_kit/server/agent_runner.py` 存在且本设计快照没有该文件
  的 diff；这只是设计期核对，最终实现仍必须重复执行 protected-file gate。

## 二、阻断项闭环总表

| ID | 级别 | 原问题 | R5 状态 | 关闭依据 |
|---|---|---|---|---|
| DR-001 | P1 | 错误假定 re-entry 缺少 `threadId` | **CLOSED** | 明确复用现有 Dream-files 响应；禁止新端点/权限性 binding 字段 |
| DR-002 | P1 | 新 shared controller 可能成为第三套 runtime | **CLOSED** | ChatPanel-first；唯一 `useChat`/live reducer；仅抽取 hydration |
| DR-003 | P0 | canonical confirmation 无可执行的服务端 policy/原子 identity | **CLOSED** | policy+Future publish 前原子注册；精确三元 identity、CAS、全出口清理 |
| DR-004 | P1 | adapter 内部调用方遗漏 | **CLOSED** | 三个 caller 逐一列出并保留各自 owner 语义 |
| DR-005 | P1 | Observer/coordinator 资源所有权和退出路径不闭环 | **CLOSED** | factory-owned handle、bounded queue、lease、统一 awaited teardown |
| DR-006 | P1 | runner 禁改及 service/factory ownership 未成为硬约束 | **CLOSED** | non-goal、ownership、migration 和 test gate 四处一致 |
| DR-007 | P1 | 私有控制行、字段级可见性和空白气泡未定义 | **CLOSED** | 共享 row filter、字段快照、zero-visible-parts、filtered export |
| DR-008 | P1 | Stop 真实性、失败恢复和历史 subagent 规则未定义 | **CLOSED** | current-main-only、uncertainty locked、authoritative recovery、unmount≠Stop |
| DR-009 | P1 | 强制验证、headed E2E、隔离和清理不完整 | **CLOSED** | 精确命令、fake provider、semantic waits、headless→headed、zero residue |

## 三、逐项关闭记录

### DR-001 — existing Dream-files `threadId` / no new API — CLOSED

规范位置：

- `architecture.md:193-207` 把 existing actor-scoped Dream-files 定为唯一 re-entry
  seam，并明确“不新增 endpoint 或 binding identifier”。既有业务响应可选的
  `agentActivity` 是无权限含义的展示提示，不参与 re-entry。
- `interaction-design.md:123-151,348-374,493-503` 的 Chat→Dream、刷新和权限时序均是
  Dream-files → existing `threadId` → hydration/ChatPanel；run ID 不进入 Chat plane。
- `lifecycle.md:321-335`、`migration-plan.md:194-205,277-287` 和
  `testing-and-acceptance.md:137-145` 同步了相同契约和负向 API inventory gate。

当前证据：`useStoryWorkspaceDreamFiles.ts:178-193` 已解析现有 `threadId`，所以修订
与实际代码一致。

未验证内容：尚未实施 Dream wrapper，也未运行跨 actor Dream-files contract test；
最终 diff/API inventory 仍需证明未新增 re-entry transport 或权限性 binding 字段。

### DR-002 — ChatPanel-first / 唯一 `useChat` — CLOSED

规范位置：

- `architecture.md:36-48,131-164,376-390,478-484` 明确禁止 app-wide Provider、
  second `useChat` 和大型 controller；ChatPanel 是唯一 transport/live reducer/
  confirm/stop owner。
- 可共享 primitive 被限制为
  `initialMessages/authoritativeRunning/reconnectNonce/pendingToolCallIds/
  settledToolCallIds/recoverAfterEof`，不得 parse/send/confirm/stop 或持有 live
  `UIMessage`。
- `interaction-design.md:28-59`、`lifecycle.md:24-28`、
  `migration-plan.md:51-70`、`testing-and-acceptance.md:30-46,224-247` 一致要求
  Dream 直接组合 ChatPanel，并以 source/bundle test 禁止第二套 runtime。

当前证据：`ChatPanel.tsx:285-315,484-612` 和 `ChatView.tsx:711-796` 提供了设计所列
的最小抽取 seam。

未验证内容：hydration primitive 和 Dream wrapper 尚未实现；TypeScript、Chat
regression、production bundle 以及“只有一个 `useChat`”的 source gate 尚未运行。

### DR-003 — server policy / exact identity / atomic resolution — CLOSED

规范位置：

- `architecture.md:240-283` 定义 `ClaudeAgentService._make_tool_confirm_cb` 与 per-turn
  `ToolConfirmationStore` 在发布 approval frame **之前**原子注册 policy+Future，key
  为 `(threadId, turnId, toolCallId)`；相同 fingerprint 才可 join，冲突 fail closed。
- 同一节给出 AskUser、network、`reject_only`、payload size、capacity、TTL/tombstone
  的 server-owned bounds；browser 不得创建或修改 policy。
- route 先做 actor/thread ownership，再 snapshot server active turn，以 exact identity
  validate+compare-and-set；并发只有一个 winner，settled reply 稳定。timeout、reject、
  Stop/cancel、terminal、context/session teardown 和 factory close 同时清理 policy 与
  Future。
- `interaction-design.md:154-196`、`lifecycle.md:243-274`、
  `migration-plan.md:73-104` 及 `testing-and-acceptance.md:48-62,146-171` 将注册顺序、
  exact identity、typed policy、atomic one-winner、cross-loop completion 和全出口清理
  固化为时序、状态机和测试矩阵。

当前证据：当前 callback 已在 `service.py:2248-2291` 做 Future-before-event；当前
store/route 缺 policy 和 exact turn CAS，且 factory 已提供 active `turn_id` 与可信
Dream state。设计因此明确了增量改动的 owner 和数据来源，不依赖将被删除的 Dream
public registry，也不要求修改 runner。

未验证内容：policy record、三元 key、route snapshot/CAS、cross-loop awaited resolve、
settled tombstone 和 cleanup 尚未实现；所有 negative/concurrent/capacity tests 仍待运行。

### DR-004 — 三个 `iter_dream_run_events` caller — CLOSED

规范位置：

- `architecture.md:313-328` 按路径列出 launch、business confirmation 和
  message/episode dispatch 三个 caller，并分别保留 failure/task、claim/heartbeat/ack
  和 claim/mark/release/awaited shutdown 语义。
- `migration-plan.md:132-151,207-240` 给出逐文件替换/删除顺序、每个 owner 的退出要求
  和最终零匹配 scan。
- `testing-and-acceptance.md:307-326` 把三个 caller 的聚焦回归、normalized drain、
  protected runner 和最终 source scan 设为 release gate。

实施结果：三个 durable caller 均通过唯一公开入口
`ClaudeAgentThreadFactory.run_streaming()` 启动 turn；普通 claim settlement 等待该
流的 same-turn completion handle，只有 launch safe-error 提取按需使用共享
`ChatStreamAdapter.decode()`。`run_events` 不再存在，`_run_streaming_frames`、
`_run_turn_task` 和 `_subscribe_events` 均为私有实现。原 claim/heartbeat/ack/release
测试与 ThreadFactory completion 契约测试通过。

### DR-005 — Coordinator 全出口资源清理 — CLOSED

规范位置：

- `architecture.md:285-311` 将 Coordinator 限定为 factory 上层的最小 turn resource
  owner：producer 前 subscribe、subscriber 非阻塞写 bounded queue、sink worker 脱离
  Chat path。
- `observer-design.md:101-145,204-244,297-340,397-444` 定义 turn handle、revocable
  generation lease、queue/dedup bounds、late-result recheck 和统一 `close_turn`。
- `lifecycle.md:294-319` 要求 context/setup failure、terminal/sentinel、Stop、task
  exception、session eviction、factory `aclose` 全部进入相同 `finally`：先 revoke，
  再 unsubscribe/cancel/await，最后清 cache；sentinel 无 finish 只 reconcile，不造终态。
- `migration-plan.md:106-129` 和 `testing-and-acceptance.md:188-222` 将所有退出路径、
  slow/raising/overflow sink、frame equivalence、late write 和 zero-resource teardown 设为
  可执行 gate。

当前证据：`thread_factory.py:150-230,473-520` 已是 EventBus/task/lock owner，规范把
attach/close 放在其现有边界内，没有创建另一个 Agent runtime。

未验证内容：Coordinator/Observer/lease 尚未实现；subscriber/task/Future 泄漏、
slow sink、overflow、factory close 和 byte-equivalence tests 均未执行。

### DR-006 — protected `agent_runner.py` 和 runtime ownership — CLOSED

规范位置：

- `architecture.md:36-48,393-405` 明确 runner 零修改，并保留 SDK classification、
  can-use-tool policy 和 cancellation；Service 继续拥有 context/callback/policy
  registration/normalized events/persistence/terminal，Factory 继续拥有 session/task/
  EventBus/lock。
- `migration-plan.md:244-255` 禁止 Coordinator/Observer classify SDK、resolve tools、
  cancel runner 或 publish conversation frames。
- `testing-and-acceptance.md:63-83,307-326,412-424,460-489` 要求 protected-file diff
  为空并运行 runner/service/factory focused regressions。

当前证据：`backend/agent_stream_events.py:7-10` 已说明 normalized boundary 不接管
runner 职责；本次设计工作区没有 protected runner diff。

未验证内容：生产实现尚未开始，因此“最终 diff 为空”和 runner/service/factory
regression 尚未证明；任何后续 runner 改动会立即使本项重新 OPEN。

### DR-007 — shared visibility / private rows / zero parts — CLOSED

规范位置：

- `architecture.md:343-368` 精确列出三类 server-private metadata row，要求 history、
  live、reconnect 和 export 共用 `filterStoryWorkspaceControlMessages`；零可见 parts
  整行跳过，禁止空 text/bubble。
- 同节以字段级 snapshot 限定 text、reasoning、tool identity/name/state/input/output/
  error 和 client-safe provider/turn error；export 只能消费已过滤 view model。
- `interaction-design.md:510-524`、`lifecycle.md:151-172` 和
  `testing-and-acceptance.md:224-289` 给出两页面 fixture 等价、私有行不渲染/不导出、
  zero-part 及跨 actor/Admin 日志负向测试。

当前证据：`story-workspace-guidance.ts:47-66` 已有共享 row filter；
`ChatView.tsx:401-404` 的空 text fallback 是需要按规范修复的现有缺口。

未验证内容：live/reconnect/export 是否全部走同一过滤模型尚未实现/证明；字段 snapshot、
zero-bubble、跨 actor 和导出测试尚未运行。

### DR-008 — Stop 真实性 / uncertainty / historical subagents — CLOSED

规范位置：

- `architecture.md:182-191`、`lifecycle.md:24-88,337-349` 将 Stop eligibility 限制为
  local submitted/streaming main turn 或 authoritative current-main `running`；历史
  subagent transcript/status 不得产生 busy/Stop。
- `interaction-design.md:232-268,526-543` 明确 2xx+`running=false` 后仍经 authoritative
  recovery 才 unlock；non-2xx、timeout、malformed 或 `running=true` 保持 input locked
  并 status+reconnect。unmount/navigation/network abort 只关闭 reader，不调用 Stop。
- `testing-and-acceptance.md:94-115,224-247` 要求 success/uncertain、history-only
  subagent、页面切换和 input lock 的 reducer/contract/E2E 断言。

当前证据：`ChatPanel.tsx:588-612` 当前先本地 stop，且没有完整检查 HTTP/body；
`thread_factory.py:559-612` 明确可能返回 `running=true`。修订契约直接覆盖真实 race。

未验证内容：Stop UI/recovery 尚未实现；真实 cancellation propagation、partial output、
历史 subagent、切页和网络不确定性测试尚未运行。

### DR-009 — mandatory verification / headed / isolation / cleanup — CLOSED

规范位置：

- `testing-and-acceptance.md:28-93` 给出四个 hard gate，`:94-289` 给出 14 场景、权限、
  confirmation、terminal、Observer、frontend、workflow 和 security 矩阵。
- `testing-and-acceptance.md:328-424` 给出 backend focused/regression、frontend
  contract、`npx tsc -b`、ESLint、build、Admin SSE、headless Chromium、随后
  `--headed --workers=1`、禁止 `waitForTimeout|sleep(`、`git diff --check`、protected
  file 和 legacy source scan 的精确命令。
- `testing-and-acceptance.md:426-443` 要求 deterministic fake provider、禁止真实模型/
  credential、unique temp DB/workspace、OS-assigned port、PID tracking、所有 pass/fail/
  Ctrl-C 路径的 finally cleanup，以及退出前 zero PID/listener/subscriber/task/Future/
  policy/handle。
- `testing-and-acceptance.md:445-490` 定义 evidence record 和最终 go/no-go checklist。

当前证据：设计期仅用
`git diff --no-index --check /dev/null docs/design/dream-agent/design-review.md`
核对本审查文件，未报告 whitespace error（untracked 文件存在内容差异时退出码为 1）；
它不能替代上述实现期命令。

未验证内容：本节列出的 backend/frontend/Admin/build/headless/headed 命令均尚未作为
最终 release candidate 执行；拟新增测试文件可能尚不存在，真实 artifact 和 cleanup
evidence 也尚未产生。

## 四、总体设计审查结论

| 审查问题 | R5 结论 | 依据 |
|---|---|---|
| 是否真正消除 Dream 第二套 Agent runtime？ | **是，设计通过** | 新构建只保留 Chat thread public conversation；旧 routes/adapter/hook/contracts 硬删除 |
| 是否真正复用 Chat thread SSE，而非旧 Dream SSE 改名？ | **是** | Dream 直接组合 ChatPanel 与 canonical routes/adapter；Observer 不编码浏览器 frame |
| 是否仍设计第二套 transport/parser/reducer？ | **否** | ChatPanel 是唯一 live owner；hydration primitive 被明确禁止 parse/live/send/confirm/stop |
| Observer 是否成为新状态机或事件存储？ | **否** | 仅 bounded process-local hint projection；无 table/outbox/checkpoint/public SSE，不反控 runtime |
| 是否保持 Service/runner/factory 职责？ | **是** | protected runner、Service 和 Factory ownership 均为 normative hard constraint |
| workflow 权限是否被削弱？ | **否** | actor/thread/run/Deck、retry graph、revision/idempotency 和 existing lifecycle guards 保留 |
| Dream 是否可能泄漏 richer Chat 数据？ | **已有明确 fail-closed 契约** | owner-visible 字段 snapshot、私有整行过滤、零 parts 跳过、filtered export 和跨 actor tests |
| 是否可能重复消息、终态或确认？ | **契约已覆盖** | shared reducer/replay、first terminal、三元 pending identity、CAS one-winner、settled result |
| 是否能以更小范围实现？ | **是** | ChatPanel-first + minimal hydration；拒绝 app-wide Provider、durable Observer 和双协议 flag |
| 旧代码能否立即全删？ | **不能一次盲删；阶段边界清楚** | 先 policy/Coordinator/caller 迁移与 gate，再在同一 releasable build 中硬删除 public protocol |

没有发现需要新增的 P0/P1 设计问题。R3 认为可能导致错误实现、安全退化或过度抽象
的九处歧义，均已被改写为 owner、数据来源、identity、时序、失败语义、清理路径和
验收测试。目标架构也没有要求修改 protected runner 或把 Observer 放入 SSE 主路径。

## 五、仍未验证但不阻断开始实现的事项

以下均是**实现/发布 gate**，不是仍然 OPEN 的设计问题：

1. 当前生产源码仍包含旧 Dream routes/adapter/hook/reducer 和三个 internal caller；
   这符合“尚未实施”的事实，不得在汇报中声称已删除。
2. `DreamRunBindingResolver`、pending policy/CAS、minimal hydration、Coordinator/Observer
   和新的 focused tests 均为 Proposed，尚无可执行结果。
3. 旧文档迁移、索引更新、dead-link/source/OpenAPI/bundle scan 和 Git recovery commit
   尚未执行。
4. backend reasonable-scope regression、TypeScript、ESLint、production build、Admin
   no-buffer、headless/headed Chromium、semantic wait、fake-provider isolation 和
   zero-residue cleanup 均无最终 evidence。
5. 性能阈值、capacity bounds、跨进程/跨 loop 竞态和 deployment rollback 需要在真实
   release candidate 上验证；设计值不能替代测量。

任一 gate 失败时应修复实现；若失败暴露的是 ownership、公开协议、identity 或终态
模型本身错误，则必须回到本审查重新打开对应 DR，而不是降低测试标准。

## 六、生产实现授权与失效条件

> 在代码基线 `a506c83d5fa9a07d37afa10b2fb947c05c9c7408` 和本次设计快照上，
> `DREAM-CONVERGENCE-2026-01/R5` 的正式结论为：**接受，并授权生产实现**。

授权范围仅包括已审 migration phases。下列任一变化会使授权自动失效并要求重新设计
审查：

- 增加新的 Dream conversation/re-entry endpoint、权限性 binding response field 或公开
  SSE schema；现有 actor-scoped Dream-files 上无权限含义、content-free、display-only
  的 `agentActivity` 不属于此项，但若其反控 lifecycle 则立即使授权失效；
- 新增第二个 `useChat`、Dream parser/reducer、app-wide conversation Provider 或长期
  双协议 runtime selector；
- 允许 browser 选择 run/actor/context/turn 或创建 confirmation policy；
- 弱化 `(threadId, turnId, toolCallId)` exact identity、register-before-publish、CAS
  one-winner 或全出口 cleanup；
- 让 Observer 持久化 lifecycle truth、产生浏览器 frame、阻塞 Chat path 或反向控制
  ClaudeAgentService；
- 修改 `backend/libs/claude_agent_kit/server/agent_runner.py`，或迁移其 SDK
  classification/tool policy/cancellation 职责；
- 把历史 subagent、workflow status 或页面局部状态当作 current main turn/Stop/terminal
  truth；
- 在同一个可发布构建中保留旧、新两套 conversation transport。

生产实现完成后，只有 `testing-and-acceptance.md` 的全部 P0/P1 checklist 有可复现的
commit、命令、结果和 artifact，才可另行授予发布许可。

## 七、R8 实施后独立审查记录（2026-08-11）

> 本节追加在 R5 设计审查之后；不改写当时的历史判断。实施后结论为
> **接受（ACCEPT）**，但发布许可仍取决于 R9 的真实验证结果。

前端独立复审确认 Dream wrapper 直接组合唯一的 `ChatPanel`，重连信号按 thread
分别计数，pre-mount terminal 只由精确 expected message identity 加权威 idle 结算，
confirmation replay 不再被 AskUser/manual 派生状态重新打开。聚焦 runtime 与确认契约
测试为 `27 passed`。

后端独立复审先后发现并关闭以下实施缺口：

1. canonical history 对 thread、message 和嵌套 Chat metadata 使用值校验白名单，
   剥离 run/actor/provenance/claim/lease/revision/session；损坏 JSON、JSON `null` 和其他
   非对象 metadata 与 SQL NULL 明确区分并 fail closed；
2. Redis 原子 first-terminal 脚本同时兼容旧 spaced finish；无论 terminal contender
   还是 late nonterminal event 先发现旧 finish，都补且只补一个 sentinel；nested
   `data.type=finish` 不误判；
3. Factory 在首次 await 前关闭 admission，普通请求和 reconnect 均在关键 await/lock
   两侧复查；Observer close 异常不阻止 thread idle 与锁释放；
4. Service/Factory 取消终态携带 `cancelled:true`，Classifier 和 Observer 即使已见
   `message-final` 仍优先归类 cancelled；InMemory EventBus 重新抛出取消；Redis client
   在 factory 后、数据库前幂等关闭。

最终五文件后端聚焦复跑：`177 passed, 25 subtests passed`，另有 23 条既存 FastAPI
`on_event` deprecation warnings；后端终审结论为 **ACCEPT**。全工作区
`git diff --check` 通过，生产源码仅有一个 `useChat(`，未发现旧 Dream public
EventSource/parser/reducer/API caller，`agent_runner.py` 无 diff。

仍属 R9 发布验证而非 R8 审查结论：真实 Redis Lua/滚动升级、真实 PostgreSQL 并发、
reasonable-scope 回归、TypeScript、ESLint、production build、Admin no-buffer、无头与
有头 Chromium、最终 OpenAPI/bundle inventory 以及 owned process/task residue。自定义
sink 若故意吞取消，Coordinator 会先撤销 lease 并有界 detach；默认生产 sink 不这样
做，但进程关闭时的零残留仍须在 R9 实测并作为显式风险记录。

## 八、R10 Observer 展示投影设计复核补充（2026-08-11）

> 结论：**修改后接受**。修改条件已经写入当前设计与实现边界，但相应测试执行、
> 不可变发布证据仍须按 `testing-and-acceptance.md` 记录，不能因源码存在而记为
> release PASS。隔离真实 Redis adapter 已单独完成 4 个 test method + 2 个
> RESP2/RESP3 subtest；该窄结果不等于分布式 HTTP 控制面通过。

本补充只批准在既有 actor-scoped Dream-files GET 上附加可选、content-free、
display-only `agentActivity`，并要求同时满足：

1. 原有 actor/run/workspace/thread 授权先完成，随后只读取完全匹配的
   `(runId, threadId, actorId)` hint；最高 generation/sequence 胜出，旧代不能覆盖
   新代，actor/generation 不进入 wire。无匹配或任何投影异常时字段缺席，原响应仍成功。
2. 响应只含稳定 activity/operation 枚举、sequence、terminal/reconcile 标记和可选
   SHA-256 关联值；不得包含 raw tool/subagent 名称、调用 ID、input 或 output。
3. `agentActivity` 只影响说明性文案，不得设置 Workflow 状态、确认资格、Chat
   lifecycle、输入锁或 Stop，也不得新增 SSE、EventSource、parser 或 reducer。页面
   view-model 只可展示 `content_generation`、`workflow_operation` 和
   `reconcile_requested` 业务提示；Observer terminal、waiting-confirmation、subagent
   和 generic-tool hint 必须返回空文案，由 canonical `ChatPanel` 独占展示。
4. 默认 sink 仍是 bounded/process-local/non-durable；existing owning services 和 DB
   仍是唯一业务真相，Observer 失败仍与 canonical Chat stream 隔离。reader 异常先
   清为 reconcile，最多重订阅/replay 一次；稳定 event ID 去重，二次失败有界关闭且不
   重启主 Agent producer。
5. `redis>=5,<8` 只支撑已知 `(session_id, turn_id)` 的共享 stream、跨进程 writer/
   replay 与单终态仲裁；它不形成 Dream transport，也不提供 active-turn discovery、
   `/status`、Stop、confirmation 或 HTTP stream routing。
6. 当前 backend 必须保持单 uvicorn worker 和 Cloud Run `max-instances=1`，直到另一个
   正式设计把上述进程内 owner 迁为可验证的分布式控制面。隔离 Redis 对 RESP2/3
   live XREAD、跨进程写/回放、并发单终态、legacy finish、TTL 和精确清理的 PASS
   不得被解释成 multi-worker/pod HTTP reconnect PASS。

当前 worktree 已有 `dreamViewModel.ts` 的展示白名单及正/负 fixture，并由
`StoryWorkspaceDreamPage.tsx` 仅将其结果用于 `activityCopy`；它没有进入
`lifecycleState`、`isReadOnly`、confirmation、Stop 或 Chat props。Redis 的上述隔离
结果也已实际执行。Observer/UI 聚焦结果为后端 116 passed + 20 subtests、前端 6
passed，并通过 TypeScript、scoped ESLint 和 diff check。Observer 的完整
broad/browser 与不可变制品 gate 仍以验收文档的最终同候选版本结果为准。

若上述任一边界被实现破坏，本补充自动失效并重新打开 DR-001、DR-005 或公开协议审查。

## 九、R27 当前源码与执行证据复审（2026-08-12）

### 当前源码结论

| 复审项 | 当前证据 | 判定 |
|---|---|---|
| 无第二 Agent runtime/公开协议 | 生产源码只在 `ChatPanel.tsx` 保留一个 `useChat(`；无 `/dream-agent/messages|events|tool-confirm`、`DreamStreamAdapter`、`iter_dream_run_events`、旧 hook 或 Provider 匹配 | **通过** |
| Dream UI 复用 canonical Chat | `StoryWorkspaceDreamThreadChat.tsx` 直接组合 `ChatPanel`，history/status/stream/send/confirm/stop 仍以 `threadId` 走 Chat contract | **通过** |
| Observer 不入主路径 | `thread_factory.py` 在 producer 前旁路 attach，attach/close 异常只记录且不阻断 Chat；`dream_lifecycle_observer.py` 只订阅 normalized EventBus 并写 bounded process-local hint | **通过** |
| 权限不降级 | Chat route 先验证 owned thread，再以 authenticated actor + thread 反查 retry leaf；actor/workspace/run/Deck/binding/revision 不一致时 fail closed | **通过** |
| Service/EventBus/session owner 不变 | `ClaudeAgentService` 仍负责 context、normalized events、persistence 和 terminal order；Factory 仍负责 session/task/bus/lock；Observer 无反向控制 | **通过** |
| 单终态与清理 | `message-final` 仅是 candidate，最终 `finish` 才结算；R19 focused/broad、S01–S10 浏览器、S11–S14 后端/源码与 R25 中断清理已执行 | **通过** |
| protected runner | `git diff --quiet a506c83 -- backend/libs/claude_agent_kit/server/agent_runner.py` 通过 | **通过** |

### 当前可执行证据

- R17：owned PostgreSQL/Admin/fake-provider 生产形态链路完整通过；
  32/32 Gateway 与 fake-provider 请求一一对应，账本平衡，外部调用为零，精确清理。
- R19：backend broad `1927 passed / 17 skipped / 655 subtests`，focused
  `687 passed`；Redis/Gateway loopback 通过；frontend `340`
  unit/contract + TypeScript + lint + build 通过；S01–S10 headless Chromium
  与 S11–S14 后端/源码验收通过。
- R20：Admin 六个 generated-story 契约文件 `28/28` 与 TypeScript 通过，
  production query 未改。
- R24/R25：验证器 24 个相关测试与 read-only SQL probe 通过；
  PG16 provider-free clone 和注入 SIGINT（exit 130）的资源/源数据/原工作区
  清理全部通过。
- R26：只发出一个真实请求，无重试/回退；`hy-preview` 精确解析且
  provider 报告 `hy3-preview`，HTTP 200 settled/succeeded，
  `entitlementBound=true`，reserve = capture + release 且剩余为零；该次运行实际
  观测到 text start/delta/end、单 `message-final`、单 `finish(stop)`、
  非空 DB assistant、session 匹配、源完整性与精确清理。

以上记录不包含 prompt/provider 正文、session/token/URL/凭据或私有数据。
R26 使用 clone-only entitled user 的新建 generic canonical thread；该用户可用的
terminal Dream thread 数为 0。因此它证明 shared Chat runtime + Gateway +
model/accounting path，不证明 terminal Dream workspace binding。既有 Admin
entitlement-enforcement 缺口保留为 residual risk；该次 proof 强制非空
entitlement binding，没有利用该缺口。

### R28 验证器与独立复审闭环

R26 后独立 review 发现，当时验证器的通用 success predicate 并未强制：

1. 非空 `message-final.text` 与严格
   `text-start → text-delta+ → text-end → message-final → finish → EOF`；
2. `visibility`/`dispatch_status`/`dispatchStatus` 私有 discriminator 不得进入可见行，
   以及 REST history 必须精确是两个非空 canonical projected rows。

这是**未来证据可假阳性**，不是已发生的 R26 运行失败：当次 sanitized
receipt 确实记录了一组 start/delta/end 和非空 DB assistant。但 clone 已删除，
不能伪造一个追溯的 final-text boolean，也不允许第二次 provider 请求。R28
必须只修 verifier/tests，让所有正负 fixture fail closed，并经独立复审返回
ACCEPT。

R28 实现已完成：成功谓词强制非 blank `message-final`，精确一个
start、至少一个 meaningful delta（允许额外 whitespace delta）、精确一个 end
和严格 tail；private denylist 包含 visibility/dispatch 异名，REST history 必须是
精确可见投影。128 个测试 + 37 个 subtest 通过，未调用 provider，
未改产品 runtime 或 `agent_runner.py`。独立 read-only re-review 又通过 19 个
定向测试并返回 **ACCEPT**；未发现新 false positive、隐私泄漏或 blocker，
也未调用 provider。

### 当前结论

runtime/protocol/reducer 收敛、Observer 旁路、权限、owner 边界、单终态、清理、
protected runner 和 R28 证据谓词均已有源码与执行证据支持。**R27
正式结论为 ACCEPT，无剩余 P0/P1 设计或本地实施 blocker。** 该结论不代表
headed、staging/canary、不可变回滚或生产 load 已执行，也不消除 Admin entitlement-
enforcement residual risk。

## 十、R32 最终可见浏览器验收复核（2026-08-12）

> 结论：**接受**。R27 的架构和实现结论不变；R32 补齐了当时尚未执行的当前候选
> 可见 Chromium 门禁，因此 DreamAgent 仓库级重构与本地验收没有剩余 P0/P1
> blocker。

复核证据：

1. Playwright 对 `dream-agent-thread-convergence.spec.ts` 发现且只发现 S01–S10；
   源码没有 `waitForTimeout` 或固定 `sleep`。
2. `--browser=chromium --headed --workers=1` 实际打开可见浏览器并以
   `10 passed (14.4s)` 完成，覆盖发送/增量、双向页面切换、工具确认与
   AskUser、network/reject-only、子代理、Stop、前后置失败、断线重连与刷新恢复。
3. S11–S14 后端/源码子集重新执行为 `9 passed, 2 deselected`；Observer 旁路、
   重放幂等、单终态和旧协议迁移契约保持通过。
4. 生产源码仍只有 `ChatPanel.tsx` 一个 `useChat` owner，旧 Dream 对话路由、
   adapter、service 和 hook 均不存在；受保护 runner 与 HEAD 的 SHA-256 一致。
5. 用户重启已清除 R30 记录的 macOS `UEs` 残留。R32 跑后没有 Playwright/
   Chromium 进程、5173/8765 监听或新报告产物；未再次调用真实供应商。

本结论是对当前工作树的设计、实现和本地验收接受，不是生产发布签字。staging/
canary、不可变制品回滚、生产负载以及既有 Admin entitlement-enforcement 风险仍由
发布流程单独处置，不构成保留第二协议或延迟后续 Dream 业务实现的理由。

## 十一、R35 全业务交互设计正式审查（2026-08-12）

> 结论：**修改后接受 → 接受**。初审发现 Mermaid 消息标点导致 1 张图无法解析，
> 且部分能力虽有事实说明却缺统一的“规则/边界/证据”审查标签；R34 已修正，复审
> 没有发现第二套 Agent runtime、虚构的页面能力或 workflow/thread 反向控制。

### 业务覆盖判断

1. `business-interaction-design.md` 以主链 + B01–B21 覆盖入口、启动、runtime、
   Dream 文件、编辑确认、共享对话、工具确认、Observer、内部命令、Guidance、
   Stop/Cancel、Retry、Execution、Episode、artifact、Story Index、完成、权限并发和
   generic output 边界。
2. 每个 B 项恰有一张 `sequenceDiagram`，同时列明业务意图、owner/规则或权限边界、
   失败/重放分支和源码/测试证据；文档没有使用状态流转图冒充业务交互。
3. 22 张 Mermaid 已由项目 Mermaid 11.16 parser 逐张解析通过；B01–B21 结构覆盖和
   55 个相关相对链接通过。

### 对抗性源码复核

- production `useChat` 仍只有 `ChatPanel.tsx` 一处；Dream 页面组合它，没有第二
  transport/parser/reducer。
- 旧 `DreamStreamAdapter`、`iter_dream_run_events`、Dream 专用 hook 和 EventSource
  没有生产调用方。
- 通用 Guidance 只有 API/hook，Dream/Execution 页面没有 caller；thread busy 时可
  返回 `dispatched: false`，当前没有 B10 同等级 startup/lease 恢复证明，文档如实
  标注。
- Workflow Retry 与 Cancel 后端能力没有被画成 Dream 页面已交付，也没有虚构其与
  Chat Stop 的自动联动。
- Execution 的 route gate 由 `storyWorkspaceCanAccessExecution` 读取
  `confirmationAccepted`；`confirmationDispatched` 只影响等待文案/主动入口。
- Dream context 在通用 story-bundle projection 前 early return，故 generic
  `hy3-preview` thread proof 没有被升级为 Dream 文件/终态证明。

### 安全、复杂度与开放决策

权限没有因共享 thread 协议而削弱：workflow 写命令仍校验 actor、run/thread、
revision/ETag、idempotency 和服务端 binding；浏览器不能选择 provenance、路径、
lease owner 或任意 Agent 命令。Observer 仍是可丢弃展示投影，不写 lifecycle，也不
反向控制 `ClaudeAgentService`。

§26 的八项是业务 owner 选择，不是被文档隐藏的实现缺陷：Stop 与 Cancel 是否一键
编排、失败 Retry UI、通用 Guidance、确认后编辑、Episode 多选、完成后导出/发布、
subagent 展示位置和 generic story projection。业务方裁决其中任一项后，应只重开
对应 B 项及其测试，不应恢复第二协议。

## 十二、R39 业务合同与集成边界复审（2026-08-12）

> 结论：**修改后接受 → 设计 ACCEPT**。实现尚未按本轮设计修正，因此本结论只授权
> 后续代码实施，不复用 R35 的“实现已完成”结论。

### 初审阻断

| ID | 阻断问题 | 修正 |
|---|---|---|
| R39-01 | Dream 文档没有完整 Project/Episode Artifact identity、sealed snapshot、revision、CAS 和 Admin/Dream writer boundary | 新增 `project-episode-artifact-contract.md`，逐项映射 Admin 权威合同 |
| R39-02 | Story Workspace 目录混合设计、执行记录、评审、测试证据和变更历史，产生多个事实 owner | 删除旧集合与 evidence，重组为 8 份功能模块文档并迁移仓库引用 |
| R39-03 | Dream runtime 等待 SDK init 的闭包安装在 `AgentStreamingCallbacks` | 目标改为命名 activator 在 `ClaudeAgentService.assemble_context` 使用 verified workspace facts；Phase 3 入口不变 |
| R39-04 | ThreadFactory 直接 attach/close Dream coordinator，未使用现有 Observer 模式 | 目标改为 `DreamObserver` 注册 `SessionObserverRegistry`；ThreadFactory 只发通用 hook |
| R39-05 | Router 以字段 tuple/set 充当 DTO | 目标改为命名 enum、DTO 和 projector class，同时保持 JSON 形状与私有字段拒绝 |
| R39-06 | Dreamflow 缺完整 tool/action/Agent ownership 与时序 | 新增 `dreamflow-tool-boundaries.md` 与 Story Workspace workflow-actions 模块 |
| R39-07 | Dream context 作为 `ClaudeAgentRunRequest` 字段跨 router/dispatcher 传递，改变了 Chat 报文语义 | 目标改为 actor + thread 在 assembly 内服务端映射，Chat request/SSE 无 Dream 字段 |
| R39-08 | 不存在的 post-confirmation Workflow 状态被写入设计、代码和 DDL | 设计状态机改为 Workflow 保持 `confirmed`，Thread 独立显示运行；要求 Admin 前向数据/约束迁移 |

### 对抗性设计检查

1. **第二 runtime**：目标只有 `ClaudeAgentService`、同一 EventBus、Thread SSE 和
   ChatPanel；Dreamflow/Observer 不调用 runner，不产生 SSE，检查通过。
2. **换名旧 SSE**：没有 Dream public event、cursor、snapshot/reducer 或 transport，
   检查通过。
3. **Observer 真值风险**：`DreamObserver` 只订阅内部 normalized facts，通过 owning
   service 幂等投影；不能确认工具、Stop、发终态或推断 Workflow 完成，检查通过。
4. **Claude 职责**：`agent_runner.py` 与 Phase 3 `run_streaming` 入口保持不变；仅
   Phase 1 assembly 增加内部映射/激活，检查通过。
5. **权限**：Dream 业务写仍要求 actor、Thread、Workspace、Run、Deck、expected
   revision、idempotency 与路径完整性，检查通过。
6. **数据泄漏**：typed DTO 不增加字段，Artifact public DTO 无路径/Thread locator/
   source metadata，检查通过。
7. **重复消息/终态/确认**：私有命令沿用 claim/lease；canonical store/Bus 保持一套；
   Workflow terminal 仍由 domain fact，检查通过。
8. **最小范围**：复用现有 resolver、context builder、registry、event classifier、
   Chat runtime 和 owning services，不引入新 broker/store/provider，检查通过。

### 接受条件

代码实施必须满足以下可执行门禁后，R39 才可从“设计 ACCEPT”升级为“实现 ACCEPT”：

- `ClaudeAgentRunRequest`、router 和内部 dispatcher 无 Dream context 字段；
- `_make_dream_runtime_init_cb` 和 Dream `on_message` callback 不存在；
- ThreadFactory 无直接 Dream coordinator 依赖，registry 中存在 `DreamObserver`；
- Router 无 `_CLIENT_THREAD_FIELDS`、`_CLIENT_MESSAGE_FIELDS`、
  `_PUBLIC_TOOL_CHOICES`；
- live Dream/Frontend/Admin schema 无被删除的 Workflow 状态；
- protected runner diff 为空；聚焦测试、类型/构建和 diff check 通过。

## 十三、R41 实现接受复审（2026-08-12）

> 结论：**ACCEPT**。R39 的全部实现门禁已关闭，未发现第二套
> Agent runtime、前端 transport/parser/reducer、Observer 反向控制或新的
> Claude Agent 报文。

| 审查项 | 实现证据 | 结论 |
|---|---|---|
| Thread 上下文 | `DreamThreadContextMapper` 用 actor + thread 在 `assemble_context` 内解析；request/router/dispatcher 无 Dream 字段 | 通过 |
| Runtime 激活 | 命名 activator 在 assembly 阶段使用 server evidence；无 closure/on-message init callback | 通过 |
| Agent 入口 | Phase 3 仍调用原 `runner.run_streaming(execution.run_options, callbacks)`；`agent_runner.py` diff 为空 | 通过 |
| Observer | `DreamObserver` 通过 `SessionObserverRegistry` 注册，异常与 SSE 隔离，不发终态/确认/停止命令 | 通过 |
| Router DTO | 命名 Enum/Pydantic DTO 投影保持原 JSON，无字段常量 allowlist | 通过 |
| Dream UI | `StoryWorkspaceDreamThreadChat` 组合唯一 `ChatPanel`，无 Dream EventSource/parser/reducer | 通过 |
| Workflow | 不存在的 post-confirmation 阶段已从 live code/docs/DDL 移除；Admin 0033 前向归一历史数据 | 通过 |
| 权限/数据 | Workflow/Artifact 写仍校验 actor、thread ownership、run/binding/revision/idempotency；配置库 capability 满足 | 通过 |

结果由全量后端、前端契约、Admin 单测/构建、真实 PostgreSQL
迁移检查、一次 `hy3-preview` 真实模型链路以及 headless/headed
Chromium 共同支持。过度设计复核未发现新 broker、event store、
Dream transport 或可删除的 wrapper。未执行的生产 load、staging/canary 与
不可变制品回滚仍是发布流程门禁，不是本地架构阻断。
