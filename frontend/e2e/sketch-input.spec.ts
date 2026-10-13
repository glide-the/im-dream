// [Input] Production AIInputDock, SketchInputDialog, upload hook and toAttachment, with isolated HTTP/send boundary fixtures.
// [Output] Local Chrome technical journeys for drawing, PNG/upload recovery, message DTOs and responsive accessibility.
// [Pos] Provider-free sketch-input verification; no database or real-model acceptance.
// [Sync] 2026-10-09: exercise real pointer input and authenticated upload headers without alternate production routes.
// [Sync] 2026-10-13: verify the source shell/layers/timeline, focus return, gestures and complete PNG upload/send recovery.

// Impact: local drafts/PNG change; existing Thread/session, upload DTO and story artifacts stay unchanged.
// This lane uses injected HTTP/send boundaries, no real database/account/model or normal service control.

import { expect, test, type Page } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { Buffer } from 'node:buffer';
import { createServer, type ViteDevServer } from 'vite';

test.use({ channel: 'chrome' });
const CSRF = 's'.repeat(43);
const HARNESS_PATH = '/sketch-input-technical';
const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

function moduleSource(options: { language: string; workspace: boolean; dark: boolean }) {
  return `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import i18n from '/app/_dream/i18n.ts';
    import { loadBrowserSession } from '/app/_dream/lib/browserSession.ts';
    import AIInputDock from '/app/_dream/components/chat/AIInputDock.tsx';
    import { toAttachment } from '/app/_dream/components/chat/AIInputDock.helpers.ts';
    import FileMessagePart from '/app/_dream/components/chat/FileMessagePart.tsx';
    import '/app/_dream/styles/tokens.css';
    import '/app/_dream/index.css';
    await loadBrowserSession();
    await i18n.changeLanguage('${options.language}');
    document.documentElement.setAttribute('data-theme', '${options.dark ? 'dark' : 'light'}');
    window.sketchMessages = [];
    function Harness() {
      const [messages, setMessages] = useState([]);
      const [reject, setReject] = useState(false);
      const [disabled, setDisabled] = useState(false);
      const [thread, setThread] = useState('sketch-owned-fixture');
      return React.createElement('main', { style: { maxWidth: 760, margin: '0 auto', padding: 12 } },
        React.createElement('h1', {}, 'Sketch input technical journey'),
        React.createElement(AIInputDock, {
          mode: 'full', disabled, threadId: thread,
          workspaceEnabled: ${options.workspace}, workspaceSessionId: ${options.workspace ? "'sketch-owned-fixture'" : 'undefined'},
          onSendMessage: async (text, files = []) => {
            if (reject) throw new Error('Injected send rejection');
            const message = { text, attachments: files.map(toAttachment) };
            window.sketchMessages.push(message);
            setMessages(previous => [...previous, message]);
          },
        }),
        React.createElement('button', { onClick: () => setReject(value => !value), 'aria-pressed': reject }, 'Inject send rejection'),
        React.createElement('button', { onClick: () => setDisabled(value => !value) }, 'Toggle composer disabled'),
        React.createElement('button', { onClick: () => setThread('sketch-owned-next') }, 'Switch Thread'),
        React.createElement('output', { 'data-testid': 'sent-count' }, messages.length),
        ...messages.flatMap((message, i) => message.attachments.map((attachment, j) =>
          React.createElement(FileMessagePart, { key: i + ':' + j, isUserMessage: true,
            part: { type: 'file', filename: attachment.name, mediaType: attachment.type, url: attachment.url } }))),
      );
    }
    createRoot(document.getElementById('root')).render(React.createElement(Harness));
  `;
}

async function startHarness(page: Page, options: { language?: string; workspace?: boolean; dark?: boolean } = {}) {
  const state = {
    uploads: 0, workspaceWrites: 0, failUpload: false, malformedUpload: false, disconnectUpload: false,
    holdUpload: false, release: () => {}, png: Buffer.alloc(0),
    unexpected: [] as string[], errors: [] as string[], startupConsole: [] as string[],
  };
  page.on('pageerror', error => state.errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') state.startupConsole.push(message.text()); });
  await page.route('**/auth/session', route => route.fulfill({ json: {
    user: { id: '1', email: 'sketch@example.test', display_name: 'Sketch fixture', avatar_url: null,
      role: 'user', created_at: null }, csrf_token: CSRF,
  } }));
  await page.route('**/api/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    // Vite also serves source modules under app/_dream/api; intercept only public HTTP API paths.
    if (!path.startsWith('/api/')) return route.continue();
    if (path === '/api/storage') return route.fulfill({ json: { type: 'unknown', supportsDirectUpload: false, isConfigured: true } });
    if (path === '/api/system-config') return route.fulfill({ json: { data: { im_full_access_enabled: false, workspace_enabled: options.workspace ?? false } } });
    if (path === '/api/claude-agent/skill-commands') return route.fulfill({ json: { commands: [] } });
    if (/^\/api\/claude-agent\/threads\/sketch-owned-(fixture|next)\/plugin-load-receipt$/.test(path)) {
      return route.fulfill({ json: { thread_id: path.split('/')[4], deck_id: null,
        workspace_found: false, receipt: null, launch_manifest: null } });
    }
    if (path === '/api/workspace/files') {
      state.workspaceWrites++;
      expect(request.headers()['x-ink-csrf']).toBe(CSRF);
      expect(request.headers().authorization).toBeUndefined();
      return route.fulfill({ json: { files: [{ workspacePath: 'files/Sketch.png', savedAt: '2026-10-09T00:00:00Z', hash: 'fixture-png' }] } });
    }
    if (path === '/api/storage/upload') {
      state.uploads++;
      expect(request.headers()['x-ink-csrf']).toBe(CSRF);
      expect(request.headers().authorization).toBeUndefined();
      const body = request.postDataBuffer()!;
      expect(body.toString('latin1')).toContain('Content-Type: image/png');
      const start = body.indexOf(PNG_SIGNATURE);
      const end = body.indexOf(Buffer.from([0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130]), start);
      expect(start).toBeGreaterThanOrEqual(0);
      expect(end).toBeGreaterThan(start);
      state.png = body.subarray(start, end + 12);
      if (state.holdUpload) await new Promise<void>(resolve => { state.release = resolve; });
      if (state.disconnectUpload) return route.abort('failed');
      if (state.failUpload) return route.fulfill({ status: 403, json: { error: 'Injected upload denial' } });
      if (state.malformedUpload) return route.fulfill({ contentType: 'application/json', body: '{' });
      return route.fulfill({ json: { key: 'sketch-fixture/Sketch.png', metadata: { contentType: 'image/png', size: state.png.length } } });
    }
    if (path.startsWith('/api/storage/file/')) return route.fulfill({ contentType: 'image/png', body: state.png });
    state.unexpected.push(request.method() + ' ' + path);
    return route.fulfill({ status: 501, json: { error: 'Unexpected fixture request' } });
  });
  const server: ViteDevServer = await createServer({
    root: fileURLToPath(new URL('../', import.meta.url)), configFile: false, logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, strictPort: true },
    plugins: [{
      name: 'sketch-input-owned-technical-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== HARNESS_PATH) return next();
          try {
            response.setHeader('Content-Type', 'text/html');
            response.end(await vite.transformIndexHtml(HARNESS_PATH,
              '<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/sketch-fixture.js"></script></body></html>'));
          } catch (error) { next(error as Error); }
        });
      },
      resolveId: id => id === '/sketch-fixture.js' ? '\0sketch-fixture.js' : null,
      load: id => id === '\0sketch-fixture.js' ? moduleSource({ language: options.language ?? 'en', workspace: options.workspace ?? false, dark: options.dark ?? false }) : null,
    }],
  });
  await server.listen();
  try {
    const address = server.httpServer!.address();
    if (!address || typeof address === 'string') throw new Error('Sketch fixture port unavailable');
    await page.goto(`http://127.0.0.1:${address.port}${HARNESS_PATH}`);
    await expect(page.getByRole('button', { name: 'Add attachment', exact: true }).or(page.getByRole('button', { name: '添加附件', exact: true }))).toBeVisible();
    return { state, server };
  } catch (error) {
    await server.close();
    throw new Error(`Sketch harness startup failed: ${JSON.stringify({ pageErrors: state.errors, console: state.startupConsole, unexpected: state.unexpected })}`, { cause: error });
  }
}

async function openSketch(page: Page, chinese = false) {
  await page.getByRole('button', { name: chinese ? '添加附件' : 'Add attachment', exact: true }).click();
  await page.getByRole('button', { name: chinese ? '绘制草图' : 'Draw a sketch', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
}

async function line(page: Page) {
  const bounds = await page.locator('canvas').boundingBox();
  if (!bounds) throw new Error('Canvas is not visible');
  await page.mouse.move(bounds.x + bounds.width * .25, bounds.y + bounds.height * .4);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width * .75, bounds.y + bounds.height * .4, { steps: 16 });
  await page.mouse.up();
}

async function ink(page: Page) {
  return page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => {
    const data = canvas.getContext('2d')!.getImageData(0, 0, canvas.width, canvas.height).data;
    let count = 0;
    for (let i = 0; i < data.length; i += 4) if (data[i] < 255 || data[i + 1] < 255 || data[i + 2] < 255) count++;
    return count;
  });
}

test('draw, erase to blank, undo/redo, retain on close, clear/undo, upload and send PNG through existing DTO', async ({ page }) => {
  const { state, server } = await startHarness(page);
  try {
    await openSketch(page);
    const add = page.getByRole('button', { name: 'Add to message', exact: true });
    await expect(add).toBeDisabled();
    await line(page);
    const original = await ink(page);
    expect(original).toBeGreaterThan(0);
    await page.getByRole('button', { name: 'Eraser', exact: true }).click();
    await line(page);
    expect(await ink(page)).toBe(0);
    await expect(add).toBeDisabled();
    await page.getByRole('button', { name: 'Undo', exact: true }).click();
    expect(await ink(page)).toBe(original);
    await page.getByRole('button', { name: 'Redo', exact: true }).click();
    expect(await ink(page)).toBe(0);
    await page.getByRole('button', { name: 'Undo', exact: true }).click();
    await page.getByRole('button', { name: 'Back', exact: true }).last().click();
    await openSketch(page);
    expect(await ink(page)).toBe(original);
    await page.getByRole('button', { name: 'Clear', exact: true }).click();
    await expect(add).toBeDisabled();
    await page.getByRole('button', { name: 'Undo', exact: true }).click();
    expect(await ink(page)).toBe(original);
    state.holdUpload = true;
    await add.click();
    await expect(page.getByRole('dialog').getByRole('status').filter({ hasText: 'Adding…' })).toHaveText('Adding…');
    await expect(page.getByRole('button', { name: 'Send message', exact: true })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Adding…', exact: true })).toBeDisabled();
    await expect.poll(() => state.uploads).toBe(1);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeVisible();
    state.release();
    await expect(page.getByRole('dialog')).toBeHidden();
    expect(state.workspaceWrites).toBe(0);
    await expect(page.getByRole('img', { name: 'Sketch.png', exact: true })).toBeVisible();
    await expect.poll(() => page.getByRole('img', { name: 'Sketch.png', exact: true }).evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(900);
    const exportedInk = await page.getByRole('img', { name: 'Sketch.png', exact: true }).evaluate((img: HTMLImageElement) => {
      const decoded = document.createElement('canvas');
      decoded.width = img.naturalWidth;
      decoded.height = img.naturalHeight;
      const context = decoded.getContext('2d')!;
      context.drawImage(img, 0, 0);
      const pixels = context.getImageData(0, 0, decoded.width, decoded.height).data;
      let count = 0;
      for (let i = 0; i < pixels.length; i += 4) if (pixels[i] < 255 || pixels[i + 1] < 255 || pixels[i + 2] < 255) count++;
      return count;
    });
    expect(exportedInk).toBe(original);
    const editor = page.getByRole('textbox', { name: 'Chat input' });
    await editor.fill('Keep this layout, with the doorway on the left.');
    await page.getByRole('button', { name: 'Inject send rejection' }).click();
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    await expect(editor).toContainText('Keep this layout');
    await expect(page.getByRole('img', { name: 'Sketch.png', exact: true })).toBeVisible();
    await expect(page.getByTestId('sent-count')).toHaveText('0');
    await page.getByRole('button', { name: 'Inject send rejection' }).click();
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    const messages = await page.evaluate(() => (window as unknown as { sketchMessages: { text: string; attachments: { type: string; storageKey: string; url: string; workspacePath?: string }[] }[] }).sketchMessages);
    expect(messages[0].text).toContain('doorway');
    expect(messages[0].attachments[0]).toMatchObject({ type: 'image/png', storageKey: 'sketch-fixture/Sketch.png', uploadSource: 'click' });
    expect(messages[0].attachments[0].workspacePath).toBeUndefined();
    expect(messages[0].attachments[0].url).not.toContain('token=');
    await openSketch(page);
    expect(await ink(page)).toBe(0);
    expect(state.errors).toEqual([]);
    expect(state.unexpected).toEqual([]);
  } finally { state.release(); await server.close(); }
});

test('upload denial and malformed result keep the drawing, retry once and preserve Workspace metadata', async ({ page }) => {
  const { state, server } = await startHarness(page, { workspace: true });
  try {
    await openSketch(page);
    await line(page);
    const original = await ink(page);
    state.failUpload = true;
    await page.getByRole('button', { name: 'Add to message', exact: true }).click();
    await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Your drawing is kept');
    expect(await ink(page)).toBe(original);
    state.failUpload = false;
    state.disconnectUpload = true;
    await page.getByRole('button', { name: 'Add to message', exact: true }).click();
    await expect.poll(() => state.uploads).toBe(2);
    await expect(page.getByRole('button', { name: 'Add to message', exact: true })).toBeEnabled();
    expect(await ink(page)).toBe(original);
    state.disconnectUpload = false;
    state.malformedUpload = true;
    await page.getByRole('button', { name: 'Add to message', exact: true }).click();
    await expect.poll(() => state.uploads).toBe(3);
    await expect(page.getByRole('button', { name: 'Add to message', exact: true })).toBeEnabled();
    expect(await ink(page)).toBe(original);
    state.malformedUpload = false;
    await page.getByRole('button', { name: 'Add to message', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await expect(page.getByRole('img', { name: 'Sketch.png', exact: true })).toHaveCount(1);
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    const attachments = await page.evaluate(() => (window as unknown as { sketchMessages: { attachments: unknown[] }[] }).sketchMessages[0].attachments);
    expect(attachments).toHaveLength(1);
    expect(attachments[0]).toMatchObject({ workspacePath: 'files/Sketch.png', hash: 'fixture-png' });
    expect(state.uploads).toBe(4);
    expect(state.workspaceWrites).toBe(4);
    expect(state.errors).toEqual([]);
    expect(state.unexpected).toEqual([]);
  } finally { await server.close(); }
});

test('PNG export failure keeps editable strokes; a new stroke replaces redo history', async ({ page }) => {
  const { state, server } = await startHarness(page);
  try {
    await openSketch(page);
    await line(page);
    await page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => {
      const data = new DataTransfer();
      data.items.add(new File(['fixture'], 'unexpected.png', { type: 'image/png' }));
      canvas.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, clipboardData: data }));
      canvas.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: data }));
    });
    expect(state.uploads).toBe(0);
    await page.getByRole('button', { name: 'Clear', exact: true }).click();
    await page.getByRole('button', { name: 'Undo', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Redo', exact: true })).toBeEnabled();
    await line(page);
    await expect(page.getByRole('button', { name: 'Redo', exact: true })).toBeDisabled();
    const before = await ink(page);
    await page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => { canvas.toBlob = callback => callback(null); });
    await page.getByRole('button', { name: 'Add to message', exact: true }).click();
    await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Your drawing is kept');
    expect(await ink(page)).toBe(before);
    expect(state.uploads).toBe(0);
    await page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => { canvas.toBlob = HTMLCanvasElement.prototype.toBlob; });
    await page.getByRole('button', { name: 'Add to message', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await page.getByRole('button', { name: 'Toggle composer disabled' }).click();
    await expect(page.getByRole('button', { name: 'Add attachment', exact: true })).toBeDisabled();
    expect(state.errors).toEqual([]);
    expect(state.unexpected).toEqual([]);
  } finally { await server.close(); }
});

test('narrow Chinese dark dialog supports focus/Escape, touch drawing, removal and the old file chooser', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  const { state, server } = await startHarness(page, { language: 'zh', dark: true });
  try {
    const trigger = page.getByRole('button', { name: '添加附件', exact: true });
    await trigger.focus();
    await trigger.press('Enter');
    await expect(page.getByRole('button', { name: '上传文件', exact: true })).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(trigger).toBeFocused();
    await openSketch(page, true);
    await expect(page.getByRole('button', { name: '画笔', exact: true })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    const dialog = await page.getByRole('dialog').boundingBox();
    expect(dialog!.x).toBeGreaterThanOrEqual(0);
    expect(dialog!.x + dialog!.width).toBeLessThanOrEqual(360);
    const rect = (await page.locator('canvas').boundingBox())!;
    const touch = await page.context().newCDPSession(page);
    await touch.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: rect.x + rect.width * .25, y: rect.y + rect.height / 2 }] });
    await touch.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: rect.x + rect.width * .75, y: rect.y + rect.height / 2 }] });
    await touch.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await touch.detach();
    await expect(page.getByRole('button', { name: '添加到消息', exact: true })).toBeEnabled();
    await page.screenshot({ path: test.info().outputPath('sketch-narrow-dark-zh.png') });
    await page.keyboard.press('Escape');
    await expect(trigger).toBeFocused();
    await openSketch(page, true);
    expect(await ink(page)).toBeGreaterThan(0);
    await page.getByRole('button', { name: '添加到消息', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await page.getByRole('button', { name: '删除文件 草图.png', exact: true }).click();
    await expect(page.getByRole('img', { name: '草图.png', exact: true })).toHaveCount(0);
    await trigger.click();
    const chooser = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: '上传文件', exact: true }).click();
    await (await chooser).setFiles({ name: 'existing-image.png', mimeType: 'image/png', buffer: state.png });
    await expect(page.getByRole('button', { name: '发送消息', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: '发送消息', exact: true }).click();
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    expect(state.errors).toEqual([]);
    expect(state.unexpected).toEqual([]);
  } finally { await server.close(); }
});


function localImage(color: string, name = 'reference.svg') {
  return { name, mimeType: 'image/svg+xml', buffer: Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120"><rect width="120" height="120" fill="${color}"/></svg>`) };
}

async function importReference(page: Page, color: string) {
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Import image', exact: true }).click();
  await (await chooser).setFiles(localImage(color));
  await expect(page.getByRole('button', { name: 'Add to message', exact: true })).toBeEnabled();
  await expect(page.getByRole('dialog').getByRole('status').filter({ hasText: 'Loading image…' })).toHaveCount(0);
}

async function pixels(page: Page) {
  return page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => canvas.toDataURL());
}

test('import image, annotate and erase on its own layer, stable history/view, upload/send and downstream PNG', async ({ page }) => {
  const { state, server } = await startHarness(page, { workspace: true });
  try {
    await openSketch(page);
    await importReference(page, '#f04b36');
    const image = await pixels(page);
    const sample = await page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => {
      const ctx = canvas.getContext('2d')!;
      return { margin: [...ctx.getImageData(10, 300, 1, 1).data], center: [...ctx.getImageData(450, 450, 1, 1).data] };
    });
    expect(sample.margin).toEqual([255, 255, 255, 255]);
    expect(sample.center).toEqual([240, 75, 54, 255]);
    expect(state.uploads).toBe(0);
    await line(page);
    const annotated = await pixels(page);
    expect(annotated).not.toBe(image);
    await page.getByRole('button', { name: 'Eraser', exact: true }).click();
    await expect(page.getByLabel('Eraser size')).toHaveValue('28');
    await page.getByLabel('Eraser size').press('ArrowRight');
    await expect(page.getByLabel('Eraser size')).toHaveValue('29');
    await line(page);
    expect(await pixels(page)).toBe(image);
    await page.getByRole('button', { name: 'Undo', exact: true }).click();
    expect(await pixels(page)).toBe(annotated);
    await page.getByRole('button', { name: 'Redo', exact: true }).click();
    expect(await pixels(page)).toBe(image);
    await page.getByRole('button', { name: 'Undo', exact: true }).click();
    await page.getByRole('button', { name: 'Clear', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Add to message', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Undo', exact: true }).click();
    expect(await pixels(page)).toBe(annotated);
    await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
    await expect(page.getByRole('status', { name: 'Zoom', exact: true })).toHaveText('110%');
    await page.getByRole('button', { name: 'Move', exact: true }).click();
    const bounds = (await page.locator('.ink-sketch__viewport').boundingBox())!;
    await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
    await page.mouse.down();
    await page.mouse.move(bounds.x + bounds.width / 2 + 24, bounds.y + bounds.height / 2 + 12, { steps: 4 });
    await page.mouse.up();
    expect(await pixels(page)).toBe(annotated);
    await page.getByRole('button', { name: 'Reset view', exact: true }).click();
    expect(await pixels(page)).toBe(annotated);
    await page.getByRole('button', { name: 'Back', exact: true }).last().click();
    await openSketch(page);
    expect(await pixels(page)).toBe(annotated);
    await page.screenshot({ path: test.info().outputPath('package-image-charcoal-desktop.png') });
    await page.getByRole('button', { name: 'Add to message', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    expect(state.uploads).toBe(1);
    expect(state.workspaceWrites).toBe(1);
    await page.getByRole('textbox', { name: 'Chat input' }).fill('Use this marked reference.');
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    const displayed = page.locator('.file-message-part img');
    // Ground the existing downstream image by its ordinary filename rather than a new renderer.
    const png = page.getByRole('img', { name: 'Sketch.png', exact: true });
    await expect(png).toBeVisible();
    await expect.poll(() => png.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(900);
    const decoded = await png.evaluate((img: HTMLImageElement) => {
      const canvas = document.createElement('canvas'); canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
      canvas.getContext('2d')!.drawImage(img, 0, 0); return canvas.toDataURL();
    });
    expect(decoded).toBe(annotated);
    expect(await displayed.count()).toBeLessThanOrEqual(1);
    expect(state.errors).toEqual([]); expect(state.unexpected).toEqual([]);
  } finally { await server.close(); }
});

test('invalid image/oversize/decode cancellation preserve the draft; replacement and Thread switch follow history', async ({ page }) => {
  const { state, server } = await startHarness(page);
  try {
    await openSketch(page);
    await line(page);
    const original = await pixels(page);
    const input = page.getByRole('dialog').locator('input[type="file"]');
    await input.setInputFiles({ name: 'broken.png', mimeType: 'image/png', buffer: Buffer.from('not a PNG') });
    await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Could not load');
    expect(await pixels(page)).toBe(original);
    await input.setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('not an image') });
    await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Your drawing is kept');
    expect(await pixels(page)).toBe(original);
    await page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => {
      const transfer = new DataTransfer();
      transfer.items.add(new File([new Uint8Array(50 * 1024 * 1024 + 1)], 'large.png', { type: 'image/png' }));
      canvas.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: transfer }));
    });
    await expect(page.getByRole('dialog').getByRole('alert')).toContainText('upload size limit');
    expect(await pixels(page)).toBe(original);
    await input.setInputFiles([]);
    expect(await pixels(page)).toBe(original);
    await importReference(page, '#235ed3');
    const blue = await pixels(page);
    await importReference(page, '#d44e25');
    const red = await pixels(page);
    expect(red).not.toBe(blue);
    await page.getByRole('button', { name: 'Undo', exact: true }).click();
    expect(await pixels(page)).toBe(blue);
    await page.getByRole('button', { name: 'Redo', exact: true }).click();
    expect(await pixels(page)).toBe(red);
    // Hold only the native decode completion event to exercise unmount/abort; no production fallback.
    await page.evaluate(() => {
      const owned = window as unknown as { NativeSketchImage: typeof Image; releaseSketchDecode?: () => void };
      owned.NativeSketchImage = window.Image;
      window.Image = function () {
        const image = new owned.NativeSketchImage();
        let handler: ((event: Event) => void) | null = null;
        Object.defineProperty(image, 'onload', { configurable: true,
          get: () => handler,
          set: (next: ((event: Event) => void) | null) => {
            handler = next;
            if (next) image.addEventListener('load', () => { owned.releaseSketchDecode = () => next.call(image, new Event('load')); }, { once: true });
          },
        });
        return image;
      } as unknown as typeof Image;
    });
    await input.setInputFiles(localImage('#40b863'));
    await expect(page.getByRole('dialog').getByRole('status').filter({ hasText: 'Loading image…' })).toHaveText('Loading image…');
    await expect.poll(() => page.evaluate(() => Boolean((window as unknown as { releaseSketchDecode?: () => void }).releaseSketchDecode))).toBe(true);
    await page.getByRole('button', { name: 'Back', exact: true }).last().click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await page.evaluate(() => {
      const owned = window as unknown as { NativeSketchImage: typeof Image; releaseSketchDecode?: () => void };
      window.Image = owned.NativeSketchImage; owned.releaseSketchDecode?.();
    });
    await openSketch(page);
    expect(await pixels(page)).toBe(red);
    await page.getByRole('button', { name: 'Back', exact: true }).last().click();
    await page.getByRole('button', { name: 'Switch Thread', exact: true }).click();
    await openSketch(page);
    expect(await ink(page)).toBe(0);
    await expect(page.getByRole('button', { name: 'Add to message', exact: true })).toBeDisabled();
    expect(state.uploads).toBe(0); expect(state.errors).toEqual([]); expect(state.unexpected).toEqual([]);
  } finally { await server.close(); }
});

test('pointer cancellation drops an unfinished stroke; narrow short-screen tools and primary action remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 480 });
  const { state, server } = await startHarness(page, { language: 'zh', dark: true });
  try {
    await openSketch(page, true);
    const canvas = page.locator('canvas');
    const box = (await canvas.boundingBox())!;
    await page.mouse.move(box.x + box.width / 3, box.y + box.height / 3);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * .6, box.y + box.height * .4);
    await expect(page.getByRole('button', { name: '添加到消息', exact: true })).toBeDisabled();
    await canvas.dispatchEvent('pointercancel', { pointerId: 1 });
    await page.mouse.up();
    expect(await ink(page)).toBe(0);
    await expect(page.getByRole('button', { name: '撤销', exact: true })).toBeDisabled();
    await line(page);
    const add = page.getByRole('button', { name: '添加到消息', exact: true });
    await expect(add).toBeEnabled();
    await expect(add).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    await page.screenshot({ path: test.info().outputPath('package-sketch-320x480-dark-zh.png') });
    await add.click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await page.getByRole('button', { name: '发送消息', exact: true }).click();
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    expect(state.errors).toEqual([]); expect(state.unexpected).toEqual([]);
  } finally { await server.close(); }
});


test('source layer toolbox and paper timeline restore snapshots; clearing history preserves editable image/ink layers', async ({ page }) => {
  const { state, server } = await startHarness(page, { workspace: true });
  try {
    await openSketch(page);
    await expect(page.getByRole('heading', { name: 'CHARCOAL NARRATIVE', exact: true })).toBeVisible();
    await importReference(page, '#f04b36');
    const image = await pixels(page);
    await line(page);
    const combined = await pixels(page);
    await page.getByRole('button', { name: 'Layers', exact: true }).click();
    await page.getByRole('button', { name: 'Image layer', exact: true }).click();
    const inkOnly = await pixels(page);
    expect(inkOnly).not.toBe(combined);
    await page.getByRole('button', { name: 'Sketch layer', exact: true }).click();
    expect(await ink(page)).toBe(0);
    await expect(page.getByRole('button', { name: 'Add to message', exact: true })).toBeDisabled();
    await line(page);
    expect(await ink(page)).toBe(0); // Hidden target cannot accumulate invisible strokes.
    await page.getByRole('button', { name: 'Image layer', exact: true }).click();
    expect(await pixels(page)).toBe(image);
    await page.getByRole('button', { name: 'Sketch layer', exact: true }).click();
    expect(await pixels(page)).toBe(combined);
    await page.getByRole('button', { name: 'Timeline', exact: true }).click();
    const timeline = page.getByRole('complementary', { name: 'Timeline', exact: true });
    await expect(timeline).toBeVisible();
    await expect(timeline.getByRole('img', { name: /^Sketch fragments \d+$/ })).toHaveCount(2);
    await page.screenshot({ path: test.info().outputPath('source-shell-layer-toolbox-timeline.png') });
    await timeline.getByRole('button', { name: 'Restore step 1: Import image', exact: true }).click();
    await expect(timeline).toBeHidden();
    await expect(page.getByRole('button', { name: 'Timeline', exact: true })).toBeFocused();
    expect(await pixels(page)).toBe(image);
    await page.getByRole('button', { name: 'Redo', exact: true }).click();
    expect(await pixels(page)).toBe(combined);
    await page.getByRole('button', { name: 'Timeline', exact: true }).click();
    await timeline.getByRole('button', { name: 'Clear timeline', exact: true }).click();
    await expect(timeline.getByText('No history recorded yet', { exact: true })).toBeVisible();
    await timeline.getByRole('button', { name: 'Close timeline', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Timeline', exact: true })).toBeFocused();
    expect(await pixels(page)).toBe(combined);
    await expect(page.getByRole('button', { name: 'Undo', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Eraser', exact: true }).click();
    await page.getByRole('button', { name: 'Erase image', exact: true }).click();
    await line(page);
    const erasedImage = await pixels(page);
    expect(erasedImage).not.toBe(combined);
    expect(await page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => [...canvas.getContext('2d')!.getImageData(450, 230, 1, 1).data])).toEqual([255,255,255,255]);
    await page.getByRole('button', { name: 'Undo', exact: true }).click();
    expect(await pixels(page)).toBe(combined);
    await page.getByRole('button', { name: 'Redo', exact: true }).click();
    expect(await pixels(page)).toBe(erasedImage);
    await page.getByRole('button', { name: 'Erase sketch', exact: true }).click();
    await line(page);
    await page.getByRole('button', { name: 'Add to message', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    expect(state.uploads).toBe(1); expect(state.errors).toEqual([]); expect(state.unexpected).toEqual([]);
  } finally { await server.close(); }
});

test('two-finger view gestures do not draw; narrow paper timeline stays bounded and restores focus', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const { state, server } = await startHarness(page, { language: 'zh', dark: true });
  try {
    await openSketch(page, true);
    await line(page);
    const before = await pixels(page);
    const box = (await page.locator('canvas').boundingBox())!;
    const touch = await page.context().newCDPSession(page);
    await touch.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [
      { x: box.x + box.width * .35, y: box.y + box.height * .6, id: 1 },
      { x: box.x + box.width * .65, y: box.y + box.height * .6, id: 2 },
    ] });
    await touch.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [
      { x: box.x + box.width * .25, y: box.y + box.height * .6, id: 1 },
      { x: box.x + box.width * .75, y: box.y + box.height * .6, id: 2 },
    ] });
    await touch.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await touch.detach();
    await expect(page.getByRole('status', { name: '缩放', exact: true })).not.toHaveText('100%');
    expect(await pixels(page)).toBe(before);
    await page.getByRole('button', { name: '复位', exact: true }).click();
    expect(await pixels(page)).toBe(before);
    await page.getByRole('button', { name: '绘图历史', exact: true }).click();
    const timeline = page.getByRole('complementary', { name: '绘图历史', exact: true });
    await expect(timeline).toBeVisible();
    await expect(timeline.getByRole('button', { name: '关闭绘图历史', exact: true })).toBeFocused();
    const bounds = (await timeline.boundingBox())!;
    expect(bounds.x).toBeGreaterThanOrEqual(0); expect(bounds.x + bounds.width).toBeLessThanOrEqual(390);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    await page.screenshot({ path: test.info().outputPath('source-shell-narrow-timeline.png') });
    await page.keyboard.press('Escape');
    await expect(timeline).toBeHidden(); await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('button', { name: '绘图历史', exact: true })).toBeFocused();
    await page.getByRole('button', { name: '添加到消息', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await page.getByRole('button', { name: '发送消息', exact: true }).click();
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    expect(state.errors).toEqual([]); expect(state.unexpected).toEqual([]);
  } finally { await server.close(); }
});
