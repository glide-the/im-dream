// [Input] A Chat thread containing human Dream messages, a private episode-action
//         envelope, and thread-owned subagents that outlive the main stream.
// [Output] Browser regression proving private envelopes stay hidden while the
//          composer uses the main thread runtime rather than transcript counts.
// [Pos] Dream-to-Chat rendering and subagent composer status regression seam.

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

function subagentTask(index: number, status: 'running' | 'completed') {
  return {
    task_id: `task-${status}-${index}`,
    agent_id: `agent-${status}-${index}`,
    agent_type: 'Explore',
    description: `${status} task ${index}`,
    summary: status === 'completed' ? `completed result ${index}` : null,
    status,
    tool_call_id: `tool-${status}-${index}`,
    spawn_depth: 1,
    started_at: '2026-08-11T08:08:52Z',
    finished_at: status === 'completed' ? '2026-08-11T08:08:53Z' : null,
    duration_ms: status === 'completed' ? 1000 : null,
    error: null,
    activity: [],
    messages: [],
    message_count: 0,
    messages_truncated: false,
    projection_version: 2,
  };
}

test('Chat hides private Dream actions and does not let stale subagent transcripts block input', async ({ page }) => {
  const dreamRunId = 'run_0123456789abcdef0123456789abcdef';
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import ChatView from '/src/components/chat/ChatView.tsx';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';

    createRoot(document.querySelector('#root')).render(
      React.createElement(ChatView, {
        requestedThreadId: 'thread-dream-subagents',
        requestedThreadNonce: 1,
      }),
    );
  `;
  let subagentsRunning = true;
  let dreamConfirmationPending = false;
  const threadConfirmationRequests: Array<Record<string, unknown>> = [];
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'chat-subagent-status-browser-harness',
      configureServer(vite) {
        vite.middlewares.use((request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url ?? '';
          if (requestUrl !== '/chat-subagent-status') return next();
          void vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root" style="height: 900px"></div>
            <script type="module" src="/chat-subagent-status-harness.js"></script></body></html>
          `).then((html) => {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          }, next);
        });
      },
      resolveId(id) {
        return id === '/chat-subagent-status-harness.js'
          ? '\0chat-subagent-status-harness.js'
          : null;
      },
      load(id) {
        return id === '\0chat-subagent-status-harness.js' ? harnessModule : null;
      },
    }],
  });

  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'chat-subagent-status-token');
    localStorage.setItem('ink-language', 'en');
  });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (path === '/api/claude-agent/threads/thread-dream-subagents/messages') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          thread: {
            id: 'thread-dream-subagents',
            title: 'Dream source thread',
            created_at: '2026-08-11T08:08:50Z',
            updated_at: '2026-08-11T08:08:54Z',
          },
          messages: [
            {
              id: 'dream_agent_human',
              role: 'user',
              parts: [{ type: 'text', text: 'Dream workbench prompt visible in Chat' }],
              metadata: {
                kind: 'story-workspace-dream-agent-user',
                story_workspace_run_id: dreamRunId,
              },
              created_at: '2026-08-11T08:08:50Z',
            },
            {
              id: 'dream_agent_9084ec8ce300049ffbeb2d66b2ec484deece91573679613026388c2fbe8c7fcd',
              role: 'user',
              parts: [{
                type: 'text',
                text: '<story_workspace_episode_action_private_v2>PRIVATE ACTION MUST NOT RENDER</story_workspace_episode_action_private_v2>',
              }],
              metadata: {
                kind: 'story-workspace-dream-agent-user',
                story_workspace_episode_action: {
                  schema: 'story-workspace-episode-action/v1',
                  action: 'review_script',
                },
              },
              created_at: '2026-08-11T08:08:51Z',
            },
            {
              id: 'dream-assistant-result',
              role: 'assistant',
              parts: [{ type: 'text', text: 'Dream result remains visible in Chat' }],
              metadata: {},
              created_at: '2026-08-11T08:08:54Z',
            },
            ...(dreamConfirmationPending ? [{
              id: 'dream-assistant-confirmation',
              role: 'assistant',
              parts: [{
                type: 'dynamic-tool',
                toolCallId: 'dream-tool-write',
                toolName: 'Write',
                state: 'input-available',
                input: { file_path: 'story.md' },
                toolMetadata: { approvalRequested: true },
              }],
              metadata: {},
              created_at: '2026-08-11T08:08:55Z',
            }] : []),
          ],
        }),
      });
      return;
    }
    if (path === '/api/claude-agent/threads/thread-dream-subagents/status') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          running: dreamConfirmationPending,
          lifecycle: dreamConfirmationPending ? 'running' : 'idle',
          turn_count: 1,
          pending_tool_call_ids: dreamConfirmationPending ? ['dream-tool-write'] : [],
          tool_confirmation_observation: 'known',
        }),
      });
      return;
    }
    if (path === '/api/claude-agent/threads/thread-dream-subagents/stream') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream; charset=utf-8',
        headers: { 'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no' },
        body: 'data: {"type":"finish","finishReason":"stop"}\n\n',
      });
      return;
    }
    if (path === '/api/claude-agent/tool-confirm') {
      threadConfirmationRequests.push(await request.postDataJSON() as Record<string, unknown>);
      dreamConfirmationPending = false;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, approved: true }),
      });
      return;
    }
    if (path === '/api/claude-agent/threads/thread-dream-subagents/subagents') {
      const tasks = subagentsRunning
        ? [
            ...Array.from({ length: 4 }, (_, index) => subagentTask(index + 1, 'running')),
            ...Array.from({ length: 4 }, (_, index) => subagentTask(index + 1, 'completed')),
          ]
        : Array.from({ length: 8 }, (_, index) => subagentTask(index + 1, 'completed'));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          exists: true,
          tasks,
          counts: subagentsRunning
            ? { running: 4, completed: 4, ended: 0, total: 8 }
            : { running: 0, completed: 8, ended: 0, total: 8 },
          updated_at: '2026-08-11T08:08:55Z',
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
    await page.goto(`http://127.0.0.1:${harnessPort}/chat-subagent-status`);

    const humanDreamMessage = page.getByText('Dream workbench prompt visible in Chat', { exact: true });
    await expect(
      humanDreamMessage,
      `Chat harness failed to restore history. Body: ${await page.locator('body').innerText()}. Diagnostics: ${diagnostics.join(' | ')}`,
    ).toBeVisible();
    await expect(page.getByText('Dream result remains visible in Chat', { exact: true })).toBeVisible();
    await expect(page.getByText('PRIVATE ACTION MUST NOT RENDER', { exact: false })).toHaveCount(0);

    const subagentButton = page.getByRole('button', {
      name: 'Subagent tasks: 4 running · 4 completed',
    });
    await expect(subagentButton).toBeVisible();
    await expect(page.getByRole('button', { name: '4 subagents running' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Stop generating' })).toHaveCount(0);
    const sendButton = page.getByRole('button', { name: 'Send message' });
    await expect(sendButton).toBeVisible();
    await expect(sendButton).toBeDisabled();
    const input = page.getByRole('textbox', { name: 'Chat input' });
    await input.fill('continue in Chat');
    await expect(sendButton).toBeEnabled();

    subagentsRunning = false;
    await subagentButton.click();
    await page.getByRole('button', { name: 'Refresh tasks' }).click();

    dreamConfirmationPending = true;
    await page.reload();
    const confirmationDock = page.getByRole('alertdialog', {
      name: 'Allow I&M to call the Write tool',
    });
    await expect(confirmationDock).toBeVisible();
    await confirmationDock.getByRole('button', { name: 'Approve' }).click();
    await expect(confirmationDock).toHaveCount(0);
    expect(threadConfirmationRequests).toEqual([{
      thread_id: 'thread-dream-subagents',
      tool_call_id: 'dream-tool-write',
      approved: true,
    }]);
    expect(diagnostics).toEqual([]);
  } finally {
    await page.close();
    await server.close();
  }
});
