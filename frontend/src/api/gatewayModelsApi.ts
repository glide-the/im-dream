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
  gatewayScopes: z.array(aliasSchema),
  contextWindow: z.number().int().nonnegative().nullable(),
  maxOutputTokens: z.number().int().nonnegative().nullable(),
}).strict();

const gatewayModelsEnvelopeSchema = z.object({
  data: z.array(gatewayModelSchema),
}).strict();

export type GatewayModel = z.infer<typeof gatewayModelSchema>;

export class GatewayModelsApiError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`Gateway model catalog request failed (${status})`);
    this.status = status;
  }
}

export async function fetchGatewayModels(signal?: AbortSignal): Promise<GatewayModel[]> {
  const response = await fetch(`${API_BASE}/api/gateway/models`, {
    headers: { Authorization: `Bearer ${getAuthToken()}` },
    signal,
  });
  if (!response.ok) throw new GatewayModelsApiError(response.status);
  const parsed = gatewayModelsEnvelopeSchema.safeParse(await response.json());
  if (!parsed.success) throw new GatewayModelsApiError(502);
  return parsed.data.data;
}

export function gatewayModelsErrorMessage(error: unknown): string {
  const status = error instanceof GatewayModelsApiError ? error.status : 503;
  if (status === 401) return '登录已失效，请重新登录后重试。';
  if (status === 402) return 'Token 额度不足，模型目录暂不可用。';
  if (status === 403) return '当前订阅没有可用模型权限。';
  if (status === 429) return '请求过于频繁，请稍后重试。';
  return '平台模型目录暂不可用，请稍后重试。';
}
