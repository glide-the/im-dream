// [Input] Production task-session navigation components, local Chrome and persisted business-link fixtures.
// [Output] Verify source action anchoring, compact created-task rows inside the assistant reply, navigation and responsive bounds.
// [Pos] Isolated browser presentation test for Chat task-session navigation.
// [Sync] 2026-09-27: cover the screenshot-led marker/list layout and canonical navigation callbacks.
// [Sync] 2026-09-27: exercise ChatMessageList placement and history-pagination fallback in local Chrome.
// [Sync] 2026-09-27: require the created-task list above assistant actions at the same reply width.

import { expect, test } from '@playwright/test';
// @ts-expect-error This browser harness imports Node APIs outside the application tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error This browser harness imports Node APIs outside the application tsconfig.
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

test('task-session navigation matches the source marker and created-task list interaction', async ({ page }, testInfo) => {
  const port = await reservePort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'task-session-navigation-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== '/task-session-navigation') return next();
          try {
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(await vite.transformIndexHtml('/task-session-navigation', '<!doctype html><html><body><div id="root"></div><script type="module" src="/task-session-navigation-harness.js"></script></body></html>'));
          } catch (error) { next(error as Error); }
        });
      },
      resolveId(id) { return id === '/task-session-navigation-harness.js' ? '\0task-session-navigation-harness.js' : null; },
      load(id) {
        if (id !== '\0task-session-navigation-harness.js') return null;
        return `
          import React from 'react';
          import { createRoot } from 'react-dom/client';
          import i18n from '/app/_dream/i18n.ts';
          import ChatMessageList from '/app/_dream/components/chat/ChatMessageList.tsx';
          import '/app/_dream/styles/tokens.css';
          import '/app/_dream/index.css';
          void i18n.changeLanguage('zh');
          window.taskNavigation = [];
          const base = { task_id: 'task-one', source_thread_id: 'source-thread', thread_id: 'child-one', title: '复核 Dream 运行中消息队列与任务会话', launch_status: 'starting', launch_error_code: null, created_at: '2026-09-27T00:00:00Z' };
          const navigate = (threadId) => window.taskNavigation.push(threadId);
          const messages = [
            { id: 'initial-user', role: 'user', parts: [{ type: 'text', text: '检查队列行为并运行完整测试。' }] },
            { id: 'later-user', role: 'user', parts: [{ type: 'text', text: '继续检查恢复。' }] },
            { id: 'assistant-final', role: 'assistant', parts: [{ type: 'text', text: '已完成独立任务。' }] },
          ];
          const created = [base, { ...base, task_id: 'task-two', thread_id: 'child-two', title: '失败任务仍可查看', launch_status: 'failed', launch_error_code: 'TASK_SESSION_LAUNCH_FAILED' }];
          function Harness() {
            const [hasOlderHistory, setHasOlderHistory] = React.useState(false);
            window.setOlderHistory = setHasOlderHistory;
            return React.createElement('main', { style: { boxSizing: 'border-box', width: '100%', maxWidth: '52rem', margin: '2rem auto', padding: '1rem' } },
              React.createElement(ChatMessageList, {
                messages, threadId: 'child-one', isLoading: false, addToolResult: () => {},
                sourceThread: { ...base, source_title: '原来交互的会话' },
                onNavigateThread: navigate, historyHasMore: hasOlderHistory,
                createdTaskLinks: created,
              })); }
          createRoot(document.querySelector('#root')).render(React.createElement(Harness));
        `;
      },
    }],
  });
  try {
    await server.listen();
    await page.goto(`http://127.0.0.1:${port}/task-session-navigation`);
    const source = page.getByRole('button', { name: '打开来源对话' });
    await expect(source).toContainText('原来交互的会话');
    await expect(page.locator('[data-chat-message-id="initial-user"] [aria-label="打开来源对话"]')).toHaveCount(1);
    await expect(page.locator('[data-chat-message-id="later-user"] [aria-label="打开来源对话"]')).toHaveCount(0);
    const sourceBox = await source.boundingBox();
    const userTextBox = await page.getByText('检查队列行为并运行完整测试。').boundingBox();
    expect(sourceBox).not.toBeNull();
    expect(userTextBox).not.toBeNull();
    expect(sourceBox!.y + sourceBox!.height).toBeLessThan(userTextBox!.y);
    await source.click();
    const list = page.getByRole('region', { name: '此对话创建的任务' });
    await expect(list).toContainText('此对话创建的任务 · 2');
    await expect(list).toContainText('启动失败');
    const assistant = page.locator('[data-chat-message-id="assistant-final"]');
    await expect(assistant.getByRole('region', { name: '此对话创建的任务' })).toHaveCount(1);
    const listBox = await list.boundingBox();
    const assistantBox = await assistant.boundingBox();
    const actionBox = await assistant.getByTitle('Copy').boundingBox();
    expect(listBox).not.toBeNull();
    expect(assistantBox).not.toBeNull();
    expect(actionBox).not.toBeNull();
    expect(Math.abs(listBox!.width - assistantBox!.width)).toBeLessThan(1);
    expect(listBox!.y + listBox!.height).toBeLessThanOrEqual(actionBox!.y);
    await list.getByRole('button', { name: '打开聊天' }).first().click();
    expect(await page.evaluate(() => (window as unknown as { taskNavigation: string[] }).taskNavigation)).toEqual(['source-thread', 'child-one']);
    await page.evaluate(() => (window as unknown as { setOlderHistory: (value: boolean) => void }).setOlderHistory(true));
    await expect(page.locator('[data-chat-message-id="initial-user"] [aria-label="打开来源对话"]')).toHaveCount(0);
    await expect(source).toHaveCount(1);
    await page.evaluate(() => (window as unknown as { setOlderHistory: (value: boolean) => void }).setOlderHistory(false));
    await expect(page.locator('[data-chat-message-id="initial-user"] [aria-label="打开来源对话"]')).toHaveCount(1);
    await page.screenshot({ path: testInfo.outputPath('task-session-navigation-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(list).toBeVisible();
    const box = await list.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(390);
    const mobileAssistant = await assistant.boundingBox();
    expect(mobileAssistant).not.toBeNull();
    expect(Math.abs(box!.width - mobileAssistant!.width)).toBeLessThan(1);
    const mobileSource = await source.boundingBox();
    expect(mobileSource).not.toBeNull();
    expect(mobileSource!.x).toBeGreaterThanOrEqual(0);
    expect(mobileSource!.x + mobileSource!.width).toBeLessThanOrEqual(390);
    await page.screenshot({ path: testInfo.outputPath('task-session-navigation-mobile.png'), fullPage: true });
  } finally {
    await server.close();
  }
});
