// [Input] Sidebar guidance inputs, thread chat_message rows, and the Task 3
//         guidance endpoint.
// [Output] Guidance seams for the execution page sidebar (Task 5, design_004
//          §5.3): idempotent payload construction (client idempotency key →
//          message id guide_<key>), the POST transport seam, submit-result
//          presentation including the dispatched:false "已记录待拾取" state
//          (Task 3 review leftover R2), guidance history extraction
//          (thread_id + metadata.kind reverse lookup), and the history hook.
// [Pos] story-workspace hooks node - guidance seam (Task 5)
// [Sync] 2026-08-04: initial implementation. History reuses the existing
//                    GET /api/claude-agent/threads/{thread_id}/messages read
//                    (Task 3 record: no dedicated GET endpoint); extraction
//                    keeps guidance rows — never the Chat-view filter, which
//                    removes them.

import { useCallback, useEffect, useState } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import { isStoryWorkspaceGuidanceMetadata } from '../../lib/story-workspace-guidance';
import type {
  StoryWorkspaceGuidanceAccepted,
  StoryWorkspaceGuidanceCommandPayload,
  StoryWorkspaceGuidanceHistoryEntry,
  StoryWorkspaceGuidanceKind,
} from './contracts';

/** Path (without API base) of the Task 3 guidance endpoint. */
export function storyWorkspaceGuidanceEndpoint(runId: string): string {
  return `/api/story-workspace/runs/${encodeURIComponent(runId)}/guidance`;
}

/**
 * Client idempotency key for one guidance submission (≤255 contract bound).
 * Each logical submission gets a fresh key; UI-level double submits reuse the
 * in-flight key so the server-side replay path (202 replayed:true) applies.
 */
export function newStoryWorkspaceGuidanceIdempotencyKey(): string {
  const uuid = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  return `swg_${uuid}`;
}

export interface StoryWorkspaceGuidanceSubmitInput {
  kind: StoryWorkspaceGuidanceKind;
  /** Authenticated user id as a string (server enforces equality, else 403). */
  actor: string;
  /** free-text: required non-blank; retry-step: optional note. */
  text?: string;
  /** retry-step: required. */
  stepId?: string;
  /** Defaults to a freshly generated key. */
  idempotencyKey?: string;
}

/**
 * Build the endpoint payload, mirroring the server contract validators:
 * free-text requires non-blank text, retry-step requires a step id, actor is
 * mandatory. Returns null for invalid commands so the sidebar never fires a
 * request the server would reject with 422.
 */
export function buildStoryWorkspaceGuidancePayload(
  input: StoryWorkspaceGuidanceSubmitInput,
): StoryWorkspaceGuidanceCommandPayload | null {
  const actor = input.actor.trim();
  if (!actor) return null;

  const text = input.text?.trim();
  if (input.kind === 'free-text' && !text) return null;

  let stepId: string | undefined;
  if (input.kind === 'retry-step') {
    stepId = input.stepId?.trim();
    if (!stepId) return null;
  }

  return {
    kind: input.kind,
    ...(text ? { text } : {}),
    ...(stepId ? { step_id: stepId } : {}),
    idempotency_key: input.idempotencyKey ?? newStoryWorkspaceGuidanceIdempotencyKey(),
    actor,
  };
}

/**
 * Human-facing result line for one accepted guidance command. The
 * dispatched:false ("已记录，待执行 Agent 拾取") branch is a first-class
 * state — the thread had an in-flight turn and the persisted guidance waits
 * for the next one (Task 3 review leftover R2).
 */
export function describeStoryWorkspaceGuidanceResult(
  result: StoryWorkspaceGuidanceAccepted,
): string {
  if (result.replayed) {
    return '该指导已提交过（幂等去重），未重复发送。';
  }
  return result.dispatched
    ? '指导已发送给执行 Agent。'
    : '指导已记录，待执行 Agent 拾取（当前有进行中的回合）。';
}

/**
 * Reverse-look guidance history from thread chat_message rows: keep only
 * rows whose metadata marks a guidance command (DEC-032) and map the audit
 * fields. Order is preserved (chronological as returned by the endpoint).
 * Malformed rows (non-object metadata, missing id) are skipped.
 */
export function extractStoryWorkspaceGuidanceHistory(
  messages: readonly { id?: unknown; created_at?: unknown; metadata?: unknown }[],
): StoryWorkspaceGuidanceHistoryEntry[] {
  const entries: StoryWorkspaceGuidanceHistoryEntry[] = [];
  for (const message of messages) {
    if (!isStoryWorkspaceGuidanceMetadata(message.metadata)) continue;
    if (typeof message.id !== 'string' || !message.id) continue;
    const metadata = message.metadata as Record<string, unknown>;
    entries.push({
      messageId: message.id,
      createdAt: typeof message.created_at === 'string' ? message.created_at : null,
      commandKind: typeof metadata.command_kind === 'string' ? metadata.command_kind : null,
      stepId: typeof metadata.step_id === 'string' ? metadata.step_id : null,
      textSummary: typeof metadata.text_summary === 'string' ? metadata.text_summary : null,
      requestId: typeof metadata.request_id === 'string' ? metadata.request_id : null,
      idempotencyKey: typeof metadata.idempotency_key === 'string' ? metadata.idempotency_key : null,
    });
  }
  return entries;
}

export type StoryWorkspaceGuidanceSubmitOutcome =
  | { ok: true; result: StoryWorkspaceGuidanceAccepted }
  | { ok: false; status: number; errorCode: string | null };

export interface SubmitStoryWorkspaceGuidanceOptions {
  fetchImpl?: typeof fetch;
  token?: string | null;
}

function readErrorCode(body: unknown): string | null {
  if (typeof body !== 'object' || body === null) return null;
  const candidate = body as Record<string, unknown>;
  if (typeof candidate.error_code === 'string') return candidate.error_code;
  const nested = candidate.error;
  if (typeof nested === 'object' && nested !== null) {
    const code = (nested as Record<string, unknown>).code;
    if (typeof code === 'string') return code;
  }
  return null;
}

/**
 * POST one idempotent guidance command to the Task 3 endpoint. `endpoint` is
 * the full URL (callers apply `apiUrl()` at the runtime edge — the seam stays
 * node-testable, Task 2 precedent). Transport failures degrade to
 * `{ok:false, status:0}`; HTTP failures carry the server error code
 * (WORKFLOW_RUN_NOT_GUIDABLE / IDEMPOTENCY_CONFLICT / …) so the sidebar can
 * render actionable states.
 */
export async function submitStoryWorkspaceGuidance(
  endpoint: string,
  payload: StoryWorkspaceGuidanceCommandPayload,
  options: SubmitStoryWorkspaceGuidanceOptions = {},
): Promise<StoryWorkspaceGuidanceSubmitOutcome> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const headers = new Headers({
    Accept: 'application/json',
    'Content-Type': 'application/json',
  });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);

  let response: Response;
  try {
    response = await fetchImpl(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers,
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, status: 0, errorCode: null };
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // An unstructured server response never reaches the UI verbatim.
  }

  if (!response.ok) {
    return { ok: false, status: response.status, errorCode: readErrorCode(body) };
  }
  return { ok: true, result: body as StoryWorkspaceGuidanceAccepted };
}

/* --------------------------------------------------------------------------
 * Guidance history read (§5.3 指导历史) — reuses the existing thread messages
 * endpoint; no dedicated GET endpoint exists (Task 3 record).
 * ------------------------------------------------------------------------ */

export function storyWorkspaceGuidanceHistoryEndpoint(threadId: string): string {
  return `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`;
}

export interface FetchStoryWorkspaceGuidanceHistoryOptions {
  fetchImpl?: typeof fetch;
  token?: string | null;
  signal?: AbortSignal;
}

/**
 * Fetch and reverse-look the guidance history of a run's source chat thread.
 * `endpoint` is the full URL (callers apply `apiUrl()` at the runtime edge).
 * Any transport/HTTP/JSON failure degrades to an empty list — the history
 * panel must never break the execution page.
 */
export async function fetchStoryWorkspaceGuidanceHistory(
  endpoint: string,
  options: FetchStoryWorkspaceGuidanceHistoryOptions = {},
): Promise<StoryWorkspaceGuidanceHistoryEntry[]> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const headers = new Headers({ Accept: 'application/json' });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);

  let response: Response;
  try {
    response = await fetchImpl(endpoint, {
      credentials: 'include',
      headers,
      signal: options.signal ?? null,
    });
  } catch {
    return [];
  }
  if (!response.ok) return [];

  let payload: { messages?: { id?: unknown; created_at?: unknown; metadata?: unknown }[] };
  try {
    payload = await response.json() as typeof payload;
  } catch {
    return [];
  }
  return extractStoryWorkspaceGuidanceHistory(payload.messages ?? []);
}

export interface StoryWorkspaceGuidanceHistoryState {
  entries: StoryWorkspaceGuidanceHistoryEntry[];
  isLoading: boolean;
  refetch: () => void;
}

/**
 * Guidance history for the sidebar / run-records tab. `threadId` is the run's
 * source_voice_thread_id (the transport channel, DEC-032); without it the
 * hook stays inert. `refetch` re-reads after a submission.
 */
export function useStoryWorkspaceGuidanceHistory(
  threadId: string | null | undefined,
): StoryWorkspaceGuidanceHistoryState {
  const [entries, setEntries] = useState<StoryWorkspaceGuidanceHistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!threadId) {
      setEntries([]);
      setIsLoading(false);
      return;
    }
    const controller = new AbortController();
    setIsLoading(true);
    void fetchStoryWorkspaceGuidanceHistory(apiUrl(storyWorkspaceGuidanceHistoryEndpoint(threadId)), {
      token: getAuthToken(),
      signal: controller.signal,
    }).then((resolved) => {
      if (controller.signal.aborted) return;
      setEntries(resolved);
      setIsLoading(false);
    });
    return () => controller.abort();
  }, [threadId, nonce]);

  const refetch = useCallback(() => setNonce((value) => value + 1), []);

  return { entries, isLoading, refetch };
}
