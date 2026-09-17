<!-- [Input] Actual command/cwd/exit and sanitized captured stage output. -->
<!-- [Output] Immutable original failure/proof with precise technical coverage. -->
<!-- [Pos] Coordinator verification; no private configuration or real acceptance claim. -->
<!-- [Sync] 2026-09-15: retain original receipt below verbatim. -->

# Public Deck RuntimeData six-operation contract rerun receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- command: `python3 /private/tmp/ink-deck-runtime-domain/run-deck-runtime-data-contract.py`
- review: executed with the user-authorized scoped elevated permission for the provider-free public Route contract against the named isolated PostgreSQL. The private launcher handled credentials internally; no private file was read or printed.
- exit code: `0`
- result: PASS.

Captured stdout/stderr:

```text
{"result":"PASS","operations":6,"assertions":104,"fixture":"provider-free-isolated-restricted-roles","filesystem":"metadata-only; actual Dream artifact and CLI validation not claimed"}

```

The preceding failed run remains preserved at `/private/tmp/ink-deck-runtime-validation/public6-initial-failure.md`.

## Scope and cleanup

- Six public operations and 104 assertions ran, including the public Route and read-only receipt checks reported by the harness.
- No DDL, migration, fixture mutation, fault SQL, provider/model call, normal-account access, source/assertion change, external network, service change, or cleanup was performed.
- The harness explicitly reports filesystem validation as metadata-only; no Dream artifact or CLI validation is claimed.
