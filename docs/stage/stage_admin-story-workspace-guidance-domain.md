<!-- [Input] Registry114 baseline, current Dream guidance SQL/service/tests, Admin Workflow/Chat DTO and Drizzle repositories. -->
<!-- [Output] Registry115 Story guidance persistence migration plan and verifiable acceptance record. -->
<!-- [Pos] Cross-project phase plan; Admin owns data transaction, Dream owns same-thread Runtime dispatch. -->
<!-- [Sync] 2026-09-15: plan the Story Workspace guidance DTO/ORM boundary before implementation. -->

# Story Workspace Guidance 数据访问迁移

## Optimized Prompt

You are an Expert Prompt Architect and senior Next.js, Better Auth, Python, PostgreSQL and Drizzle engineer. Implement one bounded cross-project refactor from the verified Registry114 baseline: move the public Story Workspace guidance command's PostgreSQL reads, ownership checks, idempotency decision and `chat_message` persistence from Dream into one Admin Registry115 business operation. Use strict Zod DTOs in Admin, strict Pydantic DTOs in Dream, typed Drizzle repositories and the existing Admin caller-owned transaction/receipt mechanism. The operation input contains only the run id, guidance kind, optional text/step id and idempotency key; derive the canonical actor from OAuth and derive Workspace, Thread, message identity, request id, fingerprint, parts and metadata inside Admin. Lock and validate the owned Workflow Run, owned Workspace and source Thread; accept only `confirmed` or `failed`; insert the immutable guidance user message once; return an exact replay without reordering the Thread; reject a different payload under the same message identity. Return a strict persisted-result DTO and, only for a newly committed command or original-receipt recovery, a validated dispatch envelope for Dream. Dream must keep the same-thread Agent Runtime dispatcher, 202 response fields, no-mid-turn behavior and best-effort dispatch failure isolation. Unknown write results may consult only the original Admin receipt and must never resend blindly or fall back to PostgreSQL. Update operation hashes, capability/registry totals, folder/file headers, architecture and migration inventories. Add provider-free DTO/route tests, Admin repository/service/receipt tests, a named isolated PostgreSQL contract that proves ACL and transaction behavior, and an updated source-only database closure scan. Preserve Runner, ThreadFactory, EventBus, SSE, turn/resume/cancel, resource policy LKG, shared filesystem and `CLAUDE_CODE_TMPDIR` semantics. Do not change Drizzle schema or migrations unless a verified missing capability requires it.

Optional Enhancers: run the broader Story suite after focused checks and classify legacy harness failures without weakening production authentication or restoring Dream database imports.

USER REQUIREMENT: Continue the Admin-auth/data refactor; database access must become DTO/ORM business APIs while Dream retains product orchestration and Runtime behavior.

## 目标与已有证据

- Registry114 已由 Admin `9e14b7e` 和 Dream `716b7810` 提交，11 个 Story catalog 路由不再直连 PostgreSQL。
- 最新只读 AST 清单仍在 `backend/services/story_workspace/guidance_service.py` 发现 2 个 SQL literal、1 个 `database` import 和 1 个 legacy helper；公开入口是 `POST /api/story-workspace/runs/{workflow_run_id}/guidance`。
- 当前 Guidance 只允许 `confirmed`、`failed` Run，使用 `guide_{idempotency_key}` 的不可变消息身份；相同 payload 回放返回 202 且不重复投递，不同 payload 返回 `IDEMPOTENCY_CONFLICT`。
- Admin 已有 Workflow Run、Chat Thread/Message Drizzle schema、严格 DTO、canonical JSON、统一 transaction、operation receipt 与 identity/unified capability，可复用而不新增表。

## 项目责任、依赖与读取范围

| 项目 | 责任 | 依赖 |
|---|---|---|
| Admin | `story-workspace-guidance.submit` DTO、Service、typed Repository、Registry115、receipt、ACL/事务验证 | Registry114、Workflow Run 与 Chat Thread schema、OAuth canonical principal |
| Dream | 严格 Pydantic consumer、公开 route application service 替换、同线程 dispatch、unknown receipt 恢复 | Admin Registry115 发布的 exact operation hash 与 identity/unified capability |
| 协调 | 契约 JSON、架构/清单、source-only scan、命令回执 | 两侧实现及确定性验证均完成后才更新阶段结果 |

本阶段读取 Admin `operationRegistry`、`receiptHandler`、Workflow/Chat DTO/Repository/Service 和 Drizzle schema；读取 Dream guidance service、Story workflow application、公开路由、contracts、相关测试与目录规则。

## 接口、数据库与配置变化

`story-workspace-guidance.submit` 是 OAuth `dream:write` 操作。输入为 `workflow_run_id`、`kind`、`text`、`step_id`、`idempotency_key`；不得接收 actor、Workspace、Thread、message id、SQL、表名、事务或 Runtime selector。Admin 输出公开持久化结果及内部 dispatch DTO；Dream public response只保留既有 `message_id`、`story_workspace_run_id`、`review_action=guide`、`status=accepted`、`replayed`、`dispatched` 与 `request_id`。

Admin 在一个 UOW 内锁定并验证当前主体拥有的 Run、Workspace 和 source Thread，检查 Run status，生成 fingerprint/parts/metadata，执行 `ON CONFLICT DO NOTHING` 后做 canonical exact replay 比较；新写入才推进 Thread `updated_at`。同 key 不同内容为 409；缺失或越权统一为既有业务错误。无需 migration 或新配置。Dream Admin 不可用、超时、capability/hash 缺失时返回明确业务失败，不回退数据库。

## 保持不变的行为

- Dream 继续构造并运行同一个 `ClaudeAgentRunRequest`，保留当前 ThreadFactory、SSE、EventBus、resume 与“正在运行时不做 mid-turn 注入”的行为。
- Guidance 已提交但 Runtime dispatch 失败时仍返回 202、`dispatched=false`；重放不重复投递。
- Run 状态集合、消息 text/metadata 业务语义、资源策略 LKG、共享文件系统和临时目录协议不变。

## 正常、失败与状态转换

1. Dream 从 OAuth 得到当前主体并提交严格 DTO；Admin 校验 capability/hash/scope。
2. Admin 锁定 owned Run/Workspace/Thread；非 `confirmed|failed` 返回 `WORKFLOW_RUN_NOT_GUIDABLE`。
3. 无同 identity 时写入 guidance message、触碰 Thread 时间并提交 receipt，输出 `replayed=false` 与 dispatch。
4. exact identity/payload 回放输出 `replayed=true`、dispatch 为 null；identity 冲突返回 409。
5. Dream 收到新 dispatch 后 best-effort 启动同线程 turn；运行中或异常只影响 `dispatched`，不撤销已提交消息。
6. Admin 响应未知时 Dream 只查询原 request receipt；完整 committed DTO 可恢复，缺失/无效保持 unknown，禁止重发写入。

## 修改范围

Admin 新增 Guidance DTO/Repository/Service/handler/tests/隔离脚本，注册 operation 和 receipt，并同步 `app/lib/dream/.folder.md`、架构与验证文档。Dream 新增 Guidance Admin consumer/test，修改 `story_workflow_application.py` 与旧 guidance service 使生产路径无 DB，更新相关 route tests、folder docs、架构/清单与 scan。若旧 Guidance 测试依赖 SQLite，只把它改为 production DTO/dispatcher 合同，不建立第二套业务实现。

## 验收、命令与风险

- Admin：focused Vitest、`pnpm exec tsc --noEmit`、`pnpm lint`、`pnpm test:run`、`pnpm build`、具名隔离 PostgreSQL contract；核验受限 executor 仅有目标表权限且不能读取 `users`。
- Dream：Guidance DTO/route/dispatcher/provider-free tests、相关 Story 回归、`compileall`、source-only scanner；静态 AST 证明 Guidance 生产模块不再导入/调用 `database`。
- 风险：canonical JSON/fingerprint 跨语言漂移、回放错误触碰 Thread 顺序、未知响应重复 dispatch、旧测试把 SQLite helper 当生产合同。通过 Admin 单点生成、exact DTO/receipt、new-only dispatch 与 parity fixture 控制。

## 阶段结果

Admin实现已提交为`a1912ec`；Dream实现由本次提交承载。operation SHA为`a061ed38d2ca10073bbb7fd078e679f072f0cbd4ff1ce900792fbf8725223727`，Registry114 prefix SHA保持`dc80b77410aac58528dde77578154d9848d9dfc3bf55de4a35c8c315a81af704`，完整Registry115 SHA为`58ab3cd933165dca7d6ae2d6eb50f46ff8f148e8e7eaf3dd5e46ceab1ad2ba9b`。Admin isolated PostgreSQL应用全部62个migration并由restricted role通过5/5 immutable/replay/concurrency/permission/ACL场景，临时集群已清理。Admin focused 109项通过；全量244 files / 1928 passed / 36 configured skips，TypeScript、lint与Next production build均exit 0。Dream compileall通过，Guidance/route/request-auth及相邻Story聚焦55项与10个subtests通过。两仓变更Markdown共检查390个本地引用，missing为0。

Registry115 source-only scanner读取545个Python模块，得到78个production entry、49个SQL模块、452个SQL literal、27个driver/import模块、50个legacy helper、392个connection/transaction call、29个Admin consumer模块、133个operation name和0 parse error。相对Registry114减少1个production entry、1个SQL模块、2个SQL literal、1个driver/import模块和2个legacy helper；Guidance production模块已经没有Dream database符号。正常本机账户、真实Google和真实模型/Runtime完整业务验收未执行，Registry115技术验证不能替代这些验收，跨项目goal继续active。
