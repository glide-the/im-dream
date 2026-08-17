// [Input] Local AI SDK status plus authoritative thread/reconnect state.
// [Output] Shared main-turn Stop visibility and strict stop-response decoding.
// [Pos] Chat/Dream lifecycle primitive; transcript/subagent data is intentionally absent.

export function chatMainTurnCanStop(
  localStatus: string,
  runtimeRunning: boolean,
  reconnecting: boolean,
): boolean {
  return localStatus === 'submitted'
    || localStatus === 'streaming'
    || runtimeRunning
    || reconnecting;
}

export function parseThreadStopResponse(payload: unknown): { stopRequested: boolean } | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null;
  const value = payload as Record<string, unknown>;
  if (value.ok !== true || typeof value.stop_requested !== 'boolean') return null;
  return { stopRequested: value.stop_requested };
}

/** Local readers may be aborted only after an explicit stop acknowledgement or
 * a separate authoritative idle observation. */
export function chatStopMayAbortLocalReaders(
  stopRequested: boolean | null,
  authoritativeRunning: boolean | null,
): boolean {
  return stopRequested === true || authoritativeRunning === false;
}

export function toolConfirmationKeyboardDecision(
  kind: string,
  event: { readonly key: string; readonly metaKey: boolean; readonly ctrlKey: boolean },
): 'approve' | 'reject' | 'consume' | null {
  if (event.key === 'Escape') return 'reject';
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
    return kind === 'reject-only' ? 'consume' : 'approve';
  }
  return null;
}

/** A reconnect nonce belongs only to the thread hydration that observed a
 * running runtime; an idle thread must never inherit a prior thread's nonce. */
export function chatReconnectNonceForHydratedThread(
  runtimeRunning: boolean,
  reconnectStreamNonce: number,
): number {
  return runtimeRunning ? reconnectStreamNonce : 0;
}

export interface ChatReconnectCounters {
  readonly external: number;
  readonly retry: number;
}

/** Claim only monotonic advances from the two independent reconnect sources.
 * Keeping separate counters prevents an external nonce dropping to zero from
 * making an already-consumed retry look like a new local reconnect request. */
export function claimChatReconnect(
  runtimeRunning: boolean,
  externalNonce: number,
  retryNonce: number,
  lastClaim: ChatReconnectCounters,
): ChatReconnectCounters | null {
  if (!runtimeRunning) return null;
  const external = Math.max(0, externalNonce);
  const retry = Math.max(0, retryNonce);
  if (external <= lastClaim.external && retry <= lastClaim.retry) return null;
  return {
    external: Math.max(lastClaim.external, external),
    retry: Math.max(lastClaim.retry, retry),
  };
}
