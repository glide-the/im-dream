// [Input] Shared AskUserQuestion dock with multiSelect questions inside a Dream-sized constrained panel.
// [Output] Checkbox/string[] confirmation contract plus always-visible submit/cancel actions in constrained height.
// [Pos] AskUserQuestion multi-select regression and browser contract seam.
// [Sync] 2026-08-13: constrain the browser harness to a short Dream rail and assert
//                    that long question content cannot push the action buttons below it.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node harness intentionally imports Node APIs.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node harness intentionally imports Node APIs.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';
import {
  normalizeMultiSelectAnswer,
  questionAnswerIsPresent,
  questionOptionValue,
} from '../askUserQuestionAnswers';

test.use({ channel: 'chromium' });

async function reserveEphemeralPort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createNetServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (address === null || typeof address === 'string') {
        probe.close();
        reject(new Error('Could not reserve an AskUserQuestion test port.'));
        return;
      }
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
}

test('multi-select helpers preserve object values and enforce a non-empty required answer', () => {
  expect(questionOptionValue({ label: '温柔叙事', value: 'gentle' })).toBe('gentle');
  expect(questionOptionValue({ label: '仅标签' })).toBe('仅标签');
  expect(normalizeMultiSelectAnswer(['gentle', '', 3, 'mystery'])).toEqual(['gentle', 'mystery']);
  expect(normalizeMultiSelectAnswer('gentle')).toEqual(['gentle']);
  expect(questionAnswerIsPresent([], true)).toBe(false);
  expect(questionAnswerIsPresent(['gentle'], true)).toBe(true);
});

test('required multiSelect renders checkboxes and submits string[] under the Chinese question key', async ({ page }) => {
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import '/src/styles/tokens.css';
    import ToolConfirmationDock from '/src/components/chat/ToolConfirmationDock.tsx';

    const confirmation = {
      kind: 'askuser',
      partKey: 'ask-part',
      toolCallId: 'ask-multi-select',
      toolName: 'AskUserQuestion',
      input: {
        questions: [{
          id: 'story-directions',
          question: '请选择叙事方向',
          required: true,
          multiSelect: true,
          options: [
            { label: '温柔叙事', value: 'gentle', description: '克制而温暖' },
            { label: '悬疑推进', value: 'mystery' },
            '开放结局',
            '双时空叙事',
            '不可靠叙述者',
            '群像视角',
            '现实锚点',
            '留白收束',
          ],
        }],
      },
    };
    createRoot(document.querySelector('#root')).render(
      React.createElement('div', {
        id: 'dream-panel-fixture',
        style: {
          display: 'flex',
          flexDirection: 'column',
          width: '360px',
          height: '220px',
          minHeight: 0,
          overflow: 'hidden',
        },
      }, React.createElement(ToolConfirmationDock, {
        confirmation,
        threadId: 'thread-shared-ask-user',
        onSettled: (toolCallId) => {
          document.querySelector('#settled').textContent = toolCallId;
        },
      })),
    );
  `;
  const port = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'ask-user-multi-select-harness',
      configureServer(vite) {
        vite.middlewares.use((request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url ?? '';
          if (requestUrl !== '/ask-user-multi-select') return next();
          void vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root"></div><output id="settled"></output>
            <script type="module" src="/ask-user-multi-select.js"></script></body></html>
          `).then((html) => {
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          }, next);
        });
      },
      resolveId(id) {
        return id === '/ask-user-multi-select.js' ? '\0ask-user-multi-select.js' : null;
      },
      load(id) {
        return id === '\0ask-user-multi-select.js' ? harnessModule : null;
      },
    }],
  });

  const requests: Array<Record<string, unknown>> = [];
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'ask-user-token');
    localStorage.setItem('ink-language', 'zh');
  });
  await page.route('**/api/claude-agent/tool-confirm', async (route) => {
    requests.push(await route.request().postDataJSON() as Record<string, unknown>);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, approved: true }),
    });
  });

  await server.listen();
  try {
    await page.goto(`http://127.0.0.1:${port}/ask-user-multi-select`);
    const submit = page.getByRole('button', { name: '提交' });
    const cancel = page.getByRole('button', { name: '取消' });
    const gentle = page.getByRole('checkbox', { name: /温柔叙事/ });
    const mystery = page.getByRole('checkbox', { name: /悬疑推进/ });

    await expect(page.getByText('请选择叙事方向')).toBeVisible();
    await expect(submit).toBeInViewport();
    await expect(cancel).toBeInViewport();
    const panelBox = await page.locator('#dream-panel-fixture').boundingBox();
    const submitBox = await submit.boundingBox();
    const cancelBox = await cancel.boundingBox();
    expect(panelBox).not.toBeNull();
    expect(submitBox).not.toBeNull();
    expect(cancelBox).not.toBeNull();
    expect(submitBox!.y + submitBox!.height).toBeLessThanOrEqual(panelBox!.y + panelBox!.height);
    expect(cancelBox!.y + cancelBox!.height).toBeLessThanOrEqual(panelBox!.y + panelBox!.height);
    await expect(submit).toBeDisabled();
    await page.keyboard.press('Control+Enter');
    expect(requests).toEqual([]);

    await gentle.check();
    await expect(gentle).toHaveValue('gentle');
    await expect(submit).toBeEnabled();
    await gentle.uncheck();
    await expect(submit).toBeDisabled();

    await gentle.check();
    await mystery.check();
    await submit.click();
    await expect(page.locator('#settled')).toHaveText('ask-multi-select');
    expect(requests).toEqual([{
      thread_id: 'thread-shared-ask-user',
      tool_call_id: 'ask-multi-select',
      approved: true,
      answers: { '请选择叙事方向': ['gentle', 'mystery'] },
    }]);
    expect(diagnostics).toEqual([]);

  } finally {
    await server.close();
  }
});
