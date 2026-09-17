<!-- [Input] Actual command/cwd/exit and sanitized captured stage output. -->
<!-- [Output] Immutable original failure/proof with precise technical coverage. -->
<!-- [Pos] Coordinator verification; no private configuration or real acceptance claim. -->
<!-- [Sync] 2026-09-15: retain original receipt below verbatim. -->

# Ink workflow UTC deterministic validation

Worktree: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
Date: 2026-09-15 (Asia/Shanghai)

## Vitest

Command:

```text
node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workflowRunService.test.ts app/lib/dream/workflowRunCommandService.test.ts app/lib/dream/workflowPreflightService.test.ts --configLoader runner --cache false
```

Exit code: `0`

Raw key output:

```text
 ✓ app/lib/dream/workflowRunCommandService.test.ts (24 tests) 1505ms
 ✓ app/lib/dream/workflowRunService.test.ts (6 tests) 6ms
 ✓ app/lib/dream/workflowPreflightService.test.ts (10 tests) 8ms

 Test Files  3 passed (3)
      Tests  40 passed (40)
   Start at  00:57:46
   Duration  2.27s (transform 143ms, setup 21ms, import 555ms, tests 1.52s, environment 0ms)

 HTML  Report is generated
       You can run npx vite preview --outDir html to see the test results.
```

The ignored local `./html` report directory was left untouched per the no-cleanup instruction.

## TypeScript

Command:

```text
node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec tsc --noEmit --incremental false
```

Exit code: `2`

Raw diagnostic:

```text
app/lib/dream/deckPluginCompatibilityRepository.ts(7,56): error TS2724: '"@ink-memory/db/schema/dream"' has no exported member named 'story_workspace_workspaces'. Did you mean 'story_workspace_scenes'?
```

This is a concurrent compatibility/deck diagnostic outside the three focused workflow services.

## ESLint

Command:

```text
node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec eslint app/lib/dream/workflowRunService.ts app/lib/dream/workflowRunCommandService.ts app/lib/dream/workflowPreflightService.ts app/lib/dream/workflowRunService.test.ts app/lib/dream/workflowRunCommandService.test.ts app/lib/dream/workflowPreflightService.test.ts tests/integration/adminWorkflowRun.contract.ts
```

Exit code: `0`

Raw output: empty.

## Diff check

Command:

```text
git diff --check
```

Exit code: `0`

Raw output: empty.

No source, fixture, DDL, database, public contract, provider, network, browser, service, or cleanup operation was performed.

## Post-fix whole typecheck and focused lint recheck

Command:

```text
node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec tsc --noEmit --incremental false
```

Exit code: `0`

Raw output: empty. The prior concurrent `deckPluginCompatibilityRepository.ts` schema export diagnostic is cleared.

Command:

```text
node /Users/dmeck/.cache/node/corepack/v1/pnpm.cjs exec eslint app/lib/dream/deckPluginCompatibilityRepository.ts app/lib/dream/workflowPreflightDependencyRepository.ts app/lib/dream/workflowRunService.ts app/lib/dream/workflowPreflightService.ts app/lib/dream/workflowRunCommandService.ts tests/integration/adminWorkflowRun.contract.ts
```

Exit code: `0`

Raw output: empty.

Command:

```text
git diff --check
```

Exit code: `0`

Raw output: empty.

UTC focused 40-test window remains green from the prior receipt; this recheck intentionally did not repeat those tests. Public harness execution remains separate and was not run.
