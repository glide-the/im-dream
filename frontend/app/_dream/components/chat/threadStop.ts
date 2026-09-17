// [Input] Current Thread identity, Browser Cookie/CSRF session and same-origin Claude Agent Stop endpoint.
// [Output] One bounded Stop mutation plus a strict, current-Thread response DTO.
// [Pos] Chat main-turn control transport; independent from React component mount/unmount lifecycle.
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
