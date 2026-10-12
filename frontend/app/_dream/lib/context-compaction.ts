// [Input] Server-owned message metadata from live SSE or the normal history DTO.
// [Output] Validated compaction rows, latest context-use snapshots and strict legacy-text suppression.
// [Pos] Chat display protocol helper; never triggers or estimates CLI compaction.
// [Sync] 2026-10-12: require actual completion source and preserve unknown outcomes.
// [Sync] 2026-10-12: decode the latest root input/window snapshot for the existing compact command menu.
import type { UIMessage } from 'ai';

export type ContextUsageSnapshot = { readonly status: 'unavailable' } | {
  readonly status: 'available';
  readonly model: string;
  readonly inputTokens: number;
  readonly contextWindow: number;
};

export function decodeContextUsage(value: unknown): ContextUsageSnapshot | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const { status, model, inputTokens, contextWindow } = value as Record<string, unknown>;
  if (status === 'unavailable') return { status };
  if (status !== 'available' || typeof model !== 'string' || !model.trim()
    || !Number.isSafeInteger(inputTokens) || (inputTokens as number) < 0
    || !Number.isSafeInteger(contextWindow) || (contextWindow as number) <= 0) return undefined;
  return { status, model, inputTokens: inputTokens as number, contextWindow: contextWindow as number };
}

/** Never fall back across the latest reply, a model change, or an active turn. */
export function latestContextUsage(messages: readonly UIMessage[], model: unknown, running: boolean): ContextUsageSnapshot | undefined {
  if (running || typeof model !== 'string') return undefined;
  const last = messages.at(-1);
  if (last?.role !== 'assistant') return undefined;
  const metadata = last?.metadata as Record<string, unknown> | undefined;
  const snapshot = decodeContextUsage(metadata?.contextUsage);
  return snapshot?.status === 'available' && snapshot.model === model ? snapshot : undefined;
}

export function contextUsagePercentage(snapshot: ContextUsageSnapshot | undefined): number | undefined {
  const valid = decodeContextUsage(snapshot);
  return valid?.status === 'available'
    ? Math.min(100, Math.max(0, Math.round((valid.inputTokens / valid.contextWindow) * 100))) : undefined;
}
export type ContextCompactionState = 'running' | 'completed' | 'cancelled' | 'failed' | 'unconfirmed';

export interface ContextCompactionSnapshot {
  readonly id: string;
  readonly state: ContextCompactionState;
  readonly trigger: 'manual' | 'auto' | null;
}

const states = new Set<ContextCompactionState>(['running', 'completed', 'cancelled', 'failed', 'unconfirmed']);

export function decodeContextCompactions(value: unknown): ContextCompactionSnapshot[] {
  if (!Array.isArray(value)) return [];
  const rows = new Map<string, ContextCompactionSnapshot>();
  for (const candidate of value) {
    if (!candidate || typeof candidate !== 'object') continue;
    const { id, state, trigger } = candidate as Record<string, unknown>;
    if (typeof id !== 'string' || !id.trim()
      || !states.has(state as ContextCompactionState)
      || (trigger !== null && trigger !== 'manual' && trigger !== 'auto')
      || (state === 'completed' && trigger === null)) continue;
    rows.set(id, { id, state: state as ContextCompactionState, trigger });
  }
  return [...rows.values()];
}

export function readContextCompactions(metadata: unknown): ContextCompactionSnapshot[] {
  return metadata && typeof metadata === 'object'
    ? decodeContextCompactions((metadata as Record<string, unknown>).contextCompactions)
    : [];
}

export function projectContextCompactionMetadata(metadata: Record<string, unknown>): {
  contextUsage?: ContextUsageSnapshot;
  contextCompactions?: ContextCompactionSnapshot[];
  compactCompletionText?: string;
} {
  const contextCompactions = readContextCompactions(metadata);
  const contextUsage = decodeContextUsage(metadata.contextUsage);
  const completion = metadata.compactCompletionText;
  return {
    ...(contextUsage ? { contextUsage } : {}),
    ...(contextCompactions.length ? { contextCompactions } : {}),
    ...(typeof completion === 'string' && isCompactionCompletionText(completion, metadata)
      ? { compactCompletionText: completion } : {}),
  };
}

/** Only replace a server-identified synthetic completion, never ordinary prose. */
export function isCompactionCompletionText(text: string, metadata: unknown): boolean {
  if (!metadata || typeof metadata !== 'object') return false;
  const completion = (metadata as Record<string, unknown>).compactCompletionText;
  return typeof completion === 'string'
    && text === completion
    && (completion.trim() === 'Compacted' || completion.trim().startsWith('Compacted '))
    && readContextCompactions(metadata).some((row) => row.state === 'completed' && row.trigger === 'manual');
}
