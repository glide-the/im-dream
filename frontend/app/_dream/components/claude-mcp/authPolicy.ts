// [Input] Server-owned Claude MCP auth kind/state and current credential projection.
// [Output] Whether the UI may start a replacement OAuth operation without deleting the existing credential first.
// [Pos] Shared terminal-state action policy for MCP list and detail surfaces.
// [Sync] 2026-09-16: allow reauthorization from configured, connected, failed and logged-out OAuth states.
import type { ClaudeMcpServer, ClaudeMcpState } from '../../api/claudeMcpApi';

const REAUTHENTICATABLE_STATES = new Set<ClaudeMcpState>([
  'configured',
  'needs_auth',
  'connected',
  'failed',
  'logged_out',
]);

export function canStartClaudeMcpAuth(
  server: ClaudeMcpServer | null,
  state: ClaudeMcpState | undefined,
): boolean {
  if (!server || !state || !REAUTHENTICATABLE_STATES.has(state)) return false;
  if (server.auth_kind === 'oauth') return true;
  return state === 'needs_auth' && server.auth_state === 'required';
}

export function claudeMcpAuthActionLabel(server: ClaudeMcpServer): '开始认证' | '重新认证' {
  return server.credential_configured ? '重新认证' : '开始认证';
}
