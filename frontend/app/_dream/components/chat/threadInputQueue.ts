// [Input] Authenticated browser session and owned Dream Thread input endpoints.
// [Output] Typed queue receipt, list, selection, cancellation and side-task transfer calls.
// [Pos] Chat input queue API adapter used by the existing ChatPanel.
// [Sync] 2026-09-26: keep queued input outside useChat's active SSE request.
// [Sync] 2026-09-27: cancel a single queued message by revision for card deletion and editing.
// [Sync] 2026-09-27: preserve Admin's outcome_unknown receipt for ambiguous queue submissions.
// [Sync] 2026-09-27: reject malformed queue receipts before they can corrupt Chat render state.
import { browserRequestHeaders } from '../../lib/browserSession';
import { API_BASE } from '../../lib/apiBase';

export type ThreadInputStatus =
  | 'queued' | 'selected' | 'dispatching' | 'consumed'
  | 'cancelled' | 'failed' | 'state_unknown';

export interface ThreadInputEntry {
  message_id: string;
  thread_id: string;
  queue_sequence: string;
  status: ThreadInputStatus;
  revision: number;
  dispatch_turn_id: string | null;
  created_at: string;
  text: string;
}

export interface ThreadInputSnapshot {
  entries: ThreadInputEntry[];
  local_owner: boolean;
}

export function canGuideThreadInput(entry: ThreadInputEntry, localOwner: boolean): boolean {
  return localOwner && entry.status === 'queued';
}

export class ThreadInputError extends Error {
  constructor(readonly code: string, readonly status: number, readonly outcomeUnknown = false) {
    super(code);
  }
}

const THREAD_INPUT_STATUSES = new Set<ThreadInputStatus>([
  'queued', 'selected', 'dispatching', 'consumed', 'cancelled', 'failed', 'state_unknown',
]);

function invalidResponse(): never {
  throw new ThreadInputError('CHAT_INPUT_INVALID_RESPONSE', 502);
}

function parseEntry(value: unknown): ThreadInputEntry {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalidResponse();
  const entry = value as Record<string, unknown>;
  if (typeof entry.message_id !== 'string' || entry.message_id.length === 0
    || typeof entry.thread_id !== 'string' || entry.thread_id.length === 0
    || typeof entry.queue_sequence !== 'string' || entry.queue_sequence.length === 0
    || typeof entry.status !== 'string'
    || !THREAD_INPUT_STATUSES.has(entry.status as ThreadInputStatus)
    || !Number.isInteger(entry.revision) || (entry.revision as number) < 0
    || (entry.dispatch_turn_id !== null && typeof entry.dispatch_turn_id !== 'string')
    || typeof entry.created_at !== 'string' || entry.created_at.length === 0
    || typeof entry.text !== 'string') {
    invalidResponse();
  }
  return entry as unknown as ThreadInputEntry;
}

function parseSnapshot(value: unknown): ThreadInputSnapshot {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalidResponse();
  const snapshot = value as Record<string, unknown>;
  if (!Array.isArray(snapshot.entries) || typeof snapshot.local_owner !== 'boolean') invalidResponse();
  return { entries: snapshot.entries.map(parseEntry), local_owner: snapshot.local_owner };
}

function inputUrl(threadId: string): string {
  return `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/inputs`;
}

async function checkedJson(response: Response): Promise<unknown> {
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null;
    const code = detail && typeof detail === 'object' && 'error_code' in detail
      && typeof detail.error_code === 'string'
      ? detail.error_code : `CHAT_INPUT_HTTP_${response.status}`;
    const outcomeUnknown = detail && typeof detail === 'object' && 'outcome_unknown' in detail
      && detail.outcome_unknown === true;
    throw new ThreadInputError(code, response.status, Boolean(outcomeUnknown));
  }
  return body;
}

export async function fetchThreadInputs(threadId: string): Promise<ThreadInputSnapshot> {
  const response = await fetch(inputUrl(threadId), {
    headers: { ...browserRequestHeaders() },
    cache: 'no-store',
  });
  return parseSnapshot(await checkedJson(response));
}

export async function enqueueThreadInput(
  threadId: string, messageId: string, text: string, toolChoice: string,
  deckId: string | null | undefined, voiceId: string | null | undefined,
): Promise<ThreadInputEntry> {
  const response = await fetch(inputUrl(threadId), {
    method: 'POST',
    headers: { ...browserRequestHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      thread_id: threadId, resume: true, toolChoice,
      ...(deckId ? { deckId } : {}),
      ...(voiceId ? { voiceId } : {}),
      message: { id: messageId, role: 'user', parts: [{ type: 'text', text }] },
    }),
  });
  return parseEntry(await checkedJson(response));
}

export async function selectThreadInput(
  threadId: string, entry: ThreadInputEntry,
): Promise<{ entry: ThreadInputEntry; interrupt_signalled: boolean }> {
  const response = await fetch(
    `${inputUrl(threadId)}/${encodeURIComponent(entry.message_id)}/select`,
    {
      method: 'POST',
      headers: { ...browserRequestHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ expected_revision: entry.revision }),
    },
  );
  const value = await checkedJson(response);
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalidResponse();
  const receipt = value as Record<string, unknown>;
  if (typeof receipt.interrupt_signalled !== 'boolean') invalidResponse();
  return { entry: parseEntry(receipt.entry), interrupt_signalled: receipt.interrupt_signalled };
}

export async function cancelThreadInput(
  threadId: string, entry: ThreadInputEntry,
): Promise<ThreadInputEntry> {
  const response = await fetch(
    `${inputUrl(threadId)}/${encodeURIComponent(entry.message_id)}/cancel`,
    {
      method: 'POST',
      headers: { ...browserRequestHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ expected_revision: entry.revision }),
    },
  );
  return parseEntry(await checkedJson(response));
}

export async function moveThreadInputToSideTask(
  threadId: string, entry: ThreadInputEntry,
): Promise<{ task_id: string; thread_id: string; launch_status: string; dispatch_started: boolean; error_code?: string }> {
  const response = await fetch(
    `${inputUrl(threadId)}/${encodeURIComponent(entry.message_id)}/side-task`,
    {
      method: 'POST',
      headers: { ...browserRequestHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ expected_revision: entry.revision }),
    },
  );
  const value = await checkedJson(response);
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalidResponse();
  const receipt = value as Record<string, unknown>;
  if (typeof receipt.task_id !== 'string' || receipt.task_id.length === 0
    || typeof receipt.thread_id !== 'string' || receipt.thread_id.length === 0
    || typeof receipt.launch_status !== 'string' || receipt.launch_status.length === 0
    || typeof receipt.dispatch_started !== 'boolean'
    || (receipt.error_code !== undefined && typeof receipt.error_code !== 'string')) {
    invalidResponse();
  }
  return receipt as unknown as { task_id: string; thread_id: string; launch_status: string; dispatch_started: boolean; error_code?: string };
}
