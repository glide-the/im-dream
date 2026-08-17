// [Input] Dream wrapper over canonical thread history/status/SSE.
// [Output] Initial idle is not a terminal signal; observed running -> EOF -> idle settles once.
// [Pos] Shared-thread settlement race regression seam.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node harness intentionally imports Node APIs.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node harness intentionally imports Node APIs.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chromium' });

async function reserveEphemeralPort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createNetServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (address === null || typeof address === 'string') {
        probe.close();
        reject(new Error('Could not reserve a Dream settlement test port.'));
        return;
      }
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
}

test('initial idle never settles; a canonical running to terminal transition settles exactly once', async ({ page }) => {
  const harnessModule = `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';
    import { StoryWorkspaceDreamThreadChat } from '/src/components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx';

    function Harness() {
      const [refreshNonce, setRefreshNonce] = useState(0);
      const [settled, setSettled] = useState(0);
      const [expectedMessageId, setExpectedMessageId] = useState(null);
      window.observeScheduledTurn = (messageId) => {
        setExpectedMessageId(messageId);
        setRefreshNonce((value) => value + 1);
      };
      window.mountExpectedMessage = (messageId) => setExpectedMessageId(messageId);
      return React.createElement('main', { style: { height: '760px', display: 'flex' } },
        React.createElement('output', { id: 'settled' }, String(settled)),
        React.createElement('output', { id: 'expected-message' }, expectedMessageId ?? 'none'),
        React.createElement(StoryWorkspaceDreamThreadChat, {
          threadId: 'thread-dream-settlement',
          refreshNonce,
          expectedMessageId,
          onSettled: () => {
            setSettled((value) => value + 1);
            setExpectedMessageId(null);
          },
        }),
      );
    }
    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  const port = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'dream-thread-settlement-harness',
      configureServer(vite) {
        vite.middlewares.use((request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url ?? '';
          if (requestUrl !== '/dream-thread-settlement') return next();
          void vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root"></div>
            <script type="module" src="/dream-thread-settlement.js"></script></body></html>
          `).then((html) => {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          }, next);
        });
      },
      resolveId(id) {
        return id === '/dream-thread-settlement.js' ? '\0dream-thread-settlement.js' : null;
      },
      load(id) {
        return id === '\0dream-thread-settlement.js' ? harnessModule : null;
      },
    }],
  });

  let phase: 'initial-idle' | 'scheduled-unknown' | 'running' | 'terminal' = 'initial-idle';
  let expectedMessageId: string | null = null;
  let expectedDispatchStatus: 'dispatching' | 'dispatched' | 'failed' | null = null;
  let statusReads = 0;
  let initialUnknownReads = 2;
  let scheduledUnknownReads = 0;
  let allowScheduledRun = false;
  const legacyRequests: string[] = [];
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'dream-settlement-token');
    localStorage.setItem('ink-language', 'zh');
  });
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (/\/dream-agent\/(?:messages|events|tool-confirm)/.test(path)) {
      legacyRequests.push(path);
      await route.abort();
      return;
    }
    if (path === '/api/system-config') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      return;
    }
    if (path === '/api/claude-agent/threads/thread-dream-settlement/messages') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          thread: {
            id: 'thread-dream-settlement', title: 'Dream shared thread',
            created_at: '2026-08-11T00:00:00Z', updated_at: '2026-08-11T00:00:02Z',
          },
          messages: [{
            id: 'assistant-terminal', role: 'assistant',
            parts: [{ type: 'text', text: '同一 thread 的最终结果' }], metadata: {},
            created_at: '2026-08-11T00:00:02Z',
          }, ...(expectedMessageId && expectedDispatchStatus ? [{
            id: expectedMessageId,
            role: 'user',
            parts: [{ type: 'text', text: 'PRIVATE INTERNAL COMMAND' }],
            metadata: {
              kind: 'story-workspace-dream-agent-user',
              visibility: 'system-hidden',
              dispatch_status: expectedDispatchStatus,
            },
            created_at: '2026-08-11T00:00:03Z',
          }] : [])],
        }),
      });
      return;
    }
    if (path === '/api/claude-agent/threads/thread-dream-settlement/status') {
      statusReads += 1;
      if (initialUnknownReads > 0) {
        initialUnknownReads -= 1;
        await route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
        return;
      }
      if (phase === 'scheduled-unknown' && !allowScheduledRun) {
        scheduledUnknownReads += 1;
        await route.fulfill({ status: 502, contentType: 'application/json', body: '{}' });
        return;
      }
      if (phase === 'scheduled-unknown') phase = 'running';
      const current = phase;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          running: current === 'running',
          lifecycle: current === 'running' ? 'running' : 'idle',
          turn_count: current === 'terminal' ? 1 : 0,
          pending_tool_call_ids: [], tool_confirmation_observation: 'known',
        }),
      });
      return;
    }
    if (path === '/api/claude-agent/threads/thread-dream-settlement/stream') {
      phase = 'terminal';
      expectedDispatchStatus = 'dispatched';
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream; charset=utf-8',
        headers: { 'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no' },
        body: 'data: {"type":"finish","finishReason":"stop"}\n\n',
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

    await server.listen();
  try {
    await page.goto(`http://127.0.0.1:${port}/dream-thread-settlement`);
    await expect(
      page.locator('#settled'),
      `Dream thread harness did not mount: ${diagnostics.join(' | ')}`,
    ).toHaveText('0');
    await expect(page.getByRole('textbox', { name: '聊天输入' })).toBeEnabled();
    await expect.poll(() => statusReads).toBeGreaterThanOrEqual(3);
    await expect(page.locator('#settled')).toHaveText('0');

    expectedMessageId = 'message-scheduled-running';
    expectedDispatchStatus = 'dispatching';
    phase = 'scheduled-unknown';
    await page.evaluate((messageId) => {
      (window as unknown as { observeScheduledTurn: (id: string) => void })
        .observeScheduledTurn(messageId);
    }, expectedMessageId);
    await expect.poll(() => scheduledUnknownReads).toBeGreaterThanOrEqual(2);
    // Canonical Chat keeps the composer editable while a turn is pending but
    // disables Send. Dream must reuse that input-state contract rather than
    // inventing a page-specific disabled editor.
    const pendingInput = page.getByRole('textbox', { name: '聊天输入' });
    await pendingInput.fill('结算后仍可继续发送');
    await expect(page.getByRole('button', { name: '发送消息' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /停止生成|Stop generating/ })).toHaveCount(0);
    await expect(page.locator('#settled')).toHaveText('0');
    allowScheduledRun = true;
    await expect(page.locator('#settled')).toHaveText('1');
    await expect(page.locator('#expected-message')).toHaveText('none');
    const recoveredInput = page.getByRole('textbox', { name: '聊天输入' });
    await expect(recoveredInput).toHaveText('结算后仍可继续发送');
    await expect(page.getByRole('button', { name: '发送消息' })).toBeEnabled();

    expectedMessageId = 'message-completed-before-mount';
    expectedDispatchStatus = 'dispatched';
    await page.evaluate((messageId) => {
      (window as unknown as { mountExpectedMessage: (id: string) => void })
        .mountExpectedMessage(messageId);
    }, expectedMessageId);
    await expect(page.locator('#settled')).toHaveText('2');
    await expect(page.getByText('PRIVATE INTERNAL COMMAND')).toBeVisible();

    expectedMessageId = 'message-failed-before-mount';
    expectedDispatchStatus = 'failed';
    await page.evaluate((messageId) => {
      (window as unknown as { mountExpectedMessage: (id: string) => void })
        .mountExpectedMessage(messageId);
    }, expectedMessageId);
    await expect(page.locator('#settled')).toHaveText('3');
    expect(legacyRequests).toEqual([]);
  } finally {
    await page.close();
    await server.close();
  }
});
