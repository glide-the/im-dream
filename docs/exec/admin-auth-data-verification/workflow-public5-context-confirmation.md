<!-- [Input] Actual captured stage command/cwd/exit and sanitized output. -->
<!-- [Output] Retained technical evidence with original failure and coverage limits. -->
<!-- [Pos] Coordinator proof; no private configuration or real acceptance claim. -->
<!-- [Sync] 2026-09-15: preserve captured receipt below verbatim. -->

# Workflow context/confirmation public contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-workflow-contract.py`
- execution review: `sandbox_permissions=require_escalated`; approved for the named identity-proven isolated workflow60 PostgreSQL and restricted AUTH/DATA roles.
- launcher-only private 0600 configuration was not read or printed.
- no fixture/migration/DDL/GRANT, direct SQL write, real-account/model, external network, service, source, or cleanup action was performed.

## Result

- exit: `0`
- result: `PASS`
- operations: `workflow-context.resolve`, `chat-user-message.persist`, `chat-message.persist`, `runtime-delegation.create`, `receipt.read`
- context cases: `18`
- confirmation cases: `14`
- assertions: `170`
- fixture: `provider-free-isolated-restricted-roles`

## Captured stdout/stderr

```text
{"result":"PASS","operations":["workflow-context.resolve","chat-user-message.persist","chat-message.persist","runtime-delegation.create","receipt.read"],"context_cases":18,"confirmation_cases":14,"assertions":170,"fixture":"provider-free-isolated-restricted-roles"}

```

No existing Deck/Thread/type checks were rerun. No cleanup was performed.
