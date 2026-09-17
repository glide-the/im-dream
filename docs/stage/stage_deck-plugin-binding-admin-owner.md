<!-- [Input] Registry121 baseline, current Deck binding routes/services and existing Admin compatibility DTO/ORM implementation. -->
<!-- [Output] Registry122-126 cross-project implementation plan and verifiable acceptance boundary. -->
<!-- [Pos] Executable phase plan for moving five public Deck Plugin binding operations to Admin. -->
<!-- [Sync] 2026-09-16: record Registry126 implementation and bounded validation evidence. -->

# Deck Plugin Binding 数据归属迁移

## Optimized Prompt:

You are the cross-project Admin/Dream migration engineer implementing the next
bounded production database closure after Registry121. Move the five public
Deck Plugin binding operations—current state, history, options, validation and
save—from Dream PostgreSQL calls into Admin. Reuse Admin's existing strict
`deck-plugin-compatibility.check` DTO, compatibility evaluator and typed Drizzle
repository. Add closed business DTOs and a binding-specific Admin Repository,
Service and Handler; append operations without changing the frozen Registry121
prefix; publish matching strict Pydantic contracts in Dream; and replace the
five FastAPI route paths with the shared Admin client and verified OAuth bearer.

Preserve the original owner checks, requested/default Workspace binding,
selection failure order, response fields, append-only binding history,
optimistic `expected_binding_revision`, same-selection idempotency, active-row
replacement, Deck draft revision advance, error status and public response
shape. The save operation must execute permission re-check, compatibility
validation, stale update, insert and draft advance in one Admin transaction.
Do not accept actor IDs, SQL, table names, readiness flags, filesystem paths or
runtime grants in the request DTO. Do not retry an unknown write; use the
existing Admin receipt recovery contract. Admin unavailable or capability
mismatch must fail closed without Dream PostgreSQL fallback.

Keep `PUT /api/voice-decks/{deck_id}/agent-type` outside this phase because its
Dream branch also performs local shared-filesystem plugin materialization. Do
not move that Runtime execution into Admin or pretend that it has been closed;
record it as the immediate dependent phase. Do not change Agent Runtime, SSE,
EventBus, ThreadFactory, workflow launch, resource-policy LKG, admission/lease,
shared workspace files or `CLAUDE_CODE_TMPDIR`.

Create provider-free service/handler/consumer tests, route tests, registry hash
and generated-contract parity checks, and an isolated PostgreSQL contract test
that applies Admin Drizzle, exercises owner denial, compatibility failures,
same-selection replay, stale CAS, concurrent CAS, history ordering and draft
revision behavior through the public Admin operation handler. Run focused
tests, typecheck, lint, build, Dream pytest and a current-source closure check.
Update affected folder/file headers and architecture documents. Protect all
unrelated dirty files and stage only phase-owned paths.

USER REQUIREMENT:
继续完成 Admin 统一数据库访问与 Dream 全生产数据库访问迁移；所有数据库接口遵从 DTO/ORM 设计，保留 Dream Runtime、SSE 与共享文件系统语义。

## 背景与问题

Registry121 已由 Admin `7b98e10` 与 Dream `02290d44` 发布到工作分支。
当前源码显示 `deck-plugin-compatibility.check` 已由 Admin DTO、Service 和
Drizzle Repository 实现；Dream 的 `deck_plugin_binding.py` 仍通过
`BindingService`、`SelectionValidationService` 和 `runtime_context.py` 为五个
公开 binding 接口执行 SQL。继续保留这条路径会让同一权限和兼容性规则在
两个服务中重复执行。

## 目标与边界

- Admin 负责 binding 的 owner/Workspace 权限、兼容性事实、历史、CAS、事务和持久化。
- Dream 负责原 FastAPI 路由和响应交互，只发送严格业务 DTO。
- 本阶段覆盖 `plugin-options`、`plugin-binding` 当前态、历史、保存和验证。
- `agent-type` 的 Chat/Dream 切换留给下一阶段；其中本地 artifact 校验与 materialization 仍由 Dream 执行。
- 不新增 schema；继续使用 Admin Drizzle 已有表和 capability。

## 概念与规则

- 调用主体来自 Admin 校验的 OAuth access token；DTO 不包含 `actor_id`。
- `workspace_id` 是已认证用户当前/默认 Workspace 的业务定位字段；Admin 再次验证所有权。
- `deck_plugin_id`、版本和 expected revision 是封闭字段，不能携带 readiness、grant 或路径。
- compatibility、binding state 和 history 都由 Admin 当前事务生成。
- save 的未知提交结果只通过同一 operation/request receipt 恢复，Dream 不直接重试写入。

## 责任、依赖与文件

| 项目 | 责任 | 主要文件 | 依赖 |
|---|---|---|---|
| Admin | Registry122-126 DTO、Service、typed Drizzle Repository、Handler、capability/registry | `app/lib/dream/deckPluginBinding*.ts`、operation registry、internal route、契约 JSON | 现有 compatibility DTO/Repository/Service、Deck schema、identity principal |
| Dream | 严格 Pydantic consumer、五个公开路由切换、错误/回执恢复 | `backend/services/admin_data/deck_plugin_binding_data.py`、`backend/routers/deck_plugin_binding.py` | `AdminRequestAuth`、default Workspace dependency、统一 Admin client |
| 协调 | 文档、Registry 前缀/镜像、关闭清单和验证 | architecture/stage docs、focused/isolated tests | 两仓同一生成契约 |

## API 与事务

| Operation | Kind | Input | Output/事务 |
|---|---|---|---|
| `deck-plugin-binding.current` | read | deck/workspace | 当前 revision、可选 binding 及 compatibility summary |
| `deck-plugin-binding.history` | read | deck/workspace/limit | 当前 revision 与倒序不可变历史 |
| `deck-plugin-binding.options` | read | deck/workspace | 发布、废弃、撤销版本及逐项 selection summary |
| `deck-plugin-binding.validate` | read | deck/workspace/plugin/version/apply_to | 原公开 validation projection |
| `deck-plugin-binding.save` | write | validate 字段 + expected revision | 单事务锁 Deck、权限/compatibility、CAS、stale/insert、draft advance；同选择返回原记录 |

错误保持 `DECK_ACCESS_DENIED`、`BINDING_REVISION_CONFLICT` 与 selection
reason code；非法 DTO 为 `INPUT_INVALID`。Admin capability 缺失或服务不可用为明确
503，不回退 Dream 数据库。

## 保持不变的行为

- binding 仅影响下一次 Run，`applied_to=next_run`。
- history 继续按 revision 倒序，limit 为 1..100。
- 同一 plugin/version 保存不增加 revision 或 draft revision。
- 兼容性检查顺序、失败 owner/action 与 capability 排序保持现有响应。
- Agent Runtime、流式输出、共享文件、临时目录和资源策略不变。

## 正常流程与失败恢复

Dream 验证用户 access token并解析 default Workspace，调用一个命名 Admin
operation。Admin 再校验 scope、Deck/Workspace owner 和 DTO；read 在同一事务读取
一致事实。save 锁定 Deck，比较 expected revision，计算 compatibility，执行 stale
与 insert 并推进 draft revision后提交。Dream 只投影原公开响应。

权限失败返回404；compatibility 不允许返回422与原 validation；CAS 返回409与
current revision；能力/网络失败返回503。save 网络未知结果时按原 request id读取
receipt，只有已提交且 DTO/输入身份完全匹配才返回成功。

## 验收标准与风险

- Registry121 前缀哈希不变，五个新 operation 的 Admin/Dream 契约完全一致。
- 五个公开路由不导入或调用 Dream database/binding SQL service。
- Admin Service 只通过 typed Drizzle Repository 访问表，DTO 无 actor/SQL/path/readiness selector。
- provider-free、route、typecheck、lint、build和Dream pytest通过。
- 隔离 PostgreSQL验证权限、CAS、并发、历史和 draft revision；不访问真实业务库。
- 当前源码闭包明确从这五个路由移除 DB 路径，同时保留 `agent-type` 为下一阶段未关闭项。

主要风险是原 Python compatibility 失败映射与已有 Admin evaluator 的差异，以及
save 的 no-op/CAS 顺序。用原模型 fixture、并发集成测试和逐字段 DTO 校验锁定；
若不一致则修正 Admin Service 与文档，不降低断言。

## 设计评审结论

- 认证主体继续由 Admin OAuth 派生；五个 DTO 不含 actor、owner、SQL、表列、数据库、路径、readiness 或 grant 选择器。
- Admin 实现遵循 Zod DTO → Service → typed Drizzle Repository；compatibility 复用已有 Repository/Service，save 的 CAS 和 draft advance 位于同一 receipt transaction。
- Dream 只保留产品路由和错误投影，Admin 不可用、capability 缺失或响应异常时没有数据库 fallback。
- Runtime、ThreadFactory、EventBus、SSE、共享文件系统、`.claude-tmp` 与资源策略没有进入 Admin。
- `agent-type` 同时涉及本地 Runtime artifact/materialization，继续列为下一阶段，未被错误计入本阶段关闭范围。

首轮评审发现两项夹具问题和一项实际代码问题：Admin 单元测试未用输出 DTO 收窄联合类型，Handler 测试误带入 service-config 解析；Dream 路由切换时漏导入共用 `invoke_admin_operation`。夹具按既有模式修正，生产路由导入已补齐。隔离 PostgreSQL 首轮因 `FOR SHARE` 对测试角色要求 UPDATE ACL 失败；修正受限角色权限后重跑通过，正常数据库未被访问。

## 当前验收证据

| 检查 | 工作目录 | 结果 |
| --- | --- | --- |
| Admin Registry122-126 service/handler/registration | Admin worktree | 3 files、12 tests passed |
| Admin TypeScript | Admin worktree | `pnpm exec tsc --noEmit` exit 0 |
| Admin lint/build/full unit | Admin worktree | 定向 ESLint exit 0；Next production build exit 0；251 files、1957 tests passed、36 skipped |
| Admin Drizzle generate | Admin worktree | 118 tables；`No schema changes, nothing to migrate` |
| Admin Drizzle/PostgreSQL | Admin worktree | 63 migrations；5 integration tests passed；受限角色无法读取 `users.email`；隔离库已清理 |
| Dream binding/default/consumer route 组合 | Dream worktree | 80 passed、1 skipped、10 subtests passed |
| Dream Python compile | Dream worktree | consumer/router/two tests exit 0 |
| Registry 镜像/哈希 | 两个 worktree | 126 operations；Registry121 前缀 `969d316b...`；完整 `67a18f69...`；JSON byte-identical |
| Markdown 引用 | 两个 worktree | 14 个受影响文档、99 个本地引用、0 broken |
| 五个公开路由源码闭包 | Dream worktree | AST 检查 5 个入口均未引用 database/BindingService/SelectionValidationService/get_db |
| Dream 全量技术套件 | Dream worktree | 3704 passed、40 skipped、752 subtests passed；34 failures 均不命中本阶段 binding/default/consumer 文件 |

Dream 全量的 34 项既有失败包括仍向已移除 Dream database 属性打桩的旧测试、
当前 worktree 缺失的 `vendor/drama-forge` 故事素材，以及 Thread/Runtime/Product
其他迁移面的夹具失败；`--lf` 独立复跑仍得到同一组失败。本阶段直接命中的三项
旧 binding 默认 Workspace 夹具已改为真实 Admin operation 注入并进入上方 80 项
通过组合。后续阶段继续收敛全仓门禁，不能把这 34 项计为 Registry126 已通过。

本阶段技术通过不代表本机正常账户、Google 或真实模型验收完成。
