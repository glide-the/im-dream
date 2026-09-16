<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence retaining unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/config and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Deck/Voice/version public contract validation receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- contract command: `python3 /private/tmp/ink-auth-migration-validation/run-deck-contract.py`
- execution review: `sandbox_permissions=require_escalated`; approved for the named isolated ACL PostgreSQL and provider-free public Route contract.
- private launcher configuration and credentials were not read or printed.
- no source, expectation, fixture, migration, SQL, provider/model, external network, service, or cleanup changes were performed.

## Contract

Exit: `1`

Captured stdout/stderr:

```text
node:internal/modules/run_main:107
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
+ actual - expected

+ 'sha256:983c86e17d70eaa3c3a97bba3a3baa8e80891cdbaeb7c7f2afdf652b992a1a0a'
- 'sha256:10cd06e6aeae2fc44f429e0d2cef1df57c47d24646cc0efdef6a3e6845baf93a'

    at <anonymous> (/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/tests/integration/adminDeckVoice.contract.ts:73:194)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5) {
  generatedMessage: true,
  code: 'ERR_ASSERTION',
  actual: 'sha256:983c86e17d70eaa3c3a97bba3a3baa8e80891cdbaeb7c7f2afdf652b992a1a0a',
  expected: 'sha256:10cd06e6aeae2fc44f429e0d2cef1df57c47d24646cc0efdef6a3e6845baf93a',
  operator: 'strictEqual',
  diff: 'simple'
}

Node.js v26.4.0

```

Bounded result: the contract reached an actual hash assertion and failed on the observed versus expected digest. No assertion was weakened and no product diagnosis is inferred here.

## Harness lint

Command: `pnpm exec eslint --no-cache tests/integration/adminDeckVoice.contract.ts`

Exit: `0`; stdout/stderr empty.

## TypeScript

Command: `pnpm exec tsc --noEmit --pretty false --incremental false`

Exit: `2`

```text
app/lib/dream/userMessageService.ts(22,78): error TS2345: Argument of type '{ thread_id: string; message_id: string; parts_json: string; title_candidate: string; metadata_json?: string; }' is not assignable to parameter of type 'ConfirmationGuardInput'.
  Property 'metadata_json' is optional in type '{ thread_id: string; message_id: string; parts_json: string; title_candidate: string; metadata_json?: string; }' but required in type 'ConfirmationGuardInput'.
app/lib/dream/userMessageService.ts(24,33): error TS2551: Property 'persistUserMessageRaw' does not exist on type 'ChatThreadRepository'. Did you mean 'persistMessage'?
```

These TypeScript errors are outside the new `adminDeckVoice.contract.ts` harness and Deck/Voice files under this validation scope.

No cleanup was performed; the receipt is the only artifact written by this validation stage.
