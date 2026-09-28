// [Input] A ChatView opened on a Dream-owned source thread while its turn is running.
// [Output] Browser proof that refresh reattaches the same running turn, recovers
//          terminal history once, and sends only the next turn through Chat POST.
// [Pos] Dream -> Chat interoperability regression seam.
// [Sync] 2026-09-05: serve the paged history/stabilization metadata required by
//                    the shared current Chat/Dream hydration contract.
// [Sync] 2026-09-06: reload during one live turn, require a second GET stream,
//                    and reject duplicate POSTs or transcript rows.
// [Sync] 2026-09-07: bind API_BASE to the fixture origin before module load so
//                    the observed GET must reach the test-owned middleware.
// [Sync] 2026-09-07: split metadata from the first text frame so a running
//                    re-entry proves callback churn cannot abort live replay.
// [Sync] 2026-09-28: verify shell task navigation without the retired task-result card/polling path.
//                    across source and child Threads without another Chat POST.
// [Sync] 2026-09-28: an already-open idle source Chat hydrates a later child result and attaches a running return turn without reload or another POST.
// [Sync] 2026-09-28: source Chat renders its created-task list inside the assistant reply and the
//                    separate task-activity popover while Deck metadata remains unchanged.

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

test('refresh reconnects the same running turn without duplicate POST or messages', async ({ page }) => {
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import '/app/_dream/i18n.ts';
    import ChatView from '/app/_dream/components/chat/ChatView.tsx';
    import '/app/_dream/styles/tokens.css';
    import '/app/_dream/styles/markdown.css';

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
  const childResultDelivered = false;
  const secondChildDispatching = false;
  let secondChildDelivered = false;
  let reconnectStreamRequests = 0;
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
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
            reconnectStreamRequests += 1;
            reconnectStarted = true;
            if (reconnectStreamRequests === 2) {
              // Exact completion race: hydration observed running, but the
              // producer committed its final message before GET /stream.
              reconnectFinished = true;
              response.statusCode = 409;
              response.setHeader('Content-Type', 'application/json');
              response.end('{"detail":"Thread is not running"}');
              return;
            }
            if (reconnectStreamRequests === 3) {
              response.statusCode = 200;
              response.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
              response.setHeader('Cache-Control', 'no-cache, no-transform');
              response.write('data: {"type":"message-metadata","turnId":"return-turn-two"}\n\n');
              secondChildDelivered = true;
              response.end([
                'data: {"type":"text-start","id":"return-two-text"}',
                'data: {"type":"text-delta","id":"return-two-text","delta":"Second child result arrived"}',
                'data: {"type":"text-end","id":"return-two-text"}',
                'data: {"type":"message-final","text":"Second child result arrived"}',
                'data: {"type":"finish","finishReason":"stop"}',
                '',
              ].join('\n\n'));
              return;
            }
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
            response.setHeader('Cache-Control', 'no-cache, no-transform');
            response.setHeader('X-Accel-Buffering', 'no');
            response.write('data: {"type":"message-metadata","turnId":"dream-turn-live"}\n\n');
            setTimeout(() => {
              if (response.destroyed || response.writableEnded) return;
              response.write([
                'data: {"type":"text-start","id":"dream-chat-text"}',
                'data: {"type":"text-delta","id":"dream-chat-text","delta":"Dream delta visible before refresh"}',
                '',
              ].join('\n\n'));
            }, 80);
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
          if (
            requestPath === '/api/claude-agent/threads/thread-dream-chat/messages'
            && streamRequest.method === 'GET'
          ) {
            const latestMessageId = secondChildDelivered ? 'return-two-final'
              : secondChildDispatching ? 'return-two-input'
                : childResultDelivered ? 'return-final'
                  : reconnectFinished ? 'dream-assistant' : 'dream-user';
            const knownLatestMessageId = new URL(
              requestUrl,
              'http://127.0.0.1',
            ).searchParams.get('known_latest_message_id');
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
            if (childResultDelivered) messages.push({
              id: 'return-input',
              role: 'user',
              parts: [{ type: 'text', text: 'Technical task handoff input' }],
              metadata: { kind: 'task-session-result' },
              created_at: '2026-08-11T00:00:02Z',
            }, {
              id: 'return-final',
              role: 'assistant',
              parts: [{ type: 'text', text: 'I reviewed the child result' }],
              metadata: { turnStatus: 'completed', taskResultNotificationId: 'notice-child' },
              created_at: '2026-08-11T00:00:04Z',
            });
            if (secondChildDispatching) messages.push({
              id: 'return-two-input', role: 'user',
              parts: [{ type: 'text', text: 'Second technical handoff input' }],
              metadata: { kind: 'task-session-result' },
              created_at: '2026-08-11T00:00:05Z',
            });
            if (secondChildDelivered) messages.push({
              id: 'return-two-final', role: 'assistant',
              parts: [{ type: 'text', text: 'Second child result arrived' }],
              metadata: { turnStatus: 'completed', taskResultNotificationId: 'notice-two' },
              created_at: '2026-08-11T00:00:06Z',
            });
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end(JSON.stringify({
              thread: {
                id: 'thread-dream-chat',
                title: 'Dream source thread',
                created_at: '2026-08-11T00:00:00Z',
                updated_at: '2026-08-11T00:00:01Z',
              },
              messages,
              next_cursor: null,
              has_more: false,
              latest_message_id: latestMessageId,
              unchanged: knownLatestMessageId === latestMessageId,
            }));
            return;
          }
          if (
            requestPath === '/api/claude-agent/threads/thread-child-task/messages'
            && streamRequest.method === 'GET'
          ) {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end(JSON.stringify({
              thread: {
                id: 'thread-child-task', title: 'Inspect the note',
                created_at: '2026-08-11T00:00:02Z', updated_at: '2026-08-11T00:00:03Z',
              },
              messages: [{
                id: 'child-user', role: 'user',
                parts: [{ type: 'text', text: 'Please inspect the note' }],
                metadata: {}, created_at: '2026-08-11T00:00:02Z',
              }, {
                id: 'child-final', role: 'assistant',
                parts: [{ type: 'text', text: 'The note was reviewed' }],
                metadata: {}, created_at: '2026-08-11T00:00:03Z',
              }],
              next_cursor: null, has_more: false,
              latest_message_id: 'child-final', unchanged: false,
            }));
            return;
          }
          if (
            requestPath === '/api/claude-agent/threads/thread-dream-chat/status'
            && streamRequest.method === 'GET'
          ) {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end(JSON.stringify({
              running: !reconnectFinished || (secondChildDispatching && !secondChildDelivered),
              lifecycle: !reconnectFinished || (secondChildDispatching && !secondChildDelivered)
                ? 'running' : 'idle',
              turn_count: reconnectFinished ? 1 : 0,
              pending_tool_call_ids: [],
              tool_confirmation_observation: 'known',
            }));
            return;
          }
          if (requestPath === '/api/claude-agent/threads/thread-child-task/status') {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end(JSON.stringify({
              running: false, lifecycle: 'idle', turn_count: 1,
              pending_tool_call_ids: [], tool_confirmation_observation: 'known',
            }));
            return;
          }
          if (requestPath.endsWith('/task-links')) {
            const relation = {
              task_id: 'task-child', source_thread_id: 'thread-dream-chat',
              thread_id: 'thread-child-task', title: 'Inspect the note',
              launch_status: 'starting', launch_error_code: null,
              created_at: '2026-08-11T00:00:02Z',
            };
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end(JSON.stringify(requestPath.includes('/thread-child-task/')
              ? { source: { ...relation, source_title: 'Dream source thread' }, created: [] }
              : { source: null, created: [relation] }));
            return;
          }
          if (requestPath === '/api/claude-agent/threads/thread-dream-chat/tasks/task-child') {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end(JSON.stringify({
              task_id: 'task-child', thread_id: 'thread-child-task',
              title: 'Inspect the note', launch_status: 'starting',
              error_code: null, status: 'completed', running: false,
              result_message_id: 'child-final', result_text: 'The note was reviewed',
            }));
            return;
          }
          if (requestPath.endsWith('/task-results')) {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end(JSON.stringify({
              results: requestPath.includes('/thread-child-task/') ? [] : [{
                notification_id: 'notice-child',
                task_id: 'task-child',
                source_thread_id: 'thread-dream-chat',
                target_thread_id: 'thread-child-task',
                target_turn_id: 'child-turn',
                target_final_message_id: 'child-final',
                title: 'Inspect the note',
                final_text: 'The note was reviewed',
                status: childResultDelivered ? 'delivered' : 'pending',
                revision: childResultDelivered ? 3 : 1,
                claim_id: 'claim-child', source_turn_id: 'return-turn',
                source_input_message_id: 'return-input',
                source_final_message_id: 'return-final',
                error_code: null,
                created_at: '2026-08-11T00:00:03Z',
                updated_at: '2026-08-11T00:00:04Z',
              }, ...(secondChildDispatching ? [{
                notification_id: 'notice-two', task_id: 'task-two',
                source_thread_id: 'thread-dream-chat',
                target_thread_id: 'thread-child-task',
                target_turn_id: 'child-turn-two',
                target_final_message_id: 'child-final-two',
                title: 'Inspect another note', final_text: 'A second note was reviewed',
                status: secondChildDelivered ? 'delivered' : 'dispatching',
                revision: secondChildDelivered ? 3 : 2,
                claim_id: 'claim-two', source_turn_id: 'return-turn-two',
                source_input_message_id: 'return-two-input',
                source_final_message_id: secondChildDelivered ? 'return-two-final' : null,
                error_code: null,
                created_at: '2026-08-11T00:00:05Z',
                updated_at: '2026-08-11T00:00:06Z',
              }] : [])],
            }));
            return;
          }
          if (requestPath === '/api/claude-agent/threads') {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end('{"threads":[]}');
            return;
          }
          if (requestPath === '/api/decks') {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end('{"decks":[]}');
            return;
          }
          if (requestPath === '/api/system-config') {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end('{"data":{}}');
            return;
          }
          if (requestPath.startsWith('/api/')) {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'application/json');
            response.end('{}');
            return;
          }
          if (requestUrl !== '/chat-dream-reconnect') return next();
          void vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root" style="height: 900px"></div>
            <script>window.__INK_RUNTIME_CONFIG__ = { apiBaseUrl: window.location.origin, wsBaseUrl: '' };</script>
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
    if (message.type() !== 'error') return;
    if (reconnectFinished
      && message.text() === 'Failed to load resource: the server responded with a status of 409 (Conflict)') return;
    diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    const requestPath = new URL(request.url()).pathname;
    if (
      requestPath === '/api/claude-agent/threads/thread-dream-chat/stream'
      && request.failure()?.errorText === 'net::ERR_ABORTED'
    ) return;
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
  try {
    await server.listen();
    const reconnectRequest = page.waitForRequest((request) => (
      request.url().startsWith(`http://127.0.0.1:${harnessPort}/`)
      && new URL(request.url()).pathname
          === '/api/claude-agent/threads/thread-dream-chat/stream'
    ));
    await page.goto(`http://127.0.0.1:${harnessPort}/chat-dream-reconnect`);

    await reconnectRequest;
    await expect.poll(() => reconnectStarted).toBe(true);
    await expect(page.getByText('Dream delta visible before refresh', { exact: true })).toBeVisible();
    expect(reconnectFinished).toBe(false);

    const secondReconnectRequest = page.waitForRequest((request) => (
      request.url().startsWith(`http://127.0.0.1:${harnessPort}/`)
      && new URL(request.url()).pathname
          === '/api/claude-agent/threads/thread-dream-chat/stream'
    ));
    await page.reload();
    await secondReconnectRequest;
    await expect.poll(() => reconnectStreamRequests).toBe(2);
    expect(observedApiRequests.filter((request) => request === 'POST /api/claude-agent'))
      .toHaveLength(0);
    await expect(page.getByText('Dream terminal persisted in Chat', { exact: true })).toBeVisible();
    await expect(page.getByText('Dream source message', { exact: true })).toHaveCount(1);
    await expect(page.getByText('Dream terminal persisted in Chat', { exact: true })).toHaveCount(1);
    await expect(page.getByRole('region', { name: 'Task result' })).toHaveCount(0);
    expect(observedApiRequests.filter((request) => request === 'POST /api/claude-agent'))
      .toHaveLength(0);

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
    expect(observedApiRequests.filter((request) => (
      request === 'GET /api/claude-agent/threads/thread-dream-chat/stream'
    ))).toHaveLength(2);
    expect(observedApiRequests.filter((request) => request === 'POST /api/claude-agent'))
      .toHaveLength(1);
    expect(observedApiRequests.some((request) => request.endsWith('/task-results'))).toBe(false);
    await expect(page.getByRole('region', { name: 'Tasks created by this conversation' }))
      .toContainText('Inspect the note');
    await page.getByRole('button', { name: 'Task activity' }).click();
    await expect(page.getByRole('dialog', { name: 'Task activity' })).toContainText('Inspect the note');
    await expect(page.getByRole('dialog', { name: 'Task activity' })).toContainText('Completed');
    await page.getByRole('button', { name: 'Inspect the note Completed' }).click();
    await expect(page.getByText('Please inspect the note', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Open the source conversation' }).click();
    await expect(page.getByText('Dream source message', { exact: true })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Task result' })).toHaveCount(0);
    expect(observedApiRequests.filter((request) => request === 'POST /api/claude-agent'))
      .toHaveLength(1);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await server.close();
  }
});
