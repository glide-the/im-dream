// [Input] Structured Dream binding-conflict SSE, a persisted user text/file message, and ChatPanel authoritative recovery callback.
// [Output] Browser regression proving safe error copy, attachment retention, one-turn submission, and read-only reload recovery.
// [Pos] Mocked-browser acceptance seam for Dream-bound Chat turn failures.
// [Sync] 2026-08-31: initial binding-conflict interaction coverage.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chromium', viewport: { width: 390, height: 844 } });

async function reserveEphemeralPort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createNetServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (address === null || typeof address === 'string') {
        probe.close();
        reject(new Error('Could not reserve an ephemeral TCP port.'));
        return;
      }
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
}

test('binding conflict keeps the submitted text and attachment while reload stays read-only', async ({ page }) => {
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import ChatPanel from '/src/components/chat/ChatPanel.tsx';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';

    const persistedMessages = [{
      id: 'message-conflict-persisted',
      role: 'user',
      parts: [
        {
          type: 'file',
          url: '/api/storage/file?key=thread-binding/person-relations.txt',
          mediaType: 'text/plain',
          filename: '人物关系分析.txt',
        },
        { type: 'text', text: '请根据附件重新梳理人物关系。' },
      ],
    }];
    window.__bindingReloadCount = 0;
    const recovery = () => {
      window.__bindingReloadCount += 1;
      return {
        messages: persistedMessages,
        settledToolCallIds: new Set(),
        runtimePendingToolCallIds: new Set(),
        running: false,
      };
    };

    createRoot(document.querySelector('#root')).render(
      React.createElement(ChatPanel, {
        threadId: 'thread-binding-conflict',
        initialMessages: [],
        queuedPrompt: '请根据附件重新梳理人物关系。',
        queuedAttachments: [{
          name: '人物关系分析.txt',
          type: 'text/plain',
          size: 24,
          storageKey: 'thread-binding/person-relations.txt',
          workspacePath: 'files/person-relations.txt',
          savedAt: '2026-08-31T04:00:00Z',
        }],
        queuedToolChoice: 'auto',
        queuedPromptNonce: 1,
        claimQueuedPrompt: () => true,
        onReconnectComplete: recovery,
        inputPlaceholder: 'Ask Ink & Memory…',
      }),
    );
  `;
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'chat-thread-binding-conflict-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== '/chat-thread-binding-conflict') return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><head><link rel="icon" href="data:,"></head>
              <body><div id="root" style="height: 844px"></div>
              <script type="module" src="/chat-thread-binding-conflict-harness.js"></script></body></html>
            `);
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          } catch (error) {
            next(error as Error);
          }
        });
      },
      resolveId(id) {
        return id === '/chat-thread-binding-conflict-harness.js'
          ? '\0chat-thread-binding-conflict-harness.js'
          : null;
      },
      load(id) {
        return id === '\0chat-thread-binding-conflict-harness.js' ? harnessModule : null;
      },
    }],
  });

  let agentPostCount = 0;
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'binding-conflict-test-token');
    localStorage.setItem('ink-language', 'zh');
  });
  await page.route('**/*', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (path === '/api/claude-agent' && request.method() === 'POST') {
      agentPostCount += 1;
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream; charset=utf-8',
        body: [
          'data: {"type":"error","errorText":"Dream binding unavailable.","errorCode":"DREAM_THREAD_BINDING_CONFLICT","retryable":false}',
          'data: {"type":"finish","finishReason":"error"}',
          '',
        ].join('\n\n'),
      });
      return;
    }
    if (path === '/api/system-config') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"data":{"workspace_enabled":true}}' });
      return;
    }
    if (path.endsWith('/subagents')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"tasks":[]}' });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  try {
    await server.listen();
    await page.goto(`http://127.0.0.1:${harnessPort}/chat-thread-binding-conflict`);

    await expect.poll(() => agentPostCount).toBe(1);
    const alert = page.getByRole('alert');
    await expect(alert).toContainText('当前对话暂时无法继续创作');
    await expect(alert).toContainText('本次 Agent 未开始处理');
    await expect(page.getByText('请根据附件重新梳理人物关系。')).toBeVisible();
    await expect(page.getByText('人物关系分析.txt')).toBeVisible();
    await expect(page.getByText(/DREAM_THREAD_BINDING_CONFLICT/)).toHaveCount(0);
    await expect(page.getByText(/^Error:/)).toHaveCount(0);
    expect(agentPostCount).toBe(1);

    const reloadCountBefore = await page.evaluate(() => (
      (window as Window & { __bindingReloadCount?: number }).__bindingReloadCount ?? 0
    ));
    await page.getByRole('button', { name: '重新加载对话' }).click();
    await expect(alert).toHaveCount(0);
    await expect(page.getByText('请根据附件重新梳理人物关系。')).toBeVisible();
    await expect(page.getByText('人物关系分析.txt')).toBeVisible();
    const reloadCountAfter = await page.evaluate(() => (
      (window as Window & { __bindingReloadCount?: number }).__bindingReloadCount ?? 0
    ));
    expect(reloadCountAfter).toBe(reloadCountBefore + 1);
    expect(agentPostCount).toBe(1);
    expect(diagnostics).toEqual([]);

    const bodyMetrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(bodyMetrics.scrollWidth).toBeLessThanOrEqual(bodyMetrics.clientWidth);
  } finally {
    await server.close();
  }
});
