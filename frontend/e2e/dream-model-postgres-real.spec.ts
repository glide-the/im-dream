// Opt-in isolated real browser: Vite UI -> Dream FastAPI -> PostgreSQL -> local Gateway stub.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DREAM_PG_QA === '1';
const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:4177';
const BACKEND_API_BASE = process.env.INK_REAL_DREAM_API_BASE ?? 'http://127.0.0.1:18765';
const BACKEND_ROOT = resolve(process.cwd(), '../backend');
const PYTHON = resolve(BACKEND_ROOT, '.venv/bin/python');
const TEST_EMAIL = 'ink-dream-round-20260810@example.invalid';
const BALANCED_ALIAS = process.env.INK_E2E_BALANCED_ALIAS ?? 'dream-balanced';
const FAST_ALIAS = process.env.INK_E2E_FAST_ALIAS ?? 'dream-fast';
const VITE_CLIENT_WITHOUT_HMR = `
const hotContext = { data: {}, accept() {}, acceptExports() {}, decline() {}, dispose() {}, invalidate() {}, off() {}, on() {}, prune() {}, send() {} };
export function createHotContext() { return hotContext; }
export function updateStyle(id, css) { let style = document.querySelector('style[data-vite-dev-id="' + id + '"]'); if (!style) { style = document.createElement('style'); style.setAttribute('data-vite-dev-id', id); document.head.appendChild(style); } style.textContent = css; }
export function removeStyle(id) { document.querySelector('style[data-vite-dev-id="' + id + '"]')?.remove(); }
export function injectQuery(url) { return url; }
`;

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(!ENABLED, 'Set INK_REAL_DREAM_PG_QA=1 for the isolated PostgreSQL/Gateway-stub lane.');

function createToken(): string {
  const source = [
    'import auth, database, sys',
    'db = database.get_db()',
    'user = db.execute("SELECT id, email FROM users WHERE email = %s AND status = \'active\'", (sys.argv[1],)).fetchone()',
    'db.close()',
    "assert user is not None, 'isolated E2E actor missing'",
    "print(auth.create_access_token(user['id'], user['email']))",
  ].join('; ');
  return execFileSync(PYTHON, ['-c', source, TEST_EMAIL], {
    cwd: BACKEND_ROOT,
    encoding: 'utf-8',
  }).trim();
}

function collectDiagnostics(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (
      message.type() === 'error'
      && !message.text().startsWith('Failed to load resource:')
    ) diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) {
      diagnostics.push(`http ${response.status()}: ${response.url()}`);
    }
  });
  return diagnostics;
}

test('real Dream BFF persists only a live platform alias and restores it on mobile', async ({ page }) => {
  const diagnostics = collectDiagnostics(page);
  const putBodies: unknown[] = [];
  const browserApiRequests: string[] = [];
  const token = createToken();
  const resetResponse = await page.request.put(`${BACKEND_API_BASE}/api/system-config`, {
    headers: { authorization: `Bearer ${token}` },
    data: { model: BALANCED_ALIAS },
  });
  expect(resetResponse.status()).toBe(200);
  page.on('request', (request) => {
    if (request.url().includes('/api/')) browserApiRequests.push(request.url());
    if (request.method() === 'PUT' && request.url() === `${WEB_BASE}/api/system-config`) {
      putBodies.push(request.postDataJSON());
    }
  });
  await page.addInitScript(({ accessToken }) => {
    localStorage.setItem('auth_token', accessToken);
    localStorage.setItem('migration_completed', 'true');
  }, { accessToken: token });
  await page.route(`${WEB_BASE}/@vite/client`, (route) => route.fulfill({
    status: 200,
    contentType: 'text/javascript',
    body: VITE_CLIENT_WITHOUT_HMR,
  }));
  await page.route(`${WEB_BASE}/e2e/dream-model-postgres-real`, (route) => route.fulfill({
    status: 200,
    contentType: 'text/html',
    body: '<!doctype html><html lang="zh-CN"><head><script type="module">import { injectIntoGlobalHook } from "/@react-refresh"; injectIntoGlobalHook(window); window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => (type) => type;</script><script type="module" src="/@vite/client"></script><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/modelSettingsHarness.tsx"></script></body></html>',
  }));

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${WEB_BASE}/e2e/dream-model-postgres-real`);
  expect(await page.evaluate(async () => (
    (await import('/src/lib/apiBase.ts')).getApiBase()
  ))).toBe('');
  await expect.poll(() => browserApiRequests).toContain(
    `${WEB_BASE}/api/gateway/models`,
  );
  const catalogResponse = await page.request.get(`${BACKEND_API_BASE}/api/gateway/models`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(catalogResponse.status()).toBe(200);
  const catalog = await catalogResponse.json() as {
    data: Array<{ modelAlias: string; callable: boolean }>;
    defaultModelAlias: string | null;
  };
  expect(catalog).toMatchObject({ defaultModelAlias: BALANCED_ALIAS });
  expect(catalog.data.map((model) => model.modelAlias)).toEqual([
    BALANCED_ALIAS,
    FAST_ALIAS,
  ]);
  expect(catalog.data.every((model) => model.callable)).toBe(true);
  expect(diagnostics).toEqual([]);
  await expect(page.getByRole('radio', { name: /Dream Balanced/ })).toBeVisible();
  const saveResponse = page.waitForResponse((response) => (
    response.url() === `${WEB_BASE}/api/system-config`
    && response.request().method() === 'PUT'
    && response.status() === 200
  ));
  await page.getByRole('radio', { name: /Dream Fast/ }).check();
  await saveResponse;
  expect(putBodies).toEqual([{ model: FAST_ALIAS }]);
  expect(JSON.stringify(putBodies)).not.toMatch(/provider|secret|token|api.?key|dsn/i);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByRole('radio', { name: /Dream Fast/ })).toBeChecked();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  expect(diagnostics).toEqual([]);
});
