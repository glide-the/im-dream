// [Input] Same-origin browser session and authenticated Dream scheduled-task endpoints.
// [Output] Typed date/history reads and revision-checked actions for CalendarPopup.
// [Pos] Scheduled Chat browser transport; Admin remains the plan and trigger owner.
// [Sync] 2026-09-28: consume once/daily task projections without browser OAuth or local schedule calculation.
// [Sync] 2026-09-29: add the Admin-owned history cursor while keeping schedule calculation out of the browser.
// [Sync] 2026-10-07: allow optional cancellation of today's activity read; definition actions remain unchanged.
import { browserRequestHeaders } from '../lib/browserSession';
import { API_BASE } from '../lib/apiBase';

export type ScheduledRule =
  | { kind: 'once'; local_date: string; local_time: string; time_zone: string; selected_offset_minutes: number | null }
  | { kind: 'daily'; local_time: string; time_zone: string };

export type ScheduledTask = {
  id: string;
  source_thread_id: string;
  title: string;
  prompt: string;
  rule: ScheduledRule;
  next_run_at: string | null;
  status: 'active' | 'paused' | 'exhausted' | 'deleted';
  revision: number;
  created_at: string;
  updated_at: string;
};

export type ScheduledTrigger = {
  id: string;
  task_id: string;
  kind: 'scheduled' | 'manual';
  scheduled_at: string | null;
  definition_revision: number;
  title: string;
  source_thread_id: string;
  time_zone: string;
  status: 'claimed' | 'queued' | 'running' | 'succeeded' | 'failed' | 'state_unknown' | 'skipped';
  task_session_id: string | null;
  target_thread_id: string | null;
  input_message_id: string | null;
  target_turn_id: string | null;
  final_message_id: string | null;
  error_code: string | null;
  skipped_from_at: string | null;
  skipped_through_at: string | null;
  created_at: string;
  updated_at: string;
};

export class ScheduledTaskApiError extends Error {
  constructor(public readonly code: string, public readonly status: number) {
    super(code);
  }
}

async function request<T>(path: string, body?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}/api/claude-agent/scheduled-tasks${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { ...browserRequestHeaders(), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: { error_code?: string } } | null;
    throw new ScheduledTaskApiError(payload?.detail?.error_code ?? 'SCHEDULE_UNAVAILABLE', response.status);
  }
  return response.json() as Promise<T>;
}

export function getScheduledDay(localDate: string, displayTimeZone: string, options: { signal?: AbortSignal } = {}) {
  const search = new URLSearchParams({ local_date: localDate, display_time_zone: displayTimeZone });
  return request<{ tasks: ScheduledTask[]; triggers: ScheduledTrigger[] }>(`/day?${search}`, undefined, options.signal);
}

export function getScheduledTask(taskId: string) {
  return request<{ task: ScheduledTask | null }>(`/${encodeURIComponent(taskId)}`);
}

export function getScheduledHistory(taskId: string, limit = 50, beforeCreatedAt?: string) {
  const search = new URLSearchParams({ limit: String(limit) });
  if (beforeCreatedAt) search.set('before_created_at', beforeCreatedAt);
  return request<{ triggers: ScheduledTrigger[] }>(`/${encodeURIComponent(taskId)}/history?${search}`);
}

export type ScheduledTaskAction = 'edit' | 'pause' | 'resume' | 'delete' | 'restore' | 'run';

export type ScheduledTaskDefinitionAction = Exclude<ScheduledTaskAction, 'run' | 'edit'>;
export type ScheduledTaskEditBody = {
  title: string;
  prompt: string;
  rule: ScheduledRule;
  expected_revision: number;
};
export type ScheduledTaskRevisionBody = { expected_revision: number };
export type ScheduledTaskRunBody = { manual_request_key: string };
export type ScheduledTaskDefinitionResult = { task: ScheduledTask };
export type ScheduledTaskRunResult = { trigger: ScheduledTrigger };

export function updateScheduledTask(
  taskId: string,
  action: 'edit',
  body: ScheduledTaskEditBody,
): Promise<ScheduledTaskDefinitionResult>;
export function updateScheduledTask(
  taskId: string,
  action: ScheduledTaskDefinitionAction,
  body: ScheduledTaskRevisionBody,
): Promise<ScheduledTaskDefinitionResult>;
export function updateScheduledTask(
  taskId: string,
  action: 'run',
  body: ScheduledTaskRunBody,
): Promise<ScheduledTaskRunResult>;
export function updateScheduledTask(
  taskId: string,
  action: ScheduledTaskAction,
  body: ScheduledTaskEditBody | ScheduledTaskRevisionBody | ScheduledTaskRunBody,
) {
  return request<ScheduledTaskDefinitionResult | ScheduledTaskRunResult>(
    `/${encodeURIComponent(taskId)}/${action}`, body,
  );
}
