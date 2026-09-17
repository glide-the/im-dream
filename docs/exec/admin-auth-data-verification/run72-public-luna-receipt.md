<!-- [Input] Actual safe command receipt; exact secret and pattern disclosure checks passed. -->
<!-- [Output] Verbatim result with original failures and executed/skipped scope explicit. -->
<!-- [Pos] Coordinator-owned isolated technical evidence; not real account/Google/model acceptance. -->
<!-- [Sync] 2026-09-15: retain Run72 full/remaining/cleanup outcomes without overwriting historical receipts. -->

# Run72 public Luna contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-run72-public-contract.py`
- review: executed once with scoped elevated permission for the user-authorized provider-free public Run72 Route/SELECT contract against the named isolated PostgreSQL. The wrapper handled private 0600 configuration internally; no private JSON or token was read or printed.
- exit code: `1`
- result: the harness stopped at its first safe-error-code assertion. No pass is claimed for the remaining cases.

Captured stdout/stderr:

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: Original safe error code required
    at equal (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowRunCreation.contract.ts:70:69)
    at call (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowRunCreation.contract.ts:93:62)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
    at async <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowRunCreation.contract.ts:139:76) {
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

- No case count was emitted because execution stopped at the first assertion.
- The harness called the public production Route/Drizzle path; any preceding successful public business operations could therefore persist normal writes in the named isolated database, and SELECT verification could read it. No direct seed, DDL, migration, trigger change, fault SQL, privileged owner mutation, provider/model, real-account, external network, browser, or service action was performed.
- The harness `finally` path closed this run's process pools and verification clients. No independent cleanup/catalog check was run, and no claim is made for the remaining cases.
- The wrapper's own raw command receipt was not read or modified.
