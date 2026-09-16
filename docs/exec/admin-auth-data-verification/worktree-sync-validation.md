<!-- [Input] Actual Luna runner command receipt for the saved source/worktree hash verification script. -->
<!-- [Output] Durable synchronization validation evidence, with raw command output preserved. -->
<!-- [Pos] Read-only technical verification; does not close the full auth/data migration. -->
<!-- [Sync] 2026-09-14: copied the actual passing Luna receipt after execution. -->

# Source to worktree synchronization validation receipt

- cwd: `/Users/dmeck/project/ink-dream-memory`
- script: `/private/tmp/ink-worktree-sync-20260914-validate.py`
- scope: read-only source-to-worktree synchronization, preservation, inventory, local-link, JSON, frozen migration, and `git diff --check` verification.
- no project/source/fixture changes, file-body output, browser/network/service access, or cleanup was performed.

## Preflight

Command: `git status --short`

Exit: `0`

```text
 M docs/exec/.folder.md
 M docs/exec/exec_admin-auth-data-coordination.md
 M docs/stage/.folder.md
 M docs/stage/stage_admin-auth-data-coordination.md
?? docs/exec/admin-auth-data-verification/
?? docs/stage/stage_admin-auth-data-business-validation.md
?? docs/stage/stage_admin-auth-data-migration-validation.md
?? docs/stage/stage_admin-chat-thread-domain.md
?? docs/stage/stage_worktree-sync_20260914.md
```

## Validation

Command: `python3 /private/tmp/ink-worktree-sync-20260914-validate.py`

Exit: `0`

Captured stdout/stderr:

```text
dream: 20 synchronized files; target-only changes preserved; git diff --check exit 0
admin: 9 synchronized files; target-only changes preserved; git diff --check exit 0
PASS: 149 byte/preservation checks, both Markdown inventories, local references, JSON parsing and frozen migrations unchanged
```

No additional checks or cleanup were run.
