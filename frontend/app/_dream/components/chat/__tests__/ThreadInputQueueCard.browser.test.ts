// [Input] The production queued-input card, local Chrome, and callback spies with no business API writes.
// [Output] Verify screenshot actions, queued-only guards, keyboard menu and mobile card width.
// [Pos] Isolated browser presentation test for the Chat composer queue card.
// [Sync] 2026-09-27: capture the production card/menu at desktop and mobile sizes while checking screenshot actions.

import { expect, test } from '@playwright/test';
// @ts-expect-error This browser harness imports Node APIs outside the application tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error This browser harness imports Node APIs outside the application tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chrome' });

async function reservePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createNetServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (!address || typeof address === 'string') { probe.close(); reject(new Error('Port unavailable')); return; }
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
}

test('queue card exposes the pictured per-message actions and guards selected messages', async ({ page }, testInfo) => {
  const port = await reservePort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true },
    plugins: [{
      name: 'thread-input-queue-card-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== '/queue-card') return next();
          try {
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(await vite.transformIndexHtml('/queue-card', '<!doctype html><html><body><div id="root"></div><script type="module" src="/queue-card-harness.js"></script></body></html>'));
          } catch (error) { next(error as Error); }
        });
      },
      resolveId(id) { return id === '/queue-card-harness.js' ? '\0queue-card-harness.js' : null; },
      load(id) {
        if (id !== '\0queue-card-harness.js') return null;
        return `
          import React, { useState } from 'react';
          import { createRoot } from 'react-dom/client';
          import i18n from '/app/_dream/i18n.ts';
          import Card from '/app/_dream/components/chat/ThreadInputQueueCard.tsx';
          import '/app/_dream/styles/tokens.css';
          import '/app/_dream/index.css';
          void i18n.changeLanguage('zh');
          window.queueActions = [];
          function Harness() {
            const [status, setStatus] = useState('queued');
            const entry = { message_id: 'queued-one', thread_id: 'owned-thread', queue_sequence: '1', status,
              revision: 1, dispatch_turn_id: null, created_at: '2026-09-27T00:00:00Z', text: '输出再长一点' };
            const record = (action, text) => { window.queueActions.push({ action, text }); return Promise.resolve(); };
            return React.createElement('main', { style: { maxWidth: '52rem', minHeight: '80vh', margin: '2rem auto', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' } },
              React.createElement('section', { style: { maxHeight: '5rem', overflowY: 'auto' } },
                React.createElement(Card, { entry, localOwner: true,
                  onGuide: () => record('guide'), onCancel: () => record('cancel'),
                  onEdit: (_entry, text) => record('edit', text), onSideChat: () => record('side') })),
              React.createElement('button', { 'data-testid': 'select-state', onClick: () => setStatus('selected') }, 'Select state'));
          }
          createRoot(document.querySelector('#root')).render(React.createElement(Harness));
        `;
      },
    }],
  });
  try {
    await server.listen();
    await page.goto(`http://127.0.0.1:${port}/queue-card`);
    const card = page.getByTestId('thread-input-queue-card');
    await expect(card).toBeVisible();
    await expect(card).toContainText('输出再长一点');
    await card.screenshot({ path: testInfo.outputPath('queue-card-desktop.png') });
    await expect(card.getByRole('button', { name: '调整方向' })).toBeEnabled();
    await card.getByRole('button', { name: '调整方向' }).click();
    await card.getByRole('button', { name: '更多操作' }).click();
    await expect(page.getByRole('menuitem', { name: '在侧边聊天中打开' })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath('queue-menu-desktop.png') });
    await page.getByRole('menuitem', { name: '在侧边聊天中打开' }).click();
    await card.getByRole('button', { name: '更多操作' }).click();
    await page.getByRole('menuitem', { name: '编辑消息' }).click();
    await card.getByRole('textbox', { name: '编辑消息' }).fill('修改后的消息');
    await card.getByRole('button', { name: '保存' }).click();
    await expect.poll(() => page.evaluate(() => (window as unknown as { queueActions: unknown[] }).queueActions.length)).toBe(3);
    await page.getByTestId('select-state').click();
    await expect(card.getByRole('button', { name: '调整方向' })).toBeDisabled();
    await expect(card.getByRole('button', { name: '删除排队消息' })).toBeDisabled();
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(card).toBeInViewport();
    expect(await card.evaluate((node) => node.getBoundingClientRect().width)).toBeLessThanOrEqual(390);
    await card.getByRole('button', { name: '更多操作' }).click();
    const menuBox = await page.getByRole('menu').boundingBox();
    expect(menuBox).not.toBeNull();
    expect(menuBox!.x).toBeGreaterThanOrEqual(0);
    expect(menuBox!.x + menuBox!.width).toBeLessThanOrEqual(390);
    await page.screenshot({ path: testInfo.outputPath('queue-menu-mobile.png') });
    await page.keyboard.press('Escape');
    await expect(page.getByRole('menu')).toHaveCount(0);
    await expect(card.getByRole('button', { name: '更多操作' })).toBeFocused();
  } finally {
    await server.close();
  }
});
