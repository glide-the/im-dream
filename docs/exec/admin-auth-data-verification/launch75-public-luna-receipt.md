<!-- [Input] Actual safe command receipt; pinned disclosure checks passed. -->
<!-- [Output] Original outcomes with executed/skipped scope and failures retained. -->
<!-- [Pos] Coordinator-owned isolated technical evidence; real acceptance remains separate. -->
<!-- [Sync] 2026-09-15: preserve launch75/Workspace/failure candidate and continuation/recovery evidence. -->

# Launch75 public Luna contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-launch75-public-contract.py`
- review: executed once with scoped elevated permission for the user-authorized provider-free public Auth+DATA/Drizzle contract against the named isolated PostgreSQL. Private fixture/configuration values were handled by the wrapper and were not read or printed.
- exit code: `1`
- result: the harness reached the original-public-status assertion and stopped at the first failure. No pass is claimed for the remaining cases.

Captured stdout/stderr:

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: Unexpected public original status
    at equal (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminDreamLaunch.contract.ts:96:69)
    at checkOriginals (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminDreamLaunch.contract.ts:158:49)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
    at async <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminDreamLaunch.contract.ts:255:22) {
  generatedMessage: true,
  code: 'ERR_ASSERTION',
  actual: false,
  expected: true,
  operator: '==',
  diff: 'simple'
}

Node.js v26.4.0
```

## Scope and cleanup

- No case or assertion count was emitted because execution stopped at the first assertion; no remaining cases are claimed.
- The public Route may have performed its preceding isolated business writes; no direct fixture/SQL seed, trigger, DDL, production/normal-account, Google/provider/model, external network, dependency installation, or harness/source modification was performed.
- The wrapper's `finally` path closed only its owned pools/clients; no user service was stopped and no business record was deleted. No independent cleanup/catalog proof was run.
