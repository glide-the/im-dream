// [Input] Production ChatMessageList with one server-projected historical assistant final.
// [Output] Local-Chrome evidence for bounded exact-id recovery, single-flight, retry, scheduled-task markers, and MCP App promotion.
// [Pos] Shared Chat/Dream lazy process-detail browser acceptance seam.
// [Sync] 2026-09-02: created for final-first history hydration and on-demand canonical process rendering.
// [Sync] 2026-09-06: prove the exact MCP App panel is a persistent sibling outside the collapsible process.
// [Sync] 2026-10-07: prove a persisted scheduled creation process restores its marker beside the canonical final reply and opens details.
// [Sync] 2026-09-29: auto-recover historical Tool results so persisted scheduled-task markers survive reload.
// [Sync] 2026-09-29: use the production top-level scheduled-task Tool receipt and verify the entire marker opens details.
// [Sync] 2026-10-07: restore a marker from the canonical process detail before opening the scheduled-task sidebar.

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
  import React, { useState } from 'react';
  import { createRoot } from 'react-dom/client';
  import '/app/_dream/i18n.ts';
  import '/app/_dream/styles/tokens.css';
  import '/app/_dream/styles/markdown.css';
  import ChatMessageList from '/app/_dream/components/chat/ChatMessageList.tsx';
  import ScheduledTaskDetailSidebar from '/app/_dream/components/chat/ScheduledTaskDetailSidebar.tsx';

  window.__detailPayload = {
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
  window.__processMode = new URLSearchParams(location.search).get('mode') || 'pending';
  window.fetch = (input) => {
    const url = String(input);
    if (url.includes('/scheduled-tasks/st_1/history')) {
      return Promise.resolve(new Response(JSON.stringify({ triggers: [{
        id: 'trigger_1', task_id: 'st_1', kind: 'scheduled', scheduled_at: '2026-09-30T01:00:00Z',
        definition_revision: 1, title: '晨间复盘', source_thread_id: 'thread-source', time_zone: 'Asia/Shanghai',
        status: 'succeeded', task_session_id: null, target_thread_id: 'thread-result', input_message_id: null,
        target_turn_id: null, final_message_id: 'message-final', error_code: null, skipped_from_at: null,
        skipped_through_at: null, created_at: '2026-09-30T01:00:01Z', updated_at: '2026-09-30T01:00:02Z',
      }, {
        id: 'trigger_0', task_id: 'st_1', kind: 'scheduled', scheduled_at: '2026-09-29T01:00:00Z',
        definition_revision: 1, title: '晨间复盘', source_thread_id: 'thread-source', time_zone: 'Asia/Shanghai',
        status: 'failed', task_session_id: null, target_thread_id: 'thread-older-result', input_message_id: null,
        target_turn_id: null, final_message_id: null, error_code: 'UPSTREAM_FAILED', skipped_from_at: null,
        skipped_through_at: null, created_at: '2026-09-29T01:00:01Z', updated_at: '2026-09-29T01:00:02Z',
      }] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }
    if (url.includes('/scheduled-tasks/st_1')) {
      return Promise.resolve(new Response(JSON.stringify({ task: {
        id: 'st_1', source_thread_id: 'thread-source', title: '晨间复盘', prompt: '整理今天的笔记',
        rule: { kind: 'daily', local_time: '09:00', time_zone: 'Asia/Shanghai' },
        next_run_at: '2026-10-01T01:00:00Z', status: 'active', revision: 1,
        created_at: '2026-09-29T01:00:00Z', updated_at: '2026-09-29T01:00:00Z',
      } }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }
    window.__processRequests += 1;
    window.__processUrls.push(url);
    if (window.__processMode === 'fail-once') {
      window.__processMode = 'success';
      return Promise.resolve(new Response('{}', { status: 503 }));
    }
    if (window.__processMode === 'success') {
      return Promise.resolve(new Response(JSON.stringify(window.__detailPayload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }));
    }
    return new Promise((resolve) => {
      window.__resolveProcess = () => resolve(new Response(JSON.stringify(window.__detailPayload), {
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
  function Harness() {
    const [selected, setSelected] = useState(null);
    return React.createElement('div', { style: { height: '620px', display: 'flex', overflow: 'hidden' } },
      React.createElement('div', { 'data-chat-scroll-region': 'messages', style: { flex: 1, overflow: 'auto' } },
        React.createElement(ChatMessageList, {
          messages: [summary], threadId: 'thread/1', isLoading: false, addToolResult: () => {},
          historicalMessageIds: new Set(['assistant/1']),
          onOpenScheduledTask: (task) => { window.__openedScheduledTask = task; setSelected(task); },
        })),
      selected ? React.createElement(ScheduledTaskDetailSidebar, {
        taskId: selected.id, snapshot: selected, onClose: () => setSelected(null),
        onOpenThread: (threadId) => { window.__openedThread = threadId; },
      }) : null,
    );
  }
  createRoot(document.querySelector('#root')).render(React.createElement(Harness));
`;

async function startHarness() {
  const port = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'chat-history-process-lazy-load-browser-harness',
      enforce: 'pre',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as { url?: string }).url ?? '';
          if (requestUrl !== '/chat-history-process' && !requestUrl.startsWith('/chat-history-process?')) return next();
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
        if (id.endsWith('/mcp-apps/McpAppHostPanel') || id.endsWith('/mcp-apps/McpAppHostPanel.tsx')) {
          return '\0mock-mcp-app-host-panel.js';
        }
        return id === '/chat-history-process.js' ? '\0chat-history-process.js' : null;
      },
      load(id) {
        if (id === '\0mock-mcp-app-host-panel.js') {
          return `
            import React from 'react';
            export default function MockMcpAppHostPanel({ call }) {
              return React.createElement('section', {
                'aria-label': 'Interactive tool result',
                'data-testid': 'mcp-app-panel',
                'data-tool-call-id': call.toolCallId,
              }, 'interactive App result');
            }
          `;
        }
        return id === '\0chat-history-process.js' ? harnessModule : null;
      },
    }],
  });
  await server.listen();
  return { server, url: `http://127.0.0.1:${port}/chat-history-process` };
}

test('historical final auto-recovers once and repeated expansion shares that detail fetch', async ({ page }) => {
  const { server, url } = await startHarness();
  try {
    await page.goto(url);
    const toggle = page.locator('.chat-assistant-turn__toggle');
    await expect(page.getByText('visible final answer')).toBeVisible();
    await expect.poll(() => page.evaluate(() => (window as unknown as { __processRequests: number }).__processRequests)).toBe(1);

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

test('automatic detail failure keeps final readable and explicit expansion retries the same endpoint', async ({ page }) => {
  const { server, url } = await startHarness();
  try {
    await page.goto(`${url}?mode=fail-once`);
    await expect.poll(() => page.evaluate(() => (window as unknown as { __processRequests: number }).__processRequests)).toBe(1);
    await page.getByRole('button', { name: /process/i }).click();
    await expect(page.getByText('visible final answer')).toBeVisible();
    await expect(page.locator('[data-turn-process]')
      .getByText('loaded process evidence').last()).toBeVisible();
    expect(await page.evaluate(() => (window as unknown as { __processRequests: number }).__processRequests)).toBe(2);
  } finally {
    await server.close();
  }
});

test('validated MCP App panel stays outside the process disclosure after collapse', async ({ page }) => {
  const { server, url } = await startHarness();
  try {
    await page.goto(url);
    await page.evaluate(() => {
      const result = {
        content: [{ type: 'text', text: 'Read-only state: ready' }],
        structuredContent: { state: 'ready' },
      };
      (window as unknown as {
        __processMode: string;
        __detailPayload: unknown;
      }).__processMode = 'success';
      (window as unknown as { __detailPayload: unknown }).__detailPayload = {
        id: 'assistant/1',
        role: 'assistant',
        parts: [
          { type: 'reasoning', text: 'loaded process evidence' },
          {
            type: 'dynamic-tool',
            toolName: 'mcp__official-basic__get-time',
            toolCallId: 'call-1',
            state: 'output-available',
            input: { requested: true },
            output: result,
            toolMetadata: {
              mcpAppResult: {
                version: 1,
                serverRef: 'official-basic',
                toolName: 'get-time',
                toolCallId: 'call-1',
                input: { requested: true },
                workspaceScope: 'workspace-1',
                resourceUri: 'ui://get-time/mcp-app.html',
                result,
              },
            },
          },
          { type: 'text', text: 'visible final answer' },
        ],
        metadata: {
          turnId: 'turn-1',
          turnStatus: 'completed',
          finalPartIndex: 2,
          durationMs: 1200,
        },
      };
      (window as unknown as { __resolveProcess: () => void }).__resolveProcess();
    });

    const toggle = page.locator('.chat-assistant-turn__toggle');
    await toggle.click();
    await expect(page.locator('[data-turn-process]')
      .getByText('loaded process evidence').last()).toBeVisible();

    const panel = page.locator('[data-testid="mcp-app-panel"]');
    await expect(panel).toHaveCount(1);
    await expect(panel).toHaveText('interactive App result');
    expect(await panel.evaluate((element) => ({
      insideProcess: Boolean(element.closest('[data-turn-process]')),
      insideOutsideProcess: Boolean(element.closest('[data-turn-outside-process]')),
    }))).toEqual({ insideProcess: false, insideOutsideProcess: true });

    await toggle.click();
    await expect(page.locator('[data-turn-process]')).toHaveCount(0);
    await expect(panel).toHaveCount(1);
    expect(await panel.evaluate((element) => Boolean(
      element.closest('[data-turn-outside-process]'),
    ))).toBe(true);
  } finally {
    await server.close();
  }
});

test('persisted create_scheduled_task process restores a marker beside its canonical final reply', async ({ page }) => {
  const { server, url } = await startHarness();
  try {
    await page.goto(url);
    await page.evaluate(() => {
      (window as unknown as { __detailPayload: unknown }).__detailPayload = {
        id: 'assistant/1',
        role: 'assistant',
        parts: [
          {
            type: 'tool-invocation', toolName: 'mcp__user__create_scheduled_task', toolCallId: 'schedule-1',
            state: 'output-available', input: { title: '晨间复盘' },
            output: {
              ok: true,
              status: 'ok',
              scheduled_task: {
                id: 'st_1', title: '晨间复盘', status: 'active', revision: 1,
                next_run_at: '2026-09-30T01:00:00Z',
                rule: { kind: 'daily', local_time: '09:00', time_zone: 'Asia/Shanghai' },
              },
            },
          },
          { type: 'text', text: 'visible final answer' },
        ],
        metadata: { turnId: 'turn-1', turnStatus: 'completed', finalPartIndex: 1, durationMs: 1200 },
      };
    });
    await page.waitForFunction(() => typeof (
      window as unknown as { __resolveProcess?: () => void }
    ).__resolveProcess === 'function');
    await page.evaluate(() => {
      (window as unknown as { __resolveProcess: () => void }).__resolveProcess();
    });
    const marker = page.locator('.scheduled-task-marker');
    await expect(marker).toContainText('晨间复盘');
    await expect(marker).toContainText('Daily · 09:00');
    await expect(page.getByText('‹ Terminal')).toHaveCount(0);
    await expect(marker).toHaveRole('button');
    await expect(marker).toHaveAccessibleName(/Open scheduled task/);
    await marker.click();
    await expect.poll(() => page.evaluate(() => (
      window as unknown as { __openedScheduledTask?: { id: string } }
    ).__openedScheduledTask?.id)).toBe('st_1');
    const sidebar = page.getByRole('complementary', { name: 'Scheduled task' });
    await expect(sidebar.getByRole('heading', { name: 'Task information' })).toBeVisible();
    await expect(sidebar.getByRole('heading', { name: 'Conversations' })).toBeVisible();
    await expect(sidebar.getByRole('heading', { name: 'Task schedule' })).toBeVisible();
    await expect(sidebar.locator('h3')).toHaveText(['Task information', 'Conversations', 'Task schedule']);
    await expect(sidebar).toContainText('整理今天的笔记');
    await expect(sidebar).toContainText('Completed');
    await sidebar.getByRole('button', { name: /Creation conversation/ }).click();
    await expect.poll(() => page.evaluate(() => (
      window as unknown as { __openedThread?: string }
    ).__openedThread)).toBe('thread-source');
    const runConversations = sidebar.getByRole('button', { name: /Run conversation/ });
    await expect(runConversations).toHaveCount(2);
    await runConversations.nth(0).click();
    await expect.poll(() => page.evaluate(() => (
      window as unknown as { __openedThread?: string }
    ).__openedThread)).toBe('thread-result');
    await runConversations.nth(1).click();
    await expect.poll(() => page.evaluate(() => (
      window as unknown as { __openedThread?: string }
    ).__openedThread)).toBe('thread-older-result');
  } finally {
    await server.close();
  }
});
