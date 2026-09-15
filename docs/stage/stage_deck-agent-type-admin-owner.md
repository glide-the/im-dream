<!-- [Input] Registry126 baseline, the public agent-type route, Admin Runtime policy and shared plugin artifact verifier. -->
<!-- [Output] Registry127-129 DTO/ORM implementation, review conclusion and repeatable verification evidence. -->
<!-- [Pos] Executed cross-project phase record; Dream keeps artifact verification while Admin owns all persistence. -->
<!-- [Sync] 2026-09-16: complete and verify the public agent-type database closure. -->

# Deck Agent Type 数据归属迁移

## Optimized Prompt:

You are the cross-project Admin/Dream migration engineer closing the remaining
database path in `PUT /api/voice-decks/{deck_id}/agent-type` after Registry126.
Append three exact operations without changing the Registry126 prefix:
`deck-plugin-binding.clear`, `deck-agent-type.runtime-plan` and
`deck-agent-type.runtime-prepare`. Implement strict Zod DTOs, an Admin Service
and typed Drizzle Repository, production Handler registration, matching strict
Pydantic consumers and original-request receipt recovery.

For Chat, Admin must owner-lock the Deck, verify the Workspace and expected
binding revision, mark the active binding stale, advance the Deck draft only
when a binding changed, and return the existing public Chat response. For
Dream, Admin must select the single server-configured required Claude plugin
from `DREAM_RUNTIME_ACTIVATION_POLICY_JSON`, resolve its published Deck Plugin
release/runtime lock and ready installation, and return only the closed local
verification candidate. Dream verifies the immutable shared artifact and local
Claude CLI using the existing verifier. It then submits exact observed evidence
to Admin. Admin re-resolves all authoritative rows, rejects mismatches, records
or refreshes Runtime materialization and ensures the Workspace installation in
one receipt transaction. Dream finally calls the existing
`deck-plugin-binding.save` CAS operation; never combine the local filesystem
step with an Admin database transaction or blindly retry an unknown write.

Do not accept actor IDs, arbitrary plugin IDs, paths, SQL, table/column names,
runtime placement, policy or readiness flags from the browser. Do not return
`artifact_path` or `cache_ref`; Admin derives those from its own installation
row. Keep the existing OAuth user delegation, 404 owner denial, 409 stale CAS,
503 Runtime readiness failures and public response shape. Admin unavailable,
missing capability, invalid local artifact, missing CLI, ambiguous configured
release or unknown receipt must fail closed without Dream PostgreSQL fallback.

Remove `database`, `BindingService`, `SelectionValidationService` and
`DreamRuntimeProvisioningService` from the public binding router. Do not alter
the separate Dream launch preparation path in this phase; record its remaining
`DreamRuntimeProvisioningService` database dependency for the next closure.
Preserve Runtime execution, Agent/Thread/SSE/EventBus behavior, resource-policy
LKG, shared workspace files, sandbox rules and `CLAUDE_CODE_TMPDIR`.

Add provider-free DTO/service/handler/client/route tests, exact Registry prefix
and mirror checks, unknown-write recovery tests, local verifier failure tests,
and an isolated PostgreSQL contract covering owner denial, Chat no-op/clear,
Dream preparation, evidence mismatch, stale CAS, materialization idempotency,
Workspace installation and binding save. Run focused tests, typecheck, lint,
build, Dream route tests, Markdown links and an AST database-closure check.
Protect unrelated dirty Dream files and stage only phase-owned paths.

USER REQUIREMENT:
继续完成 Admin 统一数据库访问与 Dream 全生产数据库访问迁移；数据库接口必须遵从 DTO/ORM 设计，同时保留 Dream Runtime 与共享文件系统操作。

## 背景与问题

Registry126 已把 current/history/options/validate/save 五个绑定入口迁入 Admin。
同一 Router 中的 `agent-type` 仍通过 `_binding_db` 打开 PostgreSQL，并在 Chat
分支调用 `BindingService.clear`，在 Dream 分支调用
`DreamRuntimeProvisioningService.ensure_binding`。后者把共享 artifact/CLI 校验与
release、installation、materialization、binding 持久化混在一个 Python 服务内。

## 目标与边界

- Admin 负责权限、Runtime 元数据、Workspace installation、binding CAS、draft revision 和事务。
- Dream 负责从受控共享 artifact store 校验字节、执行本机 Claude CLI 兼容检查和产品路由编排。
- 本阶段只关闭公开 `agent-type` 路由；Dream launch 中复用的旧 provisioning 类单独列入下一阶段。
- 不改 schema；使用 Admin Drizzle 当前表和 `DREAM_RUNTIME_ACTIVATION_POLICY_JSON`。
- 浏览器继续只提交 `agent_type` 与 `expected_binding_revision`。

## 概念与规则

- runtime plan 由 Admin 的策略、published/deprecated release、immutable lock 和 ready installation 生成；调用方不能选择插件。
- Dream evidence 只证明本地看见的 package/version/digest/manifest；Admin 再与自己的 installation 和 lock 精确匹配。
- materialization 的 placement、key、policy revision、`artifact_path/cache_ref` 均由 Admin 配置与数据库行决定。
- Runtime prepare 可以先于 binding CAS提交；它是幂等前置条件，竞争失败只留下可复用的准备状态，不改变当前 Agent type。
- 所有写入使用 operation receipt；未知结果查同一 request id，不重发 POST。

## API、状态与事务

| Operation | Kind | 输入 | 输出与事务 |
|---|---|---|---|
| `deck-plugin-binding.clear` | write | deck/workspace/expected revision | owner-lock、CAS、可选 stale、可选 draft advance，返回 Chat 类型和当前 revision |
| `deck-agent-type.runtime-plan` | read | deck/workspace | 当前 revision、唯一目标 release/lock 与不含路径的本地安装候选 |
| `deck-agent-type.runtime-prepare` | write | deck/workspace/expected revision + exact verified evidence | 重新选定目标；同一 receipt transaction 写/刷新 materialization 和 Workspace installation |

Dream 正常切换顺序为 plan → 本地 artifact/CLI verification → prepare → existing
binding save。Chat 只调用 clear。plan/prepare 缺失目标、配置不一致或本地验证失败返回
`RUNTIME_PLUGIN_NOT_READY`；并发 binding 改动返回原 `BINDING_REVISION_CONFLICT`。

## 影响范围与保持行为

受影响文件为 Admin `deckPluginBinding*`、新增 `deckAgentTypeRuntime*`、operation
registry/handler/contract，以及 Dream `admin_data` consumer、Deck 本地 verifier、
binding router/tests和架构/目录文档。公开 JSON、`applied_to=next_run`、binding history、
同选择幂等、Chat no-op revision、draft revision、404/409/503 映射保持不变。
Agent Runtime、launch turn、流式输出、共享 Workspace 和资源策略不变。

## 验收与风险

- Registry126 前缀与两仓契约镜像保持完全一致。
- public `agent-type` 函数及其依赖不再打开 Dream DB；无 Admin fallback。
- Admin 生产数据代码只使用 typed Drizzle Repository；DTO 无 actor/path/policy/readiness selector。
- Chat clear、Dream prepare/save、stale CAS、unknown receipt、artifact/CLI failure均有断言。
- 隔离 PostgreSQL和 provider-free 门禁通过；正常业务库不用于破坏性验证。

主要风险是旧 provisioning 的自动安装能力与两段准备/绑定的竞争。当前正常启动已经
安装平台内置 plugin；本阶段在缺失 ready installation 时明确失败并保留现有启动项为
后续迁移清单，不在公开请求中恢复 Dream SQL。准备事务可安全重放，binding CAS仍是
唯一改变 Agent type 的提交点。

## 设计评审结论

实现满足本阶段边界，可以提交：Admin 的 Service 只接受严格 DTO，经 typed Drizzle
Repository 完成 owner lock、CAS、Runtime 元数据读取和 receipt transaction；Dream
Router 已删除 `database`、旧 Binding/Selection Service 与
`DreamRuntimeProvisioningService` 依赖。Runtime plan 不返回服务器路径，Dream 从既有
artifact store 推导本地路径并验证 manifest/CLI，prepare 只回传不可变 evidence。

评审中确认并保留两项后续工作：Dream launch preparation 仍引用旧 provisioning 类；
启动期 plugin seed/install 仍有数据库访问。它们不在本次公开 `agent-type` 调用链内，
必须在后续迁移为 Admin DTO 操作，且不能在缺失 Admin 能力时回退到 Dream PostgreSQL。

## 实现与契约结果

- Registry126 前缀保持不变，Registry129 canonical SHA-256 为
  `686f0668c72ca6114d894392d2dd2a2fde228b87fa31a1b858fd1dd553663881`。
- 新增 operation hash：clear 为
  `9a89ec380e280fc64b67b9725a68edf3244df0f76e41df8db5fd89b3e3fd44fc`，
  runtime-plan 为
  `87a3f0497e3927aa8c8048e6bc79de1b042631f096f85184568201dce378e5f7`，
  runtime-prepare 为
  `9cc1a08d15e0279ed977bb5b7ee25a5ab270cf32a4f67ded719c23e33d000716`。
- 两仓 `admin-dream-operation-contracts.json` 字节一致；本阶段没有 schema 变化或
  migration。
- Chat clear 保留旧 revision/no-op 语义；Dream 依次执行 plan、本地验证、prepare、
  binding.save，最终 binding CAS 仍是唯一切换 Agent type 的提交点。

## 验证回执

| 工作目录 | 命令 | 结果 |
|---|---|---|
| Admin | `pnpm test:run` | exit 0；251 files passed、17 skipped；1962 tests passed、36 skipped |
| Admin | `pnpm exec tsc --noEmit` | exit 0 |
| Admin | `pnpm build` | exit 0；Next.js 16.1.6 production build 完成 |
| Admin | `pnpm db:generate` | exit 0；118 tables；`No schema changes, nothing to migrate` |
| Admin | `node scripts/run-deck-plugin-binding-contract.mjs` | exit 0；63 migrations 后 restricted-role PostgreSQL contract 7 tests passed，隔离数据库已删除 |
| Dream | focused pytest：Admin binding consumer、local runtime verifier、binding router、deck defaults | exit 0；42 passed、1 skipped、10 subtests passed |
| Dream | `PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest==9.1.1 --with pytest-asyncio python -m pytest backend/tests -q` | exit 1；3713 passed、40 skipped、752 subtests passed、34 个基线既有失败 |
| 两仓 | 受影响 Markdown 本地引用检查 | exit 0；15 files、94 local links、0 broken |
| 两仓 | production file header 与 `git diff --check` | exit 0；7 个关键文件头完整、无 whitespace error |

Dream 全量失败集合与迁移前基线的 34 个名称一致；通过数从 3704 增加为 3713。
失败仍来自旧路由测试桩已移除的 `database` 属性、既有 dispatcher fixture 签名、缺失
Claude CLI runtime manifest、未同步 vendor 剧集 fixture 和既有 Product BFF 测试配置，
没有本阶段新增失败。
