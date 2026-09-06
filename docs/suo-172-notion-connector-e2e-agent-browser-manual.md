<!-- [Input] Current Next.js Dream Web entry, Notion connector production interfaces, browser test harnesses, and real-business test rules. -->
<!-- [Output] Reproducible Notion connector browser acceptance procedure with explicit evidence and applicability boundaries. -->
<!-- [Pos] Current SUO-172 browser-validation manual; historical issue numbers identify evidence only, not dispatch state. -->
<!-- [Sync] 2026-09-06: align current commands and source ownership with Next.js, pnpm, and frontend/app/_dream. -->

# SUO-172 Notion resource connector browser acceptance manual

## 1. Background and problem

Earlier revisions treated the Vite development server, `npm run build`, and an
absolute checkout path as the current application contract. The checked-in Web
application now runs from the root Next.js project in `frontend/`, uses the
single `frontend/pnpm-lock.yaml`, and owns Dream browser modules below
`frontend/app/_dream/`.

Some browser specifications still use an isolated Vite process to mount a real
component tree with intercepted provider responses. That process is a test
harness only. It is not the application build, the deployment entry, or evidence
that the public Notion integration is enabled.

## 2. Goals and boundaries

The full business journey is:

```text
create connector -> authenticate -> select accessible resources -> synchronize -> attach to Chat context
```

The acceptance result must keep three evidence classes separate:

1. A provider-free browser contract uses intercepted responses and does not
   call Notion, the normal backend, or the business database.
2. A local application journey uses the normal Next.js and FastAPI public
   interfaces but may still stop at an external authorization dependency.
3. A real-business journey uses the user-selected account, the normal Dream,
   Admin, Gateway, and PostgreSQL services, and leaves normal Admin-visible
   records. Only this class can establish real-business acceptance.

An unavailable external authorization session is a blocking dependency. It is
not a frontend failure, and provider-free evidence must not be promoted to a
real-business result.

## 3. Current architecture and entry points

| Concern | Current entry |
|---|---|
| Next.js Web project | `frontend/` |
| Browser application modules | `frontend/app/_dream/` |
| Resource connector client | `frontend/app/_dream/api/resourceConnectorApi.ts` |
| Settings surface | `frontend/app/_dream/components/dashboard/ConnectorNotionDetailPage.tsx` |
| Browser specification | `frontend/e2e/notion-connector-settings.spec.ts` |
| Backend connector routes | `backend/routers/resource_connectors.py` |
| Normal local start | `./deploy/local/deploy.sh start` |

The normal local addresses remain configurable. The default local script uses
`http://127.0.0.1:5173` for the Next.js Web application and
`http://127.0.0.1:8765` for FastAPI.

## 4. Preparation

Read `AGENTS.md` before running a browser journey. Reuse the installed local
Chrome browser and perform only one lightweight launch check. Do not download a
second browser unless no compatible browser exists.

Install the current frontend dependency graph from its only lock file:

```bash
cd frontend
pnpm install --frozen-lockfile
```

For a normal local application journey, start the existing public paths:

```bash
./deploy/local/deploy.sh start
./deploy/local/deploy.sh verify
```

Do not stop or modify a user-owned service. The local deployment helper may stop
only processes recorded in its own process identifier files.

## 5. Provider-free component harness

`frontend/e2e/notion-connector-settings.spec.ts` currently mounts the real
Notion Settings component through a Vite-only harness and intercepts the
provider and backend responses. When this focused specification is required,
start a task-owned Vite process on an isolated port and point `E2E_WEB_BASE` to
that process. Record the exact command, process identifier, port, and cleanup.

Example commands from `frontend/`:

```bash
pnpm exec vite --host 127.0.0.1 --port 43170 --strictPort
E2E_WEB_BASE=http://127.0.0.1:43170 \
  pnpm exec playwright test e2e/notion-connector-settings.spec.ts \
  --reporter=line --workers=1
```

The Vite process in this section is legitimate harness infrastructure. A pass
proves the production-shaped component contract under intercepted data. It does
not prove the root Next.js build, a real Notion authorization, a database write,
or production availability.

## 6. Normal application browser journey

Use the running Next.js address for the application journey:

1. Open `http://127.0.0.1:5173` and verify that the Dream shell renders.
2. Confirm that the browser console identifies a Next.js application response
   and contains no application exception. Do not require Vite logs.
3. Open Story Workspace Settings and enter the resource connector surface.
4. Create a Notion connector through the visible interface.
5. Record the returned `connector_id`; it must come from the backend rather than
   a browser-generated placeholder.
6. Start authorization and record the external authorization address without
   storing authorization codes, tokens, cookies, or complete sensitive response
   bodies.
7. After authorization succeeds, select the minimum intended databases or pages
   and verify that `selected_databases` or `selected_pages` remains present in
   the backend response.
8. Trigger refresh and verify that the source card remains reachable in the
   visible scrolling surface.
9. Attach the selected source to the intended Chat context and verify the
   snapshot identity and `.notion` projection through the normal public path.
10. Refresh the page and verify that the server-owned state is recovered.

If authorization cannot complete, stop at the exact dependency, preserve the
non-sensitive evidence, and report which account, workspace access, or external
session is required. Do not substitute a local fixture and call the journey
complete.

## 7. Evidence record

Each run must report the following fields in full language:

| Field | Required content |
|---|---|
| Target | Application revision and the connector journey under test |
| Execution mode | Provider-free component harness, normal local application, or real-business journey |
| Command trace | Start, test, and cleanup commands with exit codes |
| State trace | Create, authorize, select, synchronize, attach, and refresh results |
| Artifacts | Screenshot paths, non-sensitive response summaries, and relevant identifiers |
| Validation result | Passed, failed, or blocked for each evidence class |
| Blocking dependency | The exact external state or user action required to continue |
| Evidence source | Process, endpoint, page, database receipt, or file that produced each claim |

Do not use a numerical equivalence score to replace field-level evidence. A
visible screen, a backend response, and a persisted record answer different
questions and must be reported separately.

## 8. Current validation commands

The frontend static checks use pnpm and the root Next.js project:

```bash
cd frontend
pnpm run lint
pnpm run build
```

The focused provider-free browser specification uses the command in section 5.
Backend contract checks must name the exact test files or test selectors that
were executed. Do not cite old `tests.test_*` names unless they still resolve in
the current test inventory.

## 9. Known evidence gaps

- The Notion Settings provider-free specification remains a Vite-only component
  harness and therefore does not prove the root Next.js application boundary.
- A real Notion authorization requires a valid external session and accessible
  workspace selected for the run.
- A provider-free browser result does not establish that a public deployment or
  real-business connector is enabled.
- Historical screenshots under `logs/qa/suo-172-*` are diagnostic records; they
  are not current acceptance unless their application revision and run metadata
  are recorded.

## 10. Related records

- [Backend connector evidence](exec/exec_190_notion_resource_connector_backend_e2e_evidence.md)
- [Historical frontend connector regression](exec/exec_191_frontend_resource_connector_e2e_regression.md)
- [General browser acceptance manual](agent-browser-e2e-test-manual.md)
