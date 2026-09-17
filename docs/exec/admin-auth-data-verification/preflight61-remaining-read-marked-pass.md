<!-- [Input] Actual safe command receipt; known-secret and pattern gate passed before archival. -->
<!-- [Output] Verbatim captured output with failed/remaining coverage explicit. -->
<!-- [Pos] Coordinator-owned provider-free isolated technical evidence, not real Google/model acceptance. -->
<!-- [Sync] 2026-09-15: exact-SHA disclosure gate; private payloads excluded. -->

# Preflight61 marker remaining-read public contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-preflight61-remaining-read-contract.py`
- review: executed once with scoped elevated permission for the user-authorized provider-free read-only public Route/SELECT contract using the marker fixture. Private fixture/environment values were handled by the wrapper and were not read or printed.
- exit code: `0`
- result: PASS for the declared `remaining_reads` scope.

Captured stdout/stderr:

```text
{"result":"PASS","validation_scope":"remaining_reads","operations":1,"cases":8,"assertions":74,"fixture":"provider-free-isolated-restricted-roles","source":"actual PreflightService full projection/raw input/fingerprint/pft bytes","semantics":"remaining reads only; independent active/expired unconsumed facts; full original projection; actual clock; no writes or repeated execution"}
```

## Scope and cleanup

- Covered one remaining-read operation, eight cases, and 74 assertions, including active/expired unconsumed facts, full original projection, actual clock, raw input/fingerprint/PFT bytes, and no-state-write behavior.
- This receipt does not claim the full Preflight 24-case contract, Google/provider/model acceptance, or real-account acceptance.
- No source, assertion, fixture, database, SQL, DDL, migration, provider/model, real-account, external network, service, or cleanup action was performed. The wrapper's sanitized raw receipt is separate at `/private/tmp/ink-auth-migration-validation/preflight61-remaining-read-marker-public-command-receipt.json`.
