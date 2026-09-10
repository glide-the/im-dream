// [Input] Real Chromium input against the production AIInputDock module with mocked Skill catalog and system-config APIs.
// [Output] Regression coverage for the user-visible slash shortcut menu: draft trigger, listbox rendering, keyboard selection, dismissal, and silent catalog-failure degrade.
// [Pos] AIInputDock slash menu regression contract in frontend/app/_dream/components/chat/__tests__.

import { expect, test, type Page } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer, type ViteDevServer } from 'vite';

test.use({ channel: 'chromium' });

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

    window.${sentLogKey} = [];
    void i18n.changeLanguage('en');

    function Harness() {
      const [sentCount, setSentCount] = useState(0);
      return React.createElement(
        'main',
        null,
        React.createElement(AIInputDock, {
          onSendMessage: (message) => {
            window.${sentLogKey}.push(message);
            setSentCount((current) => current + 1);
          },
          placeholder: 'Ask Ink & Memory…',
        }),
        React.createElement('output', { 'data-testid': 'sent-count' }, String(sentCount)),
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
