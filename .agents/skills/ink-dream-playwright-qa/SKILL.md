---
name: ink-dream-playwright-qa
description: Run reliable human-journey Playwright automation and visual QA for the Ink-Dream repository. Use when Codex needs to create, debug, or execute frontend browser tests; validate authenticated Chat, Dream, Settings, SubAgent, theme, language, responsive, Markdown, console, or resize behavior; stage isolated backend/workspace fixtures; or diagnose flaky local Playwright runs on ports 5173 and 8765.
---

# Ink-Dream Playwright QA

Use the repository-local `@playwright/test` runtime and isolate mutable backend state. Produce assertions and evidence, not screenshot-only approval.

Read [references/project-workflow.md](references/project-workflow.md) before starting a browser run. Read its SubAgent fixture section only when testing SubAgent projections or timelines.

## Non-negotiable rules

- Run Playwright from `frontend/` with the installed `@playwright/test`; do not depend on a global `playwright-cli` or an MCP wrapper.
- Inspect `git status --short` first. Preserve unrelated changes and remove only artifacts created by the current QA run.
- Use a temporary `INK_DATABASE_PATH` and absolute `AGENT_CWD` for tests that create users, threads, workspaces, or Agent records.
- Treat ports `5173` and `8765` as owned only after resolving their listener PIDs. Never kill an unidentified process.
- Register API, console, page-error, and request-failure listeners before navigation.
- Write business E2E scenarios as normal human journeys through visible UI. API
  calls may stage isolated prerequisites or verify persisted facts, but must not
  replace the meaningful user interaction under test.
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
- Stop owned services and remove temporary runtime data at the end, including after failures.

## Workflow

### 1. Select the test lane

Choose the smallest lane that proves the change:

| Lane | Use for | Command pattern |
| --- | --- | --- |
| Source/unit | reducers, normalization, layout contracts | `npx playwright test src/path/test.ts` |
| Mocked browser | UI behavior independent of backend/provider | `page.route()` plus a focused `e2e/*.spec.ts` |
| Real local E2E | auth, API persistence, workspace projection, SSE integration | isolated FastAPI + Vite |
| Visual QA | theme, locale, responsive, overflow, long content | real or staged data plus screenshots |

Do not invoke a real model or external provider unless that integration is the feature under test.

### 2. Preflight the repository

Run:

```bash
python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py
```

Resolve missing dependencies and occupied ports before authoring test data. Use `npx playwright install chromium` only when the project browser is actually missing.

### 3. Start an isolated runtime

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

### 4. Build deterministic state

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
