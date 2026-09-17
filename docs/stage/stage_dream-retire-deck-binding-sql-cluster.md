# Dream Deck Binding SQL Cluster Retirement

## Optimized Prompt

You are the Dream/Admin cross-project Deck architecture engineer. Retire the unused Dream SQL implementation cluster `BindingService` → `SelectionValidationService` → `CompatibilityService` plus `services/deck/runtime_context.py`. Production public binding, Agent-type and Dream launch paths already use Admin Registry122–129 strict DTO operations and Dream-owned shared-artifact/manifest/CLI verification.

Prove the four modules have no production caller, including imported aliases and composition roots. Delete only the duplicate SQL authority. Preserve public Pydantic request/response models, route status/error projections, capability intersection pure logic, Admin client DTO validation, original request IDs/receipts, local artifact verification, Runtime dispatch, SSE and shared filesystem behavior.

Rewrite mixed SQLite tests so public binding and Agent-type routes use a provider-free strict Admin fake that models current/history/options/validate/save/clear/runtime-plan/runtime-prepare operations. Preserve normal, stale-revision, access-denied, selection-rejected, local-verification and error-projection coverage. Keep pure capability evaluator/model tests; remove tests that establish SQLite as a binding, compatibility or capability-approval authority. Remove the retired CompatibilityService from PostgreSQL SQL-boundary parametrization while retaining active InstallationService and remaining production SQL checks.

Update affected file headers, folder contracts, current architecture/design text and stage inventory. Historical stage documents remain unchanged and serve only as history. Do not add a database fallback, generic CRUD endpoint, client-supplied identity, new status machine, environment-based business branch or local Runtime placement path.

Validate symbol/import absence outside historical documentation, provider-free public route tests, Registry122–129 client tests, Agent-type local verifier tests, model/capability tests, Python compilation, Markdown references and the production database inventory. Record remaining active Deck Plugin SQL boundaries separately.

## Optional Enhancers

- Use one in-memory fake at the Admin DTO boundary so route tests exercise the production public contract without reproducing Drizzle transactions.
- Keep exact public error details for `BINDING_REVISION_CONFLICT` and `SELECTION_NOT_ALLOWED`.

## USER REQUIREMENT

Continue the Admin-auth/database-access refactor. Database interfaces must follow strict DTO → Service → ORM Repository design; Dream production paths must not retain PostgreSQL access or SQLite runtime fallbacks.

## Execution Plan

| Item | Decision |
|---|---|
| Owner | Admin Registry122–129 owns binding/selection/runtime persistence; Dream owns route projection and local artifact verification |
| Evidence | Production routes import `AdminDeckPluginBindingData`; launch uses the same DTO client; the four legacy services are referenced only by each other and legacy tests; an existing AST gate forbids them in active Agent-type code |
| Dependencies | Registry122–129 capabilities, `AdminRequestOwner`, binding public models, `verify_agent_type_runtime` |
| Code scope | Delete four legacy SQL modules; replace SQLite adapters/tests with provider-free Admin fake; retain pure capability evaluator tests |
| Contract changes | None to public endpoints, DTO hashes, Admin operations, errors, status transitions or receipt rules |
| Transaction behavior | Admin typed repositories remain the sole CAS/UOW implementation; Dream tests assert DTO behavior and never emulate transaction commits |
| Preserved behavior | current/history/options/validate/save/clear, revision conflict, selection rejection, Chat/Dream Agent-type switch, local artifact verification |
| Failure handling | Admin unavailable/capability mismatch/permission errors remain mapped by existing route; no Dream DB fallback |
| Acceptance | Four legacy modules and imports absent; provider-free tests pass; production DB inventory drops the SQL cluster |
| Remaining risk | Active plugin installation, revocation, rollback, materialization, workspace packing and Admin gateway SQL remain separate migrations |

## Design Review

The current production design already satisfies the target ownership for this cluster. Reimplementing the deleted SQL in Dream would create a second transaction authority. The minimal sufficient change is to remove the unreachable services and rewrite their tests against the published Admin DTO boundary while retaining the pure capability algorithm.

## Verification Result

| Check | Command / Evidence | Result |
|---|---|---|
| Focused Deck Plugin contracts | `cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q` over Admin binding DTO, Agent-type policy/local verifier, public binding, plugin admin/install/lock/manifest/compatibility and PostgreSQL-boundary suites | Exit 0; 62 passed, 16 subtests passed |
| Downstream Admin/launch/Chat | focused run over Dream launch Runtime, Admin default/list/detail/mutations and public Chat routes | Exit 0; 176 passed |
| Test import closure | `cd backend && PYTHONPATH=. .venv/bin/python -m pytest --collect-only -q tests` | Exit 0; 3746 tests collected; no deleted-module import remains |
| Whole backend collection diagnostic | unscoped `pytest --collect-only -q` | Deleted-module imports closed; separate optional built-in investment Skill collection still lacks `pandas` |
| Compile/import/static boundary | `py_compile`, exact import search and `git diff --check` | Exit 0; no production/test import of the four deleted modules |
| Production DB inventory | AST scan for production database imports and literal SQL calls | 21 remaining modules, down from 25; the four retired modules are absent |

The remaining active Deck Plugin persistence includes installation, revocation, rollback, materialization/reconcile, workspace packing, built-in provisioning and `admin_gateway.py`. The dynamic SQL projection in `services/deck/agent_type.py` is reached only from legacy `database.py` helpers and is tracked with that database closure rather than hidden by this retirement.
