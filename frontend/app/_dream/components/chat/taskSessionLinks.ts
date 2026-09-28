// [Input] Authenticated browser session and the current Dream business Thread id.
// [Output] Strict source/created task-session navigation and server-reported task status for Chat.
// [Pos] Chat API adapter; creation, runtime state and SDK identifiers remain server-owned.
// [Sync] 2026-09-27: add fail-closed task-session relation parsing and read transport.
// [Sync] 2026-09-27: read each owned task's runtime status without inferring completion in Browser.
// [Sync] 2026-09-27: accept optional completion-result fields but omit them from the information-card projection.
// [Sync] 2026-09-27: accept the server's completed task status after final-result commit.
import { API_BASE } from '../../lib/apiBase';
import { browserRequestHeaders } from '../../lib/browserSession';

export type TaskSessionLaunchStatus = 'pending' | 'starting' | 'failed';

export interface TaskSessionLink {
  task_id: string;
  source_thread_id: string;
  thread_id: string;
  title: string;
  launch_status: TaskSessionLaunchStatus;
  launch_error_code: string | null;
  created_at: string;
}

export interface TaskSessionSourceLink extends TaskSessionLink {
  source_title: string | null;
}

export interface TaskSessionLinksSnapshot {
  source: TaskSessionSourceLink | null;
  created: TaskSessionLink[];
}

export type TaskSessionStatus = 'pending' | 'failed' | 'running' | 'idle' | 'completed' | 'state_unknown';

export interface TaskSessionDetail {
  task_id: string;
  thread_id: string;
  title: string;
  launch_status: TaskSessionLaunchStatus;
  error_code: string | null;
  status: TaskSessionStatus;
  running: boolean;
}

export class TaskSessionLinksError extends Error {
  constructor(readonly status: number) {
    super(`TASK_SESSION_LINKS_HTTP_${status}`);
  }
}

const LAUNCH_STATUSES = new Set<TaskSessionLaunchStatus>(['pending', 'starting', 'failed']);
const TASK_STATUSES = new Set<TaskSessionStatus>(['pending', 'failed', 'running', 'idle', 'completed', 'state_unknown']);

function invalidResponse(): never {
  throw new TaskSessionLinksError(502);
}

const LINK_KEYS = new Set([
  'task_id', 'source_thread_id', 'thread_id', 'title', 'launch_status',
  'launch_error_code', 'created_at',
]);

function parseLink(value: unknown, allowSourceTitle = false): TaskSessionLink {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalidResponse();
  const link = value as Record<string, unknown>;
  if (Object.keys(link).some((key) => !LINK_KEYS.has(key) && !(allowSourceTitle && key === 'source_title'))) invalidResponse();
  if (typeof link.task_id !== 'string' || link.task_id.length === 0
    || typeof link.source_thread_id !== 'string' || link.source_thread_id.length === 0
    || typeof link.thread_id !== 'string' || link.thread_id.length === 0
    || typeof link.title !== 'string'
    || typeof link.launch_status !== 'string'
    || !LAUNCH_STATUSES.has(link.launch_status as TaskSessionLaunchStatus)
    || (link.launch_error_code !== null && typeof link.launch_error_code !== 'string')
    || typeof link.created_at !== 'string' || link.created_at.length === 0) {
    invalidResponse();
  }
  return {
    task_id: link.task_id, source_thread_id: link.source_thread_id,
    thread_id: link.thread_id, title: link.title,
    launch_status: link.launch_status, launch_error_code: link.launch_error_code,
    created_at: link.created_at,
  } as TaskSessionLink;
}

function parseSource(value: unknown): TaskSessionSourceLink {
  const link = parseLink(value, true);
  const sourceTitle = (value as Record<string, unknown>).source_title;
  if (sourceTitle !== null && typeof sourceTitle !== 'string') invalidResponse();
  return { ...link, source_title: sourceTitle } as TaskSessionSourceLink;
}

function parseSnapshot(value: unknown): TaskSessionLinksSnapshot {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalidResponse();
  const snapshot = value as Record<string, unknown>;
  if (Object.keys(snapshot).some((key) => key !== 'source' && key !== 'created')
    || !Array.isArray(snapshot.created) || !Object.hasOwn(snapshot, 'source')) invalidResponse();
  return {
    source: snapshot.source === null ? null : parseSource(snapshot.source),
    created: snapshot.created.map((item) => parseLink(item)),
  };
}

export async function fetchTaskSessionLinks(threadId: string): Promise<TaskSessionLinksSnapshot> {
  const response = await fetch(
    `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/task-links`,
    { headers: { ...browserRequestHeaders() }, cache: 'no-store' },
  );
  if (!response.ok) throw new TaskSessionLinksError(response.status);
  return parseSnapshot(await response.json().catch(() => null));
}

export async function fetchTaskSessionDetail(sourceThreadId: string, taskId: string): Promise<TaskSessionDetail> {
  const response = await fetch(
    `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(sourceThreadId)}/tasks/${encodeURIComponent(taskId)}`,
    { headers: { ...browserRequestHeaders() }, cache: 'no-store' },
  );
  if (!response.ok) throw new TaskSessionLinksError(response.status);
  const value: unknown = await response.json().catch(() => null);
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalidResponse();
  const detail = value as Record<string, unknown>;
  const keys = new Set(['task_id', 'thread_id', 'title', 'launch_status', 'error_code', 'status', 'running', 'result_message_id', 'result_text']);
  if (Object.keys(detail).some((key) => !keys.has(key))
    || typeof detail.task_id !== 'string' || !detail.task_id
    || typeof detail.thread_id !== 'string' || !detail.thread_id
    || typeof detail.title !== 'string'
    || typeof detail.launch_status !== 'string' || !LAUNCH_STATUSES.has(detail.launch_status as TaskSessionLaunchStatus)
    || (detail.error_code !== null && typeof detail.error_code !== 'string')
    || typeof detail.status !== 'string' || !TASK_STATUSES.has(detail.status as TaskSessionStatus)
    || typeof detail.running !== 'boolean'
    || (detail.result_message_id !== undefined && detail.result_message_id !== null && typeof detail.result_message_id !== 'string')
    || (detail.result_text !== undefined && detail.result_text !== null && typeof detail.result_text !== 'string')
    || (detail.running && detail.status !== 'running')) invalidResponse();
  return {
    task_id: detail.task_id,
    thread_id: detail.thread_id,
    title: detail.title,
    launch_status: detail.launch_status,
    error_code: detail.error_code,
    status: detail.status,
    running: detail.running,
  } as TaskSessionDetail;
}
