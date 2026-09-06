// [Input] Actor-scoped Run ID and the read-only Episode registry index endpoint.
// [Output] Strict ETag-aware Episode index state with Run-local polling and invalidation.
// [Pos] Story Workspace Episode index query boundary; it never selects or mutates an Episode.
// [Sync] 2026-09-02: add the default Sync-page Episode index data source.

import { useCallback, useEffect, useReducer, useRef } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import {
  storyWorkspaceParseEpisodeIndexSurface,
  type StoryWorkspaceEpisodeIndexSurface,
} from './contracts';
import {
  storyWorkspaceQuotedEtag,
  storyWorkspaceResponseMatchesEtag,
} from './httpEtag';
import {
  storyWorkspaceEpisodeArtifactsPollInterval,
  storyWorkspaceShouldInvalidateEpisodeArtifacts,
} from './useStoryWorkspaceEpisodeArtifacts';

const STORY_WORKSPACE_EPISODE_INDEX_POLL_INTERVAL_MS = 5000;

export class StoryWorkspaceEpisodeIndexHttpError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`Episode index request failed (${status}).`);
    this.name = 'StoryWorkspaceEpisodeIndexHttpError';
    this.status = status;
  }
}

export class StoryWorkspaceEpisodeIndexContractError extends Error {
  constructor() {
    super('Episode index data is unavailable.');
    this.name = 'StoryWorkspaceEpisodeIndexContractError';
  }
}

export function storyWorkspaceEpisodeIndexEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/episodes`;
}

export type StoryWorkspaceEpisodeIndexFetchResult =
  | { readonly kind: 'index'; readonly data: StoryWorkspaceEpisodeIndexSurface }
  | { readonly kind: 'not-modified'; readonly etag: string };

export async function storyWorkspaceFetchEpisodeIndex(
  endpoint: string,
  options: {
    readonly fetchImpl?: typeof fetch;
    readonly token?: string | null;
    readonly etag?: string | null;
    readonly expectedRunId?: string;
    readonly signal?: AbortSignal;
  } = {},
): Promise<StoryWorkspaceEpisodeIndexFetchResult> {
  const headers = new Headers({ Accept: 'application/json' });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);
  if (options.etag) headers.set('If-None-Match', storyWorkspaceQuotedEtag(options.etag));
  const response = await (options.fetchImpl ?? fetch)(endpoint, {
    credentials: 'include',
    headers,
    signal: options.signal ?? null,
  });
  if (response.status === 304) {
    if (
      !options.etag
      || !storyWorkspaceResponseMatchesEtag(response.headers.get('ETag'), options.etag)
    ) throw new StoryWorkspaceEpisodeIndexContractError();
    return { kind: 'not-modified', etag: options.etag };
  }
  if (!response.ok) throw new StoryWorkspaceEpisodeIndexHttpError(response.status);
  let data: StoryWorkspaceEpisodeIndexSurface;
  try {
    data = storyWorkspaceParseEpisodeIndexSurface(await response.json());
  } catch {
    throw new StoryWorkspaceEpisodeIndexContractError();
  }
  if (
    (options.expectedRunId !== undefined && data.runId !== options.expectedRunId)
    || !storyWorkspaceResponseMatchesEtag(response.headers.get('ETag'), data.etag)
  ) throw new StoryWorkspaceEpisodeIndexContractError();
  return { kind: 'index', data };
}

interface StoryWorkspaceEpisodeIndexFetchState {
  readonly runId: string | null;
  readonly data: StoryWorkspaceEpisodeIndexSurface | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly generation: number;
}

type StoryWorkspaceEpisodeIndexFetchAction =
  | { readonly type: 'reset'; readonly runId: string | null }
  | { readonly type: 'start'; readonly runId: string; readonly generation: number }
  | { readonly type: 'success'; readonly runId: string; readonly generation: number; readonly data: StoryWorkspaceEpisodeIndexSurface }
  | { readonly type: 'not-modified'; readonly runId: string; readonly generation: number }
  | { readonly type: 'error'; readonly runId: string; readonly generation: number; readonly error: Error };

const initialState = (runId: string | null): StoryWorkspaceEpisodeIndexFetchState => ({
  runId,
  data: null,
  error: null,
  isLoading: false,
  generation: 0,
});

function reduceState(
  state: StoryWorkspaceEpisodeIndexFetchState,
  action: StoryWorkspaceEpisodeIndexFetchAction,
): StoryWorkspaceEpisodeIndexFetchState {
  if (action.type === 'reset') return initialState(action.runId);
  if (action.runId !== state.runId || action.generation < state.generation) return state;
  if (action.type === 'start') {
    return { ...state, error: null, isLoading: true, generation: action.generation };
  }
  if (action.type === 'success') {
    return {
      runId: state.runId,
      data: action.data,
      error: null,
      isLoading: false,
      generation: action.generation,
    };
  }
  if (action.type === 'not-modified') {
    return { ...state, error: null, isLoading: false, generation: action.generation };
  }
  return { ...state, error: action.error, isLoading: false, generation: action.generation };
}

export interface StoryWorkspaceEpisodeIndexState {
  readonly data: StoryWorkspaceEpisodeIndexSurface | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly refresh: () => void;
}

export function useStoryWorkspaceEpisodeIndex(
  runId: string | null | undefined,
  options: {
    readonly fetchImpl?: typeof fetch;
    readonly token?: string | null;
    readonly pollIntervalMs?: number;
  } = {},
): StoryWorkspaceEpisodeIndexState {
  const normalizedRunId = runId ?? null;
  const [state, dispatch] = useReducer(reduceState, normalizedRunId, initialState);
  const runIdRef = useRef<string | null>(normalizedRunId);
  const mountedRef = useRef(false);
  const generationRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const etagRef = useRef<string | null>(null);

  const refresh = useCallback(() => {
    const requestRunId = normalizedRunId;
    if (!requestRunId || !mountedRef.current || runIdRef.current !== requestRunId) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    dispatch({ type: 'start', runId: requestRunId, generation });
    void storyWorkspaceFetchEpisodeIndex(
      apiUrl(storyWorkspaceEpisodeIndexEndpoint(requestRunId)),
      {
        fetchImpl: options.fetchImpl,
        token: options.token === undefined ? getAuthToken() : options.token,
        etag: etagRef.current,
        expectedRunId: requestRunId,
        signal: controller.signal,
      },
    ).then((result) => {
      if (
        controller.signal.aborted
        || !mountedRef.current
        || runIdRef.current !== requestRunId
        || generationRef.current !== generation
      ) return;
      if (result.kind === 'index') etagRef.current = result.data.etag;
      dispatch(result.kind === 'index'
        ? { type: 'success', runId: requestRunId, generation, data: result.data }
        : { type: 'not-modified', runId: requestRunId, generation });
    }).catch((reason: unknown) => {
      if (
        controller.signal.aborted
        || !mountedRef.current
        || runIdRef.current !== requestRunId
        || generationRef.current !== generation
      ) return;
      dispatch({
        type: 'error',
        runId: requestRunId,
        generation,
        error: reason instanceof Error ? reason : new Error('Episode index request failed.'),
      });
    });
  }, [normalizedRunId, options.fetchImpl, options.token]);

  useEffect(() => {
    mountedRef.current = true;
    runIdRef.current = normalizedRunId;
    generationRef.current += 1;
    controllerRef.current?.abort();
    controllerRef.current = null;
    etagRef.current = null;
    dispatch({ type: 'reset', runId: normalizedRunId });
    if (normalizedRunId) refresh();
    const interval = normalizedRunId
      ? window.setInterval(
        refresh,
        storyWorkspaceEpisodeArtifactsPollInterval(
          options.pollIntervalMs ?? STORY_WORKSPACE_EPISODE_INDEX_POLL_INTERVAL_MS,
        ),
      )
      : null;
    const handleOutput = (event: Event) => {
      if (
        normalizedRunId
        && storyWorkspaceShouldInvalidateEpisodeArtifacts(
          (event as CustomEvent<unknown>).detail,
          normalizedRunId,
        )
      ) refresh();
    };
    window.addEventListener('ink:story-workspace-output', handleOutput);
    return () => {
      mountedRef.current = false;
      controllerRef.current?.abort();
      if (interval !== null) window.clearInterval(interval);
      window.removeEventListener('ink:story-workspace-output', handleOutput);
    };
  }, [normalizedRunId, options.pollIntervalMs, refresh]);

  return {
    data: state.runId === normalizedRunId ? state.data : null,
    error: state.runId === normalizedRunId ? state.error : null,
    isLoading: state.runId === normalizedRunId && state.isLoading,
    refresh,
  };
}
