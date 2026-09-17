<!-- [Input] Actual captured command receipt; locally checked against known secrets and credential patterns. -->
<!-- [Output] Verbatim safe validation output; failures and omitted acceptance stay explicit. -->
<!-- [Pos] Cross-project coordinator evidence; provider-free isolated verification only. -->
<!-- [Sync] 2026-09-15: archive after exact-SHA disclosure gate; private payloads excluded. -->

# Preflight61 public contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-full-preflight61-contract.py`
- review: executed with scoped elevated permission for the user-authorized provider-free public Preflight61 contract against the named isolated PostgreSQL. Private 0600 fixture/environment values were handled by the launcher and were not read or printed.
- exit code: `1`
- result: contract reached the production operation/receipt harness but failed the first static-field/original-request-state assertion; execution stopped.

Captured stdout/stderr:

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: Every independently prepared static field and original request state required
    at equal (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowPreflight.contract.ts:82:69)
    at <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminWorkflowPreflight.contract.ts:173:5)
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

- The requested 24-case contract did not proceed beyond the reported assertion; no pass is claimed.
- No source, assertion, fixture, database reset, direct SQL write, DDL, migration, provider/model, real-account, external network, service, or cleanup action was performed.
