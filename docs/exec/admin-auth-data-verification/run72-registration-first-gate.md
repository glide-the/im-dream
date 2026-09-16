<!-- [Input] Actual safe command receipt; exact secret and pattern disclosure checks passed. -->
<!-- [Output] Verbatim result with original failures and executed/skipped scope explicit. -->
<!-- [Pos] Coordinator-owned isolated technical evidence; not real account/Google/model acceptance. -->
<!-- [Sync] 2026-09-15: retain Run72 full/remaining/cleanup outcomes without overwriting historical receipts. -->

# Run72 registration and receipt focused gate

- Worktree: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- Date: 2026-09-15 (Asia/Shanghai)
- Scope: provider-free focused validation. No database, fixture, credential, migration, registry, route, package, or source edits were made.

## Commands and results

1. Initial combined Vitest attempt (harness CLI rejection):
   `INK_DREAM_SOURCE=/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/project/ink-dream-memory/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workflowRunDto.test.ts app/lib/dream/workflowRunCreationReceipt.test.ts app/lib/dream/receiptHandlerRunCreation.test.ts app/lib/dream/receiptHandlerPreflight.test.ts app/lib/dream/workflowRunCreationSource.test.ts --testNamePattern 'matches actual (original request validation|stored display)' app/lib/dream/workflowRunCreationService.test.ts --testNamePattern 'recovers the original bounded receipt' --configLoader runner --cache false --reporter default`
   - Exit: `1`.
   - Failure: Vitest rejected two `--testNamePattern` values (`Expected a single value for option`). No tests executed.

2. Full non-source focused files:
   `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workflowRunDto.test.ts app/lib/dream/workflowRunCreationReceipt.test.ts app/lib/dream/receiptHandlerRunCreation.test.ts app/lib/dream/receiptHandlerPreflight.test.ts --configLoader runner --cache false --reporter default`
   - Exit: `0`; `4` files, `47/47` tests passed; no skips.

3. First source targeted attempt (runner path typo):
   `INK_DREAM_SOURCE=/Users/dmeck/worktrees/ef6e/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/project/ink-dream-memory/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workflowRunCreationSource.test.ts --testNamePattern 'matches actual (original request validation|stored display)' --configLoader runner --cache false --reporter default`
   - Exit: `1`; `2` targeted tests failed with source launch status `1` because the source root was incorrect. `2` tests skipped. This harness result is not used for source parity.

4. Correct source targeted command:
   `INK_DREAM_SOURCE=/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/project/ink-dream-memory/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workflowRunCreationSource.test.ts --testNamePattern 'matches actual (original request validation|stored display)' --configLoader runner --cache false --reporter default`
   - Exit: `0`; `2/2` targeted tests passed; `2` skipped by pattern.

5. First service targeted attempt (unused interpreter path typo):
   `INK_DREAM_SOURCE=/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/project/ink-memory/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workflowRunCreationService.test.ts --testNamePattern 'recovers the original bounded receipt' --configLoader runner --cache false --reporter default`
   - Exit: `0`; `1` targeted service test passed; `20` skipped. The targeted test does not invoke the source interpreter.

6. Correct service targeted command:
   `INK_DREAM_SOURCE=/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/project/ink-dream-memory/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workflowRunCreationService.test.ts --testNamePattern 'recovers the original bounded receipt' --configLoader runner --cache false --reporter default`
   - Exit: `0`; `1/1` targeted test passed; `20` skipped by pattern.

7. `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec tsc --noEmit --incremental false`
   - Exit: `0`; no diagnostics.

8. `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec eslint app/lib/dream/workflowRunDto.ts app/lib/dream/workflowRunCreationDto.ts app/lib/dream/workflowRunCreationService.ts app/lib/dream/workflowRunCreationHandler.ts app/lib/dream/operationRegistry.ts app/lib/dream/receiptHandler.ts 'app/api/internal/dream/v1/operations/[operation]/route.ts' app/lib/dream/workflowRunCreationReceipt.test.ts app/lib/dream/receiptHandlerRunCreation.test.ts app/lib/dream/receiptHandlerPreflight.test.ts app/lib/dream/workflowRunCreationSource.test.ts`
   - Exit: `0`; no diagnostics.

9. `git diff --check`
   - Exit: `0`; no whitespace errors.

## Skipped coverage

Previously passed semantic/core suites and full Preflight stages were not repeated. No public/database/fault/provider/network/browser/package/migration operation ran.
