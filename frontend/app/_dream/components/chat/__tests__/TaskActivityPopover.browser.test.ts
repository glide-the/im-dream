// [Input] Production TaskActivityContent, local Chrome and owner-scoped task/subagent fixtures.
// [Output] Visual and interaction evidence for the independent Todo-style activity popover, task navigation and failures.
// [Pos] Isolated browser acceptance for the Chat shell activity entry; Environment info remains unchanged.
// [Sync] 2026-10-07: keep ordinary activity isolated from scheduled reads and assert the persistent dialog is hidden after closing.
// [Sync] 2026-09-28: cover conditional visibility, separated task/subagent/plan cards, status, navigation and unchanged Deck metadata.

import { expect, test } from '@playwright/test';
// @ts-expect-error Browser harness imports Node APIs outside the application tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Browser harness imports Node APIs outside the application tsconfig.
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
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
}

test('current-Thread activity popover separates tasks, subagents and plans without changing Environment info', async ({ page }, testInfo) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const requestFailures: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('requestfailed', (request) => requestFailures.push(`${request.method()} ${request.url()} ${request.failure()?.errorText ?? ''}`));
  const port = await reservePort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'task-activity-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== '/task-activity') return next();
          try {
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(await vite.transformIndexHtml('/task-activity', '<!doctype html><html><body><div id="root"></div><script type="module" src="/task-activity-harness.js"></script></body></html>'));
          } catch (error) { next(error as Error); }
        });
      },
      resolveId(id) { return id === '/task-activity-harness.js' ? '\0task-activity-harness.js' : null; },
      load(id) {
        if (id !== '\0task-activity-harness.js') return null;
        return `
          import React from 'react';
          import { createRoot } from 'react-dom/client';
          import i18n from '/app/_dream/i18n.ts';
          import PluginReceiptBadge from '/app/_dream/components/chat/PluginReceiptBadge.tsx';
          import PlanButton from '/app/_dream/components/chat/PlanPanel.tsx';
          import { SubagentToolButton } from '/app/_dream/components/chat/SubagentPanel.tsx';
          import { applyPlanEvent } from '/app/_dream/hooks/useThreadPlan.ts';
          import { applyTodoEvent } from '/app/_dream/hooks/useThreadTodos.ts';
          import '/app/_dream/styles/tokens.css';
          import '/app/_dream/index.css';
          void i18n.changeLanguage('zh');
          applyPlanEvent('source-thread', { type: 'plan-updated', slug: 'review', fileName: 'review.md', content: '检查当前任务。', contentBytes: 24, updatedAt: '2026-09-27T00:00:00Z' });
          applyTodoEvent('source-thread', { type: 'todo-updated', source: 'todo_write', todos: [{ id: 'source-todo', content: '核对任务与进度入口。', status: 'in_progress', active_form: '正在核对任务与进度入口。', owner: 'Dream', blocked_by: [] }], updatedAt: '2026-09-27T00:00:00Z' });
          applyPlanEvent('plan-only-thread', { type: 'plan-updated', slug: 'plan-only', fileName: 'plan-only.md', content: '计划。', contentBytes: 9, updatedAt: '2026-09-27T00:00:00Z' });
          applyTodoEvent('todo-only-thread', { type: 'todo-updated', source: 'todo_write', todos: [{ id: 'todo-one', content: '待办。', status: 'pending', active_form: null, owner: null, blocked_by: [] }], updatedAt: '2026-09-27T00:00:00Z' });
          window.infoNavigation = [];
          window.otherHostFocus = 0;
          const deck = { id: 'deck-one', name: 'Review Deck', name_zh: '复核 Deck', is_system: false, enabled: true, agent_type: 'chat', agent_type_revision: 1, voices: [] };
          function Harness() {
            const [sidebarOpen, setSidebarOpen] = React.useState(false);
            return React.createElement('main', { style: { minHeight: '100vh', padding: '1rem', boxSizing: 'border-box', background: 'var(--color-bg-app)' } },
              React.createElement('div', { id: 'source-actions', style: { display: 'flex', justifyContent: 'flex-end' } },
                React.createElement(PluginReceiptBadge, {
                  threadId: 'source-thread', deck,
                }),
                React.createElement(PlanButton, {
                  threadId: 'source-thread', subagentSidebarOpen: sidebarOpen,
                  onToggleSubagents: () => setSidebarOpen((value) => !value),
                  onNavigateThread: (threadId) => window.infoNavigation.push(threadId),
                })),
              React.createElement('div', { id: 'visibility-fixtures', style: { display: 'none' } },
                ...['empty-thread', 'task-only-thread', 'subagent-only-thread', 'plan-only-thread', 'todo-only-thread'].map((threadId) =>
                  React.createElement('div', { id: threadId, key: threadId }, React.createElement(PlanButton, {
                    threadId, subagentSidebarOpen: false,
                    onToggleSubagents: () => {}, onNavigateThread: () => {},
                  })))),
              React.createElement('div', { id: 'sidebar-state' }, sidebarOpen ? 'sidebar-open' : 'sidebar-closed'),
              React.createElement('div', { id: 'tool-summary-fixture', style: { display: 'none' } },
                React.createElement(SubagentToolButton, { description: '复核界面' })),
              React.createElement('div', { id: 'other-host-tool-fixture', style: { display: 'none' } },
                React.createElement(SubagentToolButton, { description: '其他工作区任务', onClick: () => { window.otherHostFocus += 1; } })));
          }
          createRoot(document.querySelector('#root')).render(React.createElement(Harness));
        `;
      },
    }],
  });
  let failLinks = false;
  let firstRunning = true;
  await page.route('**/api/claude-agent/threads/*/scheduled-tasks', (route) =>
    route.fulfill({ json: { created: [], source: null } }));
  const task = (id: string, threadId: string, title: string) => ({ task_id: id, source_thread_id: 'source-thread', thread_id: threadId, title, launch_status: 'starting', launch_error_code: null, created_at: '2026-09-27T00:00:00Z' });
  await page.route('**/api/claude-agent/threads/source-thread/task-links', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(failLinks ? {} : { source: null, created: [task('first', 'child-one', '复核 Admin 队列与任务会话'), task('second', 'child-two', '复核 Dream 运行中消息队列')] }) });
  });
  await page.route('**/api/claude-agent/threads/empty-thread/task-links', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ source: null, created: [] }) });
  });
  await page.route('**/api/claude-agent/threads/task-only-thread/task-links', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ source: null, created: [task('task-only', 'child-task-only', '独立任务')] }) });
  });
  for (const threadId of ['subagent-only-thread', 'plan-only-thread', 'todo-only-thread']) {
    await page.route(`**/api/claude-agent/threads/${threadId}/task-links`, async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ source: null, created: [] }) });
    });
  }
  await page.route('**/api/claude-agent/threads/source-thread/tasks/*', async (route) => {
    const first = route.request().url().endsWith('/first');
    const running = first && firstRunning;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ task_id: first ? 'first' : 'second', thread_id: first ? 'child-one' : 'child-two', title: first ? '复核 Admin 队列与任务会话' : '复核 Dream 运行中消息队列', launch_status: 'starting', error_code: null, status: running ? 'running' : 'completed', running }) });
  });
  await page.route('**/api/claude-agent/threads/source-thread/subagents', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ exists: true, counts: { running: 0, completed: 1, ended: 0, total: 1 }, tasks: [{ task_id: 'agent-one', agent_id: 'agent-one', agent_type: 'reviewer', description: '复核界面', summary: '完成复核', status: 'completed', tool_call_id: null, spawn_depth: 1, started_at: null, finished_at: null, duration_ms: 12000, error: null, activity: [], messages: [], message_count: 0, messages_truncated: false, projection_version: 2 }], updated_at: '2026-09-27T00:00:00Z' }) });
  });
  await page.route('**/api/claude-agent/threads/empty-thread/subagents', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ exists: false, counts: { running: 0, completed: 0, ended: 0, total: 0 }, tasks: [], updated_at: null }) });
  });
  await page.route('**/api/claude-agent/threads/subagent-only-thread/subagents', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ exists: true, counts: { running: 1, completed: 0, ended: 0, total: 1 }, tasks: [{ task_id: 'agent-only', agent_id: 'agent-only', agent_type: 'reviewer', description: '独立子智能体', summary: null, status: 'running', tool_call_id: null, spawn_depth: 1, started_at: null, finished_at: null, duration_ms: null, error: null, activity: [], messages: [], message_count: 0, messages_truncated: false, projection_version: 2 }], updated_at: '2026-09-27T00:00:00Z' }) });
  });
  for (const threadId of ['task-only-thread', 'plan-only-thread', 'todo-only-thread']) {
    await page.route(`**/api/claude-agent/threads/${threadId}/subagents`, async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ exists: false, counts: { running: 0, completed: 0, ended: 0, total: 0 }, tasks: [], updated_at: null }) });
    });
  }
  await page.route('**/api/claude-agent/threads/source-thread/plugin-load-receipt', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ receipt: { plugins: [], frozen: false }, launch_manifest: { plugins: [] } }) });
  });
  await page.route('**/api/claude-plugins/installations', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ installations: [] }) });
  });
  try {
    await server.listen();
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`http://127.0.0.1:${port}/task-activity`);
    const environmentTrigger = page.getByRole('button', { name: 'Deck 元信息' });
    await expect(environmentTrigger).toHaveCount(1);
    await environmentTrigger.click();
    const environmentCard = page.getByRole('dialog', { name: 'Deck 元信息' });
    await expect(page.getByRole('dialog')).toHaveCount(1);
    await expect(environmentCard).toContainText('复核 Deck');
    await expect(environmentCard).not.toContainText('已创建的任务');
    await expect(page.locator('#source-actions [role="dialog"][aria-label="任务与进度"]')).toBeHidden();
    await page.keyboard.press('Escape');
    const activityTrigger = page.getByRole('button', { name: '任务与进度' });
    await expect(activityTrigger).toBeVisible();
    await expect(page.locator('#empty-thread').locator('button[aria-label="任务与进度"]')).toHaveCount(0);
    for (const fixtureId of ['task-only-thread', 'subagent-only-thread', 'plan-only-thread', 'todo-only-thread']) {
      await expect(page.locator(`#${fixtureId}`).locator('button[aria-label="任务与进度"]')).toHaveCount(1);
    }
    await activityTrigger.click();
    const card = page.getByRole('dialog', { name: '任务与进度' });
    await expect(card.getByRole('button', { name: /已创建的任务/ })).toBeVisible();
    await expect(card.locator('.task-activity__section')).toHaveCount(2);
    await expect(card.locator('.task-activity__plan-card')).toHaveCount(1);
    await expect(card.locator('.task-activity__todo-card')).toHaveCount(1);
    await expect(card.locator('.task-activity__todo-card')).toContainText('正在核对任务与进度入口。');
    expect((await card.boundingBox())!.width).toBeLessThanOrEqual(430);
    await expect(card.locator('.task-activity__task')).toHaveCount(2);
    await expect(card.locator('.task-activity__task[data-task-status="running"] .task-activity__status-icon')).toHaveCount(1);
    await expect(card.locator('.task-activity__task[data-task-status="completed"] .task-activity__status-icon')).toHaveCount(1);
    await expect(card).toContainText('运行中');
    await expect(card).toContainText('已完成');
    await expect(card).toContainText('1 完成');
    expect(await page.locator('#tool-summary-fixture button').count()).toBe(0);
    await expect(page.locator('#tool-summary-fixture')).toContainText('复核界面');
    expect(await page.locator('#other-host-tool-fixture button').count()).toBe(1);
    await page.locator('#other-host-tool-fixture button').evaluate((button: HTMLButtonElement) => button.click());
    expect(await page.evaluate(() => (window as unknown as { otherHostFocus: number }).otherHostFocus)).toBe(1);
    await page.screenshot({ path: testInfo.outputPath('task-activity-desktop.png'), fullPage: true });
    firstRunning = false;
    await page.keyboard.press('Escape');
    await activityTrigger.click();
    await expect(card.locator('.task-activity__task').first()).toContainText('已完成');
    await expect(card).toContainText('检查当前任务。');
    await page.keyboard.press('Escape');
    await expect(card).toBeHidden();
    await activityTrigger.click();
    await card.locator('[aria-controls="thread-subagent-sidebar"]').click();
    await expect(page.locator('#sidebar-state')).toHaveText('sidebar-open');
    await expect(card).toBeHidden();
    await activityTrigger.click();
    await card.locator('.task-activity__task').first().click();
    expect(await page.evaluate(() => (window as unknown as { infoNavigation: string[] }).infoNavigation)).toEqual(['child-one']);
    failLinks = true;
    await activityTrigger.click();
    await expect(card).toContainText('暂时无法读取任务');
    await expect(card.locator('.task-activity__task')).toHaveCount(2);
    failLinks = false;
    await card.getByRole('button', { name: '重新加载' }).click();
    await expect(card.getByText('暂时无法读取任务')).toHaveCount(0);
    await page.setViewportSize({ width: 390, height: 844 });
    await card.evaluate((element) => { element.scrollTop = 0; });
    const box = await card.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(390);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath('task-activity-mobile.png'), fullPage: true });
    expect(consoleErrors).toEqual([]);
    expect(pageErrors).toEqual([]);
    expect(requestFailures).toEqual([]);
  } finally {
    await server.close();
  }
});
