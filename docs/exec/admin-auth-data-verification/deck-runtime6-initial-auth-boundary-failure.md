<!-- [Input] Actual captured command, cwd, exit and sanitized output. -->
<!-- [Output] Preserved technical proof, original failures and actual coverage limits. -->
<!-- [Pos] Coordinator verification record; no private config or real acceptance claim. -->
<!-- [Sync] 2026-09-15: retain original captured receipt below verbatim. -->

# Public Deck RuntimeData six-operation contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-deck-runtime-domain/run-deck-runtime-data-contract.py`
- review: executed with scoped elevated permission for the user-authorized provider-free contract against the named isolated PostgreSQL; private launcher values were not read or printed.
- exit code: `1`
- result: the harness started and reached the public contract, then failed its first unauthorized-operation status assertion. This is an actual contract assertion failure, not a missing-launcher or sandbox precondition failure.

Captured stdout/stderr:

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: deck-plugin-refs.list public status (ACCESS_TOKEN_REQUIRED)

401 !== 403

    at call (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminDeckRuntimeData.contract.ts:26:149)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
    at async <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminDeckRuntimeData.contract.ts:35:101) {
  generatedMessage: false,
  code: 'ERR_ASSERTION',
  actual: 401,
  expected: 403,
  operator: 'strictEqual',
  diff: 'simple'
}

Node.js v26.4.0
```

## Scope and cleanup

- The six-operation public contract did not proceed beyond the first unauthorized `deck-plugin-refs.list` assertion.
- No source, assertion, fixture, database, SQL, migration, provider/model, real-account, network, service, or cleanup action was performed.
