<!-- [Input] Exact deterministic authentication command and safe harness output. -->
<!-- [Output] Preserved harness failure or actual bounded test counts. -->
<!-- [Pos] Coordinator auth technical evidence; real Google/device/business acceptance remains separate. -->
<!-- [Sync] 2026-09-15: retain initial runner failures and corrected Admin/Dream auth results. -->

# Dream BFF authentication deterministic gate

## Command

```text
cwd: /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory/frontend
command: pnpm exec vitest run app/api/_auth/api-proxy.test.ts app/api/_auth/handlers.test.ts app/api/_auth/login-boundary.test.ts app/api/_auth/retired-auth.test.ts app/api/_auth/runtime-request.test.ts app/_dream/lib/browserSession.test.ts
exit: 254
```

Raw stdout/stderr:

```text
undefined
 ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL  Command "vitest" not found

Did you mean "pnpm exec vite"?
```

The command did not execute any test file; no test-file count, test count, or skips were reported. This is a package-runner/dependency availability harness failure.

## Scope

No source, fixture, database, network, provider, real-account, or dependency-install action was performed. No substitute runner or retry was used, and concurrent edits were preserved.
