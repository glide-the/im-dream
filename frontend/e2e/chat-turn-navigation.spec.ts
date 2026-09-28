// [Input] Production TurnNavigation component and a local isolated Chrome/Vite fixture.
// [Output] Browser coverage for compact animated ticks, summary hover, keyboard activation, and narrow layout.
// [Pos] Provider-free Chat navigation interaction acceptance.
// [Sync] 2026-09-29: cover desktop and mobile navigation without sending a Chat turn.

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
  import TurnNavigation from '/app/_dream/components/chat/TurnNavigation.tsx';

  window.__selectedTurns = [];
  const items = [
    { messageId: 'user-1', userPreview: 'Plan the chapter', hasAttachment: false, assistantPreview: 'Here is a chapter outline', status: 'answered' },
    { messageId: 'user-2', userPreview: 'Revise the ending', hasAttachment: false, assistantPreview: 'The ending now resolves the conflict', status: 'answered' },
    { messageId: 'user-3', userPreview: 'notes.pdf', hasAttachment: true, assistantPreview: null, status: 'no_reply' },
  ];
  function Harness() {
    const [active, setActive] = useState('user-1');
    return React.createElement('div', { className: 'chat-turn-reading', style: { width: 'min(100%, 800px)', height: '550px' } },
      React.createElement('div', { className: 'chat-turn-reading__layout' },
        React.createElement(TurnNavigation, {
          items,
          activeMessageId: active,
          loadingIndex: false,
          partialIndex: false,
          locatingMessageId: null,
          failedMessageId: null,
          onNavigate: (id) => { window.__selectedTurns.push(id); setActive(id); },
          onRetryIndex: () => {},
        }),
        React.createElement('div', { style: { flex: 1, minWidth: 0, background: 'var(--color-bg-app)' } }, 'Existing message region'),
      ),
    );
  }
  createRoot(document.querySelector('#root')).render(React.createElement(Harness));
`;

let server: Awaited<ReturnType<typeof createServer>>;
let baseUrl: string;

test.beforeAll(async () => {
  const port = await reserveEphemeralPort();
  server = await createServer({
    root: fileURLToPath(new URL('../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'chat-turn-navigation-harness',
      enforce: 'pre',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== '/turn-navigation') return next();
          const html = await vite.transformIndexHtml('/turn-navigation', `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root"></div><script type="module" src="/turn-navigation.js"></script></body></html>
          `);
          response.statusCode = 200;
          response.setHeader('Content-Type', 'text/html; charset=utf-8');
          response.end(html);
        });
      },
      resolveId(id) { return id === '/turn-navigation.js' ? '\0turn-navigation.js' : null; },
      load(id) { return id === '\0turn-navigation.js' ? harnessModule : null; },
    }],
  });
  await server.listen();
  baseUrl = `http://127.0.0.1:${port}/turn-navigation`;
});

test.afterAll(async () => { await server?.close(); });

test('desktop ticks expose the paired summary and navigate by mouse or keyboard', async ({ page }) => {
  await page.goto(baseUrl);
  const ticks = page.locator('.chat-turn-navigation__tick');
  await expect(ticks).toHaveCount(3);
  expect(await page.locator('.chat-turn-navigation').evaluate((element) => element.getBoundingClientRect().width)).toBeLessThanOrEqual(40);
  expect(await ticks.evaluateAll((buttons) =>
    buttons[1].getBoundingClientRect().top - buttons[0].getBoundingClientRect().top,
  )).toBeLessThanOrEqual(22);
  await expect(ticks.first()).toHaveAttribute('data-proximity', '0');
  await ticks.nth(1).hover();
  await expect(ticks.nth(1)).toHaveAttribute('data-proximity', '0');
  await expect(ticks.first()).toHaveAttribute('data-proximity', '1');
  await expect.poll(async () => page.locator('.chat-turn-navigation__mark').evaluateAll((marks) =>
    marks[1].getBoundingClientRect().width - marks[0].getBoundingClientRect().width,
  )).toBeGreaterThan(4);
  await expect(page.locator('.chat-turn-navigation__preview')).toContainText('Revise the ending');
  await expect(page.locator('.chat-turn-navigation__preview')).toContainText('resolves the conflict');
  await page.evaluate(() => { document.documentElement.dataset.theme = 'dark'; });
  expect(await page.locator('.chat-turn-reading').evaluate((element) =>
    getComputedStyle(element).backgroundColor,
  )).toBe(await page.locator('.chat-turn-reading__layout > div:last-child').evaluate((element) =>
    getComputedStyle(element).backgroundColor,
  ));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(ticks.nth(1).locator('.chat-turn-navigation__mark')).toHaveCSS('transition-duration', '0s');
  await ticks.nth(1).click();
  await expect(ticks.nth(1)).toHaveAttribute('aria-current', 'location');
  await ticks.nth(2).focus();
  await page.keyboard.press('Enter');
  await expect.poll(() => page.evaluate(() => (window as unknown as { __selectedTurns: string[] }).__selectedTurns)).toEqual(['user-2', 'user-3']);
});

test('narrow container offers a touch-sized list without horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(baseUrl);
  const toggle = page.locator('.chat-turn-navigation__mobile-toggle');
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(page.locator('.chat-turn-navigation__mobile-item')).toHaveCount(3);
  await page.locator('.chat-turn-navigation__mobile-item').first().click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
