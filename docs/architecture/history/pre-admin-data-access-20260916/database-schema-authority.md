# Dream 数据库 Schema 权威与运行时边界

> 状态：Capability-only implemented；production environment inventory pending
> 更新：2026-08-12

## R37 提交轮次记录

- 当前轮次目标：在两个存在其他未提交工作的仓库中，分别提交“Admin/Drizzle 单一 DDL 权威 + Dream 领域运行时所有权”实现，并强制把 Dream 根 `AGENTS.md` 纳入版本管理。
- 优化后的执行提示词：审计两个工作树，只暂存数据库权威切换所需的 migration、catalog、capability、依赖清理、测试、运维文档与 Agent 协议；对同时包含 DreamAgent runtime 改动的文件执行分块暂存；分别验证 staged diff、敏感信息、测试证据和 `git diff --check` 后，按 Conventional Commits 在各仓库创建独立提交，不回退或暂存其他用户改动。
- 本轮检查或修改范围：Dream 的 capability-only runtime、Alembic/DDL 删除、legacy importer、相关数据库测试和文档；Admin 的 0032、完整 Dream schema/catalog、migration runner、数据 migration registry、接管 E2E、文档与 `AGENTS.md`。
- 本轮完成标准：两个提交仅包含上述边界；Dream `AGENTS.md` 被 Git 跟踪；`20260811_07` 的 live index/capability 和不可执行审计副本均位于 Admin；提交后其他 DreamAgent/UI 工作仍保持未暂存。
- 本轮实际结果和未验证推断：提交前完整实现验证为 Dream 1,955 passed、22 skipped、655 subtests，Admin 378 tests、TypeScript、ESLint、schema cutover 与真实 43+5 数据 E2E 通过。生产环境的 06/07 分布、PITR、migrator ACL 仍是未验证的外部发布事实，不纳入本地提交完成声明。

## 决策

Dream 不再是 PostgreSQL DDL 版本所有者。所有共享 Schema 变更只在 `/Users/dmeck/project/ink-admin-memory/drizzle` 以新的前向 migration 演进。Dream 保留领域运行时所有权：repository、transaction、用户身份、thread/workflow 绑定、业务权限和数据完整性仍由 Dream 代码负责。

```mermaid
sequenceDiagram
  participant Release as Admin release job
  participant DB as PostgreSQL
  participant Dream as Dream startup
  Release->>DB: pnpm db:migrate (MIGRATION_DATABASE_URL)
  DB-->>Release: atomic receipt + capabilities
  Release->>DB: pnpm db:migrate:check
  Dream->>DB: SELECT required schema_capabilities
  alt all capabilities satisfy minimum versions
    DB-->>Dream: safe capability receipt
    Dream->>DB: normal repository queries
  else capability missing or inconsistent
    DB-->>Dream: mismatch
    Dream-->>Dream: fail closed without DDL
  end
```

## Runtime contract

Dream production startup:

- only reads `drizzle.schema_capabilities`;
- requires `dream.schema.unified.v1` v1、`dream.workflow.thread-lookup.v1` v1、`dream.story-artifact-contract.v2` v2；
- accepts unrelated higher Admin capabilities/global migrations；
- never creates/alters/drops a table, runs Alembic, or falls back to SQLite；
- logs only safe capability mode/version/hash metadata, never DSN or business values.

There is no legacy-head fallback. The frozen `dream_alembic_version` relation,
when present on an adopted database, is historical audit data only and Dream
never reads it. Admin `0032` is responsible for validating an old `06/07`
catalog and publishing the capability receipt before Dream starts.

## Domain write boundary

Unified DDL does not grant Admin arbitrary Dream writes. Every workflow/data command must still validate the authenticated canonical user, thread/workspace ownership, workflow permission, expected version/idempotency key, referential integrity and terminal-state rules. Import tooling remains Dream-owned because it encodes source snapshot, transformation, conflict and digest semantics; Admin only owns its explicit runner and append-only receipt.

## 43+5 import

New targets must first have `dream.schema.unified.v1`. The V2 definition fixes the 48-table inventory but intentionally does not fix a business row count. Source row count, manifest hash, per-table primary-key and row digests, foreign keys, sequences and triggers are verified on every run. Existing V1 receipts remain immutable and are reused when the source fingerprint matches.

## Operational rule

Dream contains no Alembic runner or PostgreSQL DDL generator. For every new or
adopted environment, run only the Admin release commands:

```bash
pnpm db:migrate
pnpm db:migrate:check
```

Missing capability is a release/configuration failure. Dream must not repair it locally. For rollout, adoption modes, rollback and outstanding production inventory, use `/Users/dmeck/project/ink-admin-memory/docs/architecture/database-schema-authority.md`.

## Historical artifact disposition

| Original Dream artifact | Current status | Replacement | Handling |
|---|---|---|---|
| `backend/migrations/versions/20260809_01–20260809_06` | Removed from Dream | Admin `0032` plus full Drizzle contract | Frozen as non-executable `.py.txt` audit copies under Admin `drizzle/legacy/dream-alembic/` |
| `backend/migrations/versions/20260811_07_dream_thread_lookup.py` | Removed from Dream | Admin `0032` + `dream.workflow.thread-lookup.v1` | Exact source archived as `.py.txt`; index contract remains live in Admin |
| `backend/alembic.ini`, `backend/migrations/env.py`, `backend/schema/migration.py`, `backend/schema/baseline.py` | Deleted | Admin migration runner and atomic 0032 adoption | Recoverable from Git; no compatibility runner retained |
| `backend/schema/postgres.py`, `backend/schema/postgres_schema.sql`, schema renderer | Deleted | Admin Drizzle SQL/schema/snapshot/catalog | Dream importer retains only data transformation and read-only target verification |
| `dream_alembic_version` in adopted databases | Frozen audit data | `drizzle.__drizzle_migrations` + `drizzle.schema_capabilities` | Not read or updated by Dream; any later archive/drop requires a new Drizzle migration |
