// [Input] Server-derived Episode workflow action view models rendered in the Dream Agent dialog.
// [Output] Deterministic split, disclosure, keyboard and narrow-layout contracts for the action menu.
// [Pos] Story Workspace Dream Agent workflow action menu Red/Green seam (R3).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses built-ins omitted from browser app types.
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

interface WorkflowActionViewModel {
  readonly id: string;
  readonly label: string;
  readonly displayCommand: string;
  readonly isCurrent: boolean;
  readonly canDispatch: boolean;
  readonly pending: boolean;
  readonly disabledReason: string | null;
}

const actions = Array.from({ length: 4 }, (_, index): WorkflowActionViewModel => ({
  id: `episode-action-${index}`,
  label: ['规划第一集', '创作第一集剧本', '审阅第一集剧本', '完善角色与场景资产'][index] ?? '后续步骤',
  displayCommand: ['/drama-plan', '/drama-script (EP01)', '剧本审查', '/drama-asset'][index] ?? '受控步骤',
  isCurrent: index === 0,
  canDispatch: index === 0,
  pending: false,
  disabledReason: index === 0 ? null : '完成当前步骤后可用',
}));

test.setTimeout(90_000);

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
      const [requests, setRequests] = useState([]);
      const triggerRef = useRef(null);
      window.setWorkflowPending = setPending;
      return h('main', null,
        h('button', { ref: triggerRef, onClick: () => setOpen(true), type: 'button' }, '打开 Dream Agent'),
        h('output', { id: 'requests' }, requests.join(',')),
        open && h(StoryWorkspaceDreamAgentDialog, {
          agent, deckName: 'drama-forge', runId: snapshot.storyWorkspaceRunId,
          workflowActions: actions.map((action, index) => ({
            ...action,
            pending: index === 0 && pending,
          })),
          onRequestWorkflowAction: (id) => setRequests((current) => [...current, id]),
          onClose: () => setOpen(false), restoreFocusRef: triggerRef,
        }),
      );
    }
    createRoot(document.querySelector('#root')).render(h(Harness));
  `;
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, strictPort: true },
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
      return [0, 1, 2, 4].map((count) => {
        const result = split(items.slice(0, count));
        return [result.direct.length, result.overflow.length];
      });
    }, actions)).toEqual([[0, 0], [1, 0], [2, 0], [2, 2]]);
    const dialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await expect(dialog).toBeVisible();
    const currentAction = dialog.getByRole('button', { name: /规划第一集.*当前可执行/ });
    const nextAction = dialog.getByRole('button', {
      name: /创作第一集剧本.*后续，完成当前步骤后可用/,
    });
    await expect(currentAction).toBeEnabled();
    await expect(currentAction).toContainText('/drama-plan');
    await expect(nextAction).toBeDisabled();
    await expect(nextAction).toContainText('/drama-script (EP01)');
    await expect(dialog.getByRole('button', { name: /审阅第一集剧本/ })).toHaveCount(0);
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
    await expect(dialog.getByRole('button', { name: /规划第一集.*处理中/ })).toBeDisabled();
    await page.evaluate(() => {
      (window as unknown as { setWorkflowPending: (pending: boolean) => void })
        .setWorkflowPending(false);
    });

    const disclosure = dialog.getByRole('button', { name: '更多工作流操作（2）' });
    await expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    await disclosure.click();
    await expect(disclosure).toHaveAttribute('aria-expanded', 'true');
    await expect(dialog.getByRole('button', { name: /审阅第一集剧本/ })).toBeDisabled();
    await expect(dialog.getByRole('button', { name: /完善角色与场景资产/ })).toBeDisabled();

    await page.keyboard.press('Escape');
    await expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    await expect(disclosure).toBeFocused();
    await expect(dialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole('button', { name: '打开 Dream Agent' })).toBeFocused();

    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth))
      .toBe(true);

    await page.setViewportSize({ width: 1024, height: 800 });
    await page.getByRole('button', { name: '打开 Dream Agent' }).click();
    const desktopDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    const desktopDisclosure = desktopDialog.getByRole('button', { name: '更多工作流操作（2）' });
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
