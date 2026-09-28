// [Input] Real Chromium input against the production AIInputDock module with mocked Skill catalog and system-config APIs.
// [Output] Regression coverage for the user-visible slash shortcut menu: draft trigger, listbox rendering, keyboard selection, dismissal, and silent catalog-failure degrade.
// [Pos] AIInputDock slash menu regression contract in frontend/app/_dream/components/chat/__tests__.
// [Sync] 2026-09-18: cover Enter send, Shift+Enter newline, IME composition, disabled/loading states, and mobile send visibility.
// [Sync] 2026-09-26: verify the real composer accepts input beside Stop and restores a rejected queued draft in local Chrome.
// [Sync] 2026-09-27: assert the single trailing action switches between Stop and Send with draft state and stays within narrow columns.

import { expect, test, type Page } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer, type ViteDevServer } from 'vite';

test.use({ channel: 'chrome' });

const HARNESS_PATH = '/ai-input-dock-slash-menu';

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
      const { port } = address;
      probe.close((error?: Error) => {
        if (error) reject(error);
        else resolve(port);
      });
    });
  });
}

function harnessModule(sentLogKey: string): string {
  return `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import i18n from '/app/_dream/i18n.ts';
    import AIInputDock from '/app/_dream/components/chat/AIInputDock.tsx';
    import '/app/_dream/styles/tokens.css';
    import '/app/_dream/index.css';

    window.${sentLogKey} = [];
    void i18n.changeLanguage('en');

    function Harness() {
      const [sentCount, setSentCount] = useState(0);
      const [disabled, setDisabled] = useState(false);
      const [loading, setLoading] = useState(false);
      const [activeTurn, setActiveTurn] = useState(false);
      const [rejectSend, setRejectSend] = useState(false);
      return React.createElement(
        'main',
        { style: { width: '100%', maxWidth: '52rem', margin: '0 auto' } },
        React.createElement(AIInputDock, {
          disabled,
          loading,
          onStop: activeTurn ? () => {} : undefined,
          mode: 'full',
          onSendMessage: (message) => {
            if (rejectSend) return Promise.reject(new Error('queue rejected'));
            window.${sentLogKey}.push(message);
            setSentCount((current) => current + 1);
          },
          placeholder: 'Ask Ink & Memory…',
        }),
        React.createElement('output', { 'data-testid': 'sent-count' }, String(sentCount)),
        React.createElement('button', { 'data-testid': 'toggle-disabled', onClick: () => setDisabled((value) => !value) }, 'Toggle disabled'),
        React.createElement('button', { 'data-testid': 'toggle-loading', onClick: () => setLoading((value) => !value) }, 'Toggle loading'),
        React.createElement('button', { 'data-testid': 'toggle-active-turn', onClick: () => setActiveTurn((value) => !value) }, 'Toggle active turn'),
        React.createElement('button', { 'data-testid': 'toggle-reject-send', onClick: () => setRejectSend((value) => !value) }, 'Toggle rejection'),
      );
    }

    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
}

async function startHarness(page: Page, options: {
  readonly catalogStatus: number;
  readonly sentLogKey: string;
}): Promise<ViteDevServer> {
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'ai-input-dock-slash-menu-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== HARNESS_PATH) return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><head><link rel="icon" href="data:,"></head>
              <body><div id="root"></div><script type="module" src="/ai-input-dock-slash-menu-harness.js"></script></body></html>
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
        return id === '/ai-input-dock-slash-menu-harness.js'
          ? '\0ai-input-dock-slash-menu-harness.js'
          : null;
      },
      load(id) {
        return id === '\0ai-input-dock-slash-menu-harness.js'
          ? harnessModule(options.sentLogKey)
          : null;
      },
    }],
  });

  await page.route('**/api/system-config', async (route) => {
    await route.fulfill({ json: { data: { im_full_access_enabled: false, workspace_enabled: true } } });
  });
  await page.route('**/api/claude-agent/skill-commands', async (route) => {
    if (options.catalogStatus !== 200) {
      await route.fulfill({
        status: options.catalogStatus,
        json: { detail: { error_code: 'COMMON_SKILL_CATALOG_UNAVAILABLE' } },
      });
      return;
    }
    await route.fulfill({
      json: {
        commands: [
          { command: '/plot-twist', name: 'plot-twist' },
          { command: '/scene-beat', name: 'scene-beat' },
        ],
      },
    });
  });

  await server.listen();
  const address = server.httpServer?.address();
  if (address === null || address === undefined || typeof address === 'string') {
    await server.close();
    throw new Error('AIInputDock slash menu harness did not bind a TCP port.');
  }
  await page.goto(`http://127.0.0.1:${address.port}${HARNESS_PATH}`);
  return server;
}

test('suggests installed Skills for a standalone slash draft and inserts the selection', async ({ page }) => {
  const sentLogKey = 'slashMenuSentMessages';
  const server = await startHarness(page, { catalogStatus: 200, sentLogKey });
  try {
    const editor = page.locator('#chat-input');
    await expect(editor).toBeVisible();
    await editor.click();

    await editor.fill('/');
    const listbox = page.getByRole('listbox', { name: '已安装的 Skill 指令' });
    await expect(listbox).toBeVisible();
    await expect(listbox.getByRole('option', { name: '/plot-twist' })).toBeVisible();
    await expect(listbox.getByRole('option', { name: '/scene-beat' })).toBeVisible();

    await editor.press('Enter');
    await expect(listbox).toBeHidden();
    await expect(editor).toContainText('/plot-twist');

    // The selected command is sent as ordinary Chat text through the production path.
    await editor.press('Enter');
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    const sentMessages = await page.evaluate(
      (key) => (window as unknown as Record<string, string[]>)[key] ?? [],
      sentLogKey,
    );
    expect(sentMessages).toEqual(['/plot-twist']);
  } finally {
    await server.close();
  }
});

test('accepts a second draft during an active turn and restores it when queue submission fails', async ({ page }, testInfo) => {
  const server = await startHarness(page, { catalogStatus: 503, sentLogKey: 'runningQueueSentMessages' });
  try {
    const editor = page.locator('#chat-input');
    await page.getByTestId('toggle-active-turn').click();
    await page.getByTestId('toggle-loading').click();
    const send = page.getByRole('button', { name: 'Send message' });
    const stop = page.getByRole('button', { name: 'Stop generating' });
    await expect(stop).toBeVisible();
    await expect(send).toHaveCount(0);
    await expect(page.locator('.ai-input-dock__trailing-actions button')).toHaveCount(1);
    await editor.fill('queued while running');
    await expect(send).toBeEnabled();
    await expect(stop).toHaveCount(0);
    for (const width of [2598, 390]) {
      await page.setViewportSize({ width, height: 900 });
      const dock = await page.locator('.ai-input-dock').boundingBox();
      const sendBox = await send.boundingBox();
      expect(dock).not.toBeNull();
      expect(sendBox).not.toBeNull();
      expect(sendBox!.width).toBeGreaterThanOrEqual(44);
      expect(sendBox!.x + sendBox!.width).toBeLessThanOrEqual(dock!.x + dock!.width - 8);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await page.locator('.ai-input-dock').screenshot({ path: testInfo.outputPath(`active-turn-send-${width}.png`) });
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.locator('main').evaluate((node) => { node.style.maxWidth = '360px'; });
    const narrowDock = await page.locator('.ai-input-dock').boundingBox();
    const narrowSend = await send.boundingBox();
    expect(narrowDock).not.toBeNull();
    expect(narrowSend).not.toBeNull();
    expect(narrowSend!.x + narrowSend!.width).toBeLessThanOrEqual(narrowDock!.x + narrowDock!.width - 8);
    await send.click();
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    await expect(editor).toBeEmpty();
    await expect(stop).toBeVisible();
    await expect(send).toHaveCount(0);
    const narrowStop = await stop.boundingBox();
    expect(narrowStop).not.toBeNull();
    expect(narrowStop!.x + narrowStop!.width).toBeLessThanOrEqual(narrowDock!.x + narrowDock!.width - 8);
    await page.locator('.ai-input-dock').screenshot({ path: testInfo.outputPath('active-turn-stop-narrow.png') });

    await page.getByTestId('toggle-reject-send').click();
    await editor.fill('keep my queued draft');
    await expect(stop).toHaveCount(0);
    await send.click();
    await expect(editor).toHaveText('keep my queued draft');
    await expect(send).toBeVisible();
    await expect(page.locator('.ai-input-dock__trailing-actions button')).toHaveCount(1);
    await expect(page.getByTestId('sent-count')).toHaveText('1');
  } finally {
    await server.close();
  }
});

test('dismisses the slash menu with Escape and restores it when the draft changes', async ({ page }) => {
  const server = await startHarness(page, { catalogStatus: 200, sentLogKey: 'slashMenuDismissSentMessages' });
  try {
    const editor = page.locator('#chat-input');
    await expect(editor).toBeVisible();
    await editor.click();

    await editor.fill('/');
    const listbox = page.getByRole('listbox', { name: '已安装的 Skill 指令' });
    await expect(listbox).toBeVisible();

    await editor.press('Escape');
    await expect(listbox).toBeHidden();

    await editor.fill('/sc');
    await expect(listbox).toBeVisible();
    await expect(listbox.getByRole('option', { name: '/scene-beat' })).toBeVisible();
    await expect(listbox.getByRole('option', { name: '/plot-twist' })).toHaveCount(0);
  } finally {
    await server.close();
  }
});

test('keeps the composer usable without a menu when the Skill catalog fails', async ({ page }) => {
  const server = await startHarness(page, { catalogStatus: 503, sentLogKey: 'slashMenuFailureSentMessages' });
  try {
    const editor = page.locator('#chat-input');
    await expect(editor).toBeVisible();
    await editor.click();

    await editor.fill('/');
    await expect(page.getByRole('listbox')).toHaveCount(0);
    await expect(editor).toContainText('/');
    await expect(page.getByTestId('sent-count')).toHaveText('0');
  } finally {
    await server.close();
  }
});

test('uses Enter to send without breaking newline, IME, empty, loading, disabled, or mobile button rules', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const sentLogKey = 'keyboardPolicySentMessages';
  const server = await startHarness(page, { catalogStatus: 503, sentLogKey });
  try {
    const editor = page.locator('#chat-input');
    const sendButton = page.locator('.ai-input-dock__send-button');
    await expect(editor).toBeVisible();
    await expect(sendButton).toBeVisible();
    await expect(sendButton).toHaveAccessibleName('Send message');
    await expect(sendButton).toBeDisabled();
    await page.screenshot({
      path: fileURLToPath(new URL('../../../../../test-results/mobile-chat-390x844.png', import.meta.url)),
      fullPage: true,
    });

    await editor.press('Enter');
    await expect(page.getByTestId('sent-count')).toHaveText('0');

    await editor.fill('first line');
    await editor.press('Shift+Enter');
    await editor.pressSequentially('second line');
    await expect(page.getByTestId('sent-count')).toHaveText('0');
    expect(await editor.innerText()).toContain('first line\nsecond line');

    await editor.dispatchEvent('compositionstart', { data: '拼音' });
    await editor.dispatchEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      isComposing: true,
      bubbles: true,
      cancelable: true,
    });
    await expect(page.getByTestId('sent-count')).toHaveText('0');
    await editor.dispatchEvent('compositionend', { data: '拼音' });

    await page.getByTestId('toggle-loading').click();
    await expect(sendButton).toBeDisabled();
    await editor.press('Enter');
    await expect(page.getByTestId('sent-count')).toHaveText('0');
    await page.getByTestId('toggle-loading').click();

    await page.getByTestId('toggle-disabled').click();
    await expect(editor).toHaveAttribute('aria-disabled', 'true');
    await expect(sendButton).toBeDisabled();
    await page.getByTestId('toggle-disabled').click();

    await editor.press('Enter');
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    const sentMessages = await page.evaluate(
      (key) => (window as unknown as Record<string, string[]>)[key] ?? [],
      sentLogKey,
    );
    expect(sentMessages).toEqual(['first line  \nsecond line']);

    const viewportMetrics = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
    }));
    expect(viewportMetrics.documentWidth).toBeLessThanOrEqual(viewportMetrics.viewportWidth);
    const sendBox = await sendButton.boundingBox();
    expect(sendBox).not.toBeNull();
    expect(sendBox!.x + sendBox!.width).toBeLessThanOrEqual(390);
    expect(sendBox!.width).toBeGreaterThanOrEqual(44);
    expect(sendBox!.height).toBeGreaterThanOrEqual(44);

    await page.setViewportSize({ width: 430, height: 932 });
    await expect(sendButton).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(430);
    await page.screenshot({
      path: fileURLToPath(new URL('../../../../../test-results/mobile-chat-430x932.png', import.meta.url)),
      fullPage: true,
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await expect(sendButton).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1440);
    await page.screenshot({
      path: fileURLToPath(new URL('../../../../../test-results/mobile-chat-desktop-1440x900.png', import.meta.url)),
      fullPage: true,
    });
  } finally {
    await server.close();
  }
});
