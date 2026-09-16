<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence retaining unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/config and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Confirmation oracle import-fix focused rerun receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `INK_DREAM_SOURCE=/Users/dmeck/project/ink-dream-memory INK_DREAM_PYTHON=/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python pnpm exec vitest run app/lib/dream/deckLegacyParity.integration.test.ts -t 'confirmation fingerprint and identity'`
- execution review: `sandbox_permissions=require_escalated`; approved for Vite temporary compilation files.
- no source, oracle, expectation, private-config, database, credential, provider, network, service, or cleanup changes performed.

## Result

- exit: `0`
- confirmation fingerprint and identity test passed.
- full file summary: `1` passed, `3` skipped by the focused `-t` filter.

## Captured stdout/stderr

```text
(node:15753) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

 ✓ app/lib/dream/deckLegacyParity.integration.test.ts (4 tests | 3 skipped) 256ms

 Test Files  1 passed (1)
      Tests  1 passed | 3 skipped (4)
   Start at  00:04:03
   Duration  376ms (transform 32ms, setup 14ms, import 47ms, tests 256ms, environment 0ms)

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

The Node deprecation warning and generated HTML report are non-failing. Previously passing focused tests/lint were not rerun; the unrelated Workflow TypeScript diagnostic was not rerun.
