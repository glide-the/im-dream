<!-- [Input] Actual safe command receipt; exact secret and pattern disclosure checks passed. -->
<!-- [Output] Verbatim result with original failures and executed/skipped scope explicit. -->
<!-- [Pos] Coordinator-owned isolated technical evidence; not real account/Google/model acceptance. -->
<!-- [Sync] 2026-09-15: retain Run72 full/remaining/cleanup outcomes without overwriting historical receipts. -->

# Run72 remaining denied and receipt public Luna contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-run72-remaining-contract.py`
- review: executed once with scoped elevated permission for the user-authorized provider-free public Route/JWT/Drizzle contract against the named isolated PostgreSQL. Private fixture/log values were handled by the wrapper and were not read or printed.
- exit code: `0`
- result: PASS for the declared `remaining_denied_receipts` scope.

Captured stdout/stderr:

```text
{"result":"PASS","operations":["workflow-run.create","workflow-run.retry"],"validation_scope":"remaining_denied_receipts","cases":22,"skipped_accepted_cases":6,"prepared_original_cases":28,"receipt_cases":10,"assertions":230,"source":"remaining denied/GET only; original accepted bounded results retained, no repeated creation/source execution","fixture":"provider-free-isolated-restricted-roles","normal_database":"untouched"}
```

## Scope and cleanup

- Covered 22 remaining denied cases and 10 receipt cases with 230 assertions. Six previously accepted success cases were intentionally skipped; their bounded results were retained and not recreated.
- The harness used public Route/Drizzle access and read-only owner verification. It performed no direct seed, DDL, migration, fault SQL, privileged owner mutation, provider/model, real-account, external network, browser, service, package, or credential-preparation action. The reported `normal_database":"untouched"` applies to the normal database; the named isolated database was the contract target.
- The harness `finally` path closed its process pools and verification clients. No independent catalog-cleanup proof was run. The original full Run72 failure remains separate and was not overwritten.
