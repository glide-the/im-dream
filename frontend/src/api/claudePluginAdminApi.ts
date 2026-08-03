// [Input] Settings → Plugins (Claude Code) server API contracts.
// [Output] Typed client for shared plugin installations, operations, and Deck plugin refs.
// [Pos] API layer for claude-plugin-admin components and the Deck editor plugin selector.

import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';

export type ClaudePluginSourceType = 'claude-official' | 'marketplace' | 'github' | 'platform-builtin';
export type ClaudePluginInstallStatus = 'installing' | 'ready' | 'error' | 'uninstalled';
export type ClaudePluginOperationStatus = 'queued' | 'running' | 'ready' | 'error';

export interface ClaudePluginInstallation {
  id: string;
  requested_package_spec: string;
  package_name: string;
  marketplace: string;
  requested_version: string | null;
  resolved_version: string;
  source_type: ClaudePluginSourceType;
  artifact_digest: string;
  artifact_path: string;
  claude_cli_version: string;
  cli_git_commit_sha: string | null;
  manifest_json: string | null;
  component_inventory_json: string;
  compatibility_json: string;
  status: ClaudePluginInstallStatus;
  operation_id: string;
  error_code: string | null;
  error_summary: string | null;
  file_count: number;
  created_at: string;
  updated_at: string;
  installed_at: string | null;
  deck_ref_count?: number;
  deck_refs?: Array<{ deck_id: string; enabled: boolean; order_index: number }>;
}

export interface ClaudePluginInstallationsResult {
  installations: ClaudePluginInstallation[];
}

export interface ClaudePluginOperation {
  id: string;
  operation_kind: string;
  requested_package_spec: string;
  status: ClaudePluginOperationStatus;
  phase: string;
  progress: number;
  message: string | null;
  executable: string | null;
  argv_json: string | null;
  cwd: string | null;
  cli_version: string | null;
  exit_code: number | null;
  evidence_path: string | null;
  installation_id: string | null;
  error_code: string | null;
  error_summary: string | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
}

export interface DeckClaudePluginRef {
  deck_id: string;
  plugin_installation_id: string;
  package_spec: string;
  resolved_version: string;
  artifact_digest: string;
  enabled: number;
  order_index: number;
  installation_status?: ClaudePluginInstallStatus;
  source_type?: ClaudePluginSourceType;
}

export interface PluginLoadReceiptPlugin {
  package_spec: string;
  resolved_version: string | null;
  artifact_digest: string;
  relative_path: string;
  file_count?: number;
  verified: boolean;
}

export interface PluginLoadReceipt {
  thread_id: string;
  deck_id: string | null;
  workspace_found: boolean;
  receipt: {
    schema_version: string;
    workspace: string;
    deck_id: string | null;
    packed_at: string | null;
    plugins: PluginLoadReceiptPlugin[];
    frozen: boolean;
  } | null;
  launch_manifest: {
    schema_version: string;
    plugins: Array<{
      package_spec: string;
      resolved_version: string | null;
      relative_path: string;
      artifact_digest: string;
    }>;
  } | null;
}

export class ClaudePluginApiError extends Error {
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
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

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
    const errorPayload = (payload as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ClaudePluginApiError(
      errorPayload?.code ?? `HTTP_${response.status}`,
      errorPayload?.message ?? `Request failed with status ${response.status}`,
      response.status,
    );
  }
  return payload as T;
}

export async function listClaudePluginInstallations(): Promise<ClaudePluginInstallationsResult> {
  return request<ClaudePluginInstallationsResult>(
    '/api/claude-plugins/installations',
  );
}

export async function installClaudePlugin(input: {
  packageSpec: string;
  sourceType?: ClaudePluginSourceType;
}): Promise<{ accepted: boolean; operation_id: string; package_spec: string }> {
  return request('/api/claude-plugins/install', {
    method: 'POST',
    body: JSON.stringify({
      package_spec: input.packageSpec,
      ...(input.sourceType ? { source_type: input.sourceType } : {}),
    }),
  });
}

export async function getClaudePluginOperation(operationId: string): Promise<ClaudePluginOperation> {
  return request(`/api/claude-plugins/operations/${encodeURIComponent(operationId)}`);
}

export async function listClaudePluginOperations(limit = 10): Promise<ClaudePluginOperation[]> {
  const payload = await request<{ operations: ClaudePluginOperation[] }>(
    `/api/claude-plugins/operations?limit=${limit}`,
  );
  return payload.operations;
}

export async function getClaudePluginInstallation(installationId: string): Promise<ClaudePluginInstallation> {
  return request(`/api/claude-plugins/installations/${encodeURIComponent(installationId)}`);
}

export async function uninstallClaudePlugin(installationId: string): Promise<ClaudePluginInstallation> {
  return request(`/api/claude-plugins/installations/${encodeURIComponent(installationId)}/uninstall`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export async function listDeckClaudePluginRefs(deckId: string): Promise<DeckClaudePluginRef[]> {
  const payload = await request<{ refs: DeckClaudePluginRef[] }>(
    `/api/decks/${encodeURIComponent(deckId)}/claude-plugins`,
  );
  return payload.refs;
}

export async function putDeckClaudePluginRefs(
  deckId: string,
  refs: Array<{ plugin_installation_id: string; enabled: boolean; order_index: number }>,
): Promise<DeckClaudePluginRef[]> {
  const payload = await request<{ refs: DeckClaudePluginRef[] }>(
    `/api/decks/${encodeURIComponent(deckId)}/claude-plugins`,
    { method: 'PUT', body: JSON.stringify({ refs }) },
  );
  return payload.refs;
}

export async function getThreadPluginLoadReceipt(threadId: string): Promise<PluginLoadReceipt> {
  return request(`/api/claude-agent/threads/${encodeURIComponent(threadId)}/plugin-load-receipt`);
}

export function shortDigest(digest: string): string {
  const hex = digest.replace('sha256:', '');
  return `sha256-${hex.slice(0, 12)}…`;
}
