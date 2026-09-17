<!-- [Input] Actual command/cwd/exit and sanitized captured stage output. -->
<!-- [Output] Immutable original failure/proof with precise technical coverage. -->
<!-- [Pos] Coordinator verification; no private configuration or real acceptance claim. -->
<!-- [Sync] 2026-09-15: retain original receipt below verbatim. -->

# Public Workflow Run5 full contract rerun receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-workflow-run-contract.py`
- review: executed with scoped elevated permission for the user-authorized provider-free public Workflow Route/SELECT contract against the named isolated PostgreSQL. Private fixture/environment values were handled by the launcher and were not read or printed.
- exit code: `0`
- result: PASS.

Captured stdout/stderr:

```text
{"result":"PASS","operations":["workflow-run.read","workflow-run.history","workflow-run.start","workflow-run.fail","workflow-run.cancel"],"cases":21,"assertions":163,"fixture":"provider-free-isolated-restricted-roles"}

```

The preceding failed run remains preserved at `/private/tmp/ink-auth-workflow-validation/public5-full-run-initial-failure.md`.

## Scope and cleanup

- Five public operations, 21 cases, and 163 assertions completed successfully.
- No source, assertion, fixture, database, SQL, migration, provider/model, real-account, external network, service, or cleanup action was performed.
