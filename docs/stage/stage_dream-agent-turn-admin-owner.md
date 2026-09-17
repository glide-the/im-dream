<!-- [Input] Registry133, current Agent turn compositions, Guidance dispatch and the post-Registry133 source-only DB scan. -->
<!-- [Output] One executable plan for removing every ClaudeAgentService PostgreSQL fallback through existing DTO/ORM contracts. -->
<!-- [Pos] Cross-project Dream consumer phase; Admin remains the database and transaction owner. -->
<!-- [Sync] 2026-09-16: plan the mandatory Admin owner for every production Agent turn before implementation. -->

# Dream Agent turn 统一 Admin owner

## Optimized Prompt

You are an Expert Prompt Architect and senior Next.js, Better Auth, Python, PostgreSQL and Drizzle engineer. Complete one bounded cross-project database-access closure phase against the verified Admin Registry133 and Dream commit `38696794`. Reuse the existing strict Workflow context, Deck chat-context, Deck workspace-plugin, managed-MCP scope, Runtime activation, Chat Thread/Session, user-message, assistant-message and Story output DTO operations; do not add generic CRUD, a new database schema, or a duplicate transaction layer. Make every production Claude Agent turn carry one server-created `AdminWorkflowResolution`, one actor/Thread/Run-bound renewable `AdminTurnPersistence`, and the required immutable Deck snapshot. The remaining production caller is Story Workspace Guidance: after Admin has atomically persisted the command, resolve its exact Thread/Run context with the current OAuth actor, create the existing `server-persistence` delegation, resolve the exact Deck/Voice snapshot, and hand those objects to Dream's same-Thread Runtime dispatcher. If composition fails after the Guidance write commits, keep the existing 202 response with `dispatched=false`; never resend the write, invent a local actor, or open PostgreSQL.

Remove `ClaudeAgentService` fallbacks for Workflow mapping, Thread reads, SDK Session updates, plugin-pack metadata, managed-MCP workspace scope, Deck prompt lookup, user-message persistence and assistant-message persistence. A missing or wrong server owner must fail closed before the affected database-dependent operation. Reconnect must continue to subscribe to the existing EventBus without creating a new owner or turn. Preserve admission ordering and leases, Runner, ThreadFactory, EventBus, SSE frames, resume/cancel, auto-repair continuation, resource-policy default/desired/effective/revision and LKG behavior, shared-file operations, symlink rules, `0700`, and `CLAUDE_CODE_TMPDIR={AGENT_CWD}/{thread_id}/.claude-tmp`.

Update file headers, affected folder contracts, current Agent service/context design and architecture ownership text. Add provider-free tests proving the Guidance dispatcher carries the exact immutable Admin objects, closes an unused owner when the Thread is already running, leaves task cleanup to ThreadFactory for a scheduled turn, and reports `dispatched=false` after Admin owner/snapshot failures. Add AST assertions that `backend/claude_agent/service.py` has no `database` import, PostgreSQL call, SQL literal or legacy fallback. Run focused Guidance/Admin-owner/service tests, compileall, the current source-only DB scanner, Markdown reference checks and `git diff --check`. Record actual commands, exits and counts. Keep all unrelated dirty files unstaged.

Optional Enhancers: run the related Story Workspace and Claude Agent regression slice after focused checks; classify pre-existing full-suite failures without restoring database compatibility branches.

USER REQUIREMENT:

继续完成 Admin 统一认证与数据库访问服务；数据库改造成接口要遵从 DTO/ORM，Dream 保留业务编排、Agent Runtime、SSE 与共享文件系统。

## 目标与已有证据

- Dream `38696794` 已把 Launch source、Preflight、Run、dispatch 与 failure 生产持久化迁到 Admin Registry133。
- 2026-09-16 source-only AST 扫描读取 553 个 Python 模块：47 个生产 SQL 模块、23 个 driver/database import 模块、46 个 legacy helper 调用、347 个 transaction/connection 调用、35 个 Admin consumer 模块、152 个 operation 名称，`parse_errors=[]`。
- `backend/claude_agent/service.py` 仍含 1 个 SQL literal、3 个 `database` import 和 7 个 legacy helper 调用。Workflow、Deck、Thread、Session、managed MCP、Runtime activation 与消息写入均已有 Admin DTO/Drizzle 操作。
- 公开 Chat、Reflections 与 confirmation 已携带 Admin owner；Guidance 是当前会启动新 turn 却未携带 owner 的生产入口。

## 项目、责任与依赖

| 项目 | 责任 | 依赖 |
|---|---|---|
| Admin | 保持 Registry133 契约、Zod DTO、Service、typed Drizzle Repository 与 delegation 事务行为 | 已发布 Registry105-109、115、121、133 |
| Dream | Guidance 组合 Workflow/Deck/turn owner；Service 删除数据库 fallback；保持 Runtime 行为 | `AdminRequestAuth`、`AdminTurnPersistence`、严格 Pydantic DTO |
| 协调 | 冻结契约 hash、更新设计与数据库闭环证据、记录验证 | Dream 实现和确定性回归完成后更新阶段结果 |

需要读取的源码包括 Dream `routers/story_workspace.py`、`services/story_workspace/guidance_service.py`、`claude_agent/service.py`、`thread_factory.py`、`services/admin_data/request_auth.py`、`turn_persistence.py`、Workflow/Deck DTO 与相关测试；Admin 只核对当前 Registry133 广告与既有 Drizzle 实现，不制造无意义改动。

## 接口、数据库与配置变化

本阶段不改变 Admin HTTP 路径、DTO 字段、operation hash、数据库 schema 或配置。Guidance 继续先调用 `story-workspace-guidance.submit`；只在返回新 dispatch 时，用同一 OAuth actor 调用现有 `workflow-context.resolve` 和 `deck-chat-context.resolve`，再创建现有 `server-persistence` delegation。所有 PostgreSQL 查询、权限过滤、事务与 receipt 仍由 Admin 的 typed Drizzle Repository 执行。

Dream 内部 dispatcher 新增服务器对象参数：`AdminWorkflowResolution`、`AdminAgentTurnPersistence` 与 `AdminDeckChatContextResolution`。这些对象不进入浏览器 DTO、SSE、CLI 环境、workspace 或日志。Service 不接受 actor header、任意用户 ID 或数据库连接作为替代。

## 保持不变的业务行为

- Guidance 写入成功后仍返回 202；exact replay 不重复 dispatch；owner 或 Runtime 调度失败返回 `dispatched=false`。
- Runtime 仍在 Dream 执行，使用同一 ThreadFactory、Runner、EventBus、SSE、resume/cancel 和 auto-repair continuation。
- Admin 数据不可用时明确失败，不回退 Dream PostgreSQL。
- 共享文件系统、workspace freeze/repair、manifest 校验、临时目录和权限边界不变。
- resource-policy LKG 和 admission/lease 顺序不变；Agent turn 不新增资源策略远程查询。

## 正常流程、失败与状态转换

1. Dream 使用当前 OAuth actor 调用 Admin Guidance submit；Admin 在一个 ORM/UOW 事务内完成权限、幂等与消息持久化。
2. replay 结果没有 dispatch，Dream 直接返回 `replayed=true, dispatched=false`。
3. 新 dispatch 以其 Thread 解析 Workflow context；必须得到同一 Run、Deck 与 Voice。
4. Dream 为该 actor/Thread/Run 创建并绑定现有可续期 `server-persistence` owner，再读取同一 Deck/Voice snapshot。
5. Thread 空闲时 dispatcher 把三个服务器对象注入 `ClaudeAgentRunRequest`；ThreadFactory 在原 admission 后启动 owner，并在原 Phase4 关闭。
6. Thread 已运行时不启动第二 turn，立即关闭未使用 owner，保留持久化 Guidance，返回 `dispatched=false`。
7. Workflow、Run、Deck、Voice、scope、capability、DTO 或 delegation 不匹配时关闭已创建资源并返回 `dispatched=false`；不撤销已提交消息，不重发写请求。
8. Service 收到缺失或错误 owner 的新 turn 时在数据库相关动作前失败关闭。Reconnect 只订阅已有 EventBus，不进入该状态机。

## 修改文件与影响范围

- 生产：`backend/routers/story_workspace.py`、`backend/services/story_workspace/guidance_service.py`、`backend/claude_agent/service.py`。
- 测试：Guidance route/dispatcher、Claude Agent service/Admin workflow owner tests；使用真实 DTO 和 fake Admin transport，不复制状态机。
- 文档：相关 `.folder.md`、`docs/design/claude-agent/claude-agent-service-design.md`、`claude-agent-context-assembly.md`、`docs/architecture/项目架构设计说明.md` 与本阶段文件。
- Admin：只核验当前 operation registry/hash 和既有 DTO/ORM测试，不改 schema/migration。

## 验收标准、验证命令与风险

- Guidance route：新写成功后 exact Workflow/Deck/owner 注入；replay 不创建 owner；running/owner失败均保持 202 和 `dispatched=false`；资源按所有权关闭。
- Service：新 turn 的 Thread、Session、plugin metadata、managed MCP scope、Deck prompt、user/assistant message只能经 Admin owner；AST 中没有 `database`、SQL 或 PostgreSQL fallback。
- 执行 focused pytest、相关 Story/Claude Agent 回归、`python -m compileall`、source-only AST scan、Markdown引用检查与两仓 `git diff --check`。
- 风险集中在已提交 Guidance 后的资源泄漏、错误 Run/Deck snapshot、Thread 正在运行时多发 turn、测试 fake 依赖旧数据库分支。通过精确 DTO 二次比对、owner close 边界和 provider-free断言控制。

## 阶段结果

本阶段实现与设计评审通过：

- `ClaudeAgentService`删除`database` import、1个SQL literal、7个旧helper调用和2个transaction/connection调用；Thread/SDK Session、user/assistant消息、Deck prompt、workspace plugin与managed MCP scope均只接受已绑定的Admin owner/provider。
- Guidance在Registry115写入确认后，以同一OAuth actor解析严格Workflow/Deck DTO并创建现有`AdminTurnPersistence`。replay不创建owner；running Thread返回`dispatched=false`；路由交接前失败、dispatcher构造失败、拒绝排队与turn结束均按单一责任关闭owner。
- Chat、Reflections、launch、Registry121 confirmation与Registry115 Guidance全部在进入ThreadFactory前携带Workflow、Deck和适用Run绑定的Admin owner。Runner、admission/lease、ThreadFactory、EventBus、SSE、resume/cancel、资源LKG、共享文件系统和`.claude-tmp`未改变。
- Admin未新增接口、schema或migration。两仓`admin-dream-operation-contracts.json`字节一致，SHA-256均为`a6643288d4ab6c75988642bcd0f8088b3de43803ec6863a98bc79f1d0e04468f`。

实际验证：

| 工作目录 | 命令/检查 | 退出码 | 结果 |
|---|---|---:|---|
| `backend/` | related 15-file pytest slice（含完整Dream Agent acceptance） | 0 | 293 passed，32 subtests passed |
| `backend/` | `pytest -q tests/test_claude_agent_thread_factory.py` | 0 | 66 passed |
| `backend/` | four corrected S04/S13/S14 acceptance cases | 0 | 4 passed |
| `backend/` | `python -m compileall -q`（本阶段生产与测试文件） | 0 | 无编译错误 |
| Dream root | source-only Python AST scanner | 0 | 553 modules；46 production SQL modules；406 SQL literals；22 DB import modules；39 legacy calls；345 transaction calls；36 Admin consumer modules；152 operations；`parse_errors=[]` |
| Dream root | 13-file Markdown link/inventory checker | 0 | `missing_links=[]`，stage inventory PASS |
| Dream root | contract `cmp` + SHA-256 | 0 | Dream/Admin registry相同 |
| Dream root | `git diff --check` | 0 | 无空白错误 |
| `backend/` | full `pytest -q tests`（补齐pytest/pytest-asyncio harness后） | 1 | 3715 passed，734 subtests passed，39 skipped，28 failed；本阶段相关失败为0 |

全量剩余28项由既有独立范围组成：10项旧router database/auth fixture尚未切换typed Admin seam，4项本机Runtime manifest版本资格不匹配，8项Product BFF旧合同，6项worktree未提供的`vendor/drama-forge`真实fixture。它们不恢复Dream数据库回退；后续阶段继续修正可复用fixture与相应实现/环境。真实Google、正常本机账号与真实模型业务验收尚未执行，不能据此宣称跨项目任务完成。
