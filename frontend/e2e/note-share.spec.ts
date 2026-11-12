// [Sync] 2026-11-12: await the completed clipboard side effect after the server-side state recheck.
// [Sync] 2026-11-12: scope Vite optimization artifacts to this isolated share validation.
// [Sync] 2026-11-12: exercise database tokens, stable publication keys and current-status reads.
// [Input] Production note share dialog, public prose presenter, native intent parser and actual PNG capture.
// [Output] Explicit link/image choices, publication/copy recovery, privacy, download and responsive evidence.
// [Pos] Provider-free technical browser validation. Session is synthetic; Project/Episode/Artifact/Run/Hook/Thread are out of scope.
// [Impact] Only fixture share state/files change; existing services, accounts and PostgreSQL remain outside this test.
import {test, expect, type Page} from '@playwright/test';
import {createServer} from 'vite';
import type {NoteShareFixture} from './fixtures/note-share-harness';
type FixtureWindow = Window & {noteShareFixture: NoteShareFixture; bad?: unknown};
import {fileURLToPath} from 'node:url';
import {projectNote} from '../app/_dream/components/notes/noteShare';
import {isWritingShareRequest, isWritingShareResult} from '../app/_dream/components/Editor/WritingShare.protocol';

const token = 's'.repeat(43), shareId = '22222222-2222-4222-8222-222222222222', sharePath = '/share/' + token;
const shareMeta = {id: shareId, kind: 'note', source_id: 'private-session', title: '河边的记录', path: sharePath, status: 'active', source_available: true, created_at: '2026-11-12T00:00:00Z', revoked_at: null};
test.use({channel: 'chrome'});
test.setTimeout(90_000);
let server: Awaited<ReturnType<typeof createServer>>, base: string;
const errors = new WeakMap<Page, string[]>();
test.beforeAll(async () => {
  server = await createServer({root: fileURLToPath(new URL('../', import.meta.url)), configFile: false, cacheDir: fileURLToPath(new URL('../test-results/external-sharing/cache/note-share', import.meta.url)), logLevel: 'silent',
    server: {host: '127.0.0.1', port: 0}, optimizeDeps: {noDiscovery: true, include: ['react', 'react-dom', 'react-dom/client', 'react/jsx-runtime', 'react/jsx-dev-runtime', 'react-markdown', 'remark-gfm', 'ai', 'zod', 'i18next', 'react-i18next', 'html-to-image']},
    plugins: [{name: 'note-share-harness', configureServer(vite) {vite.middlewares.use(async (req, res, next) => {
      if (req.url !== '/note-share-harness') return next();
      res.setHeader('Content-Type', 'text/html');
      res.end(await vite.transformIndexHtml('/note-share-harness', '<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/note-share-harness.tsx"></script></body></html>'));
    });}}]});
  await server.listen(); base = server.resolvedUrls!.local[0];
});
test.afterAll(async () => {await server?.close();});
test.beforeEach(async ({page}) => {
  errors.set(page, []);
  page.on('pageerror', error => errors.get(page)!.push(error.message));
  page.on('console', message => {if (message.type() === 'error') {
    // This exact publication response is the intentional saved-content conflict scenario.
    if (message.location().url.includes('/api/sessions/private-session/share') && message.text().includes('409')) return;
    errors.get(page)!.push(message.text());
  }});
  page.on('requestfailed', request => {if (!request.url().includes('/api/sessions/') && request.failure()?.errorText !== 'net::ERR_ABORTED') errors.get(page)!.push(request.url());});
  await page.route('**/api/shares/' + shareId, route => route.fulfill({json: {share: shareMeta}}));
  await page.goto(base + 'note-share-harness');
  await expect(page.getByRole('button', {name: 'Share current note'})).toBeVisible();
});
test.afterEach(async ({page}) => {expect(errors.get(page)).toEqual([]);});
async function facts(page: Page) {return page.evaluate(() => {const value = (window as FixtureWindow).noteShareFixture; return {saves: value.saves, copied: value.copied};});}
const open = (page: Page) => page.getByRole('button', {name: 'Share current note'}).click();

test('prose projection excludes embedded conversations and Agent suggestions', () => {
  expect(projectNote({id: 'private', cells: [{type: 'text', content: 'Visible'}, {type: 'widget', content: 'Secret'}, {type: 'writing-suggestion', content: 'Secret'}, {type: 'text', content: '😀'}]})).toEqual({sessionId: 'private', snapshot: {title: 'Visible', created_at: null, paragraphs: ['Visible', '😀']}});
  expect(isWritingShareRequest({requestId: 'request', kind: 'copy', text: 'https://example.com' + sharePath})).toBe(true);
  expect(isWritingShareRequest({requestId: 'request', kind: 'copy', text: 'javascript:alert(1)'})).toBe(false);
  expect(isWritingShareRequest({requestId: 'request', kind: 'images', images: [{name: '../secret.png', base64: 'iVBORw=='}]})).toBe(false);
  expect(isWritingShareResult({requestId: 'request', status: 'completed'})).toBe(true);
});

test('sharing offers both choices and publishes only on link click with saved-content verification', async ({page}) => {
  const requests: {body: {content_sha256: string; request_key: string}; csrf?: string}[] = [];
  await page.route('**/api/sessions/private-session/share', async route => {requests.push({body: route.request().postDataJSON(), csrf: route.request().headers()['x-ink-csrf']}); await route.fulfill({json: {share: shareMeta, path: sharePath, url: 'https://notes.example' + sharePath}});});
  await open(page);
  const dialog = page.getByRole('dialog', {name: 'Share note'});
  await expect(dialog.getByRole('button', {name: 'Copy link'})).toBeVisible();
  await expect(dialog.getByRole('button', {name: 'Export as image'})).toBeEnabled();
  expect((await facts(page)).saves).toBe(0); expect(requests).toEqual([]);
  await dialog.getByRole('button', {name: 'Copy link'}).click();
  await expect(dialog.getByRole('button', {name: 'Link copied'})).toBeVisible();
  expect(requests).toHaveLength(1); expect(requests[0].csrf).toBe('c'.repeat(43)); expect(Object.keys(requests[0].body).sort()).toEqual(['content_sha256', 'request_key']); expect(requests[0].body.content_sha256).toMatch(/^[0-9a-f]{64}$/);
  await dialog.getByRole('button', {name: 'Link copied'}).click();
  expect((await facts(page)).saves).toBe(1); expect(requests).toHaveLength(1);
  await expect.poll(async () => (await facts(page)).copied).toEqual(['https://notes.example' + sharePath, 'https://notes.example' + sharePath]);
});

test('clipboard failure retains a selectable link without publishing another snapshot', async ({page}) => {
  await page.evaluate(() => {(window as FixtureWindow).noteShareFixture.failCopy = true;});
  await page.route('**/api/sessions/*/share', route => route.fulfill({json: {share: shareMeta, path: sharePath, url: null}}));
  await open(page); await page.getByRole('button', {name: 'Copy link', exact: true}).click();
  await expect(page.getByRole('alert')).toHaveText('Select the link below to copy it.');
  await expect(page.getByRole('textbox', {name: 'Share link'})).toHaveValue(base + 'share/' + token);
});

test('save failure and changed saved prose keep sharing retryable', async ({page}) => {
  let publications = 0;
  await page.route('**/api/sessions/*/share', async route => {publications++; await route.fulfill({status: 409, json: {detail: 'Note changed'}});});
  await page.evaluate(() => {(window as FixtureWindow).noteShareFixture.failSave = true;});
  await open(page); await page.getByRole('button', {name: 'Copy link', exact: true}).click();
  await expect(page.getByRole('alert')).toHaveText('The note could not be shared. Please retry.'); expect(publications).toBe(0);
  await page.evaluate(() => {(window as FixtureWindow).noteShareFixture.failSave = false;});
  await page.getByRole('button', {name: 'Copy link', exact: true}).click();
  await expect(page.getByRole('alert')).toHaveText('This note has changed. Close sharing and open it again.'); expect(publications).toBe(1);
  await expect(page.getByRole('textbox', {name: 'Share link'})).toHaveCount(0);
});

test('actual image preview downloads a PNG without publishing or exposing private cells', async ({page}) => {
  await open(page); await page.getByRole('button', {name: 'Export as image'}).click();
  const download = page.getByRole('button', {name: 'Download image', exact: true});
  await expect(download).toBeEnabled({timeout: 60_000});
  expect((await facts(page)).saves).toBe(0);
  const image = page.getByRole('dialog').getByRole('img').first();
  expect(await image.evaluate(async element => {const img = element as HTMLImageElement; await img.decode(); return {width: img.naturalWidth, height: img.naturalHeight};})).toMatchObject({width: 2160});
  const pending = page.waitForEvent('download'); await download.click(); const file = await pending;
  expect(file.suggestedFilename()).toMatch(/^kastention-.*\.png$/); expect(await file.failure()).toBeNull();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  expect(await page.evaluate(() => (window as FixtureWindow).bad)).toBeUndefined();
  await expect(page.getByText('private chat')).toHaveCount(0);
});

test('narrow Chinese presentation keeps choices in the viewport and empty notes disabled', async ({page}) => {
  await page.setViewportSize({width: 390, height: 740});
  await page.getByRole('button', {name: '中文'}).click();
  await page.evaluate(() => {(window as FixtureWindow).noteShareFixture.empty = true; document.documentElement.dataset.theme = 'dark';});
  await open(page);
  const dialog = page.getByRole('dialog', {name: '分享笔记'});
  await expect(dialog.getByRole('button', {name: '复制链接', exact: true})).toBeDisabled();
  await expect(dialog.getByRole('button', {name: /导出图片/})).toBeDisabled();
  const bounds = await dialog.boundingBox(); expect(bounds!.x).toBeGreaterThanOrEqual(0); expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390); expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(740);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
