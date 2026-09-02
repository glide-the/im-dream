// [Input] Production ChatMessageList with one server-projected historical assistant final.
// [Output] Local-Chrome evidence for expand-only exact-id fetch, single-flight, retry, and unmount.
// [Pos] Shared Chat/Dream lazy process-detail browser acceptance seam.
// [Sync] 2026-09-02: created for final-first history hydration and on-demand canonical process rendering.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node harness imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright Node harness imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chrome', viewport: { width: 900, height: 700 } });

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

const harnessModule = `
  import React from 'react';
  import { createRoot } from 'react-dom/client';
  import '/src/i18n.ts';
  import '/src/styles/tokens.css';
  import '/src/styles/markdown.css';
  import ChatMessageList from '/src/components/chat/ChatMessageList.tsx';

  const detailPayload = {
    id: 'assistant/1',
    role: 'assistant',
    parts: [
      { type: 'reasoning', text: 'loaded process evidence' },
      { type: 'text', text: 'visible final answer' },
    ],
    metadata: {
      turnId: 'turn-1',
      turnStatus: 'completed',
      finalPartIndex: 1,
      durationMs: 1200,
    },
  };
  window.__processRequests = 0;
  window.__processUrls = [];
  window.__processMode = 'pending';
  window.fetch = (input) => {
    window.__processRequests += 1;
    window.__processUrls.push(String(input));
    if (window.__processMode === 'fail-once') {
      window.__processMode = 'success';
      return Promise.resolve(new Response('{}', { status: 503 }));
    }
    if (window.__processMode === 'success') {
      return Promise.resolve(new Response(JSON.stringify(detailPayload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }));
    }
    return new Promise((resolve) => {
      window.__resolveProcess = () => resolve(new Response(JSON.stringify(detailPayload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }));
    });
  };

  const summary = {
    id: 'assistant/1',
    role: 'assistant',
    parts: [{ type: 'text', text: 'visible final answer' }],
    metadata: {
      turnId: 'turn-1',
      turnStatus: 'completed',
      finalPartIndex: 1,
      durationMs: 1200,
      historyProjectionVersion: 1,
      historyProcessAvailable: true,
    },
  };
  createRoot(document.querySelector('#root')).render(React.createElement('div', {
    'data-chat-scroll-region': 'messages',
    style: { height: '620px', overflow: 'auto' },
  }, React.createElement(ChatMessageList, {
    messages: [summary],
    threadId: 'thread/1',
    isLoading: false,
    addToolResult: () => {},
    historicalMessageIds: new Set(['assistant/1']),
  })));
`;

async function startHarness() {
  const port = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'chat-history-process-lazy-load-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if ((request as { url?: string }).url !== '/chat-history-process') return next();
          const html = await vite.transformIndexHtml('/chat-history-process', `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root"></div><script type="module" src="/chat-history-process.js"></script></body></html>
          `);
          response.statusCode = 200;
          response.setHeader('Content-Type', 'text/html; charset=utf-8');
          response.end(html);
        });
      },
      resolveId(id) {
        return id === '/chat-history-process.js' ? '\0chat-history-process.js' : null;
      },
      load(id) {
        return id === '\0chat-history-process.js' ? harnessModule : null;
      },
    }],
  });
  await server.listen();
  return { server, url: `http://127.0.0.1:${port}/chat-history-process` };
}

test('collapsed final makes no request and repeated expansion shares one detail fetch', async ({ page }) => {
  const { server, url } = await startHarness();
  try {
    await page.goto(url);
    const toggle = page.locator('.chat-assistant-turn__toggle');
    await expect(page.getByText('visible final answer')).toBeVisible();
    expect(await page.evaluate(() => (window as unknown as { __processRequests: number }).__processRequests)).toBe(0);

    await toggle.click();
    await expect(page.getByText(/Loading process/i)).toBeVisible();
    await toggle.click();
    await toggle.click();
    expect(await page.evaluate(() => (window as unknown as { __processRequests: number }).__processRequests)).toBe(1);
    await page.evaluate(() => (window as unknown as { __resolveProcess: () => void }).__resolveProcess());
    const loadedProcess = page.locator('[data-turn-process]')
      .getByText('loaded process evidence').last();
    await expect(loadedProcess).toBeVisible();
    const urls = await page.evaluate(() => (
      (window as unknown as { __processUrls: string[] }).__processUrls
    ));
    expect(urls[0]).toContain('/threads/thread%2F1/messages/assistant%2F1/process');

    await toggle.click();
    await expect(page.locator('[data-turn-process]')).toHaveCount(0);
    await expect(page.getByText('visible final answer')).toBeVisible();
  } finally {
    await server.close();
  }
});

test('detail failure keeps final readable and retry reuses the same public endpoint', async ({ page }) => {
  const { server, url } = await startHarness();
  try {
    await page.goto(url);
    await page.evaluate(() => {
      (window as unknown as { __processMode: string }).__processMode = 'fail-once';
    });
    await page.getByRole('button', { name: /process/i }).click();
    await expect(page.getByText(/Process could not be loaded/i)).toBeVisible();
    await expect(page.getByText('visible final answer')).toBeVisible();
    await page.getByRole('button', { name: 'Retry' }).click();
    await expect(page.locator('[data-turn-process]')
      .getByText('loaded process evidence').last()).toBeVisible();
    expect(await page.evaluate(() => (window as unknown as { __processRequests: number }).__processRequests)).toBe(2);
  } finally {
    await server.close();
  }
});
