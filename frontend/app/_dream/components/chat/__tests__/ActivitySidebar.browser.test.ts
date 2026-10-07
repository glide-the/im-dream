// [Input] Production ChatView/ActivitySidebar, public DTO fixtures, controllable clock and the installed local Chrome.
// [Output] Isolated interface evidence for display, paging/recovery, original navigation/delete, drawer focus and read-only automatic activity.
// [Pos] Technical UI validation only; shared Thread is navigation. Dream Project/Episode/canonical publication/Hook/DB remain outside scope.
// [Sync] 2026-10-07: isolate source recovery from raw-history pagination so real scrolling cannot invalidate the consumed-prefix fixture.
import { expect, test, type Page, type TestInfo } from '@playwright/test';
// @ts-expect-error Node harness APIs are intentionally outside the application browser compilation.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Node harness APIs are intentionally outside the application browser compilation.
import { createServer as createNetServer } from 'node:net';
// @ts-expect-error Node harness APIs are intentionally outside the application browser compilation.
import { rm, mkdir, writeFile } from 'node:fs/promises';
import { createServer } from 'vite';
import type { ChatHistoryThread } from '../../../api/chatHistoryApi';
import type { ScheduledTask, ScheduledTrigger } from '../../../api/scheduledTaskApi';
import type { StoryWorkspaceDreamReentryItem } from '../../../hooks/story-workspace/contracts';

test.use({ channel: 'chrome', timezoneId: 'Asia/Shanghai', viewport: { width: 1440, height: 900 } });
test.setTimeout(120000);
const NOW = Date.parse('2026-10-07T15:59:58Z');
const iso = (at: number) => new Date(at).toISOString();
const chatRow = (id: string, at = NOW - 60000): ChatHistoryThread => ({ id, title: `对话 ${id}`, created_at: iso(at), updated_at: iso(at) });
const taskRow = (id: string): ScheduledTask => ({ id, title: `任务 ${id}`, source_thread_id: 'existing', prompt: 'test fixture',
  rule: { kind: 'daily', local_time: '09:00', time_zone: 'Asia/Shanghai' }, next_run_at: null, status: 'active', revision: 2,
  created_at: iso(NOW - 100000), updated_at: iso(NOW - 80000) });
const triggerRow = (id: string, taskId: string, status: ScheduledTrigger['status']): ScheduledTrigger => ({
  id, task_id: taskId, title: `任务 ${taskId}`, source_thread_id: 'existing', kind: 'scheduled', scheduled_at: iso(NOW - 100000),
  definition_revision: 2, time_zone: 'Asia/Shanghai', status, task_session_id: null, target_thread_id: null, input_message_id: null,
  target_turn_id: null, final_message_id: null, error_code: null, skipped_from_at: null, skipped_through_at: null,
  created_at: iso(NOW - 100000), updated_at: iso(NOW - 80000),
});
const dreamRow = (id = 'run_11111111111111111111111111111111'): StoryWorkspaceDreamReentryItem => ({
  storyWorkspaceRunId: id, displayTitle: 'Dream 工作', goalPrefix: 'Fixture', deckId: 'fixture', deckDisplayName: 'Fixture',
  workflowDisplayName: 'Dream', deckPluginVersion: 'fixture', lifecycle: 'generating', outcome: 'initial', group: 'in_progress',
  stageRevisions: {}, confirmationAccepted: false, confirmationDispatched: false, lastActivityAt: iso(NOW - 70000), createdAt: iso(NOW - 90000),
  sortKey: 'original-server-order', href: `/story-workspace/dream?run=${id}`,
});
interface Fixture {
  threads: ChatHistoryThread[];
  tasks: ScheduledTask[];
  triggers: ScheduledTrigger[];
  dreams: StoryWorkspaceDreamReentryItem[];
  failChatOffset?: number;
  failHistoryOffset?: number;
  failDream?: boolean;
  failTasks?: boolean;
  delayChat?: Promise<void>;
  delayHistory?: Promise<void>;
  delayTasks?: Promise<void>;
  dayTasks?: (day: string) => ScheduledTask[];
  showSubagent?: boolean;
  fixedMountTime?: boolean;
}

async function reservePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createNetServer(); probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (!address || typeof address === 'string') { probe.close(); reject(new Error('Ephemeral port unavailable')); return; }
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
}

async function mountChat(page: Page, testInfo: TestInfo, fixture: Fixture, initialThread?: string) {
  const mutations: string[] = []; const reads: string[] = []; const pageErrors: string[] = [];
  const consoleErrors: string[] = []; const requestFailures: string[] = [];
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('requestfailed', (request) => requestFailures.push(`${request.method()} ${new URL(request.url()).pathname} ${request.failure()?.errorText ?? 'failed'}`));
  await page.clock.install({ time: new Date(NOW) });
  if (fixture.fixedMountTime) await page.clock.setFixedTime(new Date(NOW));
  await page.addInitScript(() => { localStorage.setItem('ink-language', 'zh'); });
  await page.route('**/api/**', async (route) => {
    const request = route.request(); const url = new URL(request.url()); const path = url.pathname;
    if (!path.startsWith('/api/')) { await route.continue(); return; }
    const reply = async (value: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(value) });
    if (request.method() !== 'GET') {
      mutations.push(`${request.method()} ${path}`);
      if (request.method() === 'DELETE' && /^\/api\/claude-agent\/threads\/[^/]+$/.test(path)) {
        const id = decodeURIComponent(path.split('/').at(-1)!);
        fixture.threads = fixture.threads.filter((row) => row.id !== id);
        await reply({}); return;
      }
      await reply({ detail: 'Unrequested control write' }, 409); return;
    }
    reads.push(`${path}${url.search}`);
    if (path === '/api/claude-agent/threads') {
      const offset = Number(url.searchParams.get('offset') ?? 0); const limit = Number(url.searchParams.get('limit') ?? 100);
      const snapshot = fixture.threads.slice(offset, offset + limit);
      if (limit === 50 && fixture.delayChat) await fixture.delayChat;
      if (limit === 21 && fixture.delayHistory) await fixture.delayHistory;
      if ((limit === 50 && offset === fixture.failChatOffset) || (limit === 21 && offset === fixture.failHistoryOffset)) { await reply({ detail: 'Fixture source unavailable' }, 503); return; }
      const query = url.searchParams.get('query');
      await reply({ threads: query ? fixture.threads.filter((row) => row.title?.includes(query)) : snapshot }); return;
    }
    if (path === '/api/story-workspace/dream-runs') { await reply({ runs: fixture.dreams }, fixture.failDream ? 503 : 200); return; }
    if (path === '/api/claude-agent/scheduled-tasks/day') {
      const snapshot = { tasks: fixture.dayTasks?.(url.searchParams.get('local_date')!) ?? fixture.tasks, triggers: fixture.triggers };
      if (fixture.delayTasks) await fixture.delayTasks;
      await reply(snapshot, fixture.failTasks ? 503 : 200); return;
    }
    if (/\/scheduled-tasks\/[^/]+\/history$/.test(path)) { await reply({ triggers: fixture.triggers }); return; }
    if (/\/scheduled-tasks\/[^/]+$/.test(path)) { await reply({ task: fixture.tasks.find((row) => path.endsWith(`/${row.id}`)) ?? null }); return; }
    if (path === '/api/system-config') { await reply({ data: { workspace_enabled: true, full_access_enabled: false } }); return; }
    if (path === '/api/decks') { await reply({ decks: [] }); return; }
    if (path === '/api/claude-agent/skill-commands') { await reply({ commands: [] }); return; }
    if (path === '/api/storage') { await reply({}); return; }
    if (/\/threads\/[^/]+\/messages$/.test(path)) {
      const id = path.split('/').at(-2)!;
      await reply({ thread: chatRow(id), messages: [{ id: 'saved-message', role: 'assistant', parts: [{ type: 'text', text: '已有正文保持不变。' }], created_at: iso(NOW) }], next_cursor: null, has_more: false, latest_message_id: 'saved-message', unchanged: false }); return;
    }
    if (path.endsWith('/status')) { await reply({ running: false, lifecycle: 'idle', turn_count: 1, pending_tool_call_ids: [], tool_confirmation_observation: 'known' }); return; }
    if (path.endsWith('/inputs')) { await reply({ entries: [], local_owner: false }); return; }
    if (path.endsWith('/task-links')) { await reply({ source: null, created: [] }); return; }
    if (path.endsWith('/plan')) { await reply({ exists: false }); return; }
    if (path.endsWith('/todos')) { await reply({ exists: false, todos: [] }); return; }
    if (path.endsWith('/subagents')) {
      const tasks = fixture.showSubagent ? [{ task_id: 'fixture-agent', agent_id: 'fixture-agent', agent_type: 'reviewer', description: '复核', summary: null, status: 'running', tool_call_id: null, spawn_depth: 1, started_at: null, finished_at: null, duration_ms: null, error: null, activity: [], messages: [], message_count: 0, messages_truncated: false, projection_version: 2 }] : [];
      await reply({ exists: tasks.length > 0, counts: { running: tasks.length, completed: 0, ended: 0, total: tasks.length }, tasks, updated_at: null }); return;
    }
    if (path.endsWith('/plugin-load-receipt')) { await reply({ thread_id: 'existing', receipt: null, launch_manifest: null }); return; }
    if (path === '/api/claude-plugins/installations') { await reply({ installations: [] }); return; }
    if (path === '/api/workspace/files') { await reply({ files: [], directories: [], root: '.' }); return; }
    await reply({});
  });
  const port = await reservePort(); const cacheDir = testInfo.outputPath('priority-activity-vite-cache');
  const server = await createServer({ root: fileURLToPath(new URL('../../../../../', import.meta.url)), configFile: false,
    cacheDir, logLevel: 'silent', server: { host: '127.0.0.1', port, strictPort: true }, plugins: [{
      name: 'priority-activity-production-chat-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== '/priority-activity') return next();
          response.setHeader('Content-Type', 'text/html; charset=utf-8');
          response.end(await vite.transformIndexHtml('/priority-activity', '<!doctype html><html><head><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root" style="height:100dvh"></div><script type="module" src="/priority-activity-harness.js"></script></body></html>'));
        });
      },
      resolveId(id) { return id === '/priority-activity-harness.js' ? '\0priority-activity-harness.js' : null; },
      load(id) { return id === '\0priority-activity-harness.js' ? `
        import React from 'react'; import { createRoot } from 'react-dom/client';
        import i18n from '/app/_dream/i18n.ts'; import ChatView from '/app/_dream/components/chat/ChatView.tsx';
        import '/app/_dream/styles/tokens.css'; import '/app/_dream/styles/markdown.css';
        void i18n.changeLanguage('zh');
        window.__priorityRoot = createRoot(document.querySelector('#root'));
        window.__priorityRoot.render(React.createElement(ChatView, ${JSON.stringify(initialThread ? { threadId: initialThread } : {})}));
      ` : null; },
    }] });
  await server.listen();
  try { await page.goto(`http://127.0.0.1:${port}/priority-activity`); await expect(page.getByRole('button', { name: '活动视图', exact: true })).toBeVisible(); }
  catch (reason) {
    const body = await page.locator('body').innerText().catch(() => '<fixture body unavailable>');
    console.error('Priority activity fixture mount diagnostics', JSON.stringify({ consoleErrors, pageErrors, requestFailures, reads, body }));
    await server.close(); await rm(cacheDir, { recursive: true, force: true }); throw reason;
  }
  return { mutations, reads, pageErrors, close: async () => {
    const diagnostics = testInfo.outputPath('priority-activity-safe-diagnostics.json');
    await writeFile(diagnostics, JSON.stringify({ consoleErrors, requestFailures, pageErrors, reads, mutations }, null, 2));
    await testInfo.attach('priority-activity-safe-diagnostics', { contentType: 'application/json', path: diagnostics });
    await page.close(); await server.close(); await rm(cacheDir, { recursive: true, force: true });
  } };
}

test('bell and four choices expose complete recent pages, distinct priorities, history/search and original navigation', async ({ page }, testInfo) => {
  const fixture: Fixture = { threads: [...Array.from({ length: 64 }, (_, i) => chatRow(`recent-${i}`, NOW - 60000 - i)), ...Array.from({ length: 25 }, (_, i) => chatRow(`old-${i}`, NOW - 86400000 - i))],
    tasks: [taskRow('today')], triggers: [triggerRow('running', 'today', 'running'), triggerRow('done', 'today', 'succeeded'), triggerRow('orphan', 'orphan', 'failed')], dreams: [dreamRow()] };
  const harness = await mountChat(page, testInfo, fixture);
  try {
    const bell = page.getByRole('button', { name: '活动视图', exact: true }); await bell.click();
    const sidebar = page.locator('#chat-activity-sidebar');
    await expect(sidebar.locator('[data-activity-key^="chat:"]')).toHaveCount(64);
    await expect(sidebar.locator('[data-activity-key^="scheduled:"]')).toHaveCount(2);
    await expect(sidebar.locator('[data-activity-key]').first()).toHaveAttribute('data-activity-key', 'scheduled:today');
    await expect(sidebar.locator('[data-activity-key]').nth(1)).toHaveAttribute('data-activity-key', `dream:${fixture.dreams[0].storyWorkspaceRunId}`);
    expect(harness.reads.some((url) => url.includes('limit=50&offset=50'))).toBe(true);
    await expect(sidebar).not.toHaveAttribute('aria-modal', 'true');
    await mkdir('output/playwright', { recursive: true }); await page.screenshot({ path: 'output/playwright/priority-activity-desktop.png', fullPage: true });
    await sidebar.getByRole('button', { name: '显示活动' }).click();
    const menu = sidebar.getByRole('menu'); await expect(menu.getByRole('menuitemcheckbox')).toHaveCount(4);
    await page.screenshot({ path: 'output/playwright/priority-activity-menu.png', fullPage: true });
    await menu.getByRole('menuitemcheckbox', { name: 'Chat', exact: true }).click();
    await expect(sidebar.locator('[data-activity-key^="chat:"]')).toHaveCount(0);
    await expect(sidebar.locator('[data-activity-key^="history:"]')).toHaveCount(20);
    await menu.getByRole('menuitemcheckbox', { name: '优先级部分' }).click();
    await expect(sidebar.locator('[data-activity-key^="dream:"]')).toHaveCount(0);
    await menu.getByRole('menuitemcheckbox', { name: '优先级部分' }).click();
    await menu.getByRole('menuitemcheckbox', { name: 'Chat', exact: true }).click();
    await page.keyboard.press('Escape'); await expect(sidebar.getByRole('button', { name: '显示活动' })).toBeFocused();
    await sidebar.getByRole('button', { name: '搜索历史对话' }).click();
    const search = page.getByRole('dialog', { name: '搜索历史对话' }); await expect(search).toBeVisible();
    await search.getByRole('textbox').fill('recent-63'); await page.clock.runFor(400);
    await expect(search.getByRole('button', { name: '对话 recent-63' })).toBeVisible();
    await page.keyboard.press('Escape'); await expect(sidebar.getByRole('button', { name: '搜索历史对话' })).toBeFocused();
    const href = sidebar.getByRole('link', { name: /Dream 工作/ }); await expect(href).toHaveAttribute('href', fixture.dreams[0].href);
    await href.evaluate((node) => { document.addEventListener('click', (event) => { (window as unknown as { __nativeLinkPreserved: boolean }).__nativeLinkPreserved = !event.defaultPrevented; event.preventDefault(); }, { once: true }); node.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, ctrlKey: true })); });
    expect(await page.evaluate(() => (window as unknown as { __nativeLinkPreserved: boolean }).__nativeLinkPreserved)).toBe(true);
    await sidebar.locator('[data-activity-key="scheduled:orphan"] button').click();
    await expect(sidebar).toHaveCount(0); await expect(page.locator('.scheduled-task-detail')).toBeVisible();
    await bell.click(); await expect(page.locator('.scheduled-task-detail')).toHaveCount(0);
    await sidebar.locator('[data-activity-key="chat:recent-1"] .activity-sidebar__row-main').click();
    await expect(sidebar).toHaveCount(0); await expect(page.getByText('已有正文保持不变。')).toBeVisible();
    await bell.click(); await expect(sidebar).toBeVisible(); await sidebar.getByRole('button', { name: '关闭活动' }).click(); await expect(bell).toBeFocused();
    await page.getByRole('button', { name: '更多', exact: true }).click(); await page.getByRole('button', { name: '历史对话', exact: true }).click(); await expect(sidebar).toBeVisible();
    await page.getByRole('button', { name: '更多', exact: true }).click(); await page.getByRole('button', { name: '工作空间', exact: true }).click(); await expect(sidebar).toHaveCount(0);
    await bell.click(); await expect(sidebar).toBeVisible();
    expect(harness.mutations).toEqual([]); expect(harness.pageErrors).toEqual([]);
  } finally { await harness.close(); }
});

test('partial recent failures retain rows and each source retries independently with its previous execution status', async ({ page }, testInfo) => {
  const fixture: Fixture = { threads: [...Array.from({ length: 55 }, (_, i) => chatRow(`recent-${i}`, NOW - 30000 - i)), ...Array.from({ length: 30 }, (_, i) => chatRow(`old-${i}`, NOW - 86400000 - i))], tasks: [taskRow('running')], triggers: [triggerRow('running', 'running', 'running')], dreams: [dreamRow()], failChatOffset: 50 };
  const harness = await mountChat(page, testInfo, fixture);
  try {
    await page.getByRole('button', { name: '活动视图', exact: true }).click(); const sidebar = page.locator('#chat-activity-sidebar');
    await expect(sidebar.locator('[data-activity-key^="chat:"]')).toHaveCount(50);
    const chatError = sidebar.locator('.activity-sidebar__feedback--error').filter({ hasText: 'Chat暂时无法加载' }); await expect(chatError).toBeVisible();
    expect(harness.reads.filter((read) => read.startsWith('/api/claude-agent/scheduled-tasks/day'))).toHaveLength(1);
    fixture.failChatOffset = undefined; await chatError.getByRole('button', { name: '重新加载' }).click(); await expect(sidebar.locator('[data-activity-key^="chat:"]')).toHaveCount(55);
    fixture.failDream = true; fixture.failTasks = true; await sidebar.getByRole('button', { name: '刷新活动' }).click();
    await expect(sidebar.locator('[data-activity-key^="dream:"]')).toContainText('上次状态');
    await expect(sidebar.locator('[data-activity-key="scheduled:running"]')).toHaveAttribute('data-priority', '2');
    await expect(sidebar.locator('[data-activity-key^="dream:"]')).toHaveAttribute('data-priority', '2');
    fixture.failDream = false; fixture.failTasks = false;
    await sidebar.locator('.activity-sidebar__feedback--error').filter({ hasText: 'Dream更新失败' }).getByRole('button').click(); await expect(sidebar.locator('[data-activity-key^="dream:"]')).toHaveAttribute('data-priority', '1');
    await sidebar.locator('.activity-sidebar__feedback--error').filter({ hasText: '定时任务更新失败' }).getByRole('button').click(); await expect(sidebar.locator('[data-activity-key="scheduled:running"]')).toHaveAttribute('data-priority', '0');
    expect(harness.mutations).toEqual([]); expect(harness.pageErrors).toEqual([]);
  } finally { await harness.close(); }
});

test('history paging retries preserve the next raw page after deletion and reject a delayed pre-delete reload', async ({ page }, testInfo) => {
  const fixture: Fixture = { threads: [...Array.from({ length: 55 }, (_, i) => chatRow(`recent-${i}`, NOW - 30000 - i)), ...Array.from({ length: 30 }, (_, i) => chatRow(`old-${i}`, NOW - 86400000 - i))], tasks: [], triggers: [], dreams: [] };
  const harness = await mountChat(page, testInfo, fixture, 'existing');
  try {
    await page.getByRole('button', { name: '活动视图', exact: true }).click(); const sidebar = page.locator('#chat-activity-sidebar');
    await expect(sidebar.locator('[data-activity-key^="chat:"]')).toHaveCount(55);
    await sidebar.getByRole('button', { name: '显示活动' }).click(); await sidebar.getByRole('menuitemcheckbox', { name: 'Chat', exact: true }).click(); await page.keyboard.press('Escape');
    const body = sidebar.locator('.activity-sidebar__body');
    await body.evaluate((node) => { node.scrollTop = 0; });
    await expect(sidebar.locator('[data-activity-key^="history:"]')).toHaveCount(20);
    expect(harness.reads.filter((read) => read.includes('limit=21')).map((read) => {
      const params = new URL(read, page.url()).searchParams;
      return { limit: Number(params.get('limit')), offset: Number(params.get('offset') ?? '0') };
    })).toEqual([{ limit: 21, offset: 0 }]);
    // Delete an item already consumed by history; the next request must start at 19, preserving the original lookahead item.
    await sidebar.locator('[data-activity-key="history:recent-0"]').hover(); await sidebar.locator('[data-activity-key="history:recent-0"]').getByRole('button', { name: '删除对话' }).click();
    await expect(sidebar.locator('[data-activity-key="history:recent-0"]')).toHaveCount(0);
    await expect(sidebar.locator('[data-activity-key="chat:recent-0"]')).toHaveCount(0);
    fixture.failHistoryOffset = 19; await sidebar.getByRole('button', { name: '加载更多历史' }).click();
    const historyError = sidebar.locator('.activity-sidebar__feedback--error').filter({ hasText: '历史暂时无法加载' }); await expect(historyError).toBeVisible();
    await expect(sidebar.getByText('已显示全部会话')).toHaveCount(0);
    fixture.failHistoryOffset = undefined; await historyError.getByRole('button').click();
    await expect(sidebar.locator('[data-activity-key="history:recent-20"]')).toHaveCount(1);
    await expect(sidebar.locator('[data-activity-key="history:recent-0"]')).toHaveCount(0);
    expect(harness.reads.some((read) => read.includes('limit=21&offset=19'))).toBe(true);
    // A pre-delete reload response must not resurrect the row or overwrite its corrected consumed offset.
    await body.evaluate((node) => { node.scrollTop = 0; });
    let releaseHistory!: () => void; fixture.delayHistory = new Promise<void>((resolve) => { releaseHistory = resolve; });
    await sidebar.getByRole('button', { name: '刷新活动' }).click(); await expect(sidebar.getByText('正在加载历史…')).toBeVisible();
    await sidebar.locator('[data-activity-key="history:recent-1"]').hover(); await sidebar.locator('[data-activity-key="history:recent-1"]').getByRole('button', { name: '删除对话' }).click();
    await expect(sidebar.locator('[data-activity-key="history:recent-1"]')).toHaveCount(0);
    fixture.delayHistory = undefined; releaseHistory(); await expect(sidebar.getByText('正在加载历史…')).toHaveCount(0);
    await sidebar.getByRole('button', { name: '加载更多历史' }).click(); await expect(sidebar.locator('[data-activity-key="history:recent-21"]')).toHaveCount(1);
    await expect(sidebar.locator('[data-activity-key="history:recent-1"]')).toHaveCount(0);
    expect(harness.mutations).toEqual(['DELETE /api/claude-agent/threads/recent-0', 'DELETE /api/claude-agent/threads/recent-1']); expect(harness.pageErrors).toEqual([]);
  } finally { await harness.close(); }
});

test('390px drawer manages layered focus, one list scroll, cross-day ranges and stale responses while preserving existing Chat', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const fixture: Fixture = { threads: [chatRow('existing'), ...Array.from({ length: 50 }, (_, i) => chatRow(`old-${i}`, NOW - 86400000 - i))], tasks: [], triggers: [], dreams: [dreamRow()], showSubagent: true, fixedMountTime: true,
    dayTasks: (day) => [taskRow(day === '2026-10-07' ? 'yesterday' : 'today')] };
  const harness = await mountChat(page, testInfo, fixture, 'existing');
  try {
    await expect(page.getByText('已有正文保持不变。')).toBeVisible();
    const input = page.getByRole('textbox', { name: '聊天输入' }); await input.fill('保留草稿');
    const bell = page.getByRole('button', { name: '活动视图', exact: true }); await bell.click();
    const drawer = page.getByRole('dialog', { name: '活动', exact: true }); await expect(drawer).toHaveAttribute('aria-modal', 'true');
    await expect(drawer.locator('[data-activity-key="scheduled:yesterday"]')).toBeVisible();
    expect(harness.reads.some((read) => read.includes('local_date=2026-10-07'))).toBe(true);
    await expect(drawer.getByRole('heading', { name: '活动', exact: true })).toBeFocused();
    expect(await page.locator('main').evaluate((node: HTMLElement) => node.inert)).toBe(true);
    const box = await drawer.boundingBox(); expect(box!.x).toBe(0); expect(box!.width).toBe(390);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const body = drawer.locator('.activity-sidebar__body'); await body.evaluate((node) => { node.scrollTop = 180; });
    const top = await body.evaluate((node) => node.scrollTop);
    await drawer.getByRole('button', { name: '刷新活动' }).click(); await expect.poll(() => body.evaluate((node) => node.scrollTop)).toBe(top);
    await drawer.getByRole('button', { name: '显示活动' }).click(); await page.keyboard.press('Escape'); await expect(drawer.getByRole('button', { name: '显示活动' })).toBeFocused();
    await drawer.getByRole('button', { name: '搜索历史对话' }).click(); const search = page.getByRole('dialog', { name: '搜索历史对话' }); await expect(search.getByRole('textbox')).toBeFocused();
    await page.keyboard.press('Escape'); await expect(drawer.getByRole('button', { name: '搜索历史对话' })).toBeFocused();
    await drawer.getByRole('button', { name: '关闭活动' }).focus(); await page.keyboard.press('Shift+Tab'); expect(await input.evaluate((node) => node === document.activeElement)).toBe(false);
    await page.clock.setSystemTime(new Date(NOW)); await page.clock.runFor(3000); await expect(drawer.locator('[data-activity-key="scheduled:today"]')).toBeVisible();
    await expect(drawer.locator('[data-activity-key="scheduled:yesterday"]')).toHaveCount(0); await expect(drawer.locator('[data-activity-key="chat:existing"]')).toHaveCount(1);
    expect(harness.reads.some((read) => read.includes('local_date=2026-10-08'))).toBe(true);
    await mkdir('output/playwright', { recursive: true }); await page.screenshot({ path: 'output/playwright/priority-activity-mobile.png', fullPage: true });
    await page.keyboard.press('Escape'); await expect(bell).toBeFocused(); await expect(input).toHaveText('保留草稿'); await expect(page.getByText('已有正文保持不变。')).toBeVisible();
    expect(await page.locator('main').evaluate((node: HTMLElement) => node.inert)).toBe(false);
    // Reopening across a stopped clock/date cannot relabel yesterday's task cache as today's range.
    await page.clock.setSystemTime(new Date(NOW + 86400000)); await bell.click(); await expect(drawer.locator('[data-activity-key="scheduled:today"]')).toBeVisible();
    await expect(drawer.locator('[data-activity-key="chat:existing"]')).toHaveCount(0);
    expect(harness.mutations).toEqual([]); expect(harness.pageErrors).toEqual([]);
  } finally { await harness.close(); }
});

test('closed/hidden sessions reject delayed old pages, stop new activity scheduling and recover current sources', async ({ page }, testInfo) => {
  let releaseChat!: () => void; let releaseTasks!: () => void;
  const fixture: Fixture = { threads: [chatRow('old-response')], tasks: [taskRow('old-response')], triggers: [], dreams: [],
    delayChat: new Promise<void>((resolve) => { releaseChat = resolve; }), delayTasks: new Promise<void>((resolve) => { releaseTasks = resolve; }) };
  const harness = await mountChat(page, testInfo, fixture);
  try {
    const bell = page.getByRole('button', { name: '活动视图', exact: true }); await bell.click(); const sidebar = page.locator('#chat-activity-sidebar');
    await expect(sidebar.getByText('正在加载Chat…')).toBeVisible();
    await sidebar.getByRole('button', { name: '关闭活动' }).click(); const readsOnClose = harness.reads.filter((read) => read.includes('limit=50') || read.includes('scheduled-tasks/day')).length;
    await page.clock.runFor(90000); expect(harness.reads.filter((read) => read.includes('limit=50') || read.includes('scheduled-tasks/day')).length).toBe(readsOnClose);
    fixture.threads = [chatRow('new-response', NOW + 90000)]; fixture.tasks = [taskRow('new-response')]; fixture.delayChat = undefined; fixture.delayTasks = undefined;
    await bell.click(); await expect(sidebar.locator('[data-activity-key="chat:new-response"]')).toHaveCount(1);
    releaseChat(); releaseTasks(); await expect(sidebar.locator('[data-activity-key="chat:old-response"]')).toHaveCount(0); await expect(sidebar.locator('[data-activity-key="scheduled:old-response"]')).toHaveCount(0);
    await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' }); document.dispatchEvent(new Event('visibilitychange')); });
    const hiddenCount = harness.reads.filter((read) => read.includes('limit=50') || read.includes('scheduled-tasks/day')).length;
    await page.clock.runFor(90000); expect(harness.reads.filter((read) => read.includes('limit=50') || read.includes('scheduled-tasks/day')).length).toBe(hiddenCount);
    await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' }); document.dispatchEvent(new Event('visibilitychange')); });
    await expect.poll(() => harness.reads.filter((read) => read.includes('limit=50')).length).toBeGreaterThan(2);
    expect(harness.mutations).toEqual([]); expect(harness.pageErrors).toEqual([]);
  } finally { releaseChat(); releaseTasks(); await harness.close(); }
});

test('a delayed previous-day response cannot replace today while the recent window continues through midnight', async ({ page }, testInfo) => {
  let release!: () => void;
  const fixture: Fixture = { threads: [chatRow('before-midnight')], tasks: [], triggers: [], dreams: [dreamRow()], fixedMountTime: true,
    delayTasks: new Promise<void>((resolve) => { release = resolve; }),
    dayTasks: (day) => [taskRow(day === '2026-10-07' ? 'previous-day' : 'current-day')] };
  const harness = await mountChat(page, testInfo, fixture);
  try {
    await page.getByRole('button', { name: '活动视图', exact: true }).click(); const sidebar = page.locator('#chat-activity-sidebar');
    await expect.poll(() => harness.reads.some((read) => read.includes('scheduled-tasks/day') && read.includes('local_date=2026-10-07'))).toBe(true);
    fixture.delayTasks = undefined; await page.clock.setSystemTime(new Date(NOW)); await page.clock.runFor(3000);
    await expect(sidebar.locator('[data-activity-key="scheduled:current-day"]')).toHaveCount(1);
    expect(harness.reads.some((read) => read.includes('local_date=2026-10-08'))).toBe(true);
    release(); await expect(sidebar.locator('[data-activity-key="scheduled:previous-day"]')).toHaveCount(0);
    await expect(sidebar.locator('[data-activity-key="chat:before-midnight"]')).toHaveCount(1);
    await expect(sidebar.locator('[data-activity-key^="dream:"]')).toHaveCount(1);
    expect(harness.mutations).toEqual([]); expect(harness.pageErrors).toEqual([]);
  } finally { release(); await harness.close(); }
});
