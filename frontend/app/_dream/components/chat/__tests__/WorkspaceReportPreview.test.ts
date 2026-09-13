// [Input] Production ChatMarkdown/WorkspaceProvider with finite mocked bearer-protected report/image responses.
// [Output] Local-Chrome evidence for report previews, relative/explicit images, nested viewer focus, downloads and fail-closed reads.
// [Pos] Workspace report preview technical regression test.
// [Sync] 2026-09-13: reproduce download-only report/image links without calling providers or changing real user data.
// Scope: Project/Episode/canonical stories/.dream publication/Hook/DB projections are not in scope;
// Thread and files must remain unchanged; only the visible file consumer changes.

import { expect, test } from '@playwright/test';
// @ts-expect-error Node-only harness imports.
import { readFileSync } from 'node:fs';
// @ts-expect-error Node-only harness imports.
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { parseWorkspaceUri, resolveWorkspaceDocumentReference } from '../workspaceUri';

test.use({ channel: 'chrome' });
const PNG = readFileSync(fileURLToPath(new URL('../../../../../public/placeholder-memory.png', import.meta.url)));
const REPORT = '# 图文报告\n\n![Figure 3](fig3.png)\n\n![Figure 4](workspace://files/report/fig4.png)\n\n![Figure 5](./fig5.png)\n\n`![Literal](workspace://files/report/literal.png)`\n\n<script>throw new Error("raw HTML executed")</script>';

test('relative references are document-scoped and still pass the strict Workspace parser', () => {
  expect(resolveWorkspaceDocumentReference('fig3.png')).toBe('fig3.png');
  expect(parseWorkspaceUri(resolveWorkspaceDocumentReference('./fig3.png', 'files/中文 报告/report.md'))).toMatchObject({ ok: true, path: 'files/中文 报告/fig3.png' });
  for (const value of ['../secret.png', '%252e%252e/secret.png', '/etc/passwd', 'fig3.png?token=x', '%2fsecret.png']) {
    expect(parseWorkspaceUri(resolveWorkspaceDocumentReference(value, 'files/report/report.md')).ok).toBe(false);
  }
  expect(resolveWorkspaceDocumentReference('https://example.test/image.png', 'files/report/report.md')).toBe('https://example.test/image.png');
  expect(resolveWorkspaceDocumentReference('#chapter', 'files/report/report.md')).toBe('#chapter');
});

test('open reports with three images and preview image links instead of silently downloading', async ({ page }) => {
  const module = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import i18n from '/app/_dream/i18n.ts';
    import { setThemeMode } from '/app/_dream/utils/theme.ts';
    import { WorkspaceProvider } from '/app/_dream/contexts/WorkspaceContext.tsx';
    import ChatMarkdown from '/app/_dream/components/chat/ChatMarkdown.tsx';
    import '/app/_dream/styles/tokens.css';
    import '/app/_dream/styles/markdown.css';
    const root = createRoot(document.querySelector('#root'));
    let thread = 'thread-report-preview';
    const render = () => root.render(React.createElement(WorkspaceProvider, null,
      React.createElement('main', { className: 'prose', style: { width: 'min(680px, calc(100vw - 32px))', margin: '16px auto' } },
        React.createElement(ChatMarkdown, { text: ${JSON.stringify('[打开图文报告](workspace://files/report/report.md)\n\n[图 3](workspace://files/report/fig3.png)')}, workspaceSessionId: thread }))));
    window.switchThread = () => { thread = 'thread-other'; render(); };
    window.setPresentation = async () => { await i18n.changeLanguage('zh'); setThemeMode('dark'); };
    render();
  `;
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)), configFile: false, logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0 },
    plugins: [{ name: 'workspace-report-preview-isolated-harness',
      configureServer(vite) { vite.middlewares.use((req, res, next) => {
        if ((req as unknown as { url: string }).url !== '/report-preview') return next();
        void vite.transformIndexHtml('/report-preview', '<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/report-preview.js"></script></body></html>').then(html => { res.setHeader('Content-Type', 'text/html'); res.end(html); }, next);
      }); },
      resolveId(id) { return id === '/report-preview.js' ? '\0report-preview.js' : null; },
      load(id) { return id === '\0report-preview.js' ? module : null; },
    }],
  });
  const reads: Array<{ path: string | null; thread: string | null; auth: string | undefined; endpoint: string }> = [];
  const diagnostics: string[] = [];
  let reportMime = 'text/markdown';
  page.on('pageerror', error => diagnostics.push(error.message));
  page.on('console', message => { if (message.type() === 'error') diagnostics.push(message.text()); });
  await page.addInitScript(() => { localStorage.setItem('auth_token', 'isolated-report-token'); localStorage.setItem('ink-language', 'en'); });
  await page.route('**/api/system-config', route => route.fulfill({ json: { data: { workspace_enabled: true } } }));
  await page.route('**/api/workspace/files/**', async route => {
    const url = new URL(route.request().url());
    reads.push({ path: url.searchParams.get('path'), thread: url.searchParams.get('sessionId'), auth: route.request().headers().authorization, endpoint: url.pathname });
    await route.fulfill(url.searchParams.get('path')?.endsWith('.md')
      ? { contentType: reportMime, body: REPORT }
      : { contentType: 'image/png', body: PNG });
  });
  try {
    await server.listen();
    const address = server.httpServer?.address();
    if (!address || typeof address === 'string') throw new Error('Missing isolated harness port');
    await page.goto(`http://127.0.0.1:${address.port}/report-preview`);
    const openReport = page.getByRole('button', { name: '打开图文报告', exact: true });
    await expect(openReport).toBeVisible();
    expect(reads).toHaveLength(0);
    await page.getByRole('button', { name: '图 3', exact: true }).click();
    await expect(page.locator('[data-workspace-file-preview="fullsize"]')).toBeVisible();
    expect(reads.map(read => read.path)).toEqual(['files/report/fig3.png']);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await openReport.click();
    const report = page.getByRole('dialog', { name: 'report.md', exact: true });
    await expect(report.getByRole('heading', { name: '图文报告' })).toBeVisible();
    await expect(report.locator('[data-workspace-file-preview="thumbnail"]')).toHaveCount(3);
    await expect.poll(() => report.locator('img').evaluateAll(images => images.every(image => (image as HTMLImageElement).naturalWidth > 0))).toBe(true);
    await expect(report.locator('code')).toContainText('![Literal]');
    expect(reads.some(read => read.path?.includes('literal'))).toBe(false);
    await report.getByRole('button', { name: 'Preview Figure 3 at full size', exact: true }).first().click();
    await expect(page.getByRole('dialog')).toHaveCount(2);
    const viewer = page.getByRole('dialog').last();
    await viewer.getByRole('button', { name: 'Close image preview', exact: true }).focus();
    await page.keyboard.press('Shift+Tab');
    expect(await viewer.evaluate(dialog => dialog.contains(document.activeElement))).toBe(true);
    await page.keyboard.press('Escape');
    await expect(report).toBeVisible();
    await expect(page.getByRole('dialog')).toHaveCount(1);
    expect(await page.evaluate(() => document.body.style.overflow)).toBe('hidden');
    await page.evaluate(() => (window as unknown as { setPresentation: () => Promise<void> }).setPresentation());
    await page.setViewportSize({ width: 360, height: 740 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    const bounds = await report.boundingBox();
    expect(bounds?.width).toBeLessThanOrEqual(360);
    await page.keyboard.press('Escape');
    expect(await page.evaluate(() => document.body.style.overflow)).toBe('');
    const downloadEvent = page.waitForEvent('download');
    await page.getByRole('button', { name: '下载文件', exact: true }).click();
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toBe('report.md');
    expect(reads.at(-1)?.endpoint).toBe('/api/workspace/files/download');
    reportMime = 'text/html';
    await openReport.click();
    await expect(report.getByRole('alert')).toHaveText('此文件类型不支持内联预览。');
    await page.keyboard.press('Escape');
    reportMime = 'text/markdown';
    await openReport.click();
    await expect(report.locator('[data-workspace-file-preview="thumbnail"]')).toHaveCount(3);
    await report.getByRole('button', { name: '查看 Figure 3 大图', exact: true }).first().click();
    await expect(page.getByRole('dialog')).toHaveCount(2);
    await page.evaluate(() => (window as unknown as { switchThread: () => void }).switchThread());
    await expect(page.getByRole('dialog')).toHaveCount(0);
    expect(await page.evaluate(() => document.body.style.overflow)).toBe('');
    expect(reads.every(read => read.auth === 'Bearer isolated-report-token' && read.thread === 'thread-report-preview')).toBe(true);
    expect(diagnostics).toEqual([]);
  } finally { await server.close(); }
});
