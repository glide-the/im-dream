<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence retaining unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/config and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Deck confirmation-codec validation receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- Commands were run in the requested order. No source, oracle, expectation, private-config, DB, credential, provider, network, service, or cleanup changes were made.

## Original-source parity

Command: `INK_DREAM_SOURCE=/Users/dmeck/project/ink-dream-memory INK_DREAM_PYTHON=/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python pnpm exec vitest run app/lib/dream/deckLegacyParity.integration.test.ts`

Review: `sandbox_permissions=require_escalated`; approved for Vite temporary compilation files.

Exit: `1`

Key output:

```text
app/lib/dream/deckLegacyParity.integration.test.ts (4 tests | 1 failed)
× confirmation fingerprint and identity match actual original source
✓ matches complete original Python manifest acceptance/defaults/coercion
✓ matches original canonical bytes for raw floats/bigints/Unicode/escaping
✓ matches original DB-facts snapshot/hash/diff rather than a copied builder
Error: Original source oracle failed
ModuleNotFoundError: No module named 'models'
ModuleNotFoundError: No module named 'agent_stream_events'
Tests  1 failed | 3 passed (4)
```

The new confirmation fingerprint/identity oracle was blocked by the explicit Dream Python environment missing `models` and `agent_stream_events`. The three other parity assertions passed; no expectations were changed.

## Focused codec tests

Command: `pnpm exec vitest run app/lib/dream/deckContentCanonical.test.ts app/lib/dream/deckPluginManifestDto.test.ts app/lib/dream/deckVoiceDto.test.ts`

Review: `sandbox_permissions=require_escalated`; approved for Vite temporary compilation files.

Exit: `0`

```text
✓ app/lib/dream/deckContentCanonical.test.ts (15 tests)
✓ app/lib/dream/deckPluginManifestDto.test.ts (15 tests)
✓ app/lib/dream/deckVoiceDto.test.ts (9 tests)
Test Files  3 passed (3)
Tests  39 passed (39)
```

## TypeScript

Command: `pnpm exec tsc --noEmit --pretty false --incremental false`

Exit: `2`

```text
app/lib/dream/workflowContextRepository.ts(27,58): error TS2551: Property 'ownerId' does not exist ... Did you mean 'owner_id'?
```

This is outside the focused Deck files.

## ESLint

Command: `pnpm exec eslint --no-cache app/lib/dream/deckContentCanonical.ts app/lib/dream/deckContentCanonical.test.ts app/lib/dream/deckPluginManifestDto.ts app/lib/dream/deckVoiceRepository.ts app/lib/dream/deckVoiceService.ts app/lib/dream/deckLegacyParity.integration.test.ts`

Exit: `0`; stdout/stderr empty.

No further checks or cleanup were performed.
