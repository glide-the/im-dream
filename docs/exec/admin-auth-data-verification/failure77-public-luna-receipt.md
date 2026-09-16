<!-- [Input] Actual safe command receipt or preserved validation plan; pinned disclosure scan passed. -->
<!-- [Output] Executed bounded evidence including original failures and exact outcomes. -->
<!-- [Pos] Coordinator-owned technical evidence; full migration and real acceptance remain separate. -->
<!-- [Sync] 2026-09-15: retain Failure77 public/atomic/preservation and Thread SystemConfig candidate gates. -->

# Failure77 public Luna contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-failure77-public-contract.py`
- review: executed once with scoped elevated permission for the user-authorized provider-free public Failure77 Route/OriginalGET/SELECT contract against the named isolated PostgreSQL. Private fixture/configuration values were handled by the wrapper and were not read or printed.
- exit code: `1`
- result: the harness stopped at the first exact safe-error-code assertion. No pass is claimed for the remaining cases.

Captured stdout/stderr:

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: Exact safe failure code required
    at equal (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminDreamLaunchFailure.contract.ts:77:69)
    at call (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminDreamLaunchFailure.contract.ts:105:36)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
    at async <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminDreamLaunchFailure.contract.ts:155:100) {
  generatedMessage: false,
  code: 'ERR_ASSERTION',
  actual: false,
  expected: true,
  operator: '==',
  diff: 'simple'
}

Node.js v26.4.0
```

## Scope and cleanup

- Execution stopped at the first exact safe failure-code assertion; no case or assertion count was emitted and no remaining case is claimed.
- The public Route may have performed preceding isolated business writes; no direct seed/reset, DDL, expiry modification, credential/source/assertion edit, provider/model, normal-account, external network, service, or cleanup action was performed.
- The wrapper closed only its own pools/processes; no user service was stopped and no PostgreSQL history was deleted. Its sanitized command receipt is separate and was not read or modified.
