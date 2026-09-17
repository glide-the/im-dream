<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence including unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/configuration and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Deck legacy parity validation receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- no private configuration was read.
- test environment used only explicit values:
  - `INK_DREAM_SOURCE=/Users/dmeck/project/ink-dream-memory`
  - `INK_DREAM_PYTHON=/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python`
- no database, account, model, network, service, source, fixture, assertion, or cleanup action was performed.

## Parity test

Command: `INK_DREAM_SOURCE=/Users/dmeck/project/ink-dream-memory INK_DREAM_PYTHON=/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python pnpm exec vitest run tests/integration/deckLegacyParity.integration.test.ts`

Review: `sandbox_permissions=require_escalated`; approved for Vite temporary compilation files.

Exit: `1`

Captured stdout/stderr:

```text
(node:5553) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

No test files found, exiting with code 1

filter: tests/integration/deckLegacyParity.integration.test.ts
include: app/**/*.test.ts
exclude:  node_modules, .next, dist, **/*.e2e.test.ts, **/*.e2e.ts

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

Bounded result: Vitest’s configured include pattern did not discover the requested `tests/integration` file; the 16-case parity test did not execute. This is test-discovery harness evidence, not a case mismatch or product failure.

## New test file lint

Command: `pnpm exec eslint --no-cache tests/integration/deckLegacyParity.integration.test.ts`

Exit: `0`; stdout/stderr empty.

Full TypeScript was not rerun because the parity test did not execute and ESLint reported no new TS-relevant issue. The prior 27-test/TypeScript/lint receipt remains unchanged.
