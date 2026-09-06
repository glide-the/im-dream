// [Input] Untrusted MCP Apps status candidates.
// [Output] Focused compatibility, lifecycle, and independent-origin assertions.
// [Pos] Provider-free Browser Host policy contract test.
// [Sync] 2026-09-06: lock plugin plus independent runtime-policy identity, lifecycle, origin, and capability boundaries.
// [Sync] 2026-09-06: lock connection App-settings revision into Host policy identity.

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  MCP_APPS_HOST_MANIFEST,
  mcpAppsPolicyIdentity,
  parseMcpAppsHostPolicy,
} from './host-policy.ts';

function status(overrides: Record<string, unknown> = {}) {
  return {
    productionAppsEffective: false,
    manifest: MCP_APPS_HOST_MANIFEST,
    default: {
      enabled: false,
      features: { readResource: false, appToolCalls: false, uiMessage: false, windowIm: false },
    },
    desired: {
      enabled: true,
      features: { readResource: true, appToolCalls: true, uiMessage: true, windowIm: true },
    },
    plugin: {
      manifestVersion: 1,
      pluginId: MCP_APPS_HOST_MANIFEST.pluginId,
      pluginVersion: MCP_APPS_HOST_MANIFEST.version,
      revision: 7,
      lifecycle: 'enabled',
      browserEntry: MCP_APPS_HOST_MANIFEST.browserEntry,
      nodeEntry: MCP_APPS_HOST_MANIFEST.nodeEntry,
      features: {
        resourceReads: true,
        lowRiskToolCalls: true,
        uiMessage: true,
        windowIm: true,
      },
    },
    effective: {
      enabled: true,
      features: { readResource: true, appToolCalls: true, uiMessage: true, windowIm: true },
    },
    policy: {
      revision: '7:11',
      pluginRevision: '7',
      runtimePolicyRevision: 11,
      appSettingsRevision: null,
      manifestVersion: MCP_APPS_HOST_MANIFEST.version,
      sandboxUrl: 'http://127.0.0.1:43191/mcp-apps-sandbox?v=1.0.0&revision=7',
      sandboxTokens: ['allow-scripts'],
      desiredPermissions: [],
      effectivePermissions: [],
      readyTimeoutMs: 10_000,
      policyPollMs: 2_000,
    },
    ...overrides,
  };
}

test('accepts one compatible, independently-originated effective snapshot', () => {
  const parsed = parseMcpAppsHostPolicy(status(), 'http://127.0.0.1:43190');
  assert.ok(parsed);
  assert.equal(parsed.sandboxOrigin, 'http://127.0.0.1:43191');
  assert.equal(parsed.features.appToolCalls, true);
});

test('rejects same-origin, disabled, and incompatible or stale plugin snapshots', () => {
  assert.equal(parseMcpAppsHostPolicy(status({
    policy: { ...(status().policy as Record<string, unknown>), sandboxUrl: 'http://127.0.0.1:43190/mcp-apps-sandbox' },
  }), 'http://127.0.0.1:43190'), null);
  assert.equal(parseMcpAppsHostPolicy(status({ effective: { enabled: false, features: {} } }), 'http://127.0.0.1:43190'), null);
  assert.equal(parseMcpAppsHostPolicy(status({
    manifest: { ...MCP_APPS_HOST_MANIFEST, version: '2.0.0' },
  }), 'http://127.0.0.1:43190'), null);
  assert.equal(parseMcpAppsHostPolicy(status({
    plugin: { ...(status().plugin as Record<string, unknown>), lifecycle: 'disabled' },
  }), 'http://127.0.0.1:43190'), null);
  assert.equal(parseMcpAppsHostPolicy(status({
    policy: { ...(status().policy as Record<string, unknown>), revision: '8:11' },
  }), 'http://127.0.0.1:43190'), null);
  assert.equal(parseMcpAppsHostPolicy(status({
    desired: { enabled: false, features: (status().desired as Record<string, unknown>).features },
  }), 'http://127.0.0.1:43190'), null);
  assert.equal(parseMcpAppsHostPolicy(status({
    desired: {
      enabled: true,
      features: { readResource: true, appToolCalls: true, uiMessage: false, windowIm: false },
    },
    effective: {
      enabled: true,
      features: { readResource: true, appToolCalls: true, uiMessage: true, windowIm: false },
    },
  }), 'http://127.0.0.1:43190'), null);
  assert.equal(parseMcpAppsHostPolicy(status({
    policy: {
      ...(status().policy as Record<string, unknown>),
      sandboxUrl: 'http://127.0.0.1:43191/mcp-apps-sandbox?v=1.0.0&revision=6',
    },
  }), 'http://127.0.0.1:43190'), null);
  assert.equal(parseMcpAppsHostPolicy(status({
    plugin: {
      ...(status().plugin as Record<string, unknown>),
      features: {
        resourceReads: true,
        lowRiskToolCalls: false,
        uiMessage: false,
        windowIm: false,
      },
    },
  }), 'http://127.0.0.1:43190'), null);
});

test('policy identity changes on revision, feature, or sandbox deployment changes', () => {
  const first = parseMcpAppsHostPolicy(status(), 'http://127.0.0.1:43190');
  const second = parseMcpAppsHostPolicy(status({
    plugin: { ...(status().plugin as Record<string, unknown>), revision: 8 },
    policy: {
      ...(status().policy as Record<string, unknown>),
      revision: '8:12',
      pluginRevision: '8',
      runtimePolicyRevision: 12,
      sandboxUrl: 'http://127.0.0.1:43191/mcp-apps-sandbox?v=1.0.0&revision=8',
    },
  }), 'http://127.0.0.1:43190');
  assert.ok(first && second);
  assert.notEqual(mcpAppsPolicyIdentity(first), mcpAppsPolicyIdentity(second));

  const policyOnly = parseMcpAppsHostPolicy(status({
    policy: {
      ...(status().policy as Record<string, unknown>),
      revision: '7:12',
      runtimePolicyRevision: 12,
    },
  }), 'http://127.0.0.1:43190');
  assert.ok(policyOnly);
  assert.notEqual(mcpAppsPolicyIdentity(first), mcpAppsPolicyIdentity(policyOnly));

  const connectionSettingsOnly = parseMcpAppsHostPolicy(status({
    policy: {
      ...(status().policy as Record<string, unknown>),
      revision: '7:11:3',
      appSettingsRevision: 3,
    },
  }), 'http://127.0.0.1:43190');
  assert.ok(connectionSettingsOnly);
  assert.notEqual(mcpAppsPolicyIdentity(first), mcpAppsPolicyIdentity(connectionSettingsOnly));
});
