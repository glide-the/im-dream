<!-- [Input] Actual Luna public production Route contract command output on named disposable PG. -->
<!-- [Output] Durable provider-free technical command receipt; no real Google/model claims. -->
<!-- [Pos] Cross-project coordination evidence, credentials excluded. -->
<!-- [Sync] 2026-09-14: copied after actual execution. -->

原回执文字将request_id误称thread ID；实际stack在call函数响应关联断言和故意invalid user_id输入案例。此处保留原raw output，准确诊断与修复见后续protocol-fix回执。

# Admin public Route capability-fix contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-thread-validation/run-contract.py`
- execution review: `sandbox_permissions=require_escalated`; same previously approved narrow rule for the named isolated PostgreSQL and provider-free public Route contract.
- scope: verify the primary’s stale physical capability-reference fix; no source, assertion, fixture, migration, or database changes were made.
- private secrets/configuration were not inspected or printed.

## Result

- exit: `1`
- The capability gate passed and the contract reached `chat-thread.create`.
- The next assertion failed because the returned thread ID differed from the contract fixture expectation:
  - actual: `dream_9c2138ad7db94116871518eff8fde8da`
  - expected: `contract_43655eba-8346-4a41-a18f-004f7d5ef4b9`

## Captured stdout/stderr

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: Expected values to be strictly equal
+ actual - expected

+ 'dream_9c2138ad7db94116871518eff8fde8da'
- 'contract_43655eba-8346-4a41-a18f-004f7d5ef4b9'

    at call (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminChatThread.contract.ts:31:10)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
    at async <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminChatThread.contract.ts:55:3) {
  generatedMessage: true,
  code: 'ERR_ASSERTION',
  actual: 'dream_9c2138ad7db94116871518eff8fde8da',
  expected: 'contract_43655eba-8346-4a41-a18f-004f7d5ef4b9',
  operator: 'strictEqual',
  diff: 'simple'
}

Node.js v26.4.0

```

No other checks, cleanup, external network/service access, migrations, or fixture tampering were performed.
