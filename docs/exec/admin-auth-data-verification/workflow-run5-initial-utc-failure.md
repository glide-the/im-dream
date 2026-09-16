<!-- [Input] Actual command/cwd/exit and sanitized captured stage output. -->
<!-- [Output] Immutable original failure/proof with precise technical coverage. -->
<!-- [Pos] Coordinator verification; no private configuration or real acceptance claim. -->
<!-- [Sync] 2026-09-15: retain original receipt below verbatim. -->

# Public Workflow Run5 full contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-workflow-run-contract.py`
- review: executed with scoped elevated permission for the user-authorized provider-free public Workflow Run contract against the prepared isolated PostgreSQL. Private fixture/environment files were handled only by the launcher and were not read or printed.
- exit code: `1`
- result: the public harness reached the authoritative full Run/history lifecycle assertion and failed. Per scope, execution stopped immediately; no later cases were run.

Captured stdout/stderr:

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: Authoritative full Run/history must match the original prepared lifecycle expectation
    at equal (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowRun.contract.ts:56:69)
    at call (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowRun.contract.ts:74:12)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
    at async <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowRun.contract.ts:93:10) {
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

- The contract stopped at the first reported full Run/history lifecycle mismatch; no conclusion is made about later cases.
- No source, assertion, fixture, database, SQL, migration, provider/model, real-account, external network, service, or cleanup action was performed.
