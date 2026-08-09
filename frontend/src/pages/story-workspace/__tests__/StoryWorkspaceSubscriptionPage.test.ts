// [Input] Subscription page, styles, Product API, and subscription hook source seams.
// [Output] Hierarchy, strict boundary, accessibility, lifecycle, error, and responsive regressions.
// [Pos] Focused source-level UI contract for the real monthly Token subscription route.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source only; browser app omits Node types.
import { readFileSync } from 'node:fs';

const PAGE = readFileSync(new URL('../StoryWorkspaceSubscriptionPage.tsx', import.meta.url), 'utf8');
const CSS = readFileSync(new URL('../StoryWorkspaceSubscriptionPage.css', import.meta.url), 'utf8');
const API = readFileSync(new URL('../../../api/productApi.ts', import.meta.url), 'utf8');
const HOOK = readFileSync(new URL('../../../hooks/story-workspace/useStoryWorkspaceSubscription.ts', import.meta.url), 'utf8');

test('page hierarchy follows subscription, Token conservation, entitlements, models, usage, then commands', () => {
  const headings = [
    '当前订阅与个人周期',
    '本周期 Token 守恒',
    '当前权益',
    '当前可用模型',
    '本周期 Usage',
    '为正在形成的故事留出空间',
  ];
  for (let index = 1; index < headings.length; index += 1) {
    expect(PAGE.indexOf(headings[index - 1]!)).toBeLessThan(PAGE.indexOf(headings[index]!));
  }
  expect(PAGE).not.toContain('STORY_WORKSPACE_DREAM_PLANS');
  expect(PAGE).not.toContain('订阅功能即将开放');
  expect(PAGE).not.toContain('正式开通后可在此管理');
  expect(PAGE).toContain('const canSelect = plan.available && plan.eligibility.eligible');
});

test('browser code reaches only the five same-origin BFF routes through one API owner', () => {
  expect(API).toContain("context: '/api/story-workspace/subscription/context'");
  expect(API).toContain("plans: '/api/story-workspace/subscription/plans'");
  expect(API).toContain("commands: '/api/story-workspace/subscription/commands'");
  expect(API).toContain("usage: '/api/story-workspace/usage'");
  expect(API).toContain("models: '/api/story-workspace/models'");
  expect(PAGE).not.toContain('fetch(');
  expect(PAGE).not.toContain('apiUrl(');
  expect(PAGE).not.toContain('localStorage');
  expect(HOOK).not.toContain('fetch(');
  expect(HOOK).not.toContain('apiUrl(');
  expect(HOOK).not.toContain('localStorage');
});

test('strict DTOs allow only server commercial facts and exclude local balances or fake checkout state', () => {
  for (const term of ['cashBalance', 'topUp', 'refund', 'reversal', 'financialLedger', 'fakePrice', 'mockPrice']) {
    expect(PAGE.toLocaleLowerCase()).not.toContain(term.toLocaleLowerCase());
  }
  expect(PAGE).toContain('商业参数待发布 · 暂不可开通');
  expect(PAGE).toContain('不会创建支付或订阅结果');
  expect(API).toContain('monthlyPriceMicrousd: nonNegativeIntegerSchema.nullable()');
  expect(API).toContain("unavailableReason: z.enum(['commercial_parameters_pending', 'configuration_incomplete']).nullable()");
  expect(API).toContain("unit: z.literal('tokens')");
  expect(API).toContain('Number.MAX_SAFE_INTEGER');
  expect(API).toContain('Token allowance conservation failed.');
  expect(API).toContain('.strict()');
});

test('all eight lifecycle actions use preview and execute with immutable receipt fields', () => {
  for (const action of ['create', 'renew', 'upgrade', 'downgrade', 'pause', 'resume', 'cancel', 'revoke_cancel']) {
    expect(PAGE).toContain(`${action}:`);
  }
  expect(HOOK).toContain('buildProductCommandPreview');
  expect(HOOK).toContain('previewId: preview.data.previewId');
  expect(HOOK).toContain('digest: preview.data.digest');
  expect(HOOK).toContain('expiresAt: preview.data.expiresAt');
  expect(HOOK).toContain('expectedVersion: preview.data.expectedVersion');
  expect(HOOK).toContain('idempotencyKeyRef');
  expect(HOOK).toContain('setRefreshVersion((version) => version + 1)');
});

test('loading, empty, 401/402/403/404/409/429/502/503 and unknown usage are explicit', () => {
  expect(PAGE).toContain('aria-busy="true"');
  expect(PAGE).toContain('当前没有订阅');
  expect(PAGE).toContain('暂无已发布的月度套餐');
  for (const status of [401, 402, 403, 404, 409, 429, 502, 503]) {
    expect(PAGE).toContain(`case ${status}:`);
  }
  expect(PAGE).toContain("item.settlementState === 'usageUnknown' ? '待确认'");
  expect(PAGE).toContain('本周期 Token 不足');
});

test('keyboard, focus, labels, live updates and both responsive layouts stay first-class', () => {
  expect(PAGE).toContain('story-workspace-subscription__skip-link');
  expect(PAGE).toContain('aria-live="polite"');
  expect(PAGE).toContain('role="progressbar"');
  expect(PAGE).toContain('type="radio"');
  expect(PAGE).toContain('aria-modal="true"');
  expect(PAGE).toContain("event.key === 'Escape'");
  expect(PAGE).toContain("event.key !== 'Tab'");
  expect(PAGE).toContain('commandTriggerRef.current = event.currentTarget');
  expect(PAGE).toContain('restoreFocus?.isConnected');
  expect(PAGE).toContain('requestAnimationFrame');
  expect(PAGE).toContain('role="alert"');
  expect(PAGE).toContain('<caption>');
  expect(CSS).toContain('@media (max-width: 560px)');
  expect(CSS).toContain('width: min(620px, 100%)');
  expect(CSS).toContain('width: 100%');
  expect(CSS).toContain('@media (prefers-reduced-motion: reduce)');
});
