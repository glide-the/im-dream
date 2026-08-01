// [Input] Story Workspace workflow REST/SSE contracts and the current auth token.
// [Output] Typed, authenticated API helpers for workflow preflight and run operations.
// [Pos] Story Workspace workflow API client; it never derives authoritative workflow state locally.
import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';

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
