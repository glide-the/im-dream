// [Input] Browser-mocked Gateway catalog and system-config API responses.
// [Output] Model Settings browser contracts for default selection, explicit save,
//          stale catalog recovery, and honest empty state.
// [Pos] Mocked-browser model selection acceptance in frontend/e2e
// [Sync] 2026-08-14: new users with no saved alias select Admin's live default.

import { expect, test, type Page, type Route } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';
const VITE_CLIENT_WITHOUT_HMR = `
const hotContext = { data: {}, accept() {}, acceptExports() {}, decline() {}, dispose() {}, invalidate() {}, off() {}, on() {}, prune() {}, send() {} };
export function createHotContext() { return hotContext; }
export function updateStyle(id, css) { let style = document.querySelector('style[data-vite-dev-id="' + id + '"]'); if (!style) { style = document.createElement('style'); style.setAttribute('data-vite-dev-id', id); document.head.appendChild(style); } style.textContent = css; }
export function removeStyle(id) { document.querySelector('style[data-vite-dev-id="' + id + '"]')?.remove(); }
export function injectQuery(url) { return url; }
`;

test.use({ channel: 'chromium' });

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

function collectDiagnostics(
  page: Page,
  expectedHttp: ReadonlySet<string> = new Set(),
): string[] {
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
    const url = new URL(response.url());
    const signature = `${response.status()} ${url.pathname}`;
    if (response.status() >= 400 && !expectedHttp.has(signature)) {
      diagnostics.push(`http: ${signature}`);
    }
  });
  return diagnostics;
}

test('platform Gateway default selects an unsaved new-user model and persists only an explicit change', async ({ page }) => {
  const diagnostics = collectDiagnostics(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  const updates: Array<Record<string, unknown>> = [];
  await page.addInitScript(() => localStorage.setItem('auth_token', 'model-e2e-token'));
  await page.route(`${WEB_BASE}/@vite/client`, (route) => route.fulfill({ status: 200, contentType: 'text/javascript', body: VITE_CLIENT_WITHOUT_HMR }));
  await page.route(`${WEB_BASE}/e2e/model-settings-harness`, (route) => route.fulfill({
    status: 200,
    contentType: 'text/html',
    body: '<!doctype html><html lang="zh-CN"><head><script type="module">import { injectIntoGlobalHook } from "/@react-refresh"; injectIntoGlobalHook(window); window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => (type) => type;</script><script type="module" src="/@vite/client"></script><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/modelSettingsHarness.tsx"></script></body></html>',
  }));
  await page.route(`${WEB_BASE}/api/gateway/models`, (route) => json(route, {
    data: [
      { modelAlias: 'deepseek-v4-flash', displayName: 'DeepSeek V4 Flash', protocol: 'anthropic', capabilities: { tools: true }, contextWindow: 128000, maxOutputTokens: 8192, enabled: true, callable: true, availability: 'included', requiredPlanCode: 'free', upgradeHint: null },
      { modelAlias: 'dream-fast', displayName: 'Dream Fast', protocol: 'anthropic', capabilities: { tools: true }, contextWindow: 128000, maxOutputTokens: 8192, enabled: true, callable: true, availability: 'included', requiredPlanCode: 'free', upgradeHint: null },
      { modelAlias: 'hy-preview', displayName: 'HY Preview', protocol: 'openai', capabilities: { tools: true }, contextWindow: 200000, maxOutputTokens: 16384, enabled: true, callable: false, availability: 'upgrade_required', requiredPlanCode: 'dream', upgradeHint: '升级 Dream 后可用' },
    ],
    defaultModelAlias: 'deepseek-v4-flash',
  }));
  await page.route(`${WEB_BASE}/api/system-config`, async (route) => {
    if (route.request().method() === 'PUT') {
      const patch = route.request().postDataJSON() as Record<string, unknown>;
      updates.push(patch);
      await json(route, { success: true, data: { model: patch.model, provider: 'gateway', workspace_enabled: true } });
      return;
    }
    await json(route, { provider: 'gateway', workspace_enabled: true });
  });

  await page.goto(`${WEB_BASE}/e2e/model-settings-harness`);
  const current = page.getByRole('radio', { name: /DeepSeek V4 Flash/ });
  await expect(current).toBeChecked();
  expect(updates).toEqual([]);
  await expect(page.getByRole('radio', { name: /HY Preview/ })).toBeDisabled();
  await expect(page.getByText(/需要 dream 套餐/i)).toBeVisible();
  await page.getByRole('radio', { name: /Dream Fast/ }).check();
  await expect(page.getByText('模型已保存，将用于新对话。')).toBeVisible();
  expect(updates.at(-1)).toEqual({ model: 'dream-fast' });
  expect(JSON.stringify(updates)).not.toMatch(/provider|secret|api.?key/i);
  await expect(page.getByText('GPT-4.1')).toHaveCount(0);
  await expect(page.getByText('Claude Sonnet')).toHaveCount(0);
  expect(diagnostics).toEqual([]);
});

test('catalog refresh failure preserves last-good models and exposes retry', async ({ page }) => {
  const diagnostics = collectDiagnostics(page, new Set([
    '409 /api/system-config',
    '503 /api/gateway/models',
  ]));
  await page.setViewportSize({ width: 390, height: 844 });
  let catalogReads = 0;
  await page.addInitScript(() => localStorage.setItem('auth_token', 'model-e2e-token'));
  await page.route(`${WEB_BASE}/@vite/client`, (route) => route.fulfill({ status: 200, contentType: 'text/javascript', body: VITE_CLIENT_WITHOUT_HMR }));
  await page.route(`${WEB_BASE}/e2e/model-settings-harness`, (route) => route.fulfill({
    status: 200,
    contentType: 'text/html',
    body: '<!doctype html><html lang="zh-CN"><head><script type="module">import { injectIntoGlobalHook } from "/@react-refresh"; injectIntoGlobalHook(window); window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => (type) => type;</script><script type="module" src="/@vite/client"></script><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/modelSettingsHarness.tsx"></script></body></html>',
  }));
  await page.route(`${WEB_BASE}/api/gateway/models`, async (route) => {
    catalogReads += 1;
    if (catalogReads > 1) {
      await json(route, { detail: { code: 'GATEWAY_UNAVAILABLE' } }, 503);
      return;
    }
    await json(route, {
      data: [
        { modelAlias: 'deepseek-v4-flash', displayName: 'DeepSeek V4 Flash', protocol: 'anthropic', capabilities: { tools: true }, contextWindow: 128000, maxOutputTokens: 8192, enabled: true, callable: true, availability: 'included', requiredPlanCode: 'free', upgradeHint: null },
        { modelAlias: 'dream-fast', displayName: 'Dream Fast', protocol: 'anthropic', capabilities: { tools: true }, contextWindow: 128000, maxOutputTokens: 8192, enabled: true, callable: true, availability: 'included', requiredPlanCode: 'free', upgradeHint: null },
      ],
      defaultModelAlias: 'deepseek-v4-flash',
    });
  });
  await page.route(`${WEB_BASE}/api/system-config`, async (route) => {
    if (route.request().method() === 'PUT') {
      await json(route, { detail: { code: 'GATEWAY_MODEL_SELECTION_STALE' } }, 409);
      return;
    }
    await json(route, { model: 'deepseek-v4-flash', provider: 'gateway', workspace_enabled: true });
  });

  await page.goto(`${WEB_BASE}/e2e/model-settings-harness`);
  await expect(page.getByRole('radio', { name: /DeepSeek V4 Flash/ })).toBeChecked();
  await page.getByRole('radio', { name: /Dream Fast/ }).click();
  await expect(page.getByRole('alert')).toContainText('平台模型目录暂不可用');
  await expect(page.getByRole('alert')).toContainText('上次成功加载');
  await expect(page.getByRole('radio', { name: /DeepSeek V4 Flash/ })).toBeVisible();
  await expect(page.getByRole('button', { name: '重新加载模型' })).toBeVisible();
  expect(catalogReads).toBe(2);
  expect(diagnostics).toEqual([]);
});

test('an empty live catalog renders an honest empty state without saving a fallback model', async ({ page }) => {
  const diagnostics = collectDiagnostics(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  let modelWrites = 0;
  await page.addInitScript(() => localStorage.setItem('auth_token', 'model-e2e-token'));
  await page.route(`${WEB_BASE}/@vite/client`, (route) => route.fulfill({ status: 200, contentType: 'text/javascript', body: VITE_CLIENT_WITHOUT_HMR }));
  await page.route(`${WEB_BASE}/e2e/model-settings-harness`, (route) => route.fulfill({
    status: 200,
    contentType: 'text/html',
    body: '<!doctype html><html lang="zh-CN"><head><script type="module">import { injectIntoGlobalHook } from "/@react-refresh"; injectIntoGlobalHook(window); window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => (type) => type;</script><script type="module" src="/@vite/client"></script><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/modelSettingsHarness.tsx"></script></body></html>',
  }));
  await page.route(`${WEB_BASE}/api/gateway/models`, (route) => json(route, {
    data: [],
    defaultModelAlias: null,
  }));
  await page.route(`${WEB_BASE}/api/system-config`, async (route) => {
    if (route.request().method() === 'PUT') {
      modelWrites += 1;
      await json(route, { detail: { code: 'UNEXPECTED_MODEL_SAVE' } }, 409);
      return;
    }
    await json(route, { model: 'retired-model', provider: 'gateway', workspace_enabled: true });
  });

  await page.goto(`${WEB_BASE}/e2e/model-settings-harness`);
  await expect(page.getByRole('status')).toHaveText('平台尚未启用可展示的模型。');
  await expect(page.getByRole('radio')).toHaveCount(0);
  expect(modelWrites).toBe(0);
  expect(diagnostics).toEqual([]);
});
