# Ink-Dream Playwright project workflow

## Contents

1. [Repository facts](#repository-facts)
2. [Dream business concepts and impact scope](#dream-business-concepts-and-impact-scope)
3. [Runtime lanes](#runtime-lanes)
4. [Authentication and navigation](#authentication-and-navigation)
5. [Selectors and readiness](#selectors-and-readiness)
6. [Visual matrix](#visual-matrix)
7. [SubAgent fixtures](#subagent-fixtures)
8. [Console and network audit](#console-and-network-audit)
9. [Cleanup](#cleanup)
10. [Command reference](#command-reference)

## Repository facts

- Frontend root: `frontend/`
- Backend root: `backend/`
- Web origin: `http://127.0.0.1:5173`
- API origin: `http://127.0.0.1:8765`
- Backend entry: `backend/server.py`
- Backend Python: `backend/.venv/bin/python`
- Browser package: `frontend/node_modules/@playwright/test`
- Vite proxies `/api`, `/auth`, `/oauth`, and `/polycli` to port 8765.
- The repo has no root Playwright config; run commands from `frontend/` and specify focused files explicitly.
- Existing browser specs live in `frontend/e2e/`. Many source-level contract tests also use the Playwright test runner under `frontend/src/**/__tests__/`.
- Browser specs use the full Chromium channel with `test.use({ channel: 'chromium' })`.
- Screenshots under `output/` are gitignored.

Use `npx playwright test`, not `playwright-cli`. A Codex Playwright/MCP wrapper may be unavailable even while the repository-local package works correctly.

## Dream business concepts and impact scope

Define the scenario in business terms before opening a browser or invoking a
model. The following boundaries are independent even when an initial project
uses the same text for several titles:

| Concept | Authority | Meaning | Primary consumers |
| --- | --- | --- | --- |
| Project | `stories/<project-id>/project.yaml` | workspace-level identity; `project_name` is the Project display title | PostgreSQL Story title, Story Index API `projectTitle`, Execution page level-1 heading |
| Episode | `stories/<project-id>/episodes/<EPxx>/` | one episode's narrative identity and production artifacts | Episode Artifact API, EP navigation, Episode execution heading and readers |
| Canonical Artifact | files under `stories/` | current Agent-authored business fact | after-turn Hook input |
| Run-private Artifact | `.dream/runtime/runs/<run-id>/artifact/` plus manifest | immutable-by-client publication of current canonical facts for one Run | server readers, binding, materializer |
| Story projection | PostgreSQL row materialized from current Project/Episode files | queryable business projection, not a second authoring source | Story Index API and page Project heading |
| Observer projection | non-controlling workflow/status observation | diagnostics and derived business status only | secondary panels; never canonical files or Agent lifecycle |

The successful main-turn Hook owns deterministic synchronization after any
Skill or ordinary Agent turn. MCP write/validation tools help the Agent create
correct files, but they do not replace the Hook and do not prove publication or
database materialization.

Before test execution, capture a baseline and fill an impact matrix:

| Fact/surface | Baseline | Expected after turn | Classification | Evidence |
| --- | --- | --- | --- | --- |
| Project title | current `project_name` | requested Project title | changes | canonical/private SHA, DB, API, page h1 |
| EPxx title | current Episode artifact title | same unless explicitly requested | must remain unchanged | Episode files/API/page heading |
| Thread/session | current ids | same ids with a new turn | must remain unchanged | persisted thread and Claude session |
| Other Episodes/assets | current revisions | same unless explicitly requested | out of scope | manifest/revisions |

Never write an assertion against the phrase “the title” without first mapping
it to Project or a named Episode. In the current Workbench contract, a request
to change the project title maps to `project.yaml.project_name`; it must update
the Project consumers but leave EP01 narrative content unchanged. If a user
intends a series-wide or Episode rewrite, the dialogue and expected artifact
set must say so explicitly.

## Runtime lanes

### Real business lane

When the user asks for real data, a real model, or an existing Run, use the
normal local Dream, Admin, Gateway, PostgreSQL, named account, installed Deck,
and public UI/API path. Confirm ownership read-only before interaction. Do not
clone files or databases, stage a lookalike Run, or use an isolated receipt that
cannot be found in the user's normal Admin.

Define the expected dialogue before execution:

| Turn | Visible user request | Agent/tool expectation | Canonical and Hook expectation | DB/API expectation | Visible page expectation | Must remain unchanged |
|---|---|---|---|---|---|---|
| 1 | Realistic business mutation | Same Thread resumes; only expected tools are confirmed | Canonical fact changes; Hook publishes current facts | Authoritative projection reflects the change | Actual consumer route shows the new value | all out-of-scope Project/Episode facts |
| 2 | Follow-up correction or continuation | Prior context is understood without restating the story | Hook republishes or performs an idempotent no-op | Projection remains revision-consistent | Reloaded page remains correct | thread/session identity |
| 3 | Read-only continuity question | Workbench context is read again; no write confirmation | No file or revision mutation | DB/API facts remain unchanged | Project and Episode semantics remain visible | all files and revisions |

After each Agent terminal, validate that row before sending the next message.
Matching canonical and private SHA values proves only the file boundary; the
database-backed API and actual consumer page must also pass.

The visible utterance column must contain normal page language, for example
“加一个叫小岚的场记”“把刚才的雨棚写成雨夜”“删掉刚才那个人物”“第一集最后那个镜头不要
了”. It must not contain an Agent-facing `char_id`, `scene_id`, `shot_id`,
absolute path, filename, contract-read instruction, exact `rm` command, Hook,
or `.dream` implementation detail. Discover those facts after the first turn
and use them only in assertions or confirmation allowlisting.

For character/scene/prop/storyboard collaboration, define the entire conversation
before the first browser action. The minimum complete journey is:

1. add one uniquely named temporary character, one temporary scene, one
   temporary prop, and one temporary storyboard shot that references them;
2. update all four while retaining their canonical IDs and paths;
3. request deletion while references exist and verify the Agent removes or
   resolves references atomically (or asks a visible clarification question);
4. delete the remaining temporary shot/assets and prove the baseline has been
   restored.

For file deletion, require the matching Bash invocation to finish with
`output-available` and zero exit status before accepting canonical absence.
This catches the case where `rm` executes but Claude Code later reports a
`cwd-*` shell-hook error; the UI must never tell a user that such a turn
succeeded or failed inconsistently with its persisted tool receipt.

After every turn, inspect the persisted assistant tool parts and require Reads
of both `.dream/WORKBENCH.md` and `.dream/ASSET-COLLABORATION.md`. Then compare
canonical files, Hook stage revisions, the authenticated `dream-files` API,
and the visible Execution Assets/Outline views. Do not postpone all assertions
until the final cleanup turn. Real-data cleanup must be another visible Agent
turn on the same Thread, never a direct filesystem or SQL rewrite.

### Technical isolated lane

Use a temp database because `/api/register`, thread creation, Deck binding, and preferences mutate SQLite. Use a temp Agent root because workspace lookup depends on the backend process environment.

```bash
qa_runtime="$(mktemp -d)"
mkdir -p "$qa_runtime/workspaces"

INK_DATABASE_PATH="$qa_runtime/ink.db" \
AGENT_CWD="$qa_runtime/workspaces" \
backend/.venv/bin/python backend/server.py
```

The environment must be present when Python imports `database.py` and workspace modules. Setting it after server startup is too late.

Start Vite from `frontend/`:

```bash
npm run dev -- --host 127.0.0.1
```

Before starting either service:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

If a port is occupied, inspect the PID, command, and working directory. Reuse it only when its database/workspace configuration matches the test. Otherwise stop it only with clear ownership.

Use this lane only for provider-free repeatable contracts, destructive cases,
migrations, or fault injection. Never report it as real business or real-model
acceptance.

## Authentication and navigation

Prefer API registration and localStorage seeding:

```ts
const registration = await request.post(`${API_BASE}/api/register`, {
  data: {
    email: `qa-${Date.now()}@example.test`,
    password: 'ink-dream-e2e',
    display_name: 'Ink-Dream E2E',
  },
});
expect(registration.ok()).toBeTruthy();
const { token } = await registration.json() as { token: string };

await page.addInitScript((authToken) => {
  localStorage.setItem('auth_token', authToken);
  localStorage.setItem('migration_completed', 'true');
}, token);
```

Register before `page.goto()`. Do not fill the login UI unless login itself is under test.

The Writing surface contains an expanded state chooser when no daily state exists. It can intercept pointer events over the top navigation. For a test that only needs another view:

```ts
const chat = page.getByTitle('Chat');
await chat.focus();
await chat.press('Enter');
```

For a state chooser test, click `Happy`, `OK`, or `Unhappy`, wait at least for the expanded prompt `How are you feeling today?` to become hidden, and then assert the editor. Do not wait for `OK` itself to become hidden; the collapsed chooser retains the selected state's label.

For route-backed surfaces, prefer direct navigation such as `/story-workspace/dream`.

## Selectors and readiness

Selector priority:

1. `getByRole()` with accessible name
2. `getByLabel()`
3. `getByTitle()`
4. stable `data-*` contract
5. exact visible text
6. CSS only for structural measurement

Avoid `force: true`. It hides overlays, stale state, and layout defects. Keyboard activation is acceptable when it is the intended accessibility path or the known Writing overlay is irrelevant to the feature.

For headed QA, declare both a bounded Chromium outer window and a deterministic
content viewport that fit the current desktop. Do not rely on maximize or zoom.
Assert `document.documentElement.scrollWidth <= clientWidth + 1` and require the
scenario heading, primary action, and any blocking dialog to be in the viewport
before interacting with them. A panel's intentional internal vertical scroll is
not a failure.

Use web-first assertions:

```ts
await expect(page.getByTitle('Subagents')).toBeVisible();
await page.getByTitle('Subagents').click();
await expect(page.locator('[data-subagent-view="list"]')).toBeVisible();
await expect(page.getByTitle('Subagents')).toHaveAttribute('aria-expanded', 'true');
```

### Human business journey rule

Structure business E2E cases in the order a normal user experiences them:

1. Open the visible feature page and confirm its identity.
2. Make required choices with labeled controls.
3. Enter realistic business input and submit through the visible primary action.
4. Observe the visible running state, streamed output, confirmation, or other
   progress the user relies on.
5. If a visible tool confirmation blocks the turn, identify the displayed tool
   and use the labeled controls to make the scenario's explicit decision. Never
   approve an unknown/Bash/network operation merely to advance the test, and do
   not answer AskUserQuestion without case-specific input.
6. Treat the visible Agent/Thread stop as terminal and immediately inspect the
   resulting business state.
7. Use authenticated API reads only to corroborate Thread identity,
   persistence, workflow state, or artifacts behind the already-exercised UI.
8. For each visible mutation, assert the canonical source, after-turn Hook,
   private publication when present, PostgreSQL projection, public API, and the
   final consuming page before continuing to the next dialogue.

For Dream, if the shared Thread has at least one completed turn and
`running=false`, do not keep polling characters/scenes/storyboards merely
because FastAPI, Vite, Admin, PostgreSQL, or an SSE reconnect loop is alive.
Assert the currently visible/persisted stages immediately; incomplete output is
a business failure. A fixed sleep or a longer Artifact timeout cannot convert a
stopped Agent into a running Dream workflow.

For a 250ms sidebar width transition, wait on the semantic state first, then poll until two consecutive bounding-box widths are equal. A bounded delay of about 350ms is an acceptable fallback after the semantic assertion; long sleeps are not a readiness strategy.

For resize QA, verify all paths:

```ts
const separator = page.getByRole('separator');
const initial = Number(await separator.getAttribute('aria-valuenow'));
await separator.focus();
await separator.press('ArrowLeft');
expect(Number(await separator.getAttribute('aria-valuenow'))).toBeGreaterThan(initial);
// Perform a pointer drag using boundingBox() and page.mouse.
await separator.dblclick();
await expect(separator).toHaveAttribute('aria-valuenow', String(initial));
```

## Visual matrix

Cover only dimensions relevant to the change, but for shared Chat or navigation UI include:

- light and dark;
- English and Chinese;
- wide and narrow viewport;
- short and long content;
- Markdown heading, list, link, inline code, and code block;
- loading, running, completed, failed, cancelled, and empty states when applicable;
- keyboard focus and resize interaction;
- no extra vertical scroll container.

Switch theme and language live when reloading would reopen unrelated boot UI:

```ts
await page.evaluate(async () => {
  const [{ default: i18n }, theme] = await Promise.all([
    import('/src/i18n.ts'),
    import('/src/utils/theme.ts'),
  ]);
  await i18n.changeLanguage('zh');
  theme.setThemeMode('dark');
});
```

This is appropriate for visual QA. Use actual UI controls when testing preference controls or persistence.

Take screenshots only after assertions. Use descriptive paths such as:

```ts
await page.screenshot({
  path: 'output/playwright/subagent-detail-dark-zh-narrow.png',
  fullPage: true,
});
```

## SubAgent fixtures

The SubAgent projection scans:

```text
{AGENT_CWD}/{threadId}/.claude-home/projects/**/subagents/*.meta.json
{AGENT_CWD}/{threadId}/.claude-home/projects/**/subagents/*.jsonl
```

Create the authenticated thread through the real API first. Then stage deterministic records:

```bash
python3 .agents/skills/ink-dream-playwright-qa/scripts/stage_subagent_fixture.py \
  --workspace-root "$qa_runtime/workspaces" \
  --thread-id "$thread_id"
```

The helper creates completed, running, failed, and cancelled tasks with Markdown, a paired tool call/result, and a redacted credential field. It refuses to overwrite existing fixture files.

Its expected API counts are fixed:

```json
{"running": 1, "completed": 1, "ended": 2, "total": 4}
```

Verify the backend process sees the same root before opening the UI:

```bash
curl -sS \
  -H "Authorization: Bearer $token" \
  "http://127.0.0.1:8765/api/claude-agent/threads/$thread_id/subagents"
```

Require `exists: true` and the expected task count. If the standalone projection sees files but the API returns `exists: false`, the running backend has a different `AGENT_CWD` or is a stale listener.

In the UI assert:

- compact rows for all terminal states;
- task dispatch precedes assistant/tool/final records;
- tool call and result are paired;
- `[redacted]` appears and the original secret does not;
- final content appears once;
- detail contains no `textarea` or chat composer;
- list/detail share a single sidebar scroll area.

Treat rows as compact when an ordinary row is about 60–72px, a row with a summary is at most 80px, and every row remains within the sidebar bounds. For scroll ownership, count descendants where `scrollHeight > clientHeight + 1` and computed `overflowY` is `auto` or `scroll`; the sidebar body should be the only vertical scroller.

## Console and network audit

Install listeners before navigation:

```ts
const diagnostics: string[] = [];
page.on('console', (message) => {
  if (message.type() === 'error') diagnostics.push(message.text());
});
page.on('pageerror', (error) => diagnostics.push(error.message));
page.on('requestfailed', (request) => {
  diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
});
```

Do not discard all startup errors. If the test intentionally uses the login UI, separate pre-auth bootstrap diagnostics from feature diagnostics only after authenticated readiness is asserted.

Classify failures:

- Ink-Dream JS exceptions, failed `/api` requests, React errors: fail the test.
- requests to `react-grab.com`, `fonts.googleapis.com`, or `fonts.gstatic.com`: record as external diagnostics; do not misreport them as feature regressions.
- unexpected external errors: investigate before filtering.

On the final verification run, require zero application diagnostics.

## Cleanup

Use `try/finally`, test hooks, or managed terminal session cleanup.

1. Close browser/context.
2. Stop owned Vite and FastAPI sessions.
3. Check ports and terminate only verified orphan children.
4. Remove the exact temp runtime created with `mktemp -d`.
5. Remove temporary exploratory `.mjs`/`.spec.ts` files.
6. Preserve intentional screenshots and durable specs.
7. Run `git status --short` and report unrelated existing edits separately.

Never recursively delete a broad workspace, `$HOME`, `~`, `/tmp`, or an unresolved variable.

## Command reference

```bash
# Repository preflight
python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py

# Focused source tests
cd frontend
npx playwright test src/hooks/__tests__/useThreadSubagents.test.ts

# Focused browser spec
npx playwright test e2e/subagent-detail.spec.ts --reporter=line --workers=1

# Existing project E2E scripts
npm run e2e:deck
npm run e2e:claude-plugins

# Targeted lint and production type/build verification
npx eslint path/to/source.ts path/to/spec.ts
npm run build

# Backend regression tests
cd ../backend
.venv/bin/python -m pytest -q tests/test_claude_agent_subagents.py
```
