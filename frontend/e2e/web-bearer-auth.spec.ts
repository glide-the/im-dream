// [Input] Actual Web credential owner/AuthProvider, BFF OAuth/proxy and Chat SSE transport.
// [Output] Isolated browser evidence for reopen/restart, cross-tab renewal/logout, login and private bytes.
// [Pos] Provider-free end-to-end technical validation; normal Admin/Python/database/model acceptance remains separate.
// Scope: authentication and transport change. Project, Episode, canonical Artifact,
// Run-private .dream publication, after-turn Hook and PostgreSQL projection are out of scope.
// Shared Chat DTO, SSE decoder, Stop and final visible text must retain their behavior.
import { chromium, expect, test, type BrowserContext, type Page } from '@playwright/test';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { startWebBearerHarness } from './fixtures/web-bearer-harness';

test.use({ channel: 'chrome' });
test.describe.configure({ mode: 'serial' });
let harness: Awaited<ReturnType<typeof startWebBearerHarness>>;
const errors = new WeakMap<Page, string[]>();
test.beforeAll(async () => { harness = await startWebBearerHarness(); });
test.afterAll(async () => { await harness?.close(); });
function observe(page: Page, found: string[]) {
  errors.set(page, found);
  page.on('pageerror', error => found.push(error.name + ': ' + error.message));
  // Record only credential presence. Never retain header values, request bodies or OAuth callback queries.
  page.on('request', request => {
    const url = new URL(request.url());
    expect(url.searchParams.has('access_token') || url.searchParams.has('refresh_token') || url.searchParams.has('token')).toBe(false);
  });
}
test.beforeEach(async ({ page }) => {
  harness.state.reset(); observe(page, []);
});
test.afterEach(async ({ page }, info) => {
  const business = harness.state.requests.filter(request => request.path.startsWith('/api/') || request.path === '/auth/session');
  expect(business.length).toBeGreaterThan(0);
  expect(business.every(request => request.bearer && !request.cookie && !request.csrf)).toBe(true);
  expect(harness.state.resolves).toBe(0);
  expect(errors.get(page)).toEqual([]);
  await info.attach('web-bearer-network', { contentType: 'application/json', body: JSON.stringify({
    lane: 'isolated-provider-free', requests: harness.state.requests.filter(request => request.path !== '/auth/callback'),
    resolves: harness.state.resolves, grants: harness.state.grants, refreshes: harness.state.refreshes, revokes: harness.state.revokes,
  }, null, 2) });
});
async function login(page: Page) {
  await page.goto(harness.base + '/bearer-harness');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Sign in with Admin' }).click();
  await expect(page.getByRole('heading', { name: 'Admin authorization fixture' })).toBeVisible();
  await page.getByRole('link', { name: 'Continue test account' }).click();
  await expect(page.getByRole('heading', { name: 'Signed in Web OAuth fixture' })).toBeVisible();
  expect(harness.state.codeChecks).toBe(1);
  expect(await page.evaluate(() => Object.keys(JSON.parse(localStorage.getItem('ink-dream-web-oauth')!)).sort())).toEqual(['refresh_token', 'session_id']);
  expect(await page.evaluate(() => sessionStorage.getItem('ink-dream-web-oauth'))).toBeNull();
  expect((await page.context().cookies(harness.base)).filter(cookie => cookie.name.includes('ink-dream'))).toEqual([]);
}

test('login, private image/download/upload, Chat SSE/Stop, reload and logout use Bearer with zero resolves', async ({ page }) => {
  await login(page);
  await expect(page.getByRole('img', { name: 'Private image' })).toHaveAttribute('src', /^blob:/);
  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download file' }).click();
  expect((await download).suggestedFilename()).toBe('note.txt');
  await page.getByRole('button', { name: 'Upload file' }).click();
  await expect(page.getByLabel('Result')).toHaveText('Uploaded');
  await page.getByRole('button', { name: 'Send chat' }).click();
  await expect(page.getByLabel('Chat')).toHaveText('你好，浏览器。');
  await page.getByRole('button', { name: 'Stop chat' }).click();
  await expect(page.getByLabel('Result')).toHaveText('Stopped');
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Signed in Web OAuth fixture' })).toBeVisible();
  expect(harness.state.refreshes).toBe(1);
  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  expect(harness.state.revokes).toBe(1);
  expect(await page.evaluate(() => sessionStorage.getItem('ink-dream-web-oauth'))).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem('ink-dream-web-oauth'))).toBeNull();
  await page.reload(); await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
});

test('expired token coalesces concurrent renewal and rejects a revoked refresh grant', async ({ page }) => {
  harness.state.lifetime = 1; await login(page);
  // Wait on the actual issuance lifetime, then dispatch through the normal visible controls.
  const expires = Date.now() + 1_050;
  await expect.poll(() => Date.now(), { intervals: [100], timeout: 3_000 }).toBeGreaterThan(expires);
  harness.state.lifetime = 300;
  await page.getByRole('button', { name: 'Load concurrently' }).click();
  await expect(page.getByLabel('Result')).toHaveText('12 requests succeeded');
  expect(harness.state.refreshes).toBe(1);
  harness.state.accessInvalid = true; harness.state.revoked = true;
  await page.getByRole('button', { name: 'Load concurrently' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  expect(harness.state.refreshes).toBe(2);
  expect(await page.evaluate(() => sessionStorage.getItem('ink-dream-web-oauth'))).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem('ink-dream-web-oauth'))).toBeNull();
});

test('temporary refresh and revoke failures preserve recoverable state and allow a later retry', async ({ page }) => {
  await login(page);
  harness.state.accessInvalid = true; harness.state.refreshUnavailable = true;
  await page.getByRole('button', { name: 'Load concurrently' }).click();
  await expect(page.getByLabel('Result')).toHaveText('Request failed');
  await expect(page.getByRole('heading', { name: 'Signed in Web OAuth fixture' })).toBeVisible();
  harness.state.refreshUnavailable = false;
  await page.getByRole('button', { name: 'Load concurrently' }).click();
  await expect(page.getByLabel('Result')).toHaveText('12 requests succeeded');
  harness.state.revokeUnavailable = true;
  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page.getByRole('alert')).toHaveText('Unable to log out. Please try again.');
  await expect(page.getByRole('heading', { name: 'Signed in Web OAuth fixture' })).toBeVisible();
  harness.state.revokeUnavailable = false;
  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
});

test('closing Chrome preserves the login; fresh tabs serialize rotation and share logout across restart', async ({ page }) => {
  const directory = await mkdtemp(join(tmpdir(), 'ink-web-oauth-reopen-'));
  let active: BrowserContext | undefined;
  const open = async () => {
    active = await chromium.launchPersistentContext(directory, { channel: 'chrome', headless: true, viewport: { width: 1280, height: 800 } });
    const first = active.pages()[0] ?? await active.newPage();
    observe(first, errors.get(page)!);
    active.on('page', next => observe(next, errors.get(page)!));
    return first;
  };
  try {
    const initial = await open();
    await login(initial);
    await active!.close(); active = undefined;
    const reopened = await open();
    await reopened.goto(harness.base + '/bearer-harness');
    await expect(reopened.getByRole('heading', { name: 'Signed in Web OAuth fixture' })).toBeVisible();
    expect(harness.state.grants).toBe(1); expect(harness.state.refreshes).toBe(1);
    const second = await active!.newPage(), third = await active!.newPage();
    await Promise.all([second, third].map(next => next.goto(harness.base + '/bearer-harness')));
    for (const next of [second, third]) await expect(next.getByRole('heading', { name: 'Signed in Web OAuth fixture' })).toBeVisible();
    expect(harness.state.refreshes).toBe(3);
    await second.getByRole('button', { name: 'Load concurrently' }).click();
    await expect(second.getByLabel('Result')).toHaveText('12 requests succeeded');
    await third.getByRole('button', { name: 'Log out' }).click();
    for (const next of [reopened, second, third]) await expect(next.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
    expect(harness.state.revokes).toBe(1);
    await active!.close(); active = undefined;
    const signedOut = await open();
    await signedOut.goto(harness.base + '/bearer-harness');
    await expect(signedOut.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
    expect(harness.state.grants).toBe(1); expect(harness.state.refreshes).toBe(3);
  } finally {
    await active?.close();
    await rm(directory, { recursive: true, force: true });
  }
});

test('an existing tab refresh credential migrates to durable storage on reload', async ({ page }) => {
  await login(page);
  await page.evaluate(() => {
    const saved = JSON.parse(localStorage.getItem('ink-dream-web-oauth')!);
    sessionStorage.setItem('ink-dream-web-oauth', JSON.stringify({ refresh_token: saved.refresh_token }));
    localStorage.removeItem('ink-dream-web-oauth');
  });
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Signed in Web OAuth fixture' })).toBeVisible();
  expect(harness.state.grants).toBe(1); expect(harness.state.refreshes).toBe(1);
  expect(await page.evaluate(() => Object.keys(JSON.parse(localStorage.getItem('ink-dream-web-oauth')!)).sort())).toEqual(['refresh_token', 'session_id']);
  expect(await page.evaluate(() => sessionStorage.getItem('ink-dream-web-oauth'))).toBeNull();
});
