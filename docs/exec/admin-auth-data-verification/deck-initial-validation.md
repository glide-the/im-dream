<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence including unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/configuration and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Deck domain validation receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- receipt path created before validation commands.
- scope: primary-owned Deck DTO, repository/service, canonical content, helper serializer tests, ESLint, and TypeScript diagnostics.
- pending command receipts will be filled from actual executions below.

## Commands to execute

1. `pnpm exec vitest run app/lib/dream/deckPluginManifestDto.test.ts app/lib/dream/deckVoiceDto.test.ts app/lib/dream/deckContentCanonical.test.ts`
2. `pnpm exec eslint --no-cache app/lib/dream/deckPluginManifestDto.ts app/lib/dream/deckPluginManifestDto.test.ts app/lib/dream/deckVoiceDto.ts app/lib/dream/deckVoiceDto.test.ts app/lib/dream/deckVoiceRepository.ts app/lib/dream/deckVoiceService.ts app/lib/dream/deckContentCanonical.ts app/lib/dream/deckContentCanonical.test.ts`
3. `pnpm exec tsc --noEmit --incremental false --pretty false`

## Executed receipts

### 1. Vitest

Command: `pnpm exec vitest run app/lib/dream/deckPluginManifestDto.test.ts app/lib/dream/deckVoiceDto.test.ts app/lib/dream/deckContentCanonical.test.ts`

Exit: `1`

```text
failed to load config from /Users/dmeck/.codex/worktrees/729f/ink-admin-memory/vitest.config.ts

⎯⎯⎯⎯⎯⎯⎯ Startup Error ⎯⎯⎯⎯⎯⎯⎯⎯
Error: EPERM: operation not permitted, open '/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.vite-temp/vitest.config.ts.timestamp-1789400609002-85f5fa5acc0bd.mjs'
    at async open (node:internal/fs/promises:1360:25)
    at async loadConfigFromBundledFile (file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/vite@7.3.1_@types+node@22.19.7_jiti@2.6.1_lightningcss@1.30.2_tsx@4.23.12_yaml@2.9.0/node_modules/vite/dist/node/chunks/config.js:35907:3)
    at async bundleAndLoadConfigFile (file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/vite@7.3.1_@types+node@22.19.7_jiti@2.6.1_lightningcss@1.30.2_tsx@4.23.12_yaml@2.9.0/node_modules/vite/dist/node/chunks/config.js:35797:17)
    at async loadConfigFromFile (file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/vite@7.3.1_@types+node@22.19.7_jiti@2.6.1_lightningcss@1.30.2_tsx@4.23.12_yaml@2.9.0/node_modules/vite/dist/node/chunks/config.js:35764:42)
    at async resolveConfig (file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/vite@7.3.1_@types+node@22.19.7_jiti@2.6.1_lightningcss@1.30.2_tsx@4.23.12_yaml@2.9.0/node_modules/vite/dist/node/chunks/config.js:35413:22)
    at async _createServer (file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/vite@7.3.1_@types+node@22.19.7_jiti@2.6.1_lightningcss@1.30.2_tsx@4.23.12_yaml@2.9.0/node_modules/vite/dist/node/chunks/config.js:25362:67)
    at async createViteServer (file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/vitest@4.0.18_@types+node@22.19.7_@vitest+ui@4.0.18_jiti@2.6.1_lightningcss@1.30.2_tsx@4.23.12_yaml@2.9.0/node_modules/vitest/dist/chunks/cli-api.B7PN_QUv.js:9870:17)
    at async createVitest (file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/vitest@4.0.18_@types+node@22.19.7_@vitest+ui@4.0.18_jiti@2.6.1_lightningcss@1.30.2_tsx@4.23.12_yaml@2.9.0/node_modules/vitest/dist/chunks/cli-api.B7PN_QUv.js:13186:17)
    at async prepareVitest (file:///Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.pnpm/vitest@4.0.18_@types+node@22.19.7_@vitest+ui@4.0.18_jiti@2.6.1_lightningcss@1.30.2_tsx@4.23.12_yaml@2.9.0/node_modules/vitest/dist/chunks/cli-api.B7PN_QUv.js:13548:14) {
  errno: -1,
  code: 'EPERM',
  syscall: 'open',
  path: '/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.vite-temp/vitest.config.ts.timestamp-1789400609002-85f5fa5acc0bd.mjs'
}

Node.js v26.4.0



```
```

The command stopped during Vitest config startup because the harness could not write its `.vite-temp` file; tests did not execute.

### 2. ESLint

Command: `pnpm exec eslint --no-cache app/lib/dream/deckPluginManifestDto.ts app/lib/dream/deckPluginManifestDto.test.ts app/lib/dream/deckVoiceDto.ts app/lib/dream/deckVoiceDto.test.ts app/lib/dream/deckVoiceRepository.ts app/lib/dream/deckVoiceService.ts app/lib/dream/deckContentCanonical.ts app/lib/dream/deckContentCanonical.test.ts`

Exit: `0`; stdout/stderr empty.

### 3. TypeScript

Command: `pnpm exec tsc --noEmit --incremental false --pretty false`

Exit: `2`

```text
app/lib/dream/deckContentCanonical.ts(16,136): error TS2352: Conversion of type '{ PATH: string; }' to type 'ProcessEnv' may be a mistake because neither type sufficiently overlaps with the other. If this was intentional, convert the expression to 'unknown' first.
  Property 'NODE_ENV' is missing in type '{ PATH: string; }' but required in type 'ProcessEnv'.
app/lib/dream/deckVoiceRepository.ts(81,250): error TS2345: Argument of type 'string | number | boolean' is not assignable to parameter of type 'string'.
  Type 'number' is not assignable to type 'string'.
```

Both diagnostics are in the primary-owned Deck files under test.

## Scope and cleanup

No source fixes, schema/migration/grant/fixture changes, network, database, credentials, services, browser, or cleanup actions were performed. The Vitest failure is harness-only; ESLint passed; TypeScript failed on the two listed owned files.
