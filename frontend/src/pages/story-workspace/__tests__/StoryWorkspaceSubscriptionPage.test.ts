// [Input] Simplified subscription page, styles, Product API, and subscription hook source seams.
// [Output] Focused hierarchy, real-data, accessibility, privacy, and responsive regressions.
// [Pos] Source-level UI contract for the quiet Story Workspace subscription route.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source only; browser app omits Node types.
import { readFileSync } from 'node:fs';

const PAGE = readFileSync(new URL('../StoryWorkspaceSubscriptionPage.tsx', import.meta.url), 'utf8');
const CSS = readFileSync(new URL('../StoryWorkspaceSubscriptionPage.css', import.meta.url), 'utf8');
const API = readFileSync(new URL('../../../api/productApi.ts', import.meta.url), 'utf8');
const HOOK = readFileSync(new URL('../../../hooks/story-workspace/useStoryWorkspaceSubscription.ts', import.meta.url), 'utf8');

test('page reduces the experience to overview and three single-panel tabs', () => {
  expect(PAGE).toContain("{ id: 'info', label: '订阅信息' }");
  expect(PAGE).toContain("{ id: 'allowance', label: '我的额度' }");
  expect(PAGE).toContain("{ id: 'plans', label: '可选套餐' }");
  expect(PAGE).toContain("useState<SubscriptionTab>('info')");
  expect(PAGE).toContain("activeTab === 'info'");
  expect(PAGE).toContain("activeTab === 'allowance'");
  expect(PAGE).toContain("activeTab === 'plans'");
  expect(PAGE).toContain('Dream · Subscription');
  expect(PAGE).not.toContain('STORY_WORKSPACE_DREAM_PLANS');
});

test('subscription screen loads only context and plans through the same-origin API owner', () => {
  expect(API).toContain("context: '/api/story-workspace/subscription/context'");
  expect(API).toContain("plans: '/api/story-workspace/subscription/plans'");
  expect(PAGE).not.toContain('fetch(');
  expect(PAGE).not.toContain('apiUrl(');
  expect(PAGE).not.toContain('localStorage');
  expect(HOOK).toContain('api.context({ signal: controller.signal })');
  expect(HOOK).toContain('api.plans({ page: planPage, pageSize: planPageSize }');
  expect(HOOK).not.toContain('api.usage(');
  expect(HOOK).not.toContain('api.models(');
  expect(HOOK).not.toContain('fetchProductUsage');
  expect(HOOK).not.toContain('fetchProductModelCatalog');
});

test('plans and allowance remain server-owned without static prices, balances, or checkout claims', () => {
  expect(PAGE).toContain('data.plans.data.map');
  expect(PAGE).toContain('context.allowance');
  expect(PAGE).toContain('plan.monthlyAllowanceTokens !== null');
  expect(PAGE).toContain('暂不可开通');
  expect(PAGE).toContain('不会伪造价格或开通结果');
  expect(API).toContain('monthlyPriceMicrousd: nonNegativeIntegerSchema.nullable()');
  expect(API).toContain("unavailableReason: z.enum(['commercial_parameters_pending', 'configuration_incomplete']).nullable()");
  for (const term of ['fakePrice', 'mockPrice', 'cashBalance', 'checkout', 'invoice', 'topUp']) {
    expect(PAGE.toLocaleLowerCase()).not.toContain(term.toLocaleLowerCase());
  }
});

test('implementation removes internal billing and gateway detail from the visible page', () => {
  for (const term of [
    'planVersionId',
    'cycleAnchorAt',
    'currentPeriodNumber',
    'gatewayScope',
    'modelAlias',
    'rpmLimit',
    'dailyTokenLimit',
    'storageBytes',
    'gatewayRequestId',
    'settlementState',
    'requestId',
    'reserved',
    'previewId',
    'digest',
  ]) {
    expect(PAGE).not.toContain(term);
  }
  expect(PAGE).toContain('allowance.consumed');
  expect(PAGE).toContain('allowance.remaining');
  expect(PAGE).toContain('allowance.granted');
});

test('loading, empty, and recoverable service states stay explicit but plain-language', () => {
  expect(PAGE).toContain('正在读取订阅');
  expect(PAGE).toContain('当前没有有效订阅');
  expect(PAGE).toContain('暂时没有可选套餐');
  for (const status of [401, 402, 403, 409, 429, 502, 503]) {
    expect(PAGE).toContain(`case ${status}:`);
  }
  expect(PAGE).toContain('role="alert"');
  expect(PAGE).not.toContain('请求编号');
  expect(PAGE).not.toContain('{error.code}');
});

test('tabs support roving focus, screen readers, reduced motion, and compact layouts', () => {
  expect(PAGE).toContain('role="tablist"');
  expect(PAGE).toContain('role="tab"');
  expect(PAGE).toContain('role="tabpanel"');
  expect(PAGE).toContain('aria-controls=');
  expect(PAGE).toContain('aria-selected=');
  expect(PAGE).toContain("event.key === 'ArrowRight'");
  expect(PAGE).toContain("event.key === 'ArrowLeft'");
  expect(PAGE).toContain("event.key === 'Home'");
  expect(PAGE).toContain("event.key === 'End'");
  expect(PAGE).toContain('aria-live="polite"');
  expect(PAGE).toContain('role="progressbar"');
  expect(PAGE).toContain('requestAnimationFrame');
  expect(CSS).toContain('@media (max-width: 640px)');
  expect(CSS).toContain('grid-template-columns: 1fr');
  expect(CSS).toContain('width: 100%');
  expect(CSS).toContain('@media (prefers-reduced-motion: reduce)');
});
