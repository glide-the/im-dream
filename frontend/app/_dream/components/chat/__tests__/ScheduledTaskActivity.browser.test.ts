// [Input] Production PlanButton, scheduled marker/detail components and owner-scoped API fixtures.
// [Output] Local-Chrome activity/navigation, failure, refresh, race and responsive regression evidence.
// [Pos] Provider-free isolated scheduled activity browser contract; no normal services or model calls.
// [Sync] 2026-10-07: cover creation and execution conversations with the same scheduled detail action.
import { expect, test } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chrome' });

async function reservePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createNetServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (!address || typeof address === 'string') { probe.close(); reject(new Error('Port unavailable')); return; }
      probe.close((error) => error ? reject(error) : resolve(address.port));
    });
  });
}

const task = {
  id: '550e8400-e29b-41d4-a716-446655440000', source_thread_id: 'source', title: '检查项目进度', prompt: '检查项目进度',
  rule: { kind: 'interval', interval_minutes: 10, time_zone: 'Asia/Shanghai' }, next_run_at: null,
  status: 'paused', revision: 3, created_at: '2026-09-01T00:00:00Z', updated_at: '2026-10-07T00:00:00Z',
};
const trigger = {
  id: '550e8400-e29b-41d4-a716-446655440001', task_id: task.id, kind: 'scheduled', scheduled_at: '2026-10-07T00:00:00Z',
  definition_revision: 2, title: task.title, source_thread_id: 'source', time_zone: 'Asia/Shanghai', status: 'succeeded',
  task_session_id: 'task-session', target_thread_id: 'execution', input_message_id: 'input', target_turn_id: 'turn',
  final_message_id: 'final', error_code: null, skipped_from_at: null, skipped_through_at: null,
  created_at: '2026-10-07T00:00:00Z', updated_at: '2026-10-07T00:00:00Z',
};

test('scheduled-only source and execution activity shares detail navigation, retries and isolates Thread changes', async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const port = await reservePort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)), configFile: false, logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'scheduled-activity-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== '/scheduled-activity') return next();
          try {
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(await vite.transformIndexHtml('/scheduled-activity', '<!doctype html><html><body><div id="root"></div><script type="module" src="/scheduled-activity-harness.js"></script></body></html>'));
          } catch (error) { next(error as Error); }
        });
      },
      resolveId(id) { return id === '/scheduled-activity-harness.js' ? '\0scheduled-activity-harness.js' : null; },
      load(id) {
        if (id !== '\0scheduled-activity-harness.js') return null;
        return `
          import React from 'react';
          import { createRoot } from 'react-dom/client';
          import i18n from '/app/_dream/i18n.ts';
          import PlanButton from '/app/_dream/components/chat/PlanPanel.tsx';
          import ScheduledTaskMarkerList from '/app/_dream/components/chat/ScheduledTaskMarker.tsx';
          import ScheduledTaskDetailSidebar from '/app/_dream/components/chat/ScheduledTaskDetailSidebar.tsx';
          import '/app/_dream/styles/tokens.css';
          import '/app/_dream/index.css';
          void i18n.changeLanguage('zh');
          const marker = ${JSON.stringify({ id: task.id, title: task.title, rule: task.rule, nextRunAt: null, status: 'active', revision: 1 })};
          window.openedScheduledIds = [];
          function Harness() {
            const [threadId, setThreadId] = React.useState('source');
            const [revision, setRevision] = React.useState(0);
            const [detail, setDetail] = React.useState(null);
            const openTask = (task) => { window.openedScheduledIds.push(task.id); setDetail(task); };
            return React.createElement('main', { style: { padding: '1rem', boxSizing: 'border-box', minHeight: '100vh', background: 'var(--color-bg-app)' } },
              React.createElement('nav', null, ...['source', 'execution', 'empty', 'new', 'slow'].map((id) => React.createElement('button', {
                key: id, onClick: () => { setDetail(null); setThreadId(id); } }, '切换 ' + id)),
                React.createElement('button', { onClick: () => setRevision((value) => value + 1) }, '完成创建回合')),
              React.createElement('div', { style: { display: 'flex', justifyContent: 'flex-end' } }, React.createElement(PlanButton, {
                threadId, scheduledRefreshKey: revision, subagentSidebarOpen: false,
                onToggleSubagents: () => {}, onNavigateThread: () => {}, onOpenScheduledTask: openTask,
              })),
              React.createElement('div', { id: 'creating-message' }, React.createElement(ScheduledTaskMarkerList, { tasks: [marker], onOpen: openTask })),
              detail ? React.createElement(ScheduledTaskDetailSidebar, { taskId: detail.id, snapshot: detail,
                onClose: () => setDetail(null), onOpenThread: (id) => { setDetail(null); setThreadId(id); } }) : null);
          }
          createRoot(document.querySelector('#root')).render(React.createElement(Harness));
        `;
      },
    }],
  });
  let failScheduled = false;
  let newCreated = false;
  let releaseSlow: (() => void) | undefined;
  let slowSeen = false;
  await page.route('**/api/claude-agent/threads/*/scheduled-tasks', async (route) => {
    const threadId = new URL(route.request().url()).pathname.split('/').at(-2);
    if (threadId === 'slow') {
      slowSeen = true;
      await new Promise<void>((resolve) => { releaseSlow = resolve; });
      await route.fulfill({ json: { created: [{ ...task, source_thread_id: 'slow', title: '迟到的旧会话任务' }], source: null } }).catch(() => {});
      return;
    }
    const snapshot = failScheduled ? {} : threadId === 'source' ? { created: [task], source: null }
      : threadId === 'execution' ? { created: [], source: { task, trigger } }
        : threadId === 'new' && newCreated ? { created: [{ ...task, source_thread_id: 'new', status: 'active' }], source: null }
          : { created: [], source: null };
    await route.fulfill({ json: snapshot });
  });
  await page.route('**/api/claude-agent/threads/*/task-links', (route) => route.fulfill({ json: { source: null, created: [] } }));
  await page.route('**/api/claude-agent/threads/*/subagents', (route) => route.fulfill({ json: {
    exists: false, counts: { running: 0, completed: 0, ended: 0, total: 0 }, tasks: [], updated_at: null,
  } }));
  await page.route(`**/api/claude-agent/scheduled-tasks/${task.id}`, (route) => route.fulfill({ json: { task } }));
  await page.route(`**/api/claude-agent/scheduled-tasks/${task.id}/history?*`, (route) => route.fulfill({ json: { triggers: [trigger] } }));
  try {
    await server.listen();
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`http://127.0.0.1:${port}/scheduled-activity`);
    const activity = page.getByRole('button', { name: '任务与进度', exact: true });
    const popover = page.getByRole('dialog', { name: '任务与进度', exact: true });
    const detail = page.getByRole('complementary', { name: '定时任务', exact: true });
    await expect(activity).toBeVisible();
    await activity.click();
    const scheduled = popover.locator('.task-activity__scheduled');
    const record = scheduled.getByRole('button', { name: `打开定时任务：${task.title}`, exact: true });
    await expect(record).toBeVisible();
    await expect(record).toContainText('每隔 10 分钟');
    await expect(record).toContainText('已暂停');
    await expect(record).not.toContainText('本次执行');
    await page.screenshot({ path: testInfo.outputPath('scheduled-activity-desktop.png'), fullPage: true });
    await record.focus();
    await page.keyboard.press('Enter');
    await expect(popover).toBeHidden();
    await expect(detail).toContainText(task.title);
    await expect(detail).toContainText('创建任务的会话');
    await page.getByRole('button', { name: '关闭定时任务详情' }).click();
    await page.locator('#creating-message').getByRole('button', { name: `打开定时任务：${task.title}` }).click();
    await expect(detail).toContainText(task.title);
    expect(await page.evaluate(() => (window as unknown as { openedScheduledIds: string[] }).openedScheduledIds)).toEqual([task.id, task.id]);
    await page.getByRole('button', { name: '切换 execution', exact: true }).click();
    await expect(activity).toBeVisible();
    await activity.click();
    await expect(record).toHaveCount(1);
    await expect(record).toContainText('已暂停');
    await expect(record).toContainText('本次执行：已完成');
    await page.setViewportSize({ width: 390, height: 844 });
    const box = await popover.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(390);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath('scheduled-activity-mobile.png'), fullPage: true });
    failScheduled = true;
    await page.keyboard.press('Escape');
    await activity.click();
    await expect(scheduled).toContainText('暂时无法读取定时任务');
    await expect(record).toBeVisible();
    failScheduled = false;
    await scheduled.getByRole('button', { name: '重新加载' }).click();
    await expect(scheduled).not.toContainText('暂时无法读取定时任务');
    await page.getByRole('button', { name: '切换 new', exact: true }).click();
    await expect(activity).toHaveCount(0);
    newCreated = true;
    await page.getByRole('button', { name: '完成创建回合' }).click();
    await expect(activity).toBeVisible();
    await activity.click();
    await expect(record).toContainText('已启用');
    await page.getByRole('button', { name: '切换 slow', exact: true }).click();
    await expect.poll(() => slowSeen).toBe(true);
    await page.getByRole('button', { name: '切换 empty', exact: true }).click();
    await expect(activity).toHaveCount(0);
    releaseSlow?.();
    await page.getByRole('button', { name: '完成创建回合' }).click();
    await expect(activity).toHaveCount(0);
    await expect(page.getByText('迟到的旧会话任务')).toHaveCount(0);
    expect(errors).toEqual([]);
  } finally {
    releaseSlow?.();
    await server.close();
  }
});
