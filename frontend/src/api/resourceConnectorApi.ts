// [Input] Connector REST endpoints, auth token storage, and Notion resource selection payloads.
// [Output] Fail-closed frontend client helpers for connector CRUD, auth, resource selection, snapshot policy, and sync.
// [Pos] resource connector API client node in frontend/src/api
// [Sync] 2026-07-04: add Notion resource connector API helpers with local fallback storage for the frontend task.
// [Sync] 2026-07-04: preserve backend connector UUIDs from singular create responses so auth/discovery
//                    calls do not fall back to local connector_* ids.
// [Sync] 2026-07-05: send connector resource selections with the backend's selected_* field names so
//                    selection persistence reaches /api/connectors/{id}/resources/select instead of collapsing
//                    to empty lists.
// [Sync] 2026-07-05: normalize backend auth_session terminal states (`consumed`/`failed`) so UI can stop
//                    polling and surface actionable auth errors instead of indefinitely waiting.
// [Sync] 2026-07-07: keep normalized auth/session status ahead of stale top-level connector status so consumed
//                    sessions do not regress an already authenticated connector back to pending/error in the UI.
// [Sync] 2026-07-07: expose the connector normalizer for UI-only fallback workbench state so mock/fallback data
//                    follows the same client shape as backend and localStorage responses.
// [Sync] 2026-07-08: local fallback create now replaces same-platform connectors so the frontend preserves
//                    the single-account-per-platform business rule while backend enforcement lands separately.
// [Sync] 2026-07-08: persist selected resource metadata by posting full selected Notion resource objects and
//                    normalize backend connector_resources with external Notion ids for refresh-safe selection.
// [Sync] 2026-07-09: expose a browser-local connector change event so Settings saves can refresh
//                    Chat connector status panels without adding another backend endpoint.
// [Sync] 2026-08-28: remove the obsolete localStorage connector authority, preserve backend
//                    synchronization failures, and consume the versioned scheduled-sync policy.
// [Sync] 2026-08-29: drop opaque Notion response blobs from selection payloads and expose
//                    recoverable reauthorization warnings without masking effective access.
/**
 * Resource connector API helpers.
 *
 * Connector, authentication, selection, and snapshot state are server-owned.
 * Transport or backend failures are surfaced to the user and never converted
 * into browser-local authenticated/synced state.
 */

import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';

export type ConnectorPlatform = 'notion';

export const RESOURCE_CONNECTORS_CHANGED_EVENT = 'ink-and-memory:resource-connectors-changed';

export interface ResourceConnectorsChangedDetail {
  connectorId?: string;
  reason: 'resources-selected' | 'sources-refreshed' | 'auth-updated' | 'connector-updated';
}

export function notifyResourceConnectorsChanged(detail: ResourceConnectorsChangedDetail): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent<ResourceConnectorsChangedDetail>(RESOURCE_CONNECTORS_CHANGED_EVENT, { detail }));
}

export type ConnectorStatus =
  | 'draft'
  | 'authenticating'
  | 'authenticated'
  | 'syncing'
  | 'synced'
  | 'expired'
  | 'error';

export type ConnectorSourceType = 'notion_database' | 'notion_page';

export type ConnectorSourceStatus = 'idle' | 'syncing' | 'synced' | 'error';

export type ConnectorAuthStatus = 'idle' | 'authenticating' | 'authenticated' | 'expired' | 'error';

export interface ConnectorAuthSession {
  status: ConnectorAuthStatus;
  verificationCode?: string;
  verificationUrl?: string;
  pollAttempts?: number;
  expiresAt?: string;
  message?: string;
  warning?: string;
}

export interface ConnectorSource {
  id: string;
  title: string;
  type: ConnectorSourceType;
  status: ConnectorSourceStatus;
  updatedAt: string;
  syncedAt?: string;
  pageCount?: number;
  description?: string;
  url?: string;
}

export interface ResourceConnector {
  id: string;
  name: string;
  platform: ConnectorPlatform;
  status: ConnectorStatus;
  createdAt: string;
  updatedAt: string;
  lastSyncedAt?: string;
  auth: ConnectorAuthSession;
  sources: ConnectorSource[];
  syncPolicy?: ConnectorSyncPolicy;
}

export interface ConnectorSyncRule {
  enabled: boolean;
  intervalMinutes: number;
  revision: number;
}

export interface ConnectorSyncPolicy {
  schemaVersion: number;
  default: ConnectorSyncRule;
  desired: ConnectorSyncRule;
  effective: ConnectorSyncRule;
  status: 'applied' | 'syncing' | 'error' | 'disabled';
  lastAttemptAt?: string;
  lastSuccessAt?: string;
  nextSyncAt?: string;
  lastErrorCode?: string;
  allowedIntervalMinutes: number[];
}

export interface NotionResourceOption {
  id: string;
  title: string;
  subtitle?: string;
  pageCount?: number;
  selected?: boolean;
  url?: string;
  lastEdited?: string;
  propertiesSchema?: Record<string, unknown>;
}

export interface ConnectorResourceSelection {
  databaseIds: string[];
  pageIds: string[];
  databaseOptions?: NotionResourceOption[];
  pageOptions?: NotionResourceOption[];
}

export interface CreateConnectorInput {
  name: string;
  platform?: ConnectorPlatform;
}

export interface UpdateConnectorInput {
  name?: string;
  status?: ConnectorStatus;
}

export interface UpdateConnectorSyncPolicyInput {
  enabled: boolean;
  intervalMinutes: number;
}

const DEFAULT_CONNECTOR_NAME = 'Resource Connector';
const DEFAULT_NOTION_VERIFICATION_URL = 'https://www.notion.so/my-integrations';

function nowIso(): string {
  return new Date().toISOString();
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {};
}

function asString(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined;
}

export class ResourceConnectorApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ResourceConnectorApiError';
    this.status = status;
  }
}

function hasBackendAuthSession(raw: unknown): boolean {
  const record = asRecord(raw);
  const auth = asRecord(record.auth ?? record.authentication);
  const config = asRecord(record.config);
  const authSession = asRecord(auth.auth_session);
  const configSession = asRecord(config.auth_session);
  return Boolean(
    auth.verificationUrl
      || auth.verification_url
      || auth.verificationCode
      || auth.verification_code
      || auth.pollIntervalSeconds
      || auth.poll_interval_seconds
      || record.verificationUrl
      || record.verification_url
      || record.verificationCode
      || record.verification_code
      || record.pollIntervalSeconds
      || record.poll_interval_seconds
      || authSession.auth_session_id
      || authSession.auth_session_status
      || authSession.auth_session_started_at
      || authSession.auth_session_last_polled_at
      || configSession.auth_session_id
      || configSession.auth_session_status
      || configSession.auth_session_started_at
      || configSession.auth_session_last_polled_at
      || config.verificationUrl
      || config.verification_url
      || config.verificationCode
      || config.verification_code
      || config.pollIntervalSeconds
      || config.poll_interval_seconds,
  );
}

function localizeAuthStatus(status?: string | null, hasSession = false): ConnectorAuthStatus {
  switch ((status || '').toLowerCase()) {
    case 'authenticated':
      return 'authenticated';
    case 'authenticating':
    case 'pending':
      return hasSession ? 'authenticating' : 'idle';
    case 'consumed':
    case 'failed':
      return 'error';
    case 'expired':
      return 'expired';
    case 'error':
      return 'error';
    default:
      return 'idle';
  }
}

function localizeConnectorStatus(
  status?: string | null,
  hasSession = false,
  hasSnapshot = false,
): ConnectorStatus {
  switch ((status || '').toLowerCase()) {
    case 'authenticated':
      return hasSnapshot ? 'synced' : 'authenticated';
    case 'synced':
      return hasSnapshot ? 'synced' : 'authenticated';
    case 'syncing':
      return 'syncing';
    case 'authenticating':
    case 'pending':
      return hasSession ? 'authenticating' : 'draft';
    case 'consumed':
    case 'failed':
      return 'error';
    case 'expired':
      return 'expired';
    case 'error':
      return 'error';
    default:
      return hasSnapshot ? 'synced' : 'draft';
  }
}

function normalizeSourceType(value?: string | null): ConnectorSourceType {
  return value === 'notion_page' || value === 'page' ? 'notion_page' : 'notion_database';
}

function normalizeSourceStatus(value?: string | null): ConnectorSourceStatus {
  switch (value) {
    case 'pending':
    case 'syncing':
      return 'syncing';
    case 'synced':
      return 'synced';
    case 'error':
      return 'error';
    default:
      return 'idle';
  }
}

function normalizeConnectorSource(raw: unknown): ConnectorSource {
  const record = asRecord(raw);
  const metadata = asRecord(record.metadata);
  const updatedAt = typeof record.updated_at === 'string'
    ? record.updated_at
    : typeof record.updatedAt === 'string'
      ? record.updatedAt
      : typeof metadata.last_edited === 'string'
        ? metadata.last_edited
      : nowIso();
  return {
    id: String(record.external_id ?? record.database_id ?? record.page_id ?? record.source_id ?? record.resource_id ?? record.id ?? ''),
    title: String(record.title ?? record.name ?? record.label ?? 'Untitled source'),
    type: normalizeSourceType(asString(record.type ?? record.resource_type ?? record.kind)),
    status: normalizeSourceStatus(asString(record.status ?? record.sync_status)),
    updatedAt,
    syncedAt: asString(record.synced_at)
      ?? asString(record.syncedAt)
      ?? asString(record.last_synced_at)
      ?? asString(record.lastSyncedAt),
    pageCount: typeof record.page_count === 'number'
      ? record.page_count
      : typeof record.pageCount === 'number'
        ? record.pageCount
        : typeof metadata.page_count === 'number'
          ? metadata.page_count
          : undefined,
    description: asString(record.description) ?? asString(record.subtitle) ?? asString(record.summary),
    url: asString(record.url) ?? asString(record.source_url) ?? asString(record.sourceUrl) ?? asString(metadata.url),
  };
}

function normalizeSyncRule(raw: unknown): ConnectorSyncRule | null {
  const record = asRecord(raw);
  const enabled = record.enabled;
  const intervalMinutes = record.interval_minutes ?? record.intervalMinutes;
  const revision = record.revision;
  if (
    typeof enabled !== 'boolean'
    || typeof intervalMinutes !== 'number'
    || !Number.isSafeInteger(intervalMinutes)
    || intervalMinutes <= 0
    || typeof revision !== 'number'
    || !Number.isSafeInteger(revision)
    || revision <= 0
  ) {
    return null;
  }
  return { enabled, intervalMinutes, revision };
}

function normalizeSyncPolicy(raw: unknown): ConnectorSyncPolicy | undefined {
  const record = asRecord(raw);
  const defaultRule = normalizeSyncRule(record.default);
  const desired = normalizeSyncRule(record.desired);
  const effective = normalizeSyncRule(record.effective);
  const schemaVersion = record.schema_version ?? record.schemaVersion;
  const status = asString(record.status);
  const allowed = record.allowed_interval_minutes ?? record.allowedIntervalMinutes;
  if (
    !defaultRule
    || !desired
    || !effective
    || typeof schemaVersion !== 'number'
    || !Number.isSafeInteger(schemaVersion)
    || !['applied', 'syncing', 'error', 'disabled'].includes(status ?? '')
    || !Array.isArray(allowed)
    || !allowed.every((value) => typeof value === 'number' && Number.isSafeInteger(value) && value > 0)
  ) {
    return undefined;
  }
  return {
    schemaVersion,
    default: defaultRule,
    desired,
    effective,
    status: status as ConnectorSyncPolicy['status'],
    lastAttemptAt: asString(record.last_attempt_at ?? record.lastAttemptAt),
    lastSuccessAt: asString(record.last_success_at ?? record.lastSuccessAt),
    nextSyncAt: asString(record.next_sync_at ?? record.nextSyncAt),
    lastErrorCode: asString(record.last_error_code ?? record.lastErrorCode),
    allowedIntervalMinutes: allowed,
  };
}

function normalizeConnectorAuth(raw: unknown): ConnectorAuthSession {
  const record = asRecord(raw);
  const auth = asRecord(record.auth ?? record.authentication ?? record);
  const config = asRecord(record.config);
  const session = asRecord(auth.auth_session ?? config.auth_session);
  const resolvedStatus = asString(auth.status)
    ?? asString(record.auth_status)
    ?? asString(record.status)
    ?? asString(session.auth_session_status);
  const effectiveStatus = localizeAuthStatus(resolvedStatus, hasBackendAuthSession(raw));
  const sessionStatus = asString(session.auth_session_status)?.toLowerCase();
  const message =
    asString(auth.message)
    ?? asString(auth.detail)
    ?? asString(record.message)
    ?? asString(record.detail)
    ?? asString(config.auth_error)
    ?? asString(session.auth_error);
  return {
    status: effectiveStatus,
    verificationCode:
      asString(auth.verificationCode)
      ?? asString(auth.verification_code)
      ?? asString(record.verification_code)
      ?? asString(record.code)
      ?? asString(config.verificationCode)
      ?? asString(config.verification_code),
    verificationUrl:
      asString(auth.verificationUrl)
      ?? asString(auth.verification_url)
      ?? asString(record.verification_url)
      ?? asString(config.verificationUrl)
      ?? asString(config.verification_url)
      ?? DEFAULT_NOTION_VERIFICATION_URL,
    pollAttempts: typeof auth.pollAttempts === 'number'
      ? auth.pollAttempts
      : typeof auth.poll_attempts === 'number'
        ? auth.poll_attempts
        : undefined,
    expiresAt: asString(auth.expiresAt)
      ?? asString(auth.expires_at)
      ?? asString(session.auth_session_expires_at)
      ?? asString(record.expires_at),
    message,
    warning: effectiveStatus === 'authenticated'
      && ['consumed', 'expired', 'failed'].includes(sessionStatus ?? '')
      ? message
      : undefined,
  };
}

function normalizeConnector(raw: unknown): ResourceConnector {
  const record = asRecord(raw);
  const now = nowIso();
  const sources = Array.isArray(record.sources)
    ? record.sources.map(normalizeConnectorSource)
    : Array.isArray(record.resources)
      ? record.resources.map(normalizeConnectorSource)
      : [];
  const auth = normalizeConnectorAuth(raw);
  const config = asRecord(record.config);
  const authSession = asRecord(config.auth_session);
  const hasSession = hasBackendAuthSession(raw);
  const lastSyncedAt = asString(record.last_synced_at)
    ?? asString(record.lastSyncedAt)
    ?? asString(record.synced_at)
    ?? asString(record.syncedAt);
  const connectorStatus =
    asString(record.auth_status)
    ?? auth.status
    ?? asString(record.status)
    ?? asString(record.sync_status)
    ?? asString(authSession.auth_session_status);
  const syncPolicy = normalizeSyncPolicy(record.sync_policy ?? config.snapshot_sync_policy);
  const indexIsRefreshing = syncPolicy?.status === 'syncing'
    || sources.some((source) => source.status === 'syncing');

  return {
    id: String(record.id ?? record.connector_id ?? record.resource_connector_id ?? ''),
    name: String(record.name ?? record.title ?? DEFAULT_CONNECTOR_NAME),
    platform: 'notion',
    status: indexIsRefreshing
      ? 'syncing'
      : localizeConnectorStatus(connectorStatus, hasSession, Boolean(lastSyncedAt)),
    createdAt: asString(record.created_at) ?? asString(record.createdAt) ?? now,
    updatedAt: asString(record.updated_at) ?? asString(record.updatedAt) ?? now,
    lastSyncedAt,
    auth,
    sources,
    syncPolicy,
  };
}

function requireConnector(raw: unknown): ResourceConnector {
  const connector = normalizeConnector(raw);
  if (!connector.id) {
    throw new ResourceConnectorApiError(502, 'Notion connector response is invalid. Please retry.');
  }
  return connector;
}

function normalizeConnectorListResponse(response: unknown): ResourceConnector[] {
  if (Array.isArray(response)) {
    return response.map(requireConnector);
  }

  const payload = response as { connectors?: unknown[]; connector?: unknown; data?: unknown[]; items?: unknown[] };
  if (payload?.connector) return [requireConnector(payload.connector)];
  if (Array.isArray(payload?.connectors)) return payload.connectors.map(requireConnector);
  if (Array.isArray(payload?.data)) return payload.data.map(requireConnector);
  if (Array.isArray(payload?.items)) return payload.items.map(requireConnector);
  return [];
}

function normalizeConnectorResponse(response: unknown): ResourceConnector {
  return requireConnector(
    response && typeof response === 'object' && 'connector' in response
      ? (response as { connector?: unknown }).connector
      : response,
  );
}

export function normalizeResourceConnectorFallback(raw: unknown): ResourceConnector {
  return normalizeConnector(raw);
}

async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  headers.set('Accept', 'application/json');

  const token = getAuthToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(apiUrl(path), {
    credentials: 'include',
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = '';
    try {
      const payload = await response.json() as { detail?: unknown };
      detail = typeof payload.detail === 'string' ? payload.detail.trim() : '';
    } catch {
      detail = '';
    }
    throw new ResourceConnectorApiError(
      response.status,
      detail || `Notion request failed (${response.status}). Please retry.`,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function listConnectors(): Promise<ResourceConnector[]> {
  const response = await fetchJson<unknown>('/api/connectors');
  return normalizeConnectorListResponse(response);
}

export async function createConnector(input: CreateConnectorInput): Promise<ResourceConnector> {
  const response = await fetchJson<unknown>('/api/connectors', {
    method: 'POST',
    body: JSON.stringify({
      name: input.name,
      platform: input.platform ?? 'notion',
    }),
  });
  const [connector] = normalizeConnectorListResponse(response);
  if (!connector) {
    throw new ResourceConnectorApiError(502, 'Notion connector response is invalid. Please retry.');
  }
  return connector;
}

export async function updateConnector(
  connectorId: string,
  input: UpdateConnectorInput,
): Promise<ResourceConnector | null> {
  const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
  return normalizeConnectorResponse(response);
}

export async function deleteConnector(connectorId: string): Promise<boolean> {
  await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}`, {
    method: 'DELETE',
  });
  return true;
}

export async function startConnectorAuth(connectorId: string): Promise<ResourceConnector | null> {
  const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/auth/login`, {
    method: 'POST',
  });
  return normalizeConnectorResponse(response);
}

export async function pollConnectorAuth(connectorId: string): Promise<ResourceConnector | null> {
  const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/auth/poll`, {
    method: 'POST',
  });
  return normalizeConnectorResponse(response);
}

export async function listConnectorDatabases(connectorId: string): Promise<NotionResourceOption[]> {
  const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/databases`);
  const databaseItems = (response as { databases?: unknown[] }).databases;
  const responseItems = (response as { items?: unknown[] }).items;
  const items: unknown[] = Array.isArray(response)
    ? response
    : Array.isArray(databaseItems)
      ? databaseItems
      : Array.isArray(responseItems)
        ? responseItems
        : [];

  return items.map((raw): NotionResourceOption => {
    const record = raw as Record<string, unknown>;
    const id = String(record.id ?? record.database_id ?? '').trim();
    if (!id) {
      throw new ResourceConnectorApiError(502, 'Notion database response is invalid. Please retry.');
    }
    const pageCountValue = record.page_count ?? record.pageCount;
    const propertiesSchema = asRecord(record.properties_schema ?? record.propertiesSchema);
    return {
      id,
      title: String(record.title ?? record.name ?? 'Untitled database'),
      subtitle: typeof record.subtitle === 'string'
        ? record.subtitle
        : typeof record.description === 'string'
          ? record.description
          : 'Notion database',
      pageCount: typeof pageCountValue === 'number' ? pageCountValue : undefined,
      selected: Boolean(record.selected),
      url: typeof record.url === 'string' ? record.url : undefined,
      lastEdited: typeof record.last_edited === 'string'
        ? record.last_edited
        : typeof record.lastEdited === 'string'
          ? record.lastEdited
          : undefined,
      propertiesSchema,
    };
  });
}

export async function listConnectorPages(connectorId: string): Promise<NotionResourceOption[]> {
  const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/pages`);
  const pageItems = (response as { pages?: unknown[] }).pages;
  const responseItems = (response as { items?: unknown[] }).items;
  const items: unknown[] = Array.isArray(response)
    ? response
    : Array.isArray(pageItems)
      ? pageItems
      : Array.isArray(responseItems)
        ? responseItems
        : [];

  return items.map((raw): NotionResourceOption => {
    const record = raw as Record<string, unknown>;
    const id = String(record.id ?? record.page_id ?? '').trim();
    if (!id) {
      throw new ResourceConnectorApiError(502, 'Notion page response is invalid. Please retry.');
    }
    return {
      id,
      title: String(record.title ?? record.name ?? 'Untitled page'),
      subtitle: typeof record.subtitle === 'string'
        ? record.subtitle
        : typeof record.description === 'string'
          ? record.description
          : 'Standalone page',
      selected: Boolean(record.selected),
      url: typeof record.url === 'string' ? record.url : undefined,
      lastEdited: typeof record.last_edited === 'string'
        ? record.last_edited
        : typeof record.lastEdited === 'string'
          ? record.lastEdited
          : undefined,
    };
  });
}

export async function selectConnectorResources(
  connectorId: string,
  selection: ConnectorResourceSelection,
): Promise<ResourceConnector | null> {
  const databaseOptions = selection.databaseOptions ?? [];
  const pageOptions = selection.pageOptions ?? [];
  const databaseOptionById = new Map(databaseOptions.map((item) => [item.id, item]));
  const pageOptionById = new Map(pageOptions.map((item) => [item.id, item]));
  const selectedDatabasePayload = selection.databaseIds.map((id) => {
    const option = databaseOptionById.get(id);
    if (!option) return id;
    return {
      database_id: option.id,
      title: option.title,
      subtitle: option.subtitle,
      page_count: option.pageCount,
      url: option.url,
      last_edited: option.lastEdited,
      properties_schema: option.propertiesSchema,
    };
  });
  const selectedPagePayload = selection.pageIds.map((id) => {
    const option = pageOptionById.get(id);
    if (!option) return id;
    return {
      page_id: option.id,
      title: option.title,
      subtitle: option.subtitle,
      url: option.url,
      last_edited: option.lastEdited,
    };
  });

  const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/resources/select`, {
    method: 'POST',
    body: JSON.stringify({
      selected_databases: selectedDatabasePayload,
      selected_pages: selectedPagePayload,
    }),
  });
  return normalizeConnectorResponse(response);
}

export async function refreshConnectorSources(connectorId: string): Promise<ResourceConnector | null> {
  const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/sync`, {
    method: 'POST',
  });
  return normalizeConnectorResponse(response);
}

export async function getConnector(connectorId: string): Promise<ResourceConnector | null> {
  const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}`);
  return normalizeConnectorResponse(response);
}

export async function updateConnectorSyncPolicy(
  connectorId: string,
  input: UpdateConnectorSyncPolicyInput,
): Promise<ResourceConnector> {
  const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/sync-policy`, {
    method: 'PUT',
    body: JSON.stringify({
      enabled: input.enabled,
      interval_minutes: input.intervalMinutes,
    }),
  });
  return normalizeConnectorResponse(response);
}
