<!-- [Input] Actual Luna command/cwd/exit captured Social deterministic validation. -->
<!-- [Output] Original pass/failure evidence with a separately recorded focused rerun. -->
<!-- [Pos] Provider-free technical proof; no normal-user acceptance or private fixture. -->
<!-- [Sync] 2026-09-15: preserve original sanitized receipt below verbatim. -->

# Social Friendship type rerun and documentation scope correction receipt

## Type rerun

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `pnpm exec tsc --noEmit --incremental false`
- exit code: `0`
- stdout/stderr: empty.

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `pnpm exec eslint app/lib/dream/socialFriendshipRepository.ts`
- exit code: `0`
- stdout/stderr: empty.

The earlier social Friendship receipt remains at `/private/tmp/ink-social-friendship-validation/focused-receipt.md`; its original 25-test pass, typecheck failure, and initial documentation result were not overwritten.

## Corrected focused documentation checker

Checker: `/private/tmp/ink-social-friendship-validation/doc-check.py`.

The checker covers eight affected paths: the six ordinary mirrored documents from the original scope, `docs/exec/.folder.md` under the previously reviewed three-way union rule, and the new `docs/stage/stage_admin-workflow-preflight-request-migration.md`. For `docs/exec/.folder.md`, it removes only the five previously reviewed Admin consumer index rows and the one previously reviewed Sync line before comparing source and ef6e; all other bytes must match. Every Markdown file is checked for local links and `[Input]`/`[Output]`/`[Pos]`/`[Sync]` metadata. Both roots run `git diff --check`.

- cwd: `/Users/dmeck/project/ink-dream-memory`
- command: `python3 /private/tmp/ink-social-friendship-validation/doc-check.py`
- exit code: `0`
- key output:

```text
source diff-check exit 0
target diff-check exit 0
DOC_FILES 8
DOC_STATUS PASS
DOC_FAILURES 0
```

The prior uncorrected checker failure is preserved in the earlier receipt; no project documentation was edited by this validation.

## Scope and cleanup

No source, docs, assertions, fixture, database, migration, provider/model, account, network, service, or cleanup action was performed.
