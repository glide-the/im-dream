<!-- [Input] Registry133, Admin Drizzle managed-MCP capabilities and Dream PostgresMcpRepository call graph. -->
<!-- [Output] Executable cross-project plan for moving all managed-MCP persistence to named Admin DTO/ORM operations. -->
<!-- [Pos] Cross-project database-access phase; Dream retains MCP protocol, OAuth coordination and Runtime composition. -->
<!-- [Sync] 2026-09-16: plan the complete managed-MCP repository migration before implementation. -->
<!-- [Sync] 2026-09-16: record the implemented Registry147 provider and Dream DTO-consumer closure. -->

# Managed MCP 数据域迁入 Admin

## Optimized Prompt

You are an Expert Prompt Architect and senior Next.js, Python, PostgreSQL, Drizzle and MCP engineer. Implement one complete cross-project database-access migration for Dream managed MCP resources. The verified source is Dream `backend/claude_mcp/repository.py`, which currently opens PostgreSQL UOWs for Server list/get/create/update/delete, per-connection App desired settings, encrypted credential envelopes, discovery snapshots and legacy import receipts. Move every SQL statement, actor/workspace ownership filter, CAS check, uniqueness decision and transaction to Admin. Reuse the existing Admin internal operation registry, service identity plus OAuth/delegation authentication, strict Zod DTOs, named handlers, typed Drizzle repositories, capability requirements, receipt recovery and audit conventions. Do not add generic CRUD, SQL/table selectors, actor IDs in request DTOs, plaintext credentials, a second OAuth state machine or a migration when the existing Admin Drizzle schema is sufficient.

Append explicit operation contracts for the complete repository surface: Server list/get/create/update/delete; App settings get/update; encrypted credential get/upsert/delete; discovery snapshot get/save; import receipt get/import. Derive the canonical actor only from the presented Admin OAuth or entity-bound delegation. Keep identifiers, workspace scope, config/credential/settings revisions, transport endpoint invariants, encrypted envelope bounds, inventory hash/TTL and import fingerprints strict. Each write runs in one Admin transaction, uses Drizzle ORM, records the original request receipt, and exposes safe conflict/not-found errors. Unknown write outcomes are recovered only by the original request ID; non-idempotent writes are never blindly retried.

Replace Dream `PostgresMcpRepository` with a typed Admin repository client that maps exact Pydantic DTOs to the existing domain records. Pass the current OAuth token for product requests and the existing renewable `server-persistence` delegation for Agent turns. Keep discovery sessions, third-party MCP OAuth, AES-256-GCM encryption/decryption, Runtime snapshot projection, MCP Apps policy, Agent Runner/EventBus/SSE, shared filesystem and workspace rules in Dream. Delete Dream PostgreSQL pool construction and capability SQL from the managed-MCP composition. Add cross-language contract hash tests, Admin DTO/Service/Drizzle tests and Dream consumer/AST tests. Run focused TypeScript and Python tests, typecheck/lint, compileall, Markdown reference checks and a fresh source-only DB scan. Preserve unrelated dirty files.

Optional Enhancers: add an isolated restricted-role PostgreSQL contract after deterministic tests; run the broader managed-MCP and Agent Runtime suites if the focused tests pass.

USER REQUIREMENT:

继续完成 Admin 统一认证与数据库访问服务；数据库改造成接口必须遵从 DTO 与 ORM 设计，Dream 生产路径不得保留 PostgreSQL 访问。

## 目标与已有证据

- Dream `4d901446` 已要求每个生产 Agent turn 持有 Admin Workflow、Deck 与 turn persistence owner。
- 最新 source-only AST 回执扫描 553 个 Python 模块；除集中式 `backend/database.py` 外，`backend/claude_mcp/repository.py` 是最大的独立数据库入口，包含 1 个公共 SQL 常量、6 个数据库/driver import 和 37 个事务/连接调用。
- 调用图确认 `ClaudeMcpService`、inventory、OAuth、runtime snapshot 与 importer 共同依赖该 repository 的 14 类数据操作。
- Admin Drizzle 已拥有 `dream_mcp_servers`、`dream_mcp_credentials`、`dream_mcp_discovery_snapshots`、`dream_mcp_import_receipts`，以及 `dream.managed-mcp-resources.v1` 和 `dream.mcp-app-connection-settings.v1` capability；本阶段不需要 schema migration。

## 项目、责任人与依赖

| 项目 | 责任 | 依赖 |
|---|---|---|
| Admin | 追加严格 Zod DTO、Service、typed Drizzle Repository、Handler、Registry capability、receipt/audit 和测试 | 现有四表、identity capability、内部 service/OAuth/delegation auth |
| Dream | 新建 Pydantic DTO consumer，替换 `PostgresMcpRepository`，传递 OAuth 或 server-persistence token | Admin 新 Registry 与现有 `AdminDataClient` |
| 协调 | 冻结跨语言 contract hash，更新能力归属、数据库迁移清单和验证回执 | Admin 先提交并推送，Dream 再锁定 hash |

## 读取范围与修改范围

Admin 读取并修改 `app/lib/dream/operationRegistry.ts`、内部 operation Route、相关 `.folder.md`，新增 managed-MCP DTO、Service、Repository、Handler 与测试；只读取 `packages/db/src/schema/dream.ts` 和 0038/0053 migrations，不修改历史 Drizzle 文件。

Dream 读取并修改 `backend/claude_mcp/{repository,service,inventory,oauth,runtime_snapshot}.py`、`backend/routers/claude_mcp.py`、Agent Runtime 调用点、`backend/services/admin_data/**` 与相关测试/目录文档。删除 managed-MCP 的 PostgreSQL composition，不改变 MCP SDK、加密、网络或文件行为。

## 接口、数据库与配置变化

- API 使用 `managed-mcp.*` 命名操作；请求 DTO 不接收 actor、SQL、表、列、数据库连接或任意权限 selector。
- Server/credential/snapshot/import writes use caller-generated request ID for exact receipt recovery. CAS writes also carry expected revision; create/import retain business uniqueness.
- Credential DTO carries only encrypted `ciphertext/iv/tag/fingerprint/key_version` and expiry. Plaintext token remains inside Dream MCP OAuth/Runtime process and never enters Admin API logs.
- Dream production no longer reads `DATABASE_URL`/PostgreSQL pool for managed MCP. Admin existing `DREAM_DATA_DATABASE_URL` remains the sole database credential for this domain.
- Existing physical capability hashes remain the schema gate. New operation capability hashes distinguish API compatibility from Drizzle head.

## 保持不变的行为

- Public managed-MCP routes, status/error semantics, server ordering, user/workspace override, config revision and App desired/effective behavior remain.
- MCP discovery, SDK pagination, timeout/single-flight, third-party OAuth callback/cancel/refresh and AES-GCM document validation remain in Dream.
- Runtime snapshots remain detached and secret-bearing only in Dream memory; Agent turn uses the existing server-persistence grant and does not query resource policy.
- Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel、resource-policy LKG、shared filesystem、symlink、`0700` 与 `CLAUDE_CODE_TMPDIR` 不变。

## 流程、失败与状态转换

1. Dream public route authenticates through Admin and obtains the current `AdminRequestActor`; each managed-MCP data call presents its OAuth token.
2. Admin Handler validates the registered operation and strict DTO, resolves actor/scope from the token, checks both schema capabilities, then enters one transaction.
3. Read operations return actor/workspace-filtered DTOs. Missing data returns nullable output only where the current repository does; exact get/mutation failures retain safe not-found/conflict codes.
4. Writes lock or CAS the owned row, persist all coupled changes such as credential/snapshot invalidation, store audit and original receipt, then commit once.
5. A Dream timeout on a write queries only that original receipt. Committed returns the stored result; absent becomes an explicit unknown business failure and does not resend.
6. Agent Runtime uses the current renewable `server-persistence` delegation token for list/get credential/snapshot calls. Missing, expired, revoked, wrong Thread/Run or insufficient scope fails before ORM access.
7. Admin unavailable, capability mismatch, malformed encrypted envelope, inventory drift, revision conflict or workspace ownership failure returns a stable domain error; Dream never falls back to PostgreSQL.

## 验收标准与命令

- Admin Registry prefix through 133 remains byte-identical; all new descriptors have exact contract hashes and required schema capabilities.
- Admin tests prove strict DTO rejection, current-actor/workspace filtering, Server/App CAS, credential+snapshot invalidation, discovery revision identity, import replay/conflict and original receipt recovery.
- Dream tests prove exact advertised hashes, DTO mapping, OAuth/delegation token propagation, unknown-write recovery and no SQL/database/ConnectionPool/Postgres import in the managed-MCP production composition.
- Run focused `pnpm exec vitest run ...`, cache-free `tsc --noEmit --incremental false`, owned-file ESLint, focused Python `pytest`, `compileall`, Markdown reference validation, `git diff --check` and a fresh source-only DB scan. Record commands, working directories, exit codes and key counts.

## 风险与回滚

- Largest risk is partial write ambiguity; original request receipt recovery is required before removing local repository code.
- OAuth operations can outlive one browser request; their data calls must carry a current OAuth/delegation credential without storing it in workspace, CLI arguments or logs.
- Rollback deploys Dream `4d901446` only while the same database remains available; Admin operations are additive and can remain registered. No schema rollback is needed.

## 实现与评审结论

- Admin 已发布 Registry134-147，`ManagedMcpRepository` 使用 typed Drizzle ORM
  承担 actor/workspace 过滤、CAS、credential/snapshot invalidation、import
  serialization、事务、audit 与原请求 receipt；现有两项 schema capability
  足够，因此未新增 migration。
- Dream `AdminManagedMcpRepository` 通过十四个 strict Pydantic DTO 消费该
  契约。公开 Resources 使用当前 Admin OAuth；普通 Agent turn 使用现有
  Thread/Run 绑定的 `server-persistence` grant。Dream 无 SQL、ORM、连接池
  或 PostgreSQL fallback。
- Reflections 的 `rta_` 合同继续严格限制为六项 Chat/SystemConfig/Session
  操作。其固定分析 Runtime 注入明确的空 `ManagedMcpRuntimeSnapshot`，不扩展
  RTA 到 MCP，也不改变 section persistence、EventBus、SSE 或文件工作区。
- 离线 legacy importer 从 `INK_MCP_IMPORT_ACCESS_TOKEN` 调用 Admin
  `/principal` 派生 canonical actor，经同一 DTO adapter 导入；命令行不再
  接收 actor ID，也不读取数据库凭据。
- Admin 最终 Registry147 SHA 为
  `73a50db695af5170765f8473179b8a8dacd817c5c457161d75bec5b97c1e32f1`；
  两仓 operation artifact SHA-256 均为
  `9cd4be42914d338d4180c5c85e969b7a452f93570318cc23366b24e7a5cbe5a6`。

## 实际验证回执

| 工作目录 | 命令范围 | 结果 |
|---|---|---|
| Admin worktree | managed-MCP DTO、Service、typed Drizzle Repository、Handler、Registry 与非 integration 全量测试 | `1997 passed, 36 skipped`；Registry134-147 已由 `7eb7c71`、`ccf98d1`、`5433367` 推送 |
| Dream worktree | `test_admin_request_auth.py`、`test_admin_data_boundary.py`、`test_server_claude_agent.py`、`test_admin_server_credentials.py` | `195 passed, 4 subtests passed`，exit 0 |
| Dream worktree | `test_claude_mcp*.py` 与 `mcp_apps_phase0..3` | `184 passed, 3 skipped`，exit 0 |
| Dream worktree | 受影响 Python 模块 `py_compile` | exit 0 |
| 两仓 | JSON parse、byte size 与 SHA-256 对照 | 均为 `1010454` bytes；SHA-256 `9cd4be42914d338d4180c5c85e969b7a452f93570318cc23366b24e7a5cbe5a6` |
| Dream worktree | dirty-safe Python AST source scan | exit 0；554 modules、80 production entries、45 SQL modules、405 SQL literals、19 driver/legacy database import modules、38 legacy helper calls、308 transaction/connection calls、168 Admin operations、0 parse error |

扫描报告为
[`dream-db-closure-after-managed-mcp-registry147-source-only.json`](../exec/admin-auth-data-verification/dream-db-closure-after-managed-mcp-registry147-source-only.json)。
它证明本阶段的 `repository.py`、Router、importer 与 retained credential
compatibility module 均无 SQL、ORM、PostgreSQL pool、`DATABASE_URL` 或旧
`database` helper；它不把仍待迁移的 Plugin、Notion、startup 和旧集中式
`backend/database.py` 计为已关闭。
