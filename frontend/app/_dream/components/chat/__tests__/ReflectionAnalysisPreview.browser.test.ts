// [Input] Production ChatMessageList, an oversized Reflections prompt, local Chrome and a navigation callback.
// [Output] Verify the raw prompt is not mounted, one localized tag is rendered, and section navigation remains responsive.
// [Pos] Isolated browser presentation test for Reflections Analyze Chat previews.
// [Sync] 2026-10-14: cover exact preview replacement, ordinary-message fallback, click, focus and narrow bounds.

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

test('oversized Reflections user text becomes one section tag without mounting the private body', async ({ page }, testInfo) => {
  const port = await reservePort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'reflection-analysis-preview-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== '/reflection-analysis-preview') return next();
          try {
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(await vite.transformIndexHtml('/reflection-analysis-preview', '<!doctype html><html><body><div id="root"></div><script type="module" src="/reflection-analysis-preview-harness.js"></script></body></html>'));
          } catch (error) { next(error as Error); }
        });
      },
      resolveId(id) { return id === '/reflection-analysis-preview-harness.js' ? '\0reflection-analysis-preview-harness.js' : null; },
      load(id) {
        if (id !== '\0reflection-analysis-preview-harness.js') return null;
        return `
          import React from 'react';
          import { createRoot } from 'react-dom/client';
          import i18n from '/app/_dream/i18n.ts';
          import ChatMessageList from '/app/_dream/components/chat/ChatMessageList.tsx';
          import '/app/_dream/styles/tokens.css';
          import '/app/_dream/index.css';
          import '/app/_dream/components/chat/ChatView.css';
          void i18n.changeLanguage('zh');
          window.openedReflectionSections = [];
          window.openedThreads = [];
          const privateBody = 'PRIVATE_NOTION_BODY_SHOULD_NOT_MOUNT '.repeat(60000);
          const messages = [
            { id: 'reflection', role: 'user', parts: [{ type: 'text', text: privateBody + '\\nComplete this Reflections analysis in this turn.\\n# Reflections — Behavioral Patterns Workflow\\nAnalyze all evidence.' }] },
            { id: 'assistant-final', role: 'assistant', parts: [{ type: 'text', text: '回顾分析结果仍然可读。' }] },
            { id: 'ordinary', role: 'user', parts: [{ type: 'text', text: '普通 Chat 消息仍按原样显示。' }] },
          ];
          createRoot(document.querySelector('#root')).render(React.createElement('main', { style: { width: '100%', maxWidth: '52rem', margin: '2rem auto', padding: '1rem', boxSizing: 'border-box' } },
            React.createElement(ChatMessageList, {
              messages,
              threadId: 'reflection-thread',
              isLoading: false,
              addToolResult: () => {},
              sourceThread: { task_id: 'reflection-task', source_thread_id: 'source-thread', thread_id: 'reflection-thread', source_title: '来源对话', title: '回顾分析', launch_status: 'starting', launch_error_code: null, created_at: '2026-10-14T00:00:00Z' },
              onNavigateThread: (threadId) => window.openedThreads.push(threadId),
              onOpenReflectionSection: (section) => window.openedReflectionSections.push(section),
            })));
        `;
      },
    }],
  });

  try {
    await server.listen();
    await page.goto(`http://127.0.0.1:${port}/reflection-analysis-preview`);
    const reflectionMessage = page.locator('[data-chat-message-id="reflection"]');
    const tag = reflectionMessage.getByRole('button', { name: '打开回顾分析：行为模式' });
    await expect(tag).toHaveText('回顾分析 · 行为模式');
    await expect(reflectionMessage.locator('.reflection-analysis-preview__tag')).toHaveCount(1);
    await expect(reflectionMessage.locator('[title="Copy"]')).toHaveCount(0);
    const source = reflectionMessage.getByRole('button', { name: '打开来源对话' });
    await expect(source).toContainText('来源对话');
    const sourceBox = await source.boundingBox();
    const tagBox = await tag.boundingBox();
    expect(sourceBox).not.toBeNull();
    expect(tagBox).not.toBeNull();
    expect(sourceBox!.y + sourceBox!.height).toBeLessThanOrEqual(tagBox!.y);
    await expect(page.getByText('回顾分析结果仍然可读。')).toBeVisible();
    await expect(page.getByText('普通 Chat 消息仍按原样显示。')).toBeVisible();
    expect(await page.evaluate(() => document.body.textContent?.includes('PRIVATE_NOTION_BODY_SHOULD_NOT_MOUNT'))).toBe(false);

    await tag.focus();
    await expect(tag).toBeFocused();
    await source.click();
    await tag.click();
    expect(await page.evaluate(() => (window as unknown as { openedThreads: string[] }).openedThreads)).toEqual(['source-thread']);
    expect(await page.evaluate(() => (window as unknown as { openedReflectionSections: string[] }).openedReflectionSections)).toEqual(['patterns']);
    await page.screenshot({ path: testInfo.outputPath('reflection-analysis-preview-desktop.png'), fullPage: true });

    await page.setViewportSize({ width: 375, height: 812 });
    const box = await tag.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(375);
    await page.screenshot({ path: testInfo.outputPath('reflection-analysis-preview-narrow.png'), fullPage: true });
  } finally {
    await server.close();
  }
});
