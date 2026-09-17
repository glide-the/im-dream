<!-- [Input] Actual Luna public production Route contract command output on named disposable PG. -->
<!-- [Output] Durable provider-free technical command receipt; no real Google/model claims. -->
<!-- [Pos] Cross-project coordination evidence, credentials excluded. -->
<!-- [Sync] 2026-09-14: copied after actual execution. -->

# Admin public Route contract approved execution receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-thread-validation/run-contract.py`
- execution: `sandbox_permissions=require_escalated`; automatic review approved the requested isolated validation command.
- review justification: run the user-requested provider-free production Route contract against the identity-verified, named isolated PostgreSQL using launcher-read configuration and normal public Route writes; no migrations/DDL, real accounts, external network, or service changes.
- credentials remained inside the launcher’s `0600` configuration and were not read or printed.

## Result

- exit: `1`
- contract reached `chat-thread.create`; assertion failed because the Route returned HTTP `503` instead of expected `200`.
- This receipt records the observed Route result. No diagnosis or source/config/fixture change was performed.

## Captured stdout/stderr

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: chat-thread.create unexpected HTTP status

503 !== 200

    at call (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminChatThread.contract.ts:28:10)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
    at async <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminChatThread.contract.ts:42:19) {
  generatedMessage: false,
  code: 'ERR_ASSERTION',
  actual: 503,
  expected: 200,
  operator: 'strictEqual',
  diff: 'simple'
}

Node.js v26.4.0

```

## Scope and cleanup

No migration, DDL, fixture mutation, external network, browser, service, or cleanup action was performed. The previously observed socket `EPERM` harness blocker was bypassed only through the approved sandbox review; this run reached the Route and produced the `503` result.
