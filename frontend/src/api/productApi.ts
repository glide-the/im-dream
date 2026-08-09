// [Input] Five same-origin Dream Product BFF routes and the current Dream auth token.
// [Output] Strict Token-only subscription, usage, model, and command contracts.
// [Pos] Sole browser transport boundary for the Dream monthly Token subscription experience.

import { z } from 'zod';
import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';

export const PRODUCT_BFF_ENDPOINTS = {
  context: '/api/story-workspace/subscription/context',
  plans: '/api/story-workspace/subscription/plans',
  commands: '/api/story-workspace/subscription/commands',
  usage: '/api/story-workspace/usage',
  models: '/api/story-workspace/models',
} as const;

const MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER;
const nonNegativeIntegerSchema = z.number().int().min(0).max(MAX_SAFE_INTEGER);
const positiveIntegerSchema = z.number().int().min(1).max(MAX_SAFE_INTEGER);
const safeIdentifierSchema = z.string().min(1).max(200);
const safeTextSchema = z.string().min(1).max(4_000);
const isoTimestampSchema = z.string().min(20).max(64).refine(
  (value) => /(Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)),
  'Expected an ISO timestamp with an explicit timezone.',
);

export const productActionSchema = z.enum([
  'create',
  'renew',
  'upgrade',
  'downgrade',
  'pause',
  'resume',
  'cancel',
  'revoke_cancel',
]);

const productEntitlementSchema = z.object({
  gatewayScopes: z.array(safeIdentifierSchema),
  modelAliases: z.array(safeIdentifierSchema),
  rpmLimit: nonNegativeIntegerSchema.nullable(),
  dailyTokenLimit: nonNegativeIntegerSchema.nullable(),
  storageBytes: nonNegativeIntegerSchema.nullable(),
}).strict();

const planSummarySchema = z.object({
  planCode: safeIdentifierSchema,
  planName: z.string().min(1).max(160),
  planVersionId: safeIdentifierSchema,
  version: nonNegativeIntegerSchema,
  billingCycle: z.literal('monthly'),
  monthlyAllowanceTokens: nonNegativeIntegerSchema,
}).strict();

const planEligibilitySchema = z.object({
  eligible: z.boolean(),
  reasonCode: safeIdentifierSchema.nullable(),
  appliesAt: isoTimestampSchema.nullable(),
}).strict();

const productPlanSchema = planSummarySchema.extend({
  description: safeTextSchema.nullable(),
  entitlements: z.array(productEntitlementSchema),
  eligibility: planEligibilitySchema,
  availableActions: z.array(productActionSchema),
}).strict();

const allowanceSchema = z.object({
  unit: z.literal('tokens'),
  granted: nonNegativeIntegerSchema,
  reserved: nonNegativeIntegerSchema,
  consumed: nonNegativeIntegerSchema,
  remaining: nonNegativeIntegerSchema,
  resetsAt: isoTimestampSchema,
}).strict().superRefine((value, context) => {
  const accounted = value.reserved + value.consumed + value.remaining;
  if (!Number.isSafeInteger(accounted) || value.granted !== accounted) {
    context.addIssue({
      code: 'custom',
      message: 'Token allowance conservation failed.',
      path: ['granted'],
    });
  }
});

const pendingChangeSchema = planSummarySchema.extend({
  appliesAt: isoTimestampSchema,
}).strict();

const subscriptionSchema = z.object({
  id: safeIdentifierSchema,
  status: z.enum([
    'trial',
    'active',
    'paused',
    'cancel_at_period_end',
    'cancelled',
    'expired',
    'legacyUnavailable',
  ]),
  version: positiveIntegerSchema,
  cycleAnchorAt: isoTimestampSchema,
  currentPeriodNumber: nonNegativeIntegerSchema,
  currentPeriodStart: isoTimestampSchema,
  currentPeriodEnd: isoTimestampSchema,
  renewalEnabled: z.boolean(),
  cancelAtPeriodEnd: z.boolean(),
  pendingChange: pendingChangeSchema.nullable(),
  allowedActions: z.array(productActionSchema),
}).strict();

const contextEntitlementSchema = z.object({
  gatewayScope: safeIdentifierSchema,
  modelAliases: z.array(safeIdentifierSchema),
  rpmLimit: nonNegativeIntegerSchema.nullable(),
  dailyTokenLimit: nonNegativeIntegerSchema.nullable(),
  storageBytes: nonNegativeIntegerSchema.nullable(),
}).strict();

export const subscriptionContextEnvelopeSchema = z.object({
  data: z.object({
    canonicalUser: z.object({ id: safeIdentifierSchema }).strict(),
    subscription: subscriptionSchema.nullable(),
    planVersion: planSummarySchema.nullable(),
    entitlements: z.array(contextEntitlementSchema),
    allowance: allowanceSchema.nullable(),
    asOf: isoTimestampSchema,
  }).strict(),
  meta: z.object({ requestId: safeIdentifierSchema }).strict(),
}).strict();

export const plansEnvelopeSchema = z.object({
  data: z.array(productPlanSchema),
  meta: z.object({
    total: nonNegativeIntegerSchema,
    page: positiveIntegerSchema,
    pageSize: positiveIntegerSchema,
    requestId: safeIdentifierSchema,
  }).strict(),
}).strict();

const usageItemSchema = z.object({
  gatewayRequestId: safeIdentifierSchema,
  modelAlias: safeIdentifierSchema,
  gatewayScope: safeIdentifierSchema,
  protocol: z.enum(['anthropic', 'openai']),
  outcome: z.enum(['completed', 'failed', 'cancelled', 'inProgress']),
  settlementState: z.enum(['settled', 'usageUnknown', 'inProgress', 'rejected']),
  inputTokens: nonNegativeIntegerSchema,
  outputTokens: nonNegativeIntegerSchema,
  cacheReadTokens: nonNegativeIntegerSchema,
  cacheWriteTokens: nonNegativeIntegerSchema,
  totalTokens: nonNegativeIntegerSchema,
  allowanceReservedTokens: nonNegativeIntegerSchema,
  allowanceConsumedTokens: nonNegativeIntegerSchema,
  allowanceReleasedTokens: nonNegativeIntegerSchema,
  occurredAt: isoTimestampSchema,
  errorCategory: safeIdentifierSchema.nullable(),
}).strict();

export const usageEnvelopeSchema = z.object({
  data: z.object({
    period: z.object({
      start: isoTimestampSchema,
      end: isoTimestampSchema,
      timezone: z.literal('UTC'),
    }).strict().nullable(),
    allowance: allowanceSchema.nullable(),
    summary: z.object({
      requestCount: nonNegativeIntegerSchema,
      inputTokens: nonNegativeIntegerSchema,
      outputTokens: nonNegativeIntegerSchema,
      cacheReadTokens: nonNegativeIntegerSchema,
      cacheWriteTokens: nonNegativeIntegerSchema,
      totalTokens: nonNegativeIntegerSchema,
      unknownUsageCount: nonNegativeIntegerSchema,
    }).strict(),
    projection: z.object({
      asOf: isoTimestampSchema,
      sampleWindowDays: nonNegativeIntegerSchema,
      projectedExhaustionAt: isoTimestampSchema.nullable(),
      projectedTokenShortfall: nonNegativeIntegerSchema.nullable(),
      confidence: z.literal('insufficientData'),
    }).strict(),
    items: z.array(usageItemSchema),
  }).strict(),
  meta: z.object({
    total: nonNegativeIntegerSchema,
    page: positiveIntegerSchema,
    pageSize: positiveIntegerSchema,
    requestId: safeIdentifierSchema,
  }).strict(),
}).strict();

const productModelSchema = z.object({
  modelAlias: safeIdentifierSchema,
  displayName: z.string().min(1).max(160),
  description: safeTextSchema.nullable(),
  capabilities: z.array(safeIdentifierSchema),
  contexts: z.array(safeIdentifierSchema),
  eligibility: z.object({
    allowed: z.literal(true),
    reasonCode: z.null(),
    subscriptionStatus: safeIdentifierSchema,
    gatewayScopes: z.array(safeIdentifierSchema),
    rpmLimit: nonNegativeIntegerSchema.nullable(),
    dailyTokenLimit: nonNegativeIntegerSchema.nullable(),
    storageBytes: nonNegativeIntegerSchema.nullable(),
    monthlyTokenRemaining: nonNegativeIntegerSchema,
    monthlyTokenResetAt: isoTimestampSchema,
  }).strict(),
  limits: z.object({
    contextWindow: nonNegativeIntegerSchema.nullable(),
    maxOutputTokens: nonNegativeIntegerSchema.nullable(),
  }).strict(),
  availability: z.literal('available'),
  asOf: isoTimestampSchema,
}).strict();

export const modelCatalogEnvelopeSchema = z.object({
  data: z.object({
    items: z.array(productModelSchema),
    asOf: isoTimestampSchema,
  }).strict(),
  meta: z.object({ requestId: safeIdentifierSchema }).strict(),
}).strict();

const commandPreviewSchema = z.object({
  action: productActionSchema,
  allowed: z.boolean(),
  reasonCode: safeIdentifierSchema.nullable(),
  previewId: safeIdentifierSchema,
  digest: safeIdentifierSchema,
  expiresAt: isoTimestampSchema,
  expectedVersion: positiveIntegerSchema.nullable(),
  current: planSummarySchema.nullable(),
  target: planSummarySchema.nullable(),
  appliesAt: isoTimestampSchema.nullable(),
  allowanceImpact: z.object({
    unit: z.literal('tokens'),
    currentPeriodTokens: nonNegativeIntegerSchema.nullable(),
    nextPeriodTokens: nonNegativeIntegerSchema.nullable(),
    currentPeriodChanges: z.boolean(),
  }).strict(),
  entitlementImpact: z.object({
    currentModelAliases: z.array(safeIdentifierSchema),
    targetModelAliases: z.array(safeIdentifierSchema),
  }).strict(),
  gatewayImpact: z.object({ callableAfterExecute: z.boolean() }).strict(),
  warnings: z.array(safeTextSchema),
}).strict();

export const commandPreviewEnvelopeSchema = z.object({
  data: commandPreviewSchema,
  meta: z.object({ requestId: safeIdentifierSchema }).strict(),
}).strict();

export const commandResultEnvelopeSchema = z.object({
  data: z.object({
    commandId: safeIdentifierSchema,
    outcome: z.enum(['applied', 'scheduled']),
    subscription: z.object({
      id: safeIdentifierSchema,
      status: safeIdentifierSchema,
      version: positiveIntegerSchema,
      planVersionId: safeIdentifierSchema,
      pendingPlanVersionId: safeIdentifierSchema.nullable(),
      currentPeriodStart: isoTimestampSchema,
      currentPeriodEnd: isoTimestampSchema,
    }).strict(),
    actualImpact: z.object({
      unit: z.literal('tokens'),
      appliesAt: isoTimestampSchema.nullable(),
      grantedTokens: nonNegativeIntegerSchema.nullable(),
      reservedTokens: nonNegativeIntegerSchema.nullable(),
      consumedTokens: nonNegativeIntegerSchema.nullable(),
      remainingTokens: nonNegativeIntegerSchema.nullable(),
    }).strict(),
    idempotentReplay: z.boolean(),
  }).strict(),
  meta: z.object({ requestId: safeIdentifierSchema }).strict(),
}).strict();

const productErrorDetailsSchema = z.object({
  field: safeTextSchema.nullable().optional(),
  issues: z.array(z.object({
    code: safeIdentifierSchema,
    path: z.array(z.string()),
    message: safeTextSchema,
  }).strict()).nullable().optional(),
  expectedVersion: nonNegativeIntegerSchema.nullable().optional(),
  actualVersion: nonNegativeIntegerSchema.nullable().optional(),
  periodEnd: isoTimestampSchema.nullable().optional(),
  status: safeIdentifierSchema.nullable().optional(),
  reasonCode: safeIdentifierSchema.nullable().optional(),
  metric: z.literal('tokens').nullable().optional(),
  unit: z.literal('tokens').nullable().optional(),
  availableTokens: nonNegativeIntegerSchema.nullable().optional(),
  requiredTokens: nonNegativeIntegerSchema.nullable().optional(),
  modelAlias: safeIdentifierSchema.nullable().optional(),
  gatewayScope: safeIdentifierSchema.nullable().optional(),
  requiredScope: safeIdentifierSchema.nullable().optional(),
  retryable: z.boolean().nullable().optional(),
  window: safeIdentifierSchema.nullable().optional(),
  current: nonNegativeIntegerSchema.nullable().optional(),
  limit: nonNegativeIntegerSchema.nullable().optional(),
  remaining: nonNegativeIntegerSchema.nullable().optional(),
}).strict();

const productErrorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string().regex(/^[A-Z][A-Z0-9_]{1,99}$/),
    message: safeTextSchema,
    details: productErrorDetailsSchema.optional(),
  }).strict(),
  meta: z.object({
    requestId: safeIdentifierSchema,
    retryAfterSeconds: z.number().int().min(0).max(86_400).optional(),
  }).strict(),
}).strict();

export type ProductAction = z.infer<typeof productActionSchema>;
export type SubscriptionContextEnvelope = z.infer<typeof subscriptionContextEnvelopeSchema>;
export type PlansEnvelope = z.infer<typeof plansEnvelopeSchema>;
export type ProductPlan = PlansEnvelope['data'][number];
export type UsageEnvelope = z.infer<typeof usageEnvelopeSchema>;
export type ModelCatalogEnvelope = z.infer<typeof modelCatalogEnvelopeSchema>;
export type CommandPreviewEnvelope = z.infer<typeof commandPreviewEnvelopeSchema>;
export type CommandResultEnvelope = z.infer<typeof commandResultEnvelopeSchema>;
export type ProductErrorDetails = z.infer<typeof productErrorDetailsSchema>;

export interface PreviewProductCommand {
  action: ProductAction;
  phase: 'preview';
  targetPlanVersionId: string | null;
  expectedVersion: number | null;
}

export interface ExecuteProductCommand {
  action: ProductAction;
  phase: 'execute';
  targetPlanVersionId: string | null;
  expectedVersion: number | null;
  previewId: string;
  digest: string;
  expiresAt: string;
  reason: string;
}

export type ProductCommand = PreviewProductCommand | ExecuteProductCommand;

export interface ProductRequestOptions {
  fetchImpl?: typeof fetch;
  token?: string | null;
  signal?: AbortSignal;
  resolveUrl?: (path: string) => string;
}

export interface ProductCommandRequestOptions extends ProductRequestOptions {
  idempotencyKey?: string;
}

const targetPlanVersionIdSchema = z.string()
  .min(1)
  .max(100)
  .regex(/^[A-Za-z0-9][A-Za-z0-9._:-]*$/)
  .nullable();
const previewCommandSchema = z.object({
  action: productActionSchema,
  phase: z.literal('preview'),
  targetPlanVersionId: targetPlanVersionIdSchema,
  expectedVersion: z.number().int().min(1).max(2_147_483_647).nullable(),
}).strict();
const executeCommandSchema = z.object({
  action: productActionSchema,
  phase: z.literal('execute'),
  targetPlanVersionId: targetPlanVersionIdSchema,
  expectedVersion: z.number().int().min(1).max(2_147_483_647).nullable(),
  previewId: z.string().regex(/^preview_[A-Za-z0-9_-]{22}$/),
  digest: z.string().regex(/^sha256:[A-Za-z0-9_-]{43}$/),
  expiresAt: isoTimestampSchema,
  reason: z.string().trim().min(3).max(500),
}).strict();

export class ProductApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: ProductErrorDetails | null;
  readonly requestId: string | null;
  readonly retryAfterSeconds: number | null;

  constructor(input: {
    code: string;
    status: number;
    message: string;
    details?: ProductErrorDetails | null;
    requestId?: string | null;
    retryAfterSeconds?: number | null;
  }) {
    super(input.message);
    this.name = 'ProductApiError';
    this.code = input.code;
    this.status = input.status;
    this.details = input.details ?? null;
    this.requestId = input.requestId ?? null;
    this.retryAfterSeconds = input.retryAfterSeconds ?? null;
  }
}

function contractError(): ProductApiError {
  return new ProductApiError({
    code: 'PRODUCT_RESPONSE_CONTRACT_INVALID',
    status: 503,
    message: '订阅服务返回了不安全或不完整的数据。',
  });
}

function requestHeaders(hasBody: boolean, tokenOverride: string | null | undefined): Headers {
  const headers = new Headers({ Accept: 'application/json' });
  const token = tokenOverride === undefined ? getAuthToken() : tokenOverride;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (hasBody) headers.set('Content-Type', 'application/json');
  return headers;
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text.length > 1_048_576) throw contractError();
  try {
    return text.length > 0 ? JSON.parse(text) : null;
  } catch {
    throw contractError();
  }
}

async function requestProduct<T>(
  path: string,
  schema: z.ZodType<T>,
  options: ProductRequestOptions,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  const headers = requestHeaders(init.body !== undefined, options.token);
  new Headers(init.headers).forEach((value, key) => headers.set(key, value));
  try {
    response = await (options.fetchImpl ?? fetch)(
      options.resolveUrl ? options.resolveUrl(path) : apiUrl(path),
      {
      ...init,
      credentials: 'include',
      headers,
      signal: options.signal,
      },
    );
  } catch (cause) {
    if (typeof DOMException !== 'undefined' && cause instanceof DOMException && cause.name === 'AbortError') throw cause;
    throw new ProductApiError({
      code: 'PRODUCT_DEPENDENCY_UNAVAILABLE',
      status: 503,
      message: '订阅服务暂时不可用。',
    });
  }

  const payload = await readJson(response);
  if (!response.ok) {
    const parsedError = productErrorEnvelopeSchema.safeParse(payload);
    if (!parsedError.success) throw contractError();
    if (response.status === 402) {
      const details = parsedError.data.error.details;
      if (
        parsedError.data.error.code !== 'SUBSCRIPTION_TOKEN_ALLOWANCE_EXHAUSTED'
        || details?.metric !== 'tokens'
        || details.unit !== 'tokens'
        || details.availableTokens === undefined
        || details.availableTokens === null
        || details.requiredTokens === undefined
        || details.requiredTokens === null
        || !details.periodEnd
      ) {
        throw contractError();
      }
    }
    throw new ProductApiError({
      code: parsedError.data.error.code,
      status: response.status,
      message: parsedError.data.error.message,
      details: parsedError.data.error.details ?? null,
      requestId: parsedError.data.meta.requestId,
      retryAfterSeconds: parsedError.data.meta.retryAfterSeconds ?? null,
    });
  }

  const parsed = schema.safeParse(payload);
  if (!parsed.success) throw contractError();
  return parsed.data;
}

export function fetchProductSubscriptionContext(
  options: ProductRequestOptions = {},
): Promise<SubscriptionContextEnvelope> {
  return requestProduct(PRODUCT_BFF_ENDPOINTS.context, subscriptionContextEnvelopeSchema, options);
}

export function fetchProductPlans(
  input: { page: number; pageSize: number },
  options: ProductRequestOptions = {},
): Promise<PlansEnvelope> {
  const params = new URLSearchParams({
    page: String(input.page),
    pageSize: String(input.pageSize),
  });
  return requestProduct(`${PRODUCT_BFF_ENDPOINTS.plans}?${params}`, plansEnvelopeSchema, options);
}

export function fetchProductUsage(
  input: { page: number; pageSize: number },
  options: ProductRequestOptions = {},
): Promise<UsageEnvelope> {
  const params = new URLSearchParams({
    period: 'current_subscription_period',
    sort: 'occurredAt',
    order: 'desc',
    page: String(input.page),
    pageSize: String(input.pageSize),
  });
  return requestProduct(`${PRODUCT_BFF_ENDPOINTS.usage}?${params}`, usageEnvelopeSchema, options);
}

export function fetchProductModelCatalog(
  options: ProductRequestOptions = {},
): Promise<ModelCatalogEnvelope> {
  return requestProduct(PRODUCT_BFF_ENDPOINTS.models, modelCatalogEnvelopeSchema, options);
}

function assertCommandShape(command: ProductCommand): void {
  const requiresTarget = command.action === 'create'
    || command.action === 'upgrade'
    || command.action === 'downgrade';
  if (requiresTarget !== (command.targetPlanVersionId !== null)) {
    throw new TypeError('The command target does not match the action.');
  }
  if (command.action === 'create' && command.expectedVersion !== null) {
    throw new TypeError('Create commands must not carry a subscription version.');
  }
  if (command.action !== 'create' && command.expectedVersion === null) {
    throw new TypeError('The command requires the current subscription version.');
  }
}

export function submitProductSubscriptionCommand(
  command: PreviewProductCommand,
  options?: ProductCommandRequestOptions,
): Promise<CommandPreviewEnvelope>;
export function submitProductSubscriptionCommand(
  command: ExecuteProductCommand,
  options: ProductCommandRequestOptions & { idempotencyKey: string },
): Promise<CommandResultEnvelope>;
export function submitProductSubscriptionCommand(
  command: ProductCommand,
  options: ProductCommandRequestOptions = {},
): Promise<CommandPreviewEnvelope | CommandResultEnvelope> {
  assertCommandShape(command);
  if (command.phase === 'preview' && options.idempotencyKey !== undefined) {
    throw new TypeError('Preview commands cannot carry an idempotency key.');
  }
  if (command.phase === 'execute' && !/^[A-Za-z0-9._~-]{8,128}$/.test(options.idempotencyKey ?? '')) {
    throw new TypeError('Execute commands require a valid idempotency key.');
  }
  const headers = requestHeaders(true, options.token);
  if (command.phase === 'preview') {
    return requestProduct(PRODUCT_BFF_ENDPOINTS.commands, commandPreviewEnvelopeSchema, options, {
      method: 'POST',
      headers,
      body: JSON.stringify(previewCommandSchema.parse(command)),
    });
  }
  headers.set('Idempotency-Key', options.idempotencyKey!);
  return requestProduct(PRODUCT_BFF_ENDPOINTS.commands, commandResultEnvelopeSchema, options, {
    method: 'POST',
    headers,
    body: JSON.stringify(executeCommandSchema.parse(command)),
  });
}
