// [Input] One complete StoryWorkspaceDreamConfirmationCommand.
// [Output] Run-scoped 202 transport seam and single in-flight React hook.
// [Pos] story-workspace hooks node - Dream's only confirmation action (Task 3 F3)
// [Sync] 2026-08-04: initial implementation; no reject/retry/second-confirm path.

import { useCallback, useEffect, useRef, useState } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import type {
  StoryWorkspaceDreamConfirmationAccepted,
  StoryWorkspaceDreamConfirmationCommand,
} from './contracts';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requiredString(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error(`Dream confirmation response has invalid ${field}.`);
  }
  return value;
}

export function dreamConfirmationEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/dream-confirmation`;
}

export function newStoryWorkspaceDreamConfirmationIdempotencyKey(
  uuidFactory: () => string = () => {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  },
): string {
  return `swc_${uuidFactory()}`;
}

export function parseStoryWorkspaceDreamConfirmationAccepted(
  value: unknown,
): StoryWorkspaceDreamConfirmationAccepted {
  if (!isRecord(value)) throw new Error('Dream confirmation response must be an object.');
  if (
    value.status !== 'accepted'
    || typeof value.replayed !== 'boolean'
    || typeof value.dispatched !== 'boolean'
  ) {
    throw new Error('Dream confirmation response has an invalid status.');
  }
  return {
    messageId: requiredString(value.messageId, 'messageId'),
    storyWorkspaceRunId: requiredString(value.storyWorkspaceRunId, 'storyWorkspaceRunId'),
    threadId: requiredString(value.threadId, 'threadId'),
    status: 'accepted',
    replayed: value.replayed,
    dispatched: value.dispatched,
    requestId: requiredString(value.requestId, 'requestId'),
  };
}

export interface SubmitStoryWorkspaceDreamConfirmationOptions {
  fetchImpl?: typeof fetch;
  token?: string | null;
  signal?: AbortSignal;
  /** Full runtime URL override; the pure transport otherwise uses the relative path. */
  endpoint?: string;
}

/** Submit Dream's one confirmation; URL/body run drift is rejected client-side. */
export async function submitStoryWorkspaceDreamConfirmation(
  runId: string,
  command: StoryWorkspaceDreamConfirmationCommand,
  options: SubmitStoryWorkspaceDreamConfirmationOptions = {},
): Promise<StoryWorkspaceDreamConfirmationAccepted> {
  if (command.storyWorkspaceRunId !== runId) {
    throw new Error('Dream confirmation run does not match the current page.');
  }
  const headers = new Headers({
    Accept: 'application/json',
    'Content-Type': 'application/json',
  });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);
  const response = await (options.fetchImpl ?? fetch)(
    options.endpoint ?? dreamConfirmationEndpoint(runId),
    {
      method: 'POST',
      credentials: 'include',
      headers,
      body: JSON.stringify(command),
      signal: options.signal ?? null,
    },
  );
  if (response.status !== 202) {
    throw new Error(`Dream confirmation was not accepted (${response.status}).`);
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Dream confirmation response is not valid JSON.');
  }
  const accepted = parseStoryWorkspaceDreamConfirmationAccepted(payload);
  if (accepted.storyWorkspaceRunId !== runId || accepted.threadId !== command.threadId) {
    throw new Error('Dream confirmation response does not match the submitted command.');
  }
  return accepted;
}

export interface StoryWorkspaceDreamConfirmationState {
  status: 'idle' | 'confirming' | 'accepted';
  accepted: StoryWorkspaceDreamConfirmationAccepted | null;
  error: Error | null;
  submit: (
    command: StoryWorkspaceDreamConfirmationCommand,
  ) => Promise<StoryWorkspaceDreamConfirmationAccepted>;
}

/** Prevent duplicate clicks by sharing the current in-flight Promise. */
export function useStoryWorkspaceDreamConfirmation(
  runId: string,
  options: SubmitStoryWorkspaceDreamConfirmationOptions = {},
): StoryWorkspaceDreamConfirmationState {
  const [status, setStatus] = useState<'idle' | 'confirming' | 'accepted'>('idle');
  const [accepted, setAccepted] = useState<StoryWorkspaceDreamConfirmationAccepted | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const inFlight = useRef<Promise<StoryWorkspaceDreamConfirmationAccepted> | null>(null);

  useEffect(() => {
    inFlight.current = null;
    setStatus('idle');
    setAccepted(null);
    setError(null);
  }, [runId]);

  const submit = useCallback((command: StoryWorkspaceDreamConfirmationCommand) => {
    if (inFlight.current) return inFlight.current;
    setStatus('confirming');
    setError(null);
    const pending = submitStoryWorkspaceDreamConfirmation(runId, command, {
      fetchImpl: options.fetchImpl,
      token: options.token === undefined ? getAuthToken() : options.token,
      signal: options.signal,
      endpoint: apiUrl(dreamConfirmationEndpoint(runId)),
    }).then((result) => {
      setAccepted(result);
      setStatus('accepted');
      return result;
    }).catch((reason: unknown) => {
      const nextError = reason instanceof Error
        ? reason
        : new Error('Dream confirmation was not accepted.');
      setError(nextError);
      setStatus('idle');
      throw nextError;
    }).finally(() => {
      inFlight.current = null;
    });
    inFlight.current = pending;
    return pending;
  }, [options.fetchImpl, options.signal, options.token, runId]);

  return { status, accepted, error, submit };
}
