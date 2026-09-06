// [Input] Current hydrated/live UIMessage window plus latest or older persisted page.
// [Output] Pure ID-stable reset/merge/prepend operations with deterministic de-duplication.
// [Pos] Shared pagination reducer seam used by ChatPanel and provider-free tests.
// [Sync] 2026-09-02: created for concurrent latest recovery and older-page prepend.

import type { UIMessage } from 'ai';

export interface ChatScrollAnchor {
  readonly scroller: HTMLElement;
  readonly element: HTMLElement;
  readonly top: number;
}

export function captureChatScrollAnchor(
  scroller: HTMLElement | null,
  element: HTMLElement | null,
): ChatScrollAnchor | null {
  return scroller && element
    ? { scroller, element, top: element.getBoundingClientRect().top }
    : null;
}

export function restoreChatScrollAnchor(anchor: ChatScrollAnchor | null): void {
  if (!anchor) return;
  anchor.scroller.scrollTop += anchor.element.getBoundingClientRect().top - anchor.top;
}

function messageMergeKey(message: UIMessage): string {
  const metadata = message.metadata && typeof message.metadata === 'object'
    ? message.metadata as Record<string, unknown>
    : null;
  const turnId = metadata?.turnId;
  return message.role === 'assistant' && typeof turnId === 'string' && turnId
    ? `turn:${turnId}`
    : `message:${message.id}`;
}

export function mergeRecoveredLatestPage(
  currentMessages: readonly UIMessage[],
  recoveredMessages: readonly UIMessage[],
): { messages: UIMessage[]; overlapsLoadedWindow: boolean } {
  const currentKeys = new Set(currentMessages.map(messageMergeKey));
  const overlapsLoadedWindow = recoveredMessages.some((message) => currentKeys.has(messageMergeKey(message)));
  if (!overlapsLoadedWindow) {
    return { messages: [...recoveredMessages], overlapsLoadedWindow: false };
  }
  const recoveredByKey = new Map(recoveredMessages.map((message) => [messageMergeKey(message), message]));
  const merged = currentMessages.map((message) => recoveredByKey.get(messageMergeKey(message)) ?? message);
  const mergedKeys = new Set(merged.map(messageMergeKey));
  for (const message of recoveredMessages) {
    const key = messageMergeKey(message);
    if (!mergedKeys.has(key)) {
      merged.push(message);
      mergedKeys.add(key);
    }
  }
  return { messages: merged, overlapsLoadedWindow: true };
}

export function prependUniqueOlderMessages(
  currentMessages: readonly UIMessage[],
  olderMessages: readonly UIMessage[],
): UIMessage[] {
  const currentKeys = new Set(currentMessages.map(messageMergeKey));
  return [
    ...olderMessages.filter((message) => !currentKeys.has(messageMergeKey(message))),
    ...currentMessages,
  ];
}

export function mergeCompleteHistoryWithLive(
  persistedMessages: readonly UIMessage[],
  liveMessages: readonly UIMessage[],
): UIMessage[] {
  const liveByKey = new Map(liveMessages.map((message) => [messageMergeKey(message), message]));
  const merged = persistedMessages.map((message) => liveByKey.get(messageMergeKey(message)) ?? message);
  const mergedKeys = new Set(merged.map(messageMergeKey));
  for (const message of liveMessages) {
    const key = messageMergeKey(message);
    if (!mergedKeys.has(key)) {
      merged.push(message);
      mergedKeys.add(key);
    }
  }
  return merged;
}
