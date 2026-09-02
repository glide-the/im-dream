// [Input] Validated historical turn projection and a deliberately heavy lazy part renderer.
// [Output] Browser proof for final-only default mount, accessibility, order, unmount, and anchor stability.
// [Pos] Shared Chat/Dream historical-turn interaction acceptance seam.
// [Sync] 2026-09-02: created for the approved process disclosure interaction.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node harness imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright Node harness imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chrome', viewport: { width: 720, height: 640 } });

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

test('collapsed history mounts only final and keyboard expansion mounts exact process order', async ({ page }) => {
  const harnessModule = `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import '/src/styles/tokens.css';
    import AssistantTurnGroup from '/src/components/chat/AssistantTurnGroup.tsx';

    window.__partCalls = [];
    const parts = ['reasoning-json', 'intermediate-markdown', 'tool-output-json', 'final-answer'];
    function Harness() {
      const [expanded, setExpanded] = useState(false);
      return React.createElement('div', {
        'data-chat-scroll-region': 'messages',
        style: { height: '260px', overflow: 'auto', paddingTop: '120px' },
      }, React.createElement(AssistantTurnGroup, {
        projection: {
          turnKey: 'turn-stable',
          finalPartIndex: 3,
          processPartIndexes: [0, 1, 2],
          durationMs: 3200,
        },
        expanded,
        onExpandedChange: (_turnKey, value) => setExpanded(value),
        renderPart: (partIndex, kind) => {
          window.__partCalls.push(partIndex);
          return React.createElement('div', {
            key: partIndex,
            'data-heavy-process-node': kind === 'process' ? parts[partIndex] : undefined,
            'data-final-node': kind === 'final' ? 'true' : undefined,
          }, parts[partIndex]);
        },
      }));
    }
    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  const port = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'assistant-turn-group-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if ((request as { url?: string }).url !== '/assistant-turn-group') return next();
          const html = await vite.transformIndexHtml('/assistant-turn-group', `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root"></div><script type="module" src="/assistant-turn-group.js"></script></body></html>
          `);
          response.statusCode = 200;
          response.setHeader('Content-Type', 'text/html; charset=utf-8');
          response.end(html);
        });
      },
      resolveId(id) {
        return id === '/assistant-turn-group.js' ? '\0assistant-turn-group.js' : null;
      },
      load(id) {
        return id === '\0assistant-turn-group.js' ? harnessModule : null;
      },
    }],
  });

  try {
    await server.listen();
    await page.goto(`http://127.0.0.1:${port}/assistant-turn-group`);
    const toggle = page.getByRole('button', { name: /process/i });
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('[data-final-node="true"]')).toHaveText('final-answer');
    await expect(page.locator('[data-heavy-process-node]')).toHaveCount(0);
    expect(await page.evaluate(() => (window as unknown as { __partCalls: number[] }).__partCalls)).toEqual([3]);

    const anchorTop = await toggle.evaluate((element) => element.getBoundingClientRect().top);
    await toggle.focus();
    await page.keyboard.press('Enter');
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(toggle).toBeFocused();
    const controls = await toggle.getAttribute('aria-controls');
    expect(controls).toBeTruthy();
    await expect(page.locator(`#${controls}`)).toBeVisible();
    await expect(page.locator('[data-heavy-process-node]')).toHaveText([
      'reasoning-json',
      'intermediate-markdown',
      'tool-output-json',
    ]);
    const expandedTop = await toggle.evaluate((element) => element.getBoundingClientRect().top);
    expect(Math.abs(expandedTop - anchorTop)).toBeLessThan(1);

    await page.keyboard.press('Space');
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('[data-heavy-process-node]')).toHaveCount(0);
    await expect(page.locator('[data-final-node="true"]')).toHaveText('final-answer');
    await expect(toggle).toBeFocused();
  } finally {
    await server.close();
  }
});
