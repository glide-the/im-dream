// [Input] A run-scoped, server-allowlisted Dream Agent snapshot and SSE stream.
// [Output] Dream-only message view model; it never consumes generic Chat parts.
// [Pos] Story Workspace Dream Agent adapter (design_008 §9/§17).

import { useCallback, useEffect, useRef, useState } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import type {
  StoryWorkspaceDreamAgentEvent,
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
const RECONNECT_DELAYS = [500, 1000, 2000, 4000, 8000] as const;

type StoryWorkspaceDreamAgentWireRecord = Record<string, unknown>;

function storyWorkspaceDreamAgentIsRecord(value: unknown): value is StoryWorkspaceDreamAgentWireRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
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
    return {
      id: storyWorkspaceDreamAgentString(candidate.id, 'message.id'),
      role: storyWorkspaceDreamAgentRole(candidate.role),
      text,
      truncated: candidate.truncated,
      createdAt: storyWorkspaceDreamAgentDate(candidate.createdAt, 'message.createdAt'),
    };
  });
  if (new Set(messages.map((message) => message.id)).size !== messages.length) {
    throw new Error('Dream Agent response repeats a message id.');
  }
  return {
    storyWorkspaceRunId: runId,
    lifecycle: value.lifecycle,
    activeTurnId: value.activeTurnId,
    canSend: value.canSend,
    sendBlockReason: block as StoryWorkspaceDreamAgentMessageSnapshot['sendBlockReason'],
    messages,
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
    || serializedAnswers.length > 16_000) {
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
  readonly streamTurnId: string | null;
  readonly pendingToolConfirmations: readonly StoryWorkspaceDreamAgentToolConfirmation[];
  readonly seenCursors: readonly string[];
  readonly shouldReconcile: boolean;
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
  state: Omit<StoryWorkspaceDreamAgentReducedState, 'shouldReconcile' | 'pendingToolConfirmations'>
    & Partial<Pick<StoryWorkspaceDreamAgentReducedState, 'shouldReconcile' | 'pendingToolConfirmations'>>,
  events: readonly StoryWorkspaceDreamAgentEvent[],
): StoryWorkspaceDreamAgentReducedState {
  let streamText = state.streamText;
  let streamTurnId = state.streamTurnId;
  let pendingToolConfirmations = [...(state.pendingToolConfirmations ?? [])];
  let shouldReconcile = Boolean(state.shouldReconcile);
  const seen = new Set(state.seenCursors);
  for (const event of events) {
    if (event.type === 'assistant_text_delta') {
      if (seen.has(event.cursor)) continue;
      seen.add(event.cursor);
      streamTurnId = event.turnId;
      streamText += event.delta;
      continue;
    }
    if (event.type === 'tool_confirmation_requested') {
      if (seen.has(event.cursor)) continue;
      seen.add(event.cursor);
      streamTurnId = event.turnId;
      if (!pendingToolConfirmations.some((item) => item.toolCallId === event.confirmation.toolCallId)) {
        pendingToolConfirmations.push(event.confirmation);
      }
      continue;
    }
    if (event.type === 'tool_confirmation_resolved') {
      if (seen.has(event.cursor)) continue;
      seen.add(event.cursor);
      pendingToolConfirmations = pendingToolConfirmations.filter((item) => item.toolCallId !== event.toolCallId);
      continue;
    }
    if (event.type === 'assistant_message_committed' || event.lifecycle === 'idle') {
      streamText = '';
      streamTurnId = null;
      pendingToolConfirmations = [];
      shouldReconcile = true;
    }
  }
  return { snapshot: state.snapshot, streamText, streamTurnId, pendingToolConfirmations, seenCursors: [...seen], shouldReconcile };
}

function storyWorkspaceParseDreamAgentToolQuestion(value: unknown): StoryWorkspaceDreamAgentToolConfirmationQuestion | null {
  if (!storyWorkspaceDreamAgentIsRecord(value)) return null;
  const allowedTypes = ['text', 'textarea', 'select', 'checkbox', 'radio', 'number'] as const;
  if (typeof value.id !== 'string' || !value.id || value.id.length > 128
    || typeof value.question !== 'string' || !value.question || value.question.length > 300
    || !allowedTypes.includes(value.type as typeof allowedTypes[number])
    || typeof value.required !== 'boolean') return null;
  const options = Array.isArray(value.options) ? value.options.map((option) => {
    if (!storyWorkspaceDreamAgentIsRecord(option)
      || typeof option.label !== 'string' || !option.label || option.label.length > 120
      || typeof option.value !== 'string' || !option.value || option.value.length > 120
      || (option.description !== undefined && (typeof option.description !== 'string' || option.description.length > 300))) return null;
    return {
      label: option.label,
      value: option.value,
      ...(typeof option.description === 'string' ? { description: option.description } : {}),
    };
  }) : undefined;
  if (options?.some((option) => option === null) || (options?.length ?? 0) > 12) return null;
  return {
    id: value.id,
    question: value.question,
    type: value.type as StoryWorkspaceDreamAgentToolConfirmationQuestion['type'],
    required: value.required,
    ...(typeof value.multiSelect === 'boolean' ? { multiSelect: value.multiSelect } : {}),
    ...(options ? { options: options as NonNullable<StoryWorkspaceDreamAgentToolConfirmationQuestion['options']> } : {}),
    ...(typeof value.placeholder === 'string' && value.placeholder.length <= 160 ? { placeholder: value.placeholder } : {}),
  };
}

function storyWorkspaceParseDreamAgentToolConfirmation(value: unknown): StoryWorkspaceDreamAgentToolConfirmation | null {
  if (!storyWorkspaceDreamAgentIsRecord(value)
    || typeof value.toolCallId !== 'string' || !value.toolCallId || value.toolCallId.length > 255
    || (value.kind !== 'approval' && value.kind !== 'ask_user' && value.kind !== 'sandbox_network')
    || typeof value.toolName !== 'string' || !value.toolName || value.toolName.length > 160) return null;
  const questions = Array.isArray(value.questions)
    ? value.questions.map(storyWorkspaceParseDreamAgentToolQuestion)
    : undefined;
  if (questions?.some((question) => question === null) || (questions?.length ?? 0) > 8) return null;
  let network: StoryWorkspaceDreamAgentToolConfirmation['network'];
  if (value.network !== undefined) {
    if (!storyWorkspaceDreamAgentIsRecord(value.network)
      || (value.network.host !== null && (typeof value.network.host !== 'string' || value.network.host.length > 255))
      || !['allowlist', 'open', 'deny', 'unknown'].includes(String(value.network.policy))) return null;
    network = {
      host: value.network.host as string | null,
      policy: value.network.policy as 'allowlist' | 'open' | 'deny' | 'unknown',
    };
  }
  return {
    toolCallId: value.toolCallId,
    kind: value.kind,
    toolName: value.toolName,
    ...(typeof value.title === 'string' && value.title.length <= 300 ? { title: value.title } : {}),
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
  readonly streamTurnId: string | null;
  readonly pendingToolConfirmation: StoryWorkspaceDreamAgentToolConfirmation | null;
  readonly isLoading: boolean;
  readonly isSending: boolean;
  readonly isConfirmingTool: boolean;
  readonly isReconnecting: boolean;
  readonly error: Error | null;
  readonly unreadCount: number;
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
  const [streamTurnId, setStreamTurnId] = useState<string | null>(null);
  const [pendingToolConfirmations, setPendingToolConfirmations] = useState<readonly StoryWorkspaceDreamAgentToolConfirmation[]>([]);
  const [isLoading, setIsLoading] = useState(Boolean(runId));
  const [isSending, setIsSending] = useState(false);
  const [isConfirmingTool, setIsConfirmingTool] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [readThroughId, setReadThroughId] = useState<string | null>(null);
  const [readStreamTurnId, setReadStreamTurnId] = useState<string | null>(null);
  const inFlight = useRef(false);
  const toolConfirmationInFlight = useRef(false);
  const refresh = useCallback(() => setReload((value) => value + 1), []);

  useEffect(() => {
    if (!runId) {
      setSnapshot(null); setStreamText(''); setStreamTurnId(null); setPendingToolConfirmations([]); setIsLoading(false);
      return undefined;
    }
    let active = true;
    let streamController: AbortController | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectIndex = 0;
    let latestCursor: string | null = null;
    let latestTurnId: string | null = null;
    let latestSnapshot: StoryWorkspaceDreamAgentMessageSnapshot | null = null;
    const seenCursors = new Set<string>();
    const controller = new AbortController();
    const reconcile = async () => {
      const next = await storyWorkspaceFetchDreamAgentSnapshot(runId, { signal: controller.signal });
      if (!active) return null;
      if (latestTurnId && next.activeTurnId && next.activeTurnId !== latestTurnId) {
        latestCursor = null;
        seenCursors.clear();
        setPendingToolConfirmations([]);
      }
      latestSnapshot = next;
      setSnapshot(next); setError(null);
      return next;
    };
    const reconcileTerminal = async () => {
      const beforeIds = new Set(latestSnapshot?.messages.filter((message) => message.role === 'assistant').map((message) => message.id));
      for (let attempt = 0; attempt < 4; attempt += 1) {
        const next = await reconcile();
        const persisted = next?.messages.some((message) => message.role === 'assistant' && !beforeIds.has(message.id));
        if (persisted || attempt === 3 || !active) {
          setStreamText(''); setStreamTurnId(null);
          return next;
        }
        await new Promise<void>((resolve) => { setTimeout(resolve, 150 * (attempt + 1)); });
      }
      return null;
    };
    const scheduleReconnect = () => {
      if (!active || reconnectTimer) return;
      setIsReconnecting(true);
      const delay = RECONNECT_DELAYS[Math.min(reconnectIndex, RECONNECT_DELAYS.length - 1)];
      reconnectIndex += 1;
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        void reconcile().then((next) => {
          if (next?.lifecycle === 'streaming') connect();
          else if (active) setIsReconnecting(false);
        }).catch((reason: unknown) => {
          if (active && reason instanceof Error && reason.name !== 'AbortError') setError(reason);
          scheduleReconnect();
        });
      }, delay);
    };
    const process = (parsed: StoryWorkspaceDreamAgentEvent) => {
      if (!parsed || !active) return;
      reconnectIndex = 0;
      setIsReconnecting(false);
      if (parsed.type === 'assistant_text_delta') {
        if (seenCursors.has(parsed.cursor)) return;
        seenCursors.add(parsed.cursor); latestCursor = parsed.cursor; latestTurnId = parsed.turnId;
        setStreamTurnId(parsed.turnId);
        setStreamText((previous) => previous + parsed.delta);
        return;
      }
      if (parsed.type === 'tool_confirmation_requested') {
        if (seenCursors.has(parsed.cursor)) return;
        seenCursors.add(parsed.cursor); latestCursor = parsed.cursor; latestTurnId = parsed.turnId;
        setPendingToolConfirmations((current) => (
          current.some((item) => item.toolCallId === parsed.confirmation.toolCallId)
            ? current
            : [...current, parsed.confirmation]
        ));
        return;
      }
      if (parsed.type === 'tool_confirmation_resolved') {
        if (seenCursors.has(parsed.cursor)) return;
        seenCursors.add(parsed.cursor); latestCursor = parsed.cursor; latestTurnId = parsed.turnId;
        setPendingToolConfirmations((current) => current.filter((item) => item.toolCallId !== parsed.toolCallId));
        return;
      }
      if (parsed.type === 'assistant_message_committed'
        || (parsed.type === 'status' && parsed.lifecycle === 'idle')) {
        setPendingToolConfirmations([]);
        streamController?.abort(); streamController = null;
        void reconcileTerminal().then((next) => { if (next?.lifecycle === 'streaming') connect(); }).catch((reason: unknown) => {
          if (active && reason instanceof Error && reason.name !== 'AbortError') { setError(reason); scheduleReconnect(); }
        });
      }
    };
    const connect = () => {
      if (!active) return;
      streamController?.abort();
      streamController = new AbortController();
      void storyWorkspaceReadDreamAgentEventStream(runId, {
        after: latestCursor,
        onEvent: process,
        signal: streamController.signal,
      }).then(() => {
        if (active && latestSnapshot?.lifecycle === 'streaming') scheduleReconnect();
      }).catch((reason: unknown) => {
        if (!active || (reason instanceof Error && reason.name === 'AbortError')) return;
        setError(reason instanceof Error ? reason : new Error('Dream Agent 实时消息暂不可用。'));
        scheduleReconnect();
      });
    };
    setIsLoading(true);
    void reconcile().then((next) => { if (next?.lifecycle === 'streaming') connect(); }).catch((reason: unknown) => {
      if (active && reason instanceof Error && reason.name !== 'AbortError') { setError(reason); scheduleReconnect(); }
    }).finally(() => { if (active) setIsLoading(false); });
    return () => {
      active = false; controller.abort(); streamController?.abort();
      if (reconnectTimer) clearTimeout(reconnectTimer);
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
    snapshot, streamText, streamTurnId, pendingToolConfirmation,
    isLoading, isSending, isConfirmingTool, isReconnecting, error, unreadCount,
    refresh, markRead, send, confirmTool,
  };
}
