<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence including unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/configuration and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Deck domain focused rerun receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- initial receipt preserved at `/private/tmp/ink-deck-validation/initial-receipt.md`.
- Vitest ran with the approved elevated sandbox exception because Vite needed to write worktree temporary compilation files; no database/account/network writes were authorized or performed.
- no source fixes or private configuration access performed.

## Vitest

Command: `pnpm exec vitest run app/lib/dream/deckPluginManifestDto.test.ts app/lib/dream/deckVoiceDto.test.ts app/lib/dream/deckContentCanonical.test.ts`

Review: `sandbox_permissions=require_escalated`; approved.

Exit: `0`

```text
(node:4162) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

 ✓ app/lib/dream/deckPluginManifestDto.test.ts (15 tests) 5ms
 ✓ app/lib/dream/deckContentCanonical.test.ts (3 tests) 74ms
 ✓ app/lib/dream/deckVoiceDto.test.ts (9 tests) 4ms

 Test Files  3 passed (3)
      Tests  27 passed (27)
   Start at  23:46:03
   Duration  372ms (transform 35ms, setup 21ms, import 96ms, tests 83ms, environment 0ms)

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

The Node deprecation warning is non-failing. Vitest generated its configured HTML report; it was not inspected or removed.

## TypeScript

Command: `pnpm exec tsc --noEmit --incremental false --pretty false`

Exit: `0`; stdout/stderr empty.

## ESLint

Command: `pnpm exec eslint --no-cache app/lib/dream/deckContentCanonical.ts app/lib/dream/deckVoiceRepository.ts`

Exit: `0`; stdout/stderr empty.

## Scope and cleanup

The two previously reported Deck TypeScript diagnostics are cleared. No source, schema, migration, grant, fixture, database, service, browser, network, dependency, or cleanup action was performed. The initial failed receipt remains preserved.
