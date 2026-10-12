// [Input] Current Thread identity, Browser Cookie/CSRF session and same-origin Claude Agent Stop endpoint.
// [Output] Bounded Stop requests and strict current-Thread receipts, retaining the original submission stop intent.
// [Pos] Chat main-turn control transport; independent from React component mount/unmount lifecycle.
// [Sync] 2026-10-12: bind Stop to the original pending POST across mounts; pre-admission idle and unknown cannot unlock retry.
// [Sync] 2026-09-17: keep an accepted Stop request alive across ChatPanel remounts and validate the complete receipt.

import { z } from 'zod';
import { apiUrl } from '../../lib/apiBase';
import { browserRequestHeaders } from '../../lib/browserSession';

const DEFAULT_STOP_TIMEOUT_MS = 10_000;

const threadStopReceiptSchema = z.strictObject({
  ok: z.literal(true),
  thread_id: z.string().min(1).max(255),
  stop_requested: z.boolean(),
  running: z.boolean(),
  lifecycle: z.string().min(1).max(64),
});

export interface ThreadStopReceipt {
  readonly threadId: string;
  readonly stopRequested: boolean;
  readonly running: boolean;
  readonly lifecycle: string;
}

export class ThreadStopRequestError extends Error {
  readonly code: 'STOP_TRANSPORT_FAILED' | 'STOP_RESPONSE_INVALID';

  constructor(code: ThreadStopRequestError['code']) {
    super(code);
    this.name = 'ThreadStopRequestError';
    this.code = code;
  }
}

export async function requestClaudeThreadStop(
  threadId: string,
  transport: typeof fetch = fetch,
  timeoutMilliseconds = DEFAULT_STOP_TIMEOUT_MS,
): Promise<ThreadStopReceipt> {
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), timeoutMilliseconds);
  try {
    let response: Response;
    try {
      response = await transport(
        apiUrl(`/api/claude-agent/threads/${encodeURIComponent(threadId)}/stop`),
        {
          method: 'POST',
          credentials: 'include',
          cache: 'no-store',
          headers: { ...browserRequestHeaders() },
          signal: controller.signal,
          keepalive: true,
        },
      );
    } catch {
      throw new ThreadStopRequestError('STOP_TRANSPORT_FAILED');
    }
    if (!response.ok) throw new ThreadStopRequestError('STOP_TRANSPORT_FAILED');

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new ThreadStopRequestError('STOP_RESPONSE_INVALID');
    }
    const parsed = threadStopReceiptSchema.safeParse(payload);
    if (!parsed.success || parsed.data.thread_id !== threadId) {
      throw new ThreadStopRequestError('STOP_RESPONSE_INVALID');
    }
    return Object.freeze({
      threadId: parsed.data.thread_id,
      stopRequested: parsed.data.stop_requested,
      running: parsed.data.running,
      lifecycle: parsed.data.lifecycle,
    });
  } finally {
    globalThis.clearTimeout(timeout);
  }
}


// Submission ownership outlives a ChatPanel mount. Headers alone do not prove
// the lazy Factory has registered the task; only its production stream does.
export interface ClaudeThreadSubmission {
  readonly threadId: string;
  readonly messageId: string;
  phase: 'pending' | 'accepted' | 'rejected' | 'terminal' | 'unknown';
  stopPending: boolean;
  dispatched: boolean;
  stopPromise?: Promise<ThreadStopReceipt>;
  readonly readiness: Promise<void>;
  readonly resolveReadiness: () => void;
}
const submissions = new Map<string, ClaudeThreadSubmission>();
const submissionListeners = new Map<string, Set<() => void>>();
function notifySubmission(threadId: string) {
  submissionListeners.get(threadId)?.forEach((listener) => listener());
}
export function beginClaudeThreadSubmission(threadId: string, messageId: string): ClaudeThreadSubmission {
  if (submissions.get(threadId)?.stopPending) throw new ThreadStopRequestError('STOP_TRANSPORT_FAILED');
  let resolveReadiness!: () => void;
  const readiness = new Promise<void>((resolve) => { resolveReadiness = resolve; });
  const ticket: ClaudeThreadSubmission = {
    threadId, messageId, phase: 'pending', stopPending: false, dispatched: false, readiness, resolveReadiness,
  };
  submissions.set(threadId, ticket);
  notifySubmission(threadId);
  return ticket;
}
export function observeClaudeThreadSubmission(
  ticket: ClaudeThreadSubmission,
  phase: ClaudeThreadSubmission['phase'],
) {
  if (ticket.phase === 'terminal' || ticket.phase === 'rejected') return;
  ticket.phase = phase;
  if (phase !== 'pending') ticket.resolveReadiness();
  if ((phase === 'terminal' || phase === 'rejected') && !ticket.stopPromise) ticket.stopPending = false;
  notifySubmission(ticket.threadId);
}
export function claudeThreadStopPending(threadId: string): boolean {
  return submissions.get(threadId)?.stopPending === true;
}
export function subscribeClaudeThreadStop(threadId: string, listener: () => void): () => void {
  const listeners = submissionListeners.get(threadId) ?? new Set<() => void>();
  submissionListeners.set(threadId, listeners);
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
    if (!listeners.size) submissionListeners.delete(threadId);
  };
}

/** Keep the original POST alive when Stop overtakes its lazy admission. */
export async function requestClaudeSubmittedThreadStop(
  threadId: string,
  transport: typeof fetch = fetch,
): Promise<ThreadStopReceipt> {
  const ticket = submissions.get(threadId);
  if (!ticket) return requestClaudeThreadStop(threadId, transport);
  if (ticket.stopPromise) return ticket.stopPromise;
  if (ticket.phase === 'unknown' && ticket.stopPending) {
    // A background status poll cannot attribute a different task to this POST.
    throw new ThreadStopRequestError('STOP_TRANSPORT_FAILED');
  }
  ticket.stopPending = true;
  notifySubmission(threadId);
  const stopBeforeAdmission = ticket.phase === 'pending' || ticket.phase === 'unknown';
  const stopping = (async () => {
    let receipt = await requestClaudeThreadStop(threadId, transport);
    if (!receipt.stopRequested && stopBeforeAdmission) {
      if (ticket.phase === 'pending') await ticket.readiness;
      // An old intent can never target a subsequent POST.
      if (submissions.get(threadId) !== ticket) return receipt;
      if ((() => ticket.phase)() === 'accepted') receipt = await requestClaudeThreadStop(threadId, transport);
    }
    if (receipt.stopRequested || (receipt.running === false
      && (ticket.phase === 'accepted' || ticket.phase === 'rejected' || ticket.phase === 'terminal'))) {
      ticket.stopPending = false;
      notifySubmission(threadId);
      return receipt;
    }
    throw new ThreadStopRequestError('STOP_TRANSPORT_FAILED');
  })();
  ticket.stopPromise = stopping;
  try {
    return await stopping;
  } finally {
    if (ticket.stopPromise === stopping) {
      ticket.stopPromise = undefined;
      if (ticket.phase === 'terminal' || ticket.phase === 'rejected') ticket.stopPending = false;
      notifySubmission(threadId);
    }
  }
}
