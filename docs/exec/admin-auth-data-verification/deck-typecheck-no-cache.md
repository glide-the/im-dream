<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence including unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/configuration and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Deck TypeScript no-cache validation receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `pnpm exec tsc --noEmit --pretty false --incremental false`
- exit: `0`
- stdout/stderr: empty

This focused rerun disabled the `tsconfig.tsbuildinfo` write that previously caused the harness-only `EPERM`. No TypeScript source diagnostics were produced. Previously passing parity/focused tests and lint were not rerun.

No source, config, oracle, database, credential, network, service, or cleanup changes were performed.
