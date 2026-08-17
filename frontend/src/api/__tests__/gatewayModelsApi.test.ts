// [Input] Gateway model catalog payloads and frontend effective-selection helper.
// [Output] Verify strict catalog validation and Admin-default selection for new users.
// [Pos] gateway model API contract test in frontend/src/api/__tests__
// [Sync] 2026-08-14: cover callable Admin default fallback and invalid default rejection.

import { expect, test } from '@playwright/test';
import {
  GatewayModelsApiError,
  parseGatewayModelCatalog,
  resolveGatewayModelSelection,
} from '../gatewayModelsApi';

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

test('new users use the Admin callable default without creating a browser default', () => {
  const parsed = parseGatewayModelCatalog(catalog);
  expect(resolveGatewayModelSelection(undefined, parsed)).toBe('dream-balanced');
  expect(resolveGatewayModelSelection('', parsed)).toBe('dream-balanced');
  expect(resolveGatewayModelSelection('dream-premium', parsed)).toBe('dream-premium');
});

test('catalog rejects a default alias that is absent or not callable', () => {
  const lockedDefault = structuredClone(catalog) as unknown as {
    defaultModelAlias: string;
  };
  lockedDefault.defaultModelAlias = 'dream-premium';
  expect(() => parseGatewayModelCatalog(lockedDefault)).toThrow(GatewayModelsApiError);
});

test('catalog fails closed on legacy scope fields or missing availability metadata', () => {
  const legacy = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>> };
  legacy.data[0].gatewayScopes = ['messages:create'];
  expect(() => parseGatewayModelCatalog(legacy)).toThrow(GatewayModelsApiError);
  const missing = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>> };
  delete missing.data[0].availability;
  expect(() => parseGatewayModelCatalog(missing)).toThrow(GatewayModelsApiError);
});
