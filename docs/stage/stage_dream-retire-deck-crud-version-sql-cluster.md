# Dream Deck CRUD and Version SQL Cluster Retirement

## Optimized Prompt

You are the Dream/Admin cross-project Deck data-boundary engineer. Retire the zero-production-caller Dream Deck CRUD, Voice CRUD, list/detail/sharing/default-reconciliation and content-version SQL implementations from `backend/database.py`, `services/deck/content_versioning.py` and the SQL projection portion of `services/deck/agent_type.py`. Public Dream Deck, Voice and content-version routes already consume registered Admin operations through strict Pydantic DTOs; Admin Services and typed Drizzle repositories own authorization, transactions, CAS, snapshot hashes and persistence.

Prove every removed Dream function has no production caller outside the legacy database module and tests. Preserve the pure published-manifest to `chat`/`dream` mapping, Dream route response projection, Admin capability/hash checks, request-owner propagation, unknown-write receipt recovery, shared artifact checks, Runtime dispatch, SSE and shared filesystem behavior. Keep the still-active built-in Deck Plugin backfill boundary as a separately tracked migration candidate.

Delete tests that execute Dream SQL as Deck or Voice authority. Strengthen provider-free public route and Admin DTO tests so list/detail/default/mutation/Voice/version normal flows, authorization, capability mismatch, conflict, no-change and unknown-result behavior remain covered. Do not recreate repositories in Dream, add a database fallback, accept client-supplied user IDs, split an Admin transaction into multiple calls or change public status/error payloads.

Update affected file headers, folder contracts, current architecture/design text and stage inventory. Historical documents remain unchanged. Validate import/symbol absence, DTO route suites, Python compilation, test collection, Markdown references and the production database inventory. Report the active SQL boundaries that remain.

## Optional Enhancers

- Use AST source gates to prove the public routes do not import Dream `database` or the retired content-version service.
- Treat dynamic f-string SQL in the inventory as SQL; do not undercount it because the first `execute` argument is an `ast.JoinedStr`.

## USER REQUIREMENT

Continue the Admin-auth/database-access refactor. Database interfaces must follow strict DTO → Service → ORM Repository design; Dream production paths must not retain PostgreSQL access or SQLite runtime fallbacks.

## Execution Plan

| Item | Decision |
|---|---|
| Owner | Admin Deck/Voice/version DTO operations own persistence; Dream owns route projection and pure Agent-type mapping |
| Evidence | `routers/voices.py` and `routers/deck_versions.py` use Admin data services; legacy SQL symbols have no production caller outside `database.py`; public AST tests fence legacy helpers |
| Dependencies | Registered Admin Deck/Voice/version operations, `AdminRequestOwner`, strict DTO hashes and existing receipt recovery |
| Code scope | Remove dead Deck/Voice/version SQL functions and tests; retain active built-in backfill; simplify `agent_type.py` to its pure mapper |
| Contract changes | No public endpoint, DTO, error, CAS, pagination, snapshot or receipt change |
| Transaction behavior | Admin typed repositories remain the only Deck/Voice/version UOW; Dream makes one typed business-operation call and never retries unknown non-idempotent writes blindly |
| Preserved behavior | list/detail/default/create/update/delete/fork/publish/sync, Voice mutations, version state/preview/commit/history/detail, Agent type, Runtime/SSE/shared files |
| Failure handling | Admin unavailable, capability mismatch, denial, conflict, no-change and unknown commit keep existing public projections; no Dream DB fallback |
| Acceptance | Retired symbols/imports absent; public Admin DTO route suites and collection pass; dynamic-SQL-aware inventory drops the cluster |
| Remaining risk | Built-in backfill, plugin installation/runtime materialization, Story Workspace and other tracked production SQL boundaries remain |

## Design Review

The production routes already satisfy the target DTO → Admin Service → typed Drizzle Repository ownership. Keeping unreachable Dream SQL and database-backed tests creates a second authority and hides regression risk. Removing that code and retaining public-contract tests is the minimum sufficient implementation.

## Verification Result

| Check | Command / Evidence | Result |
|---|---|---|
| Public Deck/Voice/version contracts | Focused `pytest` over all Admin Deck/Voice consumers, Agent-type/default policies and binding tests | Exit 0; 350 passed, 5 subtests passed |
| Direct affected contracts | Focused public/default/list/detail/mutation/Voice/version/Chat suite | Exit 0; 264 passed |
| Remaining legacy test compatibility | `pytest` over database/PostgreSQL service files | Exit 0; 14 passed, 3 opt-in skipped, 31 subtests passed |
| Test import closure | `PYTHONPATH=. .venv/bin/python -m pytest --collect-only -q tests` | Exit 0; 3719 tests collected; no deleted-module import remains |
| Compile and whitespace | `py_compile` for affected production/tests; `git diff --check` | Exit 0 |
| Dynamic-SQL-aware source inventory | `dream-db-closure-after-deck-crud-version-retirement-source-only.json` | 29→27 SQL modules; 480→402 SQL calls; retired owned symbols 0; parse errors 0 |

The active built-in Deck Plugin ref backfill remains in `database.py`, which still has 73 SQL calls under this stage's scanner. Plugin installation/materialization, Story Workspace and other inventory entries remain separate migrations; this phase does not claim complete Dream PostgreSQL removal.
