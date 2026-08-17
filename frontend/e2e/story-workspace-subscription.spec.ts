// [Input] Vite UI plus deterministic Product BFF context/plan fixtures.
// [Output] Desktop/mobile tab, focus, hierarchy, and overflow evidence.
// [Pos] Focused component regression; the separate gateway-real suite verifies the unmocked Product API.

import { expect, test, type Page, type Route } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';
const VITE_CLIENT_WITHOUT_HMR = `
const hotContext = {
  data: {},
  accept() {},
  acceptExports() {},
  decline() {},
  dispose() {},
  invalidate() {},
  off() {},
  on() {},
  prune() {},
  send() {},
};
export function createHotContext() { return hotContext; }
export function updateStyle(id, css) {
  let style = document.querySelector('style[data-vite-dev-id="' + id + '"]');
  if (!style) {
    style = document.createElement('style');
    style.setAttribute('data-vite-dev-id', id);
    document.head.appendChild(style);
  }
  style.textContent = css;
}
export function removeStyle(id) {
  document.querySelector('style[data-vite-dev-id="' + id + '"]')?.remove();
}
export function injectQuery(url) { return url; }
`;

test.use({ channel: 'chromium' });

async function fulfill(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

function plan(input: {
  code: string;
  name: string;
  eyebrow: string;
  note: string;
  details: string[];
  available: boolean;
  current?: boolean;
}) {
  return {
    planCode: input.code,
    planName: input.name,
    eyebrow: input.eyebrow,
    note: input.note,
    details: input.details,
    description: null,
    planVersionId: input.available ? `pv_${input.code}` : `pv_${input.code}_draft`,
    version: 1,
    versionStatus: input.available ? 'published' : 'draft',
    billingCycle: 'monthly',
    monthlyAllowanceTokens: input.available ? 100_000 : null,
    monthlyPriceMicrousd: input.available ? 0 : null,
    currency: 'USD',
    available: input.available,
    unavailableReason: input.available ? null : 'commercial_parameters_pending',
    entitlements: input.current ? [{
      gatewayScopes: ['messages:create'],
      modelAliases: ['free-agent'],
      rpmLimit: 20,
      dailyTokenLimit: null,
      storageBytes: null,
    }] : [],
    eligibility: {
      eligible: input.available,
      reasonCode: input.available ? null : 'PLAN_NOT_AVAILABLE',
      appliesAt: null,
    },
    availableActions: [],
  };
}

async function installProductMocks(page: Page) {
  await page.route(`${WEB_BASE}/api/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/me') {
      await fulfill(route, { id: 7, email: 'subscription-e2e@example.test', display_name: 'Subscription E2E' });
      return;
    }
    if (url.pathname === '/api/story-workspace/subscription/context') {
      await fulfill(route, {
        data: {
          canonicalUser: { id: '7' },
          subscription: {
            id: 'sub_free_7',
            status: 'active',
            version: 1,
            cycleAnchorAt: '2026-08-09T10:00:00Z',
            currentPeriodNumber: 0,
            currentPeriodStart: '2026-08-09T10:00:00Z',
            currentPeriodEnd: '2026-09-09T10:00:00Z',
            renewalEnabled: true,
            cancelAtPeriodEnd: false,
            pendingChange: null,
            allowedActions: [],
          },
          planVersion: {
            planCode: 'free',
            planName: 'Free',
            planVersionId: 'pv_free',
            version: 1,
            billingCycle: 'monthly',
            monthlyAllowanceTokens: 100_000,
            monthlyPriceMicrousd: 0,
            currency: 'USD',
          },
          entitlements: [{
            gatewayScope: 'messages:create',
            modelAliases: ['free-agent'],
            rpmLimit: 20,
            dailyTokenLimit: null,
            storageBytes: null,
          }],
          allowance: {
            unit: 'tokens',
            granted: 100_000,
            reserved: 1_000,
            consumed: 24_000,
            remaining: 75_000,
            resetsAt: '2026-09-09T10:00:00Z',
          },
          asOf: '2026-08-09T10:05:00Z',
        },
        meta: { requestId: 'req_context' },
      });
      return;
    }
    if (url.pathname === '/api/story-workspace/subscription/plans') {
      await fulfill(route, {
        data: [
          plan({
            code: 'free',
            name: 'Free',
            eyebrow: 'A quiet beginning',
            note: '从一段创作目标开始',
            details: ['查看已有 Deck', '发起有限次数的 Dream', '保留最近的工作台入口'],
            available: true,
            current: true,
          }),
          plan({
            code: 'dream',
            name: 'Dream',
            eyebrow: 'For active stories',
            note: '给持续创作留出空间',
            details: ['更充足的 Dream 创作额度', '更长的 Dream Agent 对话历史'],
            available: false,
          }),
          plan({
            code: 'is-dreaming',
            name: 'is Dreaming',
            eyebrow: 'For ongoing worlds',
            note: '为长期作品准备的工作台',
            details: ['面向多部作品的持续创作支持', '更完整的 Deck 与工作台协作空间'],
            available: false,
          }),
        ],
        meta: { total: 3, page: 1, pageSize: 20, requestId: 'req_plans' },
      });
      return;
    }
    await fulfill(route, { error: { code: 'NOT_FOUND', message: 'Not found' } }, 404);
  });
}

async function preparePage(page: Page) {
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (!/react-grab\.com|fonts\.googleapis\.com|fonts\.gstatic\.com/.test(url)) {
      diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'subscription-e2e-token');
    localStorage.setItem('migration_completed', 'true');
  });
  await installProductMocks(page);
  await page.route(`${WEB_BASE}/@vite/client`, async (route) => {
    await route.fulfill({ status: 200, contentType: 'text/javascript', body: VITE_CLIENT_WITHOUT_HMR });
  });
  await page.route(`${WEB_BASE}/e2e/subscription-harness`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<!doctype html><html lang="zh-CN"><head><script type="module">import { injectIntoGlobalHook } from "/@react-refresh"; injectIntoGlobalHook(window); window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => (type) => type;</script><script type="module" src="/@vite/client"></script><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><main id="root"></main><script type="module" src="/e2e/fixtures/storyWorkspaceSubscriptionHarness.tsx"></script></body></html>',
    });
  });
  await page.goto(`${WEB_BASE}/e2e/subscription-harness`);
  await expect(page).toHaveURL(/\/e2e\/subscription-harness$/);
  await expect(page.getByRole('heading', { name: 'Free', level: 1 })).toBeVisible();
  return diagnostics;
}

test('1440×1000 keeps one calm panel visible and exposes real plan copy on demand', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const diagnostics = await preparePage(page);

  await expect(page.getByRole('heading', { name: 'Free', level: 1 })).toBeFocused();
  await expect(page.getByRole('tab', { name: '订阅信息' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('heading', { name: 'Free', level: 2 })).toBeVisible();
  await expect(page.getByText('查看已有 Deck')).toBeVisible();
  await expect(page.getByRole('progressbar')).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath('subscription-desktop-info-1440x1000.png'), fullPage: true });

  await page.getByRole('tab', { name: '我的额度' }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '24000');
  await expect(page.getByRole('heading', { name: /75,000 Token/ })).toBeVisible();
  await expect(page.getByText('1,000', { exact: true })).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath('subscription-desktop-allowance-1440x1000.png'), fullPage: true });

  await page.getByRole('button', { name: '查看可选套餐' }).click();
  await expect(page.getByRole('tab', { name: '可选套餐' })).toBeFocused();
  const planPanel = page.getByRole('tabpanel', { name: '可选套餐' });
  await expect(planPanel.getByText('Free', { exact: true })).toBeVisible();
  await expect(planPanel.getByText('Dream', { exact: true })).toBeVisible();
  await expect(planPanel.getByText('is Dreaming', { exact: true })).toBeVisible();
  await expect(planPanel.getByText('暂不可开通')).toHaveCount(2);

  const visibleCopy = (await page.locator('body').innerText()).toLocaleLowerCase();
  for (const forbidden of ['plan version', 'gateway', 'model alias', 'rpm', 'request id', 'checkout', 'invoice']) {
    expect(visibleCopy).not.toContain(forbidden);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('subscription-desktop-1440x1000.png'), fullPage: true });
  expect(diagnostics).toEqual([]);
});

test('390×844 is overflow-free and supports keyboard tab navigation', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const diagnostics = await preparePage(page);

  const infoTab = page.getByRole('tab', { name: '订阅信息' });
  await infoTab.focus();
  await infoTab.press('ArrowRight');
  await expect(page.getByRole('tab', { name: '我的额度' })).toBeFocused();
  await expect(page.getByRole('progressbar')).toBeVisible();
  await page.getByRole('tab', { name: '我的额度' }).press('End');
  await expect(page.getByRole('tab', { name: '可选套餐' })).toBeFocused();
  await expect(page.getByRole('tabpanel', { name: '可选套餐' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  await page.screenshot({ path: testInfo.outputPath('subscription-mobile-390x844.png'), fullPage: true });
  expect(diagnostics).toEqual([]);
});
