<!-- [Input] Registry129 baseline, current Dream launch Runtime provisioning SQL and frozen Run replay semantics. -->
<!-- [Output] Registry130-132 DTO/ORM design, implementation scope, review and verification record. -->
<!-- [Pos] Cross-project implementation stage; launch business UOW remains separate while Runtime metadata moves to Admin. -->
<!-- [Sync] 2026-09-16: record implemented launch Runtime ownership and isolated validation. -->

# Dream Launch Runtime 数据归属迁移

## Optimized Prompt:

You are the Admin/Dream migration engineer removing
`DreamRuntimeProvisioningService` from the production Story Workspace launch
path. Preserve Registry129 byte-for-byte and append three strict operations:
`dream-launch.runtime-scope`, `dream-launch.runtime-plan` and
`dream-launch.runtime-prepare`. Build Zod DTOs, an Admin application Service,
typed Drizzle Repository, handlers/registration/receipts, matching strict
Pydantic consumers, request-scoped Dream orchestration and original-request
receipt recovery.

The scope operation must derive the canonical user from OAuth, verify the
enabled owned Deck, default Workspace and optional enabled Voice, and return
only the bound identifiers. The plan input must be one strict mode-validated
object whose cross-field validator rejects invalid combinations. `current`
mode derives the active explicit Deck Plugin binding and the
single server-policy Runtime target. `replay` mode accepts only the exact
Workflow Run and Thread identifiers in addition to Deck/Workspace/Voice;
Admin must load the actor-owned Run and derive its frozen binding and Runtime
lock. Reject caller-supplied actor IDs, plugin selection, lock IDs, paths,
placement, policy, readiness, SQL, table or column selectors.

The plan output must contain the immutable binding projection and one local
verification candidate without `artifact_path` or `cache_ref`. Dream derives
the local path from the existing shared artifact store, verifies digest,
manifest and Claude CLI compatibility with the Registry129 verifier, then
sends only exact observed evidence to `runtime-prepare`. Admin must repeat all
ownership, binding/Run and lock checks in the receipt transaction, reject
TOCTOU changes, and idempotently materialize the server-owned Runtime
placement. Current mode must ensure the Workspace Deck Plugin installation;
replay mode must preserve the Run's frozen binding and never switch to a newer
active binding.

Inject the Admin consumer and OAuth access token at the authenticated launch
request boundary. The launch application, Agent Runtime, ThreadFactory,
EventBus, SSE, turn/resume/cancel and shared workspace operations stay in
Dream. Remove launch imports/calls for `PluginInstallService`,
`InstallationService`, `BindingService`, `SelectionValidationService`, raw
Runtime placement persistence and `database.get_db` from the Runtime
provisioning component only. Do not claim the rest of launch persistence has
moved in this phase. Missing Admin capability, unavailable ready installation,
invalid local artifact, stale current binding, wrong frozen Run or unknown
write outcome must fail closed without Dream PostgreSQL fallback.

Add provider-free DTO/Service/handler/client/coordinator tests, current and
replay ordering tests, an AST closure fence, exact Registry129 prefix/mirror
checks, and an isolated restricted-role PostgreSQL test for scope denial,
Voice denial, current binding, replay frozen binding, evidence mismatch,
concurrency, materialization idempotency and Workspace installation. Update
affected file headers, folder contracts and architecture documents. Run
focused tests, typecheck, lint, isolated PostgreSQL, build, Dream full tests,
Markdown link inventory and diff checks. Protect every unrelated dirty Dream
file and stage mixed folder indexes through an index-only patch.

USER REQUIREMENT:
继续完成 Admin 统一数据库访问与 Dream 全生产数据库访问迁移；数据库接口必须遵从 DTO/ORM 设计，并保持 Dream Runtime、SSE 和共享文件系统语义。

## 背景与问题

Registry127-129 已关闭公开 `agent-type` Router 的数据库访问，但 Story Workspace
launch 的 `DreamRuntimeProvisioningService` 仍直接查询 Deck/Workspace/Voice、binding、
release lock、Claude installation、materialization 与 Workspace installation，并在 Dream
内调用旧安装和选择服务。新启动要求当前显式选择；幂等重放要求使用 Run 已冻结的
binding 和 Runtime lock，不能因为当前发布版本变化而改写历史 Run。

## 目标与边界

- Admin 负责 launch Runtime scope、binding/Run/lock 派生、Runtime 元数据和事务。
- Dream 负责 authenticated request 编排、本地共享 artifact 字节与 CLI 校验。
- 只移除 launch Runtime provisioning SQL；source、Preflight、Run 创建和 dispatch 的剩余
  Dream 数据访问继续列在迁移清单中。
- 不改 schema，不执行正常业务数据库的 migration 或破坏性验证。

## 概念与规则

- `current` plan 必须返回当前 active binding；没有显式选择时仍返回
  `WORKFLOW_SELECTION_REQUIRED`。
- `replay` plan 从 actor-owned Run 和 Thread 派生 frozen binding/lock；调用方只提交业务
  identity，不能提交期望 plugin/lock 作为选择器。
- plan 不返回服务器路径。Dream 用 artifact store 推导路径，prepare 只接收不可变
  evidence。
- prepare 在一个 Admin receipt transaction 中重复授权和目标解析；未知提交只读原
  request receipt，不重发写入。
- ready Claude installation 不存在时返回 `RUNTIME_PLUGIN_NOT_READY`，不得在 Dream HTTP
  请求中恢复 SQL 或隐式 runtime install。

## 接口与状态

| Operation | Kind | 输入 | 输出/事务 |
|---|---|---|---|
| `dream-launch.runtime-scope` | read | Deck、Workspace、nullable Voice | OAuth owner/enable 检查与同 identity 回显 |
| `dream-launch.runtime-plan` | read | strict current/replay union | frozen binding + 无路径 Runtime candidate |
| `dream-launch.runtime-prepare` | write | 同 mode identity + plan revision + verified evidence | 重查 scope/Run/binding/lock；幂等 materialization，current mode确保 Workspace installation |

正常 current 流程为 scope → existing replay lookup → current plan → 本地验证 → prepare；
replay 流程为 scope → actor/idempotency lookup → replay plan → 本地验证 → prepare。scope
保持原先 Voice 拒绝发生在 replay/model resolution 之前。Admin 网络、能力或本地验证失败
均不创建 Preflight、Run 或 launch source。

## 验收与风险

- Registry129 prefix 和两仓 contract 镜像不变。
- `DreamRuntimeProvisioningService` 及其 launch 调用删除；对应调用链无 Dream SQL/ORM。
- Admin 数据代码只使用 strict DTO → Service → typed Drizzle Repository。
- current/replay、Voice denial、frozen lock、TOCTOU、receipt recovery 和本地验证失败均有
  确定性断言。
- Runtime、SSE、共享文件和 `CLAUDE_CODE_TMPDIR` 无改动。

主要风险是旧服务会在请求内安装缺失的 builtin plugin。新边界要求 Admin 元数据先就绪，
Dream launch 在缺失 ready installation 时返回明确业务失败。启动期 seed/install 仍是后续
迁移项；不能用 Dream 数据库 fallback 掩盖部署前置条件。

## 设计评审结论

评审通过后按原顺序实现。Admin 仍是唯一认证与数据库访问服务；三个 operation 没有引入新 Session、用户主体、队列或控制通道。current 与 replay 使用同一 DTO family，但 validator 强制 current 的 Run/Thread 为 null、replay 两者同时存在；Admin 根据 OAuth 主体执行权限过滤。plan 不公开路径，Dream 只验证本机共享 artifact。prepare 在原 receipt UOW 重新解析目标，写入 materialization，并只在 current 模式确保 Workspace installation。Run-frozen binding 可以处于 stale 状态，不会被当前 active revision 替换；当前部署策略无法支持冻结 lock 时明确失败。

评审中修正了两项实现细节：请求路由直接复用 `_admin_actor` 中已验证的 bearer，避免第二套身份传递；Dream 在任何 Admin 调用前结束遗留只读 transaction，并在 idempotent Run 查询后再次结束只读 transaction，避免跨 HTTP 持有 PostgreSQL transaction。未修改 Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel、共享文件系统路径、`.claude-tmp` 或资源策略。

## 实现与证据

- Admin Registry132 使用 strict Zod DTO、`runDeckPluginBindingOperation` Service 与 `DeckPluginBindingRepository` typed Drizzle 查询 Run、Preflight、binding、release、lock、installation 和 materialization。除固定 actor cast 与 database clock 外没有调用方 SQL。
- Dream `AdminDeckPluginBindingData` 使用同 hash strict Pydantic DTO 与 original-receipt unknown-write barrier；`AdminDreamLaunchRuntime` 只做 DTO 编排和本地 immutable verifier，不导入数据库库或调用 `execute/cursor/commit/rollback`。
- `DreamRuntimeProvisioningService`、`PluginInstallService`、`InstallationService`、`BindingService`、`SelectionValidationService` 和 local Runtime placement 已从生产 launch Runtime component 删除。其余 launch source、Preflight、Run、dispatch 和 failure persistence 继续作为后续清单项。
- Registry129 prefix SHA 保持 `686f0668c72ca6114d894392d2dd2a2fde228b87fa31a1b858fd1dd553663881`；Registry132 完整 SHA 为 `6e0149b3d3354d081564af21349f364cc092087d5aadce0d5164654a6c005bb2`。
- Admin provider-free Service/registration：18 tests passed；Admin TypeScript typecheck exit 0。
- Admin disposable PostgreSQL：63 migrations applied；restricted executor 8 tests passed；current prepare、stale-binding replay、CAS、ACL 和 cleanup 全部通过。
- Dream DTO/coordinator/launch：43 tests passed、1 个既有 SQLite 行锁场景跳过、18 subtests passed；AST fence 确认 Runtime coordinator 无数据库 client/call 且 provisioning class 不存在。

## 验证回执

| 工作目录 | 命令 | 结果 |
|---|---|---|
| Admin | `pnpm test:run` | exit 0；251 files passed、17 skipped；1965 tests passed、36 skipped |
| Admin | `pnpm exec tsc --noEmit` | exit 0 |
| Admin | focused ESLint | exit 0 |
| Admin | `pnpm build` | exit 0；Next.js 16.1.6 production build 完成 |
| Admin | `pnpm db:generate` | exit 0；118 tables；`No schema changes, nothing to migrate` |
| Admin | `node scripts/run-deck-plugin-binding-contract.mjs` | exit 0；63 migrations 后 restricted-role PostgreSQL contract 8 tests passed，隔离数据库已删除 |
| Dream | focused pytest：Registry132 DTO、Runtime coordinator、launch route | exit 0；43 passed、1 skipped、18 subtests passed |
| Dream | `PYTHONPATH=backend /Users/dmeck/project/ink-dream-memory/.venv/bin/python -m pytest -q backend/tests --tb=short` | exit 1；3719 passed、40 skipped、752 subtests passed；34 个失败名称与迁移前基线一致 |
| 两仓 | 受影响 Markdown 本地引用检查 | exit 0；13 documents、73 relative links、0 broken |
| 两仓 | `git diff --check` | exit 0 |

Dream 全量通过数相对 Registry129 阶段的 3713 增加为 3719，失败数、失败名称和
752 个 subtests 均未变化；本阶段没有新增失败。失败仍来自既有路由测试桩、Claude CLI
runtime manifest、vendor 剧集 fixture 和 Product BFF 测试配置，与 Registry130-132
Runtime DTO/ORM 迁移无关。
