// [Input] Actor-scoped Run plus registry Episode UID, artifact REST surface, and output hints.
// [Output] Run+Episode-isolated ETag fetch seam, last-good reducer, and polling hook.
// [Pos] Story Workspace Episode artifact query boundary (U5)
// [Sync] 2026-09-02: key requests, reducers, ETags, and last-good data by Run+Episode.

import { useCallback, useEffect, useReducer, useRef } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import {
  storyWorkspaceParseEpisodeArtifactSurface,
  type StoryWorkspaceEpisodeArtifactSurface,
} from './contracts';
import {
  storyWorkspaceQuotedEtag,
  storyWorkspaceResponseMatchesEtag,
} from './httpEtag';

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

export function storyWorkspaceEpisodeArtifactsEndpoint(
  runId: string,
  episodeId?: string | null,
): string {
  const endpoint = `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/episode-artifacts`;
  return episodeId ? `${endpoint}?episode=${encodeURIComponent(episodeId)}` : endpoint;
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
  readonly requestEpisodeId: string | null;
  readonly currentEpisodeId: string | null;
  readonly requestGeneration: number;
  readonly currentGeneration: number;
}

export interface StoryWorkspaceEpisodeArtifactsRequestTicket {
  readonly runId: string;
  readonly episodeId: string | null;
  readonly generation: number;
  readonly signal: AbortSignal;
}

export interface StoryWorkspaceEpisodeArtifactsRequestLifecycle {
  activate: (runId: string | null, episodeId?: string | null) => void;
  begin: (runId: string, episodeId?: string | null) => StoryWorkspaceEpisodeArtifactsRequestTicket;
  shouldCommit: (ticket: StoryWorkspaceEpisodeArtifactsRequestTicket) => boolean;
  commitEtag: (ticket: StoryWorkspaceEpisodeArtifactsRequestTicket, etag: string | null) => boolean;
  etagFor: (runId: string, episodeId?: string | null) => string | null;
  cleanup: () => void;
}

/**
 * Mounted request lifecycle shared by the hook and its Node seam. It owns the
 * AbortController, generation, run-local ETag, and late-response commit gate.
 */
export function storyWorkspaceCreateEpisodeArtifactsRequestLifecycle(
  initialRunId: string | null,
  initialEpisodeId: string | null = null,
): StoryWorkspaceEpisodeArtifactsRequestLifecycle {
  let generation = 0;
  let currentRunId = initialRunId;
  let currentEpisodeId = initialEpisodeId;
  let mounted = true;
  let etag: string | null = null;
  let controller: AbortController | null = null;

  const moveToQuery = (runId: string | null, episodeId: string | null) => {
    if (currentRunId === runId && currentEpisodeId === episodeId) return;
    controller?.abort();
    controller = null;
    generation += 1;
    currentRunId = runId;
    currentEpisodeId = episodeId;
    etag = null;
  };
  const shouldCommit = (ticket: StoryWorkspaceEpisodeArtifactsRequestTicket) => (
    mounted && storyWorkspaceShouldCommitEpisodeArtifactsResponse({
      signal: ticket.signal,
      requestRunId: ticket.runId,
      currentRunId,
      requestEpisodeId: ticket.episodeId,
      currentEpisodeId,
      requestGeneration: ticket.generation,
      currentGeneration: generation,
    })
  );

  return {
    activate(runId, episodeId = null) {
      moveToQuery(runId, episodeId);
      mounted = true;
    },
    begin(runId, episodeId = null) {
      if (!mounted) throw new Error('Episode artifact request lifecycle is inactive.');
      moveToQuery(runId, episodeId);
      controller?.abort();
      controller = new AbortController();
      generation += 1;
      return { runId, episodeId, generation, signal: controller.signal };
    },
    shouldCommit,
    commitEtag(ticket, value) {
      if (!shouldCommit(ticket)) return false;
      etag = value;
      return true;
    },
    etagFor(runId, episodeId = null) {
      return mounted && currentRunId === runId && currentEpisodeId === episodeId
        ? etag
        : null;
    },
    cleanup() {
      mounted = false;
      controller?.abort();
      controller = null;
      generation += 1;
      etag = null;
    },
  };
}

export function storyWorkspaceShouldCommitEpisodeArtifactsResponse(
  guard: StoryWorkspaceEpisodeArtifactsCommitGuard,
): boolean {
  return !guard.signal.aborted
    && guard.requestRunId === guard.currentRunId
    && guard.requestEpisodeId === guard.currentEpisodeId
    && guard.requestGeneration === guard.currentGeneration;
}

export interface StoryWorkspaceEpisodeArtifactsFetchOptions {
  readonly fetchImpl?: typeof fetch;
  readonly token?: string | null;
  readonly etag?: string | null;
  readonly expectedRunId?: string;
  readonly expectedEpisodeId?: string;
  readonly signal?: AbortSignal;
}

export type StoryWorkspaceEpisodeArtifactsFetchResult =
  | { readonly kind: 'surface'; readonly data: StoryWorkspaceEpisodeArtifactSurface }
  | { readonly kind: 'not-modified'; readonly etag: string };

/** Fetch one authoritative snapshot without ever consuming an error response body. */
export async function storyWorkspaceFetchEpisodeArtifacts(
  endpoint: string,
  options: StoryWorkspaceEpisodeArtifactsFetchOptions = {},
): Promise<StoryWorkspaceEpisodeArtifactsFetchResult> {
  const headers = new Headers({ Accept: 'application/json' });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);
  if (options.etag) headers.set('If-None-Match', storyWorkspaceQuotedEtag(options.etag));
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
    if (!storyWorkspaceResponseMatchesEtag(responseEtag, options.etag)) {
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
  if (
    options.expectedEpisodeId !== undefined
    && data.opaqueEpisodeId !== options.expectedEpisodeId
  ) throw new StoryWorkspaceEpisodeArtifactsContractError();
  const responseEtag = response.headers.get('ETag');
  if (data.bindingAvailability === 'bound') {
    if (data.etag === null || !storyWorkspaceResponseMatchesEtag(responseEtag, data.etag)) {
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
  readonly episodeId: string | null;
  /** Per-artifact merged display surface; its manifest always comes from latest. */
  readonly data: StoryWorkspaceEpisodeArtifactSurface | null;
  /** Unmodified latest structurally valid 200 response. */
  readonly latest: StoryWorkspaceEpisodeArtifactSurface | null;
  readonly artifactCache: StoryWorkspaceEpisodeArtifactSessionCache;
  readonly invalidArtifactKeys: readonly StoryWorkspaceEpisodeArtifactRoot[];
  readonly unavailableArtifactKeys: readonly StoryWorkspaceEpisodeArtifactRoot[];
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
  | { readonly type: 'reset'; readonly runId: string | null; readonly episodeId?: string | null }
  | { readonly type: 'start'; readonly runId: string; readonly episodeId?: string | null; readonly generation: number }
  | { readonly type: 'success'; readonly runId: string; readonly episodeId?: string | null; readonly generation: number; readonly data: StoryWorkspaceEpisodeArtifactSurface }
  | { readonly type: 'not-modified'; readonly runId: string; readonly episodeId?: string | null; readonly generation: number }
  | { readonly type: 'invalid'; readonly runId: string; readonly episodeId?: string | null; readonly generation: number; readonly diagnostic: StoryWorkspaceEpisodeArtifactsDiagnostic }
  | { readonly type: 'error'; readonly runId: string; readonly episodeId?: string | null; readonly generation: number; readonly error: Error };

export function storyWorkspaceEpisodeArtifactsInitialState(
  runId: string | null = null,
  episodeId: string | null = null,
): StoryWorkspaceEpisodeArtifactsFetchState {
  return {
    runId,
    episodeId,
    data: null,
    latest: null,
    artifactCache: {},
    invalidArtifactKeys: [],
    unavailableArtifactKeys: [],
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
    else if (availability !== 'invalid' && availability !== 'unavailable') delete next[key];
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
  const documents = [...(latest.documents ?? [])];
  for (const key of ['episode-outline.md', 'script.md', 'review-report.md'] as const) {
    if (!stale.has(key)) continue;
    const cached = cache[key]?.documents?.find((document) => document.relativeKey === key);
    if (cached === undefined) continue;
    const currentIndex = documents.findIndex((document) => document.relativeKey === key);
    if (currentIndex < 0) documents.push(cached);
    else documents[currentIndex] = cached;
  }
  return {
    ...latest,
    artifacts: latest.artifacts,
    documents,
    narrative,
    auxiliary,
  };
}

/** Pure stale-response and last-good gate; reset is the only cross-run transition. */
export function storyWorkspaceReduceEpisodeArtifactsFetch(
  state: StoryWorkspaceEpisodeArtifactsFetchState,
  action: StoryWorkspaceEpisodeArtifactsFetchAction,
): StoryWorkspaceEpisodeArtifactsFetchState {
  if (action.type === 'reset') {
    return storyWorkspaceEpisodeArtifactsInitialState(action.runId, action.episodeId ?? null);
  }
  if (
    action.runId !== state.runId
    || (action.episodeId ?? null) !== state.episodeId
    || action.generation < state.generation
  ) return state;
  if (action.type === 'start') {
    return { ...state, error: null, isLoading: true, generation: action.generation };
  }
  if (action.type === 'success') {
    const artifactCache = storyWorkspaceUpdateEpisodeArtifactCache(state.artifactCache, action.data);
    const invalidArtifactKeys = STORY_WORKSPACE_EPISODE_ARTIFACT_KEYS.filter(
      (key) => storyWorkspaceEpisodeArtifactAvailability(action.data, key) === 'invalid',
    );
    const unavailableArtifactKeys = STORY_WORKSPACE_EPISODE_ARTIFACT_KEYS.filter(
      (key) => storyWorkspaceEpisodeArtifactAvailability(action.data, key) === 'unavailable',
    );
    const recoverableArtifactKeys = STORY_WORKSPACE_EPISODE_ARTIFACT_KEYS.filter(
      (key) => {
        const availability = storyWorkspaceEpisodeArtifactAvailability(action.data, key);
        return availability === 'invalid' || availability === 'unavailable';
      },
    );
    const staleArtifactKeys = recoverableArtifactKeys.filter(
      (key) => artifactCache[key] !== undefined,
    );
    return {
      runId: state.runId,
      episodeId: state.episodeId,
      data: storyWorkspaceMergeEpisodeArtifactLastGood(action.data, artifactCache, staleArtifactKeys),
      latest: action.data,
      artifactCache,
      invalidArtifactKeys,
      unavailableArtifactKeys,
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
  readonly unavailableArtifactKeys: readonly StoryWorkspaceEpisodeArtifactRoot[];
  readonly staleArtifactKeys: readonly StoryWorkspaceEpisodeArtifactRoot[];
  readonly diagnostic: StoryWorkspaceEpisodeArtifactsDiagnostic | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly isShowingLastGood: boolean;
  readonly refresh: () => void;
}

/**
 * Reenter and poll one explicit registry Episode. ETags and last-good data live
 * only for this mounted hook instance and clear when either identity changes.
 */
export function useStoryWorkspaceEpisodeArtifacts(
  runId: string | null | undefined,
  episodeId: string | null | undefined,
  options: StoryWorkspaceEpisodeArtifactsUseOptions = {},
): StoryWorkspaceEpisodeArtifactsState {
  const normalizedRunId = runId ?? null;
  const normalizedEpisodeId = episodeId ?? null;
  const [state, dispatch] = useReducer(
    storyWorkspaceReduceEpisodeArtifactsFetch,
    storyWorkspaceEpisodeArtifactsInitialState(normalizedRunId, normalizedEpisodeId),
  );
  const lifecycleRef = useRef<StoryWorkspaceEpisodeArtifactsRequestLifecycle | null>(null);
  const renderedRunIdRef = useRef<string | null>(normalizedRunId);
  const renderedEpisodeIdRef = useRef<string | null>(normalizedEpisodeId);
  if (lifecycleRef.current === null) {
    lifecycleRef.current = storyWorkspaceCreateEpisodeArtifactsRequestLifecycle(
      normalizedRunId,
      normalizedEpisodeId,
    );
  }
  const lifecycle = lifecycleRef.current;

  const refresh = useCallback(() => {
    if (!normalizedRunId || !normalizedEpisodeId) return;
    const ticket = lifecycle.begin(normalizedRunId, normalizedEpisodeId);
    dispatch({
      type: 'start',
      runId: normalizedRunId,
      episodeId: normalizedEpisodeId,
      generation: ticket.generation,
    });
    void storyWorkspaceFetchEpisodeArtifacts(
      apiUrl(storyWorkspaceEpisodeArtifactsEndpoint(normalizedRunId, normalizedEpisodeId)),
      {
        fetchImpl: options.fetchImpl,
        token: options.token === undefined ? getAuthToken() : options.token,
        etag: lifecycle.etagFor(normalizedRunId, normalizedEpisodeId),
        expectedRunId: normalizedRunId,
        expectedEpisodeId: normalizedEpisodeId,
        signal: ticket.signal,
      },
    ).then((result) => {
      if (!lifecycle.shouldCommit(ticket)) return;
      if (result.kind === 'not-modified') {
        dispatch({
          type: 'not-modified',
          runId: normalizedRunId,
          episodeId: normalizedEpisodeId,
          generation: ticket.generation,
        });
        return;
      }
      if (!lifecycle.commitEtag(ticket, result.data.etag)) return;
      dispatch({
        type: 'success',
        runId: normalizedRunId,
        episodeId: normalizedEpisodeId,
        generation: ticket.generation,
        data: result.data,
      });
    }).catch((reason: unknown) => {
      if (
        !lifecycle.shouldCommit(ticket)
        || storyWorkspaceIsEpisodeArtifactsAbort(reason)
      ) return;
      if (reason instanceof StoryWorkspaceEpisodeArtifactsContractError) {
        dispatch({
          type: 'invalid',
          runId: normalizedRunId,
          episodeId: normalizedEpisodeId,
          generation: ticket.generation,
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
        episodeId: normalizedEpisodeId,
        generation: ticket.generation,
        error: reason instanceof Error
          ? reason
          : new Error('Episode artifact request failed.'),
      });
    });
  }, [lifecycle, normalizedEpisodeId, normalizedRunId, options.fetchImpl, options.token]);

  useEffect(() => {
    lifecycle.activate(normalizedRunId, normalizedEpisodeId);
    if (
      renderedRunIdRef.current !== normalizedRunId
      || renderedEpisodeIdRef.current !== normalizedEpisodeId
    ) {
      renderedRunIdRef.current = normalizedRunId;
      renderedEpisodeIdRef.current = normalizedEpisodeId;
      dispatch({
        type: 'reset',
        runId: normalizedRunId,
        episodeId: normalizedEpisodeId,
      });
    }
    if (normalizedRunId && normalizedEpisodeId) refresh();
    return () => lifecycle.cleanup();
  }, [lifecycle, normalizedEpisodeId, normalizedRunId, refresh]);

  useEffect(() => {
    if (!normalizedRunId || !normalizedEpisodeId) return;
    const timer = window.setInterval(
      refresh,
      storyWorkspaceEpisodeArtifactsPollInterval(options.pollIntervalMs),
    );
    return () => window.clearInterval(timer);
  }, [normalizedEpisodeId, normalizedRunId, options.pollIntervalMs, refresh]);

  useEffect(() => {
    if (!normalizedRunId || !normalizedEpisodeId) return;
    const handleOutput = (event: Event) => {
      if (storyWorkspaceShouldInvalidateEpisodeArtifacts(
        (event as CustomEvent<unknown>).detail,
        normalizedRunId,
      )) refresh();
    };
    window.addEventListener(STORY_WORKSPACE_EPISODE_OUTPUT_EVENT, handleOutput);
    return () => window.removeEventListener(STORY_WORKSPACE_EPISODE_OUTPUT_EVENT, handleOutput);
  }, [normalizedEpisodeId, normalizedRunId, refresh]);

  const isCurrentQuery = state.runId === normalizedRunId
    && state.episodeId === normalizedEpisodeId;

  return {
    data: isCurrentQuery ? state.data : null,
    latest: isCurrentQuery ? state.latest : null,
    invalidArtifactKeys: isCurrentQuery ? state.invalidArtifactKeys : [],
    unavailableArtifactKeys: isCurrentQuery
      ? state.unavailableArtifactKeys
      : [],
    staleArtifactKeys: isCurrentQuery ? state.staleArtifactKeys : [],
    diagnostic: isCurrentQuery ? state.diagnostic : null,
    error: isCurrentQuery ? state.error : null,
    isLoading: isCurrentQuery && state.isLoading,
    isShowingLastGood: isCurrentQuery
      && state.data !== null
      && (state.diagnostic !== null || state.staleArtifactKeys.length > 0),
    refresh,
  };
}
