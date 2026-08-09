// [Input] Auth token and Dream same-origin Gateway models BFF.
// [Output] Strict platform model catalog DTOs for Settings controls.
// [Pos] frontend API boundary for Admin public Gateway models.
import { z } from 'zod';
import { getAuthToken } from '../contexts/AuthContext';
import { API_BASE } from '../lib/apiBase';

const aliasSchema = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$/);

const gatewayModelSchema = z.object({
  modelAlias: aliasSchema,
  displayName: z.string().min(1).max(160),
  protocol: z.enum(['anthropic', 'openai']),
  capabilities: z.record(z.string(), z.boolean()),
  contextWindow: z.number().int().nonnegative().nullable(),
  maxOutputTokens: z.number().int().nonnegative().nullable(),
  enabled: z.literal(true),
  callable: z.boolean(),
  availability: z.enum([
    'included',
    'upgrade_required',
    'subscription_inactive',
    'allowance_exhausted',
    'permission_denied',
    'maintenance',
  ]),
  requiredPlanCode: aliasSchema.nullable(),
  upgradeHint: z.string().min(1).max(240).nullable(),
}).strict().superRefine((model, context) => {
  if (model.callable !== (model.availability === 'included')) {
    context.addIssue({ code: 'custom', path: ['callable'], message: 'Callable must match included availability.' });
  }
});

const gatewayModelsEnvelopeSchema = z.object({
  data: z.array(gatewayModelSchema),
  defaultModelAlias: aliasSchema.nullable(),
}).strict();

export type GatewayModel = z.infer<typeof gatewayModelSchema>;
export type GatewayModelCatalog = {
  models: GatewayModel[];
  defaultModelAlias: string | null;
};

export class GatewayModelsApiError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`Gateway model catalog request failed (${status})`);
    this.status = status;
  }
}

export function parseGatewayModelCatalog(payload: unknown): GatewayModelCatalog {
  const parsed = gatewayModelsEnvelopeSchema.safeParse(payload);
  if (!parsed.success) throw new GatewayModelsApiError(502);
  return { models: parsed.data.data, defaultModelAlias: parsed.data.defaultModelAlias };
}

export async function fetchGatewayModels(signal?: AbortSignal): Promise<GatewayModelCatalog> {
  const response = await fetch(`${API_BASE}/api/gateway/models`, {
    headers: { Authorization: `Bearer ${getAuthToken()}` },
    signal,
  });
  if (!response.ok) throw new GatewayModelsApiError(response.status);
  return parseGatewayModelCatalog(await response.json());
}

export function gatewayModelsErrorMessage(error: unknown): string {
  const status = error instanceof GatewayModelsApiError ? error.status : 503;
  if (status === 401) return '登录已失效，请重新登录后重试。';
  if (status === 402) return 'Token 额度不足，请查看当前周期用量。';
  if (status === 403) return '当前操作没有模型权限。';
  if (status === 409) return '已保存的模型已失效，请重新选择。';
  if (status === 429) return '请求过于频繁，请稍后重试。';
  if (status === 502) return '平台模型目录响应异常，请稍后重试。';
  return '平台模型目录暂不可用，请稍后重试。';
}
