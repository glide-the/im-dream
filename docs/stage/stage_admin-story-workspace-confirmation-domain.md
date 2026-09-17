<!-- [Input] Registry115 baseline, Dream confirmation persistence/coordinator, Admin confirmation guard and Workflow ORM. -->
<!-- [Output] Registry120 confirmation DTO/ORM migration plan and acceptance boundary. -->
<!-- [Pos] Cross-project phase plan; Admin owns durable state, Dream owns filesystem validation and Runtime delivery. -->
<!-- [Sync] 2026-09-16: implement and verify the Registry120 DTO/ORM confirmation state machine. -->

# Story Workspace Confirmation 数据访问迁移

## Optimized Prompt

You are an Expert Prompt Architect and senior Next.js, Better Auth, Python, PostgreSQL and Drizzle engineer. Starting from verified Registry115, migrate the complete Story Workspace Dream-confirmation database state machine from Dream to Admin as five closed business operations: OAuth `story-workspace-confirmation.submit` and `story-workspace-confirmation.fact`, plus service-only `story-workspace-confirmation.claim`, `story-workspace-confirmation.lease` and `story-workspace-confirmation.ack`. Define strict Zod DTOs in Admin and byte-compatible strict Pydantic DTOs in Dream. Implement all PostgreSQL reads, ownership checks, row locks, status transitions, claim compare-and-set, message persistence, receipt and audit work through typed Drizzle repositories in Admin; no operation may accept SQL, table names, arbitrary actor IDs or generic CRUD fields. Add the exact `story-confirmation:dispatch` service scope and a required Admin-owned lease policy. Dream must validate the current shared-filesystem projection twice around the network submission, retain the original command and visible Chat control envelope, and keep the existing same-thread Runtime dispatcher, retry/backoff, lease heartbeat and at-least-once delivery behavior. The Admin submit operation derives the canonical actor, source Thread, deterministic message ID, command fingerprint, metadata, request identity and Run lifecycle effects; exact replay returns the original result, while a changed command or second confirmation for the same actor/Run conflicts. The claim operation atomically selects a requested or oldest eligible pending/expired item, recovers the same claim ID after an unknown response, advances a historical eligible Run to `confirmed` before returning work and refreshes the server-owned instruction envelope. Lease renews only the exact live claim. Ack succeeds only for the exact claim after the Run is confirmed/completed and records the irreversible claim hash. The fact read derives scope from the current OAuth principal and owned Run. Unknown OAuth submit results use only the original receipt; background operations are exact compare-and-set commands whose same-ID retry and subsequent reconciliation recover uncertain outcomes. Update registry hashes, capabilities, service configuration, architecture/inventory docs and file headers. Add provider-free DTO/client/coordinator tests, Admin unit/handler/receipt tests, a named isolated PostgreSQL contract proving concurrency and ACL, and a new source-only closure scan. Preserve Runner, ThreadFactory, EventBus, SSE, turn/resume/cancel, resource-policy LKG, shared-filesystem paths, symlink rules, `0700` and `CLAUDE_CODE_TMPDIR`.

Optional Enhancers: after focused validation, run the broader Story Workspace and both-repository deterministic suites; classify missing local credentials or live services as real-acceptance prerequisites without weakening production code.

USER REQUIREMENT: Continue the cross-project refactor. Convert database access to DTO/ORM business interfaces while Admin owns authentication and data access and Dream retains product orchestration, Runtime and shared filesystem behavior.

## 目标与已有证据

- Admin `a1912ec` 与 Dream `c568524c` 已完成 Registry115 Guidance；Admin 工作区干净，Dream 的其他未提交插件改动继续受保护。
- `dream_confirmation_service.py` 当前包含 15 个 SQL literal、1 个 PostgreSQL driver import 和 34 个 connection/transaction call，覆盖提交、事实读取、认领、租约、确认回执和启动恢复。
- Admin 已有 `confirmationGuard`、Workflow Run/Transition、Chat Message/Thread schema、canonical JSON、统一 UOW、operation receipt 与 Drizzle repositories，可复用现有表而无需 DDL。
- Dream 的公开确认命令与 `.dream` 文件投影属于共享文件系统域；Run/Thread/Message、生命周期和持久化工作项属于 Admin 数据域。

## 项目、责任与依赖

| 项目 | 责任 | 依赖 |
|---|---|---|
| Admin | 五项严格 DTO、Handler、Service、typed Repository、Registry120、OAuth receipt、后台 scope/lease policy、事务与 ACL | Registry115、Better Auth canonical principal、Workflow/Chat schema、现有 confirmation guard |
| Dream | Pydantic consumer、OAuth submit/fact、服务身份 claim/lease/ack、文件投影双读、Coordinator 与 Runtime 调度 | Admin Registry120 完整 operation hash、`story-confirmation:dispatch` 配置与 capability |
| 协调 | 契约 JSON、架构/迁移清单、source-only scan、确定性和隔离回执 | 两侧代码、文档与必需验证均完成后更新阶段结果 |

本阶段读取 Dream confirmation service/application/router/contracts/lifecycle/tests、Admin operation registry/receipt/auth/background handler/Workflow与Chat repositories、两仓目录规则和现行架构文档。官方协议不发生变化；本阶段不引入新的 OAuth/Device Flow API。

## 接口、数据库与配置

| Operation | Audience | Input | Output与事务 |
|---|---|---|---|
| `story-workspace-confirmation.submit` | OAuth `dream:write` | 完整 confirmation command；不含 actor、message ID、状态或表字段 | 校验 owned Run/Workspace/source Thread，在一个 UOW 中保存不可变 user message、触碰 Thread、推进正常 `pending_review→confirmed` 并提交 receipt/audit；返回 accepted 与 pending dispatch |
| `story-workspace-confirmation.fact` | OAuth `dream:read` | `workflow_run_id` | 从 owned Run 派生 Thread，返回 accepted/dispatched；只读、不领用 |
| `story-workspace-confirmation.claim` | service `story-confirmation:dispatch` | nullable target `message_id` 与随机 `claim_id` | 锁定目标或最早 eligible 行；同 claim 重读恢复，pending/过期 lease CAS 到 dispatching；必要时按原合法边推进历史 Run 至 confirmed |
| `story-workspace-confirmation.lease` | service `story-confirmation:dispatch` | `message_id`、`claim_id`、nullable `duration_seconds` | 只续期当前claim；null使用Admin策略，短租约支持backoff/立即释放，任何值都不能超过Admin上限；不同claim无写入 |
| `story-workspace-confirmation.ack` | service `story-confirmation:dispatch` | `message_id`、`claim_id` | 仅 confirmed/completed Run 且 exact claim 可写 dispatched；重复同 claim 通过 hash 幂等恢复 |

Admin 新增必填 `DREAM_CONFIRMATION_DISPATCH_LEASE_SECONDS`，校验为正安全整数并由 Admin 计算 wall-clock deadline。`DREAM_DATA_SERVICE_CLIENTS[*].backgroundScopes` 增加 exact `story-confirmation:dispatch` 枚举；Dream不接收数据库凭据；Admin拥有租约上限和默认值，Dream只能为backoff或立即释放请求不超过上限的短租约。无 schema/migration 变化。

## 保持不变的业务行为

- 浏览器仍提交现有 camelCase command，返回现有 202 `StoryWorkspaceDreamConfirmationAccepted`。
- 文件根、规范化、符号链接限制、base revision 校验和三阶段实体/编辑校验仍由 Dream 执行；Agent 继续以 command 中 base revision 做文件 CAS。
- confirmation 仍是可见普通 user `chat_message`；消息 ID、command fingerprint、parts 和 metadata 保持跨语言字节语义。
- Coordinator 仍以 at-least-once 方式排队同 Thread turn，保留启动扫描、指数退避、lease heartbeat、取消/停止与完成后 ack。
- Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel、资源策略 LKG、共享文件系统和临时目录协议不变。

## 正常流程、失败和状态转换

1. Dream 用当前用户 OAuth 获取 owned Run/Thread，并从共享文件系统读取、严格验证投影。
2. Dream 再读一次同一投影后调用 submit；Admin 重新验证 actor/Run/Workspace/Thread，生成 identity/envelope，原子保存并返回 pending dispatch。
3. Dream Coordinator 以服务身份 claim；Admin 只把 pending 或已过期 dispatching 变成 exact claim，返回当前 parts/metadata/lease。
4. Dream 在本进程排队同 Thread Runtime；heartbeat 仅续期该 claim。Runtime 完成后 ack，Admin 校验生命周期与 claim 后写 dispatched。
5. submit exact replay返回原 request/result；不同 command、第二个确认或伪造 Thread/actor 返回 409。claim unknown 用同 claim ID恢复；ack重复同 claim恢复；lease/服务不可用保留当前租约并由后续 reconcile 接管。
6. Admin unavailable、capability/hash/scope缺失、DTO非法、Run越权或状态非法时 fail closed；Dream 不回退 PostgreSQL。文件在 submit 前漂移返回既有 `CONFIG_VERSION_DRIFT`/`OUTPUT_CONTRACT_INVALID`，不会产生数据库写入。

## 修改范围

Admin 新增 confirmation DTO/Repository/Service/Handler/tests与隔离 runner，扩展 auth config、shared route、receipt、registry及环境/架构文档。Dream 新增 confirmation Admin DTO/client/tests，重构 confirmation service/Coordinator与 application wiring，移除该 service 的 psycopg/SQL/connection factory，更新 request auth、配置说明、目录文档、迁移清单和 scan。共享 dirty 文档只选择性暂存本阶段行，不暂存其他任务改动。

## 验收标准、命令和风险

- Admin：focused Vitest、`pnpm exec tsc --noEmit`、`pnpm lint`、`pnpm test:run`、`pnpm build`、具名隔离 PostgreSQL contract；证明 immutable replay、second-confirmation conflict、claim race、expired reclaim、lease/ack claim ownership、Run transition/history、restricted executor ACL 和 `users` deny。
- Dream：provider-free Pydantic parity、public route、projection double-read、Coordinator claim/renew/ack/reconcile、Chat confirmation guard相邻回归、`compileall`、Story suite和 source-only scanner。
- 风险：Python/Node canonical JSON 漂移；旧 running confirmation恢复时生命周期事件顺序；HTTP unknown result导致重复 Agent turn；lease wall clock漂移；共享文件与数据库不是同一 durability domain。通过 Admin 单点生成、raw canonical fixture、exact claim ID、CAS/ack hash、过期接管和 Agent文件CAS控制。
- 本阶段技术验证不能替代真实 Google、真实本机服务和真实模型验收；这些继续保留在总体验收 gate。
## 实现与评审结果

- Admin新增五项Registry120 operation、封闭Zod DTO、Service、typed Drizzle Repository、OAuth receipt与后台scope检查。Repository不接受调用方SQL/表列；固定advisory lock和PostgreSQL clock表达式只服务于幂等与租约。`fact`只读且不申请更新锁。
- Dream新增五项严格Pydantic DTO consumer，生产confirmation service不再导入数据库driver、连接池或SQL。公开提交用既有Admin Run DTO校验actor/Thread，保持两次共享文件系统投影检查；Coordinator仅通过Admin claim/lease/ack持久化状态。
- 并发评审修正为：只有首次业务提交返回即时dispatch，业务重放返回null并交给持久reconciler，防止并发HTTP结果向Runtime重复注入。Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel和文件权限协议未改变。
- 数据结构已由Admin Drizzle现有Run/Transition/Thread/Message/receipt表覆盖；本阶段没有DDL或migration。

## 已取得验收证据

| 验证 | 工作目录 | 结果 |
|---|---|---|
| `node scripts/run-story-workspace-confirmation-contract.mjs` | Admin worktree | 通过；具名隔离数据库执行4项PostgreSQL合同，验证三段Run transition、消息/receipt原子提交、claim/lease/ack/fact、并发一新一重放、越权拒绝、restricted role无权读取`users.email/password_hash`；数据库及角色已清理 |
| `/Users/dmeck/project/ink-dream-memory/.venv/bin/python -m pytest -q backend/tests/test_story_workspace_dream_api.py backend/tests/test_story_workspace_dream_confirmation.py` | Dream worktree | 通过；38 tests与23 subtests，覆盖公开202入口、DTO/hash/capability、投影双读、current actor、unknown receipt、claim/lease/ack和Runtime调度 |
| `python -m py_compile ...` | Dream worktree | 通过；本阶段生产与测试Python文件无语法错误 |
| `pnpm exec tsc --noEmit` | Admin worktree | 通过；Registry120 service overload、DTO、Repository与handler类型闭合 |
| `pnpm exec vitest run app/lib/dream/*Registration.test.ts app/lib/dream/storyWorkspaceConfirmation*.test.ts` | Admin worktree | 通过；19 files / 108 tests，隔离PG 4项在普通lane按设计skip并由独立runner执行 |
| `git diff/list files | xargs pnpm exec eslint` | Admin worktree | 通过；本阶段全部TypeScript文件lint无错误 |
| `python -m pytest -q tests/test_story_workspace*.py` | Dream `backend/` | 通过；718 tests、180 subtests，4项环境条件skip；测试期间只临时映射源仓库已有vendor fixture并已清理 |
| confirmation生产source scan + `py_compile` | Dream worktree | 通过；旧confirmation helper、SQL literal、psycopg、`database.get_db`与`get_db(`匹配均为0 |
| Registry120 Markdown relative-link check / `git diff --check` | 两个worktree | 通过；Admin 5个、Dream 10个受影响Markdown文件引用有效，补丁无空白错误 |

上述均为确定性或隔离技术验证，不替代本机真实Dream/Admin/Gateway/PostgreSQL账户与模型验收；总任务其它数据库入口仍未关闭。

扩大Story suite首次从仓库根运行时有20项harness失败：旧launch测试覆盖了已替换的`get_current_user`而非当前`_story_workflow_current_user`，一个测试依赖`backend/`相对cwd，worktree也未检出git忽略的vendor fixture。更新launch测试依赖后单文件28 tests/18 subtests通过；再从`backend/`运行并临时只读映射源仓库vendor，完整Story suite通过。该过程未修改产品认证顺序或vendor内容。Admin第一次组合lint命令因zsh未拆分变量把文件列表当成一个路径而退出2；改用`xargs`后退出0，测试本身在该次已全部通过。
