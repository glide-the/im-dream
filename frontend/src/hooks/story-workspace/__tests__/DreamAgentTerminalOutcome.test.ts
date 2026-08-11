// [Input] A run-scoped Dream snapshot plus genuinely chunked safe SSE terminal events.
// [Output] Chromium proof that partial Dream text renders before EOF and a safe
//          failed outcome survives terminal REST reconciliation.
// [Pos] Dream Agent browser lifecycle regression seam.

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

test('Dream renders a partial delta before EOF and keeps a safe failed outcome', async ({ page }) => {
  const runId = 'run_0123456789abcdef0123456789abcdef';
  const turnId = 'turn-dream-failure';
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import { useStoryWorkspaceDreamAgent } from '/src/hooks/story-workspace/useStoryWorkspaceDreamAgent.ts';

    function Harness() {
      const agent = useStoryWorkspaceDreamAgent('${runId}');
      return React.createElement('main', null,
        React.createElement('p', { 'data-testid': 'stream' }, agent.streamText),
        React.createElement('p', { 'data-testid': 'outcome' }, agent.terminalOutcome ?? 'none'),
        React.createElement('p', { 'data-testid': 'error' }, agent.error?.message ?? ''),
      );
    }
    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  let terminalSent = false;
  let controlledStreamAborts = 0;
  let snapshotReads = 0;
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'dream-terminal-outcome-browser-harness',
      configureServer(vite) {
        vite.middlewares.use((request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url ?? '';
          const path = new URL(requestUrl, 'http://127.0.0.1').pathname;
          if (path.endsWith('/dream-agent/events')) {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
            response.setHeader('Cache-Control', 'no-cache, no-transform');
            response.setHeader('X-Accel-Buffering', 'no');
            response.write([
              'event: status\ndata: {"lifecycle":"streaming"}',
              `id: ${turnId}:0\nevent: assistant_text_delta\ndata: {"turnId":"${turnId}","delta":"失败前的增量🙂"}`,
              '',
            ].join('\n\n'));
            setTimeout(() => {
              terminalSent = true;
              response.end([
                `id: ${turnId}:1\nevent: agent_turn_failed\ndata: {"turnId":"${turnId}","code":"DREAM_AGENT_TURN_FAILED"}`,
                '',
              ].join('\n\n'));
            }, 500);
            return;
          }
          if (requestUrl !== '/dream-terminal-outcome') return next();
          void vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root"></div><script type="module" src="/dream-terminal-outcome-harness.js"></script></body></html>
          `).then((html) => {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          }, next);
        });
      },
      resolveId(id) {
        return id === '/dream-terminal-outcome-harness.js'
          ? '\0dream-terminal-outcome-harness.js'
          : null;
      },
      load(id) {
        return id === '\0dream-terminal-outcome-harness.js' ? harnessModule : null;
      },
    }],
  });

  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    if (terminalSent
      && new URL(request.url()).pathname.endsWith('/dream-agent/events')
      && request.failure()?.errorText === 'net::ERR_ABORTED') {
      controlledStreamAborts += 1;
      return;
    }
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  await page.addInitScript(() => localStorage.setItem('auth_token', 'dream-terminal-token'));
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith('/dream-agent/events')) {
      await route.continue();
      return;
    }
    if (path.endsWith('/dream-agent/messages')) {
      snapshotReads += 1;
      const running = snapshotReads === 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          storyWorkspaceRunId: runId,
          lifecycle: running ? 'streaming' : 'idle',
          activeTurnId: running ? turnId : null,
          canSend: !running,
          sendBlockReason: running ? 'generating' : null,
          messages: [],
          pendingToolConfirmations: [],
          toolConfirmationObservation: 'known',
          snapshotAt: '2026-08-11T09:00:00Z',
        }),
      });
      return;
    }
    await route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
  });

  try {
    await server.listen();
    await page.goto(`http://127.0.0.1:${harnessPort}/dream-terminal-outcome`);
    await expect(page.getByTestId('stream')).toHaveText('失败前的增量🙂');
    expect(terminalSent).toBe(false);
    await expect(page.getByTestId('outcome')).toHaveText('failed');
    await expect(page.getByTestId('error')).toHaveText('Dream Agent 本次执行失败，请重试。');
    expect(snapshotReads).toBeGreaterThan(1);
    expect(controlledStreamAborts).toBe(1);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await server.close();
  }
});
