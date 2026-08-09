// [Input] Vite UI plus deterministic mocks for the five same-origin Product BFF routes.
// [Output] Desktop/mobile rendering, command receipt, refetch, focus, and overflow evidence.
// [Pos] Focused mocked-browser E2E for the monthly Token subscription page.

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

function planSummary(planVersionId = 'pv_creator', planName = 'Creator', version = 4, tokens = 1_000_000) {
  return {
    planCode: planName.toLocaleLowerCase(),
    planName,
    planVersionId,
    version,
    billingCycle: 'monthly',
    monthlyAllowanceTokens: tokens,
  };
}

function allowance() {
  return {
    unit: 'tokens',
    granted: 1_000_000,
    reserved: 1_000,
    consumed: 240_000,
    remaining: 759_000,
    resetsAt: '2026-09-09T10:00:00Z',
  };
}

async function fulfill(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function installProductMocks(page: Page) {
  let pendingChange = false;
  let contextReads = 0;
  const executed: Array<{ body: Record<string, unknown>; idempotencyKey: string | null }> = [];

  await page.route(`${WEB_BASE}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === '/api/me') {
      await fulfill(route, { id: 7, email: 'subscription-e2e@example.test', display_name: 'Subscription E2E' });
      return;
    }
    if (url.pathname === '/api/story-workspace/subscription/context') {
      contextReads += 1;
      await fulfill(route, {
        data: {
          canonicalUser: { id: '7' },
          subscription: {
            id: 'sub_7',
            status: 'active',
            version: pendingChange ? 8 : 7,
            cycleAnchorAt: '2026-08-09T10:00:00Z',
            currentPeriodNumber: 0,
            currentPeriodStart: '2026-08-09T10:00:00Z',
            currentPeriodEnd: '2026-09-09T10:00:00Z',
            renewalEnabled: true,
            cancelAtPeriodEnd: false,
            pendingChange: pendingChange ? {
              ...planSummary('pv_studio', 'Studio', 2, 2_000_000),
              appliesAt: '2026-09-09T10:00:00Z',
            } : null,
            allowedActions: ['upgrade', 'downgrade', 'pause', 'cancel'],
          },
          planVersion: planSummary(),
          entitlements: [{
            gatewayScope: 'messages:create',
            modelAliases: ['dream-balanced'],
            rpmLimit: 30,
            dailyTokenLimit: 200_000,
            storageBytes: 10_737_418_240,
          }],
          allowance: allowance(),
          asOf: '2026-08-09T10:05:00Z',
        },
        meta: { requestId: `req_context_${contextReads}` },
      });
      return;
    }
    if (url.pathname === '/api/story-workspace/subscription/plans') {
      await fulfill(route, {
        data: [
          {
            ...planSummary('pv_studio', 'Studio', 2, 2_000_000),
            description: 'For long-form story work.',
            entitlements: [{
              gatewayScopes: ['messages:create', 'chat:create'],
              modelAliases: ['dream-balanced', 'dream-long'],
              rpmLimit: 60,
              dailyTokenLimit: 400_000,
              storageBytes: 21_474_836_480,
            }],
            eligibility: { eligible: true, reasonCode: null, appliesAt: '2026-09-09T10:00:00Z' },
            availableActions: ['upgrade'],
          },
          {
            ...planSummary('pv_archive', 'Archive', 1, 500_000),
            description: 'Not eligible for the current subscription state.',
            entitlements: [{
              gatewayScopes: ['messages:create'],
              modelAliases: ['dream-balanced'],
              rpmLimit: 15,
              dailyTokenLimit: 100_000,
              storageBytes: 5_368_709_120,
            }],
            eligibility: { eligible: false, reasonCode: 'PLAN_NOT_ELIGIBLE', appliesAt: null },
            availableActions: ['downgrade'],
          },
        ],
        meta: { total: 2, page: 1, pageSize: 20, requestId: 'req_plans' },
      });
      return;
    }
    if (url.pathname === '/api/story-workspace/usage') {
      await fulfill(route, {
        data: {
          period: { start: '2026-08-09T10:00:00Z', end: '2026-09-09T10:00:00Z', timezone: 'UTC' },
          allowance: allowance(),
          summary: {
            requestCount: 1,
            inputTokens: 1_000,
            outputTokens: 500,
            cacheReadTokens: 0,
            cacheWriteTokens: 0,
            totalTokens: 1_500,
            unknownUsageCount: 0,
          },
          projection: {
            asOf: '2026-08-09T10:05:00Z',
            sampleWindowDays: 7,
            projectedExhaustionAt: null,
            projectedTokenShortfall: null,
            confidence: 'insufficientData',
          },
          items: [{
            gatewayRequestId: 'gw_req_1',
            modelAlias: 'dream-balanced',
            gatewayScope: 'messages:create',
            protocol: 'anthropic',
            outcome: 'completed',
            settlementState: 'settled',
            inputTokens: 1_000,
            outputTokens: 500,
            cacheReadTokens: 0,
            cacheWriteTokens: 0,
            totalTokens: 1_500,
            allowanceReservedTokens: 2_000,
            allowanceConsumedTokens: 1_500,
            allowanceReleasedTokens: 500,
            occurredAt: '2026-08-09T10:03:00Z',
            errorCategory: null,
          }],
        },
        meta: { total: 1, page: 1, pageSize: 25, requestId: 'req_usage' },
      });
      return;
    }
    if (url.pathname === '/api/story-workspace/models') {
      await fulfill(route, {
        data: {
          items: [{
            modelAlias: 'dream-balanced',
            displayName: 'Balanced',
            description: 'Balanced quality and latency.',
            capabilities: ['text', 'stream'],
            contexts: ['story_generation'],
            eligibility: {
              allowed: true,
              reasonCode: null,
              subscriptionStatus: 'active',
              gatewayScopes: ['messages:create'],
              rpmLimit: 30,
              dailyTokenLimit: 200_000,
              storageBytes: 10_737_418_240,
              monthlyTokenRemaining: 759_000,
              monthlyTokenResetAt: '2026-09-09T10:00:00Z',
            },
            limits: { contextWindow: 200_000, maxOutputTokens: 8_192 },
            availability: 'available',
            asOf: '2026-08-09T10:05:00Z',
          }],
          asOf: '2026-08-09T10:05:00Z',
        },
        meta: { requestId: 'req_models' },
      });
      return;
    }
    if (url.pathname === '/api/story-workspace/subscription/commands') {
      const body = request.postDataJSON() as Record<string, unknown>;
      if (body.phase === 'preview') {
        await fulfill(route, {
          data: {
            action: body.action,
            allowed: true,
            reasonCode: null,
            previewId: 'preview_abcdefghijklmnopqrstuv',
            digest: 'sha256:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ',
            expiresAt: '2026-08-09T10:10:00Z',
            expectedVersion: 7,
            current: planSummary(),
            target: planSummary('pv_studio', 'Studio', 2, 2_000_000),
            appliesAt: '2026-09-09T10:00:00Z',
            allowanceImpact: {
              unit: 'tokens',
              currentPeriodTokens: 1_000_000,
              nextPeriodTokens: 2_000_000,
              currentPeriodChanges: false,
            },
            entitlementImpact: {
              currentModelAliases: ['dream-balanced'],
              targetModelAliases: ['dream-balanced', 'dream-long'],
            },
            gatewayImpact: { callableAfterExecute: true },
            warnings: [],
          },
          meta: { requestId: 'req_preview' },
        });
        return;
      }
      executed.push({
        body,
        idempotencyKey: request.headers()['idempotency-key'] ?? null,
      });
      pendingChange = true;
      await fulfill(route, {
        data: {
          commandId: 'cmd_upgrade',
          outcome: 'scheduled',
          subscription: {
            id: 'sub_7',
            status: 'active',
            version: 8,
            planVersionId: 'pv_creator',
            pendingPlanVersionId: 'pv_studio',
            currentPeriodStart: '2026-08-09T10:00:00Z',
            currentPeriodEnd: '2026-09-09T10:00:00Z',
          },
          actualImpact: {
            unit: 'tokens',
            appliesAt: '2026-09-09T10:00:00Z',
            grantedTokens: null,
            reservedTokens: null,
            consumedTokens: null,
            remainingTokens: null,
          },
          idempotentReplay: false,
        },
        meta: { requestId: 'req_execute' },
      });
      return;
    }
    await fulfill(route, {});
  });

  return {
    executed,
    contextReads: () => contextReads,
  };
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
  const product = await installProductMocks(page);
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
  await expect(page.getByRole('heading', { name: '月度 Token 订阅' })).toBeVisible();
  await expect(page.getByText('本周期 Token 守恒')).toBeVisible();
  return { diagnostics, product };
}

test('1440×1000 renders facts and executes a receipt-backed next-period upgrade', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  const { diagnostics, product } = await preparePage(page);

  await expect(page.getByRole('heading', { name: '月度 Token 订阅' })).toBeFocused();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '240000');
  await expect(page.getByText('759,000', { exact: true })).toBeVisible();
  await expect(page.getByRole('radio', { name: /Archive/ })).toBeDisabled();
  const visibleCopy = (await page.locator('body').innerText()).toLocaleLowerCase();
  for (const forbidden of ['price', 'currency', 'microusd', 'cash balance', 'checkout', 'refund', 'financial ledger']) {
    expect(visibleCopy).not.toContain(forbidden);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  await page.getByRole('radio', { name: /Studio/ }).check();
  await page.getByRole('button', { name: '下周期升级' }).click();
  const dialog = page.getByRole('dialog', { name: '下周期升级' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('heading', { name: '下周期升级' })).toBeFocused();
  await dialog.getByRole('checkbox').check();
  await dialog.getByRole('button', { name: '确认下周期升级' }).click();
  await expect(page.getByText('变更已安排')).toBeVisible();
  await expect(page.getByText(/已安排 Studio v2/)).toBeVisible();
  expect(product.executed).toHaveLength(1);
  expect(product.executed[0]?.idempotencyKey).toMatch(/^dream-subscription-/);
  expect(product.executed[0]?.body).toMatchObject({
    expectedVersion: 7,
    previewId: 'preview_abcdefghijklmnopqrstuv',
    digest: 'sha256:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ',
    expiresAt: '2026-08-09T10:10:00Z',
  });
  expect(product.contextReads()).toBeGreaterThan(1);
  await page.screenshot({
    path: testInfo.outputPath('subscription-desktop-1440x1000.png'),
    fullPage: true,
  });
  expect(diagnostics).toEqual([]);
});

test('390×844 remains single-column, overflow-free, and restores focus after Escape', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const { diagnostics } = await preparePage(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.locator('.story-workspace-subscription__usage-cards')).toBeVisible();
  const radio = page.getByRole('radio', { name: /Studio/ });
  await radio.check();
  const previewButton = page.getByRole('button', { name: '下周期升级' });
  await previewButton.focus();
  await previewButton.press('Enter');
  await expect(page.getByRole('dialog', { name: '下周期升级' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(previewButton).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath('subscription-mobile-390x844.png'),
    fullPage: true,
  });
  expect(diagnostics).toEqual([]);
});
