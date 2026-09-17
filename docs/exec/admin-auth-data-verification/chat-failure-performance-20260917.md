<!-- [Input] One real local Dream Chat turn, its SSE terminal, Admin DTO request timings, and the current Dream/Admin ownership contracts. -->
<!-- [Output] Sanitized failure diagnosis, optimization design, implementation scope, and repeatable validation ledger. -->
<!-- [Pos] Current Chat incident receipt; it contains no OAuth credential, provider key, password, transcript body, or database DSN. -->
<!-- [Sync] 2026-09-17: record the initial diagnosis and implementation plan before focused and real-path validation. -->

# Chat 失败与 Admin 数据接口延迟验证

## 本轮 Prompt Architect 规划

### Optimized Prompt:

Act as the Dream Chat and Admin DTO-boundary performance owner. Diagnose the real local Chat failure through the public browser, Dream SSE, Admin business API and Gateway records without reading or changing unrelated user data. Preserve the production boundary `Dream Pydantic DTO → Admin Zod DTO → Domain Service → typed Repository → Drizzle/UOW`; Dream must not regain PostgreSQL credentials, SQL, ORM, transaction or permission logic. Preserve request authentication, principal validation, operation/schema digest checks, Runtime, EventBus, SSE, turn/resume/cancel, resource-policy LKG, shared filesystem behavior and the `.claude-tmp` contract.

Use the observed evidence that the current turn persisted its user message and then received Gateway HTTP 402 `SUBSCRIPTION_TOKEN_ALLOWANCE_EXHAUSTED`, with 76,005 available Tokens and 102,993 required for the selected model request. Do not mutate subscription ledgers, fabricate allowance, silently cap model output, or retry the non-idempotent turn. Convert that known provider terminal into one redacted structured SSE error and localized actionable Chat feedback.

Reduce Admin boundary latency by retaining the fully validated immutable capability DTO inside the existing `AdminDataClient`. Explicit `capabilities()` remains a forced refresh that clears all advertisements and the snapshot before I/O; a failed or invalid refresh leaves the client unready. Domain consumers use `capabilities_snapshot()` so one authenticated request/process bootstrap does not repeat identical capability discovery before every DTO operation or Runtime delegation. Admin still performs actor mapping, authorization, data filtering and transaction work on every business call. Keep `/principal` fresh per request.

Update affected source headers, folder contracts and this receipt. Add deterministic tests for snapshot reuse, forced-refresh invalidation/recovery, warmed delegation creation, redacted allowance SSE and localized error rendering. Run focused Python and frontend checks, diff/Markdown validation, then compare the real Chat POST response-header latency before and after using the normal local Dream/Admin/Gateway/PostgreSQL services. A 402 terminal may be used to measure the pre-model path; it is not a successful model acceptance. Report exact commands, exit codes, timings and any remaining requirement for a successful model reply.

USER REQUIREMENT:

Investigate why all Chat conversations fail and optimize the slowdown introduced after Dream moved persistence to Admin data interfaces.

## 已有证据与决策

| 项目 | 证据 | 结论 |
| --- | --- | --- |
| Chat 失败 | 公开 `/api/claude-agent` 返回正常 SSE；用户消息已持久化，模型生成前 Gateway 返回 402 | 当前失败是订阅周期 Token 可预留额度不足，不是 Admin DTO 持久化失败 |
| 当前额度 | 可用 76,005，当前模型请求需要 102,993 | 在额度或受支持模型配置改变前，真实回复仍会失败；本轮不修改账本或伪造额度 |
| 首包延迟 | 优化前真实 POST 约 2.836 秒才收到 SSE headers | SSE 前存在可测的 Admin DTO 调用成本 |
| capability | 单次 authenticated capability GET 约 0.32–0.35 秒，同一 turn 在 Workflow、SystemConfig 和三个 Runtime delegation 等位置重复读取 | 复用已经完整验证的 frozen DTO；不缓存用户 principal，不移动权限或事务到 Dream |

## 保持不变的行为

- Dream 继续只提交严格 Pydantic 业务 DTO；Admin 继续使用 Zod、Domain Service、typed Repository 和 Drizzle/UOW。
- 每个业务接口仍由 Admin 校验调用服务、委托用户、scope、实体权限和事务条件。
- capability 缺失、hash 漂移、刷新失败或响应非法仍 fail closed；没有 PostgreSQL fallback。
- 用户消息未知提交、assistant 部分持久化、SSE 断开、turn/resume/cancel 和 Runtime delegation 原语义不变。
- Resource provider 继续在后台保留 revision/LKG 与错误隔离，Agent turn 主路径不查询资源策略。

## 验收计划

1. Python provider-free tests verify one capability HTTP request for repeated snapshots, explicit refresh invalidation/recovery, and no duplicate discovery for a warmed delegation creator.
2. Claude Agent service tests verify that only the known allowance code becomes `GATEWAY_TOKEN_ALLOWANCE_EXHAUSTED`, with no available/required/provider/request details in SSE.
3. Browser harness verifies localized allowance feedback, persisted-message guidance, read-only reload and absence of raw provider text.
4. Real local Chrome repeats one minimal public Chat turn. Record POST header latency and the truthful terminal; do not resend after an unknown write.
5. Static review confirms Dream still has no production PostgreSQL access and `git diff --check` plus Markdown path checks pass.

## 验证回执

| 验证 | 工作目录 | 结果 |
| --- | --- | --- |
| `PYTHONPATH=. uv run pytest -q tests/test_admin_data_boundary.py tests/test_admin_delegation.py tests/test_claude_agent_service.py` | `backend` | exit 0；152 passed、9 subtests passed |
| `PYTHONPATH=. uv run pytest -q tests/test_admin_*.py` | `backend` | exit 0；1450 passed；覆盖全部 Admin consumer、request auth、Runtime delegation、receipt 与路由合同 |
| `PYTHONPATH=. uv run pytest -q tests/test_postgres_runtime_sql_boundaries.py` | `backend` | exit 0；7 passed；候选生产源码继续不含 Dream PostgreSQL client、SQL、DSN 或退休 repository |
| `corepack pnpm exec playwright test app/_dream/components/chat/__tests__/ChatThreadBindingConflict.test.ts --reporter=line` | `frontend` | exit 0；1 passed；真实 Chromium 验证 typed allowance 卡片、消息保留提示、provider 明细隐藏与只读reload |
| `corepack pnpm exec tsc --noEmit` | `frontend` | exit 0 |
| `corepack pnpm exec eslint app/_dream/components/chat/ChatMessageList.tsx app/_dream/i18n.ts app/_dream/components/chat/__tests__/ChatThreadBindingConflict.test.ts` | `frontend` | exit 0 |
| `git diff --check`、本文件相对链接检查 | repository root | exit 0；`markdown-links-ok` |

## 真实本机复测

本轮只重启 Dream `8765` 后端以加载修改；Admin `3000`、PostgreSQL `54329`、Dream frontend `5173` 保持原进程。重启后 `/api/health` 返回 200，Dream 后端监听进程为本轮启动的 PID 49767。

使用现有 Chrome 正常登录态，从 `http://localhost:5173/story-workspace/chat` 走公开生产入口发送两个最小消息。两条用户消息均通过 Admin 数据接口保存在正常 Chat Thread `34ec1cad-4e1d-40b6-a99e-448ebc134819`，浏览器展示新的 typed allowance 卡片，没有显示 provider response、request id 或内部异常。

热态 Chat POST 的 Resource Timing：

| 指标 | 优化前 | 优化后 | 变化 |
| --- | ---: | ---: | ---: |
| `/api/claude-agent` request → SSE response headers | 2,836.2 ms | 2,130.5 ms | -705.7 ms（-24.9%） |
| 优化后 request → 402 terminal 完成 | 不作为接口准备基准 | 7,242.7 ms | 后半段包含 Runtime 启动与 Gateway 额度拒绝，不由 capability cache 决定 |

真实 Gateway 仍返回 `SUBSCRIPTION_TOKEN_ALLOWANCE_EXHAUSTED`：可用 76,005，本次热态请求需要 103,004，所选模型为 `gpt-5.6-luna`。这证明失败根因仍是额度不足；本轮没有修改 subscription、ledger、模型 capability 或 Gateway request，也没有把 402 冒充为成功模型验收。成功回复仍需要可用额度不少于实际请求预留量，或由产品所有者通过受支持的 Admin 模型/订阅配置降低请求所需预留量。
