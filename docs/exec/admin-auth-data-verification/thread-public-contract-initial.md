<!-- [Input] Actual Luna command receipt captured in /private/tmp/ink-auth-thread-validation/public-contract-receipt.md. -->
<!-- [Output] Verbatim command/exit/output evidence after this header. -->
<!-- [Pos] Durable technical validation record; not real-user/Google/model acceptance. -->
<!-- [Sync] 2026-09-14: preserve executed receipts without changing assertions or outcomes. -->

# Admin public Route contract validation receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- requested isolated database: `ink_auth_data_codex_test_792494523a17` on `127.0.0.1:51534`; private launcher configuration was not read.
- no source, fixture, config, production, migration, network, browser, service, or dependency changes were made.

## Preflight status

Command: `git status --short`

Exit: `0`

```text
 M app/lib/admin/claude-agent-resources.ts
 M app/lib/gateway/auth.ts
 M app/lib/product/auth.ts
 M drizzle/meta/_journal.json
 M package.json
 M packages/db/drizzle.config.ts
 M packages/db/package.json
 M pnpm-lock.yaml
?? app/.well-known/
?? app/api/auth/
?? app/api/internal/dream/
?? app/api/runtime-delegations/
?? app/auth/
?? app/lib/auth/
?? app/lib/claude-agent-resource-dto.ts
?? app/lib/dream/
?? docs/architecture/admin-dream-auth-data-contract.md
?? docs/architecture/admin-dream-operation-contracts.json
?? docs/architecture/dream-database-access-inventory.json
?? docs/task/admin-auth-data-provider-plan.md
?? docs/verification/admin-auth-data-provider-matrix.md
?? drizzle/0054_clean_network.sql
?? drizzle/0055_unique_kitty_pryde.sql
?? drizzle/contracts/identity-better-auth-v1.json
?? drizzle/contracts/identity-runtime-delegation-v1.json
?? drizzle/meta/0054_snapshot.json
?? drizzle/meta/0055_snapshot.json
?? packages/db/src/schema/auth-generated.ts
?? packages/db/src/schema/auth.ts
?? tests/integration/
```

## Public contract harness

Command: `python3 /private/tmp/ink-auth-thread-validation/run-contract.py`

Exit: `1`

```text
node:net:2145
      const error = new UVExceptionWithHostPort(rval, 'listen', address, port);
                    ^

Error: listen EPERM: operation not permitted /var/folders/bn/m6tkvhx160d9nx6v6rkkkrj80000gn/T/tsx-501/71493.pipe
    at Server.setupListenHandle [as _listen2] (node:net:2145:21)
    at listenInCluster (node:net:2224:12)
    at Server.listen (node:net:2361:5)
    at file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/tsx@4.23.12/node_modules/tsx/dist/cli.mjs:53:31472
    at new Promise (<anonymous>)
    at createIpcServer (file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/tsx@4.23.12/node_modules/tsx/dist/cli.mjs:53:31450)
    at async file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/tsx@4.23.12/node_modules/tsx/dist/cli.mjs:55:542 {
  code: 'EPERM',
  errno: -1,
  syscall: 'listen',
  address: '/var/folders/bn/m6tkvhx160d9nx6v6rkkkrj80000gn/T/tsx-501/71493.pipe',
  port: -1
}

Node.js v26.4.0
```

This is a harness-only tsx IPC socket permission failure before the public Route contract ran. No Route or database operation was exercised.

## Focused unit/type/lint checks

Command: `pnpm exec vitest run app/lib/dream/chatThreadDto.test.ts --configLoader runner --cache false --reporter default`

Exit: `0`

```text
(node:71565) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

 ✓ app/lib/dream/chatThreadDto.test.ts (12 tests) 5ms

 Test Files  1 passed (1)
      Tests  12 passed (12)
   Start at  22:51:09
   Duration  417ms (transform 97ms, setup 13ms, import 328ms, tests 5ms, environment 0ms)
```

Command: `pnpm exec tsc --noEmit --incremental false`

Exit: `2`

```text
app/auth/consent/AuthConsent.tsx(15,42): error TS2551: Property 'redirect_uri' does not exist on type 'NonNullable<OAuthRedirectResult | { redirect: boolean; url: string; }>'. Did you mean 'redirect'?
  Property 'redirect_uri' does not exist on type 'OAuthRedirectResult'.
```

The TypeScript failure is in the other Agent’s `app/auth/consent/AuthConsent.tsx`, outside this focused DTO/Repository ownership.

Command: `pnpm exec eslint app/lib/dream/chatThreadDto.ts app/lib/dream/chatThreadRepository.ts app/lib/dream/chatThreadDto.test.ts tests/integration/adminChatThread.contract.ts`

Exit: `0`; stdout/stderr empty.

## Limitations and cleanup

The contract stage is blocked by the tsx IPC harness before route execution; it is not product evidence. The focused Vitest suite passed all 12 tests. TypeScript remains blocked by the unrelated consent component error. No private config or credentials were read. No DB, migration, fixture mutation, external network, browser, service, or cleanup action was performed.
