// [Input] Production Next shell, intercepted authenticated session, calendar storage reads,
// scheduled-task DTOs, revisioned actions, and the canonical Chat thread navigation boundary.
// [Output] Provider-free Chrome receipts for the fixed-month/scrolling-paper-stack CalendarPopup journeys
// and its existing task lifecycle, without database, model, scheduled worker, or diary mutation.
// [Pos] Technical isolated scheduled-task browser journey in frontend/e2e.
// [Sync] 2026-09-29: verify the desktop task/diary stack scrolls without moving the adjacent month paper, with single-column Calendar scrolling on narrower screens.

import { expect, test, type Locator, type Page, type Route } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:55173';
const TASK_ID = 'st_browser_qa_20260929';
const TASK_DATE = '2026-09-28';
const TASK_ONLY_DATE = '2026-09-29';
const TARGET_THREAD_ID = 'thread_target_schedule_qa';
const CSRF = 's'.repeat(43);

test.use({ channel: 'chrome' });
test.describe.configure({ mode: 'serial' });

type TaskStatus = 'active' | 'paused' | 'exhausted' | 'deleted';
type TriggerStatus = 'claimed' | 'queued' | 'running' | 'succeeded' | 'failed' | 'state_unknown' | 'skipped';
type TaskRule =
  | { kind: 'once'; local_date: string; local_time: string; time_zone: string; selected_offset_minutes: number | null }
  | { kind: 'daily'; local_time: string; time_zone: string };
type Task = {
  id: string; source_thread_id: string; title: string; prompt: string; rule: TaskRule;
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
};

function baseTask(status: TaskStatus = 'active'): Task {
  return {
    id: TASK_ID,
    source_thread_id: 'thread_schedule_source',
    title: '晨间复盘',
    prompt: '整理今天的笔记',
    rule: { kind: 'daily', local_time: '09:00', time_zone: 'UTC' },
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
    created_at: '2026-09-28T09:01:00Z', updated_at: '2026-09-28T09:01:00Z',
  };
}

async function installFixtures(page: Page, options: FixtureOptions = {}) {
  let task = baseTask(options.taskStatus);
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
  const configuredHistory = options.historyCount === undefined ? null
    : Array.from({ length: options.historyCount }, (_, index) => {
        const createdAt = new Date(Date.UTC(2026, 8, 28, 9, 30 - index)).toISOString();
        return { ...baseTrigger(task, 'succeeded', true), id: `trigger_history_${index}`,
          created_at: createdAt, updated_at: createdAt };
      });

  page.on('console', (message) => {
    const expectedResponse = message.text().includes('409 (Conflict)') || message.text().includes('503 (Service Unavailable)')
      || (Boolean(options.editErrorCodes?.length) && message.text().includes('400 (Bad Request)'));
    const expectedUnknownRun = options.firstRunOutcome === 'network_unknown'
      && message.text() === 'Failed to load resource: net::ERR_CONNECTION_RESET';
    if (message.type() === 'error' && !message.text().includes('react-grab.com')
      && !expectedResponse && !expectedUnknownRun) {
      unexpected.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => unexpected.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const url = request.url();
    const path = new URL(url).pathname;
    const expectedNavigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && path === '/api/sessions/events';
    const expectedDreamListNavigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && path === '/api/story-workspace/dream-runs';
    const expectedUnknownRun = options.firstRunOutcome === 'network_unknown'
      && path === `/api/claude-agent/scheduled-tasks/${TASK_ID}/run`;
    if (!url.includes('react-grab.com') && !url.includes('fonts.googleapis.com')
      && !expectedNavigationAbort && !expectedDreamListNavigationAbort && !expectedUnknownRun) {
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
      await route.fulfill({ json: { sessions: [{ id: 'note_existing_qa', created_at: `${TASK_DATE}T07:30:00Z`, updated_at: `${TASK_DATE}T07:30:00Z`, date_key: TASK_DATE, first_line: '普通日历笔记仍然可见' }] } });
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
        await route.fulfill({ json: { tasks: visible ? [task] : [], triggers: visible ? triggers : [] } });
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
          { id: 'scheduled-final', role: 'assistant', parts: [{ type: 'text', text: '定时任务执行完成' }], metadata: {}, created_at: '2026-09-28T09:02:00Z' }],
        next_cursor: null, has_more: false, latest_message_id: 'scheduled-final', unchanged: false,
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
    // No request writes a backend, database, model, worker, or diary.
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
    allowDayReads: () => { dayUnavailable = false; },
    completeRunningOnNextDayRead: () => { completeRunningOnNextDayRead = true; },
  };
}

async function openCalendar(page: Page, viewport = { width: 1440, height: 900 }) {
  await page.clock.setFixedTime(new Date('2026-09-28T12:00:00Z'));
  await page.setViewportSize(viewport);
  await page.goto(`${WEB_BASE}/story-workspace/writing`);
  const calendarButton = page.getByRole('button', { name: 'Calendar' });
  await expect(calendarButton).toBeVisible();
  await calendarButton.focus();
  await calendarButton.press('Enter');
  const dialog = page.getByRole('dialog', { name: '日历' });
  await expect(dialog).toBeVisible();
  return { calendarButton, dialog };
}

async function openMore(card: Locator) {
  await card.getByRole('button', { name: /更多操作/ }).click();
}

async function readFloatingPaperSafety(dialog: Locator) {
  return dialog.evaluate((element) => {
    const layout = element.querySelector('.calendar-popup');
    const stack = element.querySelector('.calendar-popup__workspace-scroll');
    if (!(layout instanceof HTMLElement) || !(stack instanceof HTMLElement)) {
      throw new Error('calendar floating-paper scroll regions are incomplete');
    }
    const usesLayoutScroll = getComputedStyle(layout).overflowY === 'auto';
    const content = usesLayoutScroll ? layout : stack;
    const papers = Array.from(usesLayoutScroll
      ? element.querySelectorAll('.calendar-popup__calendar, .calendar-popup__section')
      : stack.querySelectorAll(':scope > .calendar-popup__section'));
    if (papers.length !== (usesLayoutScroll ? 3 : 2)
      || papers.some((paper) => !(paper instanceof HTMLElement))) {
      throw new Error('calendar floating-paper geometry is incomplete');
    }
    const calendar = element.querySelector('.calendar-popup__calendar');
    const calendarTopBefore = calendar?.getBoundingClientRect().top ?? null;
    const previousScrollTop = content.scrollTop;
    content.scrollTop = content.scrollHeight;
    const contentRect = content.getBoundingClientRect();
    const paperRects = papers.map((paper) => paper.getBoundingClientRect());
    const style = getComputedStyle(content);
    const result = {
      paddingLeft: Number.parseFloat(style.paddingLeft),
      paddingRight: Number.parseFloat(style.paddingRight),
      paddingBottom: Number.parseFloat(style.paddingBottom),
      leftGap: Math.min(...paperRects.map((rect) => rect.left - contentRect.left)),
      rightGap: Math.min(...paperRects.map((rect) => contentRect.right - rect.right)),
      bottomGap: contentRect.bottom - Math.max(...paperRects.map((rect) => rect.bottom)),
      maxScrollTop: content.scrollHeight - content.clientHeight,
      reachedScrollBottom: Math.abs(content.scrollTop - (content.scrollHeight - content.clientHeight)) <= 1,
      scrollOwner: usesLayoutScroll ? 'layout' : 'stack',
      fixedCalendarDelta: usesLayoutScroll || calendarTopBefore === null || !calendar
        ? null : Math.abs(calendar.getBoundingClientRect().top - calendarTopBefore),
    };
    content.scrollTop = previousScrollTop;
    return result;
  });
}

function expectFloatingPaperSafety(
  safety: Awaited<ReturnType<typeof readFloatingPaperSafety>>,
  expected: { side: number; bottom: number },
) {
  expect(safety.paddingLeft).toBe(expected.side);
  expect(safety.paddingRight).toBe(expected.side);
  expect(safety.leftGap).toBeGreaterThanOrEqual(expected.side - 1);
  expect(safety.rightGap).toBeGreaterThanOrEqual(expected.side - 1);
  expect(safety.bottomGap).toBeGreaterThanOrEqual(expected.bottom - 1);
  expect(safety.reachedScrollBottom).toBe(true);
}

test('desktop journey follows the reviewed task-before-diary lifecycle', async ({ page }, testInfo) => {
  const fixture = await installFixtures(page, { firstRunOutcome: 'server_error' });
  const { dialog } = await openCalendar(page);

  const workspace = dialog.locator('.calendar-popup__workspace');
  const stack = workspace.locator('.calendar-popup__workspace-scroll');
  const taskSection = stack.locator(':scope > .calendar-popup__task-section');
  const diarySection = stack.locator(':scope > .calendar-popup__diary-section');
  await expect(taskSection.locator('.calendar-popup__card-count')).toHaveText('1 项');
  await expect(diarySection.locator('.calendar-popup__card-count')).toHaveText('1 篇');
  await expect(dialog.getByText('普通日历笔记仍然可见')).toBeVisible();
  await expect(dialog.getByText('晨间复盘')).toBeVisible();
  expect(await dialog.locator('.calendar-popup__section-heading h3').allTextContents()).toEqual(['今天的定时任务', '今天的日记']);
  await expect(dialog.locator('.calendar-popup__date-summary')).toHaveCount(0);
  expect(await taskSection.evaluate((element) =>
    element.nextElementSibling?.classList.contains('calendar-popup__diary-section'))).toBe(true);
  const cardBoxes = await Promise.all([taskSection.boundingBox(), diarySection.boundingBox()]);
  expect(cardBoxes[0] && cardBoxes[1] && cardBoxes[1].y > cardBoxes[0].y + cardBoxes[0].height).toBeTruthy();
  const closeBox = await dialog.getByRole('button', { name: '关闭' }).boundingBox();
  const paperBoxes = await Promise.all([
    dialog.locator('.calendar-popup__calendar').boundingBox(), taskSection.boundingBox(), diarySection.boundingBox(),
  ]);
  expect(closeBox && paperBoxes.every((paper) => paper && (
    closeBox.x + closeBox.width <= paper.x || paper.x + paper.width <= closeBox.x
    || closeBox.y + closeBox.height <= paper.y || paper.y + paper.height <= closeBox.y
  ))).toBeTruthy();
  const surfaces = await dialog.evaluate((element) => {
    const dialogStyle = getComputedStyle(element);
    const workspaceElement = element.querySelector('.calendar-popup__workspace');
    if (!(workspaceElement instanceof HTMLElement)) throw new Error('calendar workspace is missing');
    const workspaceStyle = getComputedStyle(workspaceElement);
    const papers = Array.from(element.querySelectorAll('.calendar-popup__calendar, .calendar-popup__section')).map((paper) => {
      const style = getComputedStyle(paper);
      return { borderWidth: style.borderTopWidth, background: style.backgroundColor, boxShadow: style.boxShadow };
    });
    const task = element.querySelector('.calendar-popup__task');
    const fact = element.querySelector('.calendar-popup__task-facts > div');
    return {
      dialog: {
        borderWidth: dialogStyle.borderTopWidth,
        background: dialogStyle.backgroundColor,
        boxShadow: dialogStyle.boxShadow,
      },
      workspace: {
        borderWidth: workspaceStyle.borderTopWidth,
        background: workspaceStyle.backgroundColor,
        boxShadow: workspaceStyle.boxShadow,
      },
      papers,
      task: task ? {
        borderWidth: getComputedStyle(task).borderTopWidth,
        background: getComputedStyle(task).backgroundColor,
        boxShadow: getComputedStyle(task).boxShadow,
      } : null,
      factBackground: fact ? getComputedStyle(fact).backgroundColor : null,
    };
  });
  expect(surfaces.dialog).toEqual({ borderWidth: '0px', background: 'rgba(0, 0, 0, 0)', boxShadow: 'none' });
  expect(surfaces.workspace).toEqual({ borderWidth: '0px', background: 'rgba(0, 0, 0, 0)', boxShadow: 'none' });
  expect(surfaces.papers).toHaveLength(3);
  expect(surfaces.papers.every((paperStyle) => paperStyle.borderWidth !== '0px'
    && paperStyle.background !== 'rgba(0, 0, 0, 0)' && paperStyle.boxShadow !== 'none')).toBe(true);
  expect(surfaces.task).toEqual({ borderWidth: '0px', background: 'rgba(0, 0, 0, 0)', boxShadow: 'none' });
  expect(surfaces.factBackground).toBe('rgba(0, 0, 0, 0)');
  const hiddenTitle = await dialog.locator('.modal-title--default').evaluate((element) => {
    const style = getComputedStyle(element);
    return { position: style.position, width: style.width, height: style.height, clip: style.clip };
  });
  expect(hiddenTitle).toEqual({ position: 'absolute', width: '1px', height: '1px', clip: 'rect(0px, 0px, 0px, 0px)' });
  const desktopSafety = await readFloatingPaperSafety(dialog);
  expect(desktopSafety.scrollOwner).toBe('stack');
  expect(desktopSafety.fixedCalendarDelta).toBeLessThanOrEqual(1);
  expectFloatingPaperSafety(desktopSafety, { side: 36, bottom: 56 });
  await expect(dialog.getByRole('gridcell', { name: /2026.*9.*29/ })).not.toHaveClass(/calendar-popup__day--has-entry/);

  const card = dialog.locator('.calendar-popup__task').first();
  await openMore(card);
  await card.getByRole('menuitem', { name: /编辑/ }).click();
  await card.getByLabel('标题').fill('新的每日复盘');
  await card.getByLabel('执行提示词').fill('整理新的笔记');
  await card.getByRole('button', { name: /保存：/ }).click();
  await expect(card.getByRole('alert').filter({ hasText: '最新已生效配置' })).toContainText('服务端更新后的复盘');
  await expect(card.getByLabel('标题')).toHaveValue('新的每日复盘');
  await card.getByRole('button', { name: /基于最新版本保存/ }).click();
  await expect(card).toContainText('新的每日复盘');
  expect(fixture.getDefinitionRequests().slice(0, 2)).toEqual([
    { action: 'edit', revision: 1 }, { action: 'edit', revision: 2 },
  ]);

  await card.getByRole('button', { name: /暂停：/ }).click();
  await expect(card).toContainText('已暂停');
  await expect(card).toContainText('恢复后重新计算下一次执行');
  await card.getByRole('button', { name: /恢复：/ }).click();
  await expect(card).toContainText('已启用');
  await expect(card).toContainText('9月30日');

  await card.getByRole('button', { name: /立即运行：/ }).click();
  await expect(card.getByRole('alert').filter({ hasText: '任务更新失败' })).toBeVisible();
  await card.getByRole('button', { name: /立即运行：/ }).click();
  await expect(card).toContainText('已完成');
  expect(fixture.getManualRequestKeys()).toHaveLength(2);
  expect(fixture.getManualRequestKeys()[1]).not.toBe(fixture.getManualRequestKeys()[0]);

  await openMore(card);
  await card.getByRole('menuitem', { name: /历史/ }).click();
  await expect(card.getByRole('heading', { name: /执行历史/ })).toBeVisible();
  await expect(card).toContainText('手动执行');
  await expect(card.locator('.calendar-popup__history').getByRole('button', { name: /打开会话/ })).toBeVisible();

  await openMore(card);
  await card.getByRole('menuitem', { name: /删除/ }).click();
  const undo = dialog.locator('.calendar-popup__undo-row');
  await expect(undo).toContainText('已删除“新的每日复盘”');
  await undo.getByRole('button', { name: /撤销删除/ }).click();
  const restored = dialog.locator('.calendar-popup__task').first();
  await expect(restored).toContainText('已启用');
  await testInfo.attach('calendar-floating-wide', {
    body: await page.screenshot({ fullPage: true }), contentType: 'image/png',
  });

  await restored.locator('.calendar-popup__primary-actions').getByRole('button', { name: /打开会话/ }).click();
  await expect(page).toHaveURL(/\/story-workspace\/chat$/);
  await expect(dialog).toBeHidden();
  await expect.poll(() => fixture.getTargetThreadRequests().some((item) => item.includes(TARGET_THREAD_ID))).toBe(true);
  expect(fixture.getUnexpected()).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBeTruthy();
});

test('mobile exhausted state keeps unknown execution safe and menu keyboard-operable', async ({ page }, testInfo) => {
  const fixture = await installFixtures(page, {
    taskStatus: 'exhausted', initialTriggerStatus: 'state_unknown', initialTriggerHasThread: true,
    firstRunOutcome: 'success',
  });
  const { dialog } = await openCalendar(page, { width: 390, height: 844 });
  const card = dialog.locator('.calendar-popup__task').first();

  await expect(card.getByRole('button', { name: /立即运行/ })).toBeDisabled();
  await expect(card.locator('.calendar-popup__primary-actions').getByRole('button', { name: /打开会话/ })).toHaveCount(0);
  const attention = dialog.getByRole('button', { name: '有 1 项需处理' });
  await attention.click();
  await expect(card).toBeFocused();

  const more = card.getByRole('button', { name: /更多操作/ });
  await more.click();
  const historyItem = card.getByRole('menuitem', { name: /历史/ });
  const deleteItem = card.getByRole('menuitem', { name: /删除/ });
  await expect(historyItem).toBeFocused();
  await expect(card.getByRole('menuitem', { name: /编辑/ })).toHaveCount(0);
  await page.keyboard.press('ArrowDown');
  await expect(deleteItem).toBeFocused();
  await page.keyboard.press('ArrowUp');
  await expect(historyItem).toBeFocused();
  await historyItem.click();
  await expect(card.getByRole('button', { name: /打开会话/ })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(card.getByRole('heading', { name: /执行历史/ })).toHaveCount(0);
  await expect(more).toBeFocused();

  const calendarBox = await dialog.locator('.calendar-popup__calendar').boundingBox();
  const taskBox = await dialog.locator('.calendar-popup__task-section').boundingBox();
  const diaryBox = await dialog.locator('.calendar-popup__diary-section').boundingBox();
  expect(calendarBox && taskBox && diaryBox
    && taskBox.y > calendarBox.y + calendarBox.height
    && diaryBox.y > taskBox.y + taskBox.height).toBeTruthy();
  const mobileSafety = await readFloatingPaperSafety(dialog);
  expect(mobileSafety.scrollOwner).toBe('layout');
  expectFloatingPaperSafety(mobileSafety, { side: 16, bottom: 24 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBeTruthy();
  await testInfo.attach('calendar-floating-mobile', {
    body: await page.screenshot({ fullPage: true }), contentType: 'image/png',
  });
  expect(fixture.getUnexpected()).toEqual([]);
});

test('tablet breakpoint keeps one scroll owner and switches cleanly to two columns', async ({ page }, testInfo) => {
  const fixture = await installFixtures(page, { firstRunOutcome: 'success' });
  const { dialog } = await openCalendar(page, { width: 1024, height: 768 });
  const calendar = dialog.locator('.calendar-popup__calendar');
  const taskSection = dialog.locator('.calendar-popup__task-section');
  const diarySection = dialog.locator('.calendar-popup__diary-section');

  const singleColumnBoxes = await Promise.all([calendar.boundingBox(), taskSection.boundingBox(), diarySection.boundingBox()]);
  expect(singleColumnBoxes[0] && singleColumnBoxes[1] && singleColumnBoxes[2]
    && singleColumnBoxes[1].y > singleColumnBoxes[0].y + singleColumnBoxes[0].height
    && singleColumnBoxes[2].y > singleColumnBoxes[1].y + singleColumnBoxes[1].height).toBeTruthy();
  const closeBox = await dialog.getByRole('button', { name: '关闭' }).boundingBox();
  expect(closeBox && singleColumnBoxes.every((paper) => paper && (
    closeBox.x + closeBox.width <= paper.x || paper.x + paper.width <= closeBox.x
    || closeBox.y + closeBox.height <= paper.y || paper.y + paper.height <= closeBox.y
  ))).toBeTruthy();
  const scrollOwners = await dialog.evaluate((element) => {
    const content = element.querySelector(':scope > .modal-content--default');
    const layout = element.querySelector('.calendar-popup');
    const stack = element.querySelector('.calendar-popup__workspace-scroll');
    if (!(content instanceof HTMLElement) || !(layout instanceof HTMLElement) || !(stack instanceof HTMLElement)) {
      throw new Error('calendar scroll structure is incomplete');
    }
    return {
      content: getComputedStyle(content).overflowY,
      layout: getComputedStyle(layout).overflowY,
      stack: getComputedStyle(stack).overflowY,
    };
  });
  expect(scrollOwners).toEqual({ content: 'hidden', layout: 'auto', stack: 'visible' });
  const tabletSafety = await readFloatingPaperSafety(dialog);
  expect(tabletSafety.scrollOwner).toBe('layout');
  expectFloatingPaperSafety(tabletSafety, { side: 20, bottom: 32 });

  await page.setViewportSize({ width: 1025, height: 768 });
  const twoColumnBoxes = await Promise.all([calendar.boundingBox(), taskSection.boundingBox()]);
  expect(twoColumnBoxes[0] && twoColumnBoxes[1]
    && twoColumnBoxes[1].x > twoColumnBoxes[0].x + twoColumnBoxes[0].width
    && Math.abs(twoColumnBoxes[1].y - twoColumnBoxes[0].y) <= 1).toBeTruthy();
  const desktopScrollOwners = await dialog.evaluate((element) => ({
    layout: getComputedStyle(element.querySelector('.calendar-popup') as HTMLElement).overflowY,
    stack: getComputedStyle(element.querySelector('.calendar-popup__workspace-scroll') as HTMLElement).overflowY,
  }));
  expect(desktopScrollOwners).toEqual({ layout: 'hidden', stack: 'auto' });
  const contentFits = await dialog.locator('.calendar-popup').evaluate((element) =>
    element.scrollWidth <= element.clientWidth + 1);
  expect(contentFits).toBeTruthy();
  await testInfo.attach('calendar-floating-tablet-boundary', {
    body: await page.screenshot({ fullPage: true }), contentType: 'image/png',
  });

  await page.setViewportSize({ width: 1440, height: 480 });
  const shortViewportDialogBox = await dialog.boundingBox();
  const shortViewportCalendarTop = (await calendar.boundingBox())?.y;
  const monthScroll = await calendar.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
    return {
      overflowY: getComputedStyle(element).overflowY,
      maxScrollTop: element.scrollHeight - element.clientHeight,
      reachedBottom: Math.abs(element.scrollTop - (element.scrollHeight - element.clientHeight)) <= 1,
    };
  });
  expect(monthScroll.overflowY).toBe('auto');
  expect(monthScroll.maxScrollTop).toBeGreaterThan(0);
  expect(monthScroll.reachedBottom).toBe(true);
  await expect(calendar.getByRole('gridcell', { name: /2026.*9.*30/ })).toBeVisible();
  expect((await calendar.boundingBox())?.y).toBeCloseTo(shortViewportCalendarTop ?? 0, 0);
  expect(shortViewportDialogBox && shortViewportDialogBox.height <= 416 + 1).toBeTruthy();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBeTruthy();
  expect(fixture.getUnexpected()).toEqual([]);
});

test('unknown manual-run response reuses one request key before creating a second run', async ({ page }) => {
  const fixture = await installFixtures(page, { firstRunOutcome: 'network_unknown' });
  const { dialog } = await openCalendar(page);
  const card = dialog.locator('.calendar-popup__task').first();

  await card.getByRole('button', { name: /立即运行：/ }).click();
  await expect(card.getByRole('alert').filter({ hasText: '正在确认是否已创建本次执行' })).toBeVisible();
  await card.getByRole('button', { name: /核查运行请求：/ }).click();
  await expect(card).toContainText('已完成');
  expect(fixture.getManualRequestKeys()).toHaveLength(2);
  expect(fixture.getManualRequestKeys()[1]).toBe(fixture.getManualRequestKeys()[0]);
  expect(fixture.getUnexpected()).toEqual([]);
});

test('task-free date keeps an independent empty task card beside diary content', async ({ page }) => {
  const fixture = await installFixtures(page, { empty: true, firstRunOutcome: 'success' });
  const { dialog } = await openCalendar(page);
  const taskSection = dialog.locator('.calendar-popup__task-section');
  await expect(taskSection).toHaveCount(1);
  await expect(taskSection.getByRole('heading', { name: '今天的定时任务' })).toBeVisible();
  await expect(taskSection.locator('.calendar-popup__card-count')).toHaveText('0 项');
  await expect(taskSection.getByText('这一天没有定时任务。')).toBeVisible();
  await expect(dialog.getByRole('heading', { name: '今天的日记' })).toBeVisible();
  await expect(dialog.getByText('普通日历笔记仍然可见')).toBeVisible();
  expect(fixture.getUnexpected()).toEqual([]);
});

test('task read failure stays inside its card while diary remains actionable', async ({ page }) => {
  const fixture = await installFixtures(page, {
    dayStartsUnavailable: true,
    firstRunOutcome: 'success',
  });
  const { dialog } = await openCalendar(page);
  const taskSection = dialog.locator('.calendar-popup__task-section');
  const diarySection = dialog.locator('.calendar-popup__diary-section');
  await expect(taskSection.getByRole('alert')).toContainText('任务暂不可用。');
  await expect(diarySection.getByText('普通日历笔记仍然可见')).toBeVisible();
  await expect(diarySection.getByRole('button', { name: '打开: 普通日历笔记仍然可见' })).toBeEnabled();
  await expect(diarySection.getByRole('button', { name: '删除: 普通日历笔记仍然可见' })).toBeEnabled();
  fixture.allowDayReads();
  await taskSection.getByRole('button', { name: '重试' }).click();
  await expect(taskSection.getByText('晨间复盘')).toBeVisible();
  await expect(diarySection.getByText('普通日历笔记仍然可见')).toBeVisible();
  expect(fixture.getUnexpected()).toEqual([]);
});

test('active execution refreshes to a terminal result and history loads older pages by cursor', async ({ page }) => {
  const fixture = await installFixtures(page, {
    initialTriggerStatus: 'running', initialTriggerHasThread: true,
    historyCount: 21, firstRunOutcome: 'success',
  });
  const { dialog } = await openCalendar(page);
  const card = dialog.locator('.calendar-popup__task').first();

  await expect(card).toContainText('执行中');
  fixture.completeRunningOnNextDayRead();
  await expect(card).toContainText('已完成', { timeout: 7_000 });
  expect(fixture.getDayReadCount()).toBeGreaterThanOrEqual(2);
  const settledReadCount = fixture.getDayReadCount();
  await page.waitForTimeout(2_300);
  expect(fixture.getDayReadCount()).toBe(settledReadCount);

  await openMore(card);
  await card.getByRole('menuitem', { name: /历史/ }).click();
  const history = card.locator('.calendar-popup__history');
  await expect(history.getByRole('listitem')).toHaveCount(20);
  await history.getByRole('button', { name: /加载更早记录/ }).click();
  await expect(history.getByRole('listitem')).toHaveCount(21);
  await expect(history.getByRole('button', { name: /加载更早记录/ })).toHaveCount(0);
  const safety = await readFloatingPaperSafety(dialog);
  expect(safety.maxScrollTop).toBeGreaterThan(0);
  expect(safety.scrollOwner).toBe('stack');
  expect(safety.fixedCalendarDelta).toBeLessThanOrEqual(1);
  expectFloatingPaperSafety(safety, { side: 36, bottom: 56 });
  expect(fixture.getHistoryRequests().some((search) => search.includes('before_created_at='))).toBe(true);
  expect(fixture.getUnexpected()).toEqual([]);
});

test('edit keeps the desired draft and explains repeated or missing daylight-saving times', async ({ page }) => {
  const fixture = await installFixtures(page, {
    firstEditConflict: false,
    editErrorCodes: ['SCHEDULE_OFFSET_REQUIRED', 'SCHEDULE_LOCAL_TIME_MISSING'],
    firstRunOutcome: 'success',
  });
  const { dialog } = await openCalendar(page);
  const card = dialog.locator('.calendar-popup__task').first();

  await openMore(card);
  await card.getByRole('menuitem', { name: /编辑/ }).click();
  await card.getByLabel('计划').selectOption('once');
  await card.getByLabel('日期').fill('2026-11-01');
  await card.getByLabel('时间').fill('01:30');
  await card.getByLabel('时区').fill('America/New_York');
  await card.getByRole('button', { name: /保存：/ }).click();
  await expect(card.getByRole('alert')).toContainText('该当地时间因时钟调整会出现两次');
  await expect(card.getByLabel('时间')).toHaveValue('01:30');

  await card.getByLabel('日期').fill('2026-03-08');
  await card.getByLabel('时间').fill('02:30');
  await card.getByRole('button', { name: /保存：/ }).click();
  await expect(card.getByRole('alert')).toContainText('这个当地时间因时钟调整而不存在');
  await expect(card.getByLabel('时间')).toHaveValue('02:30');

  await card.getByLabel('时间').fill('03:30');
  await card.getByRole('button', { name: /保存：/ }).click();
  await expect(card).toContainText('2026-03-08 03:30 (America/New_York)');
  expect(fixture.getEditBodies().slice(0, 2).map((body) => (body.rule as TaskRule).kind === 'once'
    ? (body.rule as Extract<TaskRule, { kind: 'once' }>).selected_offset_minutes : 'daily')).toEqual([null, null]);
  expect(fixture.getUnexpected()).toEqual([]);
});
