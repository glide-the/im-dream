// [Input] Production AssistantTurnGroup + ChatMarkdown with one generated oversized historical process body.
// [Output] Local-Chrome node/time evidence that collapsed history skips heavy Markdown DOM and remounts on demand.
// [Pos] Performance-characterization acceptance seam; assertions are structural, not a fixed millisecond SLA.
// [Sync] 2026-09-02: validate oversized render cost through the full projection contract.

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

test('oversized historical process has zero Markdown DOM until expansion and unmounts again', async ({ page }) => {
  const harnessModule = `
    import React, { useLayoutEffect, useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import '/src/i18n.ts';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';
    import AssistantTurnGroup from '/src/components/chat/AssistantTurnGroup.tsx';
    import ChatMarkdown from '/src/components/chat/ChatMarkdown.tsx';

    const startedAt = performance.now();
    const row = '## JSON 过程\\n- status: ok\\n- payload: **{"items":[1,2,3],"message":"long historical tool result"}**\\n\\n';
    const largeMarkdown = Array.from({ length: 12000 }, () => row).join('');
    window.__largeBytes = new TextEncoder().encode(largeMarkdown).byteLength;
    function Harness() {
      const [expanded, setExpanded] = useState(false);
      useLayoutEffect(() => {
        requestAnimationFrame(() => {
          window.__historyMetrics = window.__historyMetrics || {};
          window.__historyMetrics[expanded ? 'expanded' : 'collapsed'] = {
            elapsedMs: performance.now() - (window.__toggleStartedAt || startedAt),
            domNodes: document.querySelectorAll('*').length,
          };
        });
      }, [expanded]);
      return React.createElement('div', {
        'data-chat-scroll-region': 'messages',
        style: { height: '620px', overflow: 'auto' },
      }, React.createElement(AssistantTurnGroup, {
        projection: {
          turnKey: 'turn-large',
          finalPartIndex: 1,
          processPartIndexes: [0],
          processAvailable: true,
          deferredProcess: false,
          durationMs: null,
        },
        expanded,
        onExpandedChange: (_turnKey, value) => {
          window.__toggleStartedAt = performance.now();
          setExpanded(value);
        },
        renderPart: (partIndex, kind) => kind === 'process'
          ? React.createElement('div', { 'data-large-process': largeMarkdown.length },
              React.createElement(ChatMarkdown, { text: largeMarkdown }))
          : React.createElement(ChatMarkdown, { text: '最终正文保持默认可读。' }),
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
      name: 'chat-history-large-message-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if ((request as { url?: string }).url !== '/chat-history-large-message') return next();
          const html = await vite.transformIndexHtml('/chat-history-large-message', `
            <!doctype html><html><head><link rel="icon" href="data:,"></head>
            <body><div id="root"></div><script type="module" src="/chat-history-large-message.js"></script></body></html>
          `);
          response.statusCode = 200;
          response.setHeader('Content-Type', 'text/html; charset=utf-8');
          response.end(html);
        });
      },
      resolveId(id) {
        return id === '/chat-history-large-message.js' ? '\0chat-history-large-message.js' : null;
      },
      load(id) {
        return id === '\0chat-history-large-message.js' ? harnessModule : null;
      },
    }],
  });

  try {
    await server.listen();
    await page.goto(`http://127.0.0.1:${port}/chat-history-large-message`);
    const toggle = page.getByRole('button', { name: /process/i });
    await expect(page.getByText('最终正文保持默认可读。')).toBeVisible();
    await expect(page.locator('[data-large-process]')).toHaveCount(0);
    await page.waitForFunction(() => Boolean((window as unknown as { __historyMetrics?: { collapsed?: unknown } }).__historyMetrics?.collapsed));
    const collapsed = await page.evaluate(() => ({
      bytes: (window as unknown as { __largeBytes: number }).__largeBytes,
      metrics: (window as unknown as { __historyMetrics: { collapsed: { elapsedMs: number; domNodes: number } } }).__historyMetrics.collapsed,
    }));

    await toggle.click();
    await expect(page.locator('[data-large-process]')).toBeVisible({ timeout: 30_000 });
    await page.waitForFunction(() => Boolean((window as unknown as { __historyMetrics?: { expanded?: unknown } }).__historyMetrics?.expanded));
    const expanded = await page.evaluate(() => (
      (window as unknown as { __historyMetrics: { expanded: { elapsedMs: number; domNodes: number } } }).__historyMetrics.expanded
    ));
    expect(collapsed.bytes).toBeGreaterThan(1_000_000);
    expect(collapsed.metrics.domNodes).toBeLessThan(expanded.domNodes);
    expect(expanded.domNodes).toBeGreaterThan(50_000);

    await toggle.click();
    await expect(page.locator('[data-large-process]')).toHaveCount(0);
    const remountedNodes = await page.locator('*').count();
    expect(remountedNodes).toBeLessThan(expanded.domNodes);
    // Emit characterization evidence without enforcing a machine-specific time SLA.
    console.log(JSON.stringify({ largeHistory: { ...collapsed, expanded, remountedNodes } }));
  } finally {
    await server.close();
  }
});
