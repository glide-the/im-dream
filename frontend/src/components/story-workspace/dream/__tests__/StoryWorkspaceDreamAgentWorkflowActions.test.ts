// [Input] Server-derived Episode workflow action view models rendered in the Dream Agent dialog.
// [Output] Deterministic split, disclosure, keyboard and narrow-layout contracts for the action menu.
// [Pos] Story Workspace Dream Agent workflow action menu Red/Green seam (R3).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses built-ins omitted from browser app types.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright Node seam uses built-ins omitted from browser app types.
import { createServer as createTcpServer } from 'node:net';
import { createServer } from 'vite';

interface WorkflowActionViewModel {
  readonly id: string;
  readonly label: string;
  readonly displayCommand: string;
  readonly isCurrent: boolean;
  readonly canDispatch: boolean;
  readonly pending: boolean;
  readonly disabledReason: string | null;
  readonly availability: 'executable' | 'preview' | 'blocked';
  readonly description: string;
  readonly targetEpisodeLabel: string;
}

const actions = Array.from({ length: 7 }, (_, index): WorkflowActionViewModel => ({
  id: `episode-action-${index}`,
  label: [
    '生成 EP01 Prompt 包',
    '基于最新剧本更新 EP01 详细分镜',
    '审阅 EP01 完整产物',
    '校验并提交 EP01',
    '准备 EP01 渲染与配音指引',
    '开始 EP02 分集规划',
    '创作 EP02 剧本',
  ][index] ?? '后续步骤',
  displayCommand: [
    '/drama-prompt (EP01)',
    '/drama-storyboard (EP01)',
    'script-reviewer · EP01 完整链路',
    '校验并提交 · EP01',
    '/drama-render + /drama-voice · EP01',
    '/drama-plan',
    '/drama-script (EP02)',
  ][index] ?? '受控步骤',
  isCurrent: index === 0,
  canDispatch: index <= 1 || index === 4,
  pending: false,
  disabledReason: index <= 1 || index === 4 ? null : '完成当前步骤后可用',
  availability: index <= 1 || index === 4
    ? 'executable'
    : index === 5 ? 'blocked' : 'preview',
  description: `动作说明 ${index + 1}`,
  targetEpisodeLabel: index < 5 ? 'EP01' : 'EP02',
}));

test.setTimeout(90_000);

async function reserveEphemeralPort(): Promise<number> {
  const tcpServer = createTcpServer();
  await new Promise<void>((resolve, reject) => {
    tcpServer.once('error', reject);
    tcpServer.listen(0, '127.0.0.1', resolve);
  });
  const address = tcpServer.address();
  if (address === null || typeof address === 'string') {
    tcpServer.close();
    throw new Error('Could not reserve an ephemeral workflow action test port.');
  }
  await new Promise<void>((resolve, reject) => {
    tcpServer.close((error: unknown) => (error ? reject(error) : resolve()));
  });
  return address.port;
}

test('narrow dialog exposes only server actions, traps disclosure focus and has no overflow', async ({ page }) => {
  const diagnostics: string[] = [];
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  const harnessModule = `
    import React, { createElement as h, useRef, useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import {
      StoryWorkspaceDreamAgentDialog,
      storyWorkspaceSplitDreamAgentWorkflowActions,
    } from '/src/components/story-workspace/dream/StoryWorkspaceDreamAgentDialog.tsx';
    import '/src/pages/story-workspace/StoryWorkspaceDreamPage.css';
    const actions = ${JSON.stringify(actions)};
    const snapshot = {
      storyWorkspaceRunId: 'run_${'a'.repeat(32)}', lifecycle: 'idle', activeTurnId: null,
      canSend: true, sendBlockReason: null, messages: [], snapshotAt: '2026-08-06T00:00:00Z',
    };
    const agent = {
      snapshot, streamText: '', streamContent: [], streamTurnId: null,
      pendingToolConfirmation: null, isLoading: false, isSending: false,
      isConfirmingTool: false, isReconnecting: false, error: null, unreadCount: 0,
      refresh: () => undefined, markRead: () => undefined,
      send: async () => false, confirmTool: async () => false,
    };
    window.splitActions = storyWorkspaceSplitDreamAgentWorkflowActions;
    function Harness() {
      const [open, setOpen] = useState(true);
      const [pending, setPending] = useState(false);
      const [initialWorkflowFocus, setInitialWorkflowFocus] = useState(null);
      const [requests, setRequests] = useState([]);
      const triggerRef = useRef(null);
      window.setWorkflowPending = setPending;
      window.reopenWorkflowFocus = (actionId, wasOverflow) => {
        setInitialWorkflowFocus({ actionId, wasOverflow });
        setOpen(true);
      };
      return h('main', null,
        h('button', {
          ref: triggerRef,
          onClick: () => {
            setInitialWorkflowFocus(null);
            setOpen(true);
          },
          type: 'button',
        }, '打开 Dream Agent'),
        h('output', { id: 'requests' }, requests.join(',')),
        open && h(StoryWorkspaceDreamAgentDialog, {
          agent, deckName: 'drama-forge', runId: snapshot.storyWorkspaceRunId,
          workflowActions: actions.map((action, index) => ({
            ...action,
            pending: index === 0 && pending,
          })),
          initialWorkflowFocus,
          onRequestWorkflowAction: (id) => setRequests((current) => [...current, id]),
          onClose: () => setOpen(false), restoreFocusRef: triggerRef,
        }),
      );
    }
    createRoot(document.querySelector('#root')).render(h(Harness));
  `;
  const port = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'r3-agent-workflow-actions-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== '/r3-agent-workflow-actions') return next();
          const html = await vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><body><div id="root"></div>
            <script type="module" src="/r3-agent-workflow-actions.js"></script></body></html>
          `);
          response.statusCode = 200;
          response.setHeader('Content-Type', 'text/html; charset=utf-8');
          response.end(html);
        });
      },
      resolveId(id) {
        return id === '/r3-agent-workflow-actions.js' ? '\0r3-agent-workflow-actions.js' : null;
      },
      load(id) {
        return id === '\0r3-agent-workflow-actions.js' ? harnessModule : null;
      },
    }],
  });
  await server.listen();
  const address = server.httpServer?.address();
  if (address === null || address === undefined || typeof address === 'string') {
    await server.close();
    throw new Error('R3 workflow actions harness did not bind a TCP port.');
  }
  try {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`http://127.0.0.1:${address.port}/r3-agent-workflow-actions`);
    expect(await page.evaluate((items) => {
      const split = (window as unknown as {
        splitActions: (value: readonly WorkflowActionViewModel[]) => {
          direct: readonly WorkflowActionViewModel[];
          overflow: readonly WorkflowActionViewModel[];
        };
      }).splitActions;
      return [0, 1, 2, 7].map((count) => {
        const result = split(items.slice(0, count));
        return [result.direct.length, result.overflow.length];
      });
    }, actions)).toEqual([[0, 0], [1, 0], [2, 0], [2, 5]]);
    const dialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('当前与后续 Episode')).toBeVisible();
    const currentAction = dialog.getByRole('button', { name: /生成 EP01 Prompt 包.*推荐操作.*当前可执行/ });
    const nextAction = dialog.getByRole('button', {
      name: /基于最新剧本更新 EP01 详细分镜.*当前可执行/,
    });
    await expect(currentAction).toBeEnabled();
    await expect(currentAction).toContainText('/drama-prompt (EP01)');
    await expect(nextAction).toBeEnabled();
    await expect(nextAction).toContainText('/drama-storyboard (EP01)');
    await expect(dialog.getByRole('button', { name: /审阅 EP01 完整产物/ })).toHaveCount(0);
    await page.evaluate(() => {
      const disabledDecoy = document.createElement('button');
      disabledDecoy.disabled = true;
      disabledDecoy.tabIndex = 0;
      disabledDecoy.textContent = '禁用焦点诱饵';
      document.querySelector('[role="dialog"]')?.append(disabledDecoy);
    });

    const closeButton = dialog.getByRole('button', { name: '收起 Dream Agent' });
    const composerInput = dialog.getByRole('textbox', { name: '给 Dream Agent 留言' });
    await closeButton.focus();
    await page.keyboard.press('Shift+Tab');
    await expect(composerInput).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(closeButton).toBeFocused();

    await currentAction.click();
    await expect(page.locator('#requests')).toHaveText('episode-action-0');
    await page.evaluate(() => {
      (window as unknown as { setWorkflowPending: (pending: boolean) => void })
        .setWorkflowPending(true);
    });
    await expect(dialog.getByRole('button', { name: /生成 EP01 Prompt 包.*处理中/ })).toBeDisabled();
    await page.evaluate(() => {
      (window as unknown as { setWorkflowPending: (pending: boolean) => void })
        .setWorkflowPending(false);
    });

    const disclosure = dialog.getByRole('button', { name: '更多工作流操作（5）' });
    await expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    await disclosure.click();
    await expect(disclosure).toHaveAttribute('aria-expanded', 'true');
    await expect(dialog.getByRole('button', { name: /审阅 EP01 完整产物.*未来可用/ })).toBeDisabled();
    await expect(dialog.getByRole('button', { name: /开始 EP02 分集规划.*暂不可用/ })).toBeDisabled();

    await page.keyboard.press('Escape');
    await expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    await expect(disclosure).toBeFocused();
    await expect(dialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole('button', { name: '打开 Dream Agent' })).toBeFocused();

    await page.evaluate(() => {
      (window as unknown as {
        reopenWorkflowFocus: (actionId: string, wasOverflow: boolean) => void;
      }).reopenWorkflowFocus('episode-action-4', true);
    });
    const restoredDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    const restoredDisclosure = restoredDialog.getByRole('button', {
      name: '更多工作流操作（5）',
    });
    await expect(restoredDisclosure).toHaveAttribute('aria-expanded', 'true');
    await expect(restoredDialog.getByRole('button', {
      name: /准备 EP01 渲染与配音指引.*当前可执行/,
    })).toBeFocused();
    await page.keyboard.press('Escape');
    await page.keyboard.press('Escape');

    await page.evaluate(() => {
      (window as unknown as {
        reopenWorkflowFocus: (actionId: string, wasOverflow: boolean) => void;
      }).reopenWorkflowFocus('episode-action-missing', true);
    });
    const fallbackDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    const fallbackDisclosure = fallbackDialog.getByRole('button', {
      name: '更多工作流操作（5）',
    });
    await expect(fallbackDisclosure).toHaveAttribute('aria-expanded', 'true');
    await expect(fallbackDisclosure).toBeFocused();
    await page.keyboard.press('Escape');
    await page.keyboard.press('Escape');

    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth))
      .toBe(true);

    await page.setViewportSize({ width: 1024, height: 800 });
    await page.getByRole('button', { name: '打开 Dream Agent' }).click();
    const desktopDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    const desktopDisclosure = desktopDialog.getByRole('button', { name: '更多工作流操作（5）' });
    await desktopDisclosure.click();
    await page.keyboard.press('Escape');
    await expect(desktopDisclosure).toHaveAttribute('aria-expanded', 'false');
    await expect(desktopDisclosure).toBeFocused();
    await expect(desktopDialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(desktopDialog).toHaveCount(0);
    await expect(page.getByRole('button', { name: '打开 Dream Agent' })).toBeFocused();
    expect(diagnostics).toEqual([]);
  } finally {
    await server.close();
  }
});
