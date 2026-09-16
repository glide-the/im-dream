<!-- [Input] Exact deterministic authentication command and safe harness output. -->
<!-- [Output] Preserved harness failure or actual bounded test counts. -->
<!-- [Pos] Coordinator auth technical evidence; real Google/device/business acceptance remains separate. -->
<!-- [Sync] 2026-09-15: retain initial runner failures and corrected Admin/Dream auth results. -->

# Dream retired authentication deterministic primary gate

## Command

```text
cwd: /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory/frontend
command: node --import /Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/tsx/dist/esm/index.mjs --test app/api/_auth/retired-auth.test.ts
exit: 0
exec chunk: 0d1abe
```

Raw result summary:

```text
tests 13
suites 0
pass 13
fail 0
cancelled 0
skipped 0
todo 0
duration_ms 203.902459
```

The test asserted each legacy login/register/Google/device/token route returns the configured 410 boundary and invalid public authority returns 503 without publishing private endpoints. No database, network, provider, real account, dependency install, source, fixture or service was used or modified.
