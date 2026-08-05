// [Input] Story Workspace workflow REST/SSE contracts and the current auth token.
// [Output] Typed, authenticated API helpers for workflow preflight and run operations.
// [Pos] Story Workspace workflow API client; it never derives authoritative workflow state locally.
import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';
import type {
  StoryWorkspaceDreamLaunchAccepted,
  StoryWorkspaceDreamLaunchCommand,
  StoryWorkspaceDreamReentryCollection,
  StoryWorkspaceDreamReentryItem,
} from '../hooks/story-workspace/contracts';

export const PREFLIGHT_CHECK_ORDER = [
  'identity_workspace_permission',
  'binding_release',
  'manifest_workflow_schema',
  'host_agent_runtime_compatibility',
  'capability_source_policy',
  'deck_runtime_snapshot',
  'runtime_materialization',
  'token_issuance',
] as const;

export type WorkflowPreflightCheck = typeof PREFLIGHT_CHECK_ORDER[number];
export type WorkflowPreflightStatus = 'checking' | 'passed' | 'failed' | 'expired';
export type WorkflowPreflightStepStatus = 'waiting' | 'checking' | 'passed' | 'failed';

export interface WorkflowPreflightStep {
  check: WorkflowPreflightCheck;
  status: WorkflowPreflightStepStatus;
  error_code?: string | null;
}

export interface WorkflowPreflight {
  workflow_preflight_id: string;
  deck_id: string;
  binding_revision: number;
  deck_plugin_id: string;
  deck_plugin_version: string;
  runtime_plugin_lock_id: string;
  deck_runtime_profile_id: string;
  deck_runtime_snapshot_id: string | null;
  deck_runtime_snapshot_summary_hash: string | null;
  input_hash: string;
  status: WorkflowPreflightStatus;
  current_check?: WorkflowPreflightCheck | null;
  checks?: WorkflowPreflightStep[];
  error_code: string | null;
  failed_check: WorkflowPreflightCheck | null;
  expires_at: string;
  preflight_token: string | null;
  created_at: string;
}

export type WorkflowRunStatus =
  | 'preflight'
  | 'queued'
  | 'running'
  | 'output_validating'
  | 'pending_review'
  | 'confirmed'
  | 'rejected'
  | 'continuing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface WorkflowRunStep {
  id: string;
  name: string;
  status: 'waiting' | 'running' | 'completed' | 'failed';
}

export interface WorkflowSourceContext {
  source_type: 'voice_chat';
  source_access: 'granted' | 'denied';
  voice_display_name?: string | null;
  source_message_time?: string | null;
  source_url?: string | null;
}

export interface WorkflowRunTransition {
  transition_id: string;
  transition_seq: number;
  from_status: WorkflowRunStatus | null;
  to_status: WorkflowRunStatus;
  reason_code?: string | null;
  occurred_at: string;
}

export interface WorkflowRun {
  workflow_run_id: string;
  deck_plugin_id: string;
  deck_plugin_display_name?: string | null;
  deck_plugin_version: string;
  workflow_definition_ref: string;
  workflow_summary?: string | null;
  deck_runtime_profile_id?: string | null;
  deck_runtime_snapshot_id: string;
  runtime_plugin_lock_id: string;
  runtime_load_receipt_id: string | null;
  workflow_preflight_id: string;
  status: WorkflowRunStatus;
  status_version: number;
  failed_step: string | null;
  error_code: string | null;
  retry_of_run_id: string | null;
  result_ref?: string | null;
  result_summary?: string | null;
  steps?: WorkflowRunStep[];
  current_step?: string | null;
  transitions?: WorkflowRunTransition[];
  source_context?: WorkflowSourceContext | null;
  /**
   * Chat thread that initiated the run (guidance transport channel, DEC-032).
   * Returned by the run read since SUO-198; optional for older payloads.
   */
  source_voice_thread_id?: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface WorkflowRunEvent {
  event_id: string;
  event_type: 'workflow.run.status_changed' | string;
  aggregate_version: number;
  aggregate_id: string;
  workflow_run_id?: string;
  occurred_at: string;
  payload?: {
    status?: WorkflowRunStatus;
    failed_step?: string | null;
    error_code?: string | null;
    current_step?: string | null;
    steps?: WorkflowRunStep[];
  };
}

export interface CreateWorkflowPreflightInput {
  deck_id: string;
  binding_revision: number;
  input: Record<string, unknown>;
}

export interface CreateWorkflowRunInput {
  workflow_preflight_id: string;
  preflight_token: string;
  idempotency_key: string;
  source_voice_thread_id?: string;
  source_message_id?: string;
  source_message_time?: string;
}

export interface RetryWorkflowRunInput {
  workflow_preflight_id: string;
  preflight_token: string;
  idempotency_key: string;
}

interface ApiErrorBody {
  detail?: string;
  error_code?: string;
  message?: string;
}

export const storyWorkspaceDreamLaunchEndpoint = '/api/story-workspace/dream-runs/start';
export const storyWorkspaceDreamRunsEndpoint = '/api/story-workspace/dream-runs';

export interface StoryWorkspaceDreamLaunchRequestOptions {
  fetchImpl?: typeof fetch;
  token?: string | null;
  signal?: AbortSignal;
  /** Full runtime URL override; the pure transport otherwise uses the relative path. */
  endpoint?: string;
}

export class StoryWorkspaceApiError extends Error {
  readonly errorCode: string | null;
  readonly status: number;

  constructor(status: number, errorCode: string | null) {
    super(`Story Workspace 请求失败（${status}）`);
    this.name = 'StoryWorkspaceApiError';
    this.status = status;
    this.errorCode = errorCode;
  }
}

function authHeaders(hasBody: boolean): Headers {
  const headers = new Headers({ Accept: 'application/json' });
  const token = getAuthToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (hasBody) headers.set('Content-Type', 'application/json');
  return headers;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requiredLaunchString(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new Error(`Dream launch response has invalid ${field}.`);
  }
  return value;
}

function readCompatibleLaunchField(
  value: Record<string, unknown>,
  canonical: string,
  legacy: string,
): unknown {
  const canonicalValue = value[canonical];
  const legacyValue = value[legacy];
  if (
    canonicalValue !== undefined
    && legacyValue !== undefined
    && canonicalValue !== legacyValue
  ) {
    throw new Error(`Dream launch response has conflicting ${canonical}.`);
  }
  return canonicalValue ?? legacyValue;
}

/** Validate the canonical camelCase response; snake_case is migration-only input. */
export function storyWorkspaceParseDreamLaunchAccepted(
  value: unknown,
): StoryWorkspaceDreamLaunchAccepted {
  if (!isRecord(value)) throw new Error('Dream launch response must be an object.');
  const workflowRunId = requiredLaunchString(
    readCompatibleLaunchField(value, 'workflowRunId', 'workflow_run_id'),
    'workflowRunId',
  );
  if (!/^run_[0-9a-f]{32}$/.test(workflowRunId)) {
    throw new Error('Dream launch response has invalid workflowRunId.');
  }
  return {
    workflowRunId,
    threadId: requiredLaunchString(
      readCompatibleLaunchField(value, 'threadId', 'thread_id'),
      'threadId',
    ),
  };
}

/** Start one Dream run through the dedicated Story Workspace boundary. */
export async function storyWorkspaceStartDreamRun(
  input: StoryWorkspaceDreamLaunchCommand,
  options: StoryWorkspaceDreamLaunchRequestOptions = {},
): Promise<StoryWorkspaceDreamLaunchAccepted> {
  const headers = new Headers({
    Accept: 'application/json',
    'Content-Type': 'application/json',
  });
  const token = options.token === undefined ? getAuthToken() : options.token;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await (options.fetchImpl ?? fetch)(
    options.endpoint ?? apiUrl(storyWorkspaceDreamLaunchEndpoint),
    {
      method: 'POST',
      credentials: 'include',
      headers,
      body: JSON.stringify(input),
      signal: options.signal ?? null,
    },
  );
  if (response.status !== 201) {
    let body: ApiErrorBody = {};
    try {
      body = await response.json() as ApiErrorBody;
    } catch {
      // Keep the launch page on a stable, non-sensitive technical message.
    }
    throw new StoryWorkspaceApiError(response.status, body.error_code ?? null);
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Dream launch response is not valid JSON.');
  }
  return storyWorkspaceParseDreamLaunchAccepted(payload);
}

function storyWorkspaceReadDreamRunString(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new Error(`Dream re-entry response has invalid ${field}.`);
  }
  return value;
}

function storyWorkspaceReadBoundedDreamRunString(
  value: unknown,
  field: string,
  maxLength: number,
): string {
  const parsed = storyWorkspaceReadDreamRunString(value, field);
  if (parsed.trim().length === 0 || parsed.length > maxLength) {
    throw new Error(`Dream re-entry response has invalid ${field}.`);
  }
  return parsed;
}

function storyWorkspaceReadDreamRunDate(value: unknown, field: string): string {
  const parsed = storyWorkspaceReadDreamRunString(value, field);
  const hasTimeZone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(parsed);
  const isIsoDateTime = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/i.test(parsed);
  if (!hasTimeZone || !isIsoDateTime || Number.isNaN(Date.parse(parsed))) {
    throw new Error(`Dream re-entry response has invalid ${field}.`);
  }
  return parsed;
}

function storyWorkspaceReadDreamRunRecord(value: unknown, field: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`Dream re-entry response has invalid ${field}.`);
  return value;
}

function storyWorkspaceReadDreamRunBoolean(value: unknown, field: string): boolean {
  if (typeof value !== 'boolean') {
    throw new Error(`Dream re-entry response has invalid ${field}.`);
  }
  return value;
}

function storyWorkspaceValidateDreamRunLifecycle(
  lifecycle: StoryWorkspaceDreamReentryItem['lifecycle'],
  group: StoryWorkspaceDreamReentryItem['group'],
  confirmationAccepted: boolean,
  confirmationDispatched: boolean,
): void {
  if (confirmationDispatched && !confirmationAccepted) {
    throw new Error('Dream re-entry response has incompatible confirmation facts.');
  }
  const groupMatches = lifecycle === 'recent' ? group === 'recent' : group === 'in_progress';
  if (!groupMatches) throw new Error('Dream re-entry response has incompatible recent lifecycle group.');
  if ((lifecycle === 'generating' || lifecycle === 'waiting_confirmation')
    && (confirmationAccepted || confirmationDispatched)) {
    throw new Error('Dream re-entry response has incompatible pre-confirmation facts.');
  }
  if ((lifecycle === 'continuing' || lifecycle === 'recent') && !confirmationAccepted) {
    throw new Error('Dream re-entry response has incompatible post-confirmation facts.');
  }
  if (lifecycle === 'recent' && !confirmationDispatched) {
    throw new Error('Dream re-entry response has incompatible recent facts.');
  }
}

/** Parse the server-owned collection without deriving client-side run status or order. */
export function storyWorkspaceParseDreamRuns(value: unknown): StoryWorkspaceDreamReentryCollection {
  const payload = storyWorkspaceReadDreamRunRecord(value, 'payload');
  if (!Array.isArray(payload.runs)) throw new Error('Dream re-entry response has invalid runs.');
  const runs = payload.runs.map((candidate) => {
    const run = storyWorkspaceReadDreamRunRecord(candidate, 'run');
    const lifecycle = storyWorkspaceReadDreamRunString(run.lifecycle, 'lifecycle');
    const group = storyWorkspaceReadDreamRunString(run.group, 'group');
    if (!['generating', 'waiting_confirmation', 'continuing', 'recent'].includes(lifecycle)) {
      throw new Error('Dream re-entry response has invalid lifecycle.');
    }
    if (group !== 'in_progress' && group !== 'recent') {
      throw new Error('Dream re-entry response has invalid group.');
    }
    const storyWorkspaceRunId = storyWorkspaceReadDreamRunString(
      run.storyWorkspaceRunId,
      'storyWorkspaceRunId',
    );
    if (!/^run_[0-9a-f]{32}$/.test(storyWorkspaceRunId)) {
      throw new Error('Dream re-entry response has invalid storyWorkspaceRunId.');
    }
    if (run.workflowDisplayName !== 'Dream') {
      throw new Error('Dream re-entry response has invalid workflowDisplayName.');
    }
    const stageRevisions = storyWorkspaceReadDreamRunRecord(run.stageRevisions, 'stageRevisions');
    const stageKeys = Object.keys(stageRevisions);
    if (stageKeys.some((key) => !['characters', 'scenes', 'storyboards'].includes(key))) {
      throw new Error('Dream re-entry response has invalid stage key.');
    }
    for (const revision of Object.values(stageRevisions)) {
      if (!Number.isInteger(revision) || (revision as number) < 0) {
        throw new Error('Dream re-entry response has invalid stage revision.');
      }
    }
    const confirmationAccepted = storyWorkspaceReadDreamRunBoolean(
      run.confirmationAccepted,
      'confirmationAccepted',
    );
    const confirmationDispatched = storyWorkspaceReadDreamRunBoolean(
      run.confirmationDispatched,
      'confirmationDispatched',
    );
    storyWorkspaceValidateDreamRunLifecycle(
      lifecycle as StoryWorkspaceDreamReentryItem['lifecycle'],
      group as StoryWorkspaceDreamReentryItem['group'],
      confirmationAccepted,
      confirmationDispatched,
    );
    const href = storyWorkspaceReadDreamRunString(run.href, 'href');
    if (href !== `/story-workspace/dream?run=${storyWorkspaceRunId}`) {
      throw new Error('Dream re-entry response has invalid href.');
    }
    return {
      storyWorkspaceRunId,
      deckId: storyWorkspaceReadBoundedDreamRunString(run.deckId, 'deckId', 255),
      deckDisplayName: storyWorkspaceReadBoundedDreamRunString(
        run.deckDisplayName,
        'deckDisplayName',
        255,
      ),
      workflowDisplayName: 'Dream' as const,
      deckPluginVersion: storyWorkspaceReadBoundedDreamRunString(
        run.deckPluginVersion,
        'deckPluginVersion',
        255,
      ),
      lifecycle: lifecycle as StoryWorkspaceDreamReentryItem['lifecycle'],
      group: group as StoryWorkspaceDreamReentryItem['group'],
      stageRevisions: stageRevisions as StoryWorkspaceDreamReentryItem['stageRevisions'],
      confirmationAccepted,
      confirmationDispatched,
      lastActivityAt: storyWorkspaceReadDreamRunDate(run.lastActivityAt, 'lastActivityAt'),
      createdAt: storyWorkspaceReadDreamRunDate(run.createdAt, 'createdAt'),
      sortKey: storyWorkspaceReadBoundedDreamRunString(run.sortKey, 'sortKey', 512),
      href,
    } satisfies StoryWorkspaceDreamReentryItem;
  });
  return { runs };
}

export interface StoryWorkspaceDreamRunsRequestOptions {
  endpoint?: string;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
  token?: string | null;
}

export async function storyWorkspaceFetchDreamRuns(
  options: StoryWorkspaceDreamRunsRequestOptions = {},
): Promise<StoryWorkspaceDreamReentryCollection> {
  const headers = new Headers({ Accept: 'application/json' });
  const token = options.token === undefined ? getAuthToken() : options.token;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await (options.fetchImpl ?? fetch)(
    options.endpoint ?? apiUrl(storyWorkspaceDreamRunsEndpoint),
    {
    credentials: 'include',
    headers,
    signal: options.signal,
    },
  );
  if (!response.ok) {
    throw new StoryWorkspaceApiError(response.status, null);
  }
  return storyWorkspaceParseDreamRuns(await response.json());
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: 'include',
    headers: authHeaders(init.body !== undefined),
  });
  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = await response.json() as ApiErrorBody;
    } catch {
      // Do not expose an unstructured server response to workflow UI.
    }
    throw new StoryWorkspaceApiError(response.status, body.error_code ?? null);
  }
  return response.json() as Promise<T>;
}

export function createWorkflowPreflight(
  input: CreateWorkflowPreflightInput,
): Promise<WorkflowPreflight> {
  return request('/api/story-workspace/workflow-preflights', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getWorkflowPreflight(preflightId: string): Promise<WorkflowPreflight> {
  return request(`/api/story-workspace/workflow-preflights/${encodeURIComponent(preflightId)}`);
}

export function createWorkflowRun(input: CreateWorkflowRunInput): Promise<WorkflowRun> {
  return request('/api/story-workspace/workflow-runs', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getWorkflowRun(workflowRunId: string): Promise<WorkflowRun> {
  return request(`/api/story-workspace/workflow-runs/${encodeURIComponent(workflowRunId)}`);
}

export function retryWorkflowRun(
  workflowRunId: string,
  input: RetryWorkflowRunInput,
): Promise<WorkflowRun> {
  return request(`/api/story-workspace/workflow-runs/${encodeURIComponent(workflowRunId)}/retry`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function cancelWorkflowRun(workflowRunId: string): Promise<WorkflowRun> {
  return request(`/api/story-workspace/workflow-runs/${encodeURIComponent(workflowRunId)}/cancel`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function workflowRunEventsUrl(workflowRunId: string): string {
  return apiUrl(`/api/story-workspace/workflow-runs/${encodeURIComponent(workflowRunId)}/events`);
}
