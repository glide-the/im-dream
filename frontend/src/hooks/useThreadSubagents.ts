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

function normalizeTask(task: ThreadSubagentApiTask): ThreadSubagentTask | null {
  if (!task || typeof task.task_id !== 'string' || !task.task_id) return null;
  if (!['running', 'completed', 'failed', 'cancelled'].includes(task.status)) return null;
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
        ? payload.tasks.map(normalizeTask).filter((task): task is ThreadSubagentTask => task !== null)
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
