<!-- [Input] Actual Luna command/cwd/exit captured Social deterministic validation. -->
<!-- [Output] Original pass/failure evidence with a separately recorded focused rerun. -->
<!-- [Pos] Provider-free technical proof; no normal-user acceptance or private fixture. -->
<!-- [Sync] 2026-09-15: preserve original sanitized receipt below verbatim. -->

# Social Friendship focused validation receipt

## Worktree and preflight

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `git status --short`
- exit code: `0`
- result: concurrent shared changes and untracked files were present and preserved.
- target files confirmed by `rg --files`: `app/lib/dream/socialFriendshipDto.ts`, `app/lib/dream/socialFriendshipRepository.ts`, `app/lib/dream/socialFriendshipService.ts`, and `app/lib/dream/socialFriendship.test.ts`.

## Focused Vitest

- command: `pnpm exec vitest run app/lib/dream/socialFriendship.test.ts --reporter=default`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- review: scoped elevation used for Vite temporary compilation files; installed dependencies only.
- exit code: `0`
- key output: `Test Files 1 passed (1)`; `Tests 25 passed (25)`.

Captured stdout/stderr:

```text
 RUN  v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

(node:63754) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
 ✓ app/lib/dream/socialFriendship.test.ts (25 tests) 7ms

 Test Files  1 passed (1)
      Tests  25 passed (25)
   Start at  01:23:00
   Duration  535ms (transform 148ms, setup 21ms, import 414ms, tests 7ms, environment 0ms)
```

## TypeScript

- command: `pnpm exec tsc --noEmit --incremental false`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `2`
- diagnostic:

```text
app/lib/dream/socialFriendshipRepository.ts(7,91): error TS2459: Module '"@ink-memory/db/schema/dream"' declares 'users' locally, but it is not exported.
```

This is an owner-file type error; no source change was made.

## Focused ESLint

- command: `pnpm exec eslint app/lib/dream/socialFriendshipDto.ts app/lib/dream/socialFriendshipRepository.ts app/lib/dream/socialFriendshipService.ts app/lib/dream/socialFriendship.test.ts`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

## Git diff check

- command: `git diff --check`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

## Focused documentation checker

Checker saved before execution at `/private/tmp/ink-social-friendship-validation/doc-check.py`; it compares the seven affected Markdown paths byte-for-byte between source and ef6e, checks local links and `[Input]`/`[Output]`/`[Pos]`/`[Sync]` metadata, and runs `git diff --check` in both roots.

- command: `python3 /private/tmp/ink-social-friendship-validation/doc-check.py`
- cwd: `/Users/dmeck/project/ink-dream-memory`
- corrected checker exit code: `1`
- output:

```text
source diff-check exit 0
target diff-check exit 0
DOC_FILES 7
DOC_STATUS FAIL
DOC_FAILURES 5
byte mismatch docs/exec/.folder.md
docs/exec/.folder.md missing Input header
docs/exec/.folder.md missing Output header
docs/exec/.folder.md missing Pos header
docs/exec/.folder.md missing Sync header
```

The first checker attempt used an incorrect line-start header regex and exited 1 with 29 false positives; it was corrected in the artifact checker only and rerun. The corrected result above identifies the actual target folder-index mismatch and missing metadata.

## Scope and cleanup

No project source, docs, assertions, fixtures, database, migration, provider/model, real-account, network, browser, service, or cleanup action was performed. Existing shared changes were preserved. The social friendship public contract was not run.
