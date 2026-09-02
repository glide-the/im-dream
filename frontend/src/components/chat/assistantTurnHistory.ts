// [Input] Hydrated AI SDK UIMessage plus server-owned Chat turn metadata.
// [Output] Pure, fail-closed projection of full or final-only historical assistant turns.
// [Pos] Shared history-turn protocol node used by every ChatPanel/ChatMessageList host.
// [Sync] 2026-09-02: support server-owned final-only v1 rows whose process loads on expansion.

import { isToolUIPart, type UIMessage } from 'ai';
import type { ChatMetadata } from '../../lib/chat-schema';

export interface HistoricalAssistantTurnProjection {
  readonly turnKey: string;
  readonly finalPartIndex: number;
  readonly processPartIndexes: readonly number[];
  readonly processAvailable: boolean;
  readonly deferredProcess: boolean;
  readonly durationMs: number | null;
}

function hasOwn(value: object, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function processPart(part: UIMessage['parts'][number]): boolean {
  if (part.type === 'reasoning' || part.type === 'tool-invocation') return true;
  try {
    return isToolUIPart(part);
  } catch {
    return false;
  }
}

/** Mirror the backend's strict completed suffix rule for untrusted browser DTOs. */
export function resolveCompletedFinalPartIndex(message: UIMessage): number | null {
  let lastProcessIndex = -1;
  for (let index = 0; index < message.parts.length; index += 1) {
    const part = message.parts[index];
    if (!part || typeof part !== 'object') return null;
    if (part.type === 'text') continue;
    if (processPart(part)) {
      lastProcessIndex = index;
      continue;
    }
    return null;
  }
  const suffix = message.parts.slice(lastProcessIndex + 1);
  if (suffix.length !== 1) return null;
  const finalPart = suffix[0];
  return finalPart.type === 'text' && typeof finalPart.text === 'string' && finalPart.text.trim()
    ? lastProcessIndex + 1
    : null;
}

function validDuration(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
    ? value
    : null;
}

/**
 * Project only an initial/older hydrated assistant message.  Any malformed new
 * completion envelope refuses legacy inference and leaves the complete message
 * on the existing diagnostic renderer.
 */
export function projectHistoricalAssistantTurn(
  message: UIMessage,
): HistoricalAssistantTurnProjection | null {
  if (message.role !== 'assistant') return null;
  const metadata = (message.metadata && typeof message.metadata === 'object')
    ? message.metadata as ChatMetadata
    : {};
  if (metadata.is_partial === true || metadata.turnProjectionInvalid === true) return null;

  if (metadata.historyProjectionVersion === 1) {
    if (typeof metadata.historyProcessAvailable !== 'boolean'
      || message.parts.length !== 1
      || message.parts[0]?.type !== 'text'
      || typeof message.parts[0].text !== 'string'
      || !message.parts[0].text.trim()) {
      return null;
    }
    const hasCompletionEnvelope = (
      hasOwn(metadata, 'turnId')
      || hasOwn(metadata, 'turnStatus')
      || hasOwn(metadata, 'finalPartIndex')
      || hasOwn(metadata, 'durationMs')
      || hasOwn(metadata, 'turnProjectionInvalid')
    );
    if (hasCompletionEnvelope && (
      metadata.turnStatus !== 'completed'
      || typeof metadata.turnId !== 'string'
      || !metadata.turnId
      || !Number.isInteger(metadata.finalPartIndex)
      || (metadata.finalPartIndex as number) < 0
      || metadata.historyProcessAvailable !== ((metadata.finalPartIndex as number) > 0)
    )) return null;
    return {
      turnKey: typeof metadata.turnId === 'string' && metadata.turnId
        ? metadata.turnId
        : message.id,
      finalPartIndex: 0,
      processPartIndexes: [],
      processAvailable: metadata.historyProcessAvailable,
      deferredProcess: metadata.historyProcessAvailable,
      durationMs: validDuration(metadata.durationMs),
    };
  }

  const strictFinalIndex = resolveCompletedFinalPartIndex(message);
  const hasNewProjection = (
    hasOwn(metadata, 'turnId')
    || hasOwn(metadata, 'turnStatus')
    || hasOwn(metadata, 'finalPartIndex')
    || hasOwn(metadata, 'durationMs')
    || hasOwn(metadata, 'turnProjectionInvalid')
  );

  let turnKey = message.id;
  let finalPartIndex = strictFinalIndex;
  let durationMs: number | null = null;
  if (hasNewProjection) {
    if (
      metadata.turnStatus !== 'completed'
      || typeof metadata.turnId !== 'string'
      || !metadata.turnId
      || !Number.isInteger(metadata.finalPartIndex)
      || (metadata.finalPartIndex as number) < 0
      || metadata.finalPartIndex !== strictFinalIndex
    ) {
      return null;
    }
    turnKey = metadata.turnId;
    finalPartIndex = metadata.finalPartIndex;
    durationMs = validDuration(metadata.durationMs);
  }
  if (finalPartIndex === null) return null;

  return {
    turnKey,
    finalPartIndex,
    processPartIndexes: message.parts
      .map((_part, index) => index)
      .filter((index) => index !== finalPartIndex),
    processAvailable: finalPartIndex > 0,
    deferredProcess: false,
    durationMs,
  };
}
