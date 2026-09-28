// [Input] Owner-scoped turn-navigation DTO and the current visible UIMessage window.
// [Output] Safe, ID-stable user-turn summaries for the Chat navigation rail.
// [Pos] Pure Chat turn-navigation projection beside the shared message renderer.
// [Sync] 2026-09-29: create user-message markers and pair only replies before the next user row.

import type { UIMessage } from 'ai';
import { API_BASE } from '../../lib/apiBase';
import { browserRequestHeaders } from '../../lib/browserSession';
import { projectHistoricalAssistantTurn } from './assistantTurnHistory';

export type ChatTurnNavigationStatus = 'answered' | 'running' | 'failed' | 'cancelled' | 'no_reply' | 'state_unknown';

export interface ChatTurnNavigationItem {
  readonly messageId: string;
  readonly userPreview: string;
  readonly hasAttachment: boolean;
  readonly assistantPreview: string | null;
  readonly status: ChatTurnNavigationStatus;
}

const NON_USER_INPUT_KINDS = new Set([
  'story-workspace-dream-auto-repair',
  'story-workspace-dream-confirmation',
  'task-session-result',
]);

function metadataOf(message: UIMessage): Record<string, unknown> {
  return message.metadata && typeof message.metadata === 'object'
    ? message.metadata as Record<string, unknown>
    : {};
}

function preview(value: string): string {
  return value.replace(/\s+/g, ' ').trim();
}

export function isNavigableUserMessage(message: UIMessage): boolean {
  if (message.role !== 'user') return false;
  const metadata = metadataOf(message);
  if (NON_USER_INPUT_KINDS.has(String(metadata.kind ?? ''))
    || metadata.visibility === 'system-hidden') return false;
  return message.parts.some((part) => part.type === 'text' && Boolean(part.text?.trim())
    || part.type === 'file');
}

export function projectVisibleTurnNavigation(
  messages: readonly UIMessage[],
  running: boolean,
): ChatTurnNavigationItem[] {
  const items: ChatTurnNavigationItem[] = [];
  const runningTurnId = running
    ? [...messages].reverse().find(isNavigableUserMessage)?.id ?? null
    : null;
  let current: ChatTurnNavigationItem | null = null;
  for (const message of messages) {
    if (message.role === 'user') {
      current = null;
      if (!isNavigableUserMessage(message)) continue;
      const text = preview(message.parts
        .filter((part) => part.type === 'text')
        .map((part) => part.text)
        .join(' '));
      const filenames = message.parts
        .filter((part) => part.type === 'file')
        .map((part) => part.filename)
        .filter((name): name is string => typeof name === 'string' && Boolean(name.trim()));
      current = {
        messageId: message.id,
        userPreview: text || preview(filenames[0] ?? ''),
        hasAttachment: message.parts.some((part) => part.type === 'file'),
        assistantPreview: null,
        status: metadataOf(message).dispatch_status === 'failed' ? 'failed' : 'no_reply',
      };
      items.push(current);
      continue;
    }
    if (message.role !== 'assistant' || !current) continue;
    const metadata = metadataOf(message);
    const currentTurnRunning = current.messageId === runningTurnId;
    const projection = currentTurnRunning && metadata.turnStatus !== 'completed'
      ? null
      : projectHistoricalAssistantTurn(message);
    const final = projection ? message.parts[projection.finalPartIndex] : null;
    if (final?.type === 'text' && final.text.trim()) {
      current = { ...current, assistantPreview: preview(final.text), status: 'answered' };
    } else if (metadata.turnStatus === 'error') {
      current = { ...current, status: 'failed' };
    } else if (metadata.turnStatus === 'cancelled') {
      current = { ...current, status: 'cancelled' };
    } else if (metadata.turnProjectionInvalid === true) {
      current = { ...current, status: 'state_unknown' };
    } else if (currentTurnRunning) {
      const partial = [...message.parts].reverse().find((part) => part.type === 'text' && part.text.trim());
      current = {
        ...current,
        assistantPreview: partial?.type === 'text' ? preview(partial.text) : current.assistantPreview,
        status: 'running',
      };
    }
    items[items.length - 1] = current;
  }
  if (running && items.length > 0) {
    const last = items[items.length - 1];
    if (last.status === 'no_reply') items[items.length - 1] = { ...last, status: 'running' };
  }
  return items;
}

export function mergeTurnNavigation(
  indexed: readonly ChatTurnNavigationItem[],
  visible: readonly ChatTurnNavigationItem[],
): ChatTurnNavigationItem[] {
  const visibleById = new Map(visible.map((item) => [item.messageId, item]));
  const indexedIds = new Set(indexed.map((item) => item.messageId));
  return [
    ...indexed.map((item) => {
      const live = visibleById.get(item.messageId);
      if (!live) return item;
      return {
        ...item,
        ...live,
        assistantPreview: live.assistantPreview ?? item.assistantPreview,
        status: live.status === 'no_reply' && item.status !== 'no_reply'
          ? item.status
          : live.status,
      };
    }),
    ...visible.filter((item) => !indexedIds.has(item.messageId)),
  ];
}

export async function fetchTurnNavigation(
  threadId: string,
  signal?: AbortSignal,
): Promise<ChatTurnNavigationItem[]> {
  const response = await fetch(
    `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/turn-navigation`,
    { cache: 'no-store', headers: { ...browserRequestHeaders() }, signal },
  );
  if (!response.ok) throw new Error(`Turn navigation is unavailable (${response.status}).`);
  const payload: unknown = await response.json();
  if (!payload || typeof payload !== 'object' || !('items' in payload)
    || !Array.isArray(payload.items)) throw new Error('Turn navigation payload is invalid.');
  const validStatuses = new Set<ChatTurnNavigationStatus>(['answered', 'failed', 'cancelled', 'no_reply', 'state_unknown']);
  const items = payload.items as unknown[];
  if (!items.every((item) => {
    if (!item || typeof item !== 'object') return false;
    const value = item as Record<string, unknown>;
    return typeof value.message_id === 'string' && Boolean(value.message_id)
      && typeof value.user_preview === 'string'
      && typeof value.has_attachment === 'boolean'
      && (value.assistant_preview === null || typeof value.assistant_preview === 'string')
      && validStatuses.has(value.status as ChatTurnNavigationStatus);
  })) throw new Error('Turn navigation item is invalid.');
  return items.map((item) => {
    const value = item as Record<string, unknown>;
    return {
      messageId: value.message_id as string,
      userPreview: value.user_preview as string,
      hasAttachment: value.has_attachment as boolean,
      assistantPreview: value.assistant_preview as string | null,
      status: value.status as ChatTurnNavigationStatus,
    };
  });
}
