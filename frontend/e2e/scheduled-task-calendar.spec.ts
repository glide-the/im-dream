// [Input] Production Next shell, intercepted authenticated session, calendar
// storage reads, and scheduled-task DTOs with revisioned actions.
// [Output] Provider-free browser receipt for CalendarPopup schedule cards and
// the ordinary calendar note surface without database or model mutation.
// [Pos] Technical isolated scheduled-task browser journey in frontend/e2e.
// [Sync] 2026-09-28: cover visible task/history lifecycle and retry semantics.

import { expect, test, type Page, type Route } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:55173';
const TASK_ID = 'st_browser_qa_20260928';
const TASK_DATE = '2026-09-28';
const TOKEN = 'scheduled-task-calendar-technical-token';
const CSRF = 's'.repeat(43);

test.use({ channel: 'chrome' });
test.describe.configure({ mode: 'serial' });

type TaskStatus = 'active' | 'paused' | 'exhausted' | 'deleted';
type Task = {
  id: string; source_thread_id: string; title: string; prompt: string;
  rule: { kind: 'daily'; local_time: string; time_zone: string };
  next_run_at: string | null; status: TaskStatus; revision: number;
  created_at: string; updated_at: string;
};
type Trigger = {
  id: string; task_id: string; kind: 'manual' | 'scheduled'; scheduled_at: string | null;
  definition_revision: number; title: string; source_thread_id: string;
  time_zone: string; status: 'failed' | 'succeeded'; task_session_id: string | null;
  target_thread_id: string | null; input_message_id: string | null;
  target_turn_id: string | null; final_message_id: string | null; error_code: string | null;
  skipped_from_at: string | null; skipped_through_at: string | null;
  created_at: string; updated_at: string;
};

function baseTask(): Task {
  return {
    id: TASK_ID,
    source_thread_id: 'thread_schedule_source',
    title: '晨间复盘',
    prompt: '整理今天的笔记',
    rule: { kind: 'daily', local_time: '09:00', time_zone: 'UTC' },
    next_run_at: '2026-09-29T09:00:00Z',
    status: 'active',
    revision: 1,
    created_at: '2026-09-27T08:00:00Z',
    updated_at: '2026-09-27T08:00:00Z',
  };
}

function baseTrigger(task: Task, status: Trigger['status'], errorCode: string | null): Trigger {
  return {
    id: `trigger_${status}`, task_id: task.id, kind: 'manual', scheduled_at: null,
    definition_revision: task.revision, title: task.title, source_thread_id: task.source_thread_id,
    time_zone: task.rule.time_zone, status, task_session_id: 'session_schedule_qa',
    target_thread_id: status === 'succeeded' ? 'thread_target_schedule_qa' : null,
    input_message_id: null, target_turn_id: null, final_message_id: null, error_code: errorCode,
    skipped_from_at: null, skipped_through_at: null,
    created_at: '2026-09-28T09:01:00Z', updated_at: '2026-09-28T09:01:00Z',
  };
}

async function installFixtures(page: Page) {
  let task = baseTask();
  let triggers: Trigger[] = [];
  let firstEditConflict = true;
  let firstRunFailure = true;
  const unexpected: string[] = [];

  page.on('console', (message) => {
    const expectedResponse = message.text().includes('409 (Conflict)') || message.text().includes('503 (Service Unavailable)');
    if (message.type() === 'error' && !message.text().includes('react-grab.com') && !expectedResponse) {
      unexpected.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => unexpected.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const url = request.url();
    const expectedNavigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && new URL(url).pathname === '/api/sessions/events';
    if (!url.includes('react-grab.com') && !url.includes('fonts.googleapis.com') && !expectedNavigationAbort) {
      unexpected.push(`request: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });

  await page.route('**/auth/session', async (route) => {
    await route.fulfill({ json: {
      user: { id: '20260928', email: 'scheduled-calendar@example.test', display_name: 'Schedule QA', avatar_url: null, role: 'user', created_at: '2026-09-01T00:00:00Z' },
      csrf_token: CSRF,
    } });
  });
  await page.route('**/api/**', async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === '/api/sessions' && request.method() === 'GET') {
      await route.fulfill({ json: { sessions: [{ id: 'note_existing_qa', created_at: `${TASK_DATE}T07:30:00Z`, updated_at: `${TASK_DATE}T07:30:00Z`, date_key: TASK_DATE, first_line: '普通日历笔记仍然可见' }] } });
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
        await route.fulfill({ json: { tasks: task.status === 'deleted' ? [task] : [task], triggers } });
        return;
      }
      if (suffix === `/${TASK_ID}`) {
        await route.fulfill({ json: { task } });
        return;
      }
      if (suffix === `/${TASK_ID}/history`) {
        await route.fulfill({ json: { triggers } });
        return;
      }
      const action = suffix.split('/').at(-1);
      if (request.method() === 'POST' && action) {
        const body = request.postDataJSON() as Record<string, unknown>;
        if (action === 'edit') {
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
          task = { ...task, title: String(body.title), prompt: String(body.prompt), revision: task.revision + 1, updated_at: '2026-09-28T09:03:00Z' };
          await route.fulfill({ json: { task } });
          return;
        }
        if (['pause', 'resume', 'delete', 'restore'].includes(action)) {
          if (body.expected_revision !== task.revision) {
            await route.fulfill({ status: 409, json: { detail: { error_code: 'SCHEDULE_REVISION_CONFLICT' } } });
            return;
          }
          const status: TaskStatus = action === 'pause' ? 'paused' : action === 'resume' || action === 'restore' ? 'active' : 'deleted';
          task = { ...task, status, revision: task.revision + 1, updated_at: '2026-09-28T09:04:00Z' };
          await route.fulfill({ json: { task } });
          return;
        }
        if (action === 'run') {
          if (firstRunFailure) {
            firstRunFailure = false;
            await route.fulfill({ status: 503, json: { detail: { error_code: 'SCHEDULE_RUN_FAILED' } } });
            return;
          }
          const trigger = baseTrigger(task, 'succeeded', null);
          triggers = [...triggers, trigger];
          await route.fulfill({ json: { task, trigger } });
          return;
        }
      }
    }

    // Boot calls unrelated to this isolated UI contract are production-shaped
    // empty reads. No request writes a backend, database, model, or note.
    if (request.method() === 'GET') {
      await route.fulfill({ json: path === '/api/decks' ? { decks: [] } : path === '/api/default-voices' ? {} : path === '/api/claude-agent/threads' ? { threads: [] } : {} });
      return;
    }
    unexpected.push(`unexpected API ${request.method()} ${path}`);
    await route.fulfill({ status: 501, json: { error: { code: 'UNEXPECTED_E2E_API' } } });
  });

  await page.addInitScript(({ token }) => {
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
    void token;
  }, { token: TOKEN });
  return { getUnexpected: () => unexpected };
}

test('CalendarPopup completes visible schedule lifecycle and preserves ordinary notes', async ({ page }) => {
  const { getUnexpected } = await installFixtures(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${WEB_BASE}/story-workspace/writing`);

  await expect(page.getByRole('button', { name: 'Calendar' })).toBeVisible();
  // Writing's state chooser can cover the floating toolbar; keyboard
  // activation exercises the same labeled control without hiding that UI.
  await page.getByRole('button', { name: 'Calendar' }).focus();
  await page.getByRole('button', { name: 'Calendar' }).press('Enter');
  await expect(page.getByText('普通日历笔记仍然可见')).toBeVisible();
  await expect(page.getByText('晨间复盘')).toBeVisible();
  await expect(page.getByText('每天 09:00').or(page.getByText('每天 09:00', { exact: false })).first()).toBeVisible();

  const card = page.locator('article').filter({ has: page.getByRole('button', { name: '历史' }) }).first();
  await card.getByRole('button', { name: '编辑' }).click();
  await card.getByLabel('标题').fill('新的每日复盘');
  await card.getByLabel('执行提示词').fill('整理新的笔记');
  await card.getByRole('button', { name: '保存' }).click();
  await expect(page.getByRole('alert').filter({ hasText: '任务已变化' })).toBeVisible();
  await expect(card.getByLabel('标题')).toHaveValue('新的每日复盘');
  await card.getByRole('button', { name: '保存' }).click();
  await expect(card).toContainText('新的每日复盘');

  await card.getByRole('button', { name: '暂停' }).click();
  await expect(card).toContainText('已暂停');
  await card.getByRole('button', { name: '恢复' }).click();
  await expect(card).toContainText('待执行');

  await card.getByRole('button', { name: '立即运行' }).click();
  await expect(page.getByRole('alert').filter({ hasText: '任务更新失败' })).toBeVisible();
  await card.getByRole('button', { name: '立即运行' }).click();
  await expect(card).toContainText('已完成');

  await card.getByRole('button', { name: '历史' }).click();
  await expect(card).toContainText('手动执行');

  await card.getByRole('button', { name: '删除' }).click();
  await expect(card).toContainText('已删除');
  await card.getByRole('button', { name: '撤销删除' }).click();
  await expect(card).toContainText('待执行');

  expect(getUnexpected()).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBeTruthy();
});
