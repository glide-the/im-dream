// [Sync] 2026-10-14: preserve original timeline geometry while inserting task recap records and reusing earlier-days loading.
// [Input] Authenticated Story Workspace Reflections route and public Reflections task/content DTOs.
// [Output] Provider-free browser journeys for source selection, task SSE/recovery, report persistence,
//          idempotent creation retry, partial failure, Notion source states, and responsive keyboard UI.
// [Pos] Technical isolated browser validation; no normal account, model, database, migration, or service write.
// [Sync] 2026-10-13: add analysis-content source and task lifecycle coverage through the production UI/API seams.
// [Sync] 2026-10-13: prepared tasks remain idle on load and start only from explicit continuation.
// [Sync] 2026-10-13: definite Notion body-read failures clear preparing state without creating or starting a task.
// [Sync] 2026-10-14: cover Chat-origin section deep links, report focus, query consumption and browser return.
// [Sync] 2026-10-14: classify Chat/Analysis route teardown aborts as expected request cleanup.
//
// Business scope: the Project, Episode, canonical Story artifacts, Run-private .dream publication, and after-turn
// Hook are out of scope. The Reflections task is the changed business fact; its public task/report DTOs and visible
// Analysis page are the consumers. The fixture owns only public API responses and protocol events.

import { expect, test, type Page } from '@playwright/test';
import { installFixtures, isReflectionHistoryCancellation, isReflectionHistoryNavigationCancellation, WEB_BASE } from './fixtures/calendarHarness';

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
  id: number | string;
  analysis_created_at?: string;
  task_id?: string | null;
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
  historyReadFailureOnce?: boolean;
  historyReadFailureUntilRetry?: boolean;
  historyMoreFailureOnce?: boolean;
  historyRequests: string[];
  holdTaskLookup?: boolean;
  releaseTaskLookup?: () => void;
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
  holdTaskLookup?: boolean;
} = {}) {
  const base = await installFixtures(page, { diaryCount: 1, reflectionHistory: true });
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
    unexpectedReflectionRequests: [], historyRequests: [], holdTaskLookup: options.holdTaskLookup,
  };
  const taskLookupResolvers: Array<() => void> = [];
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
    const url = new URL(request.url());
    const expectedNavigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && (url.pathname === '/api/sessions/events'
        || url.pathname === '/api/story-workspace/dream-runs'
        || (url.pathname === '/api/claude-agent/threads' && url.search === '?limit=21'));
    if (external(request.url()) || expectedNavigationAbort || isReflectionHistoryCancellation(request)
      || isReflectionHistoryNavigationCancellation(request, base.isReflectionHistoryNavigationActive())) return;
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
  await page.route(/\/api\/reports(?:\/history)?(?:\?|$)/, async route => {
    state.reportApiRequests.push(`${route.request().method()} /api/reports`);
    if (route.request().method() === 'GET') {
      const url = new URL(route.request().url());
      if (url.pathname === '/api/reports/history') {
        state.historyRequests.push(url.search);
        const more = url.searchParams.has('before_id');
        if ((!more && (state.historyReadFailureOnce || state.historyReadFailureUntilRetry)) || (more && state.historyMoreFailureOnce)) {
          state.historyReadFailureOnce = false; state.historyMoreFailureOnce = false;
          allowHttpError(503, url.pathname);
          await route.fulfill({ status: 503, json: { detail: 'ADMIN_CAPABILITY_UNAVAILABLE' } });
          return;
        }
        const reports = state.reports.map(report => ({ ...report, id: String(report.id),
          task_id: report.task_id !== undefined ? report.task_id : report.report_data.task_id,
          analysis_created_at: report.analysis_created_at ?? (report.report_data.task_id === state.taskId ? makeTask(state).created_at : report.created_at),
        })).sort((a, b) => {
          const time = a.analysis_created_at === b.analysis_created_at ? 0 : a.analysis_created_at > b.analysis_created_at ? -1 : 1;
          return time || (BigInt(a.id) > BigInt(b.id) ? -1 : BigInt(a.id) < BigInt(b.id) ? 1 : 0);
        });
        const beforeId = url.searchParams.get('before_id');
        const start = beforeId ? reports.findIndex(report => report.id === beforeId) + 1 : 0;
        const limit = Number(url.searchParams.get('limit') ?? 10);
        const selected = reports.slice(start, start + limit);
        const last = selected.at(-1);
        await route.fulfill({ json: { reports: selected,
          next_cursor: reports.length > start + limit && last ? { id: last.id, created_at: last.analysis_created_at } : null,
        } });
      } else await route.fulfill({ json: { reports: state.reports } });
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
      state.reports = [makeReport(state), ...state.reports.filter(report => report.id !== 9001)];
      await route.fulfill({ status: 200, json: { saved: true } });
      return;
    }
    if (suffix.endsWith('/results') && request.method() === 'GET') {
      await route.fulfill({ json: { results: state.results } });
      return;
    }
    if (request.method() === 'GET') {
      if (state.holdTaskLookup) await new Promise<void>(resolve => {
        taskLookupResolvers.push(resolve);
        state.releaseTaskLookup = () => { state.holdTaskLookup = false; taskLookupResolvers.splice(0).forEach(release => release()); };
      });
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

test('Chat-origin section navigation opens the matching saved report once and restores clean history', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { seedReport: true });
  for (let index = 0; index < 12; index += 1) fixture.reports.unshift({
    ...fixture.reports[0],
    id: 9002 + index,
    created_at: '2026-10-14T03:00:05Z',
    report_data: {
      ...fixture.reports[0].report_data,
      task_id: `40000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
      echoes: [], patterns: [],
    },
  });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`${WEB_BASE}/story-workspace/chat`);
  await expect(page.getByRole('button', { name: 'Chat', exact: true })).toBeVisible();
  // AnalysisView loads these three resources on route entry. The analysis-content
  // and deck endpoints are intentionally lazy and only run after the user opens
  // the Analysis content control, so they are not part of this deep-link read set.
  const waitForAnalysisReads = () => Promise.all([
    page.waitForResponse(response => new URL(response.url()).pathname === '/api/sessions/aggregate'),
    page.waitForResponse(response => new URL(response.url()).pathname === '/api/reports/history'),
    page.waitForResponse(response => new URL(response.url()).pathname === '/api/reflections/latest'),
  ]);
  const firstReads = waitForAnalysisReads();
  await page.evaluate((href) => {
    window.history.pushState({ inkDreamView: 'story-workspace' }, '', href);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, '/story-workspace/analysis?section=patterns');
  await firstReads;

  const patterns = page.locator('[data-reflection-section="patterns"]');
  await expect(patterns).toBeVisible();
  await expect(patterns).toHaveAttribute('aria-pressed', 'true');
  await expect(patterns).toBeFocused();
  await expect(page.getByText('Review loop', { exact: true })).toBeVisible();
  expect(fixture.historyRequests.some(query => new URLSearchParams(query).has('before_id'))).toBe(true);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);

  await page.goBack();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/chat`);
  const restoredReads = waitForAnalysisReads();
  await page.goForward();
  await restoredReads;
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page.getByRole('heading', { name: 'Reflections', exact: true })).toBeVisible();
  await expect(page.locator('[data-reflection-section="patterns"]')).toHaveCount(0);
  expect(fixture.unexpectedReflectionRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});

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
  await expect(page.getByRole('button', { name: 'Past Reflections', exact: false })).toBeVisible();
  await page.getByRole('button', { name: /Past Reflections/ }).click();
  await page.getByRole('button', { name: 'Analysis content', exact: false }).click();
  const nextContent = page.getByRole('region', { name: 'Analysis content options' });
  await nextContent.getByRole('checkbox', { name: 'Include Notion in analysis' }).uncheck();
  expect(fixture.createRequests[0].analysis_content).toMatchObject({ include_notion: true, snapshot_version: SNAPSHOT_VERSION, agent_id: AGENT_ID });

  await page.reload();
  await expect(page.getByRole('button', { name: 'Past Reflections', exact: false })).toBeVisible();
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
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);
  await expect.poll(() => fixture.eventRequests.length).toBeGreaterThan(0);
  // A recovered task with terminal results opens its existing report after the
  // resume stream settles; assert that visible consumer rather than the
  // dashboard heading that only exists before recovery completes.
  await expect(page.getByRole('button', { name: '← Past Reflections' })).toBeVisible();
  await expect(page.getByText('Repeated concern', { exact: true })).toBeVisible();
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
  const fixture = await installReflectionFixtures(page, { activeTaskOnLoad: true, taskStatus: 'CREATED', holdTaskLookup: true });
  await openAnalysis(page);
  await expect.poll(() => Boolean(fixture.releaseTaskLookup)).toBe(true);
  await expect(page.getByText('42', { exact: true })).toBeVisible();
  fixture.releaseTaskLookup?.();
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
  fixture.reports[0].created_at = new Date().toISOString();
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


function historyFixtures(count: number): FixtureReport[] {
  return Array.from({ length: count }, (_, index) => {
    // Intentional: report saving/order differs from analysis creation and diary range.
    const created = new Date(Date.UTC(2026, 9, 13, 16, 1 - index)).toISOString();
    return { id: String(9007199254741000n + BigInt(index)), created_at: '2026-12-01T00:00:00Z',
      analysis_created_at: created, task_id: `80000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
      report_data: { echoes: [{ ...resultFor('echoes'), related_session_ids: [], title: `History insight ${index}`, description: `Distinct report content ${index}` }],
        traits: [], patterns: [], stats: { days: 120, entries: 9, words: 42 }, task_id: `80000000-0000-4000-8000-${String(index).padStart(12, '0')}`, analysis_content: null } };
  });
}

async function installTimelineReads(page: Page) {
  await page.route('**/api/pictures/range*', route => route.fulfill({ json: { pictures: [] } }));
}

for (const count of [0, 1, 3, 31]) test(`history preview keeps latest three independent analyses from ${count} records`, async ({ page }) => {
  const fixture = await installReflectionFixtures(page);
  fixture.reports = historyFixtures(count);
  await installTimelineReads(page);
  await openAnalysis(page);
  const history = page.getByRole('region', { name: 'Past Reflections', exact: true });
  if (count === 0) await expect(history).toHaveCount(0);
  else {
    await expect(history.locator('[data-analysis-report-id]')).toHaveCount(Math.min(count, 3));
    expect(await history.locator('[data-analysis-report-id]').evaluateAll(nodes => nodes.map(node => node.getAttribute('data-analysis-report-id'))))
      .toEqual(fixture.reports.slice(0, 3).map(report => String(report.id)));
    const card = history.locator('[data-analysis-report-id]').first();
    await card.focus(); await page.keyboard.press('Enter');
    await expect(page.getByText('History insight 0', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Past Reflections', exact: false })).toBeFocused();
    await page.getByRole('button', { name: 'Past Reflections', exact: false }).click();
  }
  if (count === 0) await page.getByRole('button', { name: 'Timeline', exact: true }).click();
  else await history.getByRole('button', { name: 'Past Reflections', exact: false }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/timeline`);
  if (count === 0) {
    await expect(page.locator('[data-analysis-report-id]')).toHaveCount(0);
    await expect(page.getByText('No analysis reports yet.')).toHaveCount(0);
  }
  else await expect(page.locator(`[data-analysis-report-id="${fixture.reports[0].id}"]`)).toBeVisible();
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});

for (const width of [1440, 375]) test(`analysis history navigates and reads older reports with stable return at ${width}px`, async ({ page }, testInfo) => {
  const fixture = await installReflectionFixtures(page);
  fixture.reports = historyFixtures(31);
  // Equal creation instants require decimal-id descending order; independent same-day reports stay separate.
  fixture.reports[1].analysis_created_at = fixture.reports[0].analysis_created_at;
  fixture.reports[30].analysis_created_at = '2025-09-30T16:00:00Z';
  await installTimelineReads(page);
  await page.route('**/api/preferences', route => route.fulfill({ json: { first_login_completed: true, timezone: 'Asia/Shanghai' } }));
  await openAnalysis(page, { width, height: 812 });
  const preview = page.getByRole('region', { name: 'Past Reflections', exact: true });
  await expect(preview.locator('[data-analysis-report-id]')).toHaveCount(3);
  expect(await preview.locator('[data-analysis-report-id]').first().getAttribute('data-analysis-report-id')).toBe(String(fixture.reports[1].id));
  const entry = preview.getByRole('button', { name: 'Past Reflections', exact: false });
  await entry.focus(); await page.keyboard.press('Enter');
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/timeline`);
  const scroll = page.getByTestId('timeline-scroll');
  await expect(page.locator(`[data-analysis-report-id="${fixture.reports[1].id}"]`)).toBeVisible();
  await expect(page.locator(`[data-analysis-id="${fixture.reports[1].id}"]`)).toHaveAttribute('data-date', '2026-10-14');
  const rows = await scroll.locator('[data-date]').evaluateAll(nodes => nodes.map(node => {
    const element = node as HTMLElement;
    return { top: Number.parseFloat(element.style.top), height: element.getBoundingClientRect().height };
  }).sort((a, b) => a.top - b.top));
  expect(rows.length).toBeGreaterThan(1);
  for (const row of rows) {
    expect(row.height).toBe(100);
    expect(row.top % 70).toBe(width === 375 ? 20 : 32);
  }
  for (let index = 1; index < rows.length; index += 1) expect(rows[index].top - rows[index - 1].top).toBe(70);
  await expect(page.getByRole('button', { name: 'Load earlier analyses' })).toHaveCount(0);
  const target = page.locator(`[data-analysis-report-id="${fixture.reports[1].id}"]`);
  const before = await scroll.evaluate(node => node.scrollTop);
  await target.focus(); await page.keyboard.press('Space');
  const reader = page.getByRole('region', { name: 'Analysis report', exact: true });
  await expect(reader.getByText('History insight 1', { exact: true })).toBeVisible();
  await expect(reader.getByRole('button', { name: 'Timeline', exact: false })).toBeFocused();
  await reader.getByRole('button', { name: 'Timeline', exact: false }).click();
  await expect(target).toBeFocused();
  expect(await scroll.evaluate(node => node.scrollTop)).toBe(before);
  fixture.historyMoreFailureOnce = true;
  await scroll.evaluate(node => { node.scrollTop = 0; });
  const retry = page.locator('[data-analysis-history-error="true"]');
  await expect(retry).toBeVisible();
  await expect(retry).toHaveAttribute('title', 'Analysis history could not be loaded.');
  const failedCursor = fixture.historyRequests.at(-1);
  const failedRequestIndex = fixture.historyRequests.length - 1;
  await retry.click();
  await expect(retry).toHaveCount(0);
  expect(fixture.historyRequests[failedRequestIndex + 1]).toBe(failedCursor);
  // Earlier recap pages use the original timeline load action and scrolling.
  for (let index = 0; index < 4; index += 1) {
    await scroll.evaluate(node => { node.scrollTop = 0; });
    await expect(page.getByRole('button', { name: 'Loading…', exact: true })).toHaveCount(0);
    if (await page.locator(`[data-analysis-report-id="${fixture.reports[30].id}"]`).count()) break;
    await page.getByRole('button', { name: 'Load earlier days', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Loading…', exact: true })).toHaveCount(0);
  }
  await expect(page.getByRole('button', { name: 'Load earlier analyses' })).toHaveCount(0);
  await scroll.evaluate(node => { node.scrollTop = 0; });
  const oldest = page.locator(`[data-analysis-report-id="${fixture.reports[30].id}"]`);
  await expect(oldest).toBeVisible();
  await expect(page.locator(`[data-analysis-id="${fixture.reports[30].id}"]`)).toHaveAttribute('data-date', '2025-10-01');
  await oldest.click();
  await reader.getByRole('button', { name: 'History insight 30', exact: false }).click();
  await expect(reader.getByText('Distinct report content 30', { exact: true })).toBeVisible();
  await reader.getByRole('button', { name: 'Timeline', exact: false }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath(`analysis-timeline-${width}.png`) });
  fixture.base.beginReflectionHistoryNavigation();
  await page.reload();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/timeline`);
  await expect(page.locator(`[data-analysis-report-id="${fixture.reports[1].id}"]`)).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/analysis`);
  await expect(page.getByRole('region', { name: 'Past Reflections', exact: true }).locator('[data-analysis-report-id]')).toHaveCount(3);
  fixture.base.endReflectionHistoryNavigation();
  expect(fixture.reportRequests).toEqual([]);
  expect(fixture.createRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});

test('history first-read failure retries while the original task and entry remain available', async ({ page }) => {
  const fixture = await installReflectionFixtures(page, { activeTaskOnLoad: true, taskStatus: 'CREATED', seedActiveTaskStorage: false });
  fixture.historyReadFailureUntilRetry = true;
  fixture.reports = historyFixtures(1);
  await openAnalysis(page);
  await expect(page.getByRole('alert').filter({ hasText: 'Analysis history could not be loaded.' })).toContainText('Analysis history could not be loaded.');
  await expect(page.getByRole('button', { name: 'Continue unstarted analysis', exact: false })).toBeVisible();
  fixture.historyReadFailureUntilRetry = false;
  await page.getByRole('alert').filter({ hasText: 'Analysis history could not be loaded.' }).getByRole('button', { name: 'Retry', exact: true }).click();
  await expect(page.locator('[data-analysis-report-id]')).toHaveCount(1);
  expect(fixture.startRequests).toEqual([]);
  expect(fixture.errors).toEqual([]);
});


test('visible analysis creation reaches saved preview and the same timeline report', async ({ page }) => {
  const fixture = await installReflectionFixtures(page);
  await installTimelineReads(page);
  await openAnalysis(page);
  await expect(page.getByRole('region', { name: 'Past Reflections', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Generate New Analysis', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Analysis report' }).getByText('Repeated concern', { exact: true })).toBeVisible();
  expect(fixture.createRequests).toHaveLength(1);
  expect(fixture.startRequests).toEqual([TASK_ID]);
  expect(fixture.eventRequests).toEqual([TASK_ID]);
  expect(fixture.reportRequests).toContain(TASK_ID);
  await page.getByRole('button', { name: 'Past Reflections', exact: false }).click();
  await expect(page.getByRole('region', { name: 'Past Reflections', exact: true }).locator('[data-analysis-report-id="9001"]')).toBeVisible();
  await page.getByRole('region', { name: 'Past Reflections', exact: true }).getByRole('button', { name: 'Past Reflections', exact: false }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/timeline`);
  const report = page.locator('[data-analysis-report-id="9001"]');
  await expect(report).toBeVisible();
  const writesBeforeReading = fixture.reportRequests.length;
  await report.click();
  await expect(page.getByRole('region', { name: 'Analysis report' }).getByText('Repeated concern', { exact: true })).toBeVisible();
  await page.getByRole('region', { name: 'Analysis report' }).getByRole('button', { name: 'Timeline', exact: false }).click();
  await expect(report).toBeFocused();
  expect(fixture.reportRequests.length).toBe(writesBeforeReading);
  expect(fixture.errors).toEqual([]);
  expect(fixture.base.getUnexpected()).toEqual([]);
});


test('timeline diary and historical picture still open beside an analysis report', async ({ page }) => {
  const fixture = await installReflectionFixtures(page);
  fixture.reports = historyFixtures(1);
  await page.clock.install({ time: new Date('2026-10-14T01:00:00Z') });
  const pictureDate = '2026-10-13';
  const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9H0AAAAASUVORK5CYII=';
  await page.route(/\/api\/sessions(?:\/range)?(?:\?|$)/, async route => {
    if (route.request().method() !== 'GET') { await route.fallback(); return; }
    await route.fulfill({ json: { sessions: [{ id: 'note_existing_qa', date_key: pictureDate,
      first_line: 'Original diary remains visible', created_at: `${pictureDate}T07:00:00Z`, updated_at: `${pictureDate}T07:00:00Z` }] } });
  });
  await page.route('**/api/pictures/range*', route => route.fulfill({ json: { pictures: [{ date: pictureDate, base64: png, prompt: 'Historical picture' }] } }));
  await page.route(`**/api/pictures/${pictureDate}/full`, route => route.fulfill({ json: { image_base64: png } }));
  await page.route('**/api/sessions/batch', route => route.fulfill({ json: { sessions: [{ id: 'note_existing_qa',
    editor_state: { cells: [], commentors: [] }, created_at: `${pictureDate}T07:00:00Z`, updated_at: `${pictureDate}T07:00:00Z` }] } }));
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`${WEB_BASE}/story-workspace/timeline`);
  await expect(page.getByText('Original diary remains visible', { exact: true })).toBeVisible();
  await page.getByRole('img', { name: 'Historical picture', exact: true }).click();
  await expect(page.getByText('Starred Comments', { exact: true })).toBeVisible();
  await expect(page.getByRole('img', { name: 'Generated image' })).toBeVisible();
  await expect(page.getByText('No comments for this day', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '×', exact: true }).click();
  await expect(page.getByText('Starred Comments', { exact: true })).toHaveCount(0);
  const report = page.locator(`[data-analysis-report-id="${fixture.reports[0].id}"]`);
  await report.click();
  const reader = page.getByRole('region', { name: 'Analysis report' });
  await reader.getByRole('button', { name: 'History insight 0', exact: false }).click();
  await expect(reader.getByText('Distinct report content 0', { exact: true })).toBeVisible();
  await reader.getByRole('button', { name: 'Timeline', exact: false }).click();
  await expect(page.getByText('Original diary remains visible', { exact: true })).toBeVisible();
  expect(fixture.errors).toEqual([]); expect(fixture.base.getUnexpected()).toEqual([]);
});
