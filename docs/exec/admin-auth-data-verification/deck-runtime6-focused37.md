<!-- [Input] Actual captured command, cwd, exit and sanitized output. -->
<!-- [Output] Preserved technical proof, original failures and actual coverage limits. -->
<!-- [Pos] Coordinator verification record; no private config or real acceptance claim. -->
<!-- [Sync] 2026-09-15: retain original captured receipt below verbatim. -->

# Deck RuntimeData focused validation receipt

Date: 2026-09-15 (Asia/Shanghai)

## Preflight

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `git status --short`
- exit code: `0`
- result: worktree contained concurrent edits and untracked files; they were preserved.

Captured stdout:

```text
 M .cursor/rules/00-overview.mdc
 M README.md
 M app/(admin)/admin/(workspace)/layout.tsx
 M app/api/admin/auth/bootstrap/route.test.ts
 M app/api/admin/auth/bootstrap/route.ts
 M app/api/admin/auth/login/route.ts
 M app/api/admin/auth/logout/route.ts
 M app/lib/admin/.folder.md
 M app/lib/admin/bootstrap.ts
 M app/lib/admin/claude-agent-resources.ts
 M app/lib/admin/guard.ts
 D app/lib/admin/login.ts
 M app/lib/admin/session.ts
 M app/lib/gateway/auth.test.ts
 M app/lib/gateway/auth.ts
 M app/lib/product/auth.test.ts
 M app/lib/product/auth.ts
 M config/.folder.md
 M docker/.folder.md
 M docker/Dockerfile
 M docs/README.md
 M docs/architecture/database-schema-authority.md
 M drizzle/.folder.md
 M drizzle/data/.folder.md
 M drizzle/meta/_journal.json
 M next.config.js
 M package.json
 M packages/db/drizzle.config.ts
 M packages/db/package.json
 M packages/db/src/schema/dream.ts
 M pnpm-lock.yaml
?? app/.folder.md
?? app/.well-known/
?? app/api/.folder.md
?? app/api/auth/
?? app/api/dream/
?? app/api/internal/dream/
?? app/api/runtime-delegations/
?? app/auth/
?? app/lib/.folder.md
?? app/lib/admin/session.test.ts
?? app/lib/auth/
?? app/lib/claude-agent-resource-dto.ts
?? app/lib/dream/
?? config/dream-domain-policy.ts
?? docs/architecture/.folder.md
?? docs/architecture/admin-dream-auth-data-contract.md
?? docs/architecture/admin-dream-delegation-contracts.json
?? docs/architecture/admin-dream-domain-implementation-map.json
?? docs/architecture/admin-dream-domain-implementation-map.md
?? docs/architecture/admin-dream-operation-contracts.json
?? docs/architecture/auth-device.md
?? docs/architecture/auth.md
?? docs/architecture/dream-database-access-inventory.json
?? docs/task/.folder.md
?? docs/task/admin-auth-data-provider-plan.md
?? docs/verification/.folder.md
?? docs/verification/admin-auth-data-provider-matrix.md
?? drizzle/0054_clean_network.sql
?? drizzle/0055_unique_kitty_pryde.sql
?? drizzle/0056_fuzzy_invaders.sql
?? drizzle/0057_striped_justice.sql
?? drizzle/0058_bouncy_captain_britain.sql
?? drizzle/0059_normal_martin_li.sql
?? drizzle/contracts/dream-deck-content-canonical-storage-v1.json
?? drizzle/contracts/identity-better-auth-v1.json
?? drizzle/contracts/identity-registration-integrity-v1.json
?? drizzle/contracts/identity-runtime-delegation-v1.json
?? drizzle/contracts/identity-runtime-purpose-v1.json
?? drizzle/data/auth-access-policy.mjs
?? drizzle/data/auth-subject-adoption-core.ts
?? drizzle/data/auth-subject-adoption.mjs
?? drizzle/meta/0054_snapshot.json
?? drizzle/meta/0055_snapshot.json
?? drizzle/meta/0056_snapshot.json
?? drizzle/meta/0057_snapshot.json
?? drizzle/meta/0058_snapshot.json
?? drizzle/meta/0059_snapshot.json
?? packages/db/src/schema/.folder.md
?? packages/db/src/schema/auth-generated.ts
?? packages/db/src/schema/auth.ts
?? tests/fixtures/.folder.md
?? tests/fixtures/workflowRun.ts
?? tests/integration/
```

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `rg --files app/lib/dream/deckRuntimeData.test.ts app/lib/dream/deckContentCanonical.test.ts app/lib/dream/deckRuntimeDataDto.ts app/lib/dream/deckRuntimeDataRepository.ts app/lib/dream/deckRuntimeDataService.ts app/lib/dream/deckVoiceRepository.ts app/lib/dream/deckContentCanonical.ts tests/integration/adminDeckRuntimeData.contract.ts`
- exit code: `0`

Captured stdout:

```text
tests/integration/adminDeckRuntimeData.contract.ts
app/lib/dream/deckContentCanonical.ts
app/lib/dream/deckVoiceRepository.ts
app/lib/dream/deckRuntimeDataService.ts
app/lib/dream/deckRuntimeDataRepository.ts
app/lib/dream/deckRuntimeDataDto.ts
app/lib/dream/deckContentCanonical.test.ts
app/lib/dream/deckRuntimeData.test.ts
```

## Validation commands

### Vitest

- command: `pnpm exec vitest run app/lib/dream/deckRuntimeData.test.ts app/lib/dream/deckContentCanonical.test.ts`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- review: executed with scoped elevated permission because Vite temporary compilation files require local worktree write access; installed dependencies only.
- exit code: `0`
- key output: `Test Files 2 passed (2)`, `Tests 37 passed (37)`.

Captured stdout/stderr:

```text
(node:37135) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

 ✓ app/lib/dream/deckContentCanonical.test.ts (15 tests) 345ms
 ✓ app/lib/dream/deckRuntimeData.test.ts (22 tests) 200ms

 Test Files  2 passed (2)
      Tests  37 passed (37)
   Start at  00:40:11
   Duration  1.02s (transform 110ms, setup 20ms, import 339ms, tests 545ms, environment 0ms)

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

### TypeScript

- command: `pnpm exec tsc --noEmit --pretty false --incremental false`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

### ESLint

- command: `pnpm exec eslint app/lib/dream/deckRuntimeDataDto.ts app/lib/dream/deckRuntimeDataRepository.ts app/lib/dream/deckRuntimeDataService.ts app/lib/dream/deckRuntimeData.test.ts app/lib/dream/deckVoiceRepository.ts app/lib/dream/deckContentCanonical.ts tests/integration/adminDeckRuntimeData.contract.ts`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

## Scope and cleanup

Only the requested focused tests, full no-cache typecheck, and focused lint ran. No public contract, migration, DDL, fixture preparation, provider/model call, real account access, network, browser, service, source edit, or cleanup was performed.
