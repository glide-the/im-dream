// [Input] Product API transport with injectable fetch responses.
// [Output] Contract, security, error, and command receipt regression evidence.
// [Pos] Focused browser-transport unit tests for the Token-only subscription surface.

import { expect, test } from '@playwright/test';
import {
  PRODUCT_BFF_ENDPOINTS,
  ProductApiError,
  fetchProductSubscriptionContext,
  submitProductSubscriptionCommand,
} from '../productApi';

function contextEnvelope() {
  return {
    data: {
      canonicalUser: { id: '1' },
      subscription: {
        id: 'sub_1',
        status: 'active',
        version: 7,
        cycleAnchorAt: '2026-08-09T10:00:00Z',
        currentPeriodNumber: 0,
        currentPeriodStart: '2026-08-09T10:00:00Z',
        currentPeriodEnd: '2026-09-09T10:00:00Z',
        renewalEnabled: true,
        cancelAtPeriodEnd: false,
        pendingChange: null,
        allowedActions: ['upgrade', 'downgrade', 'pause', 'cancel'],
      },
      planVersion: {
        planCode: 'creator',
        planName: 'Creator',
        planVersionId: 'pv_4',
        version: 4,
        billingCycle: 'monthly',
        monthlyAllowanceTokens: 1_000_000,
        monthlyPriceMicrousd: 9_000_000,
        currency: 'USD',
      },
      entitlements: [{
        gatewayScope: 'messages:create',
        modelAliases: ['dream-balanced'],
        rpmLimit: 30,
        dailyTokenLimit: null,
        storageBytes: 10_737_418_240,
      }],
      allowance: {
        unit: 'tokens',
        granted: 1_000_000,
        reserved: 1_000,
        consumed: 240_000,
        remaining: 759_000,
        resetsAt: '2026-09-09T10:00:00Z',
      },
      asOf: '2026-08-09T10:05:00Z',
    },
    meta: { requestId: 'req_1' },
  };
}

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

test('the browser product boundary contains exactly the six approved same-origin routes', () => {
  expect(Object.values(PRODUCT_BFF_ENDPOINTS)).toEqual([
    '/api/story-workspace/subscription/context',
    '/api/story-workspace/subscription/plans',
    '/api/story-workspace/subscription/commands',
    '/api/story-workspace/usage',
    '/api/story-workspace/models',
    '/api/story-workspace/subscription/payment-intents',
  ]);
});

test('context parsing preserves server Token facts and authenticated request behavior', async () => {
  const calls: Array<{ input: string; init?: RequestInit }> = [];
  const result = await fetchProductSubscriptionContext({
    token: 'session-token',
    resolveUrl: (path) => path,
    fetchImpl: (async (input, init) => {
      calls.push({ input: String(input), init });
      return jsonResponse(contextEnvelope());
    }) as typeof fetch,
  });

  expect(result.data.allowance?.remaining).toBe(759_000);
  expect(calls[0]?.input).toBe(PRODUCT_BFF_ENDPOINTS.context);
  expect(calls[0]?.init?.credentials).toBe('include');
  expect(new Headers(calls[0]?.init?.headers).get('authorization')).toBe('Bearer session-token');
});

test('context parsing preserves the supported past-due renewal state', async () => {
  const payload = contextEnvelope();
  payload.data.subscription.status = 'past_due';
  payload.data.subscription.allowedActions = ['renew'];

  const result = await fetchProductSubscriptionContext({
    token: null,
    resolveUrl: (path) => path,
    fetchImpl: (async () => jsonResponse(payload)) as typeof fetch,
  });

  expect(result.data.subscription).toMatchObject({
    status: 'past_due',
    allowedActions: ['renew'],
  });
});

test('strict parsing rejects unknown nested fields, unsafe integers, and broken conservation', async () => {
  for (const mutate of [
    (payload: ReturnType<typeof contextEnvelope>) => {
      Object.assign(payload.data.planVersion!, { providerRoute: 'forbidden' });
    },
    (payload: ReturnType<typeof contextEnvelope>) => {
      payload.data.allowance!.granted = Number.MAX_SAFE_INTEGER + 1;
    },
    (payload: ReturnType<typeof contextEnvelope>) => {
      payload.data.allowance!.remaining += 1;
    },
  ]) {
    const payload = contextEnvelope();
    mutate(payload);
    await expect(fetchProductSubscriptionContext({
      token: null,
      resolveUrl: (path) => path,
      fetchImpl: (async () => jsonResponse(payload)) as typeof fetch,
    })).rejects.toMatchObject({
      status: 503,
      code: 'PRODUCT_RESPONSE_CONTRACT_INVALID',
    });
  }
});

test('all published product error statuses retain stable codes and safe recovery metadata', async () => {
  const cases = [401, 402, 403, 404, 409, 429, 502, 503];
  for (const status of cases) {
    const code = status === 402
      ? 'SUBSCRIPTION_TOKEN_ALLOWANCE_EXHAUSTED'
      : `PRODUCT_TEST_${status}`;
    const details = status === 402 ? {
      metric: 'tokens',
      unit: 'tokens',
      availableTokens: 0,
      requiredTokens: 1,
      periodEnd: '2026-09-09T10:00:00Z',
    } : undefined;
    const promise = fetchProductSubscriptionContext({
      token: null,
      resolveUrl: (path) => path,
      fetchImpl: (async () => jsonResponse({
        error: { code, message: 'Safe product error.', ...(details ? { details } : {}) },
        meta: { requestId: `req_${status}`, ...(status === 429 ? { retryAfterSeconds: 30 } : {}) },
      }, status)) as typeof fetch,
    });
    await expect(promise).rejects.toBeInstanceOf(ProductApiError);
    await expect(promise).rejects.toMatchObject({
      status,
      code,
      requestId: `req_${status}`,
      retryAfterSeconds: status === 429 ? 30 : null,
    });
  }
});

test('safe model and Gateway recovery details remain readable while unknown fields fail closed', async () => {
  const safeError = fetchProductSubscriptionContext({
    token: null,
    resolveUrl: (path) => path,
    fetchImpl: (async () => jsonResponse({
      error: {
        code: 'ENTITLEMENT_REQUIRED',
        message: 'The requested model scope is unavailable.',
        details: {
          modelAlias: 'dream-long',
          gatewayScope: 'messages:create',
          requiredScope: 'messages:create',
          retryable: false,
        },
      },
      meta: { requestId: 'req_entitlement' },
    }, 403)) as typeof fetch,
  });
  await expect(safeError).rejects.toMatchObject({
    status: 403,
    details: {
      modelAlias: 'dream-long',
      gatewayScope: 'messages:create',
      requiredScope: 'messages:create',
      retryable: false,
    },
  });

  await expect(fetchProductSubscriptionContext({
    token: null,
    resolveUrl: (path) => path,
    fetchImpl: (async () => jsonResponse({
      error: {
        code: 'ENTITLEMENT_REQUIRED',
        message: 'The requested model scope is unavailable.',
        details: { modelAlias: 'dream-long', providerRoute: 'forbidden' },
      },
      meta: { requestId: 'req_unsafe' },
    }, 403)) as typeof fetch,
  })).rejects.toMatchObject({
    status: 503,
    code: 'PRODUCT_RESPONSE_CONTRACT_INVALID',
  });
});

test('execute forwards the preview receipt, expected version, and one idempotency key', async () => {
  let captured: { input: string; init?: RequestInit } | null = null;
  const result = await submitProductSubscriptionCommand({
    action: 'upgrade',
    phase: 'execute',
    targetPlanVersionId: 'pv_5',
    expectedVersion: 7,
    previewId: 'preview_abcdefghijklmnopqrstuv',
    digest: 'sha256:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ',
    expiresAt: '2026-08-09T10:10:00Z',
    reason: 'Apply the next monthly Token plan.',
  }, {
    idempotencyKey: 'subscription-command-12345678',
    token: 'session-token',
    resolveUrl: (path) => path,
    fetchImpl: (async (input, init) => {
      captured = { input: String(input), init };
      return jsonResponse({
        data: {
          commandId: 'cmd_1',
          outcome: 'scheduled',
          subscription: {
            id: 'sub_1',
            status: 'active',
            version: 8,
            planVersionId: 'pv_4',
            pendingPlanVersionId: 'pv_5',
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
    }) as typeof fetch,
  });

  expect(result.data.outcome).toBe('scheduled');
  expect(captured).not.toBeNull();
  const request = captured as unknown as { input: string; init?: RequestInit };
  expect(request.input).toBe(PRODUCT_BFF_ENDPOINTS.commands);
  expect(new Headers(request.init?.headers).get('idempotency-key')).toBe('subscription-command-12345678');
  expect(JSON.parse(String(request.init?.body))).toMatchObject({
    expectedVersion: 7,
    previewId: 'preview_abcdefghijklmnopqrstuv',
    expiresAt: '2026-08-09T10:10:00Z',
  });
});

test('a non-target lifecycle execute keeps nullable Dream input and one receipt', async () => {
  let capturedBody: Record<string, unknown> | null = null;
  const result = await submitProductSubscriptionCommand({
    action: 'pause',
    phase: 'execute',
    targetPlanVersionId: null,
    expectedVersion: 7,
    previewId: 'preview_abcdefghijklmnopqrstuv',
    digest: 'sha256:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ',
    expiresAt: '2026-08-09T10:10:00Z',
    reason: 'Pause without changing the personal monthly period.',
  }, {
    idempotencyKey: 'pause-command-12345678',
    token: null,
    resolveUrl: (path) => path,
    fetchImpl: (async (_input, init) => {
      capturedBody = JSON.parse(String(init?.body)) as Record<string, unknown>;
      return jsonResponse({
        data: {
          commandId: 'cmd_pause',
          outcome: 'applied',
          subscription: {
            id: 'sub_1',
            status: 'paused',
            version: 8,
            planVersionId: 'pv_4',
            pendingPlanVersionId: null,
            currentPeriodStart: '2026-08-09T10:00:00Z',
            currentPeriodEnd: '2026-09-09T10:00:00Z',
          },
          actualImpact: {
            unit: 'tokens',
            appliesAt: '2026-08-09T10:06:00Z',
            grantedTokens: 1_000_000,
            reservedTokens: 1_000,
            consumedTokens: 240_000,
            remainingTokens: 759_000,
          },
          idempotentReplay: false,
        },
        meta: { requestId: 'req_pause' },
      });
    }) as typeof fetch,
  });

  expect(result.data.subscription.status).toBe('paused');
  expect(capturedBody).toMatchObject({
    action: 'pause',
    targetPlanVersionId: null,
    expectedVersion: 7,
    previewId: 'preview_abcdefghijklmnopqrstuv',
  });
});

test('preview never accepts an idempotency key and execute requires one', async () => {
  expect(() => submitProductSubscriptionCommand({
    action: 'pause',
    phase: 'preview',
    targetPlanVersionId: null,
    expectedVersion: 7,
  }, {
    idempotencyKey: 'not-allowed',
    token: null,
    fetchImpl: (async () => { throw new Error('must not call'); }) as typeof fetch,
  })).toThrow('Preview commands cannot carry an idempotency key.');

  expect(() => submitProductSubscriptionCommand({
    action: 'pause',
    phase: 'execute',
    targetPlanVersionId: null,
    expectedVersion: 7,
    previewId: 'preview_abcdefghijklmnopqrstuv',
    digest: 'sha256:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ',
    expiresAt: '2026-08-09T10:10:00Z',
    reason: 'Pause this monthly Token subscription.',
  }, {
    idempotencyKey: '',
    token: null,
    fetchImpl: (async () => { throw new Error('must not call'); }) as typeof fetch,
  })).toThrow('Execute commands require a valid idempotency key.');
});
