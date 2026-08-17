// [Input] Pure command builders used by the subscription hook.
// [Output] Expected-version, preview receipt, and idempotency invariants.
// [Pos] Focused command orchestration regression tests.

import { expect, test } from '@playwright/test';
// @ts-expect-error Node seam reads the hook source to enforce storage ownership.
import { readFileSync } from 'node:fs';
import type { CommandPreviewEnvelope } from '../../../api/productApi';
import {
  buildProductCommandExecute,
  buildProductCommandPreview,
  newProductCommandIdempotencyKey,
} from '../useStoryWorkspaceSubscription';

const SOURCE = readFileSync(new URL('../useStoryWorkspaceSubscription.ts', import.meta.url), 'utf8');

function previewEnvelope(): CommandPreviewEnvelope {
  return {
    data: {
      action: 'upgrade',
      allowed: true,
      reasonCode: null,
      previewId: 'preview_abcdefghijklmnopqrstuv',
      digest: 'sha256:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ',
      expiresAt: '2026-08-09T10:10:00Z',
      expectedVersion: 7,
      current: {
        planCode: 'creator',
        planName: 'Creator',
        planVersionId: 'pv_4',
        version: 4,
        billingCycle: 'monthly',
        monthlyAllowanceTokens: 1_000_000,
        monthlyPriceMicrousd: 9_000_000,
        currency: 'USD',
      },
      target: {
        planCode: 'studio',
        planName: 'Studio',
        planVersionId: 'pv_5',
        version: 5,
        billingCycle: 'monthly',
        monthlyAllowanceTokens: 2_000_000,
        monthlyPriceMicrousd: 19_000_000,
        currency: 'USD',
      },
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
  };
}

test('create carries no subscription version while all existing-subscription actions do', () => {
  expect(buildProductCommandPreview('create', 'pv_4', null)).toEqual({
    action: 'create',
    phase: 'preview',
    targetPlanVersionId: 'pv_4',
    expectedVersion: null,
  });
  expect(buildProductCommandPreview('pause', null, 7)).toEqual({
    action: 'pause',
    phase: 'preview',
    targetPlanVersionId: null,
    expectedVersion: 7,
  });
});

test('execute copies the immutable preview receipt instead of re-deriving impact', () => {
  expect(buildProductCommandExecute(
    previewEnvelope(),
    'pv_5',
    'Apply this version at the next personal period boundary.',
  )).toEqual({
    action: 'upgrade',
    phase: 'execute',
    targetPlanVersionId: 'pv_5',
    expectedVersion: 7,
    previewId: 'preview_abcdefghijklmnopqrstuv',
    digest: 'sha256:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ',
    expiresAt: '2026-08-09T10:10:00Z',
    reason: 'Apply this version at the next personal period boundary.',
  });
});

test('idempotency keys are scoped, deterministic under injection, and valid for the BFF', () => {
  const key = newProductCommandIdempotencyKey(() => '123e4567-e89b-12d3-a456-426614174000');
  expect(key).toBe('dream-subscription-123e4567-e89b-12d3-a456-426614174000');
  expect(key).toMatch(/^[A-Za-z0-9._~-]{8,128}$/);
});

test('the hook delegates session storage and transport to the shared Product API boundary', () => {
  expect(SOURCE).not.toContain('localStorage');
  expect(SOURCE).not.toContain('sessionStorage');
  expect(SOURCE).not.toContain('apiUrl(');
  expect(SOURCE).not.toContain('fetch(');
  expect(SOURCE).toContain('setRefreshVersion((version) => version + 1)');
});
