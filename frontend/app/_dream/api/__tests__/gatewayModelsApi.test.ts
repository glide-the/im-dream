// [Sync] 2026-10-10: independent Image model selection and endpoint-specific capability/eligibility with explicit recovery.
// [Input] Gateway model catalog payloads and frontend effective-selection helper.
// [Output] Verify strict catalog validation and Admin-default selection for new users.
// [Pos] gateway model API contract test in frontend/app/_dream/api/__tests__
// [Sync] 2026-08-14: cover callable Admin default fallback and invalid default rejection.
// [Sync] 2026-10-10: keep included-but-uncallable Messages models from invalidating the complete catalog.

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

test('included subscription models may be uncallable for Messages without hiding available models', () => {
  const input = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>>; defaultModelAlias: string };
  input.data.push({ ...input.data[0], modelAlias: 'included-chat-locked', callable: false });
  input.data.push({ ...input.data[0], modelAlias: 'image-only', callable: false, capabilities: { chat: false } });
  const parsed = parseGatewayModelCatalog(input);
  expect(parsed.models.map(model => model.modelAlias)).toEqual(['dream-balanced', 'dream-premium', 'included-chat-locked']);
  expect(parsed.models.find(model => model.modelAlias === 'included-chat-locked')?.callable).toBe(false);
  expect(resolveGatewayModelSelection(undefined, parsed)).toBe('dream-balanced');
});

test('callable still requires an included subscription and default still requires a text model', () => {
  const input = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>>; defaultModelAlias: string };
  input.data[1].callable = true;
  expect(() => parseGatewayModelCatalog(input)).toThrow(GatewayModelsApiError);
  input.data[1].callable = false;
  input.data[0].capabilities = { chat: false };
  expect(() => parseGatewayModelCatalog(input)).toThrow(GatewayModelsApiError);
});


test('Images-only candidates are independent and never imply native Responses capability', () => {
  const input = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>> };
  input.data.push({ ...input.data[0], modelAlias: 'image-a', capabilities: { chat: false }, callable: false,
    images: { generation: true, edit: true, configured: true, entitled: true, callable: true },
    responsesImage: { generation: false, edit: false, configured: false, entitled: true, callable: false } });
  const parsed = parseGatewayModelCatalog(input);
  expect(parsed.imageModels.map(model => model.modelAlias)).toEqual(['image-a']);
  expect(parsed.models.some(model => model.modelAlias === 'image-a')).toBe(false);
  expect(parsed.imageModels[0].responsesImage?.generation).toBe(false);
  expect(parseGatewayModelCatalog(catalog).imageModels).toEqual([]);
});

test('image callability fails closed on missing prerequisites and native text eligibility', () => {
  for (const field of ['images', 'responsesImage']) {
    const input = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>> };
    input.data[0][field] = { generation: true, edit: true, configured: false, entitled: true, callable: true };
    expect(() => parseGatewayModelCatalog(input)).toThrow(GatewayModelsApiError);
  }
  const input = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>> };
  input.data[1].responsesImage = { generation: true, edit: true, configured: true, entitled: true, callable: true };
  expect(() => parseGatewayModelCatalog(input)).toThrow(GatewayModelsApiError);
});

test('legacy Images capabilities without an explicit chat capability never become AI candidates or defaults', () => {
  const input = structuredClone(catalog) as unknown as { data: Array<Record<string, unknown>>; defaultModelAlias: string };
  input.data.push({ ...input.data[0], modelAlias: 'legacy-image', capabilities: { image_generation: true, image_edit: true },
    images: { generation: true, edit: true, configured: true, entitled: true, callable: true } });
  const parsed = parseGatewayModelCatalog(input);
  expect(parsed.models.some(model => model.modelAlias === 'legacy-image')).toBe(false);
  expect(parsed.imageModels.map(model => model.modelAlias)).toEqual(['legacy-image']);
  input.defaultModelAlias = 'legacy-image';
  expect(() => parseGatewayModelCatalog(input)).toThrow(GatewayModelsApiError);
});
