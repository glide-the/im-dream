// [Input] A run-scoped, server-allowlisted Dream Agent snapshot and SSE stream.
// [Output] Dream-only message view model; it never consumes generic Chat parts.
// [Pos] Story Workspace Dream Agent adapter (design_008 §9/§17).

import { useCallback, useEffect, useRef, useState } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import type {
  StoryWorkspaceDreamAgentEvent,
  StoryWorkspaceDreamAgentActivityCategory,
  StoryWorkspaceDreamAgentActivityContent,
  StoryWorkspaceDreamAgentContent,
  StoryWorkspaceDreamAgentMessage,
  StoryWorkspaceDreamAgentMessageAccepted,
  StoryWorkspaceDreamAgentMessageCommand,
  StoryWorkspaceDreamAgentMessageSnapshot,
  StoryWorkspaceDreamAgentToolConfirmation,
  StoryWorkspaceDreamAgentToolConfirmationCommand,
  StoryWorkspaceDreamAgentToolConfirmationQuestion,
  StoryWorkspaceDreamAgentToolConfirmationResolved,
} from './contracts';

const RUN_ID_PATTERN = /^run_[0-9a-f]{32}$/;
const MAX_TEXT_LENGTH = 4000;
const MAX_TOOL_CONFIRMATION_ANSWERS_BYTES = 8192;
const MAX_DREAM_AGENT_CONFIRMATION_TOMBSTONES = 256;
const MAX_DREAM_AGENT_CONFIRMATION_MUTATIONS = 512;
const RECONNECT_DELAYS = [500, 1000, 2000, 4000, 8000] as const;
const DREAM_AGENT_ACTIVITY_LABELS: Readonly<Record<StoryWorkspaceDreamAgentActivityCategory, StoryWorkspaceDreamAgentActivityContent['label']>> = {
  workspace_read: '读取工作区资料',
  dream_write: '更新 Dream 内容',
  reference_lookup: '查找参考资料',
  delegation: '协同处理创作任务',
  other: '处理 Dream 创作任务',
};
const DREAM_AGENT_ACTIVITY_ID = /^dream_activity_[0-9a-f]{32,64}$/;
export const STORY_WORKSPACE_DREAM_AGENT_STABLE_CONNECTION_MS = 10_000;
export const STORY_WORKSPACE_DREAM_AGENT_BUSY_POLL_INTERVAL_MS = 3_000;

export function storyWorkspaceDreamAgentShouldPollBusy(
  snapshot: Pick<
    StoryWorkspaceDreamAgentMessageSnapshot,
    'lifecycle' | 'activeTurnId' | 'sendBlockReason' | 'canSend'
  > | null | undefined,
): boolean {
  return snapshot?.lifecycle === 'idle'
    && snapshot.sendBlockReason === 'busy'
    && !snapshot.canSend;
}

export function storyWorkspaceDreamAgentShouldPollSettlement(
  snapshot: Pick<StoryWorkspaceDreamAgentMessageSnapshot, 'lifecycle'> | null | undefined,
): boolean {
  return snapshot?.lifecycle === 'streaming';
}

export function storyWorkspaceDreamAgentHasSettledMessage(
  snapshot: StoryWorkspaceDreamAgentMessageSnapshot | null | undefined,
  messageId: string,
): boolean {
  if (
    snapshot?.lifecycle !== 'idle'
    || snapshot.activeTurnId !== null
    || !snapshot.canSend
  ) return false;
  return snapshot.messages.some(
    (message) => message.id === messageId && message.role === 'user',
  );
}

export function storyWorkspaceDreamAgentReconnectDelay(attemptIndex: number): number {
  const normalizedIndex = Number.isFinite(attemptIndex)
    ? Math.max(0, Math.floor(attemptIndex))
    : 0;
  return RECONNECT_DELAYS[Math.min(normalizedIndex, RECONNECT_DELAYS.length - 1)];
}

type StoryWorkspaceDreamAgentWireRecord = Record<string, unknown>;

function storyWorkspaceDreamAgentIsRecord(value: unknown): value is StoryWorkspaceDreamAgentWireRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function storyWorkspaceDreamAgentHasOnlyKeys(
  value: StoryWorkspaceDreamAgentWireRecord,
  allowed: readonly string[],
): boolean {
  const allowedKeys = new Set(allowed);
  return Object.keys(value).every((key) => allowedKeys.has(key));
}

function storyWorkspaceDreamAgentString(value: unknown, field: string, maximum = 255): string {
  if (typeof value !== 'string' || value.length === 0 || value.length > maximum) {
    throw new Error(`Dream Agent response has invalid ${field}.`);
  }
  return value;
}

function storyWorkspaceDreamAgentDate(value: unknown, field: string): string {
  const parsed = storyWorkspaceDreamAgentString(value, field);
  if (Number.isNaN(Date.parse(parsed))) {
    throw new Error(`Dream Agent response has invalid ${field}.`);
  }
  return parsed;
}

function storyWorkspaceDreamAgentRole(value: unknown): 'user' | 'assistant' {
  if (value === 'user' || value === 'assistant') return value;
  throw new Error('Dream Agent response has invalid message role.');
}

function storyWorkspaceParseDreamAgentActivity(value: unknown): StoryWorkspaceDreamAgentActivityContent | null {
  if (!storyWorkspaceDreamAgentIsRecord(value)
    || value.kind !== 'activity'
    || typeof value.id !== 'string'
    || !DREAM_AGENT_ACTIVITY_ID.test(value.id)
    || !['workspace_read', 'dream_write', 'reference_lookup', 'delegation', 'other'].includes(String(value.category))
    || !['running', 'completed', 'stopped'].includes(String(value.status))) return null;
  const category = value.category as StoryWorkspaceDreamAgentActivityCategory;
  if (value.label !== DREAM_AGENT_ACTIVITY_LABELS[category]) return null;
  return {
    kind: 'activity',
    id: value.id,
    category,
    label: DREAM_AGENT_ACTIVITY_LABELS[category],
    status: value.status as StoryWorkspaceDreamAgentActivityContent['status'],
  };
}

function storyWorkspaceParseDreamAgentContent(
  value: unknown,
  fallbackText: string,
  fallbackTruncated: boolean,
): readonly StoryWorkspaceDreamAgentContent[] {
  if (!Array.isArray(value)) {
    return [{ kind: 'text', text: fallbackText, truncated: fallbackTruncated }];
  }
  return value.map((part): StoryWorkspaceDreamAgentContent => {
    if (storyWorkspaceDreamAgentIsRecord(part) && part.kind === 'text') {
      const text = storyWorkspaceDreamAgentString(part.text, 'message.content.text', MAX_TEXT_LENGTH);
      if (typeof part.truncated !== 'boolean') throw new Error('Dream Agent text content has invalid truncated flag.');
      return { kind: 'text', text, truncated: part.truncated };
    }
    const activity = storyWorkspaceParseDreamAgentActivity(part);
    if (activity) return activity;
    throw new Error('Dream Agent response has invalid safe content.');
  });
}

/** Parse only the safe backend projection, never generic Chat message parts. */
export function storyWorkspaceParseDreamAgentSnapshot(
  value: unknown,
): StoryWorkspaceDreamAgentMessageSnapshot {
  if (!storyWorkspaceDreamAgentIsRecord(value)) {
    throw new Error('Dream Agent response must be an object.');
  }
  const runId = storyWorkspaceDreamAgentString(value.storyWorkspaceRunId, 'storyWorkspaceRunId');
  if (!RUN_ID_PATTERN.test(runId)) throw new Error('Dream Agent response has invalid run id.');
  if (value.lifecycle !== 'idle' && value.lifecycle !== 'streaming') {
    throw new Error('Dream Agent response has invalid lifecycle.');
  }
  if (value.activeTurnId !== null && typeof value.activeTurnId !== 'string') {
    throw new Error('Dream Agent response has invalid activeTurnId.');
  }
  if (typeof value.canSend !== 'boolean') throw new Error('Dream Agent response has invalid canSend.');
  const block = value.sendBlockReason;
  if (block !== null && !['generating', 'waiting_confirmation', 'confirming', 'continuing', 'busy'].includes(String(block))) {
    throw new Error('Dream Agent response has invalid sendBlockReason.');
  }
  if (!Array.isArray(value.messages)) throw new Error('Dream Agent response has invalid messages.');
  const messages = value.messages.map((candidate): StoryWorkspaceDreamAgentMessage => {
    if (!storyWorkspaceDreamAgentIsRecord(candidate)) throw new Error('Dream Agent message must be an object.');
    const text = storyWorkspaceDreamAgentString(candidate.text, 'message.text', MAX_TEXT_LENGTH);
    if (typeof candidate.truncated !== 'boolean') throw new Error('Dream Agent response has invalid message.truncated.');
    const content = storyWorkspaceParseDreamAgentContent(candidate.content, text, candidate.truncated);
    return {
      id: storyWorkspaceDreamAgentString(candidate.id, 'message.id'),
      role: storyWorkspaceDreamAgentRole(candidate.role),
      text,
      truncated: candidate.truncated,
      content,
      createdAt: storyWorkspaceDreamAgentDate(candidate.createdAt, 'message.createdAt'),
    };
  });
  if (new Set(messages.map((message) => message.id)).size !== messages.length) {
    throw new Error('Dream Agent response repeats a message id.');
  }
  if (!Array.isArray(value.pendingToolConfirmations)) {
    throw new Error('Dream Agent response has invalid pendingToolConfirmations.');
  }
  if (value.toolConfirmationObservation !== 'known'
    && value.toolConfirmationObservation !== 'unknown') {
    throw new Error('Dream Agent response has invalid toolConfirmationObservation.');
  }
  const pendingToolConfirmations: StoryWorkspaceDreamAgentToolConfirmation[] = [];
  const seenToolCallIds = new Set<string>();
  for (const candidate of value.pendingToolConfirmations) {
    const confirmation = storyWorkspaceParseDreamAgentToolConfirmation(candidate);
    if (!confirmation) {
      throw new Error('Dream Agent response has invalid pending tool confirmation.');
    }
    if (seenToolCallIds.has(confirmation.toolCallId)) continue;
    seenToolCallIds.add(confirmation.toolCallId);
    pendingToolConfirmations.push(confirmation);
  }
  return {
    storyWorkspaceRunId: runId,
    lifecycle: value.lifecycle,
    activeTurnId: value.activeTurnId,
    canSend: value.canSend,
    sendBlockReason: block as StoryWorkspaceDreamAgentMessageSnapshot['sendBlockReason'],
    messages,
    pendingToolConfirmations,
    toolConfirmationObservation: value.toolConfirmationObservation,
    snapshotAt: storyWorkspaceDreamAgentDate(value.snapshotAt, 'snapshotAt'),
  };
}

export function storyWorkspaceDreamAgentMessagesEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/dream-agent/messages`;
}

export function storyWorkspaceDreamAgentEventsEndpoint(runId: string, cursor?: string | null): string {
  const endpoint = `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/dream-agent/events`;
  return cursor ? `${endpoint}?after=${encodeURIComponent(cursor)}` : endpoint;
}

export function storyWorkspaceDreamAgentToolConfirmationEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/dream-agent/tool-confirm`;
}

/** Keep the command surface visibly run-scoped: no thread, Deck or runtime fields cross the browser boundary. */
export function storyWorkspaceBuildDreamAgentSendPayload(
  runId: string,
  text: string,
  idempotencyKey: string,
): { readonly endpoint: string; readonly body: StoryWorkspaceDreamAgentMessageCommand } | null {
  const normalized = text.trim();
  if (!RUN_ID_PATTERN.test(runId) || !normalized || normalized.length > MAX_TEXT_LENGTH || !idempotencyKey) {
    return null;
  }
  return {
    endpoint: storyWorkspaceDreamAgentMessagesEndpoint(runId),
    body: { text: normalized, idempotencyKey },
  };
}

/** Keep tool decisions run-scoped; thread and Deck identities never cross the browser boundary. */
export function storyWorkspaceBuildDreamAgentToolConfirmationPayload(
  runId: string,
  toolCallId: string,
  approved: boolean,
  reason?: string,
  answers?: Readonly<Record<string, unknown>>,
): { readonly endpoint: string; readonly body: StoryWorkspaceDreamAgentToolConfirmationCommand } | null {
  const normalizedToolCallId = toolCallId.trim();
  const normalizedReason = reason?.trim();
  let serializedAnswers = '';
  try {
    serializedAnswers = answers ? JSON.stringify(answers) : '';
  } catch {
    return null;
  }
  if (!RUN_ID_PATTERN.test(runId)
    || !normalizedToolCallId
    || normalizedToolCallId.length > 255
    || (normalizedReason?.length ?? 0) > 500
    || new TextEncoder().encode(serializedAnswers).byteLength > MAX_TOOL_CONFIRMATION_ANSWERS_BYTES) {
    return null;
  }
  return {
    endpoint: storyWorkspaceDreamAgentToolConfirmationEndpoint(runId),
    body: {
      toolCallId: normalizedToolCallId,
      approved,
      ...(normalizedReason ? { reason: normalizedReason } : {}),
      ...(answers ? { answers } : {}),
    },
  };
}

export interface StoryWorkspaceDreamAgentFetchOptions {
  readonly fetchImpl?: typeof fetch;
  readonly token?: string | null;
  readonly signal?: AbortSignal;
  /** Test/runtime override; production uses the configured API base. */
  readonly endpoint?: string;
}

export interface StoryWorkspaceDreamAgentStreamOptions extends StoryWorkspaceDreamAgentFetchOptions {
  readonly after?: string | null;
  readonly onOpen?: () => void;
  readonly onEvent?: (event: StoryWorkspaceDreamAgentEvent) => void;
}

export async function storyWorkspaceFetchDreamAgentSnapshot(
  runId: string,
  options: StoryWorkspaceDreamAgentFetchOptions = {},
): Promise<StoryWorkspaceDreamAgentMessageSnapshot> {
  const headers = new Headers({ Accept: 'application/json' });
  const token = options.token === undefined ? getAuthToken() : options.token;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await (options.fetchImpl ?? fetch)(options.endpoint ?? apiUrl(storyWorkspaceDreamAgentMessagesEndpoint(runId)), {
    credentials: 'include', headers, signal: options.signal ?? null,
  });
  if (!response.ok) throw new Error(`Dream Agent snapshot request failed (${response.status}).`);
  return storyWorkspaceParseDreamAgentSnapshot(await response.json() as unknown);
}

export async function storyWorkspaceSubmitDreamAgentMessage(
  runId: string,
  command: StoryWorkspaceDreamAgentMessageCommand,
  options: StoryWorkspaceDreamAgentFetchOptions = {},
): Promise<StoryWorkspaceDreamAgentMessageAccepted> {
  const payload = storyWorkspaceBuildDreamAgentSendPayload(runId, command.text, command.idempotencyKey);
  if (!payload) {
    throw new Error('Dream Agent message is invalid.');
  }
  const headers = new Headers({ Accept: 'application/json', 'Content-Type': 'application/json' });
  const token = options.token === undefined ? getAuthToken() : options.token;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await (options.fetchImpl ?? fetch)(options.endpoint ?? apiUrl(payload.endpoint), {
    method: 'POST', credentials: 'include', headers,
    body: JSON.stringify(payload.body),
    signal: options.signal ?? null,
  });
  if (response.status !== 202) throw new Error(`Dream Agent message request failed (${response.status}).`);
  const value = await response.json() as unknown;
  if (!storyWorkspaceDreamAgentIsRecord(value)
    || value.storyWorkspaceRunId !== runId
    || typeof value.messageId !== 'string'
    || value.accepted !== true) {
    throw new Error('Dream Agent message response is invalid.');
  }
  return { storyWorkspaceRunId: runId, messageId: value.messageId, accepted: true };
}

export async function storyWorkspaceSubmitDreamAgentToolConfirmation(
  runId: string,
  command: StoryWorkspaceDreamAgentToolConfirmationCommand,
  options: StoryWorkspaceDreamAgentFetchOptions = {},
): Promise<StoryWorkspaceDreamAgentToolConfirmationResolved> {
  const payload = storyWorkspaceBuildDreamAgentToolConfirmationPayload(
    runId,
    command.toolCallId,
    command.approved,
    command.reason,
    command.answers,
  );
  if (!payload) throw new Error('Dream Agent tool confirmation is invalid.');
  const headers = new Headers({ Accept: 'application/json', 'Content-Type': 'application/json' });
  const token = options.token === undefined ? getAuthToken() : options.token;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await (options.fetchImpl ?? fetch)(options.endpoint ?? apiUrl(payload.endpoint), {
    method: 'POST', credentials: 'include', headers,
    body: JSON.stringify(payload.body),
    signal: options.signal ?? null,
  });
  if (!response.ok) throw new Error(`Dream Agent tool confirmation failed (${response.status}).`);
  const value = await response.json() as unknown;
  if (!storyWorkspaceDreamAgentIsRecord(value)
    || value.storyWorkspaceRunId !== runId
    || value.toolCallId !== command.toolCallId
    || value.resolved !== true) {
    throw new Error('Dream Agent tool confirmation response is invalid.');
  }
  return { storyWorkspaceRunId: runId, toolCallId: command.toolCallId, resolved: true };
}

/** Read a filtered Dream SSE stream with fetch so bearer auth, cookies and AbortSignal share one transport. */
export async function storyWorkspaceReadDreamAgentEventStream(
  runId: string,
  options: StoryWorkspaceDreamAgentStreamOptions = {},
): Promise<readonly StoryWorkspaceDreamAgentEvent[]> {
  const headers = new Headers({ Accept: 'text/event-stream' });
  const token = options.token === undefined ? getAuthToken() : options.token;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await (options.fetchImpl ?? fetch)(
    options.endpoint ?? apiUrl(storyWorkspaceDreamAgentEventsEndpoint(runId, options.after)),
    { credentials: 'include', headers, signal: options.signal ?? null },
  );
  if (!response.ok || !response.body) throw new Error(`Dream Agent event stream failed (${response.status}).`);
  options.onOpen?.();
  const decoder = new TextDecoder();
  const reader = response.body.getReader();
  const events: StoryWorkspaceDreamAgentEvent[] = [];
  let buffer = '';
  const readFrame = (frame: string) => {
    const lines = frame.split(/\r?\n/);
    const eventName = lines.find((line) => line.startsWith('event:'))?.slice(6).trim() ?? 'message';
    const cursor = lines.find((line) => line.startsWith('id:'))?.slice(3).trim() ?? '';
    const data = lines.filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim()).join('\n');
    if (!data) return;
    const parsed = storyWorkspaceParseDreamAgentEvent(eventName, data, cursor);
    if (!parsed) return;
    events.push(parsed);
    options.onEvent?.(parsed);
  };
  try {
    while (true) {
      const next = await reader.read();
      buffer += decoder.decode(next.value, { stream: !next.done });
      let boundary = buffer.search(/\r?\n\r?\n/);
      while (boundary >= 0) {
        readFrame(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary).replace(/^\r?\n\r?\n/, '');
        boundary = buffer.search(/\r?\n\r?\n/);
      }
      if (next.done) break;
    }
    if (buffer.trim()) readFrame(buffer);
  } finally {
    reader.releaseLock();
  }
  return events;
}

export interface StoryWorkspaceDreamAgentReducedState {
  readonly snapshot: StoryWorkspaceDreamAgentMessageSnapshot;
  readonly streamText: string;
  readonly streamContent: readonly StoryWorkspaceDreamAgentContent[];
  readonly streamTurnId: string | null;
  readonly pendingToolConfirmations: readonly StoryWorkspaceDreamAgentToolConfirmation[];
  readonly resolvedToolConfirmationKeys: readonly string[];
  readonly seenCursors: readonly string[];
  readonly shouldReconcile: boolean;
}

type StoryWorkspaceDreamAgentConfirmationMutation =
  | Pick<Extract<StoryWorkspaceDreamAgentEvent, { type: 'tool_confirmation_requested' }>, 'type' | 'turnId' | 'confirmation'>
  | Pick<Extract<StoryWorkspaceDreamAgentEvent, { type: 'tool_confirmation_resolved' }>, 'type' | 'turnId' | 'toolCallId'>;

interface StoryWorkspaceDreamAgentVersionedConfirmationMutation {
  readonly revision: number;
  readonly mutation: StoryWorkspaceDreamAgentConfirmationMutation;
}

function storyWorkspaceBoundDreamAgentConfirmationTombstones(
  tombstones: readonly string[],
): readonly string[] {
  return [...new Set(tombstones)].slice(-MAX_DREAM_AGENT_CONFIRMATION_TOMBSTONES);
}

function storyWorkspaceRememberDreamAgentConfirmationTombstone(
  tombstones: Set<string>,
  key: string,
): void {
  tombstones.delete(key);
  tombstones.add(key);
  while (tombstones.size > MAX_DREAM_AGENT_CONFIRMATION_TOMBSTONES) {
    const oldest = tombstones.values().next().value as string | undefined;
    if (oldest === undefined) break;
    tombstones.delete(oldest);
  }
}

function storyWorkspaceAppendDreamAgentConfirmationMutation(
  journal: readonly StoryWorkspaceDreamAgentVersionedConfirmationMutation[],
  entry: StoryWorkspaceDreamAgentVersionedConfirmationMutation,
): StoryWorkspaceDreamAgentVersionedConfirmationMutation[] {
  return [...journal, entry].slice(-MAX_DREAM_AGENT_CONFIRMATION_MUTATIONS);
}

function storyWorkspaceDreamAgentConfirmationKey(turnId: string, toolCallId: string): string {
  return JSON.stringify([turnId, toolCallId]);
}

function storyWorkspaceDreamAgentConfirmationKeyParts(
  key: string,
): readonly [string, string] | null {
  try {
    const parsed = JSON.parse(key) as unknown;
    return Array.isArray(parsed)
      && parsed.length === 2
      && typeof parsed[0] === 'string'
      && typeof parsed[1] === 'string'
      ? [parsed[0], parsed[1]]
      : null;
  } catch {
    return null;
  }
}

/** GC only from a server observation; unknown can never mean a tool settled. */
export function storyWorkspaceGarbageCollectDreamAgentConfirmationTombstones(
  tombstones: readonly string[],
  snapshot: StoryWorkspaceDreamAgentMessageSnapshot,
): readonly string[] {
  if (snapshot.toolConfirmationObservation !== 'known') {
    return storyWorkspaceBoundDreamAgentConfirmationTombstones(tombstones);
  }
  if (snapshot.activeTurnId === null) return [];
  return storyWorkspaceBoundDreamAgentConfirmationTombstones(tombstones.filter((key) => {
    const parts = storyWorkspaceDreamAgentConfirmationKeyParts(key);
    return parts !== null
      && parts[0] === snapshot.activeTurnId;
  }));
}

/**
 * Replace the local queue with the REST snapshot, then apply only SSE changes
 * that arrived after that snapshot request began. This keeps REST authoritative
 * while preserving lower-latency confirmations and resolutions.
 */
export function storyWorkspaceReconcileDreamAgentPendingToolConfirmations(
  snapshot: StoryWorkspaceDreamAgentMessageSnapshot,
  previousActiveTurnId: string | null,
  mutationsAfterRequest: readonly (
    StoryWorkspaceDreamAgentEvent | StoryWorkspaceDreamAgentConfirmationMutation
  )[],
  resolvedToolConfirmationKeys: readonly string[] = [],
): readonly StoryWorkspaceDreamAgentToolConfirmation[] {
  let activeTurnId = snapshot.activeTurnId;
  const snapshotReplacedLiveTurn = previousActiveTurnId !== null
    && snapshot.activeTurnId !== null
    && snapshot.activeTurnId !== previousActiveTurnId;
  let mayAdvanceFromSnapshotTurn = !snapshotReplacedLiveTurn;
  const tombstones = new Set(resolvedToolConfirmationKeys);
  for (const mutation of mutationsAfterRequest) {
    if (mutation.type === 'tool_confirmation_resolved') {
      tombstones.add(storyWorkspaceDreamAgentConfirmationKey(mutation.turnId, mutation.toolCallId));
    }
  }
  let pending = snapshot.pendingToolConfirmations.filter((confirmation) => (
    activeTurnId === null
    || !tombstones.has(storyWorkspaceDreamAgentConfirmationKey(activeTurnId, confirmation.toolCallId))
  ));

  for (const mutation of mutationsAfterRequest) {
    if (mutation.type !== 'tool_confirmation_requested'
      && mutation.type !== 'tool_confirmation_resolved') continue;
    if (mutation.turnId !== activeTurnId) {
      if (!mayAdvanceFromSnapshotTurn || mutation.type !== 'tool_confirmation_requested') continue;
      if (snapshot.activeTurnId === null && mutation.turnId === previousActiveTurnId) continue;
      activeTurnId = mutation.turnId;
      pending = [];
      mayAdvanceFromSnapshotTurn = false;
    }
    if (mutation.type === 'tool_confirmation_resolved') {
      pending = pending.filter((item) => item.toolCallId !== mutation.toolCallId);
      continue;
    }
    if (tombstones.has(storyWorkspaceDreamAgentConfirmationKey(
      mutation.turnId,
      mutation.confirmation.toolCallId,
    ))) continue;
    if (!pending.some((item) => item.toolCallId === mutation.confirmation.toolCallId)) {
      pending.push(mutation.confirmation);
    }
  }
  return pending;
}

function storyWorkspaceAppendDreamAgentStreamText(
  content: readonly StoryWorkspaceDreamAgentContent[],
  delta: string,
): readonly StoryWorkspaceDreamAgentContent[] {
  if (!delta) return content;
  const next = [...content];
  const last = next.at(-1);
  if (last?.kind === 'text') {
    next[next.length - 1] = { ...last, text: `${last.text}${delta}` };
  } else {
    next.push({ kind: 'text', text: delta, truncated: false });
  }
  return next;
}

function storyWorkspaceUpsertDreamAgentActivity(
  content: readonly StoryWorkspaceDreamAgentContent[],
  activity: StoryWorkspaceDreamAgentActivityContent,
): readonly StoryWorkspaceDreamAgentContent[] {
  const index = content.findIndex((item) => item.kind === 'activity' && item.id === activity.id);
  if (index < 0) return [...content, activity];
  const next = [...content];
  next[index] = activity;
  return next;
}

/** UI-only unread calculation. It never participates in run or message recovery truth. */
export function storyWorkspaceComputeDreamAgentUnreadCount(
  messages: readonly StoryWorkspaceDreamAgentMessage[],
  readThroughId: string | null,
  streamTurnId: string | null,
  readStreamTurnId: string | null,
  streamText: string,
): number {
  const assistants = messages.filter((message) => message.role === 'assistant');
  const index = readThroughId ? assistants.findIndex((message) => message.id === readThroughId) : -1;
  return Math.max(0, assistants.length - index - 1)
    + (streamText && streamTurnId !== readStreamTurnId ? 1 : 0);
}

/** Pure event seam: replay identities de-duplicate transient text, while terminal frames require a DB snapshot. */
export function storyWorkspaceReduceDreamAgentEvents(
  state: Omit<StoryWorkspaceDreamAgentReducedState, 'shouldReconcile' | 'pendingToolConfirmations' | 'streamContent' | 'resolvedToolConfirmationKeys'>
    & Partial<Pick<StoryWorkspaceDreamAgentReducedState, 'shouldReconcile' | 'pendingToolConfirmations' | 'streamContent' | 'resolvedToolConfirmationKeys'>>,
  events: readonly StoryWorkspaceDreamAgentEvent[],
): StoryWorkspaceDreamAgentReducedState {
  let streamText = state.streamText;
  let streamContent = state.streamContent ?? [];
  let streamTurnId = state.streamTurnId;
  let pendingToolConfirmations = [
    ...(state.pendingToolConfirmations ?? state.snapshot.pendingToolConfirmations),
  ];
  let shouldReconcile = Boolean(state.shouldReconcile);
  const seen = new Set(state.seenCursors);
  const resolvedToolConfirmationKeys = new Set(state.resolvedToolConfirmationKeys ?? []);
  for (const event of events) {
    if (event.type === 'assistant_text_delta') {
      if (seen.has(event.cursor)) continue;
      seen.add(event.cursor);
      streamTurnId = event.turnId;
      streamText += event.delta;
      streamContent = storyWorkspaceAppendDreamAgentStreamText(streamContent, event.delta);
      continue;
    }
    if (event.type === 'agent_activity_started' || event.type === 'agent_activity_finished') {
      if (seen.has(event.cursor)) continue;
      seen.add(event.cursor);
      streamTurnId = event.turnId;
      streamContent = storyWorkspaceUpsertDreamAgentActivity(streamContent, event.activity);
      continue;
    }
    if (event.type === 'tool_confirmation_requested') {
      if (seen.has(event.cursor)) continue;
      seen.add(event.cursor);
      const previousConfirmationTurnId = streamTurnId ?? state.snapshot.activeTurnId;
      if (previousConfirmationTurnId !== null && previousConfirmationTurnId !== event.turnId) {
        pendingToolConfirmations = [];
      }
      streamTurnId = event.turnId;
      if (!resolvedToolConfirmationKeys.has(storyWorkspaceDreamAgentConfirmationKey(
        event.turnId,
        event.confirmation.toolCallId,
      )) && !pendingToolConfirmations.some((item) => item.toolCallId === event.confirmation.toolCallId)) {
        pendingToolConfirmations.push(event.confirmation);
      }
      continue;
    }
    if (event.type === 'tool_confirmation_resolved') {
      if (seen.has(event.cursor)) continue;
      seen.add(event.cursor);
      storyWorkspaceRememberDreamAgentConfirmationTombstone(
        resolvedToolConfirmationKeys,
        storyWorkspaceDreamAgentConfirmationKey(event.turnId, event.toolCallId),
      );
      const confirmationTurnId = streamTurnId ?? state.snapshot.activeTurnId;
      if (confirmationTurnId === null || confirmationTurnId === event.turnId) {
        pendingToolConfirmations = pendingToolConfirmations.filter((item) => item.toolCallId !== event.toolCallId);
      }
      continue;
    }
    if (event.type === 'assistant_message_committed' || event.lifecycle === 'idle') {
      streamText = '';
      streamContent = [];
      streamTurnId = null;
      pendingToolConfirmations = [];
      shouldReconcile = true;
    }
  }
  return {
    snapshot: state.snapshot,
    streamText,
    streamContent,
    streamTurnId,
    pendingToolConfirmations,
    resolvedToolConfirmationKeys: [...resolvedToolConfirmationKeys],
    seenCursors: [...seen],
    shouldReconcile,
  };
}

function storyWorkspaceParseDreamAgentToolQuestion(value: unknown): StoryWorkspaceDreamAgentToolConfirmationQuestion | null {
  if (!storyWorkspaceDreamAgentIsRecord(value)
    || !storyWorkspaceDreamAgentHasOnlyKeys(value, [
      'id', 'question', 'type', 'required', 'multiSelect', 'options', 'placeholder',
    ])) return null;
  const allowedTypes = ['text', 'textarea', 'select', 'checkbox', 'radio', 'number'] as const;
  if (typeof value.id !== 'string' || !/^q[0-9]+$/.test(value.id) || value.id.length > 128
    || typeof value.question !== 'string' || !value.question || value.question.length > 300
    || !allowedTypes.includes(value.type as typeof allowedTypes[number])
    || typeof value.required !== 'boolean'
    || (value.multiSelect !== undefined && value.multiSelect !== null && typeof value.multiSelect !== 'boolean')
    || (value.placeholder !== undefined && value.placeholder !== null
      && (typeof value.placeholder !== 'string' || value.placeholder.length > 160))) return null;
  const options = Array.isArray(value.options) ? value.options.map((option) => {
    if (!storyWorkspaceDreamAgentIsRecord(option)
      || !storyWorkspaceDreamAgentHasOnlyKeys(option, ['label', 'value'])
      || typeof option.label !== 'string' || !option.label || option.label.length > 120
      || typeof option.value !== 'string' || !option.value || option.value.length > 120) return null;
    return {
      label: option.label,
      value: option.value,
    };
  }) : undefined;
  if (value.options !== undefined && value.options !== null && !Array.isArray(value.options)) return null;
  if (options?.some((option) => option === null) || (options?.length ?? 0) > 12) return null;
  return {
    id: value.id,
    question: value.question,
    type: value.type as StoryWorkspaceDreamAgentToolConfirmationQuestion['type'],
    required: value.required,
    ...(typeof value.multiSelect === 'boolean' ? { multiSelect: value.multiSelect } : {}),
    ...(options ? { options: options as NonNullable<StoryWorkspaceDreamAgentToolConfirmationQuestion['options']> } : {}),
    ...(typeof value.placeholder === 'string' ? { placeholder: value.placeholder } : {}),
  };
}

function storyWorkspaceParseDreamAgentToolConfirmation(value: unknown): StoryWorkspaceDreamAgentToolConfirmation | null {
  if (!storyWorkspaceDreamAgentIsRecord(value)
    || !storyWorkspaceDreamAgentHasOnlyKeys(value, [
      'toolCallId', 'kind', 'toolName', 'questions', 'network',
    ])
    || typeof value.toolCallId !== 'string' || !/^[A-Za-z0-9._:/-]+$/.test(value.toolCallId) || value.toolCallId.length > 255
    || (value.kind !== 'approval' && value.kind !== 'ask_user'
      && value.kind !== 'sandbox_network' && value.kind !== 'reject_only')
    || typeof value.toolName !== 'string' || !/^[A-Za-z0-9 .:-]+$/.test(value.toolName)
    || value.toolName.length > 80) return null;
  const questions = Array.isArray(value.questions)
    ? value.questions.map(storyWorkspaceParseDreamAgentToolQuestion)
    : undefined;
  if (value.questions !== undefined && value.questions !== null && !Array.isArray(value.questions)) return null;
  if (questions?.some((question) => question === null) || (questions?.length ?? 0) > 8) return null;
  let network: StoryWorkspaceDreamAgentToolConfirmation['network'];
  if (value.network !== undefined && value.network !== null) {
    if (!storyWorkspaceDreamAgentIsRecord(value.network)
      || !storyWorkspaceDreamAgentHasOnlyKeys(value.network, ['host', 'policy'])
      || (value.network.host !== null && (typeof value.network.host !== 'string'
        || value.network.host.length > 253
        || !/^(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|[A-Fa-f0-9:]+)(?::[0-9]{1,5})?$/.test(value.network.host)))
      || !['allowlist', 'open', 'deny', 'unknown'].includes(String(value.network.policy))) return null;
    network = {
      host: value.network.host as string | null,
      policy: value.network.policy as 'allowlist' | 'open' | 'deny' | 'unknown',
    };
  }
  if (value.kind === 'ask_user' && (!questions?.length || network !== undefined)) return null;
  if (value.kind === 'sandbox_network' && (!network || questions !== undefined)) return null;
  if ((value.kind === 'approval' || value.kind === 'reject_only')
    && (questions !== undefined || network !== undefined)) return null;
  return {
    toolCallId: value.toolCallId,
    kind: value.kind,
    toolName: value.toolName,
    ...(questions ? { questions: questions as NonNullable<StoryWorkspaceDreamAgentToolConfirmation['questions']> } : {}),
    ...(network ? { network } : {}),
  };
}

/** Parse one normalized allowlisted SSE event. Unknown/raw Chat events are ignored. */
export function storyWorkspaceParseDreamAgentEvent(
  eventName: string,
  rawData: string,
  cursor: string,
): StoryWorkspaceDreamAgentEvent | null {
  let value: unknown;
  try {
    value = JSON.parse(rawData) as unknown;
  } catch {
    return null;
  }
  if (!storyWorkspaceDreamAgentIsRecord(value)) return null;
  if (eventName === 'assistant_text_delta'
    && typeof value.turnId === 'string'
    && typeof value.delta === 'string'
    && value.delta.length <= MAX_TEXT_LENGTH
    && cursor) {
    return { type: 'assistant_text_delta', cursor, turnId: value.turnId, delta: value.delta };
  }
  if ((eventName === 'agent_activity_started' || eventName === 'agent_activity_finished')
    && typeof value.turnId === 'string'
    && cursor) {
    const activity = storyWorkspaceParseDreamAgentActivity(value.activity);
    if (!activity) return null;
    if (eventName === 'agent_activity_started' && activity.status !== 'running') return null;
    if (eventName === 'agent_activity_finished' && activity.status === 'running') return null;
    return { type: eventName, cursor, turnId: value.turnId, activity };
  }
  if (eventName === 'assistant_message_committed' && typeof value.turnId === 'string') {
    return { type: 'assistant_message_committed', turnId: value.turnId };
  }
  if (eventName === 'tool_confirmation_requested'
    && typeof value.turnId === 'string'
    && cursor) {
    const confirmation = storyWorkspaceParseDreamAgentToolConfirmation(value.confirmation);
    return confirmation
      ? { type: 'tool_confirmation_requested', cursor, turnId: value.turnId, confirmation }
      : null;
  }
  if (eventName === 'tool_confirmation_resolved'
    && typeof value.turnId === 'string'
    && typeof value.toolCallId === 'string'
    && value.toolCallId.length > 0
    && value.toolCallId.length <= 255
    && cursor) {
    return { type: 'tool_confirmation_resolved', cursor, turnId: value.turnId, toolCallId: value.toolCallId };
  }
  if (eventName === 'status' && (value.lifecycle === 'idle' || value.lifecycle === 'streaming')) {
    return { type: 'status', lifecycle: value.lifecycle };
  }
  return null;
}

export function storyWorkspaceNewDreamAgentIdempotencyKey(): string {
  const token = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID().replaceAll('-', '')
    : `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
  return `dream_agent_${token}`;
}

export interface StoryWorkspaceDreamAgentViewModel {
  readonly snapshot: StoryWorkspaceDreamAgentMessageSnapshot | null;
  readonly streamText: string;
  readonly streamContent: readonly StoryWorkspaceDreamAgentContent[];
  readonly streamTurnId: string | null;
  readonly pendingToolConfirmation: StoryWorkspaceDreamAgentToolConfirmation | null;
  readonly isLoading: boolean;
  readonly isSending: boolean;
  readonly isConfirmingTool: boolean;
  readonly isReconnecting: boolean;
  readonly error: Error | null;
  readonly unreadCount: number;
  /** View-local invalidation signal emitted after a terminal turn is durably reconciled. */
  readonly settledRevision: number;
  readonly refresh: () => void;
  readonly markRead: () => void;
  readonly send: (text: string, idempotencyKey: string) => Promise<boolean>;
  readonly confirmTool: (approved: boolean, reason?: string, answers?: Readonly<Record<string, unknown>>) => Promise<boolean>;
}

/** Snapshot-first Dream-only adapter with replay de-duplication and terminal reconciliation. */
export function useStoryWorkspaceDreamAgent(runId: string | null | undefined): StoryWorkspaceDreamAgentViewModel {
  const [reload, setReload] = useState(0);
  const [snapshot, setSnapshot] = useState<StoryWorkspaceDreamAgentMessageSnapshot | null>(null);
  const [streamText, setStreamText] = useState('');
  const [streamContent, setStreamContent] = useState<readonly StoryWorkspaceDreamAgentContent[]>([]);
  const [streamTurnId, setStreamTurnId] = useState<string | null>(null);
  const [pendingToolConfirmations, setPendingToolConfirmations] = useState<readonly StoryWorkspaceDreamAgentToolConfirmation[]>([]);
  const [isLoading, setIsLoading] = useState(Boolean(runId));
  const [isSending, setIsSending] = useState(false);
  const [isConfirmingTool, setIsConfirmingTool] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [readThroughId, setReadThroughId] = useState<string | null>(null);
  const [readStreamTurnId, setReadStreamTurnId] = useState<string | null>(null);
  const [settledRevision, setSettledRevision] = useState(0);
  const inFlight = useRef(false);
  const toolConfirmationInFlight = useRef(false);
  const activeTurnIdRef = useRef<string | null>(null);
  const confirmationMutationRevisionRef = useRef(0);
  const confirmationMutationsRef = useRef<StoryWorkspaceDreamAgentVersionedConfirmationMutation[]>([]);
  const resolvedToolConfirmationKeysRef = useRef<Set<string>>(new Set());
  const refresh = useCallback(() => setReload((value) => value + 1), []);

  useEffect(() => {
    if (!runId) {
      setSnapshot(null); setStreamText(''); setStreamContent([]); setStreamTurnId(null); setPendingToolConfirmations([]); setIsLoading(false);
      setSettledRevision(0);
      activeTurnIdRef.current = null;
      confirmationMutationRevisionRef.current = 0;
      confirmationMutationsRef.current = [];
      resolvedToolConfirmationKeysRef.current.clear();
      return undefined;
    }
    activeTurnIdRef.current = null;
    confirmationMutationRevisionRef.current = 0;
    confirmationMutationsRef.current = [];
    resolvedToolConfirmationKeysRef.current.clear();
    let active = true;
    let streamController: AbortController | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let stableConnectionTimer: ReturnType<typeof setTimeout> | null = null;
    let busyPollTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectIndex = 0;
    let latestCursor: string | null = null;
    let latestTurnId: string | null = null;
    let latestSnapshot: StoryWorkspaceDreamAgentMessageSnapshot | null = null;
    let terminalReconcileInFlight = false;
    const seenCursors = new Set<string>();
    const settledTurnKeys = new Set<string>();
    const controller = new AbortController();
    const markSettled = (key: string | null | undefined) => {
      if (!active || !key || settledTurnKeys.has(key)) return;
      settledTurnKeys.add(key);
      setSettledRevision((value) => value + 1);
    };
    const reconcile = async () => {
      const previousSnapshot = latestSnapshot;
      const previousActiveTurnId = latestTurnId ?? latestSnapshot?.activeTurnId ?? null;
      const mutationRevisionAtRequest = confirmationMutationRevisionRef.current;
      const next = await storyWorkspaceFetchDreamAgentSnapshot(runId, { signal: controller.signal });
      if (!active) return null;
      const mutationsAfterRequest = confirmationMutationsRef.current
        .filter((entry) => entry.revision > mutationRevisionAtRequest)
        .map((entry) => entry.mutation);
      const snapshotReplacedTurn = previousActiveTurnId !== null
        && next.activeTurnId !== previousActiveTurnId;
      if (snapshotReplacedTurn) {
        latestCursor = null;
        seenCursors.clear();
        setStreamText('');
        setStreamContent([]);
        setStreamTurnId(null);
      }
      const concurrentNextTurn = !(
        previousActiveTurnId !== null
        && next.activeTurnId !== null
        && next.activeTurnId !== previousActiveTurnId
      ) ? mutationsAfterRequest.find((mutation) => (
          mutation.type === 'tool_confirmation_requested'
          && mutation.turnId !== next.activeTurnId
          && !(next.activeTurnId === null && mutation.turnId === previousActiveTurnId)
        ))?.turnId ?? null : null;
      latestTurnId = concurrentNextTurn ?? next.activeTurnId;
      activeTurnIdRef.current = latestTurnId;
      latestSnapshot = next;
      setSnapshot(next);
      const terminalGateObserved = next.lifecycle === 'idle'
        && next.activeTurnId === null
        && (next.sendBlockReason === 'waiting_confirmation'
          || next.sendBlockReason === 'continuing');
      if ((previousSnapshot?.lifecycle === 'streaming' && next.lifecycle === 'idle')
        || (previousSnapshot === null && terminalGateObserved)) {
        markSettled(previousActiveTurnId
          ?? next.messages.filter((message) => message.role === 'assistant').at(-1)?.id);
      }
      const tombstonesBeforeObservation = [
        ...resolvedToolConfirmationKeysRef.current,
      ];
      setPendingToolConfirmations(storyWorkspaceReconcileDreamAgentPendingToolConfirmations(
        next,
        previousActiveTurnId,
        mutationsAfterRequest,
        tombstonesBeforeObservation,
      ));
      resolvedToolConfirmationKeysRef.current = new Set(
        storyWorkspaceGarbageCollectDreamAgentConfirmationTombstones(
          tombstonesBeforeObservation,
          next,
        ),
      );
      confirmationMutationsRef.current = [];
      setError(null);
      return next;
    };
    const reconcileTerminal = async () => {
      const terminalTurnId = latestTurnId ?? latestSnapshot?.activeTurnId ?? null;
      const beforeIds = new Set(latestSnapshot?.messages.filter((message) => message.role === 'assistant').map((message) => message.id));
      for (let attempt = 0; attempt < 4; attempt += 1) {
        const next = await reconcile();
        const persisted = next?.messages.some((message) => message.role === 'assistant' && !beforeIds.has(message.id));
        if (persisted || attempt === 3 || !active) {
          setStreamText(''); setStreamContent([]); setStreamTurnId(null);
          markSettled(terminalTurnId
            ?? next?.messages.filter((message) => message.role === 'assistant').at(-1)?.id);
          return next;
        }
        await new Promise<void>((resolve) => { setTimeout(resolve, 150 * (attempt + 1)); });
      }
      return null;
    };
    const clearStableConnectionTimer = () => {
      if (stableConnectionTimer) clearTimeout(stableConnectionTimer);
      stableConnectionTimer = null;
    };
    const clearBusyPollTimer = () => {
      if (busyPollTimer) clearTimeout(busyPollTimer);
      busyPollTimer = null;
    };
    const scheduleBusyPoll = (
      candidate: StoryWorkspaceDreamAgentMessageSnapshot | null | undefined,
    ) => {
      clearBusyPollTimer();
      if (!active || (!storyWorkspaceDreamAgentShouldPollBusy(candidate)
        && !storyWorkspaceDreamAgentShouldPollSettlement(candidate))) return;
      busyPollTimer = setTimeout(() => {
        busyPollTimer = null;
        void reconcile().then((next) => {
          if (next?.lifecycle === 'streaming') {
            if (!streamController) connect();
            scheduleBusyPoll(next);
          }
          else scheduleBusyPoll(next);
        }).catch((reason: unknown) => {
          if (active && reason instanceof Error && reason.name !== 'AbortError') setError(reason);
          scheduleBusyPoll(latestSnapshot);
        });
      }, STORY_WORKSPACE_DREAM_AGENT_BUSY_POLL_INTERVAL_MS);
    };
    const markStreamOpen = () => {
      if (!active) return;
      clearStableConnectionTimer();
      stableConnectionTimer = setTimeout(() => {
        stableConnectionTimer = null;
        reconnectIndex = 0;
        setIsReconnecting(false);
      }, STORY_WORKSPACE_DREAM_AGENT_STABLE_CONNECTION_MS);
    };
    const scheduleReconnect = () => {
      if (!active || reconnectTimer) return;
      setIsReconnecting(true);
      const delay = storyWorkspaceDreamAgentReconnectDelay(reconnectIndex);
      reconnectIndex += 1;
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        void reconcile().then((next) => {
          if (next?.lifecycle === 'streaming') {
            connect();
            scheduleBusyPoll(next);
          }
          else if (active) {
            setIsReconnecting(false);
            scheduleBusyPoll(next);
          }
        }).catch((reason: unknown) => {
          if (active && reason instanceof Error && reason.name !== 'AbortError') setError(reason);
          scheduleReconnect();
        });
      }, delay);
    };
    const process = (parsed: StoryWorkspaceDreamAgentEvent) => {
      if (!parsed || !active) return;
      if (parsed.type === 'assistant_text_delta') {
        if (seenCursors.has(parsed.cursor)) return;
        seenCursors.add(parsed.cursor); latestCursor = parsed.cursor; latestTurnId = parsed.turnId;
        setStreamTurnId(parsed.turnId);
        setStreamText((previous) => previous + parsed.delta);
        setStreamContent((previous) => storyWorkspaceAppendDreamAgentStreamText(previous, parsed.delta));
        return;
      }
      if (parsed.type === 'agent_activity_started' || parsed.type === 'agent_activity_finished') {
        if (seenCursors.has(parsed.cursor)) return;
        seenCursors.add(parsed.cursor); latestCursor = parsed.cursor; latestTurnId = parsed.turnId;
        setStreamTurnId(parsed.turnId);
        setStreamContent((previous) => storyWorkspaceUpsertDreamAgentActivity(previous, parsed.activity));
        return;
      }
      if (parsed.type === 'tool_confirmation_requested') {
        if (seenCursors.has(parsed.cursor)) return;
        seenCursors.add(parsed.cursor); latestCursor = parsed.cursor;
        const confirmationKey = storyWorkspaceDreamAgentConfirmationKey(
          parsed.turnId,
          parsed.confirmation.toolCallId,
        );
        const replayWasResolved = resolvedToolConfirmationKeysRef.current.has(confirmationKey);
        const replacedTurn = !replayWasResolved
          && latestTurnId !== null
          && latestTurnId !== parsed.turnId;
        if (!replayWasResolved) {
          latestTurnId = parsed.turnId;
          activeTurnIdRef.current = parsed.turnId;
        }
        confirmationMutationRevisionRef.current += 1;
        confirmationMutationsRef.current = storyWorkspaceAppendDreamAgentConfirmationMutation(
          confirmationMutationsRef.current,
          {
            revision: confirmationMutationRevisionRef.current,
            mutation: parsed,
          },
        );
        setPendingToolConfirmations((current) => (
          replayWasResolved
            ? current
            : !replacedTurn && current.some((item) => item.toolCallId === parsed.confirmation.toolCallId)
            ? current
            : [...(replacedTurn ? [] : current), parsed.confirmation]
        ));
        return;
      }
      if (parsed.type === 'tool_confirmation_resolved') {
        if (seenCursors.has(parsed.cursor)) return;
        seenCursors.add(parsed.cursor); latestCursor = parsed.cursor;
        const resolvesCurrentTurn = latestTurnId === null || latestTurnId === parsed.turnId;
        if (resolvesCurrentTurn) {
          latestTurnId = parsed.turnId;
          activeTurnIdRef.current = parsed.turnId;
        }
        confirmationMutationRevisionRef.current += 1;
        confirmationMutationsRef.current = storyWorkspaceAppendDreamAgentConfirmationMutation(
          confirmationMutationsRef.current,
          {
            revision: confirmationMutationRevisionRef.current,
            mutation: parsed,
          },
        );
        storyWorkspaceRememberDreamAgentConfirmationTombstone(
          resolvedToolConfirmationKeysRef.current,
          storyWorkspaceDreamAgentConfirmationKey(parsed.turnId, parsed.toolCallId),
        );
        if (resolvesCurrentTurn) {
          setPendingToolConfirmations((current) => current.filter((item) => item.toolCallId !== parsed.toolCallId));
        }
        return;
      }
      if (parsed.type === 'assistant_message_committed'
        || (parsed.type === 'status' && parsed.lifecycle === 'idle')) {
        if (terminalReconcileInFlight) return;
        terminalReconcileInFlight = true;
        setPendingToolConfirmations([]);
        streamController?.abort(); streamController = null;
        void reconcileTerminal().then((next) => {
          if (next?.lifecycle === 'streaming') {
            connect();
            scheduleBusyPoll(next);
          }
          else scheduleBusyPoll(next);
        }).catch((reason: unknown) => {
          if (active && reason instanceof Error && reason.name !== 'AbortError') { setError(reason); scheduleReconnect(); }
        }).finally(() => { terminalReconcileInFlight = false; });
      }
    };
    const connect = () => {
      if (!active) return;
      clearBusyPollTimer();
      streamController?.abort();
      clearStableConnectionTimer();
      streamController = new AbortController();
      void storyWorkspaceReadDreamAgentEventStream(runId, {
        after: latestCursor,
        onEvent: process,
        onOpen: markStreamOpen,
        signal: streamController.signal,
      }).then(() => {
        if (active && latestSnapshot?.lifecycle === 'streaming') scheduleReconnect();
      }).catch((reason: unknown) => {
        if (!active || (reason instanceof Error && reason.name === 'AbortError')) return;
        setError(reason instanceof Error ? reason : new Error('Dream Agent 实时消息暂不可用。'));
        scheduleReconnect();
      }).finally(clearStableConnectionTimer);
    };
    setIsLoading(true);
    void reconcile().then((next) => {
      if (next?.lifecycle === 'streaming') {
        connect();
        scheduleBusyPoll(next);
      }
      else scheduleBusyPoll(next);
    }).catch((reason: unknown) => {
      if (active && reason instanceof Error && reason.name !== 'AbortError') { setError(reason); scheduleReconnect(); }
    }).finally(() => { if (active) setIsLoading(false); });
    return () => {
      active = false; controller.abort(); streamController?.abort();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      clearBusyPollTimer();
      clearStableConnectionTimer();
    };
  }, [reload, runId]);

  const markRead = useCallback(() => {
    const lastAssistant = snapshot?.messages.filter((message) => message.role === 'assistant').at(-1);
    setReadThroughId(lastAssistant?.id ?? null);
    setReadStreamTurnId(streamTurnId);
  }, [snapshot?.messages, streamTurnId]);
  const unreadCount = storyWorkspaceComputeDreamAgentUnreadCount(
    snapshot?.messages ?? [], readThroughId, streamTurnId, readStreamTurnId, streamText,
  );
  const pendingToolConfirmation = pendingToolConfirmations[0] ?? null;
  const send = useCallback(async (text: string, idempotencyKey: string) => {
    if (!runId || !snapshot?.canSend || inFlight.current) return false;
    inFlight.current = true; setIsSending(true);
    try {
      await storyWorkspaceSubmitDreamAgentMessage(runId, {
        text, idempotencyKey,
      });
      refresh();
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason : new Error('Dream Agent 消息暂未发送。'));
      return false;
    } finally {
      inFlight.current = false; setIsSending(false);
    }
  }, [refresh, runId, snapshot?.canSend]);

  const confirmTool = useCallback(async (
    approved: boolean,
    reason?: string,
    answers?: Readonly<Record<string, unknown>>,
  ) => {
    if (!runId || !pendingToolConfirmation || toolConfirmationInFlight.current) return false;
    toolConfirmationInFlight.current = true; setIsConfirmingTool(true);
    try {
      await storyWorkspaceSubmitDreamAgentToolConfirmation(runId, {
        toolCallId: pendingToolConfirmation.toolCallId,
        approved,
        ...(reason ? { reason } : {}),
        ...(answers ? { answers } : {}),
      });
      if (activeTurnIdRef.current) {
        confirmationMutationRevisionRef.current += 1;
        confirmationMutationsRef.current = storyWorkspaceAppendDreamAgentConfirmationMutation(
          confirmationMutationsRef.current,
          {
            revision: confirmationMutationRevisionRef.current,
            mutation: {
              type: 'tool_confirmation_resolved',
              turnId: activeTurnIdRef.current,
              toolCallId: pendingToolConfirmation.toolCallId,
            },
          },
        );
        storyWorkspaceRememberDreamAgentConfirmationTombstone(
          resolvedToolConfirmationKeysRef.current,
          storyWorkspaceDreamAgentConfirmationKey(
            activeTurnIdRef.current,
            pendingToolConfirmation.toolCallId,
          ),
        );
      }
      setPendingToolConfirmations((current) => current.filter(
        (item) => item.toolCallId !== pendingToolConfirmation.toolCallId,
      ));
      setError(null);
      return true;
    } catch (reasonCaught) {
      setError(reasonCaught instanceof Error ? reasonCaught : new Error('Dream Agent 工具确认暂未提交。'));
      return false;
    } finally {
      toolConfirmationInFlight.current = false; setIsConfirmingTool(false);
    }
  }, [pendingToolConfirmation, runId]);

  return {
    snapshot, streamText, streamContent, streamTurnId, pendingToolConfirmation,
    isLoading, isSending, isConfirmingTool, isReconnecting, error, unreadCount,
    settledRevision, refresh, markRead, send, confirmTool,
  };
}
