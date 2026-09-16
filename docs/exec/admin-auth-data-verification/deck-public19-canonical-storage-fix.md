<!-- [Input] Actual captured command/cwd/exit/stdout from the named validation stage. -->
<!-- [Output] Sanitized technical evidence retaining unchanged failures and coverage limits. -->
<!-- [Pos] Coordinator evidence; excludes private fixture/config and real acceptance claims. -->
<!-- [Sync] 2026-09-15: preserve the original captured receipt below verbatim. -->

# Deck/Voice canonical-storage public contract receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- no credentials/private configuration were read or printed.
- no raw SQL, DDL, migration, fixture/setup, normal-account, provider/model, external network, service, or cleanup action was performed.

## Public contract

Command: `python3 /private/tmp/ink-auth-migration-validation/run-deck-contract.py`

Review: `sandbox_permissions=require_escalated`; approved for the named isolated ACL PostgreSQL and provider-free public Route contract.

Exit: `0`

Captured stdout/stderr:

```text
PUBLIC DECK VOICE CONTRACT PASS: operations=19; assertions=246; restricted-pools/DTO/owner/atomic-default/fork/sync/revision/CAS/raw-numeric-hash/receipt; provider-free

```

## TypeScript

Command: `pnpm exec tsc --noEmit --pretty false --incremental false`

Exit: `0`; stdout/stderr empty.

## Focused lint

Command: `pnpm exec eslint --no-cache app/lib/dream/deckVoiceRepository.ts app/lib/dream/deckVoiceService.ts tests/integration/adminDeckVoice.contract.ts`

Exit: `0`; stdout/stderr empty.

No previously passing 39-unit or old 14-operation checks were rerun. No cleanup was performed.
