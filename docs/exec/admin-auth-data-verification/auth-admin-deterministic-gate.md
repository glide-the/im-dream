<!-- [Input] Exact deterministic authentication command and safe harness output. -->
<!-- [Output] Preserved harness failure or actual bounded test counts. -->
<!-- [Pos] Coordinator auth technical evidence; real Google/device/business acceptance remains separate. -->
<!-- [Sync] 2026-09-15: retain initial runner failures and corrected Admin/Dream auth results. -->

# Admin authentication deterministic gate

## Command

```text
cwd: /Users/dmeck/.codex/worktrees/729f/ink-admin-memory
command: npx vitest run app/lib/auth/accessToken.test.ts app/lib/auth/adminAuthService.test.ts app/lib/auth/browserRedirect.test.ts app/lib/auth/browserSessionService.test.ts app/lib/auth/capabilitiesHandler.test.ts app/lib/auth/config.test.ts app/lib/auth/delegationService.test.ts app/lib/auth/pageContext.test.ts app/lib/auth/password.test.ts app/lib/auth/schemaContract.test.ts app/lib/auth/serviceAccessToken.test.ts app/lib/auth/serviceIdentity.test.ts app/lib/auth/subjectAdoption.test.ts
exit: 1
```

Raw key output:

```text
failed to load config from /Users/dmeck/.codex/worktrees/729f/ink-admin-memory/vitest.config.ts
⎯⎯⎯⎯⎯⎯⎯ Startup Error ⎯⎯⎯⎯⎯⎯⎯⎯
Error: EPERM: operation not permitted, open '/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/node_modules/.vite-temp/vitest.config.ts.timestamp-1789431934444-6b9cf55b51f768.mjs'
...
npm verbose exit 1
npm verbose code 1
```

The command did not reach test collection; no test-file count, test count, or skips were reported. This is a Vite temporary-file sandbox/harness failure, not an application assertion result.

## Scope

No source, fixture, database, network, provider, real-account, or dependency-install action was performed. The worktree had extensive concurrent edits before testing; they were preserved. No substitute runner or retry was used.
