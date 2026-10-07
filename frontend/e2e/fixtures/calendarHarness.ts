// [Sync] 2026-10-07: classify exact Chat-list and target-Thread schedule-relation aborts during result handoff.
// [Sync] 2026-10-07: capture the synchronous Thread-handoff phase before asynchronous request-header inspection.
// [Sync] 2026-10-07: serve v3 repeat, Chat mode, model snapshots and the callable model catalog through production DTO routes.
// [Sync] 2026-10-06: recognize injected Calendar documents metadata faults/cancellation on the exact public route.
// [Sync] 2026-10-06: measure borderless geometry and actual alpha layers over an opaque ancestor; long titles remain public DTO fixture data.
// [Sync] 2026-10-06: wait for the existing Modal initial focus before tab journeys; a test-only hook permits bounded first-frame readiness evidence.
// [Sync] 2026-10-07: measure actual workspace exterior/shadow space and natural height; long task/diary data uses public DTOs only.
// [Sync] 2026-10-07: bound the Chat thread handoff cancellation to its exact navigation phase, path, query, and referer.
// [Input] Production Next shell, intercepted authenticated session, calendar storage reads,
// scheduled-task DTOs, revisioned actions, and the canonical Chat thread navigation boundary.
// [Output] Provider-free Chrome receipts for Calendar task rows, result replacement, editor modal,
// fixed-month/exclusive-panel scroll geometry, and the existing task lifecycle without real persistence.
// [Pos] Technical isolated scheduled-task browser journey in frontend/e2e.
// [Sync] 2026-10-05: retain page-error stacks, explicitly classify AuthEntry cleanup and stub the unrelated development inspection script.
// [Sync] 2026-09-29: verify the desktop task/diary stack scrolls without moving the adjacent month paper, with single-column Calendar scrolling on narrower screens.
// [Sync] 2026-09-29: verify v4 composer, compact action rows, exact final-message result, and independent edit/history dialogs.
// [Sync] 2026-09-29: classify the result-view history abort during Chat handoff as expected cleanup.
// [Sync] 2026-09-29: assert the localized Tiptap composer by role and keep unsent-draft checks inside the message list.
// [Sync] 2026-09-29: assert refreshed trigger completion through the v4 compact-row state class.
// [Sync] 2026-09-29: keep paginated history older than the active trigger so refresh settlement is observed causally.
// [Sync] 2026-09-29: prove result rendering selects trigger.final_message_id even when the target Thread has a newer assistant reply.
// Business impact: scheduled definitions/revisions and trigger records change inside the isolated DTO fixture;
// the linked Chat Thread is the visible run-result consumer; diary records and normal Chat transport remain unchanged.

import { expect, type Locator, type Page, type Route } from '@playwright/test';

export const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:55173';
export const TASK_ID = 'st_browser_qa_20260929';
export const TASK_DATE = '2026-09-28';
export const TASK_ONLY_DATE = '2026-09-29';
export const TARGET_THREAD_ID = 'thread_target_schedule_qa';
export const CSRF = 's'.repeat(43);



type TaskStatus = 'active' | 'paused' | 'exhausted' | 'deleted';
type TriggerStatus = 'claimed' | 'queued' | 'running' | 'succeeded' | 'failed' | 'state_unknown' | 'skipped';
export type TaskRule =
  | { kind: 'once'; local_date: string; local_time: string; time_zone: string; selected_offset_minutes: number | null }
  | { kind: 'daily'; local_time: string; time_zone: string }
  | { kind: 'interval'; interval_minutes: number; time_zone: string }
  | { kind: 'hourly'; interval_hours: number; minute: number; time_zone: string }
  | { kind: 'weekly'; weekdays: Array<'MO' | 'TU' | 'WE' | 'TH' | 'FR' | 'SA' | 'SU'>; local_time: string; time_zone: string };
type Task = {
  id: string; source_thread_id: string; title: string; prompt: string; rule: TaskRule;
  run_thread_mode: 'source_thread' | 'new_thread_each_run'; model_alias: string | null;
  next_run_at: string | null; status: TaskStatus; revision: number;
  created_at: string; updated_at: string;
};
type Trigger = {
  id: string; task_id: string; kind: 'manual' | 'scheduled'; scheduled_at: string | null;
  definition_revision: number; title: string; source_thread_id: string;
  time_zone: string; status: TriggerStatus; task_session_id: string | null;
  target_thread_id: string | null; input_message_id: string | null;
  target_turn_id: string | null; final_message_id: string | null; error_code: string | null;
  skipped_from_at: string | null; skipped_through_at: string | null;
  run_thread_mode_snapshot: 'source_thread' | 'new_thread_each_run'; model_alias_snapshot: string | null;
  created_at: string; updated_at: string;
};

type FixtureOptions = {
  empty?: boolean;
  taskStatus?: TaskStatus;
  initialTriggerStatus?: TriggerStatus;
  initialTriggerHasThread?: boolean;
  firstRunOutcome?: 'server_error' | 'network_unknown' | 'success';
  firstEditConflict?: boolean;
  editErrorCodes?: string[];
  historyCount?: number;
  dayStartsUnavailable?: boolean;
  notionFaults?: boolean;
  authEntryLifecycle?: boolean;
  longTitle?: boolean;
  taskCount?: number;
  diaryCount?: number;
};

function baseTask(status: TaskStatus = 'active'): Task {
  return {
    id: TASK_ID,
    source_thread_id: 'thread_schedule_source',
    title: '晨间复盘',
    prompt: '整理今天的笔记',
    rule: { kind: 'daily', local_time: '09:00', time_zone: 'UTC' },
    run_thread_mode: 'new_thread_each_run', model_alias: 'dream-balanced',
    next_run_at: status === 'active' ? '2026-09-29T09:00:00Z' : null,
    status,
    revision: 1,
    created_at: '2026-09-27T08:00:00Z',
    updated_at: '2026-09-27T08:00:00Z',
  };
}

function baseTrigger(task: Task, status: TriggerStatus, hasThread = status === 'succeeded'): Trigger {
  return {
    id: `trigger_${status}`, task_id: task.id, kind: 'manual', scheduled_at: null,
    definition_revision: task.revision, title: task.title, source_thread_id: task.source_thread_id,
    time_zone: task.rule.time_zone, status, task_session_id: 'session_schedule_qa',
    target_thread_id: hasThread ? TARGET_THREAD_ID : null,
    input_message_id: null, target_turn_id: null,
    final_message_id: status === 'succeeded' ? 'message_schedule_final' : null,
    error_code: status === 'failed' ? 'SCHEDULE_EXECUTION_FAILED' : null,
    skipped_from_at: null, skipped_through_at: null,
    run_thread_mode_snapshot: task.run_thread_mode, model_alias_snapshot: task.model_alias,
    created_at: '2026-09-28T09:01:00Z', updated_at: '2026-09-28T09:01:00Z',
  };
}

export async function installFixtures(page: Page, options: FixtureOptions = {}) {
  let diaryDeleted = false;
  let taskCount = options.taskCount ?? 1;
  let task = baseTask(options.taskStatus);
  if (options.longTitle) task = { ...task, title: '晨间复盘与长期写作资料整理：'.repeat(8) };
  let triggers: Trigger[] = options.initialTriggerStatus
    ? [baseTrigger(task, options.initialTriggerStatus, options.initialTriggerHasThread)] : [];
  let firstEditConflict = options.firstEditConflict ?? true;
  const editErrorCodes = [...(options.editErrorCodes ?? [])];
  let firstRunPending = options.firstRunOutcome !== 'success';
  let dayReadCount = 0;
  let dayUnavailable = options.dayStartsUnavailable ?? false;
  let completeRunningOnNextDayRead = false;
  const unexpected: string[] = [];
  const manualRequestKeys: string[] = [];
  const definitionRequests: Array<{ action: string; revision: unknown }> = [];
  const editBodies: Array<Record<string, unknown>> = [];
  const historyRequests: string[] = [];
  const targetThreadRequests: string[] = [];
  let threadHandoffStage = false;
  const threadHandoffAborts: Array<{ method: string; path: string; query: string; error: string; pagePath: string; refererPath: string }> = [];
  const configuredHistory = options.historyCount === undefined ? null
    : Array.from({ length: options.historyCount }, (_, index) => {
        const createdAt = new Date(Date.UTC(2026, 8, 28, 8, 30 - index)).toISOString();
        return { ...baseTrigger(task, 'succeeded', true), id: `trigger_history_${index}`,
          created_at: createdAt, updated_at: createdAt };
      });

  // Reuse the repository's deterministic fixture for this optional Next dev tool.
  await page.route(/^https?:\/\/unpkg\.com\/react-grab\/dist\/index\.global\.js$/, async (route) => {
    await route.fulfill({ contentType: 'application/javascript', body: '' });
  });

  page.on('console', (message) => {
    const expectedResponse = message.text().includes('409 (Conflict)') || message.text().includes('503 (Service Unavailable)')
      || (Boolean(options.editErrorCodes?.length) && message.text().includes('400 (Bad Request)'));
    const expectedUnknownRun = options.firstRunOutcome === 'network_unknown'
      && message.text() === 'Failed to load resource: net::ERR_CONNECTION_RESET';
    const expectedNotionFault = options.notionFaults && /\/api\/connectors(?:\/[^/]+\/notion\/(?:documents|today))?(?:\?|$)/.test(message.location().url)
      && /(?:401|403|404|429|502|503|ERR_INTERNET_DISCONNECTED|ERR_ABORTED)/.test(message.text());
    if (message.type() === 'error' && !message.text().includes('react-grab.com')
      && !expectedResponse && !expectedUnknownRun && !expectedNotionFault) {
      unexpected.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => unexpected.push(`pageerror: ${error.stack ?? error.message}`));
  page.on('requestfailed', async (request) => {
    const url = request.url();
    const path = new URL(url).pathname;
    const parsedUrl = new URL(url);
    const failure = request.failure()?.errorText ?? 'failed';
    // Capture the synchronous lifecycle phase before awaiting headers. The
    // caller may end the handoff phase while this listener is suspended.
    const threadHandoffStageAtFailure = threadHandoffStage;
    const requestHeaders = await request.allHeaders();
    const referer = requestHeaders.referer ?? '';
    const refererPath = referer ? new URL(referer).pathname : '';
    const expectedThreadHandoffAbort = threadHandoffStageAtFailure
      && request.method() === 'GET'
      && parsedUrl.pathname === '/api/claude-agent/threads'
      && parsedUrl.search === '?limit=21'
      && failure === 'net::ERR_ABORTED'
      && new URL(page.url()).pathname === '/story-workspace/chat'
      && refererPath === '/story-workspace/chat';
    const expectedChatListNavigationAbort = request.method() === 'GET'
      && parsedUrl.pathname === '/api/claude-agent/threads'
      && parsedUrl.search === '?limit=21'
      && failure === 'net::ERR_ABORTED'
      && new URL(page.url()).pathname === '/story-workspace/chat'
      && refererPath === '/story-workspace/chat';
    const expectedNavigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && path === '/api/sessions/events';
    const expectedDreamListNavigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && path === '/api/story-workspace/dream-runs';
    const expectedScheduledResultNavigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && path === `/api/claude-agent/threads/${TARGET_THREAD_ID}/messages`;
    const expectedScheduledRelationNavigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && path === `/api/claude-agent/threads/${TARGET_THREAD_ID}/scheduled-tasks`
      && new URL(page.url()).pathname === '/story-workspace/chat';
    const expectedUnknownRun = options.firstRunOutcome === 'network_unknown'
      && path === `/api/claude-agent/scheduled-tasks/${TASK_ID}/run`;
    const expectedNotionCancellation = options.notionFaults && /^\/api\/connectors\/[^/]+\/notion\/(?:documents|today)$/.test(path)
      && ['net::ERR_ABORTED', 'net::ERR_INTERNET_DISCONNECTED'].includes(request.failure()?.errorText ?? '');
    const expectedAuthEntryCancellation = options.authEntryLifecycle && request.method() === 'GET'
      && path === '/auth/options' && request.failure()?.errorText === 'net::ERR_ABORTED';
    if (expectedThreadHandoffAbort) {
      threadHandoffAborts.push({ method: request.method(), path, query: parsedUrl.search,
        error: failure, pagePath: new URL(page.url()).pathname, refererPath });
      return;
    }
    if (!url.includes('react-grab.com') && !url.includes('fonts.googleapis.com')
      && !expectedNavigationAbort && !expectedDreamListNavigationAbort && !expectedChatListNavigationAbort
      && !expectedScheduledResultNavigationAbort && !expectedUnknownRun && !expectedNotionCancellation
      && !expectedScheduledRelationNavigationAbort
      && !expectedAuthEntryCancellation) {
      unexpected.push(`request: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });

  await page.route('**/auth/session', async (route) => {
    await route.fulfill({ json: {
      user: { id: '20260929', email: 'scheduled-calendar@example.test', display_name: 'Schedule QA', avatar_url: null, role: 'user', created_at: '2026-09-01T00:00:00Z' },
      csrf_token: CSRF,
    } });
  });
  await page.route('**/api/**', async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (path.includes(TARGET_THREAD_ID)) targetThreadRequests.push(`${request.method()} ${path}`);

    if (path === '/api/sessions' && request.method() === 'GET') {
      await route.fulfill({ json: { sessions: diaryDeleted ? [] : Array.from({ length: options.diaryCount ?? 1 }, (_, index) => ({
        id: index === 0 ? 'note_existing_qa' : `note_layout_qa_${index}`, created_at: `${TASK_DATE}T07:30:00Z`, updated_at: `${TASK_DATE}T07:30:00Z`, date_key: TASK_DATE,
        first_line: options.longTitle ? '普通日历笔记与长标题的完整浏览旅程：'.repeat(8) : index === 0 ? '普通日历笔记仍然可见' : `普通日历笔记 ${index}`,
      })) } });
      return;
    }
    if (path === '/api/sessions/note_existing_qa') {
      if (request.method() === 'DELETE') { diaryDeleted = true; await route.fulfill({ json: { success: true } }); }
      else await route.fulfill({ json: { id: 'note_existing_qa', name: '普通日历笔记仍然可见', created_at: `${TASK_DATE}T07:30:00Z`, updated_at: `${TASK_DATE}T07:30:00Z`, editor_state: { id: 'note_existing_qa', createdAt: `${TASK_DATE}T07:30:00Z`, cells: [{ id: 'text-fixture', type: 'text', content: '普通日历笔记仍然可见' }], commentors: [], tasks: [], weightPath: [], overlappedPhrases: [], notFoundPhrases: [] } } });
      return;
    }
    if (path === '/api/sessions' && request.method() === 'POST') {
      await route.fulfill({ status: 200, json: {} });
      return;
    }
    if (path === '/api/preferences') {
      await route.fulfill({ json: { first_login_completed: true, timezone: 'UTC' } });
      return;
    }
    if (path === '/api/sessions/events') {
      await route.fulfill({ contentType: 'text/event-stream', body: ': connected\n\n' });
      return;
    }
    if (path === '/api/gateway/models' && request.method() === 'GET') {
      await route.fulfill({ json: { data: [{
        modelAlias: 'dream-balanced', displayName: 'Dream Balanced', protocol: 'anthropic', capabilities: {},
        contextWindow: 200000, maxOutputTokens: 8192, enabled: true, callable: true,
        availability: 'included', requiredPlanCode: null, upgradeHint: null,
      }, {
        modelAlias: 'dream-fast', displayName: 'Dream Fast', protocol: 'anthropic', capabilities: {},
        contextWindow: 200000, maxOutputTokens: 8192, enabled: true, callable: true,
        availability: 'included', requiredPlanCode: null, upgradeHint: null,
      }], defaultModelAlias: 'dream-balanced' } });
      return;
    }
    if (path.startsWith('/api/claude-agent/scheduled-tasks')) {
      const suffix = path.slice('/api/claude-agent/scheduled-tasks'.length);
      if (suffix === '/day') {
        const selectedDate = url.searchParams.get('local_date');
        if (dayUnavailable) {
          await route.fulfill({ status: 503, json: { detail: { error_code: 'ADMIN_DATA_UNAVAILABLE' } } });
          return;
        }
        const visible = !options.empty && (selectedDate === TASK_DATE || selectedDate === TASK_ONLY_DATE);
        if (visible) {
          dayReadCount += 1;
          if (completeRunningOnNextDayRead) {
            completeRunningOnNextDayRead = false;
            triggers = triggers.map((trigger) => trigger.status === 'running'
              ? { ...trigger, status: 'succeeded', target_thread_id: TARGET_THREAD_ID,
                  final_message_id: 'message_schedule_final', updated_at: '2026-09-28T09:03:00Z' }
              : trigger);
          }
        }
        await route.fulfill({ json: { tasks: visible ? [...Array.from({ length: Math.max(0, taskCount - 1) }, (_, index) => ({ ...task,
          id: `${TASK_ID}_layout_${index}`, title: `完整任务列表行 ${index}` })), task] : [], triggers: visible ? triggers : [] } });
        return;
      }
      if (suffix === `/${TASK_ID}`) {
        await route.fulfill({ json: { task } });
        return;
      }
      if (suffix === `/${TASK_ID}/history`) {
        historyRequests.push(url.search);
        const before = url.searchParams.get('before_created_at');
        const limit = Number(url.searchParams.get('limit') ?? 50);
        const source = configuredHistory ?? triggers;
        const page = source.filter((trigger) => !before || trigger.created_at < before).slice(0, limit);
        await route.fulfill({ json: { triggers: page } });
        return;
      }
      const action = suffix.split('/').at(-1);
      if (request.method() === 'POST' && action) {
        const body = request.postDataJSON() as Record<string, unknown>;
        if (action === 'edit') {
          definitionRequests.push({ action, revision: body.expected_revision });
          editBodies.push(body);
          const editErrorCode = editErrorCodes.shift();
          if (editErrorCode) {
            await route.fulfill({ status: 400, json: { detail: { error_code: editErrorCode } } });
            return;
          }
          if (firstEditConflict) {
            firstEditConflict = false;
            task = { ...task, title: '服务端更新后的复盘', revision: task.revision + 1, updated_at: '2026-09-28T09:02:00Z' };
            await route.fulfill({ status: 409, json: { detail: { error_code: 'SCHEDULE_REVISION_CONFLICT' } } });
            return;
          }
          if (body.expected_revision !== task.revision) {
            await route.fulfill({ status: 409, json: { detail: { error_code: 'SCHEDULE_REVISION_CONFLICT' } } });
            return;
          }
          task = { ...task, title: String(body.title), prompt: String(body.prompt), rule: body.rule as TaskRule,
            run_thread_mode: body.run_thread_mode as Task['run_thread_mode'], model_alias: String(body.model_alias),
            revision: task.revision + 1, updated_at: '2026-09-28T09:03:00Z' };
          await route.fulfill({ json: { task } });
          return;
        }
        if (['pause', 'resume', 'delete', 'restore'].includes(action)) {
          definitionRequests.push({ action, revision: body.expected_revision });
          if (body.expected_revision !== task.revision) {
            await route.fulfill({ status: 409, json: { detail: { error_code: 'SCHEDULE_REVISION_CONFLICT' } } });
            return;
          }
          const status: TaskStatus = action === 'pause' ? 'paused'
            : action === 'resume' || action === 'restore' ? 'active' : 'deleted';
          task = { ...task, status, next_run_at: status === 'active' ? '2026-09-30T09:00:00Z' : null,
            revision: task.revision + 1, updated_at: '2026-09-28T09:04:00Z' };
          await route.fulfill({ json: { task } });
          return;
        }
        if (action === 'run') {
          manualRequestKeys.push(String(body.manual_request_key));
          if (firstRunPending) {
            firstRunPending = false;
            if (options.firstRunOutcome === 'network_unknown') {
              await route.abort('connectionreset');
            } else {
              await route.fulfill({ status: 503, json: { detail: { error_code: 'SCHEDULE_RUN_FAILED' } } });
            }
            return;
          }
          const trigger = baseTrigger(task, 'succeeded', true);
          triggers = [trigger, ...triggers.filter((item) => item.id !== trigger.id)];
          await route.fulfill({ json: { trigger } });
          return;
        }
      }
    }

    if (path === `/api/claude-agent/threads/${TARGET_THREAD_ID}/messages`) {
      await route.fulfill({ json: {
        thread: { id: TARGET_THREAD_ID, title: '定时任务执行会话', created_at: '2026-09-28T09:01:00Z', updated_at: '2026-09-28T09:02:00Z' },
        messages: [{ id: 'scheduled-user', role: 'user', parts: [{ type: 'text', text: '整理今天的笔记' }], metadata: {}, created_at: '2026-09-28T09:01:00Z' },
          { id: 'message_schedule_final', role: 'assistant', parts: [{ type: 'text', text: '## 定时任务执行完成\n\n已整理今天的笔记。' }], metadata: {}, created_at: '2026-09-28T09:02:00Z' },
          { id: 'message_after_schedule_final', role: 'assistant', parts: [{ type: 'text', text: '这是一条更晚的普通回复，不能作为定时任务结果。' }], metadata: {}, created_at: '2026-09-28T09:04:00Z' }],
        next_cursor: null, has_more: false, latest_message_id: 'message_after_schedule_final', unchanged: false,
      } });
      return;
    }
    if (path === `/api/claude-agent/threads/${TARGET_THREAD_ID}/status`) {
      await route.fulfill({ json: { running: false, lifecycle: 'idle', turn_count: 1,
        pending_tool_call_ids: [], tool_confirmation_observation: 'known' } });
      return;
    }
    if (path === `/api/claude-agent/threads/${TARGET_THREAD_ID}/inputs`) {
      await route.fulfill({ json: { entries: [], local_owner: true } });
      return;
    }
    if (path === `/api/claude-agent/threads/${TARGET_THREAD_ID}/task-links`) {
      await route.fulfill({ json: { source: null, created: [] } });
      return;
    }
    if (path === `/api/claude-agent/threads/${TARGET_THREAD_ID}/stream`) {
      await route.fulfill({ contentType: 'text/event-stream', body: ': connected\n\n' });
      return;
    }

    // Boot calls unrelated to this isolated UI contract are production-shaped empty reads.
    // No request writes a backend, database, model or worker; diary writes stay in memory.
    if (request.method() === 'GET') {
      await route.fulfill({ json: path === '/api/decks' ? { decks: [] }
        : path === '/api/default-voices' ? {} : path === '/api/claude-agent/threads' ? { threads: [] } : {} });
      return;
    }
    unexpected.push(`unexpected API ${request.method()} ${path}`);
    await route.fulfill({ status: 501, json: { error: { code: 'UNEXPECTED_E2E_API' } } });
  });

  await page.addInitScript(() => {
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  });
  return {
    getUnexpected: () => unexpected,
    getManualRequestKeys: () => manualRequestKeys,
    getDefinitionRequests: () => definitionRequests,
    getEditBodies: () => editBodies,
    getHistoryRequests: () => historyRequests,
    getDayReadCount: () => dayReadCount,
    getTargetThreadRequests: () => targetThreadRequests,
    beginThreadHandoff: () => { threadHandoffStage = true; },
    endThreadHandoff: () => { threadHandoffStage = false; },
    getThreadHandoffAborts: () => [...threadHandoffAborts],
    allowDayReads: () => { dayUnavailable = false; },
    completeRunningOnNextDayRead: () => { completeRunningOnNextDayRead = true; },
    setTaskCount: (count: number) => { taskCount = count; },
  };
}

export async function openCalendar(page: Page, viewport = { width: 1440, height: 900 },
  options: { beforeOpen?: () => Promise<void>; waitForInitialFocus?: boolean } = {}) {
  await page.clock.setFixedTime(new Date('2026-09-28T12:00:00Z'));
  await page.setViewportSize(viewport);
  await page.goto(`${WEB_BASE}/story-workspace/writing`);
  const calendarButton = page.getByRole('button', { name: 'Calendar' });
  await expect(calendarButton).toBeVisible();
  await options.beforeOpen?.();
  await calendarButton.focus();
  await calendarButton.press('Enter');
  const dialog = page.getByRole('dialog', { name: '日历' });
  await expect(dialog).toBeVisible();
  if (options.waitForInitialFocus !== false) {
    await expect(dialog.getByRole('button', { name: '← 上个月', exact: true })).toBeFocused();
  }
  return { calendarButton, dialog };
}

export async function openMore(card: Locator) {
  await card.getByRole('button', { name: /更多操作/ }).click();
}

export async function readFloatingPaperSafety(dialog: Locator) {
  return dialog.evaluate((element) => {
    const layout = element.querySelector('.calendar-popup');
    const workspace = element.querySelector('.calendar-popup__workspace');
    const calendar = element.querySelector('.calendar-popup__calendar');
    const panel = element.querySelector('[role=tabpanel]:not([hidden])');
    if (!(layout instanceof HTMLElement) || !(workspace instanceof HTMLElement)
      || !(calendar instanceof HTMLElement) || !(panel instanceof HTMLElement)) {
      throw new Error('calendar floating exterior/scroll structure is incomplete');
    }
    const usesLayoutScroll = getComputedStyle(layout).overflowY === 'auto';
    const owner = usesLayoutScroll ? layout : panel;
    const calendarTopBefore = calendar.getBoundingClientRect().top;
    const previousScrollTop = owner.scrollTop;
    owner.scrollTop = owner.scrollHeight;
    const layoutRect = layout.getBoundingClientRect();
    const paperRects = [calendar, workspace].map((paper) => paper.getBoundingClientRect());
    const style = getComputedStyle(layout);
    const result = {
      paddingLeft: Number.parseFloat(style.paddingLeft), paddingRight: Number.parseFloat(style.paddingRight),
      paddingBottom: Number.parseFloat(style.paddingBottom),
      leftGap: Math.min(...paperRects.map((rect) => rect.left - layoutRect.left)),
      rightGap: Math.min(...paperRects.map((rect) => layoutRect.right - rect.right)),
      bottomGap: layoutRect.bottom - Math.max(...paperRects.map((rect) => rect.bottom)),
      maxScrollTop: owner.scrollHeight - owner.clientHeight,
      reachedScrollBottom: Math.abs(owner.scrollTop - (owner.scrollHeight - owner.clientHeight)) <= 1,
      scrollOwner: usesLayoutScroll ? 'layout' : 'stack',
      fixedCalendarDelta: usesLayoutScroll ? null : Math.abs(calendar.getBoundingClientRect().top - calendarTopBefore),
      workspaceExterior: { top: paperRects[1].top, bottom: paperRects[1].bottom, height: paperRects[1].height },
    };
    owner.scrollTop = previousScrollTop;
    return result;
  });
}

export function expectFloatingPaperSafety(
  safety: Awaited<ReturnType<typeof readFloatingPaperSafety>>,
  expected: { side: number; bottom: number },
) {
  expect(safety.paddingLeft).toBeGreaterThanOrEqual(expected.side - 1);
  expect(safety.paddingRight).toBeGreaterThanOrEqual(expected.side - 1);
  expect(safety.paddingBottom).toBeGreaterThanOrEqual(expected.bottom - 1);
  expect(safety.leftGap).toBeGreaterThanOrEqual(expected.side - 1);
  expect(safety.rightGap).toBeGreaterThanOrEqual(expected.side - 1);
  expect(safety.bottomGap).toBeGreaterThanOrEqual(expected.bottom - 1);
  expect(safety.reachedScrollBottom).toBe(true);
}

export async function readCalendarVisualMetrics(dialog: Locator) {
  return dialog.evaluate((root) => {
    const canvas = document.createElement('canvas'); canvas.width = 1; canvas.height = 1;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Contrast canvas unavailable');
    const pixels = () => Array.from(context.getImageData(0, 0, 1, 1).data);
    const paint = (color: string) => { context.fillStyle = color; context.fillRect(0, 0, 1, 1); };
    const backgroundFor = (element: Element) => {
      const layers: string[] = [];
      let opaqueOwner: string | null = null;
      for (let current: Element | null = element; current; current = current.parentElement) {
        const style = getComputedStyle(current);
        if (style.backgroundImage !== 'none' || Number.parseFloat(style.opacity) !== 1
          || style.filter !== 'none' || style.mixBlendMode !== 'normal') {
          throw new Error(`Unmeasured contrast layer: ${current.className}`);
        }
        layers.push(style.backgroundColor);
        context.clearRect(0, 0, 1, 1); paint(style.backgroundColor);
        if (pixels()[3] === 255) { opaqueOwner = current.className; break; }
      }
      if (opaqueOwner === null) throw new Error('Contrast has no actual opaque ancestor');
      context.clearRect(0, 0, 1, 1);
      layers.reverse().forEach(paint);
      const values = pixels();
      if (values[3] !== 255) throw new Error('Contrast composition is not opaque');
      return { color: `rgb(${values.slice(0, 3).join(', ')})`, layers, opaqueOwner };
    };
    const luminance = (values: number[]) => values.slice(0, 3).map((value) => value / 255)
      .map((value) => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
      .reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
    const contrast = (element: Element, foreground = getComputedStyle(element).color) => {
      const background = backgroundFor(element);
      context.clearRect(0, 0, 1, 1); paint(background.color);
      const backgroundLuminance = luminance(pixels());
      paint(foreground);
      const [low, high] = [backgroundLuminance, luminance(pixels())].sort((a, b) => a - b);
      return { foreground, background, ratio: (high + .05) / (low + .05) };
    };
    const required = (selector: string) => {
      const element = root.querySelector<HTMLElement>(selector);
      if (!element) throw new Error(`Calendar visual target missing: ${selector}`);
      return element;
    };
    const surface = (element: Element) => {
      const style = getComputedStyle(element);
      return { borders: [style.borderTopWidth, style.borderRightWidth, style.borderBottomWidth, style.borderLeftWidth],
        radius: style.borderRadius, corners: [style.borderTopLeftRadius, style.borderTopRightRadius, style.borderBottomRightRadius, style.borderBottomLeftRadius],
        shadow: style.boxShadow, background: style.backgroundColor };
    };
    const tabsElement = required('.calendar-popup__tabs');
    const layoutElement = required('.calendar-popup');
    const calendarElement = required('.calendar-popup__calendar');
    const workspaceElement = required('.calendar-popup__workspace');
    const panel = required('[role="tabpanel"]:not([hidden])');
    // Sticky tabs move over their own panel while scrolling; the natural seam
    // must be measured before that translation, without losing the user's scroll.
    const visualPaperJoin = Math.abs(tabsElement.getBoundingClientRect().bottom - panel.getBoundingClientRect().top);
    const originalScrollTop = layoutElement.scrollTop;
    let paperJoin = visualPaperJoin;
    if (getComputedStyle(tabsElement).position === 'sticky') {
      try {
        layoutElement.scrollTop = 0;
        paperJoin = Math.abs(tabsElement.getBoundingClientRect().bottom - panel.getBoundingClientRect().top);
      } finally { layoutElement.scrollTop = originalScrollTop; }
    }
    const dayBoxes = Array.from(calendarElement.querySelectorAll('.calendar-popup__day, .calendar-popup__day-placeholder'))
      .map((day) => day.getBoundingClientRect());

    const heading = required('[role="tabpanel"]:not([hidden]) .calendar-popup__section-heading');
    const body = required('[role="tabpanel"]:not([hidden]) .calendar-popup__card-body');
    const rect = (element: Element) => {
      const box = element.getBoundingClientRect();
      return { left: box.left, right: box.right, top: box.top, bottom: box.bottom, width: box.width, height: box.height };
    };
    const contentLeft = (element: Element) => element.getBoundingClientRect().left
      + Number.parseFloat(getComputedStyle(element).paddingLeft);
    const focused = document.activeElement instanceof HTMLElement && root.contains(document.activeElement)
      ? document.activeElement : null;
    const focusStyle = focused ? getComputedStyle(focused) : null;
    const tooltip = root.querySelector('[role="tooltip"]');
    const rows = Array.from(panel.querySelectorAll('.calendar-popup__task, .calendar-popup__diary, .calendar-popup__undo-row, .calendar-popup__notion-group li'));
    const actionElements = Array.from(panel.querySelectorAll<HTMLElement>('.calendar-popup__refresh-link, .calendar-popup__notion-group a'))
      .filter((element) => element.getClientRects().length > 0 && !element.matches(':disabled'));
    return {
      tabs: Array.from(tabsElement.querySelectorAll<HTMLElement>('[role="tab"]')).map((element) => ({
        name: element.getAttribute('aria-label'), selected: element.getAttribute('aria-selected') === 'true',
        ...surface(element), rawBackground: getComputedStyle(element).backgroundColor, ...contrast(element),
      })),
      focus: focused && focusStyle ? { visible: focused.matches(':focus-visible'), style: focusStyle.outlineStyle,
        width: Number.parseFloat(focusStyle.outlineWidth), ...contrast(Number.parseFloat(focusStyle.outlineOffset) < 0
          ? focused : focused.parentElement ?? focused, focusStyle.outlineColor) } : null,
      tooltip: tooltip ? { ...contrast(tooltip), rect: rect(tooltip) } : null,
      actions: actionElements.map((element) => ({ text: element.textContent?.trim(), ...contrast(element) })),
      surfaces: { workspace: surface(required('.calendar-popup__workspace')), tabs: surface(tabsElement), panel: surface(panel), calendar: surface(required('.calendar-popup__calendar')) },
      rows: rows.map(surface),
      headingBorder: getComputedStyle(heading).borderBottomWidth,
      alignment: [contentLeft(tabsElement), contentLeft(heading), contentLeft(body)],
      paperJoin, visualPaperJoin,
      naturalStack: { gap: workspaceElement.getBoundingClientRect().top - calendarElement.getBoundingClientRect().bottom,
        expectedGap: Number.parseFloat(getComputedStyle(layoutElement).rowGap),
        calendarContentBottomGap: calendarElement.getBoundingClientRect().bottom - Math.max(...dayBoxes.map((box) => box.bottom)),
        calendarPaddingBottom: Number.parseFloat(getComputedStyle(calendarElement).paddingBottom),
        stickyTop: tabsElement.getBoundingClientRect().top,
        stickyExpectedTop: Math.min(Math.max(workspaceElement.getBoundingClientRect().top, layoutElement.getBoundingClientRect().top
          + Number.parseFloat(getComputedStyle(layoutElement).paddingTop) + Number.parseFloat(getComputedStyle(tabsElement).top)),
          workspaceElement.getBoundingClientRect().bottom - tabsElement.getBoundingClientRect().height) },
      rightRects: [rect(required('.calendar-popup__workspace')), rect(tabsElement), rect(panel)],
      heights: { workspace: rect(required('.calendar-popup__workspace')).height, calendar: rect(required('.calendar-popup__calendar')).height,
        available: required('.calendar-popup').clientHeight - Number.parseFloat(getComputedStyle(required('.calendar-popup')).paddingTop)
          - Number.parseFloat(getComputedStyle(required('.calendar-popup')).paddingBottom),
        panelClient: panel.clientHeight, panelScroll: panel.scrollHeight },
      scrollOwner: getComputedStyle(required('.calendar-popup')).overflowY === 'auto' ? 'layout' : 'panel',
      panelOverflow: getComputedStyle(panel).overflowY,
      tabsPosition: getComputedStyle(tabsElement).position,
      paperToken: getComputedStyle(root).getPropertyValue('--color-bg-paper').trim(),
    };
  });
}
