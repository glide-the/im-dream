// [Input] GET /api/claude-agent/threads/{thread_id}/subagents payloads.
// [Output] Thread-keyed subagent task store for the header entry and right sidebar.
// [Pos] claude-subagent projection hook in frontend/src/hooks
// [Sync] 2026-08-04: initial REST hydration store backed by workspace transcript metadata.

import { useSyncExternalStore } from 'react';
import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';

export type ThreadSubagentStatus = 'running' | 'completed' | 'failed' | 'cancelled';

export interface ThreadSubagentActivity {
  id: string;
  kind: 'message' | 'tool';
  status: 'started' | 'completed' | 'failed';
  timestamp: string | null;
  text: string | null;
  toolName: string | null;
}

export type ThreadSubagentMessageKind = 'task' | 'assistant' | 'tool_call' | 'tool_result' | 'status' | 'final' | 'system';

export interface ThreadSubagentMessage {
  id: string;
  sequence: number | null;
  kind: ThreadSubagentMessageKind;
  timestamp: string | null;
  text: string | null;
  status: string | null;
  toolName: string | null;
  toolCallId: string | null;
  input: string | null;
  output: string | null;
  redacted: boolean;
  truncated: boolean;
  legacy: boolean;
}

export interface ThreadSubagentTask {
  taskId: string;
  agentId: string;
  agentType: string;
  description: string;
  summary: string | null;
  status: ThreadSubagentStatus;
  toolCallId: string | null;
  spawnDepth: number | null;
  startedAt: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  error: string | null;
  activity: ThreadSubagentActivity[];
  messages: ThreadSubagentMessage[];
  messageCount: number;
  messagesTruncated: boolean;
  projectionVersion: number;
}

export interface ThreadSubagentCounts {
  running: number;
  completed: number;
  ended: number;
  total: number;
}

export interface ThreadSubagentState {
  exists: boolean;
  tasks: ThreadSubagentTask[];
  counts: ThreadSubagentCounts;
  updatedAt: string | null;
  loading: boolean;
  error: string | null;
}

interface ThreadSubagentApiTask {
  task_id: string;
  agent_id: string;
  agent_type: string;
  description: string;
  summary: string | null;
  status: ThreadSubagentStatus;
  tool_call_id: string | null;
  spawn_depth: number | null;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  error: string | null;
  activity?: Array<{
    id: string;
    kind: 'message' | 'tool';
    status: 'started' | 'completed' | 'failed';
    timestamp: string | null;
    text: string | null;
    tool_name: string | null;
  }>;
  messages?: Array<{
    id: string;
    sequence?: number | null;
    kind: string;
    timestamp: string | null;
    text: string | null;
    status: string | null;
    tool_name: string | null;
    tool_call_id: string | null;
    input: string | null;
    output: string | null;
    redacted?: boolean;
    truncated?: boolean;
  }>;
  message_count?: number;
  messages_truncated?: boolean;
  projection_version?: number;
}

interface ThreadSubagentApiResponse {
  exists: boolean;
  tasks: ThreadSubagentApiTask[];
  counts: ThreadSubagentCounts;
  updated_at: string | null;
}

const EMPTY_COUNTS: ThreadSubagentCounts = Object.freeze({ running: 0, completed: 0, ended: 0, total: 0 });
const EMPTY_STATE: ThreadSubagentState = Object.freeze({
  exists: false,
  tasks: Object.freeze([]) as unknown as ThreadSubagentTask[],
  counts: EMPTY_COUNTS,
  updatedAt: null,
  loading: false,
  error: null,
});

const stateByThreadId = new Map<string, ThreadSubagentState>();
const listenersByThreadId = new Map<string, Set<() => void>>();
const inFlightByThreadId = new Map<string, Promise<void>>();

function getThreadSubagents(threadId: string): ThreadSubagentState {
  return stateByThreadId.get(threadId) ?? EMPTY_STATE;
}

function setThreadSubagents(threadId: string, next: ThreadSubagentState): void {
  stateByThreadId.set(threadId, next);
  listenersByThreadId.get(threadId)?.forEach((listener) => listener());
}

function subscribeThreadSubagents(threadId: string, listener: () => void): () => void {
  let listeners = listenersByThreadId.get(threadId);
  if (!listeners) {
    listeners = new Set();
    listenersByThreadId.set(threadId, listeners);
  }
  listeners.add(listener);
  return () => {
    const current = listenersByThreadId.get(threadId);
    current?.delete(listener);
    if (current?.size === 0) listenersByThreadId.delete(threadId);
  };
}

const MESSAGE_KINDS = new Set<ThreadSubagentMessageKind>(['task', 'assistant', 'tool_call', 'tool_result', 'status', 'final', 'system']);

function normalizeMessage(item: NonNullable<ThreadSubagentApiTask['messages']>[number]): ThreadSubagentMessage | null {
  if (!item || typeof item.id !== 'string' || !item.id) return null;
  const rawKind = typeof item.kind === 'string' ? item.kind : 'system';
  const kind = MESSAGE_KINDS.has(rawKind as ThreadSubagentMessageKind)
    ? rawKind as ThreadSubagentMessageKind
    : 'system';
  return {
    id: item.id,
    sequence: typeof item.sequence === 'number' && Number.isFinite(item.sequence) ? item.sequence : null,
    kind,
    timestamp: typeof item.timestamp === 'string' ? item.timestamp : null,
    text: kind === 'system' && rawKind !== 'system'
      ? rawKind
      : typeof item.text === 'string' ? item.text : null,
    status: typeof item.status === 'string' ? item.status : null,
    toolName: typeof item.tool_name === 'string' ? item.tool_name : null,
    toolCallId: typeof item.tool_call_id === 'string' ? item.tool_call_id : null,
    input: typeof item.input === 'string' ? item.input : null,
    output: typeof item.output === 'string' ? item.output : null,
    redacted: item.redacted === true,
    truncated: item.truncated === true,
    legacy: false,
  };
}

export function normalizeThreadSubagentMessages(
  messages: ThreadSubagentApiTask['messages'],
): ThreadSubagentMessage[] {
  if (!Array.isArray(messages)) return [];
  const byId = new Map<string, { message: ThreadSubagentMessage; inputIndex: number }>();
  messages.forEach((item, inputIndex) => {
    const message = normalizeMessage(item);
    if (message) byId.set(message.id, { message, inputIndex });
  });
  return Array.from(byId.values())
    .sort((left, right) => {
      const leftSequence = left.message.sequence;
      const rightSequence = right.message.sequence;
      if (leftSequence != null || rightSequence != null) {
        if (leftSequence == null) return 1;
        if (rightSequence == null) return -1;
        if (leftSequence !== rightSequence) return leftSequence - rightSequence;
      }
      const leftTime = Date.parse(left.message.timestamp ?? '');
      const rightTime = Date.parse(right.message.timestamp ?? '');
      if (Number.isFinite(leftTime) || Number.isFinite(rightTime)) {
        if (!Number.isFinite(leftTime)) return 1;
        if (!Number.isFinite(rightTime)) return -1;
        if (leftTime !== rightTime) return leftTime - rightTime;
      }
      const idOrder = left.message.id.localeCompare(right.message.id);
      return idOrder || left.inputIndex - right.inputIndex;
    })
    .map(({ message }) => message);
}

function buildLegacyMessages(task: ThreadSubagentApiTask): ThreadSubagentMessage[] {
  const messages: ThreadSubagentMessage[] = [];
  for (const [index, item] of (task.activity ?? []).entries()) {
    if (!item || typeof item.id !== 'string') continue;
    if (item.kind === 'message' && typeof item.text === 'string' && item.text === task.summary) continue;
    messages.push({
      id: `legacy-${item.id}`,
      sequence: index + 1,
      kind: item.kind === 'tool' ? (item.status === 'started' ? 'tool_call' : 'tool_result') : 'assistant',
      timestamp: typeof item.timestamp === 'string' ? item.timestamp : null,
      text: item.kind === 'message' && typeof item.text === 'string' ? item.text : null,
      status: item.status,
      toolName: typeof item.tool_name === 'string' ? item.tool_name : null,
      toolCallId: null,
      input: null,
      output: null,
      redacted: false,
      truncated: false,
      legacy: true,
    });
  }
  if (typeof task.summary === 'string' && task.summary) {
    messages.push({
      id: `legacy-summary-${task.task_id}`,
      sequence: messages.length + 1,
      kind: task.status === 'completed' ? 'final' : 'assistant',
      timestamp: typeof task.finished_at === 'string' ? task.finished_at : null,
      text: task.summary,
      status: task.status,
      toolName: null,
      toolCallId: null,
      input: null,
      output: null,
      redacted: false,
      truncated: false,
      legacy: true,
    });
  }
  return messages;
}

export function normalizeThreadSubagentTask(task: ThreadSubagentApiTask): ThreadSubagentTask | null {
  if (!task || typeof task.task_id !== 'string' || !task.task_id) return null;
  if (!['running', 'completed', 'failed', 'cancelled'].includes(task.status)) return null;
  const messages = normalizeThreadSubagentMessages(task.messages);
  const normalizedMessages = messages.length > 0 ? messages : buildLegacyMessages(task);
  return {
    taskId: task.task_id,
    agentId: task.agent_id || task.task_id,
    agentType: task.agent_type || 'Agent',
    description: task.description || task.agent_type || 'Subagent task',
    summary: typeof task.summary === 'string' ? task.summary : null,
    status: task.status,
    toolCallId: typeof task.tool_call_id === 'string' ? task.tool_call_id : null,
    spawnDepth: typeof task.spawn_depth === 'number' ? task.spawn_depth : null,
    startedAt: typeof task.started_at === 'string' ? task.started_at : null,
    finishedAt: typeof task.finished_at === 'string' ? task.finished_at : null,
    durationMs: typeof task.duration_ms === 'number' ? task.duration_ms : null,
    error: typeof task.error === 'string' ? task.error : null,
    activity: Array.isArray(task.activity)
      ? task.activity.flatMap((item) => {
          if (!item || typeof item.id !== 'string') return [];
          if (!['message', 'tool'].includes(item.kind)) return [];
          if (!['started', 'completed', 'failed'].includes(item.status)) return [];
          return [{
            id: item.id,
            kind: item.kind,
            status: item.status,
            timestamp: typeof item.timestamp === 'string' ? item.timestamp : null,
            text: typeof item.text === 'string' ? item.text : null,
            toolName: typeof item.tool_name === 'string' ? item.tool_name : null,
          }];
        })
      : [],
    messages: normalizedMessages,
    messageCount: typeof task.message_count === 'number' ? task.message_count : normalizedMessages.length,
    messagesTruncated: task.messages_truncated === true,
    projectionVersion: typeof task.projection_version === 'number' ? task.projection_version : 1,
  };
}

export function useThreadSubagents(threadId: string | null | undefined): ThreadSubagentState {
  const key = threadId ?? '';
  return useSyncExternalStore(
    (listener) => subscribeThreadSubagents(key, listener),
    () => getThreadSubagents(key),
  );
}

/** Refresh a thread snapshot. Concurrent callers share one request. */
export function hydrateThreadSubagents(threadId: string): Promise<void> {
  if (!threadId) return Promise.resolve();
  const existing = inFlightByThreadId.get(threadId);
  if (existing) return existing;

  const previous = getThreadSubagents(threadId);
  if (!previous.exists && !previous.loading) {
    setThreadSubagents(threadId, { ...previous, loading: true, error: null });
  }

  const request = (async () => {
    try {
      const response = await fetch(
        apiUrl(`/api/claude-agent/threads/${encodeURIComponent(threadId)}/subagents`),
        { headers: { Authorization: `Bearer ${getAuthToken()}` } },
      );
      if (!response.ok) throw new Error(`Subagent tasks unavailable (${response.status})`);
      const payload = (await response.json()) as ThreadSubagentApiResponse;
      const tasks = Array.isArray(payload.tasks)
        ? payload.tasks.map(normalizeThreadSubagentTask).filter((task): task is ThreadSubagentTask => task !== null)
        : [];
      const counts = payload.counts && typeof payload.counts === 'object'
        ? {
            running: Number(payload.counts.running) || 0,
            completed: Number(payload.counts.completed) || 0,
            ended: Number(payload.counts.ended) || 0,
            total: Number(payload.counts.total) || tasks.length,
          }
        : {
            running: tasks.filter((task) => task.status === 'running').length,
            completed: tasks.filter((task) => task.status === 'completed').length,
            ended: tasks.filter((task) => task.status === 'failed' || task.status === 'cancelled').length,
            total: tasks.length,
          };
      setThreadSubagents(threadId, {
        exists: payload.exists === true && tasks.length > 0,
        tasks,
        counts,
        updatedAt: typeof payload.updated_at === 'string' ? payload.updated_at : null,
        loading: false,
        error: null,
      });
    } catch (error) {
      const current = getThreadSubagents(threadId);
      setThreadSubagents(threadId, {
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : 'Subagent tasks unavailable',
      });
    } finally {
      inFlightByThreadId.delete(threadId);
    }
  })();
  inFlightByThreadId.set(threadId, request);
  return request;
}
