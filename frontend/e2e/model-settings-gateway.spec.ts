import { expect, test, type Route } from '@playwright/test';

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

test('platform Gateway catalog drives model selection and persists only alias', async ({ page }) => {
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
      { modelAlias: 'deepseek-v4-flash', displayName: 'DeepSeek V4 Flash', protocol: 'anthropic', capabilities: { tools: true }, gatewayScopes: ['messages:create'], contextWindow: 128000, maxOutputTokens: 8192 },
      { modelAlias: 'hy-preview', displayName: 'HY Preview', protocol: 'openai', capabilities: { tools: true }, gatewayScopes: ['messages:create'], contextWindow: 200000, maxOutputTokens: 16384 },
    ],
  }));
  await page.route(`${WEB_BASE}/api/system-config`, async (route) => {
    if (route.request().method() === 'PUT') {
      const patch = route.request().postDataJSON() as Record<string, unknown>;
      updates.push(patch);
      await json(route, { success: true, data: { model: patch.model, provider: 'gateway', workspace_enabled: true } });
      return;
    }
    await json(route, { model: 'deepseek-v4-flash', provider: 'gateway', workspace_enabled: true });
  });

  await page.goto(`${WEB_BASE}/e2e/model-settings-harness`);
  const select = page.getByLabel('平台 Gateway 模型');
  await expect(select).toHaveValue('deepseek-v4-flash');
  await expect(select.locator('option')).toHaveText([
    'DeepSeek V4 Flash · deepseek-v4-flash',
    'HY Preview · hy-preview',
  ]);
  await expect(page.getByText(/上下文 128,000 Token/)).toBeVisible();
  await select.selectOption('hy-preview');
  await expect(page.getByText(/新 Claude Agent 对话将通过 Gateway 使用该模型/)).toBeVisible();
  expect(updates.at(-1)).toEqual({ model: 'hy-preview' });
  expect(JSON.stringify(updates)).not.toMatch(/provider|secret|api.?key/i);
  await expect(page.getByText('GPT-4.1')).toHaveCount(0);
  await expect(page.getByText('Claude Sonnet')).toHaveCount(0);
});
