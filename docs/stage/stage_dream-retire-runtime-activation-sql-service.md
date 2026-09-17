# Dream Runtime Activation SQL Retirement

## Optimized Prompt

Retire the Dream-local Story Workspace Runtime activation persistence service after
confirming that the production Claude Agent path already uses Admin Registry108.
Keep Dream responsible for reading and validating the frozen workspace launch
manifest, invoking the typed Admin provider, mapping bounded product failures, and
continuing the existing Agent Runtime and SSE flow. Keep Admin responsible for the
Run, Runtime lock, materialization, load receipt, Agent Session, transaction,
authorization, replay, and audit records through strict DTO → Service → typed
Drizzle Repository layers. Delete the zero-production-caller SQL implementation and
its SQLite authority tests. Do not change workspace paths, plugin digest semantics,
turn ordering, Session resume behavior, Runtime execution, or streaming events.
Prove the result with call-graph evidence, provider contract tests, fail-closed tests,
source fences, focused unit tests, compile checks, and Markdown reference checks.

Optional enhancer: compare the removed local transaction's externally observable
success and replay results with the existing Registry108 output DTO contract.

## Goal and Evidence

- `ClaudeAgentService` calls `_activate_story_workspace_dream_runtime`, which reads
  the local launch manifest and invokes `AdminWorkflowRuntimeActivationProvider`.
- The Admin consumer pins `workflow-runtime.activate` Registry108 and validates the
  strict input/output DTO pair before returning.
- `StoryWorkspaceDreamRuntimeActivationService` had no production caller. Its only
  consumer was the SQLite test that treated Dream as the Run/receipt/session writer.
- The production provider test already fences `database.get_db` and verifies that
  physical plugin paths never cross the Admin interface.

## Ownership and Dependency

| Concern | Owner | Dependency |
| --- | --- | --- |
| launch-manifest read and digest evidence | Dream | existing workspace packer and launcher |
| activation DTO, authorization and transaction | Admin | Registry108 |
| Run/receipt/session/materialization persistence | Admin | typed Drizzle Repository and UOW |
| Runtime continuation and SSE | Dream | existing Claude Agent service |
| stable user-facing activation failure | Dream | pure error contract |

## File and Contract Changes

- Reduce `dream_runtime_activation_service.py` to stable error codes and exception.
- Delete the SQLite authority test for the retired SQL implementation.
- Replace the obsolete constructor-shape test with a source fence proving that no
  local activation persistence service or SQL collaborators remain.
- No API, capability, schema, migration, path, Cookie, token, or configuration
  change is required.

## Preserved Behavior and Failure States

- Valid manifest fields remain `package_spec`, `resolved_version`,
  `artifact_digest`, and `has_manifest`.
- Missing provider, malformed manifest, rejected Admin operation, timeout, or
  capability failure still fails before the Runtime turn continues.
- Admin owns replay and unknown-submit recovery; Dream never falls back to SQL.
- Runtime, SSE, thread workspace, shared files, and Claude temporary directories are
  unchanged.

## Acceptance

1. Production call graph contains no constructor call for the removed service.
2. Registry108 provider tests prove the exact DTO projection and database fence.
3. Missing provider and Admin rejection remain bounded failures.
4. The activation contract source contains no SQL collaborator or execute call.
5. Focused tests and compile checks pass; Markdown local references resolve.
