// [Input] Real ChatPanel Stop button, Browser session/CSRF state and a delayed same-origin Stop response.
// [Output] Executable request-policy, strict DTO, compact queue-error feedback and component-remount delivery regressions.
// [Pos] Provider-free Browser acceptance seam for main-turn cancellation.
// [Sync] 2026-09-17: prove one Stop POST survives ChatPanel unmount and validates the current Thread receipt.
// [Sync] 2026-09-27: verify queue capability failure preserves the draft, status check recovers, and Stop returns after clearing.
// [Sync] 2026-09-28: clear the Tiptap draft with user keyboard input before asserting the single Stop action.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { mkdtemp, rm } from 'node:fs/promises';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { tmpdir } from 'node:os';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { join } from 'node:path';
import { createServer } from 'vite';
import {
  clearBrowserSession,
  loadBrowserSession,
} from '../../../lib/browserSession';
import {
  requestClaudeThreadStop,
  ThreadStopRequestError,
} from '../threadStop';

const CSRF = 'c'.repeat(43);
const THREAD_ID = 'thread-stop-control';

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

async function setBrowserSession(): Promise<void> {
  await loadBrowserSession((async () => new Response(JSON.stringify({
    user: {
      id: '7',
      email: 'actor@example.test',
      display_name: 'Actor',
      avatar_url: null,
      role: 'user',
      created_at: '2026-09-17T00:00:00+00:00',
    },
    csrf_token: CSRF,
  }), { status: 200, headers: { 'Content-Type': 'application/json' } })) as typeof fetch);
}

test('Stop transport sends the Browser credential policy and accepts only the current Thread DTO', async () => {
  await setBrowserSession();
  try {
    let capturedUrl = '';
    let capturedInit: RequestInit | undefined;
    const receipt = await requestClaudeThreadStop(THREAD_ID, async (input, init) => {
      capturedUrl = String(input);
      capturedInit = init;
      return new Response(JSON.stringify({
        ok: true,
        thread_id: THREAD_ID,
        stop_requested: true,
        running: false,
        lifecycle: 'idle',
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }, 1_000);

    expect(capturedUrl).toBe(`/api/claude-agent/threads/${THREAD_ID}/stop`);
    expect(capturedInit?.method).toBe('POST');
    expect(capturedInit?.credentials).toBe('include');
    expect(capturedInit?.cache).toBe('no-store');
    expect(capturedInit?.keepalive).toBe(true);
    expect(new Headers(capturedInit?.headers).get('x-ink-csrf')).toBe(CSRF);
    expect(receipt).toEqual({
      threadId: THREAD_ID,
      stopRequested: true,
      running: false,
      lifecycle: 'idle',
    });

    for (const payload of [
      {
        ok: true,
        thread_id: 'thread-other',
        stop_requested: true,
        running: false,
        lifecycle: 'idle',
      },
      {
        ok: true,
        thread_id: THREAD_ID,
        stop_requested: false,
        running: false,
        lifecycle: 'idle',
        unexpected: true,
      },
    ]) {
      await expect(requestClaudeThreadStop(
        THREAD_ID,
        async () => new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
        1_000,
      )).rejects.toMatchObject<Partial<ThreadStopRequestError>>({
        code: 'STOP_RESPONSE_INVALID',
      });
    }
  } finally {
    clearBrowserSession();
  }
});

test('clicking Stop emits one POST that survives ChatPanel unmount', async ({ page }, testInfo) => {
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import '/app/_dream/i18n.ts';
    import ChatPanel from '/app/_dream/components/chat/ChatPanel.tsx';
    import { loadBrowserSession } from '/app/_dream/lib/browserSession.ts';
    import '/app/_dream/styles/tokens.css';
    import '/app/_dream/styles/markdown.css';

    await loadBrowserSession(async () => new Response(JSON.stringify({
      user: {
        id: '7', email: 'actor@example.test', display_name: 'Actor',
        avatar_url: null, role: 'user', created_at: '2026-09-17T00:00:00+00:00',
      },
      csrf_token: '${CSRF}',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    const root = createRoot(document.querySelector('#root'));
    window.__unmountStopHarness = () => root.unmount();
    root.render(React.createElement(ChatPanel, {
      threadId: '${THREAD_ID}',
      initialMessages: [],
      initialRuntimeRunning: true,
      initialToolConfirmationKnown: true,
      inputPlaceholder: 'Ask Ink & Memory…',
    }));
  `;

  const harnessPort = await reserveEphemeralPort();
  const cacheDir = await mkdtemp(join(tmpdir(), 'ink-dream-stop-vite-'));
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    cacheDir,
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'chat-stop-control-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== '/chat-stop-control') return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><head><link rel="icon" href="data:,"></head>
              <body><div id="root" style="height: 844px"></div>
              <script type="module" src="/chat-stop-control-harness.js"></script></body></html>
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
        return id === '/chat-stop-control-harness.js'
          ? '\0chat-stop-control-harness.js'
          : null;
      },
      load(id) {
        return id === '\0chat-stop-control-harness.js' ? harnessModule : null;
      },
    }],
  }).catch(async (error) => {
    await rm(cacheDir, { recursive: true, force: true });
    throw error;
  });

  const origin = `http://127.0.0.1:${harnessPort}`;
  let stopCount = 0;
  let stopFinishedCount = 0;
  let stopHeaders: Record<string, string> = {};
  let queueReady = false;
  let releaseStop!: () => void;
  const stopRelease = new Promise<void>((resolve) => { releaseStop = resolve; });
  let markStopStarted!: () => void;
  const stopStarted = new Promise<void>((resolve) => { markStopStarted = resolve; });
  const failures: string[] = [];

  page.on('requestfailed', request => failures.push(
    `${request.failure()?.errorText ?? 'failed'} ${request.url()}`,
  ));
  page.on('requestfinished', request => {
    if (new URL(request.url()).pathname === `/api/claude-agent/threads/${THREAD_ID}/stop`) {
      stopFinishedCount += 1;
    }
  });
  await page.context().addCookies([{
    name: 'ink_dream_session',
    value: 'opaque-test-handle',
    url: origin,
  }]);
  await page.route('**/*', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === `/api/claude-agent/threads/${THREAD_ID}/stop`) {
      stopCount += 1;
      stopHeaders = request.headers();
      markStopStarted();
      await stopRelease;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          thread_id: THREAD_ID,
          stop_requested: true,
          running: false,
          lifecycle: 'idle',
        }),
      });
      return;
    }
    if (path === '/api/system-config') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"data":{}}' });
      return;
    }
    if (path === `/api/claude-agent/threads/${THREAD_ID}/inputs`) {
      const unavailable = request.method() === 'POST' || !queueReady;
      await route.fulfill({
        status: unavailable ? 503 : 200,
        contentType: 'application/json',
        body: unavailable
          ? JSON.stringify({ detail: { error_code: 'DREAM_DATA_SCHEMA_NOT_READY' } })
          : JSON.stringify({ entries: [], local_owner: true }),
      });
      return;
    }
    if (path.startsWith('/api/')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      return;
    }
    await route.continue();
  });

  try {
    await server.listen();
    await page.goto(`${origin}/chat-stop-control`);
    const editor = page.locator('#chat-input');
    await editor.fill('keep this queued draft');
    await page.getByRole('button', { name: 'Send message' }).click();
    const queueError = page.getByRole('alert').filter({ hasText: 'Messages cannot be queued right now' });
    await expect(queueError).toBeVisible();
    await expect(editor).toHaveText('keep this queued draft');
    const errorBox = await queueError.boundingBox();
    const dockBox = await page.locator('.ai-input-dock').boundingBox();
    expect(errorBox).not.toBeNull();
    expect(dockBox).not.toBeNull();
    expect(errorBox!.x).toBeGreaterThanOrEqual(dockBox!.x);
    expect(errorBox!.x + errorBox!.width).toBeLessThanOrEqual(dockBox!.x + dockBox!.width);
    await queueError.screenshot({ path: testInfo.outputPath('queue-capability-error.png') });
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);
    queueReady = true;
    await page.getByRole('button', { name: 'Check queue status' }).click();
    await expect(queueError).toHaveCount(0);
    await expect(editor).toHaveText('keep this queued draft');
    await editor.click();
    await editor.press('ControlOrMeta+A');
    await editor.press('Backspace');
    await expect(editor).toBeEmpty();
    const stopButton = page.getByRole('button', { name: 'Stop generating' });
    await expect(stopButton).toBeVisible();
    await stopButton.click();
    await stopStarted;
    await expect(page.getByRole('button', { name: 'Stopping' })).toBeVisible();

    await page.evaluate(() => {
      (window as Window & { __unmountStopHarness?: () => void }).__unmountStopHarness?.();
    });
    releaseStop();
    await expect.poll(() => stopFinishedCount).toBe(1);

    expect(stopCount).toBe(1);
    expect(stopHeaders['x-ink-csrf']).toBe(CSRF);
    expect(stopHeaders.cookie).toContain('ink_dream_session=opaque-test-handle');
    expect(failures.filter(value => value.includes('/stop'))).toEqual([]);
  } finally {
    releaseStop();
    await server.close();
    await rm(cacheDir, { recursive: true, force: true });
  }
});
