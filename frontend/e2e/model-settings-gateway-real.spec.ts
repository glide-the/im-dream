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
const ADMIN_BASE = process.env.E2E_ADMIN_BASE ?? 'http://127.0.0.1:3010';
const BACKEND_ROOT = resolve(process.cwd(), '../backend');
const PYTHON = resolve(BACKEND_ROOT, '.venv/bin/python');
const TEST_EMAIL = 'codex-free-round55@ink-memory.test';
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
test.describe.configure({ mode: 'serial' });
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

function resetLocalTestModelSelection(): void {
  const source = [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import database, sys',
    'db = database.get_db()',
    "user = db.execute(\"SELECT id FROM users WHERE email = %s AND status = 'active'\", (sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'local gateway E2E user not found'",
    "database.save_system_config(user['id'], {'model': ''})",
  ].join('; ');
  execFileSync(PYTHON, ['-c', source, TEST_EMAIL], {
    cwd: BACKEND_ROOT,
    stdio: 'ignore',
  });
}

function collectDiagnostics(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const errorText = request.failure()?.errorText ?? 'failed';
    // React StrictMode cancels the first effect pass in development. A later
    // successful response for the same real endpoint remains required below.
    if (errorText !== 'net::ERR_ABORTED') {
      diagnostics.push(`${errorText}: ${request.url()}`);
    }
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
    resetLocalTestModelSelection();
    const token = createTestToken();
    await page.addInitScript(({ token: value }) => {
      localStorage.setItem('auth_token', value);
      localStorage.setItem('migration_completed', 'true');
    }, { token });
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
    const catalog = await (await catalogResponse).json() as {
      data: Array<{ modelAlias: string; displayName: string; callable: boolean; availability: string }>;
      defaultModelAlias: string | null;
    };
    expect(catalog.data).toHaveLength(3);
    expect(catalog.defaultModelAlias).toBe('deepseek-v4-flash');
    expect(catalog.data.find((model) => model.modelAlias === 'deepseek-v4-flash')).toMatchObject({ callable: true, availability: 'included' });
    expect(catalog.data.find((model) => model.modelAlias === 'deepseek-v4-pro')).toMatchObject({ callable: true, availability: 'included' });
    expect(catalog.data.find((model) => model.modelAlias === 'hy-preview')).toMatchObject({ callable: true, availability: 'included' });
    const freeModel = page.getByRole('radio', { name: catalog.data.find((model) => model.modelAlias === 'deepseek-v4-flash')?.displayName });
    const unboundModel = page.getByRole('radio', { name: catalog.data.find((model) => model.modelAlias === 'deepseek-v4-pro')?.displayName });
    const hyModel = page.getByRole('radio', { name: catalog.data.find((model) => model.modelAlias === 'hy-preview')?.displayName });
    await expect(freeModel).toBeVisible();
    await expect(unboundModel).toBeEnabled();
    await expect(hyModel).toBeEnabled();
    await expect(page.getByText('平台维护中')).toHaveCount(0);
    const saveResponse = page.waitForResponse((response) => (
      response.url().endsWith('/api/system-config')
      && response.request().method() === 'PUT'
      && response.status() === 200
    ));
    await hyModel.check();
    await saveResponse;
    await expect(hyModel).toBeChecked();
    await expect(page.getByText('模型已保存，将用于新对话。')).toBeVisible();
    await expect(page.getByText('平台模型目录暂不可用，请稍后重试。')).toHaveCount(0);
    await expect(page.getByText('GPT-4.1')).toHaveCount(0);
    await expect(page.getByText('Claude Sonnet')).toHaveCount(0);
    await freeModel.focus();
    await expect(freeModel).toBeFocused();

    const horizontalOverflow = await page.evaluate(() => (
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
    ));
    expect(horizontalOverflow).toBe(false);
    expect(diagnostics).toEqual([]);
    await page.screenshot({ path: test.info().outputPath(`settings-${viewport.name}-${viewport.width}x${viewport.height}.png`), fullPage: true });
  });

  test(`real Product plans and Free allowance render without mocks (${viewport.name})`, async ({ page }) => {
    test.setTimeout(60_000);
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const diagnostics = collectDiagnostics(page);
    const token = createTestToken();
    await page.addInitScript(({ token: value }) => {
      localStorage.setItem('auth_token', value);
      localStorage.setItem('migration_completed', 'true');
    }, { token });

    const plansResponse = page.waitForResponse((response) => (
      response.url().includes('/api/story-workspace/subscription/plans') && response.status() === 200
    ));
    await page.goto(`${WEB_BASE}/story-workspace/subscription`);
    const plansPayload = await (await plansResponse).json() as {
      data: Array<{ planCode: string; available: boolean; versionStatus: string | null }>;
    };
    expect(plansPayload.data.map((plan) => plan.planCode).sort()).toEqual(['dream', 'free', 'is-dreaming']);
    expect(plansPayload.data.find((plan) => plan.planCode === 'free')).toMatchObject({ available: true, versionStatus: 'published' });
    expect(plansPayload.data.find((plan) => plan.planCode === 'dream')).toMatchObject({ available: false, versionStatus: 'draft' });
    expect(plansPayload.data.find((plan) => plan.planCode === 'is-dreaming')).toMatchObject({ available: false, versionStatus: 'draft' });
    await page.getByRole('tab', { name: '可选套餐' }).click();
    const planSection = page.getByRole('tabpanel', { name: '可选套餐' });
    await expect(planSection.getByText('Free', { exact: true })).toBeVisible();
    await expect(planSection.getByText('Dream', { exact: true })).toBeVisible();
    await expect(planSection.getByText('is Dreaming', { exact: true })).toBeVisible();
    const unavailableLabels = planSection.getByText('暂不可开通', { exact: true });
    await expect(unavailableLabels.first()).toBeVisible();
    expect(await unavailableLabels.evaluateAll((elements) => (
      elements.filter((element) => (element as HTMLElement).offsetParent !== null).length
    ))).toBe(2);
    await expect(planSection.getByText(/每月 100,000 Token/).first()).toBeVisible();
    const horizontalOverflow = await page.evaluate(() => (
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
    ));
    expect(horizontalOverflow).toBe(false);
    expect(diagnostics).toEqual([]);
    await page.screenshot({ path: test.info().outputPath(`subscription-${viewport.name}-${viewport.width}x${viewport.height}.png`), fullPage: true });
  });
}

test('Dream user bearer cannot access the Admin model registry', async ({ page }) => {
  const token = createTestToken();
  const response = await page.request.get(`${ADMIN_BASE}/api/admin/models?page=1&pageSize=1`, {
    headers: { authorization: `Bearer ${token}` },
    maxRedirects: 0,
  });
  expect([401, 403]).toContain(response.status());
});
