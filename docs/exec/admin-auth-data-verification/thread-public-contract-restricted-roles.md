<!-- [Input] Captured Luna command receipt. -->
<!-- [Output] All14 operation/93 assertions with limited AUTH/DATA pools; isolated technical validation only. -->
<!-- [Pos] Durable sanitized evidence. -->
<!-- [Sync] 2026-09-14: preserve raw command/cwd/exit/output below. -->

# Admin public Thread API restricted-roles contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-restricted-thread.py`
- execution review: `sandbox_permissions=require_escalated`; approved under the existing narrow authorization for the named identity-proven isolated database and provider-free public Route/DTO/ORM contract.
- roles: restricted auth/data pools for business requests, with a separate migration-owner connection only for target identity/audit receipt verification.
- no fixture/owner inspection, source/config changes, DDL/migrations/GRANTs, external network/service access, or cleanup performed.

## Preflight status

Command: `git status --short`

Exit: `0`; the full preflight output was observed before testing and all parallel worktree changes were preserved.

## Result

- exit: `0`
- `PUBLIC THREAD CONTRACT PASS`
- operations: `14`
- route calls/assertions: `93`
- verified: owner/scope/DTO/CAS/semantic replay/concurrent receipt/audit/final/process/microsecond/NULL
- database: `ink_auth_data_codex_test_792494523a17_acl56`
- provider-free: confirmed by harness output

## Captured stdout/stderr

```text
PUBLIC THREAD CONTRACT PASS: operations=14; route_calls_assertions=93; owner/scope/DTO/CAS/semantic replay/concurrent receipt/audit/final/process/microsecond/NULL verified; database=ink_auth_data_codex_test_792494523a17_acl56; provider-free




```

No owner credentials were placed in production environment variables or printed.
