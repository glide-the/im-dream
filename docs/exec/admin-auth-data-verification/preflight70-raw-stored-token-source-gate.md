<!-- [Input] Actual captured command receipt; locally checked against known secrets and credential patterns. -->
<!-- [Output] Verbatim safe validation output; failures and omitted acceptance stay explicit. -->
<!-- [Pos] Cross-project coordinator evidence; provider-free isolated verification only. -->
<!-- [Sync] 2026-09-15: archive after exact-SHA disclosure gate; private payloads excluded. -->

# PF70 raw stored-token source gate

- Worktree: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- Date: 2026-09-15 (Asia/Shanghai)
- Scope: provider-free, database-free deterministic validation of raw stored lock/snapshot/input-hash token bindings. No source, expectation, fixture, schema, migration, database, provider, network, ACL, browser, or service changes were made.

## Commands and results

1. `INK_DREAM_SOURCE=/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/project/ink-dream-memory/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workflowPreflightRawTokenSource.test.ts app/lib/dream/workflowPreflightExecutionService.test.ts app/lib/dream/workflowPreflightService.test.ts app/lib/dream/workflowTokenAuthority.test.ts --configLoader runner --cache false --reporter default`
   - Exit: `0`.
   - Result: `4` files passed; `35/35` tests passed; no skips reported.
   - Counts: execution service `15`, read/preflight service `10`, token authority `9`, raw stored-token source `1`.
   - Raw key output: `Test Files 4 passed (4)`; `Tests 35 passed (35)`; raw source test `preserves raw lock/snapshot/hash token bindings before normalized full original output` passed.

2. `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec tsc --noEmit --incremental false`
   - Exit: `0`.
   - Output: no diagnostics.

3. `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec eslint app/lib/dream/workflowPreflightRawTokenSource.test.ts app/lib/dream/workflowPreflightExecutionService.ts app/lib/dream/workflowPreflightExecutionService.test.ts app/lib/dream/workflowPreflightService.ts app/lib/dream/workflowPreflightService.test.ts app/lib/dream/workflowTokenAuthority.ts app/lib/dream/workflowTokenAuthority.test.ts tests/integration/adminWorkflowPreflight.contract.ts`
   - Exit: `0`.
   - Output: no diagnostics.

4. `git diff --check`
   - Exit: `0`.
   - Output: no whitespace errors.

## Skipped coverage

Other previously passed suites, public contracts, database, SQL, migrations, provider/network operations, fault injection, ACL, browser, and service operations were not run. No cleanup was performed.
