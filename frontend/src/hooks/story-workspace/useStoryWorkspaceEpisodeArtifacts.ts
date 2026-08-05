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
const STORY_WORKSPACE_EPISODE_MAX_TIMER_MS = 2_147_483_647;
const STORY_WORKSPACE_EPISODE_INVALID_MESSAGE = 'Episode artifact data is unavailable.';
const STORY_WORKSPACE_EPISODE_ARTIFACT_KEYS = [
  'episode-outline.md',
  'script.md',
  'storyboard.yaml',
  'prompts/',
  'renders/',
  'review-report.md',
] as const;

export type StoryWorkspaceEpisodeArtifactRoot = typeof STORY_WORKSPACE_EPISODE_ARTIFACT_KEYS[number];

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
  constructor() {
    super(STORY_WORKSPACE_EPISODE_INVALID_MESSAGE);
    this.name = 'StoryWorkspaceEpisodeArtifactsContractError';
  }
}

export function storyWorkspaceEpisodeArtifactsEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/episode-artifacts`;
}

export function storyWorkspaceEpisodeArtifactsPollInterval(requested?: number): number {
  if (requested === Number.POSITIVE_INFINITY) return STORY_WORKSPACE_EPISODE_MAX_TIMER_MS;
  if (requested === undefined || !Number.isFinite(requested)) {
    return STORY_WORKSPACE_EPISODE_MIN_POLL_INTERVAL_MS;
  }
  return Math.min(
    Math.max(Math.trunc(requested), STORY_WORKSPACE_EPISODE_MIN_POLL_INTERVAL_MS),
    STORY_WORKSPACE_EPISODE_MAX_TIMER_MS,
  );
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

export interface StoryWorkspaceEpisodeArtifactsCommitGuard {
  readonly signal: AbortSignal;
  readonly requestRunId: string;
  readonly currentRunId: string | null;
  readonly requestGeneration: number;
  readonly currentGeneration: number;
}

export function storyWorkspaceShouldCommitEpisodeArtifactsResponse(
  guard: StoryWorkspaceEpisodeArtifactsCommitGuard,
): boolean {
  return !guard.signal.aborted
    && guard.requestRunId === guard.currentRunId
    && guard.requestGeneration === guard.currentGeneration;
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
      throw new StoryWorkspaceEpisodeArtifactsContractError();
    }
    const responseEtag = response.headers.get('ETag');
    if (responseEtag !== storyWorkspaceEpisodeQuotedEtag(options.etag)) {
      throw new StoryWorkspaceEpisodeArtifactsContractError();
    }
    return { kind: 'not-modified', etag: options.etag };
  }
  if (!response.ok) throw new StoryWorkspaceEpisodeArtifactsHttpError(response.status);
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new StoryWorkspaceEpisodeArtifactsContractError();
  }
  let data: StoryWorkspaceEpisodeArtifactSurface;
  try {
    data = storyWorkspaceParseEpisodeArtifactSurface(payload);
  } catch {
    throw new StoryWorkspaceEpisodeArtifactsContractError();
  }
  if (options.expectedRunId !== undefined && data.runId !== options.expectedRunId) {
    throw new StoryWorkspaceEpisodeArtifactsContractError();
  }
  const responseEtag = response.headers.get('ETag');
  if (data.bindingAvailability === 'bound') {
    if (data.etag === null || responseEtag !== storyWorkspaceEpisodeQuotedEtag(data.etag)) {
      throw new StoryWorkspaceEpisodeArtifactsContractError();
    }
  } else if (responseEtag !== null) {
    throw new StoryWorkspaceEpisodeArtifactsContractError();
  }
  return { kind: 'surface', data };
}

export interface StoryWorkspaceEpisodeArtifactsDiagnostic {
  readonly kind: 'invalid_payload';
  readonly message: typeof STORY_WORKSPACE_EPISODE_INVALID_MESSAGE;
}

export interface StoryWorkspaceEpisodeArtifactsFetchState {
  readonly runId: string | null;
  /** Per-artifact merged display surface; its manifest always comes from latest. */
  readonly data: StoryWorkspaceEpisodeArtifactSurface | null;
  /** Unmodified latest structurally valid 200 response. */
  readonly latest: StoryWorkspaceEpisodeArtifactSurface | null;
  readonly artifactCache: StoryWorkspaceEpisodeArtifactSessionCache;
  readonly invalidArtifactKeys: readonly StoryWorkspaceEpisodeArtifactRoot[];
  readonly staleArtifactKeys: readonly StoryWorkspaceEpisodeArtifactRoot[];
  readonly diagnostic: StoryWorkspaceEpisodeArtifactsDiagnostic | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly generation: number;
}

export type StoryWorkspaceEpisodeArtifactSessionCache = Readonly<Partial<Record<
  StoryWorkspaceEpisodeArtifactRoot,
  StoryWorkspaceEpisodeArtifactSurface
>>>;

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
    latest: null,
    artifactCache: {},
    invalidArtifactKeys: [],
    staleArtifactKeys: [],
    diagnostic: null,
    error: null,
    isLoading: false,
    generation: 0,
  };
}

function storyWorkspaceEpisodeArtifactAvailability(
  surface: StoryWorkspaceEpisodeArtifactSurface,
  key: StoryWorkspaceEpisodeArtifactRoot,
): string | null {
  return surface.artifacts.find((artifact) => artifact.relativeKey === key)?.availability ?? null;
}

function storyWorkspaceUpdateEpisodeArtifactCache(
  current: StoryWorkspaceEpisodeArtifactSessionCache,
  latest: StoryWorkspaceEpisodeArtifactSurface,
): StoryWorkspaceEpisodeArtifactSessionCache {
  if (latest.bindingAvailability === 'unbound') return {};
  const next: Partial<Record<StoryWorkspaceEpisodeArtifactRoot, StoryWorkspaceEpisodeArtifactSurface>> = {
    ...current,
  };
  for (const key of STORY_WORKSPACE_EPISODE_ARTIFACT_KEYS) {
    const availability = storyWorkspaceEpisodeArtifactAvailability(latest, key);
    if (availability === 'available') next[key] = latest;
    else if (availability !== 'invalid') delete next[key];
  }
  return next;
}

function storyWorkspaceMergeEpisodeArtifactLastGood(
  latest: StoryWorkspaceEpisodeArtifactSurface,
  cache: StoryWorkspaceEpisodeArtifactSessionCache,
  staleKeys: readonly StoryWorkspaceEpisodeArtifactRoot[],
): StoryWorkspaceEpisodeArtifactSurface {
  if (staleKeys.length === 0 || latest.bindingAvailability === 'unbound') return latest;
  const stale = new Set(staleKeys);
  const latestNarrative = latest.narrative;
  let narrative = latestNarrative;
  if (latestNarrative !== null) {
    const outline = stale.has('episode-outline.md')
      ? cache['episode-outline.md']?.narrative
      : latestNarrative;
    const script = stale.has('script.md') ? cache['script.md']?.narrative : latestNarrative;
    const storyboard = stale.has('storyboard.yaml')
      ? cache['storyboard.yaml']?.narrative
      : latestNarrative;
    narrative = {
      ...latestNarrative,
      overview: outline?.overview ?? latestNarrative.overview,
      narrativeBeats: outline?.narrativeBeats ?? latestNarrative.narrativeBeats,
      scenes: script?.scenes ?? latestNarrative.scenes,
      shots: storyboard?.shots ?? latestNarrative.shots,
      associations: latestNarrative.associations,
    };
  }
  const latestAuxiliary = latest.auxiliary;
  let auxiliary = latestAuxiliary;
  if (latestAuxiliary !== null) {
    const prompts = stale.has('prompts/') ? cache['prompts/']?.auxiliary : latestAuxiliary;
    const renders = stale.has('renders/') ? cache['renders/']?.auxiliary : latestAuxiliary;
    const review = stale.has('review-report.md')
      ? cache['review-report.md']?.auxiliary
      : latestAuxiliary;
    auxiliary = {
      ...latestAuxiliary,
      manifestRevision: latest.manifestRevision ?? latestAuxiliary.manifestRevision,
      prompts: prompts?.prompts ?? latestAuxiliary.prompts,
      renderGuide: renders?.renderGuide ?? latestAuxiliary.renderGuide,
      review: review?.review ?? latestAuxiliary.review,
      associations: latestAuxiliary.associations,
    };
  }
  return {
    ...latest,
    artifacts: latest.artifacts,
    narrative,
    auxiliary,
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
    const artifactCache = storyWorkspaceUpdateEpisodeArtifactCache(state.artifactCache, action.data);
    const invalidArtifactKeys = STORY_WORKSPACE_EPISODE_ARTIFACT_KEYS.filter(
      (key) => storyWorkspaceEpisodeArtifactAvailability(action.data, key) === 'invalid',
    );
    const staleArtifactKeys = invalidArtifactKeys.filter((key) => artifactCache[key] !== undefined);
    return {
      runId: state.runId,
      data: storyWorkspaceMergeEpisodeArtifactLastGood(action.data, artifactCache, staleArtifactKeys),
      latest: action.data,
      artifactCache,
      invalidArtifactKeys,
      staleArtifactKeys,
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
      diagnostic: {
        kind: 'invalid_payload',
        message: STORY_WORKSPACE_EPISODE_INVALID_MESSAGE,
      },
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
  readonly latest: StoryWorkspaceEpisodeArtifactSurface | null;
  readonly invalidArtifactKeys: readonly StoryWorkspaceEpisodeArtifactRoot[];
  readonly staleArtifactKeys: readonly StoryWorkspaceEpisodeArtifactRoot[];
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
      if (!storyWorkspaceShouldCommitEpisodeArtifactsResponse({
        signal: nextController.signal,
        requestRunId: normalizedRunId,
        currentRunId: etagCache.current.runId,
        requestGeneration: nextGeneration,
        currentGeneration: generation.current,
      })) return;
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
      if (
        !storyWorkspaceShouldCommitEpisodeArtifactsResponse({
          signal: nextController.signal,
          requestRunId: normalizedRunId,
          currentRunId: etagCache.current.runId,
          requestGeneration: nextGeneration,
          currentGeneration: generation.current,
        })
        || storyWorkspaceIsEpisodeArtifactsAbort(reason)
      ) return;
      if (reason instanceof StoryWorkspaceEpisodeArtifactsContractError) {
        dispatch({
          type: 'invalid',
          runId: normalizedRunId,
          generation: nextGeneration,
          diagnostic: {
            kind: 'invalid_payload',
            message: STORY_WORKSPACE_EPISODE_INVALID_MESSAGE,
          },
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
    latest: state.runId === normalizedRunId ? state.latest : null,
    invalidArtifactKeys: state.runId === normalizedRunId ? state.invalidArtifactKeys : [],
    staleArtifactKeys: state.runId === normalizedRunId ? state.staleArtifactKeys : [],
    diagnostic: state.runId === normalizedRunId ? state.diagnostic : null,
    error: state.runId === normalizedRunId ? state.error : null,
    isLoading: state.runId === normalizedRunId && state.isLoading,
    isShowingLastGood: state.runId === normalizedRunId
      && state.data !== null
      && (state.diagnostic !== null || state.staleArtifactKeys.length > 0),
    refresh,
  };
}
