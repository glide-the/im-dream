# Dream Deck Plugin Release SQL Authority Retirement

## Optimized Prompt

You are the Dream/Admin cross-project Deck Plugin architect and Python refactoring engineer. Retire Dream's unused PostgreSQL `DeckPluginReleaseService` after proving that no production module imports its class or module-level database wrappers and that Admin already owns release/runtime-lock persistence through strict DTO services, typed repositories and the Admin Drizzle schema.

Modify the Dream repository only. Delete `backend/services/deck_plugin/release_service.py` and remove only the obsolete SQLite integration tests coupled to that service. Preserve the independently useful `manifest_validator`, `LockGenerator`, version-constraint, marketplace-failure, digest and lock-immutability tests. Do not alter the active Deck Plugin installation/control-plane routes, shared artifact verification, Runtime materialization, Admin schema or public API behavior.

Update affected folder documentation, the current architecture inventory and this stage record. Preserve historical task/exec documents and prior migration evidence as history. Add structural validation that no production source imports the deleted service or calls its former default-database wrappers.

Validate the retained pure manifest/lock suite, active Admin Deck Plugin consumer/control-plane suites, Python import/compile checks, Markdown references and the production database-access inventory. Explicitly distinguish retirement of unreachable code from migration of the still-active `admin_gateway.py`, installation, rollback and runtime materialization paths.

## Optional Enhancers

- Record the exact remaining Deck Plugin SQL modules for the next interface-migration phase.
- Compare active route dependencies against the published Admin operation catalog before selecting the next stage.

## USER REQUIREMENT

Continue the Admin-auth/database-access refactor. Database interfaces must follow strict DTO and ORM repository design; Dream production paths must not retain PostgreSQL credentials or database fallbacks.

## Execution Plan

| Item | Decision |
|---|---|
| Owner | Dream consumer branch; Admin remains release/lock persistence owner |
| Evidence | Repository-wide symbol search finds no production import outside the service itself; only two legacy SQLite test classes instantiate it |
| Dependencies | Existing Admin Deck Plugin repositories/operations and Admin Drizzle release/lock tables |
| Code scope | Delete the unused SQL service; remove its SQLite-only tests; retain pure manifest and lock generation tests |
| Contract changes | None to HTTP routes, Admin DTOs, capability hashes, manifest schema or runtime lock model |
| Preserved behavior | Active install/enable/disable/upgrade/rollback/readiness flows, shared artifact checks and Runtime behavior |
| Failure handling | Active Admin calls remain fail closed; no replacement Dream database fallback is introduced |
| Acceptance | No retired symbol/import remains; retained pure tests and active control-plane tests pass; database inventory drops the release service |
| Remaining risk | Active `admin_gateway.py` and installation/rollback services still contain SQL and require later DTO migration |

## Verification Result

- Repository-wide Python search finds no remaining `release_service`, `DeckPluginReleaseService`, `publish_with_lock` or `validate_release` reference; the deleted file is absent.
- Retained manifest/lock rules and active Deck Plugin/Admin consumer suites pass: `122 passed, 2 skipped, 27 subtests passed in 2.63s`.
- Python compilation and imports for `lock_generator`, `manifest_validator`, active `admin_gateway` and `installation_service` pass.
- The broad structural inventory reports `production_database_access_modules=30` and `release_service_present=false`. This stage removes one unreachable SQL module and does not claim that the remaining active Deck Plugin SQL paths are migrated.
