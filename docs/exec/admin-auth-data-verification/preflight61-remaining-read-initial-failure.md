<!-- [Input] Actual safe command receipt; known-secret and pattern gate passed before archival. -->
<!-- [Output] Verbatim captured output with failed/remaining coverage explicit. -->
<!-- [Pos] Coordinator-owned provider-free isolated technical evidence, not real Google/model acceptance. -->
<!-- [Sync] 2026-09-15: exact-SHA disclosure gate; private payloads excluded. -->

# Preflight61 remaining-read public contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-preflight61-remaining-read-contract.py`
- review: executed once with scoped elevated permission for the user-authorized provider-free read-only public Route/SELECT contract against the named isolated PostgreSQL. Private fixture/environment values were handled by the wrapper and were not read or printed.
- exit code: `1`
- result: the harness stopped at the first remaining-read state assertion. No pass is claimed for the eight cases.

Captured stdout/stderr:

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: Remaining active/expired read facts must both be unconsumed
    at check (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowPreflight.contract.ts:92:54)
    at <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowPreflight.contract.ts:177:9)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5) {
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

- The eight-case remaining-read contract stopped before later cases; this does not revalidate the full 24-case contract.
- No source, assertion, fixture, database, SQL, DDL, migration, fault injection, provider/model, real-account, external network, service, or cleanup action was performed.
- The wrapper's sanitized raw receipt is separate at `/private/tmp/ink-auth-migration-validation/preflight61-remaining-read-public-command-receipt.json`.
