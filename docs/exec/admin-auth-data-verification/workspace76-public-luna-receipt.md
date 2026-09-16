<!-- [Input] Actual safe command receipt, pinned disclosure scan passed. -->
<!-- [Output] Executed scope, original failures and concrete outcomes. -->
<!-- [Pos] Coordinator-owned technical evidence; full migration and real acceptance remain separate. -->
<!-- [Sync] 2026-09-15: retain Workspace76/public recovery and unregistered SystemConfig25 gates. -->

# Workspace76 public Luna contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-workspace76-public-contract.py`
- review: executed once with scoped elevated permission for the user-authorized provider-free default Workspace public Route/GET/SELECT contract against the named isolated PostgreSQL. Private 0600 fixture/configuration values were handled by the wrapper and were not read or printed.
- exit code: `0`
- result: PASS for the provider-free default Workspace scope.

Captured stdout/stderr:

```text
{"result":"PASS","scope":"provider-free default Workspace","cases":14,"receipts":22,"assertions":347,"protected_tables":17,"initial_same_and_distinct_original_concurrency":true,"actual_entire_original_source":true,"normal_business_runtime":"not executed"}
```

## Scope and cleanup

- Covered 14 public cases, 22 receipts, and 347 assertions with 17 protected tables, including the original-source and same/distinct concurrency checks reported by the harness.
- Public Route/GET operations and owner SELECT verification ran against the named isolated database. No direct seed, DDL, fault injection, reset, credential/source/assertion change, normal-account, provider/model, external network, or user-service operation was performed.
- The wrapper closed only its own process pools; no user service was stopped and no business history was deleted. `normal_business_runtime` was explicitly not executed.
- The wrapper's sanitized raw command receipt is separate at `/private/tmp/ink-auth-migration-validation/workspace76-public-command-receipt.json`.
