# Dream Deck Plugin Refs SQL Authority Retirement

## Optimized Prompt

You are the Dream/Admin cross-project Deck Plugin architect and Python refactoring engineer. Retire Dream's unused `DeckPluginRefService` SQL authority after proving that public Deck refs list/prepare/replace operations already use `AdminDeckRefsData`, strict Pydantic DTOs and Admin's typed Repository/Drizzle transactions.

Modify the Dream repository only. Delete `backend/services/claude_plugin/deck_refs_service.py`. Remove the historical integration-test fragment that directly instantiates this service and then exercises obsolete local refs, Chat context and Workflow routes. Preserve the active installation/list/readiness test, browser local-path rejection, production artifact digest and Claude CLI compatibility checks, public refs response shape, OAuth/scope/entity checks and unknown-write handling in the dedicated Admin consumer suites.

Do not modify current Admin operation names, capability hashes, public URLs, Runtime, SSE, shared files, installation semantics or active `PluginInstallService`. Do not replace the deleted service with SQL, a generic CRUD endpoint or a fallback.

Update folder contracts, current architecture ownership and the stage index. Keep historical task/exec documents unchanged as history. Validate repository-wide symbol absence, focused Admin refs/router tests, the retained active integration test, Python compilation/imports, Markdown references and the broad production database inventory.

## Optional Enhancers

- Record whether the old `database.replace_deck_claude_plugin_refs` helper still has a separate live caller before retiring it later.
- List remaining active Claude Plugin SQL modules for the next aggregate interface stage.

## USER REQUIREMENT

Continue the Admin-auth/database-access refactor. Database interfaces must follow strict DTO and ORM repository design; Dream production paths must not retain PostgreSQL credentials or database fallbacks.

## Execution Plan

| Item | Decision |
|---|---|
| Owner | Dream consumer branch; Admin owns Deck refs persistence and authorization |
| Evidence | No production import of `DeckPluginRefService`; public routes inject `AdminDeckRefsData`; dedicated Admin refs tests fence Dream `get_db` |
| Dependencies | Admin `deck-plugin-refs.list/prepare/replace`, identity/unified capabilities and local artifact/CLI verifier |
| Code scope | Delete unused SQL service and only its obsolete integration fragment |
| Contract changes | None to routes, DTOs, operation hashes, schemas or public errors |
| Preserved behavior | Active install/list/readiness, refs ordering/enabled values, artifact integrity, CLI compatibility and OAuth scope rules |
| Failure handling | Admin and local-verifier failures remain explicit; no Dream PostgreSQL fallback |
| Acceptance | Old symbol/import absent; Admin refs and active integration suites pass; inventory no longer lists this module |
| Remaining risk | `PluginInstallService`, marketplace/control-plane and `database.replace_deck_claude_plugin_refs` may retain separate active SQL callers |

## Verification Result

- Repository-wide Python search finds no remaining `deck_refs_service` or `DeckPluginRefService` reference; the deleted file is absent.
- Current Admin refs, public router, workspace-plugin, Chat-context and retained install/readiness integration suites pass: `65 passed in 1.39s`.
- Python compilation and imports for the public router, `AdminDeckRefsData` and local installation verifier pass.
- The broad structural inventory reports `production_database_access_modules=29` and `deck_refs_service_present=false`. Active installation, marketplace, workspace pack and control-plane SQL remain later migration work.
