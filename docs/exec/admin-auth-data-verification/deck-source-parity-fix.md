<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence including unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/configuration and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Deck source-parity and focused-domain validation receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- no source, oracle, expectation, private-config, database, credential, network, service, migration, fixture, or cleanup changes were made.

## Source parity

Command: `INK_DREAM_SOURCE=/Users/dmeck/project/ink-dream-memory INK_DREAM_PYTHON=/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python pnpm exec vitest run app/lib/dream/deckLegacyParity.integration.test.ts`

Review: `sandbox_permissions=require_escalated`; approved for Vite temporary compilation files.

Exit: `0`

```text

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

(node:10513) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)
 ✓ app/lib/dream/deckLegacyParity.integration.test.ts (3 tests) 637ms

 Test Files  1 passed (1)
      Tests  3 passed (3)
   Start at  23:56:01
   Duration  825ms (transform 57ms, setup 28ms, import 70ms, tests 637ms, environment 0ms)

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

## Focused Deck tests

Command: `pnpm exec vitest run app/lib/dream/deckPluginManifestDto.test.ts app/lib/dream/deckVoiceDto.test.ts app/lib/dream/deckContentCanonical.test.ts`

Review: `sandbox_permissions=require_escalated`; approved for Vite temporary compilation files.

Exit: `0`

```text
(node:10684) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

 ✓ app/lib/dream/deckContentCanonical.test.ts (4 tests) 92ms
 ✓ app/lib/dream/deckPluginManifestDto.test.ts (15 tests) 5ms
 ✓ app/lib/dream/deckVoiceDto.test.ts (9 tests) 4ms

 Test Files  3 passed (3)
      Tests  28 passed (28)
   Start at  23:56:12
   Duration  390ms (transform 35ms, setup 21ms, import 95ms, tests 101ms, environment 0ms)

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

## TypeScript

Command: `pnpm exec tsc --noEmit --pretty false`

Exit: `2`

```text
error TS5033: Could not write file '/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tsconfig.tsbuildinfo': EPERM: operation not permitted, open '/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tsconfig.tsbuildinfo'.
```

This is a harness write-permission failure from the command’s incremental build-info output; no TypeScript source diagnostic was produced.

## ESLint

Command: `pnpm exec eslint --no-cache app/lib/dream/deckPluginManifestDto.ts app/lib/dream/deckPluginManifestDto.test.ts app/lib/dream/deckContentCanonical.ts app/lib/dream/deckContentCanonical.test.ts app/lib/dream/deckVoiceRepository.ts app/lib/dream/chatThreadService.ts app/lib/dream/deckLegacyParity.integration.test.ts`

Exit: `0`; stdout/stderr empty.

The parity mismatch is resolved: 3 parity tests and 28 focused Deck tests passed. The Node warnings and generated HTML reports are non-failing; no report was inspected or removed.
