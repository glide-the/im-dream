// [Input] Deck Plugin management REST contracts, authenticated browser fetch, and server-owned permission/status fields.
// [Output] Normalized Deck workflow/runtime plugin records plus lifecycle mutation and operation helpers.
// [Pos] frontend-only Deck Plugin Admin API adapter; deliberately independent from Paperclip PluginRecord.

import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';

export type PluginCategory = 'deck-workflow' | 'claude-runtime';
export type DeclarationStatus = 'undeclared' | 'declared' | 'disabled';
export type MaterializationStatus = 'missing' | 'materializing' | 'materialized' | 'failed';
export type ActivationStatus = 'inactive' | 'loadable' | 'loaded' | 'load_failed';
export type InstallationStatus = 'installing' | 'ready' | 'disabled' | 'error' | 'upgrade_pending' | 'uninstalled';
export type CompatibilityStatus = 'compatible' | 'incompatible' | 'pending';
export type HealthStatus = 'healthy' | 'degraded' | 'failed' | 'unknown';
export type PluginOperationStatus = 'queued' | 'running' | 'ready' | 'completed' | 'error' | 'failed';

export interface PluginCapabilityDiffValue {
  added: string[];
  removed: string[];
}

export interface PluginRuntimeDependency {
  claudeCodePluginId: string;
  resolvedVersion: string;
  versionConstraint?: string;
  artifactDigest?: string;
  declarationStatus: DeclarationStatus;
  materializationStatus: MaterializationStatus;
  activationStatus: ActivationStatus;
  healthStatus: HealthStatus;
  lastErrorCode?: string;
  lastErrorSummary?: string;
  parentDeckPluginId?: string;
}

export interface PluginTimelineEntry {
  id: string;
  action: string;
  status: string;
  occurredAt?: string;
  actor?: string;
  summary?: string;
}

export interface PluginRunSummary {
  runId: string;
  status: string;
  startedAt?: string;
}

export interface DeckPluginInstallation {
  category: 'deck-workflow';
  deckPluginInstallationId: string;
  deckPluginId: string;
  displayName: string;
  deckPluginVersion: string;
  installedVersions: string[];
  defaultVersion?: string;
  availableVersion?: string;
  sourceType: 'marketplace' | 'local' | 'controlled' | 'unknown';
  sourceLabel: string;
  sourceVerified?: boolean;
  status: InstallationStatus;
  declarationStatus: DeclarationStatus;
  materializationStatus: MaterializationStatus;
  activationStatus: ActivationStatus;
  compatibilityStatus: CompatibilityStatus;
  compatibilitySummary?: string;
  healthStatus: HealthStatus;
  manifestRequestedCapabilities: string[];
  effectiveCapabilities: string[];
  capabilityDiff?: PluginCapabilityDiffValue;
  lastErrorCode?: string;
  lastErrorSummary?: string;
  lastErrorStage?: string;
  operationId?: string;
  lastRunAt?: string;
  updatedAt?: string;
  rollbackVersions: string[];
  isSystem: boolean;
  manifest?: {
    schemaVersion?: string;
    author?: string;
    workflowReferences: string[];
    inputSchemaVersion?: string;
    outputSchemaVersion?: string;
    deckRuntimeContract?: string;
  };
  runtimePlugins: PluginRuntimeDependency[];
  history: PluginTimelineEntry[];
  recentRuns: PluginRunSummary[];
  operationLogs: PluginTimelineEntry[];
}

export type PluginAdminItem = DeckPluginInstallation | (PluginRuntimeDependency & {
  category: 'claude-runtime';
  displayName: string;
});

export interface PluginAdminPermissions {
  canManage: boolean;
  canInstallLocal: boolean;
  canForcePurge: boolean;
}

export interface PluginInstallationListResult {
  installations: DeckPluginInstallation[];
  runtimePlugins: Array<PluginRuntimeDependency & { category: 'claude-runtime'; displayName: string }>;
  permissions: PluginAdminPermissions;
}

export interface PluginOperation {
  operationId: string;
  deckPluginId?: string;
  targetVersion?: string;
  status: PluginOperationStatus;
  phase?: string;
  progress?: number;
  message?: string;
  errorCode?: string;
  errorSummary?: string;
  updatedAt?: string;
  statusUrl?: string;
}

export interface InstallPluginInput {
  deckPluginId: string;
  deckPluginVersion: string;
  sourceType: 'marketplace' | 'local' | 'controlled';
  source: string;
}

export type PluginMutationAction =
  | 'enable'
  | 'disable'
  | 'upgrade'
  | 'rollback'
  | 'uninstall'
  | 'reconcile'
  | 'approve-upgrade'
  | 'reject-upgrade';

export interface PluginMutationInput {
  action: PluginMutationAction;
  deckPluginId: string;
  targetVersion?: string;
  purge?: boolean;
}

export class DeckPluginApiError extends Error {
  readonly code?: string;
  readonly operationId?: string;
  readonly retryable: boolean;

  constructor(message: string, options: { code?: string; operationId?: string; retryable?: boolean } = {}) {
    super(message);
    this.name = 'DeckPluginApiError';
    this.code = options.code;
    this.operationId = options.operationId;
    this.retryable = options.retryable ?? false;
  }
}

type JsonRecord = Record<string, unknown>;

function asRecord(value: unknown): JsonRecord {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as JsonRecord : {};
}

function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

function asBoolean(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined;
}

function asNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map(asString).filter((item): item is string => Boolean(item));
}

function read<T extends string>(value: unknown, values: readonly T[], fallback: T): T {
  const candidate = asString(value);
  return candidate && values.includes(candidate as T) ? candidate as T : fallback;
}

function normalizeCapabilityDiff(value: unknown): PluginCapabilityDiffValue | undefined {
  const record = asRecord(value);
  const added = asStringArray(record.added);
  const removed = asStringArray(record.removed);
  return added.length || removed.length ? { added, removed } : undefined;
}

function normalizeTimeline(value: unknown, prefix: string): PluginTimelineEntry[] {
  if (!Array.isArray(value)) return [];
  return value.map((item, index) => {
    const record = asRecord(item);
    return {
      id: asString(record.id) ?? asString(record.operation_id) ?? `${prefix}-${index}`,
      action: asString(record.action) ?? asString(record.event_type) ?? 'status_changed',
      status: asString(record.status) ?? asString(record.result_status) ?? 'recorded',
      occurredAt: asString(record.occurred_at) ?? asString(record.created_at) ?? asString(record.updated_at),
      actor: asString(record.actor) ?? asString(record.actor_id),
      summary: asString(record.summary) ?? asString(record.message),
    };
  });
}

function normalizeRuns(value: unknown): PluginRunSummary[] {
  if (!Array.isArray(value)) return [];
  return value.map((item, index) => {
    const record = asRecord(item);
    return {
      runId: asString(record.run_id) ?? asString(record.workflow_run_id) ?? `run-${index}`,
      status: asString(record.status) ?? 'unknown',
      startedAt: asString(record.started_at) ?? asString(record.created_at),
    };
  });
}

function normalizeRuntimePlugin(value: unknown, parentDeckPluginId?: string): PluginRuntimeDependency {
  const record = asRecord(value);
  const materialization = read(
    record.materialization_status,
    ['missing', 'materializing', 'materialized', 'failed'] as const,
    'missing',
  );
  const activation = read(
    record.activation_status ?? record.load_status,
    ['inactive', 'loadable', 'loaded', 'load_failed'] as const,
    'inactive',
  );
  return {
    claudeCodePluginId: asString(record.claude_code_plugin_id) ?? asString(record.plugin_id) ?? 'unknown-runtime-plugin',
    resolvedVersion: asString(record.resolved_version) ?? asString(record.version) ?? 'unresolved',
    versionConstraint: asString(record.version_constraint),
    artifactDigest: asString(record.artifact_digest),
    declarationStatus: read(record.declaration_status, ['undeclared', 'declared', 'disabled'] as const, 'undeclared'),
    materializationStatus: materialization,
    activationStatus: activation,
    healthStatus: read(record.health_status, ['healthy', 'degraded', 'failed', 'unknown'] as const,
      materialization === 'failed' || activation === 'load_failed' ? 'failed' : 'unknown'),
    lastErrorCode: asString(record.last_error_code),
    lastErrorSummary: asString(record.last_error_summary),
    parentDeckPluginId,
  };
}

export function normalizeDeckPluginInstallation(value: unknown): DeckPluginInstallation {
  const record = asRecord(value);
  const readiness = asRecord(record.runtime_readiness);
  const compatibility = asRecord(record.compatibility);
  const manifest = asRecord(record.manifest);
  const capabilities = asRecord(record.capabilities);
  const source = asRecord(record.source);
  const deckPluginId = asString(record.deck_plugin_id) ?? 'unknown-deck-plugin';
  const installedVersions = asStringArray(record.installed_versions);
  const defaultVersion = asString(record.default_version);
  const status = read(
    record.status,
    ['installing', 'ready', 'disabled', 'error', 'upgrade_pending', 'uninstalled'] as const,
    'error',
  );
  const materializationStatus = read(
    readiness.materialization_status ?? record.materialization_status,
    ['missing', 'materializing', 'materialized', 'failed'] as const,
    status === 'installing' ? 'materializing' : status === 'ready' || status === 'disabled' ? 'materialized' : 'missing',
  );
  const activationStatus = read(
    readiness.activation_status ?? record.activation_status,
    ['inactive', 'loadable', 'loaded', 'load_failed'] as const,
    status === 'ready' ? 'loadable' : 'inactive',
  );
  const requestedCapabilities = asStringArray(
    capabilities.manifest_requested ?? record.manifest_requested_capabilities ?? manifest.capabilities,
  );
  const approvedCapabilities = asStringArray(record.approved_capabilities);
  const effectiveCapabilities = asStringArray(
    compatibility.effective_capabilities ?? capabilities.effective ?? record.effective_capabilities,
  );
  const sourceType = read(
    source.type ?? record.source_type,
    ['marketplace', 'local', 'controlled', 'unknown'] as const,
    'unknown',
  );
  return {
    category: 'deck-workflow',
    deckPluginInstallationId: asString(record.deck_plugin_installation_id) ?? asString(record.id) ?? deckPluginId,
    deckPluginId,
    displayName: asString(record.display_name) ?? asString(manifest.display_name) ?? deckPluginId,
    deckPluginVersion: asString(record.deck_plugin_version) ?? defaultVersion ?? installedVersions.at(-1) ?? 'unresolved',
    installedVersions,
    defaultVersion,
    availableVersion: asString(record.available_version) ?? asString(record.latest_version),
    sourceType,
    sourceLabel: asString(source.label) ?? asString(source.uri) ?? asString(record.source_label) ?? sourceType,
    sourceVerified: asBoolean(source.verified) ?? asBoolean(record.source_verified),
    status,
    declarationStatus: read(
      readiness.declaration_status ?? record.declaration_status,
      ['undeclared', 'declared', 'disabled'] as const,
      status === 'uninstalled' ? 'undeclared' : status === 'disabled' ? 'disabled' : 'declared',
    ),
    materializationStatus,
    activationStatus,
    compatibilityStatus: read(
      compatibility.status ?? record.compatibility_status,
      ['compatible', 'incompatible', 'pending'] as const,
      compatibility.passed === true ? 'compatible' : compatibility.passed === false ? 'incompatible' : 'pending',
    ),
    compatibilitySummary: asString(compatibility.summary) ?? asString(compatibility.recovery_action),
    healthStatus: read(
      record.health_status,
      ['healthy', 'degraded', 'failed', 'unknown'] as const,
      record.last_error_code || materializationStatus === 'failed' || activationStatus === 'load_failed' ? 'failed' : status === 'ready' ? 'healthy' : 'unknown',
    ),
    manifestRequestedCapabilities: requestedCapabilities,
    effectiveCapabilities: effectiveCapabilities.length ? effectiveCapabilities : approvedCapabilities,
    capabilityDiff: normalizeCapabilityDiff(record.capability_diff),
    lastErrorCode: asString(record.last_error_code),
    lastErrorSummary: asString(record.last_error_summary),
    lastErrorStage: asString(record.last_error_stage),
    operationId: asString(record.operation_id),
    lastRunAt: asString(record.last_run_at),
    updatedAt: asString(record.updated_at),
    rollbackVersions: asStringArray(record.rollback_versions).length
      ? asStringArray(record.rollback_versions)
      : installedVersions.filter((version) => version !== defaultVersion),
    isSystem: asBoolean(record.is_system) ?? false,
    manifest: Object.keys(manifest).length ? {
      schemaVersion: asString(manifest.schema_version),
      author: asString(manifest.author),
      workflowReferences: asStringArray(manifest.workflow_references ?? manifest.workflows),
      inputSchemaVersion: asString(manifest.input_schema_version),
      outputSchemaVersion: asString(manifest.output_schema_version),
      deckRuntimeContract: asString(manifest.deck_runtime_contract),
    } : undefined,
    runtimePlugins: (Array.isArray(record.runtime_plugins) ? record.runtime_plugins : Array.isArray(manifest.runtime_plugins) ? manifest.runtime_plugins : [])
      .map((item) => normalizeRuntimePlugin(item, deckPluginId)),
    history: normalizeTimeline(record.history ?? record.status_history, `${deckPluginId}-history`),
    recentRuns: normalizeRuns(record.recent_runs),
    operationLogs: normalizeTimeline(record.operation_logs, `${deckPluginId}-operation`),
  };
}

function authHeaders(json = false): HeadersInit {
  const token = getAuthToken();
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function readPayload(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return {};
  }
}

async function request(path: string, init: RequestInit = {}): Promise<unknown> {
  const response = await fetch(apiUrl(path), {
    credentials: 'include',
    ...init,
    headers: { ...authHeaders(Boolean(init.body)), ...init.headers },
  });
  const payload = await readPayload(response);
  if (!response.ok) {
    const record = asRecord(payload);
    const nested = asRecord(record.error);
    throw new DeckPluginApiError(
      asString(nested.summary) ?? asString(record.message) ?? asString(record.detail) ?? '插件管理请求失败，请稍后重试。',
      {
        code: asString(nested.code) ?? asString(record.error_code),
        operationId: asString(nested.operation_id) ?? asString(record.operation_id),
        retryable: asBoolean(nested.retryable),
      },
    );
  }
  return payload;
}

function normalizePermissions(payload: JsonRecord): PluginAdminPermissions {
  const permissions = asRecord(payload.permissions);
  return {
    canManage: permissions.can_manage === true || payload.can_manage === true,
    canInstallLocal: permissions.can_install_local === true || payload.can_install_local === true,
    canForcePurge: permissions.can_force_purge === true || payload.can_force_purge === true,
  };
}

export async function listPluginInstallations(signal?: AbortSignal): Promise<PluginInstallationListResult> {
  const payload = await request('/api/deck-plugins/installations', { signal });
  const record = asRecord(payload);
  const rawInstallations = Array.isArray(payload)
    ? payload
    : Array.isArray(record.installations) ? record.installations : Array.isArray(record.items) ? record.items : [];
  const installations = rawInstallations.map(normalizeDeckPluginInstallation);
  const explicitRuntime = Array.isArray(record.runtime_plugins)
    ? record.runtime_plugins.map((item) => normalizeRuntimePlugin(item))
    : installations.flatMap((item) => item.runtimePlugins);
  const runtimePlugins = explicitRuntime.map((item) => ({
    ...item,
    category: 'claude-runtime' as const,
    displayName: item.claudeCodePluginId,
  }));
  return { installations, runtimePlugins, permissions: normalizePermissions(record) };
}

export async function getPluginInstallationDetail(
  deckPluginId: string,
  version: string,
  signal?: AbortSignal,
): Promise<DeckPluginInstallation> {
  const payload = await request(
    `/api/deck-plugins/${encodeURIComponent(deckPluginId)}/versions/${encodeURIComponent(version)}`,
    { signal },
  );
  const record = asRecord(payload);
  return normalizeDeckPluginInstallation(record.installation ?? record.data ?? payload);
}

export async function getPluginRuntimeReadiness(deckPluginId: string, signal?: AbortSignal): Promise<Partial<DeckPluginInstallation>> {
  const payload = await request(`/api/deck-plugins/${encodeURIComponent(deckPluginId)}/runtime-readiness`, { signal });
  const record = asRecord(payload);
  const normalized = normalizeDeckPluginInstallation({ deck_plugin_id: deckPluginId, runtime_readiness: record.data ?? payload });
  return {
    declarationStatus: normalized.declarationStatus,
    materializationStatus: normalized.materializationStatus,
    activationStatus: normalized.activationStatus,
    healthStatus: normalized.healthStatus,
    lastErrorCode: normalized.lastErrorCode,
    lastErrorSummary: normalized.lastErrorSummary,
  };
}

export async function installPlugin(input: InstallPluginInput): Promise<PluginOperation> {
  const payload = await request('/api/deck-plugins/install', {
    method: 'POST',
    body: JSON.stringify({
      deck_plugin_id: input.deckPluginId,
      deck_plugin_version: input.deckPluginVersion,
      source_type: input.sourceType,
      source: input.source,
    }),
  });
  return normalizeOperation(payload, input.deckPluginId, input.deckPluginVersion);
}

export async function mutatePlugin(input: PluginMutationInput): Promise<PluginOperation> {
  const plugin = encodeURIComponent(input.deckPluginId);
  const routeByAction: Record<PluginMutationAction, string> = {
    enable: `/api/deck-plugins/${plugin}/enable`,
    disable: `/api/deck-plugins/${plugin}/disable`,
    upgrade: `/api/deck-plugins/${plugin}/upgrade`,
    rollback: `/api/deck-plugins/${plugin}/rollback`,
    uninstall: `/api/deck-plugins/${plugin}/uninstall`,
    reconcile: `/api/deck-plugins/${plugin}/reconcile`,
    'approve-upgrade': `/api/deck-plugins/${plugin}/upgrade/approve`,
    'reject-upgrade': `/api/deck-plugins/${plugin}/upgrade/reject`,
  };
  const payload = await request(routeByAction[input.action], {
    method: 'POST',
    body: JSON.stringify({
      ...(input.targetVersion ? { target_version: input.targetVersion } : {}),
      ...(input.action === 'uninstall' ? { purge: input.purge === true } : {}),
    }),
  });
  return normalizeOperation(payload, input.deckPluginId, input.targetVersion);
}

export function normalizeOperation(value: unknown, deckPluginId?: string, targetVersion?: string): PluginOperation {
  const record = asRecord(value);
  const data = asRecord(record.operation ?? record.data);
  const source = Object.keys(data).length ? data : record;
  return {
    operationId: asString(source.operation_id) ?? asString(source.id) ?? `pending-${Date.now()}`,
    deckPluginId: asString(source.deck_plugin_id) ?? deckPluginId,
    targetVersion: asString(source.target_version) ?? targetVersion,
    status: read(source.status, ['queued', 'running', 'ready', 'completed', 'error', 'failed'] as const, 'queued'),
    phase: asString(source.phase),
    progress: asNumber(source.progress),
    message: asString(source.message) ?? asString(source.summary),
    errorCode: asString(source.error_code),
    errorSummary: asString(source.error_summary),
    updatedAt: asString(source.updated_at),
    statusUrl: asString(source.status_url),
  };
}

export async function getPluginOperation(operation: PluginOperation, signal?: AbortSignal): Promise<PluginOperation> {
  const path = operation.statusUrl && operation.statusUrl.startsWith('/')
    ? operation.statusUrl
    : `/api/deck-plugins/operations/${encodeURIComponent(operation.operationId)}`;
  const payload = await request(path, { signal });
  return normalizeOperation(payload, operation.deckPluginId, operation.targetVersion);
}
