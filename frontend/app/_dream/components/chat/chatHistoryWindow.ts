// [Input] Current hydrated/live UIMessage window, live-presented turn identities, plus latest or older persisted page.
// [Output] Pure ID-stable reset/merge/prepend operations that retain a verified live process for folded diagnostics and promoted App results.
// [Pos] Shared pagination reducer seam used by ChatPanel and provider-free tests.
// [Sync] 2026-09-02: created for concurrent latest recovery and older-page prepend.
// [Sync] 2026-09-06: retain a completed live turn's process when authoritative recovery returns its matching final-only summary; presentation decides which results remain outside its fold.

import { isToolUIPart, type UIMessage } from 'ai';

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

function messageMetadata(message: UIMessage): Record<string, unknown> {
  return message.metadata && typeof message.metadata === 'object'
    ? message.metadata as Record<string, unknown>
    : {};
}

function preserveVerifiedLiveProcess(
  current: UIMessage,
  recovered: UIMessage,
  livePresentedTurnIds: ReadonlySet<string>,
): UIMessage {
  if (current.role !== 'assistant' || recovered.role !== 'assistant') return recovered;
  const currentMetadata = messageMetadata(current);
  const recoveredMetadata = messageMetadata(recovered);
  const turnId = recoveredMetadata.turnId;
  if (typeof turnId !== 'string' || !livePresentedTurnIds.has(turnId)) return recovered;
  if (currentMetadata.turnId !== turnId
    || recoveredMetadata.historyProjectionVersion !== 1
    || recoveredMetadata.historyProcessAvailable !== true
    || recovered.parts.length !== 1
    || recovered.parts[0]?.type !== 'text'
    || typeof recovered.parts[0].text !== 'string') {
    return recovered;
  }
  const liveParts = current.parts.filter((part) => part.type !== 'step-start');
  const liveFinal = liveParts.at(-1);
  const hasLiveProcess = liveParts.some((part) => (
    part.type === 'reasoning'
    || part.type === 'tool-invocation'
    || isToolUIPart(part)
  ));
  if (!hasLiveProcess
    || liveFinal?.type !== 'text'
    || liveFinal.text !== recovered.parts[0].text
    || recoveredMetadata.finalPartIndex !== liveParts.length - 1) {
    return recovered;
  }

  // historyProjectionVersion describes the compact one-part DTO only. Once
  // its verified live process is retained, expose the ordinary completed-turn
  // envelope so the shared turn renderer can fold diagnostics and promote the
  // validated App result without losing either part.
  const completedMetadata = { ...recoveredMetadata };
  delete completedMetadata.historyProjectionVersion;
  delete completedMetadata.historyProcessAvailable;
  return {
    ...current,
    ...recovered,
    parts: liveParts,
    metadata: {
      ...currentMetadata,
      ...completedMetadata,
    },
  };
}

export function mergeRecoveredLatestPage(
  currentMessages: readonly UIMessage[],
  recoveredMessages: readonly UIMessage[],
  livePresentedTurnIds: ReadonlySet<string> = new Set<string>(),
): { messages: UIMessage[]; overlapsLoadedWindow: boolean } {
  const currentKeys = new Set(currentMessages.map(messageMergeKey));
  const overlapsLoadedWindow = recoveredMessages.some((message) => currentKeys.has(messageMergeKey(message)));
  if (!overlapsLoadedWindow) {
    return { messages: [...recoveredMessages], overlapsLoadedWindow: false };
  }
  const recoveredByKey = new Map(recoveredMessages.map((message) => [messageMergeKey(message), message]));
  const merged = currentMessages.map((message) => {
    const recovered = recoveredByKey.get(messageMergeKey(message));
    return recovered
      ? preserveVerifiedLiveProcess(message, recovered, livePresentedTurnIds)
      : message;
  });
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
