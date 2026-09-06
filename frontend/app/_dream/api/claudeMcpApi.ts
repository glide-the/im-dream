// [Input] Authenticated database-managed `/api/claude-mcp` CRUD, discovery, inventory, and OAuth operation contracts.
// [Output] Strict frontend DTOs plus explicit tools/resources/prompts discovery helpers with no CLI or browser credential persistence.
// [Pos] Transport boundary for the `claude-mcp` Resources feature.
// [Sync] 2026-08-19: historical CLI-backed discovery/login helpers; superseded by the 2026-08-25 managed-DB/standard-SDK contract below.
// [Sync] 2026-08-19: add restricted user-scope HTTPS configuration and removal helpers.
// [Sync] 2026-08-20: add sanitized public-SDK server/tool inventory contracts.
// [Sync] 2026-08-21: expose server config scope/removability and allow absolute HTTP(S) configuration.
// [Sync] 2026-08-25: carry Runtime-classified anonymous, required, authenticated, or unknown authentication state.
// [Sync] 2026-08-25: switch Resources to managed-DB capability/CRUD and explicit standard-MCP discovery.
// [Sync] 2026-08-25: add revision-aware PATCH for detail-page configuration edits.
// [Sync] 2026-08-25: keep authentication classification backend-owned; CRUD callers never choose OAuth versus anonymous.
// [Sync] 2026-08-25: make detail inventory cache-first so automatic loading never forces redundant remote discovery.

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

export type ClaudeMcpConfigScope = 'user' | 'workspace' | 'local' | 'project' | 'plugin' | 'unknown';
export type ClaudeMcpAuthState = 'anonymous' | 'required' | 'authenticated' | 'unknown';

export interface ClaudeMcpCapability {
  enabled: boolean;
  reason_code: string | null;
  cli_version: string | null;
  minimum_cli_version: string | null;
  headless_minimum_cli_version: string | null;
  credential_identity: string | null;
  management_mode: 'managed_db';
  schema_capability: 'dream.managed-mcp-resources.v1';
  schema_version: number;
  transports: Array<'streamable_http' | 'sse' | 'stdio'>;
}

export interface ClaudeMcpServer {
  name: string;
  state: ClaudeMcpState;
  auth_state: ClaudeMcpAuthState;
  transport: string | null;
  detail: string | null;
  active_operation_id: string | null;
  config_scope: ClaudeMcpConfigScope;
  removable: boolean;
  id: string | null;
  display_name: string;
  auth_kind: 'none' | 'oauth' | null;
  enabled: boolean;
  revision: number | null;
  credential_revision: number;
  credential_ref: string | null;
  credential_configured: boolean;
  workspace_id: string | null;
  url: string | null;
  stdio_profile_key: string | null;
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

export type ClaudeMcpInventoryStatus = 'connected' | 'failed' | 'needs_auth' | 'disabled';
export type ClaudeMcpInventoryCapabilityStatus = 'available' | 'not_reported';

export interface ClaudeMcpToolAnnotations {
  read_only: boolean | null;
  destructive: boolean | null;
  open_world: boolean | null;
}

export interface ClaudeMcpTool {
  name: string;
  description: string | null;
  annotations: ClaudeMcpToolAnnotations;
}

export interface ClaudeMcpResource {
  uri: string;
  name: string;
  description: string | null;
  mime_type?: string | null;
}

export interface ClaudeMcpPrompt {
  name: string;
  description: string | null;
  argument_count?: number;
  arguments?: Array<{ name: string; description?: string | null; required?: boolean }>;
}

export interface ClaudeMcpServerInventory {
  server_name: string;
  config_revision: number;
  credential_revision: number;
  status: ClaudeMcpInventoryStatus;
  config_scope: string;
  runtime_scope: string | null;
  transport: string | null;
  url: string | null;
  server_info: { name: string; version: string } | null;
  tools: ClaudeMcpTool[];
  resources: ClaudeMcpResource[];
  prompts: ClaudeMcpPrompt[];
  tool_count: number;
  tools_truncated: boolean;
  capabilities: Record<'tools' | 'resources' | 'prompts', {
    status: ClaudeMcpInventoryCapabilityStatus;
    count: number | null;
  }>;
  refreshed_at: string;
  error?: { code: string; retryable: boolean; trace_id?: string | null } | null;
  cached?: boolean;
}

interface ManagedDiscoveryResult {
  server_id: string;
  status: 'complete' | 'failed' | 'cancelled';
  config_revision: number;
  credential_revision: number;
  tools: ClaudeMcpTool[];
  resources: ClaudeMcpResource[];
  prompts: ClaudeMcpPrompt[];
  server_info: { name: string; version: string } | null;
  error: { code: string; retryable: boolean; trace_id?: string | null } | null;
  discovered_at: string;
  cached: boolean;
  truncated: boolean;
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

export async function getClaudeMcpServer(serverName: string): Promise<ClaudeMcpServer> {
  const payload = await request<{ server: ClaudeMcpServer }>(
    `/api/claude-mcp/servers/${encodeURIComponent(serverName)}`,
  );
  return payload.server;
}

export async function getClaudeMcpServerInventory(
  serverIdentifier: string,
): Promise<ClaudeMcpServerInventory> {
  const payload = await request<{ discovery: ManagedDiscoveryResult }>(
    `/api/claude-mcp/servers/${encodeURIComponent(serverIdentifier)}/discoveries`,
    { method: 'POST', body: JSON.stringify({ force: false }) },
  );
  const result = payload.discovery;
  const needsAuth = result.error?.code === 'CLAUDE_MCP_CREDENTIAL_REQUIRED';
  return {
    server_name: serverIdentifier,
    config_revision: result.config_revision,
    credential_revision: result.credential_revision,
    status: result.status === 'complete' ? 'connected' : needsAuth ? 'needs_auth' : 'failed',
    config_scope: 'managed_db',
    runtime_scope: null,
    transport: null,
    url: null,
    server_info: result.server_info,
    tools: result.tools,
    resources: result.resources,
    prompts: result.prompts,
    tool_count: result.tools.length,
    tools_truncated: result.truncated,
    capabilities: {
      tools: { status: 'available', count: result.tools.length },
      resources: { status: 'available', count: result.resources.length },
      prompts: { status: 'available', count: result.prompts.length },
    },
    refreshed_at: result.discovered_at,
    error: result.error,
    cached: result.cached,
  };
}

export async function configureClaudeMcpServer(
  name: string,
  url: string | null,
  options: {
    transport?: 'streamable_http' | 'sse' | 'stdio';
    stdioProfileKey?: string | null;
  } = {},
): Promise<ClaudeMcpServer> {
  const payload = await request<{ server: ClaudeMcpServer }>('/api/claude-mcp/servers', {
    method: 'POST',
    body: JSON.stringify({
      name,
      display_name: name,
      transport: options.transport ?? 'streamable_http',
      scope: 'user',
      url,
      stdio_profile_key: options.stdioProfileKey ?? null,
    }),
  });
  return payload.server;
}

export async function updateClaudeMcpServer(
  server: ClaudeMcpServer,
  changes: {
    displayName: string;
    transport: 'streamable_http' | 'sse' | 'stdio';
    url: string | null;
    stdioProfileKey: string | null;
    enabled: boolean;
  },
): Promise<ClaudeMcpServer> {
  if (!server.id || !server.revision) {
    throw new ClaudeMcpApiError(
      'CLAUDE_MCP_SERVER_CONFIGURATION_INVALID',
      'MCP Server 缺少可更新的数据库标识或 revision。',
      409,
    );
  }
  const payload = await request<{ server: ClaudeMcpServer }>(
    `/api/claude-mcp/servers/${encodeURIComponent(server.id)}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        expected_revision: server.revision,
        display_name: changes.displayName,
        transport: changes.transport,
        workspace_id: server.workspace_id,
        url: changes.url,
        stdio_profile_key: changes.stdioProfileKey,
        enabled: changes.enabled,
      }),
    },
  );
  return payload.server;
}

export async function removeClaudeMcpServer(serverName: string): Promise<ClaudeMcpServer> {
  const server = await getClaudeMcpServer(serverName);
  const revision = server.revision;
  const payload = await request<{ server: ClaudeMcpServer }>(
    `/api/claude-mcp/servers/${encodeURIComponent(server.id ?? serverName)}${revision ? `?expected_revision=${revision}` : ''}`,
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
    `/api/claude-mcp/servers/${encodeURIComponent(serverName)}/credential`,
    { method: 'DELETE' },
  );
  return payload.server;
}
