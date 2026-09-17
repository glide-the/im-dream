# Dream Preflight SQL Authority Retirement

## Optimized Prompt

You are the Dream/Admin cross-project workflow architect and Python refactoring engineer. Retire Dream's duplicate PostgreSQL Workflow Preflight authority after verifying that every production caller already uses Admin's published `workflow-preflight.execute` and `workflow-preflight.read` operations.

Use the existing evidence: the public POST and GET routes construct strict `PreflightExecutionInputDTO` / `PreflightInputDTO` values and invoke `AdminPreflightData`; the Dream launch application uses `AdminDreamLaunchWorkflowOperations`, including original-request receipt recovery; the only remaining `PreflightService` builder caller is the legacy `StoryWorkflowRunApplicationService` method pair, which is no longer wired to a production route. Admin owns the eight checks, token issuance, persistence, concurrency and original-request recovery through DTO → Service → typed Repository → Drizzle-managed schema.

Modify the Dream repository only. Remove the unused Dream `PreflightService`, its SQL-dependent builder and its obsolete SQLite unit test. Remove the corresponding imports and unreachable create/read methods from the legacy Story workflow application service. Keep Workflow Run, Dream Runtime, EventBus, SSE, filesystem behavior and all remaining application methods unchanged. Do not add a replacement database client, SQL fallback, test-only production branch or a second Preflight state machine.

Update the affected file headers, folder contracts, current architecture documentation and indexes. Preserve historical task and execution records as history; add a current-state correction rather than rewriting historical evidence.

Validate with focused public Preflight, launch and router tests, Python compile/import checks, Markdown link checks and a structural source gate proving production code no longer imports the retired service or builder. Confirm the public routes still serialize the same DTOs and status/error responses, Admin unavailability fails closed, and the launch path still performs source → Preflight → Run → dispatch in the existing order.

## Optional Enhancers

- Re-run the production database inventory and record the reduced set of Dream PostgreSQL modules.
- Include a source assertion that all `workflow-preflights` route handlers depend on `AdminPreflightData`.

## USER REQUIREMENT

Continue the Admin-auth/database-access refactor. Database interfaces must follow strict DTO and ORM repository design; Dream production paths must not retain PostgreSQL credentials or database fallbacks.

## Execution Plan

| Item | Decision |
|---|---|
| Owner | Dream consumer branch; Admin producer already published and validated |
| Dependencies | Admin `workflow-preflight.execute`, `workflow-preflight.read`, original receipt endpoint, identity/unified/request schema capabilities |
| Files read | Dream public route, launch infrastructure, legacy application service, Preflight service/builder/tests, folder contracts and current Preflight design |
| Code scope | Remove unused SQL service/builder and unreachable legacy methods/imports; add source-boundary regression coverage |
| Contract changes | None to HTTP, DTO, capability hash, token format, status code or Admin operation |
| Preserved behavior | Public POST 202, owner-scoped GET, unknown-result recovery, Launch ordering, Runtime/SSE/filesystem and Workflow Run behavior |
| Failure handling | Capability/auth/Admin failures remain explicit and fail closed; no Dream database retry or fallback |
| Acceptance | Focused tests pass; production imports contain no retired Preflight symbols; database scan no longer lists the removed service/builder |
| Risk | Hidden dynamic import of the legacy builder; mitigate with repository-wide symbol scan and application/router tests |

## Verification Result

- Removed `backend/services/workflow/preflight_service.py`, `backend/services/story_workspace/preflight_builder.py` and the SQLite authority test. Repository-wide Python symbol search finds no remaining import or reference to the retired classes.
- Removed the unreachable `StoryWorkflowRunApplicationService.create_preflight/get_preflight` methods. Public POST/GET remain implemented by `AdminPreflightData`; Dream Launch remains implemented by `AdminDreamLaunchWorkflowOperations`.
- Focused command passed: `295 passed in 3.85s`.
- Broader Story/Workflow command passed after excluding only three files that require the absent `vendor/drama-forge` fixture: `496 passed, 4 skipped, 181 subtests passed in 8.49s`.
- The unfiltered broader command produced `871 passed, 4 skipped` and six fixture `FileNotFoundError`/empty-catalog failures, all under the three excluded vendor-dependent test files; no product assertion failed.
- The structural production scan now reports 31 SQL/import modules under the broad DTO-migration inventory; the deleted service and builder are both absent. Remaining modules are subsequent migration or dead-path retirement work; this stage does not claim full Dream database closure.
