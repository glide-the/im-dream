<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence including unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/configuration and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Coordinator documentation synchronization focused rerun receipt

- cwd: `/Users/dmeck/project/ink-dream-memory`
- checker: `/private/tmp/ink-coordination-docs-validation/validate.py`
- command: `python3 /private/tmp/ink-coordination-docs-validation/validate.py`
- exit: `0`
- rerun reason: stage folder headers were repaired and two sanitized registration receipts were added since the preserved initial failure.
- no private configuration, database, source test, service, browser, network, or cleanup access was performed.

## Captured stdout/stderr key output

```text
PASS byte-identical docs/stage/.folder.md
PASS byte-identical docs/stage/stage_admin-chat-thread-domain.md
PASS byte-identical docs/stage/stage_admin-deck-voice-domain.md
PASS byte-identical docs/stage/stage_admin-auth-registration-adoption-validation.md
PASS byte-identical docs/exec/exec_admin-auth-data-coordination.md
PASS evidence directory file inventory matches exactly
EVIDENCE_FILES 30
PASS byte-identical docs/exec/admin-auth-data-verification/registration-adoption-proof.json
PASS byte-identical docs/exec/admin-auth-data-verification/registration-fixture-base-url-failure.json
PASS source docs/exec/admin-auth-data-verification/registration-adoption-proof.json has no credential/private-material literals
PASS target docs/exec/admin-auth-data-verification/registration-adoption-proof.json has no credential/private-material literals
PASS source docs/exec/admin-auth-data-verification/registration-fixture-base-url-failure.json has no credential/private-material literals
PASS target docs/exec/admin-auth-data-verification/registration-fixture-base-url-failure.json has no credential/private-material literals
CMD git -C /Users/dmeck/project/ink-dream-memory diff --check | exit 0
PASS source git diff --check
CMD git -C /Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory diff --check | exit 0
PASS target git diff --check
CHECKS PASS; failures=0
```

All observed checks passed, including current JSON parsing and local Markdown link resolution for both roots. The initial failed receipt remains preserved separately at `/private/tmp/ink-coordination-docs-validation/receipt.md`.
