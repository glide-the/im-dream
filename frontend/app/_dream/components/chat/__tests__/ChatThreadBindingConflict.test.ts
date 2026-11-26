// [Sync] 2026-11-27: 验证竞争拒绝、草稿保留、自动解锁及新输入提交。
// [Sync] 2026-11-26: cover an unreconciled dispatch, rejected draft, and read-only status check.
// [Input] Structured Dream binding-conflict SSE, a persisted user text/file message, and ChatPanel authoritative recovery callback.
// [Output] Browser regression proving safe binding/auto-repair error copy,
//          attachment retention, one-turn submission, and read-only reload recovery.
// [Pos] Mocked-browser acceptance seam for Dream-bound Chat turn failures.
// [Sync] 2026-08-31: initial binding-conflict interaction coverage.
// [Sync] 2026-09-01: show the allowlisted final Dream auto-repair reason instead
//                    of the generic message card.
// [Sync] 2026-09-04: prove a committed assistant remains processed when its
//                    post-turn Dream synchronization reports a typed failure.
// [Sync] 2026-09-06: isolate Vite optimization cache and await finite SSE POSTs before reloads.
// [Sync] 2026-09-17: cover safe actionable feedback for a typed Gateway allowance rejection.

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

test.use({ channel: 'chromium', viewport: { width: 390, height: 844 } });

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

test('binding conflict keeps the submitted text and attachment while reload stays read-only', async ({ page }) => {
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import '/app/_dream/i18n.ts';
    import ChatPanel from '/app/_dream/components/chat/ChatPanel.tsx';
    import '/app/_dream/styles/tokens.css';
    import '/app/_dream/styles/markdown.css';

    const reconciliation = new URLSearchParams(window.location.search).has('reconciliation');
    const savedInput = { id: 'saved-input', role: 'user', parts: [{ type: 'text', text: 'Earlier message' }] };
    const persistedMessages = [{
      id: 'message-conflict-persisted',
      role: 'user',
      parts: [
        {
          type: 'file',
          url: '/api/storage/file?key=thread-binding/person-relations.txt',
          mediaType: 'text/plain',
          filename: '人物关系分析.txt',
        },
        { type: 'text', text: '请根据附件重新梳理人物关系。' },
      ],
    }];
    window.__bindingReloadCount = 0;
    const recovery = () => {
      window.__bindingReloadCount += 1;
      return {
        messages: reconciliation ? [savedInput] : [
          ...persistedMessages,
          {
            id: 'message-sync-assistant-persisted',
            role: 'assistant',
            parts: [{ type: 'text', text: '角色卡已写入 canonical workspace。' }],
            metadata: {
              turnId: 'turn-sync-failed-after-commit',
              turnStatus: 'completed',
              finalPartIndex: 0,
            },
          },
        ],
        settledToolCallIds: new Set(),
        runtimePendingToolCallIds: new Set(),
        running: false,
      };
    };

    createRoot(document.querySelector('#root')).render(
      React.createElement(ChatPanel, {
        threadId: 'thread-binding-conflict',
        initialMessages: reconciliation ? [savedInput] : [],
        queuedPrompt: '请根据附件重新梳理人物关系。',
        queuedAttachments: [{
          name: '人物关系分析.txt',
          type: 'text/plain',
          size: 24,
          storageKey: 'thread-binding/person-relations.txt',
          workspacePath: 'files/person-relations.txt',
          savedAt: '2026-08-31T04:00:00Z',
        }],
        queuedToolChoice: 'auto',
        queuedPromptNonce: reconciliation ? undefined : 1,
        claimQueuedPrompt: () => true,
        onReconnectComplete: recovery,
        inputPlaceholder: 'Ask Ink & Memory…',
      }),
    );
  `;
  const harnessPort = await reserveEphemeralPort();
  const cacheDir = await mkdtemp(join(tmpdir(), 'ink-dream-binding-vite-'));
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    cacheDir,
    configFile: false,
    logLevel: 'silent',
    optimizeDeps: {
      entries: ['app/_dream/components/chat/ChatPanel.tsx', 'app/_dream/i18n.ts'],
      include: ['react', 'react-dom/client', 'react/jsx-runtime'],
    },
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'chat-thread-binding-conflict-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl?.split('?')[0] !== '/chat-thread-binding-conflict') return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><head><link rel="icon" href="data:,"></head>
              <body><div id="root" style="height: 844px"></div>
              <script type="module" src="/chat-thread-binding-conflict-harness.js"></script></body></html>
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
        return id === '/chat-thread-binding-conflict-harness.js'
          ? '\0chat-thread-binding-conflict-harness.js'
          : null;
      },
      load(id) {
        return id === '\0chat-thread-binding-conflict-harness.js' ? harnessModule : null;
      },
    }],
  }).catch(async (error) => {
    await rm(cacheDir, { recursive: true, force: true });
    throw error;
  });

  let agentPostCount = 0;
  let agentPostFinishedCount = 0;
  let errorMode: 'binding' | 'auto-repair' | 'sync' | 'allowance' | 'reconciliation' = 'binding';
  let queueStatus: 'dispatching' | 'failed' | null = null;
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    const failure = request.failure()?.errorText ?? 'failed';
    const path = new URL(request.url()).pathname;
    // Refresh and navigation may cancel the previous read. Never suppress a send failure.
    if (request.method() === 'GET' && failure === 'net::ERR_ABORTED'
      && /^\/api\/claude-agent\/threads\/thread-binding-conflict\/(turn-navigation|inputs|task-links|scheduled-tasks|subagents)$/.test(path)) return;
    diagnostics.push(`${failure} ${request.url()}`);
  });
  page.on('requestfinished', (request) => {
    const url = new URL(request.url());
    if (request.method() === 'POST' && url.pathname === '/api/claude-agent') {
      agentPostFinishedCount += 1;
    }
  });
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'binding-conflict-test-token');
    localStorage.setItem('ink-language', 'zh');
  });
  await page.route('**/*', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (path === '/api/claude-agent' && request.method() === 'POST') {
      agentPostCount += 1;
      if (errorMode === 'reconciliation') {
        if (!queueStatus) queueStatus = 'dispatching';
        if (queueStatus === 'failed') {
          await route.fulfill({ status: 200, contentType: 'text/event-stream', body: 'data: {"type":"finish","finishReason":"stop"}\n\n' });
          return;
        }
        await route.fulfill({ status: 409, json: { detail: { error_code: 'CHAT_CONTINUATION_BUSY' } } });
        return;
      }
      const event = errorMode === 'binding'
        ? {
            type: 'error',
            errorText: 'Dream binding unavailable.',
            errorCode: 'DREAM_THREAD_BINDING_CONFLICT',
            retryable: false,
          }
        : errorMode === 'auto-repair' ? {
            type: 'error',
            errorText: '最终错误：DREAM_CANONICAL_PROJECT_AMBIGUOUS；workspace 仍存在多个 canonical 项目目录。已停止自动修正，不会发起第三轮。',
            errorCode: 'DREAM_WORKBENCH_AUTO_REPAIR_FAILED',
            retryable: false,
          }
        : errorMode === 'sync' ? {
            type: 'error',
            errorText: 'Agent 回复已保存，但 Dream 工作区同步未完成。请重新加载对话核对工作台状态，无需重发消息。',
            errorCode: 'DREAM_ARTIFACT_SYNC_FAILED_AFTER_COMMIT',
            retryable: false,
          }
        : {
            type: 'error',
            errorText: 'The current subscription-period Token allowance is insufficient.',
            errorCode: 'GATEWAY_TOKEN_ALLOWANCE_EXHAUSTED',
            retryable: false,
          };
      const assistantFrames = errorMode === 'sync' ? [
        'data: {"type":"message-metadata","sessionId":"session-sync","turnId":"turn-sync-failed-after-commit"}',
        'data: {"type":"text-start","id":"sync-answer"}',
        'data: {"type":"text-delta","id":"sync-answer","delta":"角色卡已写入 canonical workspace。"}',
        'data: {"type":"text-end","id":"sync-answer"}',
      ] : [];
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream; charset=utf-8',
        body: [
          ...assistantFrames,
          `data: ${JSON.stringify(event)}`,
          'data: {"type":"finish","finishReason":"error"}',
          '',
        ].join('\n\n'),
      });
      return;
    }
    if (path === '/api/system-config') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"data":{"workspace_enabled":true}}' });
      return;
    }
    if (path === '/api/gateway/models') {
      await route.fulfill({ json: { data: [], defaultModelAlias: null } });
      return;
    }
    if (path.endsWith('/subagents')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"tasks":[]}' });
      return;
    }
    if (path.endsWith('/inputs') && errorMode === 'reconciliation') {
      await route.fulfill({ json: {
        local_owner: false,
        entries: queueStatus ? [{
          message_id: 'saved-input', thread_id: 'thread-binding-conflict', queue_sequence: '1',
          status: queueStatus, revision: queueStatus === 'dispatching' ? 3 : 4,
          dispatch_turn_id: 'saved-turn', created_at: '2026-11-26T09:09:00Z', text: 'Earlier message',
        }] : [],
      } });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  try {
    await server.listen();
    await page.goto(`http://127.0.0.1:${harnessPort}/chat-thread-binding-conflict`);

    await expect.poll(() => agentPostCount, { timeout: 20_000 }).toBe(1);
    const alert = page.locator('[data-chat-turn-error]');
    await expect(alert).toContainText('当前对话暂时无法继续创作');
    await expect(alert).toContainText('本次 Agent 未开始处理');
    await expect(page.getByText('请根据附件重新梳理人物关系。')).toBeVisible();
    await expect(page.getByText('人物关系分析.txt')).toBeVisible();
    await expect(page.getByText(/DREAM_THREAD_BINDING_CONFLICT/)).toHaveCount(0);
    await expect(page.getByText(/^Error:/)).toHaveCount(0);
    expect(agentPostCount).toBe(1);

    const reloadCountBefore = await page.evaluate(() => (
      (window as Window & { __bindingReloadCount?: number }).__bindingReloadCount ?? 0
    ));
    await page.getByRole('button', { name: '重新加载对话' }).click();
    await expect(alert).toHaveCount(0);
    await expect(page.getByText('请根据附件重新梳理人物关系。')).toBeVisible();
    await expect(page.getByText('人物关系分析.txt')).toBeVisible();
    const reloadCountAfter = await page.evaluate(() => (
      (window as Window & { __bindingReloadCount?: number }).__bindingReloadCount ?? 0
    ));
    expect(reloadCountAfter).toBe(reloadCountBefore + 1);
    expect(agentPostCount).toBe(1);
    expect(diagnostics).toEqual([]);

    const bodyMetrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(bodyMetrics.scrollWidth).toBeLessThanOrEqual(bodyMetrics.clientWidth);

    await expect.poll(() => agentPostFinishedCount).toBe(1);
    errorMode = 'auto-repair';
    await page.reload();
    await expect.poll(() => agentPostCount).toBe(2);
    const repairAlert = alert;
    await expect(repairAlert).toHaveAttribute(
      'data-chat-turn-error',
      'dream-auto-repair-failed',
    );
    await expect(repairAlert).toContainText('工作台自动修正已停止');
    await expect(repairAlert).toContainText(
      'DREAM_CANONICAL_PROJECT_AMBIGUOUS',
    );
    await expect(repairAlert).toContainText('不会发起第三轮');
    await expect(repairAlert).not.toContainText('消息处理未完成');

    await expect.poll(() => agentPostFinishedCount).toBe(2);
    errorMode = 'sync';
    await page.reload();
    await expect.poll(() => agentPostCount).toBe(3);
    const syncAlert = alert;
    await expect(syncAlert).toHaveAttribute(
      'data-chat-turn-error',
      'dream-artifact-sync-failed',
    );
    await expect(syncAlert).toContainText('回复已保存，工作台同步未完成');
    await expect(syncAlert).toContainText('重新加载对话');
    await expect(syncAlert).not.toContainText('消息处理未完成');
    await expect(page.getByText('角色卡已写入 canonical workspace。')).toBeVisible();

    await expect.poll(() => agentPostFinishedCount).toBe(3);
    await page.getByRole('button', { name: '重新加载对话' }).click();
    await expect(syncAlert).toHaveCount(0);
    await expect(page.getByText('角色卡已写入 canonical workspace。')).toBeVisible();
    expect(agentPostCount).toBe(3);
    expect(diagnostics).toEqual([]);

    errorMode = 'allowance';
    await page.reload();
    await expect.poll(() => agentPostCount).toBe(4);
    const allowanceAlert = alert;
    await expect(allowanceAlert).toHaveAttribute(
      'data-chat-turn-error',
      'gateway-token-allowance-exhausted',
    );
    await expect(allowanceAlert).toContainText('当前订阅周期 Token 不足');
    await expect(allowanceAlert).toContainText('你的消息已经保存');
    await expect(allowanceAlert).toContainText('模型未能完成回复');
    await expect(allowanceAlert).not.toContainText('SUBSCRIPTION_TOKEN_ALLOWANCE_EXHAUSTED');
    await expect(allowanceAlert).not.toContainText('provider_detail');

    await expect.poll(() => agentPostFinishedCount).toBe(4);
    expect(diagnostics).toEqual([]);

    errorMode = 'reconciliation';
    await page.goto(`http://127.0.0.1:${harnessPort}/chat-thread-binding-conflict?reconciliation`);
    const editor = page.getByRole('textbox', { name: '聊天输入' });
    const send = page.getByRole('button', { name: '发送消息' });
    const busy = page.getByText('此对话正在其他端处理，输入已保留，请稍后继续。');
    await editor.fill('Keep this draft');
    await send.click();
    await expect(busy).toBeVisible();
    await expect(editor).toHaveText('Keep this draft');
    await expect(send).toBeDisabled();
    await expect(page.locator('[data-chat-message-id]')).toHaveCount(1);
    await editor.fill('Continue here after interruption');
    await editor.press('Enter');
    expect(agentPostCount).toBe(5);
    queueStatus = 'failed';
    await expect(send).toBeEnabled();
    await expect(busy).toHaveCount(0);
    await expect(editor).toContainText('Continue here after interruption');
    expect(agentPostCount).toBe(5);
    await send.click();
    await expect.poll(() => agentPostCount).toBe(6);
    expect(diagnostics.filter((message) => !message.startsWith(
      'Failed to load resource: the server responded with a status of 409',
    ))).toEqual([]);
  } finally {
    await server.close();
    await rm(cacheDir, { recursive: true, force: true });
  }
});
