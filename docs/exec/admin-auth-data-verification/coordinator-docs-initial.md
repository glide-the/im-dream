<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence including unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/configuration and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Coordinator documentation synchronization validation receipt

- cwd: `/Users/dmeck/project/ink-dream-memory`
- checker: `/private/tmp/ink-coordination-docs-validation/validate.py`
- command: `python3 /private/tmp/ink-coordination-docs-validation/validate.py`
- exit: `1`
- checker was saved before execution and was not modified after the failed run.

## Scope result

The validator observed exact byte equality for all five explicit coordinator documents and all `28` files under `docs/exec/admin-auth-data-verification` in both roots. It also observed passing local-link resolution, JSON parsing, credential/private-material scans, and `git diff --check` in both roots.

The only failed assertions were:

```text
FAIL source docs/stage/.folder.md has Input header
FAIL target docs/stage/.folder.md has Input header
CHECKS FAIL; failures=2
```

These are checker-scope failures: `docs/stage/.folder.md` is a folder inventory file, not a content receipt with an `[Input]` header. No source, documentation, fixture, owner, service, browser, network, or cleanup action was performed, and the checker was not changed to mask the failure.

## Captured command output (key raw lines)

```text
PASS evidence directory file inventory matches exactly
EVIDENCE_FILES 28
PASS source parses JSON docs/exec/admin-auth-data-verification/acl-actual-privilege-proof.json
PASS target parses JSON docs/exec/admin-auth-data-verification/worktree-sync-receipt.json
PASS source docs/exec/admin-auth-data-verification/worktree-sync-validation.md has no credential/private-material literals
PASS target docs/exec/admin-auth-data-verification/worktree-sync-validation.md has no credential/private-material literals
CMD git -C /Users/dmeck/project/ink-dream-memory diff --check | exit 0
PASS source git diff --check
CMD git -C /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory diff --check | exit 0
PASS target git diff --check
CHECKS FAIL; failures=2
FAILURES
source docs/stage/.folder.md has Input header
target docs/stage/.folder.md has Input header
```

No cleanup was required.
