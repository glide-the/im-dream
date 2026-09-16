<!-- [Input] Captured source-oracle or Luna command/cwd/exit evidence. -->
<!-- [Output] Original sanitized Social9 pass/failure and shared type gate. -->
<!-- [Pos] Named isolated technical validation; no normal Google/account/model acceptance. -->
<!-- [Sync] 2026-09-15: retain original receipt below verbatim. -->

# Social Friendship public9 preflight receipt

- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- scope: requested tsc and Social9 harness ESLint preflight.

## TypeScript preflight

- command: `pnpm exec tsc --noEmit --incremental false`
- exit code: `2`
- result: failed on a concurrent non-Social file, so the public9 contract launcher was not started.

Captured stdout/stderr:

```text
app/lib/dream/deckPluginCompatibilitySource.test.ts(33,21): error TS2352: Conversion of type '{ known_capabilities: Set<string>; deck_host_compatible: boolean; claude_agent_compatible: boolean; story_schema_compatible: boolean; deck_runtime_config_compatible: boolean; ... 5 more ...; deprecated_release_allowed_by_policy: boolean; }' to type 'DeckRuntimeContext' may be a mistake because neither type sufficiently overlaps with the other. If this was intentional, convert the expression to 'unknown' first.
  Type '{ known_capabilities: Set<string>; deck_host_compatible: boolean; claude_agent_compatible: boolean; story_schema_compatible: boolean; deck_runtime_config_compatible: boolean; ... 5 more ...; deprecated_release_allowed_by_policy: boolean; }' is not comparable to type '{ deck_runtime_snapshot_policy: Set<string>; user_and_workspace_grants: Set<string>; claude_agent_runtime_supported: Set<string>; materialized_runtime_plugin_ids: Set<...>; loadable_runtime_plugin_ids: Set<...>; known_capabilities: Set<...>; deprecated_release_allowed_by_policy: boolean; }'.
    Types of property 'deck_runtime_snapshot_policy' are incompatible.
      Type 'string[]' is missing the following properties from type 'Set<string>': add, clear, delete, has, and 9 more.
```

## Harness ESLint

- command: `pnpm exec eslint tests/integration/adminSocialFriendship.contract.ts`
- cwd: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`
- exit code: `0`
- stdout/stderr: empty.

## Public contract status

The requested command `python3 /private/tmp/ink-auth-migration-validation/run-social-friendship-contract.py` was **not executed** because the required tsc preflight failed. No Social9 business assertion result is claimed.

## Scope and cleanup

No source, assertion, fixture, schema, DDL, SQL fault, database, real account, provider/model, network, service, or cleanup action was performed. Private fixture/token/environment files were not read or printed.
