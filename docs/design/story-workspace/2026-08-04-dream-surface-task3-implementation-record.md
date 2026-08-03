# Dream Surface Task 3 实施记录（story-workspace 合同：StoryWorkspaceGuidanceCommand + 幂等指导端点 + ReviewEvent guide 审计）

> 依据：`2026-08-03-dream-surface-execution-implementation-plan.md` Task 3（Step 1–Step 5，含 2026-08-03 D11/D12/D13 兼容性修订与复核批注 R5）；设计语义以 design_004 §5.3/§6、DEC-032 为准
> 日期：2026-08-04

## 任务范围

- 合同层（`backend/story_workspace/contracts.py`，DEC-026）：`StoryWorkspaceSurface` 值对象、`StoryWorkspaceGuidanceKind`（`retry-step|free-text`）、`StoryWorkspaceGuidanceCommand`、`StoryWorkspaceGuidanceCommandPayload`（请求体 + kind/字段一致性校验）、`StoryWorkspaceExecutionProjection`、`StoryWorkspaceReviewEventAction`（ReviewEvent action 枚举扩展 `guide`，合同层扩展，零 DDL）。合同版本 1.1.0 → 1.2.0。
- 服务层（新增 `backend/services/story_workspace/guidance_service.py`）：`StoryWorkspaceGuidanceService.submit_guidance`。
- 网关（`backend/services/deck/story_workflow_gateway.py`）：`StoryWorkflowApplicationGateway.submit_guidance`（run 读取复用 `WorkflowRunService.read_run` actor 范围读取）。
- 路由（`backend/routers/story_workspace.py`）：`POST /api/story-workspace/runs/{run_id}/guidance`（以 PLAN 为准的路径，非 `/workflow-runs/...`），`StoryWorkflowGateway` Protocol 增加 `submit_guidance`。
- 注入通道（`backend/claude_agent/service.py`）：`ClaudeAgentRunRequest` 新增 `message_metadata` 字段，`_persist_user_message` 透传——见「注入机制落地方式」。
- 错误码（`backend/services/errors/error_registry.py`）：新增 `WORKFLOW_RUN_NOT_GUIDABLE`（phase=run）。

## 承载与幂等（对照 D11/D12/D13，零 DDL）

- **持久化**：指导以 `metadata.kind="story-workspace-guidance"` 的 user 消息落 `chat_message`（复用既有 `metadata TEXT` 列与 `save_chat_message(..., metadata=...)`，`backend/database.py` 只读未动）。
- **审计字段**（ReviewEvent action=`guide` 语义）全部承载于同一 metadata：`story_workspace_run_id` / `actor` / `request_id`（服务端 uuid4）/ `idempotency_key` / `command_kind` / `step_id` / `text_summary`（≤200 字符）/ `review_action="guide"` / `command_fingerprint`；`created_at` 提供 timestamp。同时写一条 `logger.info("story_workspace_guidance", ...)` 审计日志（沿用 `_audit_review_action` 模式）。指导历史可按 `thread_id` + `metadata.kind` 反查，供 Task 5 侧边栏使用。
- **幂等**：消息 id = `guide_<idempotency_key>`；服务层**先 SELECT** 按 id 取出行并比对 `command_fingerprint`（`{run_id, actor, command_kind, text, step_id}` 的规范化 JSON sha256）：同键同内容 → 202 `replayed: true`，**不重复注入、不重复落库**（返回原 `request_id`）；同键不同内容 → 409 `IDEMPOTENCY_CONFLICT`，原记录保持不变。`INSERT OR REPLACE` 仅作为底层去重兜底，语义比对在应用层完成（弥补静默覆盖弱点）。
- **可指导状态**：`GUIDABLE_RUN_STATUSES = {CONTINUING, FAILED}`——`FAILED` 承接 §5.2 唯一页面级动作「重试失败步骤」（经侧边栏 `retry-step` 受控触发）；其余状态（含 `pending_review`）一律 409 `WORKFLOW_RUN_NOT_GUIDABLE`。`awaiting-guidance` 为投影态，未新增 `RunStatus` 枚举（`backend/models/workflow_run.py:26-37` 未动）。
- **通道前提**：run 必须携带 `source_voice_thread_id`（发起该 run 的同一 Chat thread，DEC-032）且该 thread 归属当前 actor，否则 409 `WORKFLOW_RUN_NOT_GUIDABLE`。
- **actor 防伪**：请求体 `actor` 只是声明式 hint，服务端强制等于认证 actor（`_workflow_actor`），不一致 → 403 `WORKFLOW_PERMISSION_DENIED`。

## 注入机制（同 thread 新 turn，复核批注 R5）落地方式

代码现状无 mid-turn 注入通道，落实路径如下：

1. 服务端先把指导消息持久化（幂等判定之后），消息本身就是「新 user turn」的用户消息（id 即 `guide_<key>`，parts 为 `[story-workspace guidance · run <id>] ...` 前缀文本）。
2. `build_thread_turn_dispatcher()`（guidance_service 内，懒加载 `agent_factory.claude_agent_thread_factory`）作为默认 dispatcher：
   - 线程已有 in-flight turn（`session_snapshot(thread_id).lifecycle == "running"`）→ 不注入（无 mid-turn 通道），返回 `delivered=False`；响应仍 202（Accepted/入队语义），`dispatched: false` 使延迟可观测；指导行已持久化，下一 turn 可携带。
   - 否则构造 `ClaudeAgentRunRequest(user_id, thread_id, resume=True, message_id=guide_<key>, message_parts, message_metadata=metadata)`，后台 task 驱动 `run_streaming` 排空帧——SDK 按 `claude_session_id` resume 既有 transcript，指导作为同 thread 的新 user turn 交给 runner；assistant 帧由 service 既有回调持久化。
3. **`backend/claude_agent/service.py` 配套改动**（偏差 3，必须项）：`run_streaming` 路径的 `_persist_user_message` 会用同一 `message_id` 再 `INSERT OR REPLACE` 一次用户行，原实现不传 `metadata` 会把 guidance metadata 抹成 NULL。故 `ClaudeAgentRunRequest` 新增 `message_metadata: Optional[dict] = None` 并在 `_persist_user_message` 透传——注入 turn 的重存与原写入完全收敛（同 id、同 parts、同 metadata），普通聊天路径 `message_metadata=None` 行为与现状完全一致。
4. dispatcher 为可注入 seam（服务构造参数），测试用录制替身；dispatch 异常只记日志不影响 202。

## TDD 过程摘要（Red → Green）

| 步骤 | 测试（`backend/tests/test_story_workspace_guidance.py`） | Red | Green |
|------|------|-----|-------|
| Step 1/2 | 全文件 23 例 | collection ImportError（`StoryWorkspaceExecutionProjection` 等不存在） | — |
| Step 3/4 服务层 | `test_guidance_accepted_when_run_continuing`（202 语义 + metadata 审计字段 + review_action=guide + dispatcher 收到同 thread 新 turn） | ✅ Red | ✅ |
| 幂等重放 | `test_guidance_idempotent_replay`（两发 202、单条记录、同一 request_id、dispatcher 仅 1 次） | ✅ Red | ✅ |
| 冲突重放 | `test_guidance_conflicting_replay_returns_409`（同键不同内容 409 `IDEMPOTENCY_CONFLICT`、原记录保留） | ✅ Red | ✅ |
| 状态守卫 | `test_guidance_rejected_when_not_confirmed`（pending_review → 409）+ `..._when_run_completed` | ✅ Red | ✅ |
| 通道守卫 | `..._without_source_thread` / `..._when_thread_not_owned` / `..._when_actor_mismatch`（403） | ✅ Red | ✅ |
| retry-step | `test_guidance_retry_step_accepted`（step_id 落 metadata 与 turn 文本） | ✅ Red | ✅ |
| dispatch 降级 | `test_guidance_dispatch_failure_still_accepted`（202 + `dispatched: false`） | ✅ Red | ✅ |
| 合同 | kind 必填字段校验（422/ValidationError）、枚举值、`guide` 值、Surface 值对象、ExecutionProjection 形状 | ✅ Red | ✅ |
| 路由层 | `test_post_guidance_*`（202 / 重放 202 replayed / 冲突 409 / 未确认 409 / 未知 run 404 / 校验 422 / actor 不符 403，错误 payload 走 `build_error_payload`） | ✅ Red | ✅ |

中途一次真实缺陷修复：路由层测试初跑 503，定位为测试替身网关跨线程复用 SQLite 连接（`sqlite3.ProgrammingError`）；改为每请求 `database.get_db()`（与生产网关一致），非实现缺陷。

## 测试运行输出

```
backend/.venv/bin/python -m pytest backend/tests/test_story_workspace_guidance.py -q
23 passed in 0.64s

回归（合同/路由/workflow/claude_agent/chat_message 相关）：
test_story_workspace_api.py test_story_workspace_contracts.py test_story_workspace_review.py
test_story_workspace_agent_integration.py test_api_routes.py test_workflow_run.py
test_workflow_preflight.py                       → 90 passed, 106 subtests passed
test_claude_agent_service.py test_claude_agent_thread_factory.py
test_claude_agent_runner.py test_server_claude_agent.py → 181 passed, 1 skipped
test_database.py test_chat_thread_retrieval.py test_session_events.py
test_agent_session.py test_api_endpoints.py      → 32 passed, 37 subtests passed
```

## 与 PLAN 的偏差（均按代码现实调整，语义不变）

1. **测试文件路径**：PLAN 写 `backend/tests/story_workspace/test_guidance.py`；代码现实后端测试扁平存放（Task 1 已记录同样偏差），落在 `backend/tests/test_story_workspace_guidance.py`。
2. **守卫测试联动更新（有意合同演进）**：`test_story_workspace_contracts.py` 两处 `STORY_WORKSPACE_CONTRACT_VERSION == "1.1.0"` → `"1.2.0"`；`test_api_routes.py` 错误码守卫 43 → 44（`test_registry_has_all_44_canonical_codes_with_recovery`，注释注明新增 guidance 码）。二者属守卫锁定旧值，随合同演进同步。
3. **PLAN Files 外新增 `backend/claude_agent/service.py` 改动**：R5 要求落实「同 thread 新 turn」注入，而新 turn 路径会重存用户消息并抹掉 guidance metadata；`ClaudeAgentRunRequest.message_metadata` 是保持审计承载不被覆盖的最小改动（见上节 ③）。未触碰 `backend/database.py`，零 DDL。
4. **可指导状态集**：PLAN 测试仅示例 continuing 接受 / pending_review 拒绝；实现按 design_004 §5.2/§5.4 补入 `FAILED`（retry-step 唯一页面级动作的承载状态），文档化为 `{CONTINUING, FAILED}`。
5. **actor 语义**：PLAN 请求体含 `actor`；实现保留该字段但强制与认证 actor 相等（`AuthenticatedActorContext`「never construct from request body fields」的既有安全不变量），不一致 403。测试用数字 user id（`"11"`）替代 PLAN 示例的 `"user-1"`，语义相同。
6. **错误码**：非可指导状态需要客户端可区分的新码，注册 `WORKFLOW_RUN_NOT_GUIDABLE`（PLAN 未命名具体码）。

## 给 Task 5（指导侧边栏消费方）的接口说明

**端点**：`POST /api/story-workspace/runs/{storyWorkspaceRunId}/guidance`

请求体（`StoryWorkspaceGuidanceCommandPayload`，extra=forbid）：

```json
{
  "kind": "free-text" | "retry-step",
  "text": "…",              // free-text 必填（≤4000）；retry-step 可选补充说明
  "step_id": "s3",          // retry-step 必填
  "idempotency_key": "…",   // 必填（≤255），客户端生成；消息 id = guide_<key>
  "actor": "<user_id>"      // 必填且必须等于当前认证用户 id，否则 403
}
```

响应：

- `202`：`{message_id, story_workspace_run_id, review_action: "guide", status: "accepted", replayed: bool, dispatched: bool, request_id}`。同键同内容重放 `replayed: true` 且不重复注入；`dispatched: false` 表示线程有 in-flight turn，指导已入队（持久化）待下一 turn 消费——侧边栏可据此显示「已记录，待执行 Agent 拾取」。
- `409`：`{"error": {code: "WORKFLOW_RUN_NOT_GUIDABLE" | "IDEMPOTENCY_CONFLICT", …}}`（前者 = run 非 continuing/failed 或无 source thread；后者 = 同键不同内容）。
- `403`：`WORKFLOW_PERMISSION_DENIED`（actor 不符）；`404`：run 不存在；`422`：合同校验失败。

**指导历史反查**（侧边栏「指令+状态+时间」列表）：按 `thread_id`（= run 的 `source_voice_thread_id`）拉取 `chat_message` 后过滤 `metadata.kind === "story-workspace-guidance"`；审计字段（`actor` / `request_id` / `command_kind` / `step_id` / `text_summary` / `created_at`）齐全。本 Task 未新增 GET 端点（PLAN 未列），侧边栏可复用既有 `GET /api/claude-agent/threads/{thread_id}/messages` 客户端过滤，如需专用端点在 Task 5 补。

**投影**：`StoryWorkspaceExecutionProjection(run_id, phase, steps[], assets_ref, events[])` 合同已就位；`awaiting-guidance` 由 `continuing` + 阻塞步骤推断，不得映射为新 RunStatus。Chat 视图按 `metadata.kind` 过滤 guidance 气泡为 Task 4 Step 0 前置。
