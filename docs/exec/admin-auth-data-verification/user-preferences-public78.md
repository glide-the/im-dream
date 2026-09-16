<!-- [Input] Actual public Preferences2 command/cwd/exit and sanitized captured output. -->
<!-- [Output] Original 78-assertion restricted-role atomicity/permission evidence. -->
<!-- [Pos] Coordinator technical proof; no private fixture or real acceptance claim. -->
<!-- [Sync] 2026-09-15: preserve original receipt below verbatim. -->

# Public User Preferences2 contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-user-preferences-contract.py`
- review: executed with scoped elevated permission for the user-authorized provider-free public Preferences Route/SELECT contract against the named isolated PostgreSQL. Private 0600 fixture/environment values were handled only by the launcher and were not read or printed.
- exit code: `0`
- result: PASS.

Captured stdout/stderr:

```text
{"result":"PASS","operations":2,"assertions":78,"fixture":"provider-free-isolated-restricted-roles","semantics":"five closed fields; NULL merge; raw config bytes; concurrent first insert; server first-login/system config isolated; receipt/audit recovery"}

```

## Scope and cleanup

- Two public operations and 78 assertions completed successfully.
- No source, assertion, expected-value, fixture, database, SQL, migration, provider/model, real-account, external network, service, or cleanup action was performed.
