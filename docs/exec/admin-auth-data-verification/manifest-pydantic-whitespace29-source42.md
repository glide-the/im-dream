<!-- [Input] Actual command/cwd/exit and sanitized captured stage output. -->
<!-- [Output] Immutable original failure/proof with precise technical coverage. -->
<!-- [Pos] Coordinator verification; no private configuration or real acceptance claim. -->
<!-- [Sync] 2026-09-15: retain original receipt below verbatim. -->

# Manifest whitespace and Preferences harness validation receipt

Worktree: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`

## 1. Manifest focused tests

- command: `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/deckPluginManifestDto.test.ts --configLoader runner --cache false`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- key output: `Test Files 1 passed (1)`; `Tests 29 passed (29)`.

Captured stdout/stderr:

```text
(node:53697) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

 ✓ app/lib/dream/deckPluginManifestDto.test.ts (29 tests) 7ms

 Test Files  1 passed (1)
      Tests  29 passed (29)
   Start at  01:04:46
   Duration  130ms (transform 17ms, setup 13ms, import 39ms, tests 7ms)

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

## 2. Actual Dream source parity

- command: `INK_DREAM_SOURCE=/Users/dmeck/project/ink-dream-memory INK_DREAM_PYTHON=/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/deckLegacyParity.integration.test.ts -t 'matches complete original Python manifest' --configLoader runner --cache false`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- key output: selected target passed; `Test Files 1 passed (1)`; `Tests 1 passed | 3 skipped (4)`.

Captured stdout/stderr:

```text
(node:53779) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

 ✓ app/lib/dream/deckLegacyParity.integration.test.ts (4 tests | 3 skipped) 105ms

 Test Files  1 passed (1)
      Tests  1 passed | 3 skipped (4)
   Start at  01:04:58
   Duration  233ms (transform 31ms, setup 11ms, import 52ms, tests 105ms, environment 0ms)

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

## 3. TypeScript

- command: `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec tsc --noEmit --incremental false`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

## 4. Focused ESLint

- command: `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec eslint app/lib/dream/deckPluginManifestDto.ts app/lib/dream/deckPluginManifestDto.test.ts app/lib/dream/deckLegacyParity.integration.test.ts tests/integration/adminUserPreferences.contract.ts`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

## Scope and cleanup

Commands used installed dependencies and the explicitly provided local Dream source/Python helper only. No source, assertion, oracle, fixture, database, provider/model, real-account, external network, service, or cleanup action was performed. The three parity cases intentionally excluded by the test filter were not rerun.
