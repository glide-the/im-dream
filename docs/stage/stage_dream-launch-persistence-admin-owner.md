<!-- [Input] Registry132 baseline and the remaining Dream launch source/Preflight/Run/dispatch/failure SQL call graph. -->
<!-- [Output] Prompt-Architect execution plan for closing the next atomic launch persistence boundary through Admin DTO/ORM operations. -->
<!-- [Pos] Cross-project implementation stage; Dream keeps Agent Runtime, streaming and shared filesystem behavior. -->
<!-- [Sync] 2026-09-16: start the post-Registry132 launch persistence closure phase. -->

# Dream Launch 持久化归属迁移

## Optimized Prompt:

You are the cross-project Admin/Dream migration engineer continuing from the
verified Registry132 baseline. Inspect the existing Admin operation registry,
strict Zod DTOs, Services, typed Drizzle Repositories, receipt handlers and
restricted-role PostgreSQL harnesses for Dream launch source creation,
Workflow Preflight, Workflow Run creation, dispatch claim/finalization and
terminal failure recording. Inspect the matching Dream strict Pydantic
consumers and the production Story Workspace launch call graph. Reuse every
already registered business operation whose authorization, idempotency,
transaction and error semantics match the current launch behavior; do not
append duplicate operations or bypass DTO/Service/ORM boundaries.

Select the smallest complete transaction boundary that removes the next set
of production Dream PostgreSQL calls without splitting an existing atomic
write across unrelated HTTP requests. Prefer an existing Admin launch
application operation when it already owns source Thread/message plus
Preflight/Run facts. If existing operations are component-level only, document
the ordering, unknown-commit recovery and consistency gap before deciding
whether one Admin application UOW is required. Caller inputs may contain only
OAuth-bound business identifiers, launch goal, idempotency key and immutable
evidence already produced by Admin. Reject caller-selected actor IDs, SQL,
tables, storage paths, lock state, internal status and permission decisions.

Implement any Admin gap as strict Zod DTO -> application Service -> typed
Drizzle Repository, with the OAuth principal providing the canonical user.
Preserve owner checks, enabled Deck/Voice checks, idempotency fingerprints,
frozen Run replay, Preflight token authority, row locking, CAS, dispatch lease,
duplicate request behavior and original-request receipt recovery. Non-idempotent
writes must never be blindly retried. Missing capability, timeout, permission
denial and unknown commit result must fail closed; Dream must not fall back to
PostgreSQL. Keep Admin Drizzle as the sole schema owner and introduce no schema
change unless the verified contract requires one.

In Dream, replace the selected SQL path with one request-scoped Admin client
and strict DTO coordinator. Keep Story Workspace page behavior, response DTOs,
Agent Runtime, Runner, ThreadFactory, EventBus, SSE, turn/resume/cancel,
dispatch task ownership, resource-policy LKG and shared filesystem operations
unchanged. Do not move Agent execution or local file writes to Admin. Preserve
the exact `CLAUDE_CODE_TMPDIR={AGENT_CWD}/{thread_id}/.claude-tmp`, `0700` and
symlink boundaries.

Update affected file headers, folder contracts, architecture documents,
capability/migration inventories and Mermaid flows. Add provider-free contract
tests, ordering/failure tests, AST closure fences and isolated restricted-role
PostgreSQL tests for authorization, idempotent replay, concurrent requests,
unknown commit recovery and transaction rollback. Run focused tests,
typecheck/lint, Admin full tests/build/db:generate, Dream full tests, Markdown
link inventory and diff checks. Stage only phase-owned files; preserve all
other dirty Dream worktree content. Commit and push both existing `codex/`
branches, then rescan the complete Dream production database inventory before
choosing the following phase.

USER REQUIREMENT:
继续跨项目重构；数据库改造成接口时必须遵从 DTO/ORM 设计，完成全部 Dream 生产数据库访问迁移并保持业务执行归属。

## 本轮计划

- 已有证据：Registry130-132 已把 launch Runtime scope、current/frozen
  binding/lock 与 metadata transaction 迁入 Admin；Admin 全量测试、构建、
  Drizzle no-change 和隔离 PostgreSQL contract 已通过。
- Admin 责任：核对并补齐 launch source、Preflight、Run、dispatch/failure 的
  业务 DTO、Service、typed Drizzle Repository、receipt 与 capability。
- Dream 责任：用统一 Admin consumer 替换选定生产 SQL，同时保留公开响应、
  Runtime、SSE、任务 registry 和共享文件系统。
- 依赖：Registry132、现有 launch/source/preflight/run/failure/dispatch operations、
  OAuth principal、original receipt 和 restricted executor ACL。
- 失败处理：Admin 不可用、超时、权限拒绝、capability 缺失、CAS 冲突与未知提交
  均返回稳定业务错误；写操作只查询原 request receipt，不重发。
- 验收：迁移清单对应入口没有 PostgreSQL import/call；事务、并发、幂等与 frozen
  replay 测试通过；两仓合同镜像一致；全量门禁无新增失败。

## 设计评审结论

- 既有 Registry75/77、Workflow Preflight、Workflow Run 与 Registry130-132 已覆盖各自事务，继续复用可避免增加重复 application API。
- 启动前唯一缺口是 actor-scoped idempotency lookup。新增 Registry133 `dream-launch-replay.lookup`，输入复用原 command 字段，输出只返回原 Run/Preflight/Thread/message identity。
- Admin 的严格 Zod DTO、Service、typed Drizzle Repository 负责 owner、enabled scope、source/fingerprint、Preflight input hash 与 Run source tuple。Dream 的严格 Pydantic consumer 只组合业务操作，不接收表列或 SQL selector。
- 新启动与 replay 保持原事务边界；未知写只读原 request receipt。Agent Runtime、任务 drain、EventBus/SSE、资源策略与共享文件均留在 Dream。
- 现有 schema 足够；不新增 migration。Registry132 prefix SHA 为 `6e0149b3d3354d081564af21349f364cc092087d5aadce0d5164654a6c005bb2`，Registry133 SHA 为 `951a3ee9d26354d0094dafec6233a13638a430672ddacd730cefc95f654b5ec3`。

## 实施结果

Admin 新增 replay lookup DTO/Repository/Service/Handler/Route 注册与测试，并生成 Registry133 合同镜像。Dream 将 launch endpoint、source、Preflight、Run、dispatch 与 failure recorder 接到同一 request-scoped Admin actor/client；replay 读取 frozen Preflight/Run，不生成占位 token，也不解析当前模型。`dream_launch_application_service.py`、`dream_launch_endpoint_service.py` 与 `dream_launch_infrastructure.py` 不含数据库 import、SQL、ORM、连接或 fallback。

| 验证 | 工作目录 | 结果 |
| --- | --- | --- |
| Admin focused Registry133/handler/registry | Admin worktree | 18 passed，exit 0 |
| Admin TypeScript | Admin worktree | `pnpm exec tsc --noEmit`，exit 0 |
| Admin restricted PostgreSQL contract | Admin worktree | 63 migrations，9 tests passed，executor ACL 生效，自有数据库清理，exit 0 |
| Admin full unit | Admin worktree | 1975 passed / 36 skipped，exit 0 |
| Admin lint / build / Drizzle generate | Admin worktree | 全部 exit 0；118 tables，`No schema changes` |
| Dream launch focused | Dream worktree | 75 passed，exit 0 |
| Dream related request/preflight/run/deck | Dream worktree | 247 passed，exit 0 |
| Dream full backend | Dream worktree | 3701 passed / 39 skipped / 34 baseline failures，exit 1；失败集合与阶段前记录一致，无 launch 新失败 |
| Contract mirror / compile / DB fence | 两 worktree | JSON 相同、Python compile exit 0、launch AST/关键字检查无数据库执行路径 |

全量 Dream 仍有 34 项既有测试债务，因此本阶段结论是 launch 技术迁移通过且无新增回归，不是整个跨项目任务完成。下一阶段必须重新运行全生产数据库候选扫描，选择下一个 DTO/ORM 领域闭包。
