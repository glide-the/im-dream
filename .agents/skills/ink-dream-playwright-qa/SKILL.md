---
name: ink-dream-playwright-qa
description: Run reliable full-business-journey Playwright automation and visual QA for the Ink-Dream repository. Use when Codex needs to create, debug, or execute frontend browser tests; validate authenticated Chat, Dream, Settings, SubAgent, theme, language, responsive, Markdown, console, resize behavior, or a complete Agent-to-file-to-Hook-to-database-to-page projection; use isolated fixtures only for explicitly technical tests; or diagnose flaky local Playwright runs on ports 5173 and 8765.
---

# Ink-Dream Playwright QA

Use the repository-local `@playwright/test` runtime. Select the real-business or
technical-isolation lane explicitly. Produce assertions and evidence, not
screenshot-only approval.

Read [references/project-workflow.md](references/project-workflow.md) before starting a browser run. Read its SubAgent fixture section only when testing SubAgent projections or timelines.

## Non-negotiable rules

- Run Playwright from `frontend/` with the installed `@playwright/test`; do not depend on a global `playwright-cli` or an MCP wrapper.
- Inspect `git status --short` first. Preserve unrelated changes and remove only artifacts created by the current QA run.
- Use an isolated database and absolute workspace root only for explicitly
  technical, provider-free, destructive, migration, or fault-injection tests.
  For user-requested real business or real-model QA, use the named existing
  local account/Run and normal Dream/Admin/Gateway/PostgreSQL path. Never clone
  real data or substitute a shadow account, Deck, ledger, or Admin instance.
- Treat ports `5173` and `8765` as owned only after resolving their listener PIDs. Never kill an unidentified process.
- Register API, console, page-error, and request-failure listeners before navigation.
- Before starting any Dream browser, model, or mutation step, write a Dream
  business concept and impact brief. Define Project, Episode, canonical
  Artifact, Run-private `.dream` publication, after-turn Hook, PostgreSQL/API
  projection, and final UI consumer for the scenario. Then mark every affected
  fact as **changes**, **must remain unchanged**, or **not in scope**. A test
  without this brief has no trustworthy expected result and must not start.
- Write business E2E scenarios as normal human journeys through visible UI. API
  calls may stage isolated prerequisites or verify persisted facts, but must not
  replace the meaningful user interaction under test.
- A business mutation is complete only when the whole consumer chain is proven:
  visible request → shared Thread/Agent action → canonical file → successful
  after-turn Hook → private `.dream` publication when applicable → PostgreSQL
  projection → public API → final visible consumer page. A file SHA, assistant
  sentence, HTTP health check, or screenshot alone is not acceptance.
- Treat visible Agent/Thread termination as the business terminal. Once the UI
  shows that the Agent has stopped, immediately validate required output and
  fail if it is incomplete; process, port, SSE reconnect, or HTTP health alone
  must never justify continued business polling.
- Handle required tool confirmations through the visible UI as part of the
  human journey. Approve only case-specific allowlisted operations after the
  test identifies the displayed tool; fail on unknown, Bash, network, or other
  unreviewed confirmations instead of silently approving or polling behind
  them. AskUserQuestion answers must come from explicit scenario input.
- Keep headed browser windows within the current desktop using an explicit
  bounded outer window and deterministic content viewport. Never use zoom,
  CSS scaling, maximization, or hidden panels to conceal a responsive defect;
  require zero document-level horizontal overflow and keep the scenario's
  heading, primary action, and blocking dialogs inside the visible viewport.
- Prefer roles, labels, titles, and test ids. Do not use forced clicks to make a test pass; use keyboard activation only when intentionally validating or bypassing the known Writing overlay.
- Wait for visible state and known transitions. Do not replace readiness checks with arbitrary long sleeps.
- Verify behavior with assertions before taking screenshots.
- Stop only services started by the QA run. Remove its temporary technical data,
  but preserve real business Run/Thread/Gateway/Admin records unless the user
  explicitly requests cleanup.

## Workflow

### 0. Define the Dream business contract and impact scope

Read the authoritative design and the named Run's current file facts before
choosing assertions. At minimum, produce this compact table in the test plan or
durable spec comments:

| Concept/fact | Source of truth | Write/sync owner | Visible consumers | Expected impact |
| --- | --- | --- | --- | --- |
| Project identity/title | canonical `stories/<project>/project.yaml` | Agent writes; successful main-turn Hook publishes and materializes | Story row, Story Index API, Execution page Project heading | changes / unchanged / out of scope |
| Episode identity/title/content | canonical `episodes/<EPxx>/` artifacts | Agent/Skill writes; Hook publishes current files | Episode API and Episode workbench | changes / unchanged / out of scope |
| Run-private publication | `.dream/runtime/runs/<run-id>/artifact/` and manifest | host-owned successful main-turn Hook | server readers and downstream materializer | changes / unchanged / out of scope |
| Shared conversation | Chat thread plus Claude session id | ClaudeAgentService | Chat and Dream composers/history | resumes / new turn only |

Do not collapse Project and Episode into a single generic “title.” For example,
changing `project.yaml.project_name` changes the Project heading and Story
projection, but does not rename EP01 or rewrite its script. Conversely, an
Episode title change must identify the affected EP and its internally
consistent artifact fields; it must not silently rename the Project.

Resolve ambiguous natural-language requests from the actual visible context,
the synchronized `WORKBENCH.md`, and authoritative artifact contract. Record
the resolution before the turn. If those sources still allow multiple material
interpretations, make clarification part of the human journey instead of
inventing an expected scope in test code.

### 1. Select the test lane

Choose the smallest lane that proves the change:

| Lane | Use for | Command pattern |
| --- | --- | --- |
| Source/unit | reducers, normalization, layout contracts | `npx playwright test src/path/test.ts` |
| Mocked browser | UI behavior independent of backend/provider | `page.route()` plus a focused `e2e/*.spec.ts` |
| Real local E2E | named real account/Run, real model, Admin-visible persistence, complete workspace projection | normal local Dream/Admin/Gateway/PostgreSQL + Vite |
| Isolated integration | provider-free auth/API persistence and deterministic faults | isolated FastAPI + Vite |
| Visual QA | theme, locale, responsive, overflow, long content | real or staged data plus screenshots |

Do not invoke a real model or external provider unless that integration is the feature under test.

### 2. Preflight the repository

Run:

```bash
python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py
```

Resolve missing dependencies and occupied ports before authoring test data. Use `npx playwright install chromium` only when the project browser is actually missing.

### 3. Start the authorized runtime

For real business or real-model QA, inspect and use the user's normal local
services. Start a missing normal service only from its real repository with its
normal configuration. Do not replace it with a clone, random-port Admin,
alternate Gateway, shadow account, or synthetic Deck.

For explicitly technical isolated QA, create one temporary runtime root:

Create one temporary runtime root. Start backend and frontend as separate managed terminal sessions; do not background them with shell `&`.

```bash
qa_runtime="$(mktemp -d)"
mkdir -p "$qa_runtime/workspaces"
INK_DATABASE_PATH="$qa_runtime/ink.db" \
AGENT_CWD="$qa_runtime/workspaces" \
backend/.venv/bin/python backend/server.py
```

From `frontend/`, start:

```bash
npm run dev -- --host 127.0.0.1
```

Wait for `http://127.0.0.1:8765/api/health` and `http://127.0.0.1:5173/` to respond. Recheck that the running backend sees the intended workspace root before staging filesystem fixtures.

### 4. Resolve business state

For real business QA, resolve the named account and existing entity read-only,
then perform only visible operations a normal user would perform. Do not seed,
clone, snapshot, or directly rewrite the business facts under test.

For technical isolated QA:

- Create a unique user through `POST /api/register` with Playwright's `request` fixture.
- Create required threads and resources through real APIs when those APIs are under test.
- Seed authentication with `page.addInitScript()` before `page.goto()`.
- Mock network boundaries with `page.route()` when the backend/provider is not under test.
- For SubAgent timeline tests, create the real thread first, then run `scripts/stage_subagent_fixture.py` against the same temporary `AGENT_CWD`.

Never hand-edit the normal development database for browser QA.

### 5. Author stable browser assertions

- Name and order the scenario as an outcome a user recognizes: navigate to the
  feature, make visible choices, enter realistic input, submit, observe visible
  progress, then inspect the visible result. Keep direct API reads as supporting
  contract evidence after or alongside that UI journey.
- Before the first message, define a compact dialogue table containing each
  visible utterance, expected Agent/tool behavior, expected canonical file,
  Hook/database/API result, expected visible page result, and facts that must
  remain unchanged. Execute it on the same Thread and verify the complete row
  after every turn before continuing.
- For Dream asset collaboration, “complete flow” means the same real Thread
  performs at least one **add**, **update**, and **delete** for every asset kind
  in scope (character, scene, prop, storyboard shot). When an asset kind has
  no page stage (currently props), verify its canonical file and references
  without inventing a frontend projection. Verify after each visible turn:
  both host Agent contracts were Read, the expected built-in file tools ran,
  canonical IDs/paths stayed stable on update, storyboard totals stayed
  consistent, the successful Hook advanced only changed stages, the
  actor-scoped `dream-files` API returned the same facts, and the refreshed
  workbench page showed them. A single happy-path mutation or a final snapshot
  is not a complete asset-collaboration test.
- Include one reference-integrity step whenever deletion is in scope. Create a
  temporary test-only character/scene/prop/shot relationship through the visible
  Agent, then require the Agent either to update/remove the references in the
  same turn or visibly ask the user for clarification. Never accept dangling
  `character_refs`, `scene_refs`, prop references, shot `characters`, `props`,
  or `scene_ref` values.
- Real-data asset tests must use unique temporary business names/IDs and finish
  with a visible Agent cleanup turn that restores the baseline. In a `finally`
  block, make a bounded best-effort cleanup through the same UI if temporary
  facts remain; never clean normal business data with direct filesystem or SQL
  mutation.
- Model business and infrastructure terminals separately. A healthy backend can
  coexist with a stopped Agent and incomplete workflow. Poll the shared Thread
  status together with derived business output; when the Thread has completed a
  turn and is no longer running, stop waiting and assert the output immediately.
- While a turn is running, sample the visible confirmation surface before each
  business-state poll. Resolve an expected confirmation using its labeled UI and
  wait for that exact dialog to settle before expecting downstream artifacts.
- In headed runs, size the browser for the actual desktop before navigation and
  assert that critical controls are in the viewport. Internal content scrolling
  is acceptable; document-level horizontal overflow and clipped blocking
  controls are failures.
- Assert the URL or route after navigation.
- Assert loading completion before interaction.
- Assert semantic content, ARIA state, message order, absence of forbidden controls, and persisted API state.
- For draggable panels, test keyboard adjustment, pointer drag, double-click reset, ARIA values, and width persistence.
- For locale/theme coverage, switch through project state modules or controls and assert the document/UI state before capturing evidence.
- For animated sidebars, wait for the detail/list locator and the short width transition before measuring or screenshotting.
- For compact SubAgent rows, require roughly 60–72px normally and no more than 80px with a summary; require all row bounds to remain inside the sidebar.
- For scroll ownership, inspect computed overflow and dimensions: the sidebar body may scroll vertically, but no timeline descendant may create a second vertical scrolling region.

### 6. Run proportional verification

Run the focused spec first, then related checks:

```bash
cd frontend
npx playwright test e2e/example.spec.ts --reporter=line --workers=1
npx eslint path/to/changed.ts path/to/test.ts
npm run build
```

Run backend tests with `backend/.venv/bin/python -m pytest ...` when projection, API, workspace, auth, or completion behavior changes.

Record:

- passed/failed counts;
- browser matrix covered;
- relevant screenshots;
- application console/page errors;
- external-only failures separately;
- any skipped scenario and reason.

### 7. Clean up and hand off

- Close the Playwright browser/context in `finally` or fixtures.
- Stop only the backend/frontend sessions started by this run.
- Confirm ports `5173` and `8765` are no longer listening if they were previously free.
- Remove the exact temporary runtime directory and temporary exploratory scripts.
- Keep durable specs and useful screenshots only when requested or intentionally part of the change.
- If evidence is temporary, report its results before removing the isolated runtime; if the user requests reviewable evidence, copy only the named final screenshots to gitignored `output/playwright/`.
- Re-run `git status --short` and distinguish current work from pre-existing edits.

## Failure discipline

- If the SubAgent API returns `exists: false`, compare the backend process environment with the fixture root; restarting without the same absolute `AGENT_CWD` does not fix the mismatch.
- If a visible nav button is intercepted by the Writing state chooser, focus it and press `Enter`, or complete the chooser and wait for its expanded prompt to collapse. Do not wait for the text `OK` to disappear because the collapsed chooser still displays it.
- If a screenshot captures a nearly closed sidebar, wait for the width transition after `aria-expanded=true` before capture.
- If the console reports auth errors during login bootstrap, fix auth seeding or begin error collection only after authenticated readiness; do not blanket-ignore application errors.
- If only external React Grab or Google Fonts requests fail, report them as external diagnostics and still require zero Ink-Dream runtime errors.
