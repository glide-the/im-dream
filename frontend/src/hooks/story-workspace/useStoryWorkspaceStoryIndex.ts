// [Input] Actor-scoped Dream run identity and the dedicated Story Index REST projection.
// [Output] Strict ETag reads, last-good state, and one idempotent reconcile mutation.
// [Pos] Story Workspace Story Index query boundary; independent from Episode Artifact CAS.

import { useCallback, useEffect, useReducer, useRef } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import type {
  StoryWorkspaceStoryIndexErrorCode,
  StoryWorkspaceStoryIndexProjection,
  StoryWorkspaceStoryIndexStatus,
} from './contracts';

const STORY_WORKSPACE_STORY_INDEX_INVALID_MESSAGE = 'Story index data is unavailable.';
export const STORY_WORKSPACE_STORY_INDEX_POLL_INTERVAL_MS = 30_000;
const STORY_WORKSPACE_STORY_INDEX_RUN_ID = /^run_[0-9a-f]{32}$/;
const STORY_WORKSPACE_STORY_INDEX_PROJECT_ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const STORY_WORKSPACE_STORY_INDEX_UUID5 =
  /^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const STORY_WORKSPACE_STORY_INDEX_REVISION = /^sha256:[0-9a-f]{64}$/;
const STORY_WORKSPACE_STORY_INDEX_IDEMPOTENCY_KEY = /^[A-Za-z0-9._:-]{1,255}$/;
const STORY_WORKSPACE_STORY_INDEX_DATETIME =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/;
const STORY_WORKSPACE_STORY_INDEX_STATUSES = new Set<StoryWorkspaceStoryIndexStatus>([
  'indexed',
  'stale',
  'missing',
  'failed',
]);
const STORY_WORKSPACE_STORY_INDEX_ERROR_CODES = new Set<StoryWorkspaceStoryIndexErrorCode>([
  'story_index_row_missing',
  'story_index_schema_unavailable',
  'story_index_database_unavailable',
  'story_index_write_failed',
  'story_index_conflict',
  'story_index_invalid_artifact',
  'story_index_revision_conflict',
  'artifact_missing',
]);
const STORY_WORKSPACE_STORY_INDEX_KEYS = [
  'runId',
  'projectId',
  'storyId',
  'status',
  'observedManifestRevision',
  'observedScriptRevision',
  'indexedManifestRevision',
  'indexedScriptRevision',
  'episodeCount',
  'lastIndexedAt',
  'errorCode',
  'retryable',
  'etag',
] as const;

function storyWorkspaceStoryIndexIsRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function storyWorkspaceStoryIndexHasExactKeys(value: Record<string, unknown>): boolean {
  const keys = Object.keys(value).sort();
  const expected = [...STORY_WORKSPACE_STORY_INDEX_KEYS].sort();
  return keys.length === expected.length && keys.every((key, index) => key === expected[index]);
}

function storyWorkspaceStoryIndexNullableRevision(value: unknown): string | null {
  if (value === null) return null;
  if (typeof value !== 'string' || !STORY_WORKSPACE_STORY_INDEX_REVISION.test(value)) {
    throw new StoryWorkspaceStoryIndexContractError();
  }
  return value;
}

function storyWorkspaceStoryIndexNullableDatetime(value: unknown): string | null {
  if (value === null) return null;
  if (
    typeof value !== 'string'
    || !STORY_WORKSPACE_STORY_INDEX_DATETIME.test(value)
    || !Number.isFinite(Date.parse(value))
  ) throw new StoryWorkspaceStoryIndexContractError();
  return value;
}

function storyWorkspaceStoryIndexNullableErrorCode(
  value: unknown,
): StoryWorkspaceStoryIndexErrorCode | null {
  if (value === null) return null;
  if (
    typeof value !== 'string'
    || !STORY_WORKSPACE_STORY_INDEX_ERROR_CODES.has(value as StoryWorkspaceStoryIndexErrorCode)
  ) throw new StoryWorkspaceStoryIndexContractError();
  return value as StoryWorkspaceStoryIndexErrorCode;
}

function storyWorkspaceStoryIndexQuotedEtag(etag: string): string {
  return `"${etag}"`;
}

function storyWorkspaceStoryIndexSafeErrorCode(
  value: unknown,
): StoryWorkspaceStoryIndexErrorCode | null {
  if (!storyWorkspaceStoryIndexIsRecord(value)) return null;
  const error = value.error;
  if (!storyWorkspaceStoryIndexIsRecord(error)) return null;
  return storyWorkspaceStoryIndexNullableErrorCodeOrNull(error.code);
}

function storyWorkspaceStoryIndexNullableErrorCodeOrNull(
  value: unknown,
): StoryWorkspaceStoryIndexErrorCode | null {
  return typeof value === 'string'
    && STORY_WORKSPACE_STORY_INDEX_ERROR_CODES.has(value as StoryWorkspaceStoryIndexErrorCode)
    ? value as StoryWorkspaceStoryIndexErrorCode
    : null;
}

async function storyWorkspaceStoryIndexReadSafeErrorCode(
  response: Response,
): Promise<StoryWorkspaceStoryIndexErrorCode | null> {
  try {
    return storyWorkspaceStoryIndexSafeErrorCode(await response.json());
  } catch {
    return null;
  }
}

export class StoryWorkspaceStoryIndexHttpError extends Error {
  readonly status: number;
  readonly errorCode: StoryWorkspaceStoryIndexErrorCode | null;

  constructor(status: number, errorCode: StoryWorkspaceStoryIndexErrorCode | null = null) {
    super(`Story index request failed (${status}).`);
    this.name = 'StoryWorkspaceStoryIndexHttpError';
    this.status = status;
    this.errorCode = errorCode;
  }
}

export class StoryWorkspaceStoryIndexContractError extends Error {
  constructor() {
    super(STORY_WORKSPACE_STORY_INDEX_INVALID_MESSAGE);
    this.name = 'StoryWorkspaceStoryIndexContractError';
  }
}

/** Strictly parse the complete public projection; unknown keys fail closed. */
export function storyWorkspaceParseStoryIndexProjection(
  value: unknown,
): StoryWorkspaceStoryIndexProjection {
  if (
    !storyWorkspaceStoryIndexIsRecord(value)
    || !storyWorkspaceStoryIndexHasExactKeys(value)
    || typeof value.runId !== 'string'
    || !STORY_WORKSPACE_STORY_INDEX_RUN_ID.test(value.runId)
    || typeof value.projectId !== 'string'
    || value.projectId.length > 255
    || !STORY_WORKSPACE_STORY_INDEX_PROJECT_ID.test(value.projectId)
    || (
      value.storyId !== null
      && (typeof value.storyId !== 'string' || !STORY_WORKSPACE_STORY_INDEX_UUID5.test(value.storyId))
    )
    || typeof value.status !== 'string'
    || !STORY_WORKSPACE_STORY_INDEX_STATUSES.has(value.status as StoryWorkspaceStoryIndexStatus)
    || typeof value.episodeCount !== 'number'
    || !Number.isSafeInteger(value.episodeCount)
    || value.episodeCount < 1
    || typeof value.retryable !== 'boolean'
    || typeof value.etag !== 'string'
    || !STORY_WORKSPACE_STORY_INDEX_REVISION.test(value.etag)
  ) throw new StoryWorkspaceStoryIndexContractError();

  const projection: StoryWorkspaceStoryIndexProjection = {
    runId: value.runId,
    projectId: value.projectId,
    storyId: value.storyId,
    status: value.status as StoryWorkspaceStoryIndexStatus,
    observedManifestRevision: storyWorkspaceStoryIndexNullableRevision(
      value.observedManifestRevision,
    ),
    observedScriptRevision: storyWorkspaceStoryIndexNullableRevision(value.observedScriptRevision),
    indexedManifestRevision: storyWorkspaceStoryIndexNullableRevision(
      value.indexedManifestRevision,
    ),
    indexedScriptRevision: storyWorkspaceStoryIndexNullableRevision(value.indexedScriptRevision),
    episodeCount: value.episodeCount,
    lastIndexedAt: storyWorkspaceStoryIndexNullableDatetime(value.lastIndexedAt),
    errorCode: storyWorkspaceStoryIndexNullableErrorCode(value.errorCode),
    retryable: value.retryable,
    etag: value.etag,
  };

  if (projection.status === 'indexed') {
    if (
      projection.storyId === null
      || projection.errorCode !== null
      || projection.observedManifestRevision === null
      || projection.observedScriptRevision === null
      || projection.observedManifestRevision !== projection.indexedManifestRevision
      || projection.observedScriptRevision !== projection.indexedScriptRevision
    ) throw new StoryWorkspaceStoryIndexContractError();
  }
  if (projection.status === 'stale' && projection.storyId === null) {
    throw new StoryWorkspaceStoryIndexContractError();
  }
  return projection;
}

export function storyWorkspaceStoryIndexEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/story-index`;
}

export function storyWorkspaceStoryIndexReconcileEndpoint(runId: string): string {
  return `${storyWorkspaceStoryIndexEndpoint(runId)}/reconcile`;
}

export function storyWorkspaceStoryIndexQueryIdentity(
  runId: string,
): readonly ['story-workspace', 'workflow-run', string, 'story-index'] {
  return ['story-workspace', 'workflow-run', runId, 'story-index'];
}

export type StoryWorkspaceStoryIndexFetchResult =
  | { readonly kind: 'projection'; readonly data: StoryWorkspaceStoryIndexProjection }
  | { readonly kind: 'not-modified'; readonly etag: string };

export interface StoryWorkspaceStoryIndexFetchOptions {
  readonly fetchImpl?: typeof fetch;
  readonly token?: string | null;
  readonly etag?: string | null;
  readonly expectedRunId?: string;
  readonly signal?: AbortSignal;
}

/** Read one index projection without allowing server diagnostics into UI errors. */
export async function storyWorkspaceFetchStoryIndex(
  endpoint: string,
  options: StoryWorkspaceStoryIndexFetchOptions = {},
): Promise<StoryWorkspaceStoryIndexFetchResult> {
  const headers = new Headers({ Accept: 'application/json' });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);
  if (options.etag) headers.set('If-None-Match', storyWorkspaceStoryIndexQuotedEtag(options.etag));
  const response = await (options.fetchImpl ?? fetch)(endpoint, {
    credentials: 'include',
    headers,
    signal: options.signal ?? null,
  });
  if (response.status === 304) {
    if (
      !options.etag
      || response.headers.get('ETag') !== storyWorkspaceStoryIndexQuotedEtag(options.etag)
    ) throw new StoryWorkspaceStoryIndexContractError();
    return { kind: 'not-modified', etag: options.etag };
  }
  if (!response.ok) {
    throw new StoryWorkspaceStoryIndexHttpError(
      response.status,
      await storyWorkspaceStoryIndexReadSafeErrorCode(response),
    );
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new StoryWorkspaceStoryIndexContractError();
  }
  const data = storyWorkspaceParseStoryIndexProjection(payload);
  if (options.expectedRunId !== undefined && data.runId !== options.expectedRunId) {
    throw new StoryWorkspaceStoryIndexContractError();
  }
  if (response.headers.get('ETag') !== storyWorkspaceStoryIndexQuotedEtag(data.etag)) {
    throw new StoryWorkspaceStoryIndexContractError();
  }
  return { kind: 'projection', data };
}

export interface StoryWorkspaceStoryIndexReconcileOptions {
  readonly fetchImpl?: typeof fetch;
  readonly token?: string | null;
  readonly signal?: AbortSignal;
  readonly idempotencyKey?: string;
  readonly endpoint?: string;
}

export function storyWorkspaceNewStoryIndexIdempotencyKey(
  uuidFactory: () => string = () => globalThis.crypto.randomUUID(),
): string {
  return `story-index:${uuidFactory()}`;
}

/** Materialize once against the exact Story Index projection ETag. */
export async function storyWorkspaceReconcileStoryIndex(
  runId: string,
  etag: string,
  options: StoryWorkspaceStoryIndexReconcileOptions = {},
): Promise<StoryWorkspaceStoryIndexProjection> {
  if (!STORY_WORKSPACE_STORY_INDEX_RUN_ID.test(runId)
    || !STORY_WORKSPACE_STORY_INDEX_REVISION.test(etag)) {
    throw new StoryWorkspaceStoryIndexContractError();
  }
  const idempotencyKey = options.idempotencyKey;
  if (
    idempotencyKey !== undefined
    && !STORY_WORKSPACE_STORY_INDEX_IDEMPOTENCY_KEY.test(idempotencyKey)
  ) throw new StoryWorkspaceStoryIndexContractError();
  const headers = new Headers({
    Accept: 'application/json',
    'Content-Type': 'application/json',
    'If-Match': storyWorkspaceStoryIndexQuotedEtag(etag),
  });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);
  const response = await (options.fetchImpl ?? fetch)(
    options.endpoint ?? storyWorkspaceStoryIndexReconcileEndpoint(runId),
    {
      method: 'POST',
      credentials: 'include',
      headers,
      body: JSON.stringify(idempotencyKey === undefined ? {} : { idempotencyKey }),
      signal: options.signal ?? null,
    },
  );
  if (!response.ok) {
    throw new StoryWorkspaceStoryIndexHttpError(
      response.status,
      await storyWorkspaceStoryIndexReadSafeErrorCode(response),
    );
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new StoryWorkspaceStoryIndexContractError();
  }
  const data = storyWorkspaceParseStoryIndexProjection(payload);
  if (
    data.runId !== runId
    || response.headers.get('ETag') !== storyWorkspaceStoryIndexQuotedEtag(data.etag)
  ) throw new StoryWorkspaceStoryIndexContractError();
  return data;
}

export interface StoryWorkspaceStoryIndexFetchState {
  readonly runId: string | null;
  readonly data: StoryWorkspaceStoryIndexProjection | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly isReconciling: boolean;
  readonly readGeneration: number;
  readonly reconcileGeneration: number;
}

export type StoryWorkspaceStoryIndexFetchAction =
  | { readonly type: 'reset'; readonly runId: string | null }
  | { readonly type: 'read-start'; readonly runId: string; readonly generation: number }
  | { readonly type: 'read-not-modified'; readonly runId: string; readonly generation: number }
  | { readonly type: 'read-success'; readonly runId: string; readonly generation: number; readonly data: StoryWorkspaceStoryIndexProjection }
  | { readonly type: 'read-error'; readonly runId: string; readonly generation: number; readonly error: Error }
  | { readonly type: 'reconcile-start'; readonly runId: string; readonly generation: number }
  | { readonly type: 'reconcile-success'; readonly runId: string; readonly generation: number; readonly data: StoryWorkspaceStoryIndexProjection }
  | { readonly type: 'reconcile-error'; readonly runId: string; readonly generation: number; readonly error: Error };

export function storyWorkspaceStoryIndexInitialState(
  runId: string | null = null,
): StoryWorkspaceStoryIndexFetchState {
  return {
    runId,
    data: null,
    error: null,
    isLoading: false,
    isReconciling: false,
    readGeneration: 0,
    reconcileGeneration: 0,
  };
}

/** Errors retain the mounted run's last-good projection and never touch Artifact state. */
export function storyWorkspaceReduceStoryIndexFetch(
  state: StoryWorkspaceStoryIndexFetchState,
  action: StoryWorkspaceStoryIndexFetchAction,
): StoryWorkspaceStoryIndexFetchState {
  if (action.type === 'reset') return storyWorkspaceStoryIndexInitialState(action.runId);
  if (action.runId !== state.runId) return state;
  if (action.type.startsWith('read-') && action.generation < state.readGeneration) return state;
  if (action.type.startsWith('reconcile-') && action.generation < state.reconcileGeneration) {
    return state;
  }
  if (action.type === 'read-start') {
    return { ...state, error: null, isLoading: true, readGeneration: action.generation };
  }
  if (action.type === 'read-not-modified') {
    return { ...state, error: null, isLoading: false, readGeneration: action.generation };
  }
  if (action.type === 'read-success') {
    return {
      ...state,
      data: action.data,
      error: null,
      isLoading: false,
      readGeneration: action.generation,
    };
  }
  if (action.type === 'read-error') {
    return {
      ...state,
      error: action.error,
      isLoading: false,
      readGeneration: action.generation,
    };
  }
  if (action.type === 'reconcile-start') {
    return {
      ...state,
      error: null,
      isReconciling: true,
      reconcileGeneration: action.generation,
    };
  }
  if (action.type === 'reconcile-success') {
    return {
      ...state,
      data: action.data,
      error: null,
      isReconciling: false,
      reconcileGeneration: action.generation,
    };
  }
  return {
    ...state,
    error: action.error,
    isReconciling: false,
    reconcileGeneration: action.generation,
  };
}

export interface StoryWorkspaceStoryIndexUseOptions {
  readonly fetchImpl?: typeof fetch;
  readonly token?: string | null;
  readonly enabled?: boolean;
  readonly pollIntervalMs?: number;
}

export interface StoryWorkspaceStoryIndexState {
  readonly data: StoryWorkspaceStoryIndexProjection | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly isReconciling: boolean;
  readonly isShowingLastGood: boolean;
  readonly refresh: () => void;
  readonly reconcile: (
    idempotencyKey?: string,
  ) => Promise<StoryWorkspaceStoryIndexProjection>;
}

function storyWorkspaceStoryIndexIsAbort(reason: unknown): boolean {
  return reason instanceof DOMException
    ? reason.name === 'AbortError'
    : storyWorkspaceStoryIndexIsRecord(reason) && reason.name === 'AbortError';
}

export function storyWorkspaceShouldPollStoryIndex(
  enabled: boolean,
  visibilityState: DocumentVisibilityState,
): boolean {
  return enabled && visibilityState === 'visible';
}

/** One run-scoped query and one mutation; neither can alter Episode Artifact truth. */
export function useStoryWorkspaceStoryIndex(
  runId: string | null | undefined,
  options: StoryWorkspaceStoryIndexUseOptions = {},
): StoryWorkspaceStoryIndexState {
  const normalizedRunId = runId ?? null;
  const enabled = options.enabled ?? true;
  const [state, dispatch] = useReducer(
    storyWorkspaceReduceStoryIndexFetch,
    normalizedRunId,
    storyWorkspaceStoryIndexInitialState,
  );
  const currentRunIdRef = useRef<string | null>(normalizedRunId);
  currentRunIdRef.current = normalizedRunId;
  const mountedRef = useRef(false);
  const etagRef = useRef<string | null>(null);
  const readGenerationRef = useRef(0);
  const reconcileGenerationRef = useRef(0);
  const readControllerRef = useRef<AbortController | null>(null);
  const reconcileControllerRef = useRef<AbortController | null>(null);
  const reconcileInFlightRef = useRef<Promise<StoryWorkspaceStoryIndexProjection> | null>(null);
  const refreshAfterReconcileRef = useRef(false);

  const refresh = useCallback(() => {
    if (!enabled || !normalizedRunId || currentRunIdRef.current !== normalizedRunId) return;
    if (reconcileInFlightRef.current !== null) {
      refreshAfterReconcileRef.current = true;
      return;
    }
    readControllerRef.current?.abort();
    const controller = new AbortController();
    readControllerRef.current = controller;
    readGenerationRef.current += 1;
    const generation = readGenerationRef.current;
    dispatch({ type: 'read-start', runId: normalizedRunId, generation });
    void storyWorkspaceFetchStoryIndex(
      apiUrl(storyWorkspaceStoryIndexEndpoint(normalizedRunId)),
      {
        fetchImpl: options.fetchImpl,
        token: options.token === undefined ? getAuthToken() : options.token,
        etag: etagRef.current,
        expectedRunId: normalizedRunId,
        signal: controller.signal,
      },
    ).then((result) => {
      if (
        !mountedRef.current
        || controller.signal.aborted
        || currentRunIdRef.current !== normalizedRunId
        || generation !== readGenerationRef.current
      ) return;
      if (result.kind === 'not-modified') {
        dispatch({ type: 'read-not-modified', runId: normalizedRunId, generation });
        return;
      }
      etagRef.current = result.data.etag;
      dispatch({
        type: 'read-success',
        runId: normalizedRunId,
        generation,
        data: result.data,
      });
    }).catch((reason: unknown) => {
      if (
        !mountedRef.current
        || controller.signal.aborted
        || currentRunIdRef.current !== normalizedRunId
        || generation !== readGenerationRef.current
        || storyWorkspaceStoryIndexIsAbort(reason)
      ) return;
      dispatch({
        type: 'read-error',
        runId: normalizedRunId,
        generation,
        error: reason instanceof Error ? reason : new Error('Story index request failed.'),
      });
    });
  }, [enabled, normalizedRunId, options.fetchImpl, options.token]);

  const reconcile = useCallback((requestedIdempotencyKey?: string) => {
    if (reconcileInFlightRef.current !== null) return reconcileInFlightRef.current;
    if (
      !enabled
      || !normalizedRunId
      || currentRunIdRef.current !== normalizedRunId
      || etagRef.current === null
    ) {
      return Promise.reject(new StoryWorkspaceStoryIndexContractError());
    }
    readControllerRef.current?.abort();
    readGenerationRef.current += 1;
    const controller = new AbortController();
    reconcileControllerRef.current = controller;
    reconcileGenerationRef.current += 1;
    const generation = reconcileGenerationRef.current;
    const currentEtag = etagRef.current;
    const idempotencyKey = requestedIdempotencyKey
      ?? storyWorkspaceNewStoryIndexIdempotencyKey();
    dispatch({ type: 'reconcile-start', runId: normalizedRunId, generation });
    const pending = storyWorkspaceReconcileStoryIndex(normalizedRunId, currentEtag, {
      fetchImpl: options.fetchImpl,
      token: options.token === undefined ? getAuthToken() : options.token,
      signal: controller.signal,
      idempotencyKey,
      endpoint: apiUrl(storyWorkspaceStoryIndexReconcileEndpoint(normalizedRunId)),
    }).then((data) => {
      if (
        !mountedRef.current
        || controller.signal.aborted
        || currentRunIdRef.current !== normalizedRunId
        || generation !== reconcileGenerationRef.current
      ) return data;
      etagRef.current = data.etag;
      dispatch({
        type: 'reconcile-success',
        runId: normalizedRunId,
        generation,
        data,
      });
      return data;
    }).catch((reason: unknown) => {
      if (
        mountedRef.current
        && !controller.signal.aborted
        && currentRunIdRef.current === normalizedRunId
        && generation === reconcileGenerationRef.current
        && !storyWorkspaceStoryIndexIsAbort(reason)
      ) {
        dispatch({
          type: 'reconcile-error',
          runId: normalizedRunId,
          generation,
          error: reason instanceof Error ? reason : new Error('Story index reconcile failed.'),
        });
      }
      throw reason;
    }).finally(() => {
      if (reconcileInFlightRef.current === pending) reconcileInFlightRef.current = null;
      reconcileControllerRef.current = null;
      if (
        refreshAfterReconcileRef.current
        && mountedRef.current
        && currentRunIdRef.current === normalizedRunId
      ) {
        refreshAfterReconcileRef.current = false;
        refresh();
      }
    });
    reconcileInFlightRef.current = pending;
    return pending;
  }, [enabled, normalizedRunId, options.fetchImpl, options.token, refresh]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      readControllerRef.current?.abort();
      reconcileControllerRef.current?.abort();
      readGenerationRef.current += 1;
      reconcileGenerationRef.current += 1;
      etagRef.current = null;
      reconcileInFlightRef.current = null;
      refreshAfterReconcileRef.current = false;
    };
  }, []);

  useEffect(() => {
    readControllerRef.current?.abort();
    reconcileControllerRef.current?.abort();
    readGenerationRef.current += 1;
    reconcileGenerationRef.current += 1;
    etagRef.current = null;
    reconcileInFlightRef.current = null;
    refreshAfterReconcileRef.current = false;
    dispatch({ type: 'reset', runId: normalizedRunId });
    if (enabled && normalizedRunId) refresh();
  }, [enabled, normalizedRunId, refresh]);

  useEffect(() => {
    if (!enabled || !normalizedRunId || typeof document === 'undefined') return;
    const intervalMs = Math.max(
      options.pollIntervalMs ?? STORY_WORKSPACE_STORY_INDEX_POLL_INTERVAL_MS,
      1_000,
    );
    let interval: number | null = null;
    const stopPolling = () => {
      if (interval === null) return;
      window.clearInterval(interval);
      interval = null;
    };
    const schedulePolling = () => {
      stopPolling();
      if (!storyWorkspaceShouldPollStoryIndex(enabled, document.visibilityState)) return;
      interval = window.setInterval(refresh, intervalMs);
    };
    const handleVisibilityChange = () => {
      const becameVisible = storyWorkspaceShouldPollStoryIndex(
        enabled,
        document.visibilityState,
      );
      schedulePolling();
      if (becameVisible) refresh();
    };
    schedulePolling();
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [enabled, normalizedRunId, options.pollIntervalMs, refresh]);

  useEffect(() => {
    if (!enabled || !normalizedRunId) return;
    const handleOutput = (event: Event) => {
      const detail = (event as CustomEvent<unknown>).detail;
      if (!storyWorkspaceStoryIndexIsRecord(detail) || detail.type !== 'story-workspace-output') {
        return;
      }
      const eventRunId = detail.runId ?? detail.storyWorkspaceRunId;
      if (eventRunId === normalizedRunId) refresh();
    };
    window.addEventListener('ink:story-workspace-output', handleOutput);
    return () => window.removeEventListener('ink:story-workspace-output', handleOutput);
  }, [enabled, normalizedRunId, refresh]);

  const current = enabled && state.runId === normalizedRunId
    ? state
    : storyWorkspaceStoryIndexInitialState();
  return {
    data: current.data,
    error: current.error,
    isLoading: current.isLoading,
    isReconciling: current.isReconciling,
    isShowingLastGood: current.data !== null && current.error !== null,
    refresh,
    reconcile,
  };
}
