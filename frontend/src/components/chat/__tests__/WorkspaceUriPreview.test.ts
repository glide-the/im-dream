// [Input] Untrusted workspace:// Markdown references, mocked authenticated Workspace responses, and current Thread/Workspace state.
// [Output] Parser and real-Chromium regression evidence for secure responsive thumbnails, fixed-sheet/content-only zoom, authenticated long-image export, reload, fallback, and compatibility paths.
// [Pos] workspace URI Chat Markdown browser contract test in frontend/src/components/chat/__tests__
// [Sync] 2026-08-22: initial parser and provider-free Chromium coverage for preview/download, reload, isolation inputs, and compatibility.
// [Sync] 2026-08-22: verify v2.1 thumbnail bounds plus wide/narrow full-size modal, focus restoration, and ordinary-image isolation.
// [Sync] 2026-08-23: prove Workspace images resolve through the same owner-bound endpoint inside the production long-image export path.
// [Sync] 2026-08-23: verify Mermaid and Workspace share one inline frame/full-screen skeleton, with enlarge beside copy and accessible zoom/download controls.
// [Sync] 2026-08-23: verify upward/downward wheel zoom, scroll suppression, shared percentage state, and 50%–200% clamping in Chromium.
// [Sync] 2026-08-23: compare real geometry before/after zoom to prove only image/diagram content scales while the paper sheet stays fixed.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { Buffer } from 'node:buffer';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { readFileSync } from 'node:fs';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { parseWorkspaceUri } from '../workspaceUri';

test.use({ channel: 'chromium' });

const PNG_BYTES = readFileSync(fileURLToPath(new URL('../../../../public/placeholder-memory.png', import.meta.url)));

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

test('parses the v1 protocol once and rejects ambiguous or escaping paths', () => {
  expect(parseWorkspaceUri('workspace://files/fashion_flux2.png')).toEqual({
    ok: true,
    path: 'files/fashion_flux2.png',
    fileName: 'fashion_flux2.png',
    canPreviewImage: true,
  });
  expect(parseWorkspaceUri('workspace://files/中文 空格.png')).toMatchObject({
    ok: true,
    path: 'files/中文 空格.png',
  });
  expect(parseWorkspaceUri('workspace://files/%E4%B8%AD%E6%96%87%20%E7%A9%BA%E6%A0%BC.png')).toMatchObject({
    ok: true,
    path: 'files/中文 空格.png',
  });
  expect(parseWorkspaceUri('workspace://files/report.pdf')).toMatchObject({
    ok: true,
    canPreviewImage: false,
  });

  const rejected = [
    ['workspace://', 'empty_path'],
    ['workspace:///etc/passwd', 'absolute_path'],
    ['workspace://files/../secret.png', 'invalid_segment'],
    ['workspace://files/%2e%2e/secret.png', 'invalid_segment'],
    ['workspace://files/%252e%252e/secret.png', 'repeated_encoding'],
    ['workspace://files%2fsecret.png', 'encoded_separator'],
    ['workspace://files\\secret.png', 'unsupported_syntax'],
    ['workspace://files/image.png?token=secret', 'unsupported_syntax'],
    ['workspace://files/image.png#fragment', 'unsupported_syntax'],
    ['workspace://private/secret.png', 'unsupported_namespace'],
    ['https://example.test/image.png', 'not_workspace_uri'],
  ] as const;
  for (const [uri, code] of rejected) {
    expect(parseWorkspaceUri(uri)).toEqual({ ok: false, code });
  }
});

test('renders three authenticated Workspace images and preserves safe fallbacks across reload', async ({ page }) => {
  const harnessModule = `
    import React from 'react';
    import { createRoot } from 'react-dom/client';
    import i18n from '/src/i18n.ts';
    import { setThemeMode } from '/src/utils/theme.ts';
    import { WorkspaceProvider } from '/src/contexts/WorkspaceContext.tsx';
    import ChatMarkdown from '/src/components/chat/ChatMarkdown.tsx';
    import { downloadThreadImage, releaseThreadImage, renderThreadImage } from '/src/components/chat/exportThreadImage.tsx';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';

    const markdown = [
      '## 生成结果预览',
      '',
      '![Flux.2 Dev](workspace://files/fashion_flux2.png)',
      '',
      '![Z-Image-Turbo](workspace://files/%E4%B8%AD%E6%96%87%20fashion_zimage.png)',
      '',
      '![Qwen Image 2512](workspace://files/fashion_qwen.webp)',
      '',
      '![Missing](workspace://files/missing.png)',
      '',
      '![Retryable](workspace://files/retry.png)',
      '',
      '![Blocked](workspace://files/%252e%252e/secret.png)',
      '',
      '![Unsupported](workspace://files/vector.svg)',
      '',
      '![Remote](https://assets.example.test/remote.png)',
      '',
      '[Workspace report](workspace://files/report.pdf)',
      '',
      '[Web documentation](https://example.test/docs)',
      '',
      '[Jump to result](#result)',
      '',
      '\`\`\`mermaid',
      'flowchart LR',
      '  A[Workspace] --> B[Preview]',
      '\`\`\`',
    ].join('\\n');

    let exportedImage = null;
    window.setPreviewPresentation = async () => {
      await i18n.changeLanguage('zh');
      setThemeMode('dark');
    };
    window.runWorkspaceImageExport = async () => {
      exportedImage = await renderThreadImage({
        threadId: 'thread-preview',
        title: 'Workspace export',
        messages: [{
          role: 'assistant',
          files: [],
          blocks: [{
            kind: 'text',
            text: [
              '## 生成结果预览',
              '',
              '![Flux.2 Dev](workspace://files/fashion_flux2.png)',
              '',
              '![Z-Image-Turbo](workspace://files/%E4%B8%AD%E6%96%87%20fashion_zimage.png)',
              '',
              '![Qwen Image 2512](workspace://files/fashion_qwen.webp)',
              '',
              '![Missing](workspace://files/missing.png)',
              '',
              '![Corrupt](workspace://files/corrupt.png)',
            ].join('\\n'),
          }],
        }],
        labels: {
          you: 'You',
          assistant: 'Assistant',
          footer: 'Ink & Memory',
          thinking: 'Thinking',
          truncated: 'Truncated',
          workspaceImageUnavailable: 'Workspace image unavailable',
        },
      });
      const preview = new Image();
      preview.id = 'workspace-export-preview';
      preview.src = exportedImage.images[0];
      preview.alt = 'Exported Workspace conversation';
      preview.style.cssText = 'position:fixed;inset:0;z-index:1000;display:block;width:100%;height:100%;object-fit:contain;background:#f6efe5;';
      document.body.appendChild(preview);
      await preview.decode();
      return {
        parts: exportedImage.images.length,
        width: preview.naturalWidth,
        height: preview.naturalHeight,
        fileName: exportedImage.fileName,
      };
    };
    window.downloadWorkspaceImageExport = async () => {
      if (!exportedImage) throw new Error('Workspace export is not ready');
      await downloadThreadImage(exportedImage);
    };
    window.releaseWorkspaceImageExport = () => {
      releaseThreadImage(exportedImage);
      exportedImage = null;
      document.querySelector('#workspace-export-preview')?.remove();
    };

    createRoot(document.querySelector('#root')).render(
      React.createElement(
        WorkspaceProvider,
        null,
        React.createElement(
          'main',
          { className: 'prose', style: { width: 'min(680px, calc(100vw - 32px))', margin: '32px auto' } },
          React.createElement(ChatMarkdown, { text: markdown, workspaceSessionId: 'thread-preview' }),
        ),
      ),
    );
  `;
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'workspace-uri-preview-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== '/workspace-uri-preview') return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><head><link rel="icon" href="data:,"></head>
              <body><div id="root"></div><script type="module" src="/workspace-uri-preview-harness.js"></script></body></html>
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
        return id === '/workspace-uri-preview-harness.js'
          ? '\0workspace-uri-preview-harness.js'
          : null;
      },
      load(id) {
        return id === '\0workspace-uri-preview-harness.js' ? harnessModule : null;
      },
    }],
  });

  const diagnostics: string[] = [];
  const expectedFileFailureDiagnostics: string[] = [];
  const fileRequests: Array<{ readonly path: string; readonly sessionId: string; readonly authorization: string | undefined }> = [];
  let workspaceEnabled = true;
  let retryAttempts = 0;
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    if (
      message.text() === 'Failed to load resource: the server responded with a status of 404 (Not Found)'
      || message.text() === 'Failed to load resource: the server responded with a status of 503 (Service Unavailable)'
    ) {
      expectedFileFailureDiagnostics.push(message.text());
      return;
    }
    diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });

  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'workspace-preview-token');
  });
  await page.route('**/api/system-config', async (route) => {
    await route.fulfill({ json: { data: { workspace_enabled: workspaceEnabled } } });
  });
  await page.route('https://assets.example.test/remote.png', async (route) => {
    await route.fulfill({ body: PNG_BYTES, contentType: 'image/png' });
  });
  await page.route('**/api/workspace/files/content?**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.searchParams.get('path') ?? '';
    fileRequests.push({
      path,
      sessionId: url.searchParams.get('sessionId') ?? '',
      authorization: route.request().headers().authorization,
    });
    if (path === 'files/missing.png') {
      await route.fulfill({ status: 404, json: { detail: 'Workspace file not found' } });
      return;
    }
    if (path === 'files/retry.png' && retryAttempts++ === 0) {
      await route.fulfill({ status: 503, json: { detail: 'Temporarily unavailable' } });
      return;
    }
    if (path === 'files/report.pdf') {
      await route.fulfill({ body: Buffer.from('%PDF-1.4 workspace preview'), contentType: 'application/pdf' });
      return;
    }
    if (path === 'files/corrupt.png') {
      await route.fulfill({ body: Buffer.from('not a valid png'), contentType: 'image/png' });
      return;
    }
    await route.fulfill({ body: PNG_BYTES, contentType: 'image/png' });
  });

  try {
    await server.listen();
    const address = server.httpServer?.address();
    if (address === null || address === undefined || typeof address === 'string') {
      throw new Error('Workspace URI harness did not bind a TCP port.');
    }
    const harnessUrl = `http://127.0.0.1:${address.port}/workspace-uri-preview`;
    await page.goto(harnessUrl);

    await expect(page.getByRole('heading', { name: '生成结果预览' })).toBeVisible();
    const mermaidBlock = page.locator('[data-markdown-media-kind="mermaid"]');
    const workspaceBlock = page.locator('[data-markdown-media-kind="workspace-image"]').first();
    await expect(mermaidBlock).toBeVisible();
    await expect(workspaceBlock).toBeVisible();
    await expect(mermaidBlock.getByTitle('Enlarge diagram')).toBeEnabled();
    const sharedFrameStyles = await Promise.all([mermaidBlock, workspaceBlock].map(async (block) => block.evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        background: style.backgroundColor,
        borderRadius: style.borderRadius,
        borderWidth: style.borderTopWidth,
      };
    })));
    expect(sharedFrameStyles[0]).toEqual(sharedFrameStyles[1]);
    const copyButton = mermaidBlock.getByTitle('Copy Markdown source');
    const enlargeDiagramButton = mermaidBlock.getByTitle('Enlarge diagram');
    expect(await copyButton.evaluate((button) => button.nextElementSibling?.getAttribute('title'))).toBe('Enlarge diagram');
    await enlargeDiagramButton.click();
    const mermaidDialog = page.getByRole('dialog', { name: 'Mermaid diagram preview' });
    await expect(mermaidDialog).toBeVisible();
    await expect(mermaidDialog.locator('.modal-zoom-value')).toHaveText('100%');
    await page.screenshot({ path: 'output/playwright/mermaid-media-preview-wide.png' });
    const mermaidStage = mermaidDialog.locator('.modal-media-stage');
    const mermaidSheet = mermaidDialog.locator('.markdown-media-preview__sheet--diagram');
    const mermaidZoomTarget = mermaidDialog.locator('.markdown-media-preview__zoom-target');
    const mermaidSheetAt100 = await mermaidSheet.boundingBox();
    const mermaidTargetAt100 = await mermaidZoomTarget.boundingBox();
    expect(mermaidSheetAt100).not.toBeNull();
    expect(mermaidTargetAt100).not.toBeNull();
    const pageScrollBeforeWheel = await page.evaluate(() => window.scrollY);
    const wheelWasPrevented = await mermaidStage.evaluate((stage) => {
      const wheel = new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaY: -120 });
      stage.dispatchEvent(wheel);
      return wheel.defaultPrevented;
    });
    expect(wheelWasPrevented).toBe(true);
    await expect(mermaidDialog.locator('.modal-zoom-value')).toHaveText('110%');
    const mermaidSheetAt110 = await mermaidSheet.boundingBox();
    const mermaidTargetAt110 = await mermaidZoomTarget.boundingBox();
    expect(mermaidSheetAt110?.width).toBeCloseTo(mermaidSheetAt100?.width ?? 0, 0);
    expect(mermaidSheetAt110?.height).toBeCloseTo(mermaidSheetAt100?.height ?? 0, 0);
    expect(mermaidTargetAt110?.width).toBeCloseTo((mermaidTargetAt100?.width ?? 0) * 1.1, 0);
    expect(mermaidTargetAt110?.height).toBeCloseTo((mermaidTargetAt100?.height ?? 0) * 1.1, 0);
    await mermaidStage.dispatchEvent('wheel', { deltaY: 120 });
    await expect(mermaidDialog.locator('.modal-zoom-value')).toHaveText('100%');
    expect(await page.evaluate(() => window.scrollY)).toBe(pageScrollBeforeWheel);
    await mermaidDialog.getByRole('button', { name: 'Zoom in' }).click();
    await expect(mermaidDialog.locator('.modal-zoom-value')).toHaveText('110%');
    const enlargedDiagramBox = await mermaidDialog.locator('.markdown-media-preview__sheet--diagram').boundingBox();
    expect(enlargedDiagramBox?.width ?? 0).toBeGreaterThan(900);
    expect(enlargedDiagramBox?.height ?? 0).toBeGreaterThan(500);
    await mermaidStage.evaluate((stage) => {
      for (let index = 0; index < 20; index += 1) {
        stage.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaY: -120 }));
      }
    });
    await expect(mermaidDialog.locator('.modal-zoom-value')).toHaveText('200%');
    const mermaidSheetAt200 = await mermaidSheet.boundingBox();
    expect(mermaidSheetAt200?.width).toBeCloseTo(mermaidSheetAt100?.width ?? 0, 0);
    expect(mermaidSheetAt200?.height).toBeCloseTo(mermaidSheetAt100?.height ?? 0, 0);
    await mermaidStage.dispatchEvent('wheel', { deltaY: -120 });
    await expect(mermaidDialog.locator('.modal-zoom-value')).toHaveText('200%');
    await mermaidStage.evaluate((stage) => {
      for (let index = 0; index < 20; index += 1) {
        stage.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaY: 120 }));
      }
    });
    await expect(mermaidDialog.locator('.modal-zoom-value')).toHaveText('50%');
    const mermaidSheetAt50 = await mermaidSheet.boundingBox();
    expect(mermaidSheetAt50?.width).toBeCloseTo(mermaidSheetAt100?.width ?? 0, 0);
    expect(mermaidSheetAt50?.height).toBeCloseTo(mermaidSheetAt100?.height ?? 0, 0);
    await mermaidStage.dispatchEvent('wheel', { deltaY: 120 });
    await expect(mermaidDialog.locator('.modal-zoom-value')).toHaveText('50%');
    await mermaidStage.click({ position: { x: 10, y: 10 } });
    await expect(mermaidDialog).toBeHidden();
    await expect(enlargeDiagramButton).toBeFocused();

    const workspaceImages = page.locator('img[data-workspace-file-state="success"]');
    await expect(workspaceImages).toHaveCount(3);
    expect(await workspaceImages.evaluateAll((images) => images.every((image) => image.getAttribute('src')?.startsWith('blob:')))).toBe(true);
    const previewTriggers = page.locator('[data-markdown-media-kind="workspace-image"] .markdown-media-block__action[aria-haspopup="dialog"]');
    await expect(previewTriggers).toHaveCount(3);
    const firstTrigger = previewTriggers.first();
    const wideThumbnailBox = await workspaceBlock.locator('.workspace-image-reference__trigger').boundingBox();
    expect(wideThumbnailBox).not.toBeNull();
    expect(wideThumbnailBox?.width).toBeLessThanOrEqual(421);
    expect(wideThumbnailBox?.height).toBeLessThanOrEqual(321);
    await expect(page.locator('[data-workspace-file-state="missing"]')).toContainText('Workspace file not found');
    await expect(page.locator('[data-workspace-file-state="retryable"]')).toContainText('Workspace file could not be loaded');
    await expect(page.locator('[data-workspace-file-state="invalid"]')).toContainText('Invalid Workspace file reference');
    await expect(page.locator('[data-workspace-file-state="unsupported"]')).toContainText('cannot be previewed inline');
    await expect(page.getByRole('img', { name: 'Remote' })).toHaveAttribute('src', 'https://assets.example.test/remote.png');
    expect(await page.getByRole('img', { name: 'Remote' }).evaluate((image) => image.closest('.workspace-image-reference__trigger'))).toBeNull();
    await expect(page.getByRole('link', { name: 'Web documentation' })).toHaveAttribute('href', 'https://example.test/docs');
    await expect(page.getByRole('link', { name: 'Jump to result' })).toHaveAttribute('href', '#result');

    const thumbnailSrc = await workspaceImages.first().getAttribute('src');
    await firstTrigger.click();
    const wideDialog = page.getByRole('dialog', { name: /Full-size preview · Flux\.2 Dev/ });
    await expect(wideDialog).toBeVisible();
    const closePreview = page.getByRole('button', { name: 'Close image preview' });
    await expect(closePreview).toBeFocused();
    const fullsizeImage = page.locator('img[data-workspace-file-preview="fullsize"]');
    await expect(fullsizeImage).toHaveAttribute('src', thumbnailSrc ?? '');
    const wideFullsizeBox = await fullsizeImage.boundingBox();
    expect(wideFullsizeBox).not.toBeNull();
    expect(wideFullsizeBox?.width ?? 0).toBeGreaterThan(wideThumbnailBox?.width ?? Number.POSITIVE_INFINITY);
    await expect(wideDialog.locator('.modal-zoom-value')).toHaveText('100%');
    await page.screenshot({ path: 'output/playwright/workspace-uri-preview-wide.png' });
    const workspaceStage = wideDialog.locator('.modal-media-stage');
    const workspaceSheet = wideDialog.locator('.markdown-media-preview__sheet');
    const workspaceSheetAt100 = await workspaceSheet.boundingBox();
    await workspaceStage.dispatchEvent('wheel', { deltaY: -120 });
    await expect(wideDialog.locator('.modal-zoom-value')).toHaveText('110%');
    const workspaceSheetAt110 = await workspaceSheet.boundingBox();
    const workspaceImageAt110 = await fullsizeImage.boundingBox();
    expect(workspaceSheetAt110?.width).toBeCloseTo(workspaceSheetAt100?.width ?? 0, 0);
    expect(workspaceSheetAt110?.height).toBeCloseTo(workspaceSheetAt100?.height ?? 0, 0);
    expect(workspaceImageAt110?.width).toBeCloseTo((wideFullsizeBox?.width ?? 0) * 1.1, 0);
    expect(workspaceImageAt110?.height).toBeCloseTo((wideFullsizeBox?.height ?? 0) * 1.1, 0);
    await page.screenshot({ path: 'output/playwright/workspace-uri-preview-content-zoom.png' });
    await workspaceStage.dispatchEvent('wheel', { deltaY: 120 });
    await expect(wideDialog.locator('.modal-zoom-value')).toHaveText('100%');
    await workspaceStage.evaluate((stage) => {
      for (let index = 0; index < 5; index += 1) {
        stage.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaY: 120 }));
      }
    });
    await expect(wideDialog.locator('.modal-zoom-value')).toHaveText('50%');
    const workspaceSheetAt50 = await workspaceSheet.boundingBox();
    const workspaceImageAt50 = await fullsizeImage.boundingBox();
    expect(workspaceSheetAt50?.width).toBeCloseTo(workspaceSheetAt100?.width ?? 0, 0);
    expect(workspaceSheetAt50?.height).toBeCloseTo(workspaceSheetAt100?.height ?? 0, 0);
    expect(workspaceImageAt50?.width).toBeCloseTo((wideFullsizeBox?.width ?? 0) * 0.5, 0);
    expect(workspaceImageAt50?.height).toBeCloseTo((wideFullsizeBox?.height ?? 0) * 0.5, 0);
    await page.screenshot({ path: 'output/playwright/workspace-uri-preview-content-zoom-50.png' });
    await workspaceStage.evaluate((stage) => {
      for (let index = 0; index < 5; index += 1) {
        stage.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaY: -120 }));
      }
    });
    await expect(wideDialog.locator('.modal-zoom-value')).toHaveText('100%');
    await wideDialog.getByRole('button', { name: 'Zoom in' }).click();
    await expect(wideDialog.locator('.modal-zoom-value')).toHaveText('110%');
    const imageDownloadPromise = page.waitForEvent('download');
    await wideDialog.getByRole('button', { name: 'Download image' }).click();
    const imageDownload = await imageDownloadPromise;
    expect(imageDownload.suggestedFilename()).toBe('fashion_flux2.png');
    await page.keyboard.press('Escape');
    await expect(wideDialog).toBeHidden();
    await expect(firstTrigger).toBeFocused();

    expect(fileRequests).toHaveLength(5);
    expect(fileRequests.every((request) => request.sessionId === 'thread-preview')).toBe(true);
    expect(fileRequests.every((request) => request.authorization === 'Bearer workspace-preview-token')).toBe(true);
    expect(fileRequests.some((request) => request.path.includes('..') || request.path.includes('%'))).toBe(false);

    const exportRequestsBefore = fileRequests.length;
    const exportResult = await page.evaluate(async () => {
      const runExport = (window as unknown as {
        runWorkspaceImageExport: () => Promise<{ parts: number; width: number; height: number; fileName: string }>;
      }).runWorkspaceImageExport;
      return runExport();
    });
    expect(exportResult.parts).toBe(1);
    expect(exportResult.width).toBe(2160);
    expect(exportResult.height).toBeGreaterThan(2500);
    expect(exportResult.fileName).toMatch(/^ink-memory-Workspace-export-thread-p\.png$/);
    const exportRequests = fileRequests.slice(exportRequestsBefore);
    expect(exportRequests).toHaveLength(5);
    expect(exportRequests.every((request) => request.sessionId === 'thread-preview')).toBe(true);
    expect(exportRequests.every((request) => request.authorization === 'Bearer workspace-preview-token')).toBe(true);
    expect(exportRequests.map((request) => request.path).sort()).toEqual([
      'files/fashion_flux2.png',
      'files/fashion_qwen.webp',
      'files/missing.png',
      'files/corrupt.png',
      'files/中文 fashion_zimage.png',
    ].sort());
    await expect(page.getByRole('img', { name: 'Exported Workspace conversation' })).toBeVisible();
    await page.screenshot({ path: 'output/playwright/workspace-uri-export.png' });
    const exportDownloadPromise = page.waitForEvent('download');
    await page.evaluate(async () => {
      await (window as unknown as { downloadWorkspaceImageExport: () => Promise<void> }).downloadWorkspaceImageExport();
    });
    const exportDownload = await exportDownloadPromise;
    expect(exportDownload.suggestedFilename()).toBe(exportResult.fileName);
    await page.evaluate(() => {
      (window as unknown as { releaseWorkspaceImageExport: () => void }).releaseWorkspaceImageExport();
    });

    const requestsBeforeRetry = fileRequests.length;
    await page.getByRole('button', { name: 'Retry' }).click();
    await expect(page.locator('img[data-workspace-file-state="success"]')).toHaveCount(4);
    expect(fileRequests).toHaveLength(requestsBeforeRetry + 1);

    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Workspace report' }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('report.pdf');
    await expect(page.getByText('Download started.')).toBeVisible();

    const requestsBeforeReload = fileRequests.length;
    await page.reload();
    await expect(page.locator('img[data-workspace-file-state="success"]')).toHaveCount(4);
    expect(fileRequests.length).toBe(requestsBeforeReload + 5);

    await page.evaluate(async () => {
      await (window as unknown as { setPreviewPresentation: () => Promise<void> }).setPreviewPresentation();
    });
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await page.setViewportSize({ width: 360, height: 740 });
    const narrowTrigger = page.locator('[data-markdown-media-kind="workspace-image"] .markdown-media-block__action[aria-haspopup="dialog"]').first();
    const narrowThumbnailBox = await page.locator('[data-markdown-media-kind="workspace-image"] .workspace-image-reference__trigger').first().boundingBox();
    expect(narrowThumbnailBox).not.toBeNull();
    expect(narrowThumbnailBox?.width).toBeLessThanOrEqual(329);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await narrowTrigger.click();
    const narrowDialog = page.getByRole('dialog', { name: /大图预览 · Flux\.2 Dev/ });
    await expect(narrowDialog).toBeVisible();
    await expect(narrowDialog.getByRole('button', { name: '缩小' })).toBeVisible();
    await expect(narrowDialog.getByRole('button', { name: '放大' })).toBeVisible();
    const narrowDialogBox = await narrowDialog.boundingBox();
    expect(narrowDialogBox).not.toBeNull();
    expect(narrowDialogBox?.width).toBe(360);
    expect(narrowDialogBox?.height).toBe(740);
    await page.screenshot({ path: 'output/playwright/workspace-uri-preview-narrow.png' });
    await page.getByRole('button', { name: '关闭图片预览' }).click();
    await expect(narrowTrigger).toBeFocused();

    workspaceEnabled = false;
    const requestsBeforeDisabledReload = fileRequests.length;
    await page.reload();
    await expect(page.locator('[data-workspace-file-state="disabled"]')).toHaveCount(7);
    await expect(page.locator('[data-workspace-file-state="invalid"]')).toHaveCount(1);
    expect(fileRequests).toHaveLength(requestsBeforeDisabledReload);
    expect(expectedFileFailureDiagnostics).toHaveLength(4);
    expect(diagnostics).toEqual([]);
  } finally {
    await server.close();
  }
});
