<!-- [Input] Actual safe command receipt; pinned disclosure checks passed. -->
<!-- [Output] Original outcomes with executed/skipped scope and failures retained. -->
<!-- [Pos] Coordinator-owned isolated technical evidence; real acceptance remains separate. -->
<!-- [Sync] 2026-09-15: preserve launch75/Workspace/failure candidate and continuation/recovery evidence. -->

# Workspace Default candidate first mechanical gate

Worktree: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`

## Preflight status

- command: `git status --short`
- exit code: `0`
- result: concurrent Admin changes were present, including the new Workspace Default files; all unrelated edits were preserved.

## Vitest

- command: `INK_DREAM_SOURCE=/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/project/ink-dream-memory/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workspaceDefault.test.ts app/lib/dream/workspaceDefaultSource.test.ts --configLoader runner --cache false --reporter default`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- review: scoped elevation for Vite temporary compilation files; installed dependencies and explicit local source/oracle only.
- exit code: `0`
- key output: `Test Files 2 passed (2)`; `Tests 21 passed (21)`.

Captured stdout/stderr:

```text
(node:73064) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
(Use `node --trace-deprecation ...` to show where the warning was created)

 RUN v4.0.18 /Users/dmeck/.codex/worktrees/729f/ink-admin-memory

 ✓ app/lib/dream/workspaceDefault.test.ts (20 tests) 9ms
 ✓ app/lib/dream/workspaceDefaultSource.test.ts (1 test) 275ms

 Test Files 2 passed (2)
      Tests 21 passed (21)
   Start at 05:56:03
   Duration 883ms (transform 203ms, setup 15ms, import 455ms, tests 284ms, environment 0ms)
```

## TypeScript

- command: `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec tsc --noEmit --incremental false`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

## Focused ESLint

- command: `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec eslint app/lib/dream/workspaceDefaultDto.ts app/lib/dream/workspaceDefaultRepository.ts app/lib/dream/workspaceDefaultService.ts app/lib/dream/workspaceDefault.test.ts app/lib/dream/workspaceDefaultSource.test.ts config/workspace-default-policy.ts`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

## Python oracle AST parse

- command: `python3 -c 'import ast,pathlib; p=pathlib.Path("tests/integration/workspaceDefaultSourceOracle.py"); ast.parse(p.read_text(),filename=str(p)); print("AST PASS")'`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout: `AST PASS`

## Git diff check

- command: `git diff --check`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

## Scope and cleanup

This was mechanical validation only. The source adapter invoked the actual production Python helper with fixed positional mocked database results and UUID; it executed no SQL, real database, network, provider, or runtime operation. No production/project source, fixtures, docs, or package files were edited, and no old gate or public contract was run. No cleanup was performed and no pre-existing Python source caches were removed.
