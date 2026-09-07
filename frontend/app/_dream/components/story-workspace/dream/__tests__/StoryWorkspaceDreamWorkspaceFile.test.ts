// [Input] Dream's direct ChatPanel host, an enabled Workspace config, owned Thread history, and a mocked regular file response.
// [Output] Prove recovered workspace:// links leave capability checking, preserve actor/Thread/path binding, and download exact bytes.
// [Pos] Dream workspace-file composition regression seam.
// [Sync] 2026-09-07: cover the Next-era direct ChatPanel host that previously omitted WorkspaceProvider.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node harness intentionally imports Node APIs.
import { readFileSync } from 'node:fs';
// @ts-expect-error Playwright's Node harness intentionally imports Node APIs.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node harness intentionally imports Node APIs.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chromium' });

const THREAD_ID = 'thread-dream-workspace-file';
const FILE_PATH = 'files/EP01-穿越乐坊-剧本-v3.md';
const FILE_NAME = 'EP01-穿越乐坊-剧本-v3.md';
const FILE_CONTENT = '# EP01 穿越乐坊\n\n确定性回归剧本正文。\n';

async function reserveEphemeralPort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createNetServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (address === null || typeof address === 'string') {
        probe.close();
        reject(new Error('Could not reserve a Dream Workspace file test port.'));
        return;
      }
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
}

test('Dream recovered workspace file becomes downloadable through the owned Thread content route', async ({ page }) => {
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import '/app/_dream/i18n.ts';
    import '/app/_dream/styles/tokens.css';
    import '/app/_dream/styles/markdown.css';
    import { StoryWorkspaceDreamThreadChat } from '/app/_dream/components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx';

    createRoot(document.querySelector('#root')).render(
      React.createElement('main', { style: { height: '760px', display: 'flex' } },
        React.createElement(StoryWorkspaceDreamThreadChat, {
          threadId: '${THREAD_ID}',
        }),
      ),
    );
  `;
  const port = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../..', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'dream-workspace-file-harness',
      configureServer(vite) {
        vite.middlewares.use((request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url ?? '';
          if (requestUrl !== '/dream-workspace-file') return next();
          void vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root"></div>
            <script type="module" src="/dream-workspace-file.js"></script></body></html>
          `).then((html) => {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          }, next);
        });
      },
      resolveId(id) {
        return id === '/dream-workspace-file.js' ? '\0dream-workspace-file.js' : null;
      },
      load(id) {
        return id === '\0dream-workspace-file.js' ? harnessModule : null;
      },
    }],
  });

  const fileRequests: Array<{
    readonly authorization: string | undefined;
    readonly path: string | null;
    readonly sessionId: string | null;
  }> = [];
  const supportingRequests: string[] = [];
  const unexpectedRequests: string[] = [];
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'dream-workspace-file-token');
    localStorage.setItem('ink-language', 'en');
  });
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    if (!url.pathname.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (url.pathname === '/api/system-config') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"workspace_enabled":true}' });
      return;
    }
    if (url.pathname === '/api/storage') {
      supportingRequests.push(url.pathname);
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      return;
    }
    if (url.pathname === '/api/claude-agent/skill-commands') {
      supportingRequests.push(url.pathname);
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"commands":[]}' });
      return;
    }
    if (url.pathname === `/api/claude-agent/threads/${THREAD_ID}/plugin-load-receipt`) {
      supportingRequests.push(url.pathname);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          thread_id: THREAD_ID,
          deck_id: null,
          workspace_found: true,
          receipt: null,
          launch_manifest: null,
        }),
      });
      return;
    }
    if (url.pathname === `/api/claude-agent/threads/${THREAD_ID}/messages`) {
      const latestMessageId = 'assistant-workspace-file';
      const knownLatestMessageId = url.searchParams.get('known_latest_message_id');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          thread: {
            id: THREAD_ID,
            title: 'Dream Workspace file',
            created_at: '2026-09-07T00:00:00Z',
            updated_at: '2026-09-07T00:00:01Z',
          },
          messages: knownLatestMessageId === latestMessageId ? [] : [{
            id: latestMessageId,
            role: 'assistant',
            parts: [{ type: 'text', text: `[下载剧本](workspace://${FILE_PATH})` }],
            metadata: {},
            created_at: '2026-09-07T00:00:01Z',
          }],
          next_cursor: null,
          has_more: false,
          latest_message_id: latestMessageId,
          unchanged: knownLatestMessageId === latestMessageId,
        }),
      });
      return;
    }
    if (url.pathname === `/api/claude-agent/threads/${THREAD_ID}/status`) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          running: false,
          lifecycle: 'idle',
          turn_count: 1,
          pending_tool_call_ids: [],
          tool_confirmation_observation: 'known',
        }),
      });
      return;
    }
    if (url.pathname === '/api/workspace/files/content') {
      fileRequests.push({
        authorization: route.request().headers().authorization,
        path: url.searchParams.get('path'),
        sessionId: url.searchParams.get('sessionId'),
      });
      await route.fulfill({
        status: 200,
        contentType: 'text/markdown; charset=utf-8',
        body: FILE_CONTENT,
      });
      return;
    }
    unexpectedRequests.push(`${route.request().method()} ${url.pathname}`);
    await route.fulfill({ status: 500, contentType: 'application/json', body: '{}' });
  });

  await server.listen();
  try {
    await page.goto(`http://127.0.0.1:${port}/dream-workspace-file`);
    const downloadButton = page.getByRole('button', { name: '下载剧本' });
    await expect(downloadButton).toBeEnabled();
    await expect(page.locator('[data-workspace-file-state="loading"]')).toHaveCount(0);
    await expect(page.locator('[data-workspace-file-state="ready"]')).toHaveCount(1);

    const downloadPromise = page.waitForEvent('download');
    await downloadButton.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(FILE_NAME);
    const downloadedPath = await download.path();
    expect(downloadedPath).not.toBeNull();
    expect(readFileSync(downloadedPath!, 'utf8')).toBe(FILE_CONTENT);
    await expect(page.locator('[data-workspace-file-state="success"]')).toHaveCount(1);

    expect(fileRequests).toEqual([{
      authorization: 'Bearer dream-workspace-file-token',
      path: FILE_PATH,
      sessionId: THREAD_ID,
    }]);
    expect(supportingRequests.sort()).toEqual([
      '/api/claude-agent/skill-commands',
      `/api/claude-agent/threads/${THREAD_ID}/plugin-load-receipt`,
      '/api/storage',
    ]);
    expect(unexpectedRequests).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await server.close();
  }
});
