<!-- [Input] Actual captured command, cwd, exit and sanitized output. -->
<!-- [Output] Preserved technical proof, original failures and actual coverage limits. -->
<!-- [Pos] Coordinator verification record; no private config or real acceptance claim. -->
<!-- [Sync] 2026-09-15: retain original captured receipt below verbatim. -->

# Public runtime62 route contract receipt

## Contract command

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-auth-migration-validation/run-deck-runtime-contract.py`
- review: executed with `sandbox_permissions=require_escalated` under the previously approved narrow rule `prefix_rule=["python3","/private/tmp/ink-auth-migration-validation/run-deck-runtime-contract.py"]`; no private fixture/config was read or printed.
- exit code: `2`
- result: harness precondition failure; Python reported that the launcher path does not exist. No Deck/Voice/Runtime route assertion executed.

Captured stdout/stderr:

```text
/opt/homebrew/Cellar/python@3.14/3.14.6/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python: can't open file '/private/tmp/ink-auth-migration-validation/run-deck-runtime-contract.py': [Errno 2] No such file or directory
```

## Focused lint command

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `pnpm exec eslint --no-cache app/lib/dream/deckRuntimeDataDto.ts app/lib/dream/deckRuntimeDataRepository.ts app/lib/dream/deckRuntimeDataService.ts app/lib/dream/deckRuntimeData.test.ts tests/integration/adminDeckRuntime.contract.ts`
- exit code: `2`
- result: ESLint precondition failure because `tests/integration/adminDeckRuntime.contract.ts` was absent. No lint assertions ran.

Captured stdout/stderr:

```text

Oops! Something went wrong! :(

ESLint: 9.39.2

No files matching the pattern "tests/integration/adminDeckRuntime.contract.ts" were found.
Please check for typing mistakes in the pattern.

```

## Scope and cleanup

- Initial read-only `git status --short` was run in the Admin worktree; concurrent edits were preserved.
- No source, fixture, migration, database, credential, service, browser, network, or cleanup action was performed.
- The runtime62 contract remains unexecuted because its launcher was missing; the focused lint remains unexecuted because the named integration file was missing.
