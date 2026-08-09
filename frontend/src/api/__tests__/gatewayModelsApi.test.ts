import { expect, test } from '@playwright/test';
import { GatewayModelsApiError, parseGatewayModelCatalog } from '../gatewayModelsApi';

const catalog = {
  data: [{
    modelAlias: 'dream-balanced',
    displayName: 'Dream Balanced',
    protocol: 'anthropic',
    capabilities: { tools: true },
    contextWindow: 200000,
    maxOutputTokens: 8192,
    enabled: true,
    callable: true,
    availability: 'included',
    requiredPlanCode: 'free',
    upgradeHint: null,
  }, {
    modelAlias: 'dream-premium',
    displayName: 'Dream Premium',
    protocol: 'openai',
    capabilities: { tools: true },
    contextWindow: null,
    maxOutputTokens: null,
    enabled: true,
    callable: false,
    availability: 'upgrade_required',
    requiredPlanCode: 'dream',
    upgradeHint: '升级 Dream 后可用',
  }],
  defaultModelAlias: 'dream-balanced',
} as const;

test('catalog preserves visible locked models and a callable Free default', () => {
  const parsed = parseGatewayModelCatalog(catalog);
  expect(parsed.defaultModelAlias).toBe('dream-balanced');
  expect(parsed.models.map((model) => [model.modelAlias, model.callable])).toEqual([
    ['dream-balanced', true],
    ['dream-premium', false],
  ]);
});

test('catalog fails closed on legacy scope fields or missing availability metadata', () => {
  const legacy = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>> };
  legacy.data[0].gatewayScopes = ['messages:create'];
  expect(() => parseGatewayModelCatalog(legacy)).toThrow(GatewayModelsApiError);
  const missing = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>> };
  delete missing.data[0].availability;
  expect(() => parseGatewayModelCatalog(missing)).toThrow(GatewayModelsApiError);
});
