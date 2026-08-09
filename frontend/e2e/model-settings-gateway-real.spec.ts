// Real local browser contract for Settings -> Dream BFF -> Admin Gateway.
// Opt-in only: it uses the named local PostgreSQL E2E identity provisioned by
// `pnpm gateway:provision-local-dream` in ink-admin-memory.

// @ts-expect-error Playwright E2E runs in Node outside the browser tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E runs in Node outside the browser tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_GATEWAY_QA === '1';
const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';
const BACKEND_ROOT = resolve(process.cwd(), '../backend');
const PYTHON = resolve(BACKEND_ROOT, '.venv/bin/python');
const TEST_EMAIL = 'codex-gateway-e2e@ink-memory.test';
const VITE_CLIENT_WITHOUT_HMR = `
const hotContext = { data: {}, accept() {}, acceptExports() {}, decline() {}, dispose() {}, invalidate() {}, off() {}, on() {}, prune() {}, send() {} };
export function createHotContext() { return hotContext; }
export function updateStyle(id, css) { let style = document.querySelector('style[data-vite-dev-id="' + id + '"]'); if (!style) { style = document.createElement('style'); style.setAttribute('data-vite-dev-id', id); document.head.appendChild(style); } style.textContent = css; }
export function removeStyle(id) { document.querySelector('style[data-vite-dev-id="' + id + '"]')?.remove(); }
export function injectQuery(url) { return url; }
`;
const HARNESS_HTML = `<!doctype html>
<html lang="zh-CN"><head>
<script type="module">import { injectIntoGlobalHook } from '/@react-refresh'; injectIntoGlobalHook(window); window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => (type) => type;</script>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head>
<body><div id="root"></div><script type="module" src="/e2e/fixtures/modelSettingsHarness.tsx"></script></body></html>`;

test.use({ channel: 'chromium' });
test.skip(!ENABLED, 'Set INK_REAL_GATEWAY_QA=1 after provisioning the local Gateway E2E identity.');

function createTestToken(): string {
  const source = [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import auth, database, sys',
    'db = database.get_db()',
    "user = db.execute(\"SELECT id, email FROM users WHERE email = %s AND status = 'active'\", (sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'local gateway E2E user not found'",
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
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'}: ${request.url()}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) {
      diagnostics.push(`http ${response.status()}: ${response.url()}`);
    }
  });
  return diagnostics;
}

for (const viewport of [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`real Gateway model is visible in Settings (${viewport.name})`, async ({ page }) => {
    test.setTimeout(60_000);
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const diagnostics = collectDiagnostics(page);
    const token = createTestToken();
    await page.addInitScript((value) => {
      localStorage.setItem('auth_token', value);
      localStorage.setItem('migration_completed', 'true');
    }, token);
    await page.route(`${WEB_BASE}/e2e/model-settings-gateway-real`, (route) => {
      return route.fulfill({ status: 200, contentType: 'text/html', body: HARNESS_HTML });
    });
    await page.route(`${WEB_BASE}/@vite/client`, (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'text/javascript',
        body: VITE_CLIENT_WITHOUT_HMR,
      });
    });

    const catalogResponse = page.waitForResponse((response) => (
      response.url().endsWith('/api/gateway/models') && response.status() === 200
    ));
    await page.goto(`${WEB_BASE}/e2e/model-settings-gateway-real`);
    await catalogResponse;

    await expect(page.getByRole('heading', { name: 'AI 模型配置' })).toBeVisible();
    const select = page.getByLabel('平台 Gateway 模型');
    await expect(select).toBeVisible();
    await expect(select).toHaveValue('deepseek-v4-flash');
    await expect(select.locator('option')).toHaveCount(1);
    await expect(select.locator('option')).toContainText('deepseek-v4-flash');
    await expect(page.getByText('平台模型目录暂不可用，请稍后重试。')).toHaveCount(0);
    await expect(page.getByText('GPT-4.1')).toHaveCount(0);
    await expect(page.getByText('Claude Sonnet')).toHaveCount(0);
    await select.focus();
    await expect(select).toBeFocused();

    const horizontalOverflow = await page.evaluate(() => (
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
    ));
    expect(horizontalOverflow).toBe(false);
    expect(diagnostics).toEqual([]);
  });
}
