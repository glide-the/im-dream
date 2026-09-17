# Dream Session and Runtime Reconcile SQL Retirement

## Optimized Prompt

Remove the Dream-local Agent Session manager and Runtime Plugin reconcile service
after proving that both have zero production callers and that Admin Registry108 now
owns their complete persistence result. Delete only the unreachable SQL transaction
implementations and SQLite authority tests. Preserve the active Claude Agent
Runtime, local workspace launch-manifest verification, plugin artifact bytes, normal
Session resume/cancel behavior, EventBus/SSE, shared filesystem paths, and stable
public error responses. Keep Admin responsible for authorization, Run and Runtime
lock checks, materialization evidence, load receipt entries, Agent Session state,
queued-to-running CAS, replay, unknown-submit recovery, audit, and the single typed
Drizzle unit of work. Prove the removal with production import-graph scans, database
symbol scans, the Registry108 Dream consumer tests, affected Runtime regressions,
compile checks, and Markdown reference validation.

Optional enhancer: retain historical task and execution reports as dated records
while clearly marking the current Admin-owned transaction in live architecture docs.

## Evidence and Decision

- `SessionManager` had no production import or constructor after the local Runtime
  activation service was retired.
- `ReconcileService`, its CLI policy types, and its receipt writers likewise had no
  production import; only `test_runtime_plugin_reconcile.py` exercised them.
- The active Claude Agent path verifies the Dream workspace launch manifest and
  calls `AdminWorkflowRuntimeActivationProvider`.
- Registry108 already validates the Run, lock, installation, materialization and
  plugin identities and commits load receipt, Session, Run transition, operation
  receipt and audit through strict DTO → Service → typed Drizzle Repository layers.

## Ownership and Dependencies

| Concern | Current owner after change | Dependency |
| --- | --- | --- |
| local plugin bytes and launch manifest | Dream | workspace packer and launcher |
| activation authorization and persistence | Admin | Registry108 |
| Session/receipt/materialization transaction | Admin | typed Drizzle UOW |
| Agent Runtime and stream lifecycle | Dream | existing Claude Agent service |
| shared workspace and temporary directory | Dream | unchanged filesystem contract |

## Changes

- Delete `services/claude_agent/session_manager.py`.
- Delete `services/runtime_plugin/reconcile_service.py`.
- Delete their two SQLite authority suites.
- Update live folder and test inventories to identify Registry108 as the only
  activation persistence path.
- Do not add schema, migration, API, DTO, capability, environment variable, network
  endpoint, queue, or filesystem behavior.

## Failure and State Semantics

- Missing or invalid local manifest evidence continues to fail before Admin.
- Admin capability, authorization, timeout, or validation failures continue to stop
  the Runtime turn without a Dream SQL fallback.
- Replay and uncertain commit recovery remain inside Registry108.
- Runtime query, resume, cancel, EventBus/SSE and workspace operations are unchanged.

## Acceptance

1. No production file imports or constructs either retired class.
2. No retired module remains in the production package.
3. Registry108 provider, DTO projection and database-fence tests pass.
4. Relevant Runtime, launch, plugin and Workflow regression tests pass.
5. Python compilation, diff checks and Markdown local-reference checks pass.
