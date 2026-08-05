// [Input] Actor-scoped run ID, Episode artifact REST surface, and optional output hints.
// [Output] Strict ETag fetch seam, last-good reducer, and polling/reentry hook.
// [Pos] Story Workspace Episode artifact query boundary (U5)
// [Sync] 2026-08-06: REST is authoritative; output events only invalidate the query.

import { useCallback, useEffect, useReducer, useRef } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import {
  storyWorkspaceParseEpisodeArtifactSurface,
  type StoryWorkspaceEpisodeArtifactSurface,
} from './contracts';

const STORY_WORKSPACE_EPISODE_OUTPUT_EVENT = 'ink:story-workspace-output';
const STORY_WORKSPACE_EPISODE_MIN_POLL_INTERVAL_MS = 5000;

function storyWorkspaceEpisodeIsRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export class StoryWorkspaceEpisodeArtifactsHttpError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`Episode artifact request failed (${status}).`);
    this.name = 'StoryWorkspaceEpisodeArtifactsHttpError';
    this.status = status;
  }
}

export class StoryWorkspaceEpisodeArtifactsContractError extends Error {
  constructor(message = 'Invalid Episode artifact surface.') {
    super(message);
    this.name = 'StoryWorkspaceEpisodeArtifactsContractError';
  }
}

export function storyWorkspaceEpisodeArtifactsEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/episode-artifacts`;
}

export function storyWorkspaceEpisodeArtifactsPollInterval(requested?: number): number {
  return Math.max(requested ?? STORY_WORKSPACE_EPISODE_MIN_POLL_INTERVAL_MS, STORY_WORKSPACE_EPISODE_MIN_POLL_INTERVAL_MS);
}

/** Event content is ignored; only an exact run identity may invalidate REST. */
export function storyWorkspaceShouldInvalidateEpisodeArtifacts(
  event: unknown,
  runId: string,
): boolean {
  if (!storyWorkspaceEpisodeIsRecord(event) || event.type !== 'story-workspace-output') {
    return false;
  }
  const eventRunId = event.runId ?? event.storyWorkspaceRunId;
  return typeof eventRunId === 'string' && eventRunId === runId;
}

export function storyWorkspaceIsEpisodeArtifactsAbort(reason: unknown): boolean {
  return reason instanceof DOMException
    ? reason.name === 'AbortError'
    : storyWorkspaceEpisodeIsRecord(reason) && reason.name === 'AbortError';
}

export interface StoryWorkspaceEpisodeArtifactsFetchOptions {
  readonly fetchImpl?: typeof fetch;
  readonly token?: string | null;
  readonly etag?: string | null;
  readonly expectedRunId?: string;
  readonly signal?: AbortSignal;
}

export type StoryWorkspaceEpisodeArtifactsFetchResult =
  | { readonly kind: 'surface'; readonly data: StoryWorkspaceEpisodeArtifactSurface }
  | { readonly kind: 'not-modified'; readonly etag: string };

function storyWorkspaceEpisodeQuotedEtag(etag: string): string {
  return `"${etag}"`;
}

/** Fetch one authoritative snapshot without ever consuming an error response body. */
export async function storyWorkspaceFetchEpisodeArtifacts(
  endpoint: string,
  options: StoryWorkspaceEpisodeArtifactsFetchOptions = {},
): Promise<StoryWorkspaceEpisodeArtifactsFetchResult> {
  const headers = new Headers({ Accept: 'application/json' });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);
  if (options.etag) headers.set('If-None-Match', storyWorkspaceEpisodeQuotedEtag(options.etag));
  const response = await (options.fetchImpl ?? fetch)(endpoint, {
    credentials: 'include',
    headers,
    signal: options.signal ?? null,
  });
  if (response.status === 304) {
    if (!options.etag) {
      throw new StoryWorkspaceEpisodeArtifactsContractError(
        'Episode artifact 304 response has no cached ETag.',
      );
    }
    const responseEtag = response.headers.get('ETag');
    if (responseEtag !== null && responseEtag !== storyWorkspaceEpisodeQuotedEtag(options.etag)) {
      throw new StoryWorkspaceEpisodeArtifactsContractError(
        'Episode artifact 304 response has an inconsistent ETag.',
      );
    }
    return { kind: 'not-modified', etag: options.etag };
  }
  if (!response.ok) throw new StoryWorkspaceEpisodeArtifactsHttpError(response.status);
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new StoryWorkspaceEpisodeArtifactsContractError(
      'Episode artifact response is not valid JSON.',
    );
  }
  let data: StoryWorkspaceEpisodeArtifactSurface;
  try {
    data = storyWorkspaceParseEpisodeArtifactSurface(payload);
  } catch (reason) {
    throw new StoryWorkspaceEpisodeArtifactsContractError(
      reason instanceof Error ? reason.message : undefined,
    );
  }
  if (options.expectedRunId !== undefined && data.runId !== options.expectedRunId) {
    throw new StoryWorkspaceEpisodeArtifactsContractError(
      'Episode artifact response does not match the requested run.',
    );
  }
  const responseEtag = response.headers.get('ETag');
  if (data.bindingAvailability === 'bound') {
    if (data.etag === null || responseEtag !== storyWorkspaceEpisodeQuotedEtag(data.etag)) {
      throw new StoryWorkspaceEpisodeArtifactsContractError(
        'Episode artifact response header ETag does not match manifestRevision.',
      );
    }
  } else if (responseEtag !== null) {
    throw new StoryWorkspaceEpisodeArtifactsContractError(
      'Unbound Episode artifact response must not expose an ETag.',
    );
  }
  return { kind: 'surface', data };
}

export interface StoryWorkspaceEpisodeArtifactsDiagnostic {
  readonly kind: 'invalid_payload';
  readonly message: string;
}

export interface StoryWorkspaceEpisodeArtifactsFetchState {
  readonly runId: string | null;
  readonly data: StoryWorkspaceEpisodeArtifactSurface | null;
  readonly diagnostic: StoryWorkspaceEpisodeArtifactsDiagnostic | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly generation: number;
}

export type StoryWorkspaceEpisodeArtifactsFetchAction =
  | { readonly type: 'reset'; readonly runId: string | null }
  | { readonly type: 'start'; readonly runId: string; readonly generation: number }
  | { readonly type: 'success'; readonly runId: string; readonly generation: number; readonly data: StoryWorkspaceEpisodeArtifactSurface }
  | { readonly type: 'not-modified'; readonly runId: string; readonly generation: number }
  | { readonly type: 'invalid'; readonly runId: string; readonly generation: number; readonly diagnostic: StoryWorkspaceEpisodeArtifactsDiagnostic }
  | { readonly type: 'error'; readonly runId: string; readonly generation: number; readonly error: Error };

export function storyWorkspaceEpisodeArtifactsInitialState(
  runId: string | null = null,
): StoryWorkspaceEpisodeArtifactsFetchState {
  return {
    runId,
    data: null,
    diagnostic: null,
    error: null,
    isLoading: false,
    generation: 0,
  };
}

/** Pure stale-response and last-good gate; reset is the only cross-run transition. */
export function storyWorkspaceReduceEpisodeArtifactsFetch(
  state: StoryWorkspaceEpisodeArtifactsFetchState,
  action: StoryWorkspaceEpisodeArtifactsFetchAction,
): StoryWorkspaceEpisodeArtifactsFetchState {
  if (action.type === 'reset') return storyWorkspaceEpisodeArtifactsInitialState(action.runId);
  if (action.runId !== state.runId || action.generation < state.generation) return state;
  if (action.type === 'start') {
    return { ...state, error: null, isLoading: true, generation: action.generation };
  }
  if (action.type === 'success') {
    return {
      runId: state.runId,
      data: action.data,
      diagnostic: null,
      error: null,
      isLoading: false,
      generation: action.generation,
    };
  }
  if (action.type === 'not-modified') {
    return {
      ...state,
      diagnostic: null,
      error: null,
      isLoading: false,
      generation: action.generation,
    };
  }
  if (action.type === 'invalid') {
    return {
      ...state,
      diagnostic: action.diagnostic,
      error: null,
      isLoading: false,
      generation: action.generation,
    };
  }
  return {
    ...state,
    error: action.error,
    isLoading: false,
    generation: action.generation,
  };
}

export interface StoryWorkspaceEpisodeArtifactsUseOptions {
  readonly fetchImpl?: typeof fetch;
  readonly token?: string | null;
  readonly pollIntervalMs?: number;
}

export interface StoryWorkspaceEpisodeArtifactsState {
  readonly data: StoryWorkspaceEpisodeArtifactSurface | null;
  readonly diagnostic: StoryWorkspaceEpisodeArtifactsDiagnostic | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly isShowingLastGood: boolean;
  readonly refresh: () => void;
}

/**
 * Reenter and poll one run's server-bound Episode. ETags and last-good data live
 * only for this mounted hook instance and are cleared when the run ID changes.
 */
export function useStoryWorkspaceEpisodeArtifacts(
  runId: string | null | undefined,
  options: StoryWorkspaceEpisodeArtifactsUseOptions = {},
): StoryWorkspaceEpisodeArtifactsState {
  const normalizedRunId = runId ?? null;
  const [state, dispatch] = useReducer(
    storyWorkspaceReduceEpisodeArtifactsFetch,
    normalizedRunId,
    storyWorkspaceEpisodeArtifactsInitialState,
  );
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const etagCache = useRef<{ runId: string | null; etag: string | null }>({
    runId: normalizedRunId,
    etag: null,
  });

  const refresh = useCallback(() => {
    if (!normalizedRunId) return;
    if (etagCache.current.runId !== normalizedRunId) {
      etagCache.current = { runId: normalizedRunId, etag: null };
    }
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    generation.current += 1;
    const nextGeneration = generation.current;
    dispatch({ type: 'start', runId: normalizedRunId, generation: nextGeneration });
    void storyWorkspaceFetchEpisodeArtifacts(
      apiUrl(storyWorkspaceEpisodeArtifactsEndpoint(normalizedRunId)),
      {
        fetchImpl: options.fetchImpl,
        token: options.token === undefined ? getAuthToken() : options.token,
        etag: etagCache.current.etag,
        expectedRunId: normalizedRunId,
        signal: nextController.signal,
      },
    ).then((result) => {
      if (nextController.signal.aborted) return;
      if (result.kind === 'not-modified') {
        dispatch({ type: 'not-modified', runId: normalizedRunId, generation: nextGeneration });
        return;
      }
      etagCache.current = { runId: normalizedRunId, etag: result.data.etag };
      dispatch({
        type: 'success',
        runId: normalizedRunId,
        generation: nextGeneration,
        data: result.data,
      });
    }).catch((reason: unknown) => {
      if (nextController.signal.aborted || storyWorkspaceIsEpisodeArtifactsAbort(reason)) return;
      if (reason instanceof StoryWorkspaceEpisodeArtifactsContractError) {
        dispatch({
          type: 'invalid',
          runId: normalizedRunId,
          generation: nextGeneration,
          diagnostic: { kind: 'invalid_payload', message: reason.message },
        });
        return;
      }
      dispatch({
        type: 'error',
        runId: normalizedRunId,
        generation: nextGeneration,
        error: reason instanceof Error
          ? reason
          : new Error('Episode artifact request failed.'),
      });
    });
  }, [normalizedRunId, options.fetchImpl, options.token]);

  useEffect(() => {
    controller.current?.abort();
    if (etagCache.current.runId !== normalizedRunId) {
      generation.current += 1;
      etagCache.current = { runId: normalizedRunId, etag: null };
      dispatch({ type: 'reset', runId: normalizedRunId });
    }
    if (normalizedRunId) refresh();
    return () => controller.current?.abort();
  }, [normalizedRunId, refresh]);

  useEffect(() => {
    if (!normalizedRunId) return;
    const timer = window.setInterval(
      refresh,
      storyWorkspaceEpisodeArtifactsPollInterval(options.pollIntervalMs),
    );
    return () => window.clearInterval(timer);
  }, [normalizedRunId, options.pollIntervalMs, refresh]);

  useEffect(() => {
    if (!normalizedRunId) return;
    const handleOutput = (event: Event) => {
      if (storyWorkspaceShouldInvalidateEpisodeArtifacts(
        (event as CustomEvent<unknown>).detail,
        normalizedRunId,
      )) refresh();
    };
    window.addEventListener(STORY_WORKSPACE_EPISODE_OUTPUT_EVENT, handleOutput);
    return () => window.removeEventListener(STORY_WORKSPACE_EPISODE_OUTPUT_EVENT, handleOutput);
  }, [normalizedRunId, refresh]);

  return {
    data: state.runId === normalizedRunId ? state.data : null,
    diagnostic: state.runId === normalizedRunId ? state.diagnostic : null,
    error: state.runId === normalizedRunId ? state.error : null,
    isLoading: state.runId === normalizedRunId && state.isLoading,
    isShowingLastGood: state.runId === normalizedRunId
      && state.data !== null
      && state.diagnostic !== null,
    refresh,
  };
}
