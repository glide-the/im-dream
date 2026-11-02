// [Input] Original Reflections public task/report/candidate DTO fixtures and Calendar auth boundary.
// [Output] One provider-free server fixture reused by Web and native component journeys.
// [Pos] Technical harness only; normal services, CLI, models and data remain untouched.
// [Sync] 2026-10-29: extract the existing fixture and serve the current bulk Deck catalog DTO.
import type {Page} from '@playwright/test';
import {installFixtures,isReflectionHistoryCancellation,isReflectionHistoryNavigationCancellation} from './calendarHarness';
export type Section = 'echoes' | 'traits' | 'patterns';

export type TaskStatus = 'CREATED' | 'RUNNING' | 'COMPLETED' | 'PARTIAL_FAILED' | 'FAILED';

export type CandidateStatus = 'ready' | 'empty' | 'no_snapshot' | 'auth_required' | 'scope_changed' | 'disconnected';

export type FixtureResult = {
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

export type SectionState = {
  section: Section;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  result_count: number;
  revision: number;
  started_at: string | null;
  completed_at: string | null;
  error_summary: string | null;
};

export type FixtureTask = {
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

export type FixtureReport = {
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

export type FixtureState = {
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

export const TASK_ID = '6f6f5df3-0d11-4d63-8f4d-9e8a0f20c901';

export const CONNECTOR_ID = '0d4f8f4b-3d9d-4fb9-8c73-5f7be4d8a101';

export const DECK_ID = '95a7f432-8f36-46f5-9b1c-8a6d6d9d2102';

export const AGENT_ID = '3db8e47f-16c7-4ac0-9e76-cb7f1f504203';

export const PAGE_ID = '8ca4f9d1-7a63-4a0b-8f7d-1e6c3b2d5404';

export const ECHO_RESULT_ID = '1b6d8e2f-3c40-4f51-9a62-7e8d9c0b1205';

export const TRAIT_RESULT_ID = '2c7e9f30-4d51-4a62-8b73-8f9e0a1c2306';

export const PATTERN_RESULT_ID = '3d8fa041-5e62-4b73-9c84-9a0f1b2d3407';

export const SNAPSHOT_VERSION = 'snapshot-reflection-browser-v1';

export const BODY_HASH = 'a'.repeat(64);

export const resultFor = (section: Section): FixtureResult => ({
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

export const contentSummary = (includeNotion: boolean, includeAgent = false, emptyNotion = false): Record<string, unknown> | null => ({
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

export function makeTask(state: FixtureState, status = state.taskStatus): FixtureTask {
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

export function makeReport(state: FixtureState): FixtureReport {
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

export function candidateResponse(state: FixtureState) {
  const ready = state.candidateStatus === 'ready';
  return {
    status: state.candidateStatus,
    page_count: ready ? state.candidatePageCount : 0,
    snapshot_version: ready ? state.candidateSnapshot : null,
    connector_id: ready ? CONNECTOR_ID : undefined,
    selection_available: true,
  };
}

export function event(type: string, sequence: number, payload: Record<string, unknown> = {}) {
  return {
    id: `event-${sequence}`, task_id: TASK_ID, type, sequence,
    created_at: `2026-10-13T03:00:0${Math.min(sequence, 9)}Z`, payload,
  };
}

export async function installReflectionFixtures(page: Page, options: {
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
          || (message.text().includes('Failed to load voices from decks') && (value.endsWith(' /api/decks') || value.endsWith(' /api/decks/catalog')))))) return;
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
    const deck={ id: DECK_ID, name: 'Editorial Lens', name_en: 'Editorial Lens', name_zh: '编辑视角', description: 'Analysis fixture', icon: 'brain', color: 'blue',
      is_system: false, enabled: true, agent_type: 'chat', agent_type_revision: 1, voices: [voice] };
    await route.fulfill({ json: new URL(route.request().url()).pathname === '/api/decks/catalog' ? {decks:[deck]} : deck });
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