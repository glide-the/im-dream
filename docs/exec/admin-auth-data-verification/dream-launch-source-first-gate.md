<!-- [Input] Actual safe command receipt; pinned disclosure checks passed. -->
<!-- [Output] Original outcomes with executed/skipped scope and failures retained. -->
<!-- [Pos] Coordinator-owned isolated technical evidence; real acceptance remains separate. -->
<!-- [Sync] 2026-09-15: preserve launch75/Workspace/failure candidate and continuation/recovery evidence. -->

# Dream launch source first gate

- Worktree: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- Date: 2026-09-15 (Asia/Shanghai)
- Scope: provider-free deterministic validation only. No production, test, expectation, registry, DDL, fixture, database, network, browser, provider, package, or cleanup changes were made.

## Commands and results

1. `INK_DREAM_SOURCE=/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/dreamLaunchSourceSource.test.ts app/lib/dream/dreamLaunchSourceService.test.ts --configLoader runner --cache false --reporter default`
   - Exit: `1`.
   - Result: `2` files failed; `19/23` tests passed and `4` failed; no skips reported.
   - Service file: `19` tests, `18` passed and `1` failed.
   - Source file: `4` tests, `1` passed and `3` failed.
   - All four failures were oracle launch harness failures with `ENOENT` for the requested interpreter path `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory/.venv/bin/python`; source body/stderr were not recorded. No source parity result is inferred.
   - Raw key output: `Test Files 2 failed (2)`; `Tests 4 failed | 19 passed (23)`.

2. `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec tsc --noEmit --incremental false`
   - Exit: `2`.
   - Diagnostic: `app/lib/dream/dreamLaunchSourceRepository.ts(6,65): error TS2724: '"@ink-memory/db/schema/dream"' has no exported member named 'story_workspace_workspaces'. Did you mean 'story_workspace_scenes'?`

3. `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec eslint config/dream-launch-policy.ts app/lib/dream/dreamLaunchSourceDto.ts app/lib/dream/dreamLaunchSourceSemantics.ts app/lib/dream/dreamLaunchSourceRepository.ts app/lib/dream/dreamLaunchSourceService.ts app/lib/dream/dreamLaunchSourceHandler.ts app/lib/dream/dreamLaunchSourceService.test.ts app/lib/dream/dreamLaunchSourceSource.test.ts`
   - Exit: `0`.
   - Output: no diagnostics.

4. `git diff --check`
   - Exit: `0`.
   - Output: no whitespace errors.

## Skipped coverage

No database, provider, network, browser, package, migration, registry, public route, fixture, or service operation ran. The oracle launch failures and typecheck diagnostic are preserved without modification.

## Evidence correction

The first command used `/Users/dmeck/.codex/worktrees/ef6e/.venv/bin/python`; this was a runner path-selection error. The task's intended interpreter was `/Users/dmeck/project/ink-dream-memory/.venv/bin/python`. The resulting `ENOENT` failures were harness-only and do not establish source behavior. The original command and failure counts above are preserved verbatim.
