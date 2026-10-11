// [Sync] 2026-10-10: independent Image model selection and endpoint-specific capability/eligibility with explicit recovery.
// [Sync] 2026-09-14: same-origin Cookie session with in-memory CSRF; no Browser OAuth Bearer/storage.
// [Sync] 2026-10-10: subscription inclusion does not imply Messages callability; omit explicitly non-chat models.
import { browserRequestHeaders } from '../lib/browserSession';
// [Input] Browser session and CSRF and Dream same-origin Gateway models BFF.
// [Output] Strict platform model catalog DTOs and effective saved/default
//          selection resolution for Settings controls.
// [Pos] frontend API boundary for Admin public Gateway models.
// [Sync] 2026-08-14: use Admin's callable defaultModelAlias when a new user
//                    has not saved an explicit model preference.
import { z } from 'zod';

import { API_BASE } from '../lib/apiBase';

const aliasSchema = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$/);

function isConversationModel(model: { capabilities: Record<string, boolean>; images?: { generation: boolean; edit: boolean } }): boolean {
  return model.capabilities.chat !== false && (
    !(model.images?.generation || model.images?.edit) || model.capabilities.chat === true
  );
}

const imageAvailabilitySchema = z.object({
  generation: z.boolean(), edit: z.boolean(), configured: z.boolean(),
  entitled: z.boolean(), callable: z.boolean(),
}).strict().superRefine((image, context) => {
  if (image.callable && (!image.configured || !image.entitled || !(image.generation || image.edit))) {
    context.addIssue({ code: 'custom', message: 'Callable image operation requires capability, configuration and entitlement.' });
  }
});

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
  images: imageAvailabilitySchema.optional(),
  responsesImage: imageAvailabilitySchema.optional(),
}).strict().superRefine((model, context) => {
  if ((model.callable || model.images?.callable || model.responsesImage?.callable) && model.availability !== 'included') {
    context.addIssue({ code: 'custom', path: ['callable'], message: 'Callable requires included availability.' });
  }
  if (model.responsesImage?.callable && (!model.callable || !isConversationModel(model))) {
    context.addIssue({ code: 'custom', path: ['responsesImage'], message: 'Responses images require a callable conversation model.' });
  }
});

const gatewayModelsEnvelopeSchema = z.object({
  data: z.array(gatewayModelSchema),
  defaultModelAlias: aliasSchema.nullable(),
}).strict().superRefine((catalog, context) => {
  if (
    catalog.defaultModelAlias !== null
    && !catalog.data.some(
      (model) => model.modelAlias === catalog.defaultModelAlias && model.callable && isConversationModel(model),
    )
  ) {
    context.addIssue({
      code: 'custom',
      path: ['defaultModelAlias'],
      message: 'Default model must be present and callable.',
    });
  }
});

export type GatewayModel = z.infer<typeof gatewayModelSchema>;
export type GatewayModelCatalog = {
  models: GatewayModel[];
  imageModels: GatewayModel[];
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
  return {
    models: parsed.data.data.filter(isConversationModel),
    imageModels: parsed.data.data.filter(model => model.images?.generation || model.images?.edit),
    defaultModelAlias: parsed.data.defaultModelAlias,
  };
}

export function imageModelAvailabilityMessage(model: GatewayModel): string | null {
  if (model.images?.callable) return null;
  if (model.availability === 'allowance_exhausted') return '额度已用完，请查看订阅与额度。';
  if (model.availability === 'permission_denied') return '当前账号没有图片调用权限。';
  if (!model.images?.configured) return '图片模型配置未就绪，请联系管理员或选择其他模型。';
  if (!model.images.entitled) return '当前图片调用资格不足，请查看订阅。';
  return model.upgradeHint ?? '图片模型暂不可用，请重新加载或选择其他模型。';
}

export function resolveGatewayModelSelection(
  savedModelAlias: string | null | undefined,
  catalog: GatewayModelCatalog,
): string {
  const saved = savedModelAlias?.trim() ?? '';
  if (saved) return saved;
  const fallback = catalog.defaultModelAlias;
  return fallback && catalog.models.some(
    (model) => model.modelAlias === fallback && model.callable,
  ) ? fallback : '';
}

export async function fetchGatewayModels(signal?: AbortSignal): Promise<GatewayModelCatalog> {
  const response = await fetch(`${API_BASE}/api/gateway/models`, {
    headers: { ...browserRequestHeaders() },
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
