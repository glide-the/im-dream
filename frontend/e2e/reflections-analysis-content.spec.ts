// [Input] Authenticated Story Workspace Reflections route and public Reflections task/content DTOs.
// [Output] Provider-free browser journeys for source selection, task SSE/recovery, report persistence,
//          idempotent creation retry, partial failure, Notion source states, and responsive keyboard UI.
// [Pos] Technical isolated browser validation; no normal account, model, database, migration, or service write.
// [Sync] 2026-10-13: add analysis-content source and task lifecycle coverage through the production UI/API seams.
// [Sync] 2026-10-13: prepared tasks remain idle on load and start only from explicit continuation.
// [Sync] 2026-10-13: definite Notion body-read failures clear preparing state without creating or starting a task.
//
// Business scope: the Project, Episode, canonical Story artifacts, Run-private .dream publication, and after-turn
// Hook are out of scope. The Reflections task is the changed business fact; its public task/report DTOs and visible
// Analysis page are the consumers. The fixture owns only public API responses and protocol events.

import { expect, test, type Page } from '@playwright/test';
import { installFixtures, WEB_BASE } from './fixtures/calendarHarness';

test.use({ channel: 'chrome' });
test.setTimeout(60_000);

type Section = 'echoes' | 'traits' | 'patterns';
type TaskStatus = 'CREATED' | 'RUNNING' | 'COMPLETED' | 'PARTIAL_FAILED' | 'FAILED';
type CandidateStatus = 'ready' | 'empty' | 'no_snapshot' | 'auth_required' | 'scope_changed' | 'disconnected';

type FixtureResult = {
  id: string;
  task_id: string;
  section: Section;
  title: string;
  description: string;
  related_session_ids: string[];
  evidence: string;
  confidence: 'high' | 'medium' | 'low';
  created_at: string;
};

type SectionState = {
  section: Section;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  result_count: number;
  revision: number;
  started_at: string | null;
  completed_at: string | null;
  error_summary: string | null;
};

type FixtureTask = {
  id: string;
  task_id: string;
  status: TaskStatus;
  sections: Section[];
  input_snapshot: Record<string, unknown>;
  analysis_content: Record<string, unknown> | null;
  workspace_path: string | null;
  revision: number;
  section_states: SectionState[];
  agent_contract_version: string;
  error_summary: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
  results: FixtureResult[];
};

type FixtureReport = {
  id: number;
  created_at: string;
  report_data: {
    echoes: FixtureResult[];
    traits: FixtureResult[];
    patterns: FixtureResult[];
    stats: { days: number; entries: number; words: number };
    task_id: string;
    analysis_content: Record<string, unknown> | null;
  };
};

type FixtureState = {
  taskId: string;
  taskStatus: TaskStatus;
  candidateStatus: CandidateStatus;
  candidatePageCount: number;
  candidateSnapshot: string | null;
  includeNotion: boolean;
  includeAgent: boolean;
  notionReadFailed: boolean;
  agentReadFailed: boolean;
  noAnalyzableInput: boolean;
  createError?: string;
  creationUnknownOnce: boolean;
  createRequests: Array<Record<string, unknown>>;
  taskResponses: FixtureTask[];
  startRequests: string[];
  eventRequests: string[];
  reportRequests: string[];
  reportApiRequests: string[];
  reportSaveFailureOnce: boolean;
  reports: FixtureReport[];
  results: FixtureResult[];
  activeTaskOnLoad: boolean;
  holdSse: boolean;
  releaseSse?: () => void;
  unexpectedReflectionRequests: string[];
};

const TASK_ID = '6f6f5df3-0d11-4d63-8f4d-9e8a0f20c901';
const CONNECTOR_ID = '0d4f8f4b-3d9d-4fb9-8c73-5f7be4d8a101';
const DECK_ID = '95a7f432-8f36-46f5-9b1c-8a6d6d9d2102';
const AGENT_ID = '3db8e47f-16c7-4ac0-9e76-cb7f1f504203';
const PAGE_ID = '8ca4f9d1-7a63-4a0b-8f7d-1e6c3b2d5404';
const ECHO_RESULT_ID = '1b6d8e2f-3c40-4f51-9a62-7e8d9c0b1205';
const TRAIT_RESULT_ID = '2c7e9f30-4d51-4a62-8b73-8f9e0a1c2306';
const PATTERN_RESULT_ID = '3d8fa041-5e62-4b73-9c84-9a0f1b2d3407';
const SNAPSHOT_VERSION = 'snapshot-reflection-browser-v1';
const BODY_HASH = 'a'.repeat(64);

const resultFor = (section: Section): FixtureResult => ({
  id: section === 'echoes' ? ECHO_RESULT_ID : section === 'traits' ? TRAIT_RESULT_ID : PATTERN_RESULT_ID,
  task_id: TASK_ID,
  section,
  title: section === 'echoes' ? 'Repeated concern' : section === 'traits' ? 'Careful observer' : 'Review loop',
  description: 'A stable provider-free reflection result.',
  related_session_ids: ['diary-reflection-1'],
  evidence: 'Monday and Friday entries repeat the same concern.',
  confidence: 'high',
  created_at: '2026-10-13T03:00:04Z',
});

const contentSummary = (includeNotion: boolean, includeAgent = false, emptyNotion = false): Record<string, unknown> | null => ({
  diary_session_ids: emptyNotion ? [] : ['diary-reflection-1'],
  notion: includeNotion ? {
    connector_id: CONNECTOR_ID,
    snapshot_version: SNAPSHOT_VERSION,
    empty_page_count: emptyNotion ? 1 : 0,
    pages: emptyNotion ? [] : [{
      page_id: PAGE_ID, title: 'Weekly notes', url: 'https://www.notion.so/reflection-page',
      content_sha256: BODY_HASH, read_at: '2026-10-13T03:00:00Z',
    }],
  } : null,
  agent: includeAgent ? {
    deck_id: DECK_ID, agent_id: AGENT_ID, deck_name: 'Editorial Lens', agent_name: 'Reflective analyst',
  } : null,
});

function makeTask(state: FixtureState, status = state.taskStatus): FixtureTask {
  const results = state.results;
  const terminal = ['COMPLETED', 'PARTIAL_FAILED', 'FAILED'].includes(status);
  const noAnalyzableFailure = state.noAnalyzableInput && status === 'FAILED';
  const sourceSummary = contentSummary(state.includeNotion, state.includeAgent, state.noAnalyzableInput);
  const section_states: SectionState[] = (['echoes', 'traits', 'patterns'] as Section[]).map(section => {
    const result_count = results.filter(item => item.section === section).length;
    const failed = status === 'PARTIAL_FAILED' && section === 'traits';
    const sectionStatus: SectionState['status'] = noAnalyzableFailure
      ? 'PENDING'
      : failed ? 'FAILED' : terminal ? 'COMPLETED' : status === 'RUNNING' ? 'RUNNING' : 'PENDING';
    return {
      section, status: sectionStatus, result_count, revision: noAnalyzableFailure ? 1 : terminal ? 3 : 1,
      started_at: sectionStatus === 'PENDING' ? null : '2026-10-13T03:00:01Z',
      completed_at: ['COMPLETED', 'FAILED'].includes(sectionStatus) ? '2026-10-13T03:00:04Z' : null,
      error_summary: failed ? 'Traits section provider-free failure.' : null,
    };
  });
  return {
    id: state.taskId,
    task_id: state.taskId,
    status,
    sections: ['echoes', 'traits', 'patterns'],
    input_snapshot: {
      session_ids: state.noAnalyzableInput ? [] : ['diary-reflection-1'], start_date: null, end_date: null,
      language: 'en', language_label: 'English',
      ...(state.includeNotion || state.includeAgent || state.noAnalyzableInput ? { analysis_content: sourceSummary } : {}),
    },
    analysis_content: sourceSummary,
    workspace_path: null,
    agent_contract_version: 'reflections-analysis-content-v1',
    error_summary: noAnalyzableFailure
      ? 'REFLECTION_NO_ANALYZABLE_INPUT (422)'
      : status === 'PARTIAL_FAILED' ? 'One section could not be completed.' : null,
    revision: noAnalyzableFailure ? 2 : terminal ? 3 : 1,
    created_at: '2026-10-13T03:00:00Z', started_at: noAnalyzableFailure ? null : '2026-10-13T03:00:01Z',
    completed_at: terminal ? '2026-10-13T03:00:04Z' : null,
    updated_at: '2026-10-13T03:00:04Z', results, section_states,
  };
}

function makeReport(state: FixtureState): FixtureReport {
  return {
    id: 9001, created_at: '2026-10-13T03:00:05Z',
    report_data: {
      echoes: state.results.filter(item => item.section === 'echoes'),
      traits: state.results.filter(item => item.section === 'traits'),
      patterns: state.results.filter(item => item.section === 'patterns'),
      stats: { days: 1, entries: 1, words: 42 }, task_id: state.taskId,
      analysis_content: contentSummary(state.includeNotion, state.includeAgent),
    },
  };
}

function candidateResponse(state: FixtureState) {
  const ready = state.candidateStatus === 'ready';
  return {
    status: state.candidateStatus,
    page_count: ready ? state.candidatePageCount : 0,
    snapshot_version: ready ? state.candidateSnapshot : null,
    connector_id: ready ? CONNECTOR_ID : undefined,
    selection_available: true,
  };
}

function event(type: string, sequence: number, payload: Record<string, unknown> = {}) {
  return {
    id: `event-${sequence}`, task_id: TASK_ID, type, sequence,
    created_at: `2026-10-13T03:00:0${Math.min(sequence, 9)}Z`, payload,
  };
}

async function installReflectionFixtures(page: Page, options: {
  candidateStatus?: CandidateStatus;
  taskStatus?: TaskStatus;
  includeNotion?: boolean;
  activeTaskOnLoad?: boolean;
  seedActiveTaskStorage?: boolean;
  latestHistoricalResults?: boolean;
  holdSse?: boolean;
  reportSaveFailureOnce?: boolean;
  creationUnknownOnce?: boolean;
  createError?: string;
  partial?: boolean;
  seedReport?: boolean;
  notionReadFailureOnce?: boolean;
  createNotionReadFailureOnce?: boolean;
  agentReadFailureOnce?: boolean;
  noAnalyzableInputAfterSse?: boolean;
} = {}) {
  const base = await installFixtures(page, { diaryCount: 1 });
  const state: FixtureState = {
    taskId: TASK_ID,
    taskStatus: options.taskStatus ?? 'COMPLETED',
    candidateStatus: options.candidateStatus ?? 'ready',
    candidatePageCount: 1,
    candidateSnapshot: SNAPSHOT_VERSION,
    includeNotion: options.includeNotion ?? false,
    includeAgent: false,
    notionReadFailed: options.notionReadFailureOnce ?? false,
    agentReadFailed: options.agentReadFailureOnce ?? false,
    noAnalyzableInput: options.noAnalyzableInputAfterSse ?? false,
    creationUnknownOnce: options.creationUnknownOnce ?? false,
    createRequests: [], taskResponses: [], startRequests: [], eventRequests: [], reportRequests: [], reportApiRequests: [],
    reportSaveFailureOnce: options.reportSaveFailureOnce ?? false,
    reports: [], results: options.noAnalyzableInputAfterSse
      ? [] : options.partial
      ? [resultFor('echoes')]
      : [resultFor('echoes'), resultFor('traits'), resultFor('patterns')],
    activeTaskOnLoad: options.activeTaskOnLoad ?? false,
    holdSse: options.holdSse ?? false,
    unexpectedReflectionRequests: [],
  };
  let createNotionReadFailureOnce = options.createNotionReadFailureOnce ?? false;
  if (options.seedReport) state.reports = [makeReport(state)];
  if (options.activeTaskOnLoad) state.taskStatus = options.taskStatus ?? 'RUNNING';

  await page.addInitScript(({ activeTask, taskId }) => {
    localStorage.setItem('ink-language', 'en');
    if (activeTask) localStorage.setItem('reflections-active-task', JSON.stringify({
      taskId, sections: ['echoes', 'traits', 'patterns'],
      startedAt: Date.now(), lastEventId: 'event-1',
    }));
  }, { activeTask: state.activeTaskOnLoad && options.seedActiveTaskStorage !== false, taskId: TASK_ID });

  const errors: string[] = [];
  const expectedHttpErrors = new Set<string>();
  const observedExpectedHttpErrors = new Set<string>();
  const external = (url: string) => /react-grab\.com|fonts\.googleapis\.com|fonts\.gstatic\.com/.test(url);
  page.on('console', (message) => {
    if (message.type() !== 'error' || external(message.location().url || message.text())) return;
    setTimeout(() => {
      if ([...observedExpectedHttpErrors].some(value => expectedHttpErrors.has(value)
        && (message.text().includes(value.split(' ')[0])
          || (message.text().includes('Failed to load voices from decks') && value.endsWith(' /api/decks'))))) return;
      errors.push(`console: ${message.text()}`);
    }, 0);
  });
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    if (external(request.url()) || new URL(request.url()).pathname === '/api/sessions/events') return;
    errors.push(`request: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  page.on('response', response => {
    const key = `${response.status()} ${new URL(response.url()).pathname}`;
    if (expectedHttpErrors.has(key)) observedExpectedHttpErrors.add(key);
  });

  const allowHttpError = (status: number, path: string) => expectedHttpErrors.add(`${status} ${path}`);
  const clearHttpError = (status: number, path: string) => expectedHttpErrors.delete(`${status} ${path}`);

  await page.route('**/api/sessions/aggregate*', async route => {
    await route.fulfill({ json: {
      stats: { total_days: state.noAnalyzableInput ? 0 : 1, total_entries: state.noAnalyzableInput ? 0 : 1, total_words: state.noAnalyzableInput ? 0 : 42 },
      sessions: state.noAnalyzableInput ? [] : [{ id: 'diary-reflection-1', name: 'A diary entry', created_at: '2026-10-12T03:00:00Z',
        updated_at: '2026-10-12T03:00:00Z', has_text: true, word_count: 42 }], timezone: 'UTC',
    } });
  });
  await page.route('**/api/reports*', async route => {
    state.reportApiRequests.push(`${route.request().method()} /api/reports`);
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: { reports: state.reports } });
      return;
    }
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 200, json: { success: true } });
      return;
    }
    state.unexpectedReflectionRequests.push(`${route.request().method()} /api/reports`);
    await route.fulfill({ status: 405, json: {} });
  });
  await page.route('**/api/decks', async route => {
    const voice = { id: AGENT_ID, deck_id: DECK_ID, name: 'Reflective analyst', name_en: 'Reflective analyst', name_zh: '反思分析师',
      system_prompt: 'Review repeated assumptions.', icon: 'brain', color: 'blue', is_system: false, enabled: true };
    const deck = { id: DECK_ID, name: 'Editorial Lens', name_en: 'Editorial Lens', name_zh: '编辑视角', description: 'Analysis fixture', icon: 'brain', color: 'blue',
      is_system: false, enabled: true, agent_type: 'chat', agent_type_revision: 1, voices: [voice] };
    if (state.agentReadFailed) {
      state.agentReadFailed = false;
      const path = new URL(route.request().url()).pathname;
      allowHttpError(503, path);
      await route.fulfill({ status: 503, json: { detail: { error_code: 'ADMIN_UNAVAILABLE' } } });
      return;
    }
    await route.fulfill({ json: { decks: [deck] } });
  });
  await page.route('**/api/decks/**', async route => {
    const voice = { id: AGENT_ID, deck_id: DECK_ID, name: 'Reflective analyst', name_en: 'Reflective analyst', name_zh: '反思分析师',
      system_prompt: 'Review repeated assumptions.', icon: 'brain', color: 'blue', is_system: false, enabled: true };
    if (state.agentReadFailed) {
      state.agentReadFailed = false;
      const path = new URL(route.request().url()).pathname;
      allowHttpError(503, path);
      await route.fulfill({ status: 503, json: { detail: { error_code: 'ADMIN_UNAVAILABLE' } } });
      return;
    }
    await route.fulfill({ json: { id: DECK_ID, name: 'Editorial Lens', name_en: 'Editorial Lens', name_zh: '编辑视角', description: 'Analysis fixture', icon: 'brain', color: 'blue',
      is_system: false, enabled: true, agent_type: 'chat', agent_type_revision: 1, voices: [voice] } });
  });
  await page.route('**/api/reflections/analysis-content', async route => {
    if (state.notionReadFailed) {
      state.notionReadFailed = false;
      const path = new URL(route.request().url()).pathname;
      allowHttpError(503, path);
      await route.fulfill({ status: 503, json: { detail: { error_code: 'ADMIN_UNAVAILABLE' } } });
      return;
    }
    await route.fulfill({ json: candidateResponse(state) });
  });
  await page.route('**/api/reflections/latest', async route => {
    const task = state.activeTaskOnLoad ? makeTask(state, state.taskStatus) : null;
    const results = options.latestHistoricalResults
      ? state.results.map(result => ({ ...result, task_id: 'previous-completed-task' })) : task?.results ?? [];
    await route.fulfill({ json: { task, results } });
  });
  await page.route('**/api/reflections/tasks', async route => {
    if (route.request().method() !== 'POST') {
      state.unexpectedReflectionRequests.push(`${route.request().method()} /api/reflections/tasks`);
      await route.fulfill({ status: 405, json: {} });
      return;
    }
    const body = route.request().postDataJSON() as Record<string, unknown>;
    state.createRequests.push(body);
    if (state.createError) {
      allowHttpError(422, new URL(route.request().url()).pathname);
      await route.fulfill({ status: 422, json: { detail: { error_code: state.createError } } });
      return;
    }
    if (createNotionReadFailureOnce) {
      createNotionReadFailureOnce = false;
      allowHttpError(502, new URL(route.request().url()).pathname);
      await route.fulfill({ status: 502, json: { detail: { error_code: 'NOTION_UPSTREAM_UNAVAILABLE', outcome_unknown: false } } });
      return;
    }
    if (state.creationUnknownOnce) {
      state.creationUnknownOnce = false;
      allowHttpError(503, new URL(route.request().url()).pathname);
      await route.fulfill({ status: 503, json: { detail: { error_code: 'ADMIN_UNAVAILABLE', outcome_unknown: true, creation_committed: true } } });
      return;
    }
    state.taskStatus = 'RUNNING';
    const analysisContent = body.analysis_content as Record<string, unknown> | undefined;
    state.includeNotion = analysisContent?.include_notion === true;
    state.includeAgent = typeof analysisContent?.agent_id === 'string';
    const createdTask = makeTask(state, 'CREATED');
    state.taskResponses.push(createdTask);
    await route.fulfill({ status: 202, json: createdTask });
  });
  await page.route('**/api/reflections/tasks/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const suffix = url.pathname.slice('/api/reflections/tasks/'.length);
    if (suffix.endsWith('/start') && request.method() === 'POST') {
      state.startRequests.push(suffix.slice(0, -'/start'.length));
      if (state.noAnalyzableInput) state.taskStatus = 'FAILED';
      else if (state.taskStatus !== 'PARTIAL_FAILED') state.taskStatus = options.partial ? 'PARTIAL_FAILED' : 'COMPLETED';
      const startedTask = makeTask(state, state.taskStatus);
      state.taskResponses.push(startedTask);
      await route.fulfill({ status: 202, json: startedTask });
      return;
    }
    if (suffix.endsWith('/events') && request.method() === 'GET') {
      state.eventRequests.push(suffix.slice(0, -'/events'.length));
      if (state.holdSse) {
        await new Promise<void>(resolve => { state.releaseSse = resolve; });
      }
      const terminalType = state.noAnalyzableInput
        ? 'reflection.task.failed'
        : state.taskStatus === 'PARTIAL_FAILED' ? 'reflection.task.partial_failed' : 'reflection.task.completed';
      const body = [
        event('reflection.stream.connected', 1),
        ...(state.noAnalyzableInput ? [] : [event('reflection.task.started', 2)]),
        event(terminalType, state.noAnalyzableInput ? 2 : 3, state.noAnalyzableInput
          ? { error_code: 'REFLECTION_NO_ANALYZABLE_INPUT', message: 'REFLECTION_NO_ANALYZABLE_INPUT (422)', retryable: false }
          : state.taskStatus === 'PARTIAL_FAILED' ? { failed_sections: ['traits'] } : {}),
      ].map(item => `id: ${item.id}\nevent: ${item.type}\ndata: ${JSON.stringify(item)}\n\n`).join('');
      state.taskStatus = state.noAnalyzableInput ? 'FAILED' : state.taskStatus === 'PARTIAL_FAILED' ? 'PARTIAL_FAILED' : 'COMPLETED';
      await route.fulfill({ contentType: 'text/event-stream', body });
      return;
    }
    if (suffix.endsWith('/report') && request.method() === 'POST') {
      const taskId = suffix.slice(0, -'/report'.length);
      state.reportRequests.push(taskId);
      if (state.reportSaveFailureOnce) {
        state.reportSaveFailureOnce = false;
        allowHttpError(503, url.pathname);
        await route.fulfill({ status: 503, json: { detail: { error_code: 'ADMIN_UNAVAILABLE' } } });
        return;
      }
      state.reports = [makeReport(state)];
      await route.fulfill({ status: 200, json: { saved: true } });
      return;
    }
    if (suffix.endsWith('/results') && request.method() === 'GET') {
      await route.fulfill({ json: { results: state.results } });
      return;
    }
    if (request.method() === 'GET') {
      const task = makeTask(state, state.taskStatus);
      state.taskResponses.push(task);
      await route.fulfill({ json: task });
      return;
    }
    state.unexpectedReflectionRequests.push(`${request.method()} ${url.pathname}`);
    await route.fulfill({ status: 405, json: {} });
  });
  return Object.assign(state, { errors, base, allowHttpError, clearHttpError });
}

async function openAnalysis(page: Page, viewport = { width: 1440, height: 900 }) {
  await page.setViewportSize(viewport);
  await page.goto(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page.getByRole('heading', { name: 'Reflections', exact: true })).toBeVisible();
}

test('default and Notion+Agent analysis create through SSE, save retry, reload, and open the persisted report', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { reportSaveFailureOnce: true });
  await openAnalysis(page);

  const contentButton = page.getByRole('button', { name: 'Analysis content', exact: false });
  await contentButton.click();
  const contentRegion = page.getByRole('region', { name: 'Analysis content options' });
  await expect(contentRegion).toBeVisible();
  await expect(contentRegion.getByText('Use all 1 linked pages for this analysis.')).toBeVisible();
  const includeNotion = contentRegion.getByRole('checkbox', { name: 'Include Notion in analysis' });
  await expect(includeNotion).toBeEnabled();
  await expect(includeNotion).not.toBeChecked();
  await expect(contentRegion.getByRole('button', { name: 'Analysis Agent' })).toContainText('Default analysis');
  await includeNotion.check();
  await contentRegion.getByRole('button', { name: 'Analysis Agent' }).press('Enter');
  await expect(page.getByRole('listbox')).toBeVisible();
  await page.getByRole('listbox').getByRole('option', { name: /Reflective analyst/ }).click();
  await expect(contentRegion.getByRole('button', { name: 'Analysis Agent' })).toContainText('Reflective analyst');

  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, connector_id: CONNECTOR_ID, snapshot_version: SNAPSHOT_VERSION, deck_id: DECK_ID, agent_id: AGENT_ID });
  await expect(page.getByRole('alert').filter({ has: page.getByRole('button', { name: 'Retry save', exact: true }) })).toBeVisible();
  expect(fixture.reportRequests).toEqual([TASK_ID]);

  fixture.clearHttpError(503, `/api/reflections/tasks/${TASK_ID}/report`);
  await page.getByRole('button', { name: 'Retry save', exact: true }).click();
  await expect.poll(() => fixture.reportRequests.length).toBe(2);
  expect(fixture.reportRequests).toEqual([TASK_ID, TASK_ID]);
  await expect(page.getByText('Past Reflections', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Past Reflections/ }).click();
  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  const nextContent = page.getByRole('region', { name: 'Analysis content options' });
  await nextContent.getByRole('checkbox', { name: 'Include Notion in analysis' }).uncheck();
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, snapshot_version: SNAPSHOT_VERSION, agent_id: AGENT_ID });

  await page.reload();
  await expect(page.getByText('Past Reflections', { exact: true })).toBeVisible();
  await page.getByText('Latest', { exact: true }).locator('..').click();
  await expect(page.getByText('Repeated concern', { exact: true })).toBeVisible();
  expect(fixture.unexpectedReflectionRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});

test('partial failure remains visible and double click locks one creation immediately', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { partial: true, holdSse: true });
  await openAnalysis(page, { width: 1440, height: 900 });
  const generate = page.getByRole('button', { name: 'Generate New Analysis', exact: true });
  await generate.dblclick();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  await expect(page.getByRole('button', { name: 'Reflecting...', exact: true })).toBeDisabled();
  await expect.poll(() => fixture.eventRequests.length).toBe(1);
  fixture.releaseSse?.();
  await expect.poll(() => fixture.taskStatus).toBe('PARTIAL_FAILED');
  await expect(page.getByRole('status').filter({ hasText: /Some sections could not finish|部分栏目未完成/ })).toBeVisible();
  await expect(page.getByText('Repeated concern', { exact: true })).toBeVisible();
  expect(fixture.startRequests).toEqual([TASK_ID]);
  expect(fixture.errors).toEqual([]);
});

test('unknown creation outcome retries with the exact same request key', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { creationUnknownOnce: true });
  await openAnalysis(page);
  const generate = page.getByRole('button', { name: 'Generate New Analysis', exact: true });
  await generate.click();
  await expect(page.getByText(/The analysis could not start\. Check the selected content and retry\./).first()).toBeVisible();
  await generate.click();
  await expect.poll(() => fixture.createRequests.length).toBe(2);
  expect(fixture.createRequests[0].request_key).toBe(fixture.createRequests[1].request_key);
  await expect(page.getByText('Repeated concern', { exact: true })).toBeVisible();
  expect(fixture.errors).toEqual([]);
});

test('created empty-input task streams FAILED with no results and keeps source recovery actionable', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { noAnalyzableInputAfterSse: true });
  await openAnalysis(page);

  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  const initialRegion = page.getByRole('region', { name: 'Analysis content options' });
  const includeNotion = initialRegion.getByRole('checkbox', { name: 'Include Notion in analysis' });
  await expect(includeNotion).toBeEnabled();
  await includeNotion.check();
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, connector_id: CONNECTOR_ID, snapshot_version: SNAPSHOT_VERSION });
  await expect.poll(() => fixture.eventRequests.length).toBe(1);
  await expect(page.getByText('Select diary entries or Notion pages with text to analyze.', { exact: true }).first()).toBeVisible();

  const failedTask = fixture.taskResponses.find(task => task.status === 'FAILED');
  expect(failedTask).toMatchObject({
    id: TASK_ID,
    task_id: TASK_ID,
    status: 'FAILED',
    workspace_path: null,
    revision: 2,
    error_summary: 'REFLECTION_NO_ANALYZABLE_INPUT (422)',
    results: [],
  });
  expect(failedTask?.input_snapshot).toMatchObject({
    session_ids: [],
    analysis_content: {
      diary_session_ids: [],
      notion: { pages: [], empty_page_count: 1 },
      agent: null,
    },
  });
  expect(failedTask?.section_states).toHaveLength(3);
  expect(failedTask?.section_states.every(section => section.status === 'PENDING' && section.result_count === 0
    && section.revision === 1 && section.completed_at === null && section.error_summary === null)).toBe(true);
  expect(fixture.results).toEqual([]);
  expect(fixture.reportRequests).toEqual([]);
  expect(fixture.reportApiRequests.filter(request => request === 'POST /api/reports')).toEqual([]);
  await expect(page.getByText('Repeated concern', { exact: true })).toHaveCount(0);

  const contentButton = page.getByRole('button', { name: 'Analysis content', exact: false });
  await contentButton.click();
  const region = page.getByRole('region', { name: 'Analysis content options' });
  const retryNotion = region.getByRole('checkbox', { name: 'Include Notion in analysis' });
  await expect(retryNotion).toBeEnabled();
  await retryNotion.uncheck();
  await retryNotion.check();
  await expect(retryNotion).toBeChecked();
  await expect(page.getByRole('button', { name: 'Generate New Analysis', exact: true })).toBeEnabled();
  expect(fixture.errors).toEqual([]);
});

test('reconnects an existing active task after reload without creating a new task', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { activeTaskOnLoad: true });
  await openAnalysis(page);
  await expect.poll(() => fixture.eventRequests.length).toBeGreaterThan(0);
  expect(fixture.createRequests).toEqual([]);
  expect(fixture.startRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
});

test('prepared task stays idle on load and explicit continuation starts its original id', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { activeTaskOnLoad: true, taskStatus: 'CREATED', seedActiveTaskStorage: false, latestHistoricalResults: true });
  await openAnalysis(page);
  const generate = page.getByRole('button', { name: 'Generate New Analysis', exact: true });
  await expect(generate).toBeEnabled();
  const continueButton = page.getByRole('button', { name: 'Continue unstarted analysis', exact: true });
  await expect(continueButton).toBeVisible();
  expect(fixture.eventRequests).toEqual([]);
  expect(fixture.startRequests).toEqual([]);
  expect(fixture.createRequests).toEqual([]);
  await expect(page.getByText('The analysis result is available, but its report has not been saved.', { exact: true })).toHaveCount(0);
  await continueButton.click();
  await expect.poll(() => fixture.startRequests).toEqual([TASK_ID]);
  await expect.poll(() => fixture.reportRequests.length).toBeGreaterThan(0);
  expect(fixture.createRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
});

test('new analysis beside a prepared task uses the current Notion selection', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { activeTaskOnLoad: true, taskStatus: 'CREATED' });
  await openAnalysis(page);
  await expect(page.getByRole('button', { name: 'Continue unstarted analysis', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  await page.getByRole('checkbox', { name: 'Include Notion in analysis' }).check();
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, snapshot_version: SNAPSHOT_VERSION });
  await expect.poll(() => fixture.reportRequests.length).toBeGreaterThan(0);
  expect(fixture.errors).toEqual([]);
});

test('Notion no-snapshot, empty, auth-required, and empty-body responses stay actionable', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { candidateStatus: 'no_snapshot' });
  await openAnalysis(page);
  const contentButton = page.getByRole('button', { name: 'Analysis content', exact: false });
  await contentButton.click();
  const region = page.getByRole('region', { name: 'Analysis content options' });
  await expect(region.getByText('Sync linked resources in Settings first.', { exact: true })).toBeVisible();

  fixture.candidateStatus = 'empty';
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByText('No Notion pages are linked.', { exact: true })).toBeVisible();
  fixture.candidateStatus = 'auth_required';
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByText('Reconnect Notion in Settings.', { exact: true })).toBeVisible();
  fixture.candidateStatus = 'scope_changed';
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByText('Linked resources changed. Sync them again in Settings.', { exact: true })).toBeVisible();

  fixture.candidateStatus = 'ready';
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  const includeNotion = region.getByRole('checkbox', { name: 'Include Notion in analysis' });
  await expect(includeNotion).toBeEnabled();
  await includeNotion.check();
  fixture.createError = 'REFLECTION_NO_ANALYZABLE_INPUT';
  fixture.allowHttpError(422, '/api/reflections/tasks');
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect(page.getByText('Select diary entries or Notion pages with text to analyze.', { exact: true }).first()).toBeVisible();
  fixture.clearHttpError(422, '/api/reflections/tasks');
  expect(fixture.errors).toEqual([]);
});

test('Notion read and Agent invalidation errors recover through the explicit reload path', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { notionReadFailureOnce: true, agentReadFailureOnce: true, createNotionReadFailureOnce: true });
  await openAnalysis(page);
  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  const region = page.getByRole('region', { name: 'Analysis content options' });
  await expect(region.getByText('Notion resources could not be loaded. Retry.', { exact: true })).toBeVisible();
  fixture.agentReadFailed = true;
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByText('Analysis Agents could not be loaded. Default analysis remains available.', { exact: true })).toBeVisible();
  await region.getByRole('button', { name: 'Reload', exact: true }).click();
  await expect(region.getByRole('button', { name: 'Analysis Agent' })).toContainText('Default analysis');
  await region.getByRole('checkbox', { name: 'Include Notion in analysis' }).check();
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect.poll(() => fixture.createRequests.length).toBe(1);
  await expect(page.getByText('Notion content is temporarily unavailable. The analysis has not started. Retry later.', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('task · preparing', { exact: true })).toHaveCount(0);
  expect(fixture.taskResponses).toEqual([]);
  expect(fixture.startRequests).toEqual([]);
  expect(fixture.eventRequests).toEqual([]);
  expect(fixture.reportRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
});

test('today re-analysis opens the diary picker with the current entries', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { seedReport: true });
  await openAnalysis(page);
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Today already has a Reflections analysis.' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('A diary entry', { exact: true })).toBeVisible();
  await expect(dialog.getByRole('checkbox')).toBeChecked();
  await expect(dialog.getByText('Re-running will create a new analysis. Choose the diary entries that should be included this time.', { exact: true })).toBeVisible();
  expect(fixture.createRequests).toEqual([]);
});

test('desktop and narrow content controls support keyboard selection and nested Escape ownership', async ({ page }) => {
  const fixture = await installReflectionFixtures(page);
  await openAnalysis(page, { width: 390, height: 700 });
  const contentButton = page.getByRole('button', { name: 'Analysis content', exact: false });
  await contentButton.focus();
  await contentButton.press('Enter');
  const region = page.getByRole('region', { name: 'Analysis content options' });
  await expect(region).toBeVisible();
  const agentTrigger = region.getByRole('button', { name: 'Analysis Agent' });
  await expect(agentTrigger).toBeEnabled();
  await agentTrigger.focus();
  await agentTrigger.press('Enter');
  const listbox = region.getByRole('listbox');
  await expect(listbox).toBeVisible();
  await listbox.getByRole('textbox').press('ArrowDown');
  await listbox.getByRole('textbox').press('Enter');
  await expect(agentTrigger).toContainText('Reflective analyst');
  await agentTrigger.press('Enter');
  await expect(listbox).toBeVisible();
  await listbox.getByRole('textbox').press('Escape');
  await expect(listbox).toHaveCount(0);
  await expect(region).toBeVisible();
  await contentButton.press('Escape');
  await expect(region).toHaveCount(0);
  await expect(contentButton).toBeFocused();
  const overflow = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(overflow.width).toBeLessThanOrEqual(overflow.client + 1);
  expect(fixture.errors).toEqual([]);
});
