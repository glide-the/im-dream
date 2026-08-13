// [Input] Owned Claude thread id, canonical thread history/status REST endpoints.
// [Output] One shared history -> status hydration snapshot for Chat and Dream shells.
// [Pos] Minimal session hydration primitive; ChatPanel remains the only live reducer.

import { isToolUIPart, type UIMessage } from 'ai';
import { getAuthToken } from '../../contexts/AuthContext';
import { API_BASE } from '../../lib/apiBase';
import { filterStoryWorkspaceControlMessages } from '../../lib/story-workspace-guidance';
import {
  deriveSettledToolCallIdsFromHistory,
  loadChatHistoryThenRuntimeStatus,
  parseChatThreadStatus,
  runtimePendingToolCallIdsFromStatus,
  type ChatThreadStatusResult,
} from './toolConfirmation';

export interface ClaudeThreadRecord {
  id: string;
  title: string | null;
  deck_id?: string | null;
  voice_id?: string | null;
  created_at: string;
  updated_at: string;
}

interface RawClaudeThreadMessage {
  id: string;
  role: string;
  parts: UIMessage['parts'];
  metadata?: Record<string, unknown>;
  created_at: string;
}

export type ClaudeThreadDispatchStatus = 'dispatching' | 'dispatched' | 'failed';

export interface ClaudeThreadHistorySnapshot {
  thread?: ClaudeThreadRecord;
  messages: UIMessage[];
  dispatchStatusByMessageId: Readonly<Record<string, ClaudeThreadDispatchStatus>>;
}

export interface ClaudeThreadHydrationSnapshot extends ClaudeThreadHistorySnapshot {
  status: ChatThreadStatusResult | null;
  settledToolCallIds: ReadonlySet<string>;
  runtimePendingToolCallIds: ReadonlySet<string>;
  running: boolean;
}

export type ClaudeThreadHydrationUnknownStage = 'messages' | 'status';

/** A failed/non-authoritative REST sample is not an empty thread or an idle
 * runtime. Callers must retain their last-good state and retry. */
export class ClaudeThreadHydrationUnknownError extends Error {
  readonly stage: ClaudeThreadHydrationUnknownStage;
  readonly httpStatus: number | null;

  constructor(
    stage: ClaudeThreadHydrationUnknownStage,
    message: string,
    options: { readonly httpStatus?: number | null; readonly cause?: unknown } = {},
  ) {
    super(message, options.cause === undefined ? undefined : { cause: options.cause });
    this.name = 'ClaudeThreadHydrationUnknownError';
    this.stage = stage;
    this.httpStatus = options.httpStatus ?? null;
  }
}

/** Retry forever while a surface is mounted, but cap the delay so an outage
 * cannot create a hot loop or an ever-growing timeout. */
export function claudeThreadHydrationRetryDelayMs(attempt: number): number {
  return Math.min(4_000, 250 * (2 ** Math.min(Math.max(0, attempt), 4)));
}

/** ChatMessageList-visible parts. Unknown/data/control parts do not earn a row. */
export function claudeThreadPartIsVisible(part: unknown): boolean {
  if (!part || typeof part !== 'object' || Array.isArray(part)) return false;
  const value = part as Record<string, unknown>;
  if (value.type === 'text' || value.type === 'reasoning') {
    return typeof value.text === 'string' && value.text.trim().length > 0;
  }
  if (value.type === 'file') return true;
  try {
    return isToolUIPart(part as UIMessage['parts'][number]);
  } catch {
    return false;
  }
}

/** Preserve the shared Dream/Chat transcript and drop only empty render rows. */
export function filterClaudeThreadVisibleMessages<T extends UIMessage>(
  messages: readonly T[],
): T[] {
  return filterStoryWorkspaceControlMessages(messages).filter(
    (message) => (message.parts ?? []).some(claudeThreadPartIsVisible),
  );
}

export async function fetchClaudeThreadStatus(
  threadId: string,
): Promise<ChatThreadStatusResult> {
  try {
    const response = await fetch(
      `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/status`,
      { headers: { Authorization: `Bearer ${getAuthToken()}` } },
    );
    if (!response.ok) {
      throw new ClaudeThreadHydrationUnknownError(
        'status',
        `Claude thread status is not authoritative (${response.status}).`,
        { httpStatus: response.status },
      );
    }
    const status = parseChatThreadStatus(await response.json());
    if (status === null) {
      throw new ClaudeThreadHydrationUnknownError(
        'status',
        'Claude thread status payload is malformed.',
      );
    }
    return status;
  } catch (reason) {
    if (reason instanceof ClaudeThreadHydrationUnknownError) throw reason;
    throw new ClaudeThreadHydrationUnknownError(
      'status',
      'Claude thread status could not be read.',
      { cause: reason },
    );
  }
}

export async function fetchClaudeThreadMessages(
  threadId: string,
): Promise<ClaudeThreadHistorySnapshot> {
  try {
    const response = await fetch(
      `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
      { headers: { Authorization: `Bearer ${getAuthToken()}` } },
    );
    if (!response.ok) {
      throw new ClaudeThreadHydrationUnknownError(
        'messages',
        `Claude thread history is not authoritative (${response.status}).`,
        { httpStatus: response.status },
      );
    }
    const payload = await response.json() as {
      thread?: ClaudeThreadRecord;
      messages?: RawClaudeThreadMessage[];
    };
    if (!payload || typeof payload !== 'object' || !Array.isArray(payload.messages)) {
      throw new ClaudeThreadHydrationUnknownError(
        'messages',
        'Claude thread history payload is malformed.',
      );
    }
    const rawMessages = payload.messages;
    const dispatchStatusByMessageId: Record<string, ClaudeThreadDispatchStatus> = {};
    for (const message of rawMessages) {
      const dispatchStatus = message.metadata?.dispatch_status;
      if (dispatchStatus === 'dispatching'
        || dispatchStatus === 'dispatched'
        || dispatchStatus === 'failed') {
        dispatchStatusByMessageId[message.id] = dispatchStatus;
      }
    }
    const messages = rawMessages.map((message): UIMessage => ({
      id: message.id,
      role: message.role as UIMessage['role'],
      parts: Array.isArray(message.parts) ? message.parts : [],
      metadata: message.metadata && typeof message.metadata === 'object'
        ? message.metadata
        : undefined,
    }));
    return {
      thread: payload.thread,
      messages: filterClaudeThreadVisibleMessages(messages),
      dispatchStatusByMessageId,
    };
  } catch (reason) {
    if (reason instanceof ClaudeThreadHydrationUnknownError) throw reason;
    throw new ClaudeThreadHydrationUnknownError(
      'messages',
      'Claude thread history could not be read.',
      { cause: reason },
    );
  }
}

/** A specific persisted internal command can prove settlement even when its
 * Agent turn completed before this surface mounted. Arbitrary idle cannot. */
export function claudeThreadExpectedDispatchIsTerminal(
  snapshot: ClaudeThreadHydrationSnapshot,
  expectedMessageId: string | null | undefined,
): boolean {
  if (!expectedMessageId || snapshot.status === null || snapshot.status.running) {
    return false;
  }
  const dispatchStatus = snapshot.dispatchStatusByMessageId[expectedMessageId];
  return dispatchStatus === 'dispatched' || dispatchStatus === 'failed';
}

/**
 * Load persistence before sampling the in-memory runtime. If idle is observed,
 * loadChatHistoryThenRuntimeStatus performs the stabilizing second history read.
 */
export async function hydrateClaudeThreadSession(
  threadId: string,
): Promise<ClaudeThreadHydrationSnapshot> {
  const { history, status } = await loadChatHistoryThenRuntimeStatus(
    () => fetchClaudeThreadMessages(threadId),
    () => fetchClaudeThreadStatus(threadId),
  );
  return {
    ...history,
    status,
    settledToolCallIds: deriveSettledToolCallIdsFromHistory(history.messages, status),
    runtimePendingToolCallIds: runtimePendingToolCallIdsFromStatus(status),
    running: status?.running === true,
  };
}
