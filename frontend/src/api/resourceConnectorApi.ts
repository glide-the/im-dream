// [Input] Connector REST endpoints, auth token storage, and Notion resource selection payloads.
// [Output] Frontend client helpers for resource connector CRUD, auth polling, resource listing, and sync.
// [Pos] resource connector API client node in frontend/src/api
// [Sync] 2026-07-04: add Notion resource connector API helpers with local fallback storage for the frontend task.
// [Sync] 2026-07-04: preserve backend connector UUIDs from singular create responses so auth/discovery
//                    calls do not fall back to local connector_* ids.
// [Sync] 2026-07-05: send connector resource selections with the backend's selected_* field names so
//                    selection persistence reaches /api/connectors/{id}/resources/select instead of collapsing
//                    to empty lists.
/**
 * Resource connector API helpers.
 *
 * The frontend prefers the real backend connector endpoints when they exist,
 * but falls back to localStorage-backed state when the backend request itself
 * fails so the UI remains usable while the backend implementation is still
 * landing.
 */

import { getAuthToken } from '../contexts/AuthContext';
import { STORAGE_KEYS } from '../constants/storageKeys';
import { apiUrl } from '../lib/apiBase';

export type ConnectorPlatform = 'notion';

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
}

export interface NotionResourceOption {
  id: string;
  title: string;
  subtitle?: string;
  pageCount?: number;
  selected?: boolean;
}

export interface ConnectorResourceSelection {
  databaseIds: string[];
  pageIds: string[];
}

export interface CreateConnectorInput {
  name: string;
  platform?: ConnectorPlatform;
}

export interface UpdateConnectorInput {
  name?: string;
  status?: ConnectorStatus;
}

const LOCAL_CONNECTOR_STORAGE_KEY = STORAGE_KEYS.RESOURCE_CONNECTORS;
const DEFAULT_CONNECTOR_NAME = 'Resource Connector';
const DEFAULT_NOTION_VERIFICATION_URL = 'https://www.notion.so/my-integrations';

const FALLBACK_DATABASES: NotionResourceOption[] = [
  {
    id: 'db-product-notes',
    title: '产品资料库',
    subtitle: 'Briefs, specs, and launch notes',
    pageCount: 18,
  },
  {
    id: 'db-research-log',
    title: '调研记录',
    subtitle: 'Interviews and research captures',
    pageCount: 12,
  },
  {
    id: 'db-roadmap',
    title: '路线图',
    subtitle: 'Milestones and release planning',
    pageCount: 9,
  },
];

const FALLBACK_PAGES: NotionResourceOption[] = [
  {
    id: 'page-brand-guide',
    title: '品牌规范',
    subtitle: 'Standalone page',
  },
  {
    id: 'page-quarterly-goals',
    title: '季度目标',
    subtitle: 'Standalone page',
  },
  {
    id: 'page-meeting-notes',
    title: '会议纪要',
    subtitle: 'Standalone page',
  },
];

function nowIso(): string {
  return new Date().toISOString();
}

function createId(prefix: string): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}_${crypto.randomUUID()}`;
  }

  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function safeJsonParse<T>(value: string | null, fallback: T): T {
  if (!value) return fallback;

  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function readLocalConnectors(): ResourceConnector[] {
  if (typeof window === 'undefined') return [];
  return safeJsonParse<ResourceConnector[]>(localStorage.getItem(LOCAL_CONNECTOR_STORAGE_KEY), []);
}

function writeLocalConnectors(connectors: ResourceConnector[]): ResourceConnector[] {
  if (typeof window !== 'undefined') {
    localStorage.setItem(LOCAL_CONNECTOR_STORAGE_KEY, JSON.stringify(connectors));
  }
  return connectors;
}

function mutateLocalConnector(
  connectorId: string,
  mutator: (connector: ResourceConnector) => ResourceConnector,
): ResourceConnector | null {
  const connectors = readLocalConnectors();
  const index = connectors.findIndex((connector) => connector.id === connectorId);
  if (index === -1) return null;

  const nextConnector = mutator({ ...connectors[index], sources: connectors[index].sources.map((source) => ({ ...source })), auth: { ...connectors[index].auth } });
  connectors[index] = nextConnector;
  writeLocalConnectors(connectors);
  return nextConnector;
}

function hasBackendAuthSession(raw: any): boolean {
  const auth = raw?.auth ?? raw?.authentication ?? {};
  const config = raw?.config ?? {};
  return Boolean(
    auth?.verificationUrl
      || auth?.verification_url
      || auth?.verificationCode
      || auth?.verification_code
      || auth?.pollIntervalSeconds
      || auth?.poll_interval_seconds
      || raw?.verificationUrl
      || raw?.verification_url
      || raw?.verificationCode
      || raw?.verification_code
      || raw?.pollIntervalSeconds
      || raw?.poll_interval_seconds
      || config?.verificationUrl
      || config?.verification_url
      || config?.verificationCode
      || config?.verification_code
      || config?.pollIntervalSeconds
      || config?.poll_interval_seconds,
  );
}

function localizeAuthStatus(status?: string | null, hasSession = false): ConnectorAuthStatus {
  switch (status) {
    case 'authenticated':
      return 'authenticated';
    case 'authenticating':
    case 'pending':
      return hasSession ? 'authenticating' : 'idle';
    case 'expired':
      return 'expired';
    case 'error':
      return 'error';
    default:
      return 'idle';
  }
}

function localizeConnectorStatus(status?: string | null, sourceCount = 0, hasSession = false): ConnectorStatus {
  switch (status) {
    case 'authenticated':
    case 'synced':
      return 'synced';
    case 'syncing':
      return 'syncing';
    case 'authenticating':
    case 'pending':
      return hasSession ? 'authenticating' : 'draft';
    case 'expired':
      return 'expired';
    case 'error':
      return 'error';
    default:
  return sourceCount > 0 ? 'synced' : 'draft';
  }
}

function normalizeSourceType(value?: string | null): ConnectorSourceType {
  return value === 'notion_page' || value === 'page' ? 'notion_page' : 'notion_database';
}

function normalizeSourceStatus(value?: string | null): ConnectorSourceStatus {
  switch (value) {
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

function normalizeConnectorSource(raw: any): ConnectorSource {
  const updatedAt = raw?.updated_at ?? raw?.updatedAt ?? nowIso();
  return {
    id: String(raw?.id ?? raw?.source_id ?? raw?.resource_id ?? createId('source')),
    title: String(raw?.title ?? raw?.name ?? raw?.label ?? 'Untitled source'),
    type: normalizeSourceType(raw?.type ?? raw?.resource_type ?? raw?.kind),
    status: normalizeSourceStatus(raw?.status ?? raw?.sync_status),
    updatedAt,
    syncedAt: raw?.synced_at ?? raw?.syncedAt ?? raw?.last_synced_at ?? raw?.lastSyncedAt,
    pageCount: typeof raw?.page_count === 'number'
      ? raw.page_count
      : typeof raw?.pageCount === 'number'
        ? raw.pageCount
        : undefined,
    description: raw?.description ?? raw?.subtitle ?? raw?.summary,
    url: raw?.url ?? raw?.source_url ?? raw?.sourceUrl,
  };
}

function normalizeConnectorAuth(raw: any): ConnectorAuthSession {
  const auth = raw?.auth ?? raw?.authentication ?? raw;
  const config = raw?.config ?? {};
  return {
    status: localizeAuthStatus(auth?.status ?? raw?.auth_status ?? raw?.status, hasBackendAuthSession(raw)),
    verificationCode:
      auth?.verificationCode
      ?? auth?.verification_code
      ?? raw?.verification_code
      ?? raw?.code
      ?? config?.verificationCode
      ?? config?.verification_code,
    verificationUrl:
      auth?.verificationUrl
      ?? auth?.verification_url
      ?? raw?.verification_url
      ?? config?.verificationUrl
      ?? config?.verification_url
      ?? DEFAULT_NOTION_VERIFICATION_URL,
    pollAttempts: typeof auth?.pollAttempts === 'number'
      ? auth.pollAttempts
      : typeof auth?.poll_attempts === 'number'
        ? auth.poll_attempts
        : undefined,
    expiresAt: auth?.expiresAt ?? auth?.expires_at ?? raw?.expires_at,
    message: auth?.message ?? raw?.message,
  };
}

function normalizeConnector(raw: any): ResourceConnector {
  const now = nowIso();
  const sources = Array.isArray(raw?.sources)
    ? raw.sources.map(normalizeConnectorSource)
    : Array.isArray(raw?.resources)
      ? raw.resources.map(normalizeConnectorSource)
      : [];
  const auth = normalizeConnectorAuth(raw);
  const sourceCount = sources.length;
  const hasSession = hasBackendAuthSession(raw);

  return {
    id: String(raw?.id ?? raw?.connector_id ?? raw?.resource_connector_id ?? createId('connector')),
    name: String(raw?.name ?? raw?.title ?? DEFAULT_CONNECTOR_NAME),
    platform: (raw?.platform === 'notion' ? 'notion' : 'notion'),
    status: localizeConnectorStatus(raw?.status ?? raw?.sync_status ?? raw?.auth_status, sourceCount, hasSession),
    createdAt: raw?.created_at ?? raw?.createdAt ?? now,
    updatedAt: raw?.updated_at ?? raw?.updatedAt ?? now,
    lastSyncedAt: raw?.last_synced_at ?? raw?.lastSyncedAt ?? raw?.synced_at ?? raw?.syncedAt,
    auth,
    sources,
  };
}

function normalizeConnectorListResponse(response: unknown): ResourceConnector[] {
  if (Array.isArray(response)) {
    return response.map(normalizeConnector);
  }

  const payload = response as { connectors?: unknown[]; connector?: unknown; data?: unknown[]; items?: unknown[] };
  if (payload?.connector) return [normalizeConnector(payload.connector)];
  if (Array.isArray(payload?.connectors)) return payload.connectors.map(normalizeConnector);
  if (Array.isArray(payload?.data)) return payload.data.map(normalizeConnector);
  if (Array.isArray(payload?.items)) return payload.items.map(normalizeConnector);
  return [];
}

function normalizeConnectorResponse(response: unknown): ResourceConnector {
  return normalizeConnector(
    response && typeof response === 'object' && 'connector' in response
      ? (response as { connector?: unknown }).connector
      : response,
  );
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
    throw new Error(`Request failed (${response.status})`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

async function remoteOrLocal<T>(remote: () => Promise<T>, local: () => Promise<T> | T): Promise<T> {
  try {
    return await remote();
  } catch {
    return await local();
  }
}

function buildLocalAuthSession(auth?: Partial<ConnectorAuthSession>): ConnectorAuthSession {
  const verificationCode = auth?.verificationCode ?? `NTN-${Math.floor(1000 + Math.random() * 9000)}`;
  const expiresAt = auth?.expiresAt ?? new Date(Date.now() + 10 * 60 * 1000).toISOString();
  return {
    status: auth?.status ?? 'authenticating',
    verificationCode,
    verificationUrl: auth?.verificationUrl ?? DEFAULT_NOTION_VERIFICATION_URL,
    pollAttempts: auth?.pollAttempts ?? 0,
    expiresAt,
    message: auth?.message ?? 'Open Notion in your browser and confirm the integration.',
  };
}

function buildLocalConnector(input: CreateConnectorInput): ResourceConnector {
  const now = nowIso();
  return {
    id: createId('connector'),
    name: input.name.trim() || DEFAULT_CONNECTOR_NAME,
    platform: input.platform ?? 'notion',
    status: 'draft',
    createdAt: now,
    updatedAt: now,
    auth: buildLocalAuthSession({ status: 'idle', message: 'Connector created. Start Notion auth to continue.' }),
    sources: [],
  };
}

function mergeSelectedSources(
  connector: ResourceConnector,
  databaseOptions: NotionResourceOption[],
  pageOptions: NotionResourceOption[],
  selection: ConnectorResourceSelection,
): ResourceConnector {
  const now = nowIso();
  const selectedDatabaseIds = new Set(selection.databaseIds);
  const selectedPageIds = new Set(selection.pageIds);

  const sources: ConnectorSource[] = [
    ...databaseOptions
      .filter((option) => selectedDatabaseIds.has(option.id))
      .map((option) => ({
        id: option.id,
        title: option.title,
        type: 'notion_database' as const,
        status: 'synced' as const,
        updatedAt: now,
        syncedAt: now,
        pageCount: option.pageCount,
        description: option.subtitle,
      })),
    ...pageOptions
      .filter((option) => selectedPageIds.has(option.id))
      .map((option) => ({
        id: option.id,
        title: option.title,
        type: 'notion_page' as const,
        status: 'synced' as const,
        updatedAt: now,
        syncedAt: now,
        description: option.subtitle,
      })),
  ];

  return {
    ...connector,
    status: sources.length > 0 ? 'synced' : connector.status,
    updatedAt: now,
    lastSyncedAt: sources.length > 0 ? now : connector.lastSyncedAt,
    sources,
    auth: {
      ...connector.auth,
      status: connector.auth.status === 'authenticated' ? 'authenticated' : connector.auth.status,
    },
  };
}

export async function listConnectors(): Promise<ResourceConnector[]> {
  return remoteOrLocal(
    async () => {
      const response = await fetchJson<unknown>('/api/connectors');
      return normalizeConnectorListResponse(response);
    },
    () => readLocalConnectors(),
  );
}

export async function createConnector(input: CreateConnectorInput): Promise<ResourceConnector> {
  const localFallback = () => {
    const connector = buildLocalConnector(input);
    const connectors = readLocalConnectors();
    writeLocalConnectors([connector, ...connectors.filter((item) => item.id !== connector.id)]);
    return connector;
  };

  return remoteOrLocal(
    async () => {
      const response = await fetchJson<unknown>('/api/connectors', {
        method: 'POST',
        body: JSON.stringify({
          name: input.name,
          platform: input.platform ?? 'notion',
        }),
      });
      const [connector] = normalizeConnectorListResponse(response);
      return connector ?? localFallback();
    },
    localFallback,
  );
}

export async function updateConnector(
  connectorId: string,
  input: UpdateConnectorInput,
): Promise<ResourceConnector | null> {
  const localFallback = () => mutateLocalConnector(connectorId, (connector) => ({
    ...connector,
    ...input,
    name: input.name?.trim() || connector.name,
    updatedAt: nowIso(),
  }));

  return remoteOrLocal(
    async () => {
      const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}`, {
        method: 'PATCH',
        body: JSON.stringify(input),
      });

      const normalized = normalizeConnectorResponse(response);
      return normalized.id ? normalized : localFallback();
    },
    localFallback,
  );
}

export async function deleteConnector(connectorId: string): Promise<boolean> {
  return remoteOrLocal(
    async () => {
      await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}`, {
        method: 'DELETE',
      });
      return true;
    },
    () => {
      const connectors = readLocalConnectors().filter((connector) => connector.id !== connectorId);
      writeLocalConnectors(connectors);
      return true;
    },
  );
}

export async function startConnectorAuth(connectorId: string): Promise<ResourceConnector | null> {
  const localFallback = () => mutateLocalConnector(connectorId, (connector) => {
    const auth = buildLocalAuthSession({
      status: 'authenticating',
      verificationCode: connector.auth.verificationCode,
      verificationUrl: connector.auth.verificationUrl,
      pollAttempts: 0,
      message: 'Open Notion and confirm access. Polling will continue automatically.',
    });

    return {
      ...connector,
      status: 'authenticating',
      updatedAt: nowIso(),
      auth,
    };
  });

  return remoteOrLocal(
    async () => {
      const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/auth/login`, {
        method: 'POST',
      });
      const normalized = normalizeConnectorResponse(response);
      return normalized.id ? normalized : localFallback();
    },
    localFallback,
  );
}

export async function pollConnectorAuth(connectorId: string): Promise<ResourceConnector | null> {
  const localFallback = () => mutateLocalConnector(connectorId, (connector) => {
    const nextAttempts = (connector.auth.pollAttempts ?? 0) + 1;
    const expired = connector.auth.expiresAt ? Date.now() >= new Date(connector.auth.expiresAt).getTime() : false;
    const authStatus: ConnectorAuthStatus = expired ? 'expired' : nextAttempts >= 2 ? 'authenticated' : 'authenticating';

    return {
      ...connector,
      status: authStatus === 'authenticated' ? 'authenticated' : authStatus === 'expired' ? 'expired' : 'authenticating',
      updatedAt: nowIso(),
      auth: {
        ...connector.auth,
        status: authStatus,
        pollAttempts: nextAttempts,
        message: authStatus === 'authenticated'
          ? 'Notion authentication completed.'
          : authStatus === 'expired'
            ? 'Notion authentication expired. Please start a new session.'
            : 'Waiting for the browser confirmation in Notion.',
      },
    };
  });

  return remoteOrLocal(
    async () => {
      const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/auth/poll`, {
        method: 'POST',
      });
      const normalized = normalizeConnectorResponse(response);
      return normalized.id ? normalized : localFallback();
    },
    localFallback,
  );
}

export async function listConnectorDatabases(connectorId: string): Promise<NotionResourceOption[]> {
  return remoteOrLocal(
    async () => {
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
        const pageCountValue = record.page_count ?? record.pageCount;

        return {
          id: String(record.id ?? record.database_id ?? createId('database')),
          title: String(record.title ?? record.name ?? 'Untitled database'),
          subtitle: typeof record.subtitle === 'string'
            ? record.subtitle
            : typeof record.description === 'string'
              ? record.description
              : 'Notion database',
          pageCount: typeof pageCountValue === 'number' ? pageCountValue : undefined,
        };
      });
    },
    () => FALLBACK_DATABASES.map((item) => ({ ...item })),
  );
}

export async function listConnectorPages(connectorId: string): Promise<NotionResourceOption[]> {
  return remoteOrLocal(
    async () => {
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
        return {
          id: String(record.id ?? record.page_id ?? createId('page')),
          title: String(record.title ?? record.name ?? 'Untitled page'),
          subtitle: typeof record.subtitle === 'string'
            ? record.subtitle
            : typeof record.description === 'string'
              ? record.description
              : 'Standalone page',
        };
      });
    },
    () => FALLBACK_PAGES.map((item) => ({ ...item })),
  );
}

export async function selectConnectorResources(
  connectorId: string,
  selection: ConnectorResourceSelection,
): Promise<ResourceConnector | null> {
  const localFallback = () => {
    const connectors = readLocalConnectors();
    const connector = connectors.find((item) => item.id === connectorId);
    if (!connector) return null;

    const databases = FALLBACK_DATABASES;
    const pages = FALLBACK_PAGES;
    const nextConnector = {
      ...connector,
      ...mergeSelectedSources(connector, databases, pages, selection),
      status: selection.databaseIds.length + selection.pageIds.length > 0 ? 'synced' as const : connector.status,
    };

    writeLocalConnectors(connectors.map((item) => (item.id === connectorId ? nextConnector : item)));
    return nextConnector;
  };

  return remoteOrLocal(
    async () => {
      const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/resources/select`, {
        method: 'POST',
        body: JSON.stringify({
          selected_databases: selection.databaseIds,
          selected_pages: selection.pageIds,
        }),
      });
      const normalized = normalizeConnectorResponse(response);
      return normalized.id ? normalized : localFallback();
    },
    localFallback,
  );
}

export async function refreshConnectorSources(connectorId: string): Promise<ResourceConnector | null> {
  const localFallback = () => mutateLocalConnector(connectorId, (connector) => {
    const now = nowIso();
    return {
      ...connector,
      status: connector.sources.length > 0 ? 'synced' : connector.status,
      updatedAt: now,
      lastSyncedAt: connector.sources.length > 0 ? now : connector.lastSyncedAt,
      sources: connector.sources.map((source) => ({
        ...source,
        status: source.status === 'error' ? 'error' : 'synced',
        updatedAt: now,
        syncedAt: now,
      })),
      auth: {
        ...connector.auth,
        status: connector.auth.status === 'authenticated' ? 'authenticated' : connector.auth.status,
      },
    };
  });

  return remoteOrLocal(
    async () => {
      const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/sync`, {
        method: 'POST',
      });
      const normalized = normalizeConnectorResponse(response);
      return normalized.id ? normalized : localFallback();
    },
    localFallback,
  );
}

export async function getConnector(connectorId: string): Promise<ResourceConnector | null> {
  return remoteOrLocal(
    async () => {
      const response = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}`);
      return normalizeConnectorResponse(response);
    },
    () => readLocalConnectors().find((connector) => connector.id === connectorId) ?? null,
  );
}
