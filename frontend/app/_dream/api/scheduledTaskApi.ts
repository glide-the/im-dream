// [Input] Same-origin browser session and authenticated Dream scheduled-task endpoints.
// [Output] Typed date/history/Thread relation reads and revision-checked actions for Calendar and Chat.
// [Pos] Scheduled Chat browser transport; Admin remains the plan and trigger owner.
// [Sync] 2026-10-07: read cancellable source/execution Thread relations and reject mismatched identities.
// [Sync] 2026-10-07: consume v3 structured repeat, source/new Thread mode and immutable model snapshots.
// [Sync] 2026-09-29: add the Admin-owned history cursor while keeping schedule calculation out of the browser.
// [Sync] 2026-10-07: allow optional cancellation of today's activity read; definition actions remain unchanged.
import { browserRequestHeaders } from '../lib/browserSession';
import { API_BASE } from '../lib/apiBase';

export type ScheduledRule =
  | { kind: 'once'; local_date: string; local_time: string; time_zone: string; selected_offset_minutes: number | null }
  | { kind: 'daily'; local_time: string; time_zone: string }
  | { kind: 'interval'; interval_minutes: number; time_zone: string }
  | { kind: 'hourly'; interval_hours: number; minute: number; time_zone: string }
  | { kind: 'weekly'; weekdays: Array<'MO' | 'TU' | 'WE' | 'TH' | 'FR' | 'SA' | 'SU'>; local_time: string; time_zone: string };

export type ScheduledRunThreadMode = 'source_thread' | 'new_thread_each_run';

export type ScheduledTask = {
  id: string;
  source_thread_id: string;
  title: string;
  prompt: string;
  rule: ScheduledRule;
  run_thread_mode: ScheduledRunThreadMode;
  model_alias: string | null;
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
  run_thread_mode_snapshot: ScheduledRunThreadMode;
  model_alias_snapshot: string | null;
  skipped_from_at: string | null;
  skipped_through_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ScheduledTaskThreadSnapshot = {
  created: ScheduledTask[];
  source: { task: ScheduledTask; trigger: ScheduledTrigger } | null;
};

export class ScheduledTaskApiError extends Error {
  constructor(public readonly code: string, public readonly status: number) {
    super(code);
  }
}

async function request<T>(path: string, body?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}/api/claude-agent${path}`, {
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
  return request<{ tasks: ScheduledTask[]; triggers: ScheduledTrigger[] }>(`/scheduled-tasks/day?${search}`, undefined, options.signal);
}

export async function getThreadScheduledTasks(threadId: string, options: { signal?: AbortSignal } = {}) {
  const snapshot = await request<ScheduledTaskThreadSnapshot>(
    `/threads/${encodeURIComponent(threadId)}/scheduled-tasks`, undefined, options.signal,
  );
  if (!snapshot || !Array.isArray(snapshot.created)
    || snapshot.created.some((task) => !task || task.source_thread_id !== threadId)
    || (snapshot.source !== null && (!snapshot.source?.task || !snapshot.source?.trigger
      || snapshot.source.trigger.target_thread_id !== threadId
      || snapshot.source.trigger.task_id !== snapshot.source.task.id))) {
    throw new ScheduledTaskApiError('SCHEDULE_RELATION_INVALID', 502);
  }
  return snapshot;
}

export function getScheduledTask(taskId: string) {
  return request<{ task: ScheduledTask | null }>(`/scheduled-tasks/${encodeURIComponent(taskId)}`);
}

export function getScheduledHistory(taskId: string, limit = 50, beforeCreatedAt?: string) {
  const search = new URLSearchParams({ limit: String(limit) });
  if (beforeCreatedAt) search.set('before_created_at', beforeCreatedAt);
  return request<{ triggers: ScheduledTrigger[] }>(`/scheduled-tasks/${encodeURIComponent(taskId)}/history?${search}`);
}

export type ScheduledTaskAction = 'edit' | 'pause' | 'resume' | 'delete' | 'restore' | 'run';

export type ScheduledTaskDefinitionAction = Exclude<ScheduledTaskAction, 'run' | 'edit'>;
export type ScheduledTaskEditBody = {
  title: string;
  prompt: string;
  rule: ScheduledRule;
  run_thread_mode: ScheduledRunThreadMode;
  model_alias: string;
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
    `/scheduled-tasks/${encodeURIComponent(taskId)}/${action}`, body,
  );
}
