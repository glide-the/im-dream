// [Input] ChatView lazy-thread first-send flow under the application's React StrictMode runtime.
// [Output] Browser regression proving one user submission owns exactly one /api/claude-agent POST.
// [Pos] Chat-only queued-send lifecycle regression seam; Dream adapters are intentionally out of scope.
// [Sync] 2026-08-24: serve the shell's read-only Dream Run collection, classify
//                    its StrictMode cleanup abort, and retain strict failure.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
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
        reject(new Error('Could not reserve an ephemeral TCP port.'));
        return;
      }
      const { port } = address;
      probe.close((error?: Error) => {
        if (error) reject(error);
        else resolve(port);
      });
    });
  });
}

test('a lazy-created Chat thread sends its queued first turn exactly once', async ({ page }) => {
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import ChatView from '/src/components/chat/ChatView.tsx';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';

    createRoot(document.querySelector('#root')).render(
      React.createElement(
        React.StrictMode,
        null,
        React.createElement(ChatView, null),
      ),
    );
  `;
  const agentRequests: Array<Record<string, unknown>> = [];
  let terminalFramesSent = 0;
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'chat-queued-send-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          const streamRequest = request as unknown as {
            readonly method?: string;
            setEncoding: (encoding: string) => void;
            on: {
              (event: 'data', listener: (chunk: string) => void): void;
              (event: 'end', listener: () => void): void;
            };
          };
          const requestPath = requestUrl
            ? new URL(requestUrl, 'http://127.0.0.1').pathname
            : '';
          if (requestPath === '/api/claude-agent' && streamRequest.method === 'POST') {
            let rawBody = '';
            streamRequest.setEncoding('utf8');
            streamRequest.on('data', (chunk: string) => {
              rawBody += chunk;
            });
            streamRequest.on('end', () => {
              agentRequests.push(JSON.parse(rawBody) as Record<string, unknown>);
              response.statusCode = 200;
              response.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
              response.setHeader('Cache-Control', 'no-cache, no-transform');
              response.setHeader('X-Accel-Buffering', 'no');
              response.write([
                'data: {"type":"text-start","id":"text-main"}',
                'data: {"type":"text-delta","id":"text-main","delta":"streamed-before-final"}',
                '',
              ].join('\n\n'));
              setTimeout(() => {
                terminalFramesSent += 1;
                response.end([
                  'data: {"type":"text-end","id":"text-main"}',
                  'data: {"type":"message-final","text":"streamed-before-final"}',
                  'data: {"type":"finish","finishReason":"stop"}',
                  '',
                ].join('\n\n'));
              }, 500);
            });
            return;
          }
          if (requestUrl !== '/chat-queued-send') return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><head><link rel="icon" href="data:,"></head>
              <body><div id="root" style="height: 900px"></div>
              <script type="module" src="/chat-queued-send-harness.js"></script></body></html>
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
        return id === '/chat-queued-send-harness.js'
          ? '\0chat-queued-send-harness.js'
          : null;
      },
      load(id) {
        return id === '\0chat-queued-send-harness.js' ? harnessModule : null;
      },
    }],
  });

  const unexpectedApiRequests: string[] = [];
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    const url = new URL(request.url());
    const isExpectedDreamRunsStrictModeAbort = (
      request.method() === 'GET'
      && url.pathname === '/api/story-workspace/dream-runs'
      && request.failure()?.errorText === 'net::ERR_ABORTED'
    );
    if (isExpectedDreamRunsStrictModeAbort) return;
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });

  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'chat-single-send-test-token');
    localStorage.setItem('ink-language', 'en');
  });

  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }

    if (path === '/api/claude-agent/threads' && method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ thread_id: 'thread-single-send' }),
      });
      return;
    }
    if (path === '/api/claude-agent' && method === 'POST') {
      // Let the Vite middleware above deliver a genuinely chunked response.
      await route.continue();
      return;
    }
    if (path === '/api/claude-agent/threads/thread-single-send/messages') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          thread: {
            id: 'thread-single-send',
            title: null,
            created_at: '2026-08-11T00:00:00Z',
            updated_at: '2026-08-11T00:00:00Z',
          },
          messages: [],
        }),
      });
      return;
    }
    if (path === '/api/claude-agent/threads/thread-single-send/status') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          running: false,
          lifecycle: 'idle',
          turn_count: 0,
          pending_tool_call_ids: [],
          tool_confirmation_observation: 'known',
        }),
      });
      return;
    }
    if (path === '/api/claude-agent/threads') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"threads":[]}' });
      return;
    }
    if (path === '/api/story-workspace/dream-runs' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"runs":[]}' });
      return;
    }
    if (path === '/api/decks') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"decks":[]}' });
      return;
    }
    if (path === '/api/system-config') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"data":{}}' });
      return;
    }
    if (path === '/api/storage') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      return;
    }

    unexpectedApiRequests.push(`${method} ${path}`);
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  try {
    await server.listen();
    const address = server.httpServer?.address();
    if (address === null || address === undefined || typeof address === 'string') {
      throw new Error('Chat queued-send harness did not bind a TCP port.');
    }
    await page.goto(`http://127.0.0.1:${address.port}/chat-queued-send`);
    await page.waitForTimeout(250);
    expect(
      diagnostics,
      `Chat harness did not reach a clean render. Body: ${await page.locator('body').innerText()}`,
    ).toEqual([]);
    expect(unexpectedApiRequests).toEqual([]);

    const input = page.getByRole('textbox', { name: 'Chat input' });
    await expect(input).toBeVisible();
    await input.fill('only send this once');
    await page.getByRole('button', { name: 'Send message' }).click();

    await expect.poll(() => agentRequests.length).toBeGreaterThan(0);
    await expect(page.getByText('streamed-before-final', { exact: true })).toBeVisible();
    expect(terminalFramesSent).toBe(0);
    await expect.poll(() => terminalFramesSent).toBe(1);
    expect(agentRequests).toHaveLength(1);
    expect(agentRequests[0]).toMatchObject({
      id: 'thread-single-send',
      resume: true,
    });
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await server.close();
  }
});
