// [Input] Claude MCP terminal-state and auth projections.
// [Output] Deterministic OAuth start/reauthorize action policy evidence.
// [Pos] Pure UI policy test; no browser login, remote MCP server or credential mutation.
// [Sync] 2026-09-16: cover failed-refresh reauthorization without forced logout.
import { expect, test } from '@playwright/test';
import type { ClaudeMcpServer, ClaudeMcpState } from '../../api/claudeMcpApi';
import { canStartClaudeMcpAuth, claudeMcpAuthActionLabel } from './authPolicy';

function server(overrides: Partial<ClaudeMcpServer> = {}): ClaudeMcpServer {
  return {
    name: 'oauth-server', state: 'configured', auth_state: 'authenticated',
    transport: 'streamable_http', detail: null, active_operation_id: null,
    config_scope: 'user', removable: true, id: 'server-1', display_name: 'OAuth server',
    auth_kind: 'oauth', enabled: true, revision: 1, credential_revision: 2,
    credential_ref: 'credential-1', credential_configured: true, workspace_id: null,
    url: 'https://mcp.example.test', stdio_profile_key: null, ...overrides,
  };
}

for (const state of ['configured', 'needs_auth', 'connected', 'failed', 'logged_out'] satisfies ClaudeMcpState[]) {
  test(`OAuth may start or replace authorization from ${state}`, () => {
    expect(canStartClaudeMcpAuth(server({ state }), state)).toBe(true);
  });
}

test('active, disabled and anonymous servers cannot start a second OAuth operation', () => {
  expect(canStartClaudeMcpAuth(server({ state: 'waiting_for_user' }), 'waiting_for_user')).toBe(false);
  expect(canStartClaudeMcpAuth(server({ state: 'disabled', enabled: false }), 'disabled')).toBe(false);
  expect(canStartClaudeMcpAuth(server({ auth_kind: 'none', auth_state: 'anonymous', credential_configured: false }), 'failed')).toBe(false);
});

test('replacement label follows credential presence rather than discovery success', () => {
  expect(claudeMcpAuthActionLabel(server({ state: 'failed' }))).toBe('重新认证');
  expect(claudeMcpAuthActionLabel(server({ credential_configured: false }))).toBe('开始认证');
});
