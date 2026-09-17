<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence including unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/configuration and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Deck legacy parity discovery rerun receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- test environment:
  - `INK_DREAM_SOURCE=/Users/dmeck/project/ink-dream-memory`
  - `INK_DREAM_PYTHON=/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python`
- no database, credentials, network, service, source, oracle, assertion, or cleanup action was performed.

## Parity test

Command: `INK_DREAM_SOURCE=/Users/dmeck/project/ink-dream-memory INK_DREAM_PYTHON=/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python pnpm exec vitest run app/lib/dream/deckLegacyParity.integration.test.ts`

Review: `sandbox_permissions=require_escalated`; approved for Vite temporary compilation files.

Exit: `1`

Captured stdout/stderr:

```text
(node:6624) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

 ❯ app/lib/dream/deckLegacyParity.integration.test.ts (3 tests | 1 failed) 577ms
     × matches complete original Python manifest acceptance/defaults/coercion 115ms
     ✓ matches original canonical bytes for raw floats/bigints/Unicode/escaping 244ms
     ✓ matches original DB-facts snapshot/hash/diff rather than a copied builder 217ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  app/lib/dream/deckLegacyParity.integration.test.ts:14:2 > actual legacy Dream parity > matches complete original Python manifest acceptance/defaults/coercion
AssertionError: case 4: expected true to be false // Object.is equality

- Expected
+ Received

- false
+ true

 ❯ app/lib/dream/deckLegacyParity.integration.test.ts:14:1108


⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯


 Test Files  1 failed (1)
      Tests  1 failed | 2 passed (3)
   Start at  23:50:11
   Duration  697ms (transform 33ms, setup 15ms, import 48ms, tests 577ms, environment 0ms)

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

Bounded result: the test discovered and executed all three suites; two passed. The complete Python manifest acceptance/defaults/coercion suite failed on case 4 because the observed value was `true` while the unchanged oracle expected `false`. This is a parity mismatch requiring primary diagnosis; no expectation was changed.

## Lint

Command: `pnpm exec eslint --no-cache app/lib/dream/deckLegacyParity.integration.test.ts`

Exit: `0`; stdout/stderr empty.

Full TypeScript was not rerun because this failure is a runtime parity assertion and no new TypeScript diagnostic was produced.
