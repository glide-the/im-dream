// [Input] Actor-scoped run ID, Episode artifact REST surface, and optional output hints.
// [Output] Strict ETag fetch seam, last-good reducer, and polling/reentry hook.
// [Pos] Story Workspace Episode artifact query boundary (U5)
// [Sync] 2026-08-06: REST is authoritative; output events only invalidate the query.

import { useCallback, useEffect, useReducer, useRef } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import {
  storyWorkspaceParseEpisodeActionAccepted,
  storyWorkspaceParseEpisodeArtifactSurface,
  type StoryWorkspaceEpisodeActionAccepted,
  type StoryWorkspaceEpisodeActionContinueRequest,
  type StoryWorkspaceEpisodeActionContinueRequestV2,
  type StoryWorkspaceEpisodeArtifactSurface,
  type StoryWorkspaceEpisodeBindingRecoveryRequest,
  type StoryWorkspaceEpisodeDispatchAction,
} from './contracts';

const STORY_WORKSPACE_EPISODE_OUTPUT_EVENT = 'ink:story-workspace-output';
const STORY_WORKSPACE_EPISODE_MIN_POLL_INTERVAL_MS = 5000;
const STORY_WORKSPACE_EPISODE_MAX_TIMER_MS = 2_147_483_647;
const STORY_WORKSPACE_EPISODE_INVALID_MESSAGE = 'Episode artifact data is unavailable.';
const STORY_WORKSPACE_EPISODE_ACTION_INVALID_MESSAGE = 'Episode action data is unavailable.';
const STORY_WORKSPACE_EPISODE_ACTION_UNAVAILABLE_MESSAGE = 'Episode action is unavailable.';
const STORY_WORKSPACE_EPISODE_RUN_ID = /^run_[0-9a-f]{32}$/;
const STORY_WORKSPACE_EPISODE_HEX_ID = /^[0-9a-f]{32}$/;
const STORY_WORKSPACE_EPISODE_REVISION = /^sha256:[0-9a-f]{64}$/;
const STORY_WORKSPACE_EPISODE_IDEMPOTENCY_KEY = /^[A-Za-z0-9._:-]{1,255}$/;
const STORY_WORKSPACE_EPISODE_GUIDANCE_DENYLIST = [
  /(?:^|\s)\/drama-[a-z-]+\b/i,
  /\b(?:hidden|internal)\s+(?:reasoning|thoughts?)\b|\bchain\s+of\s+thought\b|\bsystem\s+prompt\b|隐藏推理|内部推理|思维链|系统提示词/i,
  /\bBearer\s+\S+/i,
  /(?<![A-Za-z0-9_-])(?:sk-(?:ant-|proj-)?|gh[pousr]_|xox[baprs]-)[A-Za-z0-9_-]{16,}/i,
  /(?<![A-Za-z0-9])\/(?:Users|home)\/[^\s]+|(?<![A-Za-z0-9])[A-Za-z]:\\Users\\[^\s]+/i,
  /(?:\$\{?HOME\}?|~)\/(?:\.[^/\s]+|[^/\s]+)\/(?:[^\s]+)|(?<![A-Za-z0-9])\/(?:etc)\/(?:passwd|shadow)(?![A-Za-z0-9])/i,
  /(?<![A-Za-z0-9_])\.\.?\/[^\s]+/,
  /(?:^|[\r\n;&|])\s*(?:[$>#]\s*)?(?:git|python(?:3(?:\.\d+)*)?|npx|rm|sudo|node|bash|sh)\b\s+(?:--?[A-Za-z0-9]|[A-Za-z0-9_./@])/i,
  /\b(?:process\.)?env(?:\s*\||\s*\[|\.)|\bprintenv\b|\b[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|CREDENTIALS?)\s*=/i,
  /\b(?:curl|wget)\b.{0,500}\|\s*(?:ba|z|fi)?sh\b/i,
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/i,
] as const;
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

export class StoryWorkspaceEpisodeActionHttpError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`Episode action request failed (${status}).`);
    this.name = 'StoryWorkspaceEpisodeActionHttpError';
    this.status = status;
  }
}

export class StoryWorkspaceEpisodeActionContractError extends Error {
  constructor() {
    super(STORY_WORKSPACE_EPISODE_ACTION_INVALID_MESSAGE);
    this.name = 'StoryWorkspaceEpisodeActionContractError';
  }
}

export class StoryWorkspaceEpisodeActionUnavailableError extends Error {
  constructor() {
    super(STORY_WORKSPACE_EPISODE_ACTION_UNAVAILABLE_MESSAGE);
    this.name = 'StoryWorkspaceEpisodeActionUnavailableError';
  }
}

export function storyWorkspaceEpisodeArtifactsEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/episode-artifacts`;
}

export function storyWorkspaceEpisodeBindingRecoveryEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/episode-binding/recover`;
}

export function storyWorkspaceEpisodeActionContinueEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/episode-actions/continue`;
}

interface StoryWorkspaceEpisodeActionFetchOptions {
  readonly fetchImpl?: typeof fetch;
  readonly token?: string | null;
  readonly idempotencyKey: string;
}

export type StoryWorkspaceEpisodeBindingRecoveryOptions =
  StoryWorkspaceEpisodeActionFetchOptions;

export interface StoryWorkspaceEpisodeActionContinueOptions
  extends StoryWorkspaceEpisodeActionFetchOptions {
  readonly actionId?: string;
  readonly userGuidance?: string | null;
}

function storyWorkspaceEpisodeActionIdempotencyKey(value: unknown): string {
  if (typeof value !== 'string' || !STORY_WORKSPACE_EPISODE_IDEMPOTENCY_KEY.test(value)) {
    throw new StoryWorkspaceEpisodeActionUnavailableError();
  }
  return value;
}

function storyWorkspaceEpisodeActionGuidance(value: unknown): string | null {
  if (value === undefined || value === null) return null;
  if (typeof value !== 'string') throw new StoryWorkspaceEpisodeActionUnavailableError();
  const trimmed = value.trim();
  if (trimmed.length === 0) return null;
  if (
    [...trimmed].length > 2000
    || [...trimmed].some((character) => {
      const code = character.charCodeAt(0);
      return code < 32 && code !== 9 && code !== 10;
    })
    || STORY_WORKSPACE_EPISODE_GUIDANCE_DENYLIST.some((pattern) => pattern.test(trimmed))
  ) throw new StoryWorkspaceEpisodeActionUnavailableError();
  return trimmed;
}

function storyWorkspaceEpisodeActionHeaders(
  token: string | null | undefined,
  etag?: string,
): Headers {
  const headers = new Headers({
    Accept: 'application/json',
    'Content-Type': 'application/json',
  });
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (etag !== undefined) headers.set('If-Match', storyWorkspaceEpisodeQuotedEtag(etag));
  return headers;
}

async function storyWorkspacePostEpisodeAction(
  endpoint: string,
  body: StoryWorkspaceEpisodeBindingRecoveryRequest
    | StoryWorkspaceEpisodeActionContinueRequest
    | StoryWorkspaceEpisodeActionContinueRequestV2,
  options: StoryWorkspaceEpisodeActionFetchOptions,
  etag?: string,
): Promise<StoryWorkspaceEpisodeActionAccepted> {
  const response = await (options.fetchImpl ?? fetch)(endpoint, {
    method: 'POST',
    credentials: 'include',
    headers: storyWorkspaceEpisodeActionHeaders(options.token, etag),
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new StoryWorkspaceEpisodeActionHttpError(response.status);
  if (response.status !== 202) throw new StoryWorkspaceEpisodeActionContractError();
  let payload: unknown;
  try {
    payload = await response.json();
    return storyWorkspaceParseEpisodeActionAccepted(payload);
  } catch (error) {
    if (error instanceof StoryWorkspaceEpisodeActionContractError) throw error;
    throw new StoryWorkspaceEpisodeActionContractError();
  }
}

function storyWorkspaceEpisodeActionRunMatches(
  runId: string,
  surface: StoryWorkspaceEpisodeArtifactSurface,
): boolean {
  return STORY_WORKSPACE_EPISODE_RUN_ID.test(runId) && surface.runId === runId;
}

export async function storyWorkspaceRecoverEpisodeBinding(
  runId: string,
  surface: StoryWorkspaceEpisodeArtifactSurface,
  options: StoryWorkspaceEpisodeBindingRecoveryOptions,
): Promise<StoryWorkspaceEpisodeActionAccepted> {
  if (
    !storyWorkspaceEpisodeActionRunMatches(runId, surface)
    || surface.bindingAvailability !== 'unbound'
    || surface.workflow !== null
    || !surface.bindingRecovery.canDispatch
  ) throw new StoryWorkspaceEpisodeActionUnavailableError();
  const body: StoryWorkspaceEpisodeBindingRecoveryRequest = {
    idempotencyKey: storyWorkspaceEpisodeActionIdempotencyKey(options.idempotencyKey),
  };
  const accepted = await storyWorkspacePostEpisodeAction(
    storyWorkspaceEpisodeBindingRecoveryEndpoint(runId),
    body,
    options,
  );
  if (
    accepted.runId !== runId
    || accepted.episodeId !== null
    || accepted.capability !== 'recover_first_episode_binding'
  ) throw new StoryWorkspaceEpisodeActionContractError();
  return accepted;
}

export async function storyWorkspaceContinueEpisodeAction(
  runId: string,
  surface: StoryWorkspaceEpisodeArtifactSurface,
  options: StoryWorkspaceEpisodeActionContinueOptions,
): Promise<StoryWorkspaceEpisodeActionAccepted> {
  const actionProjection = surface.actionProjection ?? null;
  if (actionProjection !== null) {
    const selected = actionProjection.actionOptions.find(
      (option) => option.actionId === options.actionId,
    );
    const etag = surface.etag;
    if (
      !storyWorkspaceEpisodeActionRunMatches(runId, surface)
      || surface.bindingAvailability !== 'bound'
      || selected === undefined
      || selected.availability !== 'executable'
      || !selected.canDispatch
      || selected.dispatchState !== 'idle'
      || etag === null
      || !STORY_WORKSPACE_EPISODE_REVISION.test(etag)
    ) throw new StoryWorkspaceEpisodeActionUnavailableError();
    const body: StoryWorkspaceEpisodeActionContinueRequestV2 = {
      actionId: selected.actionId,
      idempotencyKey: storyWorkspaceEpisodeActionIdempotencyKey(options.idempotencyKey),
      userGuidance: storyWorkspaceEpisodeActionGuidance(options.userGuidance),
    };
    const accepted = await storyWorkspacePostEpisodeAction(
      storyWorkspaceEpisodeActionContinueEndpoint(runId),
      body,
      options,
      etag,
    );
    const targetId = selected.targetEpisode.opaqueEpisodeId;
    if (
      accepted.runId !== runId
      || accepted.capability !== selected.action
      || (
        targetId !== null
          ? accepted.episodeId !== targetId
          : accepted.episodeId === null
            || !STORY_WORKSPACE_EPISODE_HEX_ID.test(accepted.episodeId)
      )
    ) throw new StoryWorkspaceEpisodeActionContractError();
    return accepted;
  }
  const action = surface.workflow?.nextAction.action;
  const episodeId = surface.opaqueEpisodeId;
  const etag = surface.etag;
  if (
    !storyWorkspaceEpisodeActionRunMatches(runId, surface)
    || surface.bindingAvailability !== 'bound'
    || surface.workflow === null
    || !surface.workflow.nextAction.canDispatch
    || action === undefined
    || action === 'none_in_scope'
    || episodeId === null
    || !STORY_WORKSPACE_EPISODE_HEX_ID.test(episodeId)
    || etag === null
    || !STORY_WORKSPACE_EPISODE_REVISION.test(etag)
  ) throw new StoryWorkspaceEpisodeActionUnavailableError();
  const body: StoryWorkspaceEpisodeActionContinueRequest = {
    episodeId,
    action: action as StoryWorkspaceEpisodeDispatchAction,
    idempotencyKey: storyWorkspaceEpisodeActionIdempotencyKey(options.idempotencyKey),
    userGuidance: storyWorkspaceEpisodeActionGuidance(options.userGuidance),
  };
  const accepted = await storyWorkspacePostEpisodeAction(
    storyWorkspaceEpisodeActionContinueEndpoint(runId),
    body,
    options,
    etag,
  );
  if (
    accepted.runId !== runId
    || accepted.episodeId !== episodeId
    || accepted.capability !== action
  ) throw new StoryWorkspaceEpisodeActionContractError();
  return accepted;
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

export interface StoryWorkspaceEpisodeArtifactsRequestTicket {
  readonly runId: string;
  readonly generation: number;
  readonly signal: AbortSignal;
}

export interface StoryWorkspaceEpisodeArtifactsRequestLifecycle {
  activate: (runId: string | null) => void;
  begin: (runId: string) => StoryWorkspaceEpisodeArtifactsRequestTicket;
  shouldCommit: (ticket: StoryWorkspaceEpisodeArtifactsRequestTicket) => boolean;
  commitEtag: (ticket: StoryWorkspaceEpisodeArtifactsRequestTicket, etag: string | null) => boolean;
  etagFor: (runId: string) => string | null;
  cleanup: () => void;
}

/**
 * Mounted request lifecycle shared by the hook and its Node seam. It owns the
 * AbortController, generation, run-local ETag, and late-response commit gate.
 */
export function storyWorkspaceCreateEpisodeArtifactsRequestLifecycle(
  initialRunId: string | null,
): StoryWorkspaceEpisodeArtifactsRequestLifecycle {
  let generation = 0;
  let currentRunId = initialRunId;
  let mounted = true;
  let etag: string | null = null;
  let controller: AbortController | null = null;

  const moveToRun = (runId: string | null) => {
    if (currentRunId === runId) return;
    controller?.abort();
    controller = null;
    generation += 1;
    currentRunId = runId;
    etag = null;
  };
  const shouldCommit = (ticket: StoryWorkspaceEpisodeArtifactsRequestTicket) => (
    mounted && storyWorkspaceShouldCommitEpisodeArtifactsResponse({
      signal: ticket.signal,
      requestRunId: ticket.runId,
      currentRunId,
      requestGeneration: ticket.generation,
      currentGeneration: generation,
    })
  );

  return {
    activate(runId) {
      moveToRun(runId);
      mounted = true;
    },
    begin(runId) {
      if (!mounted) throw new Error('Episode artifact request lifecycle is inactive.');
      moveToRun(runId);
      controller?.abort();
      controller = new AbortController();
      generation += 1;
      return { runId, generation, signal: controller.signal };
    },
    shouldCommit,
    commitEtag(ticket, value) {
      if (!shouldCommit(ticket)) return false;
      etag = value;
      return true;
    },
    etagFor(runId) {
      return mounted && currentRunId === runId ? etag : null;
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
  const lifecycleRef = useRef<StoryWorkspaceEpisodeArtifactsRequestLifecycle | null>(null);
  const renderedRunIdRef = useRef<string | null>(normalizedRunId);
  if (lifecycleRef.current === null) {
    lifecycleRef.current = storyWorkspaceCreateEpisodeArtifactsRequestLifecycle(normalizedRunId);
  }
  const lifecycle = lifecycleRef.current;

  const refresh = useCallback(() => {
    if (!normalizedRunId) return;
    const ticket = lifecycle.begin(normalizedRunId);
    dispatch({ type: 'start', runId: normalizedRunId, generation: ticket.generation });
    void storyWorkspaceFetchEpisodeArtifacts(
      apiUrl(storyWorkspaceEpisodeArtifactsEndpoint(normalizedRunId)),
      {
        fetchImpl: options.fetchImpl,
        token: options.token === undefined ? getAuthToken() : options.token,
        etag: lifecycle.etagFor(normalizedRunId),
        expectedRunId: normalizedRunId,
        signal: ticket.signal,
      },
    ).then((result) => {
      if (!lifecycle.shouldCommit(ticket)) return;
      if (result.kind === 'not-modified') {
        dispatch({
          type: 'not-modified',
          runId: normalizedRunId,
          generation: ticket.generation,
        });
        return;
      }
      if (!lifecycle.commitEtag(ticket, result.data.etag)) return;
      dispatch({
        type: 'success',
        runId: normalizedRunId,
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
        generation: ticket.generation,
        error: reason instanceof Error
          ? reason
          : new Error('Episode artifact request failed.'),
      });
    });
  }, [lifecycle, normalizedRunId, options.fetchImpl, options.token]);

  useEffect(() => {
    lifecycle.activate(normalizedRunId);
    if (renderedRunIdRef.current !== normalizedRunId) {
      renderedRunIdRef.current = normalizedRunId;
      dispatch({ type: 'reset', runId: normalizedRunId });
    }
    if (normalizedRunId) refresh();
    return () => lifecycle.cleanup();
  }, [lifecycle, normalizedRunId, refresh]);

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
    unavailableArtifactKeys: state.runId === normalizedRunId
      ? state.unavailableArtifactKeys
      : [],
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
