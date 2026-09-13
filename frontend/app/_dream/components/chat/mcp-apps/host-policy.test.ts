// [Input] Untrusted MCP Apps status candidates.
// [Output] Focused compatibility, lifecycle, dynamic-entry and opaque-origin assertions.
// [Pos] Provider-free Browser Host policy contract test.
// [Sync] 2026-09-06: lock plugin plus independent runtime-policy identity, lifecycle, origin, and capability boundaries.
// [Sync] 2026-09-06: lock connection App-settings revision into Host policy identity.
// [Sync] 2026-09-13: cover relative sandbox URLs across frontend ports/protocols and forbid permission or target-origin expansion.

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  MCP_APPS_HOST_MANIFEST,
  mcpAppsSandboxUrl,
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
      sandboxUrl: mcpAppsSandboxUrl('7'),
      sandboxTokens: ['allow-scripts'],
      desiredPermissions: [],
      effectivePermissions: [],
      readyTimeoutMs: 10_000,
      policyPollMs: 2_000,
    },
    ...overrides,
  };
}

test('accepts one compatible snapshot with an opaque sandbox at the current frontend entry', () => {
  const parsed = parseMcpAppsHostPolicy(status(), 'http://127.0.0.1:43190');
  assert.ok(parsed);
  assert.equal(parsed.sandboxUrl, 'http://127.0.0.1:43190/mcp-apps-sandbox?v=1.0.0&revision=7');
  assert.equal(parsed.sandboxOrigin, 'null');
  assert.equal(parsed.features.appToolCalls, true);
});

test('rejects unversioned routes, disabled, and incompatible or stale plugin snapshots', () => {
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
      sandboxUrl: '/mcp-apps-sandbox?v=1.0.0&revision=6',
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
      sandboxUrl: mcpAppsSandboxUrl('8'),
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

test('sandbox address follows frontend scheme, hostname and port without a configured listener', () => {
  for (const origin of ['http://localhost:5173', 'http://127.0.0.1:42871', 'https://dream.example.test']) {
    const policy = parseMcpAppsHostPolicy(status(), origin);
    assert.ok(policy);
    assert.equal(new URL(policy.sandboxUrl).origin, origin);
    assert.equal(new URL(policy.sandboxUrl).pathname, '/mcp-apps-sandbox');
    assert.equal(policy.sandboxOrigin, 'null');
    assert.deepEqual(policy.sandboxTokens, ['allow-scripts']);
  }
});

test('same-entry support cannot select an unrelated origin/route or grant same-origin access', () => {
  for (const sandboxUrl of ['http://localhost:5174/mcp-apps-sandbox?v=1.0.0&revision=7',
    '//external.example.test/mcp-apps-sandbox?v=1.0.0&revision=7',
    '/api/me?v=1.0.0&revision=7', '/mcp-apps-sandbox?v=1.0.0&revision=7#fragment']) {
    assert.equal(parseMcpAppsHostPolicy(status({
      policy: { ...status().policy, sandboxUrl },
    }), 'http://localhost:5173'), null);
  }
  for (const sandboxTokens of [[], ['allow-scripts', 'allow-same-origin'], ['allow-scripts', 'allow-forms']]) {
    assert.equal(parseMcpAppsHostPolicy(status({
      policy: { ...status().policy, sandboxTokens },
    }), 'http://localhost:5173'), null);
  }
});
