// [Input] Authenticated `/api/claude-mcp` capability, configuration, server, and OAuth operation contracts.
// [Output] Strict frontend DTOs and restricted HTTPS add/remove helpers with no browser credential persistence.
// [Pos] Transport boundary for the `claude-mcp` Resources feature.
// [Sync] 2026-08-19: add official CLI-backed MCP discovery/login/redirect/cancel/logout API helpers.
// [Sync] 2026-08-19: add restricted user-scope HTTPS configuration and removal helpers.

import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';

export type ClaudeMcpState =
  | 'not_configured'
  | 'configured'
  | 'needs_auth'
  | 'auth_starting'
  | 'waiting_for_user'
  | 'exchanging_code'
  | 'connected'
  | 'failed'
  | 'cancelling'
  | 'logged_out'
  | 'disabled';

export interface ClaudeMcpCapability {
  enabled: boolean;
  reason_code: string | null;
  cli_version: string | null;
  minimum_cli_version: string;
  headless_minimum_cli_version: string;
  credential_identity: string | null;
}

export interface ClaudeMcpServer {
  name: string;
  state: ClaudeMcpState;
  transport: string | null;
  detail: string | null;
  active_operation_id: string | null;
}

export interface ClaudeMcpOperation {
  id: string;
  server_name: string;
  state: ClaudeMcpState;
  authorization_url: string | null;
  error: { code: string; message: string } | null;
  redirect_submitted: boolean;
  created_at: string;
  updated_at: string;
}

export class ClaudeMcpApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getAuthToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  headers.set('Accept', 'application/json');
  if (init.body !== undefined) headers.set('Content-Type', 'application/json');

  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: 'include',
    headers,
  });
  const text = await response.text();
  let payload: unknown = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const error = (payload as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ClaudeMcpApiError(
      error?.code ?? `HTTP_${response.status}`,
      error?.message ?? `Request failed with status ${response.status}`,
      response.status,
    );
  }
  return payload as T;
}

export function getClaudeMcpCapability(): Promise<ClaudeMcpCapability> {
  return request('/api/claude-mcp/capability');
}

export async function listClaudeMcpServers(): Promise<ClaudeMcpServer[]> {
  const payload = await request<{ servers: ClaudeMcpServer[] }>('/api/claude-mcp/servers');
  return payload.servers;
}

export async function configureClaudeMcpServer(
  name: string,
  url: string,
): Promise<ClaudeMcpServer> {
  const payload = await request<{ server: ClaudeMcpServer }>('/api/claude-mcp/servers', {
    method: 'POST',
    body: JSON.stringify({ name, url }),
  });
  return payload.server;
}

export async function removeClaudeMcpServer(serverName: string): Promise<ClaudeMcpServer> {
  const payload = await request<{ server: ClaudeMcpServer }>(
    `/api/claude-mcp/servers/${encodeURIComponent(serverName)}`,
    { method: 'DELETE' },
  );
  return payload.server;
}

export async function startClaudeMcpAuth(serverName: string): Promise<ClaudeMcpOperation> {
  const payload = await request<{ operation: ClaudeMcpOperation }>(
    `/api/claude-mcp/servers/${encodeURIComponent(serverName)}/auth-operations`,
    { method: 'POST', body: '{}' },
  );
  return payload.operation;
}

export async function getClaudeMcpOperation(operationId: string): Promise<ClaudeMcpOperation> {
  const payload = await request<{ operation: ClaudeMcpOperation }>(
    `/api/claude-mcp/auth-operations/${encodeURIComponent(operationId)}`,
  );
  return payload.operation;
}

export async function submitClaudeMcpRedirect(
  operationId: string,
  redirectUrl: string,
): Promise<ClaudeMcpOperation> {
  const payload = await request<{ operation: ClaudeMcpOperation }>(
    `/api/claude-mcp/auth-operations/${encodeURIComponent(operationId)}/redirect`,
    { method: 'POST', body: JSON.stringify({ redirect_url: redirectUrl }) },
  );
  return payload.operation;
}

export async function cancelClaudeMcpAuth(operationId: string): Promise<ClaudeMcpOperation> {
  const payload = await request<{ operation: ClaudeMcpOperation }>(
    `/api/claude-mcp/auth-operations/${encodeURIComponent(operationId)}/cancel`,
    { method: 'POST', body: '{}' },
  );
  return payload.operation;
}

export async function logoutClaudeMcpServer(serverName: string): Promise<ClaudeMcpServer> {
  const payload = await request<{ server: ClaudeMcpServer }>(
    `/api/claude-mcp/servers/${encodeURIComponent(serverName)}/logout`,
    { method: 'POST', body: '{}' },
  );
  return payload.server;
}
