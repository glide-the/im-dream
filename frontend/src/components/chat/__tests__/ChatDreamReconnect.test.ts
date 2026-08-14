// [Input] A ChatView opened on a Dream-owned source thread while its turn is running.
// [Output] Browser proof that Chat replays the original Chat SSE contract, recovers
//          terminal history, and sends the next turn through the ordinary Chat POST.
// [Pos] Dream -> Chat interoperability regression seam.

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
        reject(new Error('Could not reserve an ephemeral TCP port.'));
        return;
      }
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
}

test('Dream source thread reconnects with Chat SSE then continues as ordinary Chat', async ({ page }) => {
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import ChatView from '/src/components/chat/ChatView.tsx';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';

    createRoot(document.querySelector('#root')).render(
      React.createElement(ChatView, {
        requestedThreadId: 'thread-dream-chat',
        requestedThreadNonce: 1,
      }),
    );
  `;
  const ordinaryChatRequests: Array<Record<string, unknown>> = [];
  let reconnectStarted = false;
  let reconnectFinished = false;
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'chat-dream-reconnect-browser-harness',
      configureServer(vite) {
        vite.middlewares.use((request, response, next) => {
          const streamRequest = request as unknown as {
            readonly method?: string;
            readonly url?: string;
            setEncoding: (encoding: string) => void;
            on: {
              (event: 'data', listener: (chunk: string) => void): void;
              (event: 'end', listener: () => void): void;
            };
          };
          const requestUrl = streamRequest.url ?? '';
          const requestPath = new URL(requestUrl, 'http://127.0.0.1').pathname;
          if (
            requestPath === '/api/claude-agent/threads/thread-dream-chat/stream'
            && streamRequest.method === 'GET'
          ) {
            reconnectStarted = true;
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
            response.setHeader('Cache-Control', 'no-cache, no-transform');
            response.setHeader('X-Accel-Buffering', 'no');
            response.write([
              'data: {"type":"text-start","id":"dream-chat-text"}',
              'data: {"type":"text-delta","id":"dream-chat-text","delta":"Dream delta replayed in Chat"}',
              '',
            ].join('\n\n'));
            setTimeout(() => {
              reconnectFinished = true;
              response.end([
                'data: {"type":"text-end","id":"dream-chat-text"}',
                'data: {"type":"message-final","text":"Dream delta replayed in Chat"}',
                'data: {"type":"finish","finishReason":"stop"}',
                '',
              ].join('\n\n'));
            }, 800);
            return;
          }
          if (requestPath === '/api/claude-agent' && streamRequest.method === 'POST') {
            let rawBody = '';
            streamRequest.setEncoding('utf8');
            streamRequest.on('data', (chunk: string) => { rawBody += chunk; });
            streamRequest.on('end', () => {
              ordinaryChatRequests.push(JSON.parse(rawBody) as Record<string, unknown>);
              response.statusCode = 200;
              response.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
              response.end([
                'data: {"type":"text-start","id":"ordinary-chat-text"}',
                'data: {"type":"text-delta","id":"ordinary-chat-text","delta":"ordinary Chat reply"}',
                'data: {"type":"text-end","id":"ordinary-chat-text"}',
                'data: {"type":"message-final","text":"ordinary Chat reply"}',
                'data: {"type":"finish","finishReason":"stop"}',
                '',
              ].join('\n\n'));
            });
            return;
          }
          if (requestUrl !== '/chat-dream-reconnect') return next();
          void vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root" style="height: 900px"></div>
            <script type="module" src="/chat-dream-reconnect-harness.js"></script></body></html>
          `).then((html) => {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          }, next);
        });
      },
      resolveId(id) {
        return id === '/chat-dream-reconnect-harness.js'
          ? '\0chat-dream-reconnect-harness.js'
          : null;
      },
      load(id) {
        return id === '\0chat-dream-reconnect-harness.js' ? harnessModule : null;
      },
    }],
  });

  const diagnostics: string[] = [];
  const observedApiRequests: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith('/api/')) {
      observedApiRequests.push(`${request.method()} ${url.pathname}`);
    }
  });
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'dream-chat-reconnect-token');
    localStorage.setItem('ink-language', 'en');
  });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (
      path === '/api/claude-agent/threads/thread-dream-chat/stream'
      || (path === '/api/claude-agent' && request.method() === 'POST')
    ) {
      await route.continue();
      return;
    }
    if (path === '/api/claude-agent/threads/thread-dream-chat/messages') {
      const messages: Array<{
        id: string;
        role: string;
        parts: Array<{ type: string; text: string }>;
        metadata: Record<string, unknown>;
        created_at: string;
      }> = [{
        id: 'dream-user',
        role: 'user',
        parts: [{ type: 'text', text: 'Dream source message' }],
        metadata: { kind: 'story-workspace-dream-agent-user' },
        created_at: '2026-08-11T00:00:00Z',
      }];
      if (reconnectFinished) messages.push({
        id: 'dream-assistant',
        role: 'assistant',
        parts: [{ type: 'text', text: 'Dream terminal persisted in Chat' }],
        metadata: {},
        created_at: '2026-08-11T00:00:01Z',
      });
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          thread: {
            id: 'thread-dream-chat',
            title: 'Dream source thread',
            created_at: '2026-08-11T00:00:00Z',
            updated_at: '2026-08-11T00:00:01Z',
          },
          messages,
        }),
      });
      return;
    }
    if (path === '/api/claude-agent/threads/thread-dream-chat/status') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          running: !reconnectFinished,
          lifecycle: reconnectFinished ? 'idle' : 'running',
          turn_count: reconnectFinished ? 1 : 0,
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
    if (path === '/api/decks') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"decks":[]}' });
      return;
    }
    if (path === '/api/system-config') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"data":{}}' });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  try {
    await server.listen();
    const reconnectRequest = page.waitForRequest((request) => (
      new URL(request.url()).pathname
        === '/api/claude-agent/threads/thread-dream-chat/stream'
    ));
    await page.goto(`http://127.0.0.1:${harnessPort}/chat-dream-reconnect`);

    await reconnectRequest;
    await expect.poll(() => reconnectStarted).toBe(true);
    await expect(page.getByText('Dream delta replayed in Chat', { exact: true })).toBeVisible();
    expect(reconnectFinished).toBe(false);
    await expect(page.getByText('Dream terminal persisted in Chat', { exact: true })).toBeVisible();

    const input = page.getByRole('textbox', { name: 'Chat input' });
    await expect(input).toBeEnabled();
    await input.fill('continue with ordinary Chat');
    await page.getByRole('button', { name: 'Send message' }).click();
    await expect(page.getByText('ordinary Chat reply', { exact: true })).toBeVisible();
    expect(ordinaryChatRequests).toHaveLength(1);
    expect(ordinaryChatRequests[0]).toMatchObject({
      id: 'thread-dream-chat',
      resume: true,
    });
    expect(ordinaryChatRequests[0]).not.toHaveProperty('story_workspace_dream_context');
    expect(observedApiRequests).toContain(
      'GET /api/claude-agent/threads/thread-dream-chat/stream',
    );
    expect(observedApiRequests.filter((request) => request === 'POST /api/claude-agent'))
      .toHaveLength(1);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await server.close();
  }
});
