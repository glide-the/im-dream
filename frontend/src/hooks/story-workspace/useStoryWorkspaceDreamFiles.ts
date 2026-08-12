// [Input] Run-scoped Dream file REST projections and story-workspace output notices.
// [Output] Strict parser/fetch/reducer seams plus useStoryWorkspaceDreamFiles().
// [Pos] story-workspace hooks node - Dream workspace file read boundary (Task 3 F2)
// [Sync] 2026-08-04: initial implementation; REST is authoritative, SSE only invalidates.

import { useCallback, useEffect, useReducer, useRef } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import type {
  StoryWorkspaceDreamAgentActivityProjection,
  StoryWorkspaceDreamFilesResponse,
  StoryWorkspaceDreamLifecycleState,
  StoryWorkspaceDreamSource,
  StoryWorkspaceDreamStage,
  StoryWorkspaceDreamStageItem,
  StoryWorkspaceDreamStagePage,
  StoryWorkspaceDreamStageProjection,
} from './contracts';

const REQUIRED_STAGES = ['characters', 'scenes', 'storyboards'] as const;
const RUN_ID_PATTERN = /^run_[0-9a-f]{32}$/;
const DREAM_OUTPUT_EVENT = 'ink:story-workspace-output';
const AGENT_ACTIVITY_KINDS = new Set([
  'activity_started_hint',
  'activity_settled_hint',
  'waiting_confirmation_hint',
  'turn_settled_hint',
  'reconcile_requested',
]);
const AGENT_OPERATION_SCOPES = new Set([
  'tool',
  'subagent',
  'content_generation',
  'workflow_operation',
]);
const AGENT_OPERATION_STATES = new Set([
  'started',
  'waiting_confirmation',
  'succeeded',
  'failed',
]);
const AGENT_TERMINAL_OUTCOMES = new Set(['completed', 'failed', 'cancelled']);
const SHA256_HEX_PATTERN = /^[0-9a-f]{64}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requiredString(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error(`Dream files response has invalid ${field}.`);
  }
  return value;
}

function integer(value: unknown, field: string, minimum: number): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < minimum) {
    throw new Error(`Dream files response has invalid ${field}.`);
  }
  return value;
}

function stringArray(value: unknown, field: string, allowEmpty = true): string[] {
  if (
    !Array.isArray(value)
    || (!allowEmpty && value.length === 0)
    || value.some((item) => typeof item !== 'string' || item.length === 0)
    || new Set(value).size !== value.length
  ) {
    throw new Error(`Dream files response has invalid ${field}.`);
  }
  return [...value];
}

function parseSource(value: unknown): StoryWorkspaceDreamSource {
  if (!isRecord(value)) throw new Error('Dream files response has invalid source.');
  return {
    deckPluginBindingId: requiredString(value.deckPluginBindingId, 'source.deckPluginBindingId'),
    bindingRevision: integer(value.bindingRevision, 'source.bindingRevision', 1),
    deckPluginVersion: requiredString(value.deckPluginVersion, 'source.deckPluginVersion'),
    deckRuntimeSnapshotId: requiredString(
      value.deckRuntimeSnapshotId,
      'source.deckRuntimeSnapshotId',
    ),
    runtimePluginLockId: requiredString(value.runtimePluginLockId, 'source.runtimePluginLockId'),
  };
}

function stageRoute(stage: StoryWorkspaceDreamStage, runId: string): string {
  if (stage === 'characters') return `/story-workspace/characters?run=${runId}`;
  if (stage === 'scenes') return `/story-workspace/scenes?run=${runId}`;
  return `/story-workspace/runs/${runId}/execution`;
}

function stageTitle(stage: StoryWorkspaceDreamStage): string {
  if (stage === 'characters') return '人物';
  if (stage === 'scenes') return '场景';
  return '分镜';
}

function parsePage(
  value: unknown,
  stage: StoryWorkspaceDreamStage,
  runId: string,
): StoryWorkspaceDreamStagePage {
  if (!isRecord(value)) throw new Error('Dream stage has invalid page.');
  const page = {
    title: requiredString(value.title, 'stage.page.title'),
    entryRoute: requiredString(value.entryRoute, 'stage.page.entryRoute'),
  };
  if (page.title !== stageTitle(stage) || page.entryRoute !== stageRoute(stage, runId)) {
    throw new Error('Dream stage page is not canonical.');
  }
  return page;
}

function parseItem(value: unknown, sourceFiles: readonly string[]): StoryWorkspaceDreamStageItem {
  if (!isRecord(value)) throw new Error('Dream stage has invalid item.');
  const sourceFile = requiredString(value.sourceFile, 'stage.item.sourceFile');
  if (!sourceFiles.includes(sourceFile)) {
    throw new Error('Dream stage item sourceFile is not declared.');
  }
  const summary = value.summary;
  if (summary !== null && typeof summary !== 'string') {
    throw new Error('Dream stage item has invalid summary.');
  }
  return {
    entityId: requiredString(value.entityId, 'stage.item.entityId'),
    displayName: requiredString(value.displayName, 'stage.item.displayName'),
    summary,
    sourceFile,
    relations: stringArray(value.relations, 'stage.item.relations'),
  };
}

function parseStage(
  value: unknown,
  expectedStage: StoryWorkspaceDreamStage,
  runId: string,
): StoryWorkspaceDreamStageProjection {
  if (!isRecord(value) || value.stage !== expectedStage) {
    throw new Error('Dream stage key and value do not match.');
  }
  const sourceFiles = stringArray(value.sourceFiles, 'stage.sourceFiles', false);
  if (!Array.isArray(value.items)) throw new Error('Dream stage has invalid items.');
  const items = value.items.map((item) => parseItem(item, sourceFiles));
  if (new Set(items.map((item) => item.entityId)).size !== items.length) {
    throw new Error('Dream stage entityId values must be unique.');
  }
  return {
    stage: expectedStage,
    revision: integer(value.revision, 'stage.revision', 1),
    sourceFiles,
    page: parsePage(value.page, expectedStage, runId),
    items,
  };
}

function nullableEnum(
  value: unknown,
  allowed: ReadonlySet<string>,
  field: string,
): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'string' || !allowed.has(value)) {
    throw new Error(`Dream files response has invalid ${field}.`);
  }
  return value;
}

function nullableSha256(value: unknown, field: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'string' || !SHA256_HEX_PATTERN.test(value)) {
    throw new Error(`Dream files response has invalid ${field}.`);
  }
  return value;
}

function parseAgentActivity(value: unknown): StoryWorkspaceDreamAgentActivityProjection | null {
  if (value === null || value === undefined) return null;
  if (!isRecord(value) || typeof value.activity !== 'string'
    || !AGENT_ACTIVITY_KINDS.has(value.activity)) {
    throw new Error('Dream files response has invalid agentActivity.');
  }
  const terminalOutcome = nullableEnum(
    value.terminalOutcome,
    AGENT_TERMINAL_OUTCOMES,
    'agentActivity.terminalOutcome',
  ) as StoryWorkspaceDreamAgentActivityProjection['terminalOutcome'];
  const operationScope = nullableEnum(
    value.operationScope,
    AGENT_OPERATION_SCOPES,
    'agentActivity.operationScope',
  ) as StoryWorkspaceDreamAgentActivityProjection['operationScope'];
  const operationState = nullableEnum(
    value.operationState,
    AGENT_OPERATION_STATES,
    'agentActivity.operationState',
  ) as StoryWorkspaceDreamAgentActivityProjection['operationState'];
  const operationId = nullableSha256(
    value.operationId,
    'agentActivity.operationId',
  );
  if (value.activity === 'turn_settled_hint') {
    if (
      terminalOutcome === null
      || operationScope !== null
      || operationState !== null
      || operationId !== null
    ) {
      throw new Error('Dream files response has inconsistent terminal agentActivity.');
    }
  } else if (terminalOutcome !== null) {
    throw new Error('Dream files response has inconsistent agentActivity terminal outcome.');
  }
  if (typeof value.needsReconcile !== 'boolean'
    || value.needsReconcile !== (value.activity === 'reconcile_requested')) {
    throw new Error('Dream files response has inconsistent agentActivity reconciliation.');
  }
  if (value.activity === 'reconcile_requested') {
    if (operationScope !== null || operationState !== null || operationId !== null) {
      throw new Error('Dream files response has inconsistent reconciliation operation.');
    }
  } else if (value.activity !== 'turn_settled_hint') {
    const validOperationStates: Record<string, ReadonlySet<string>> = {
      activity_started_hint: new Set(['started']),
      activity_settled_hint: new Set(['succeeded', 'failed']),
      waiting_confirmation_hint: new Set(['waiting_confirmation']),
    };
    if (
      operationScope === null
      || operationState === null
      || !validOperationStates[value.activity]?.has(operationState)
    ) {
      throw new Error('Dream files response has inconsistent agentActivity operation.');
    }
  }
  return {
    activity: value.activity as StoryWorkspaceDreamAgentActivityProjection['activity'],
    sequence: integer(value.sequence, 'agentActivity.sequence', -1),
    terminalOutcome,
    needsReconcile: value.needsReconcile,
    operationScope,
    operationState,
    operationId,
  };
}

function safeParseAgentActivity(
  value: unknown,
): StoryWorkspaceDreamAgentActivityProjection | null {
  try {
    return parseAgentActivity(value);
  } catch {
    // Observer hints are display-only. A malformed optional hint must never
    // discard the authorized threadId/files projection or block ChatPanel.
    return null;
  }
}

/** Validate the backend's explicit camelCase REST boundary before hydration. */
export function storyWorkspaceParseDreamFiles(value: unknown): StoryWorkspaceDreamFilesResponse {
  if (!isRecord(value)) throw new Error('Dream files response must be an object.');
  const runId = requiredString(value.storyWorkspaceRunId, 'storyWorkspaceRunId');
  if (!RUN_ID_PATTERN.test(runId)) throw new Error('Dream files response has invalid run id.');
  if (
    !Array.isArray(value.requiredStages)
    || value.requiredStages.length !== REQUIRED_STAGES.length
    || value.requiredStages.some((stage, index) => stage !== REQUIRED_STAGES[index])
  ) {
    throw new Error('Dream files response has invalid requiredStages.');
  }
  if (!isRecord(value.stages)) throw new Error('Dream files response has invalid stages.');

  const stages: Partial<Record<StoryWorkspaceDreamStage, StoryWorkspaceDreamStageProjection>> = {};
  for (const key of Object.keys(value.stages)) {
    if (!REQUIRED_STAGES.includes(key as StoryWorkspaceDreamStage)) {
      throw new Error('Dream files response contains an unknown stage.');
    }
    const stage = key as StoryWorkspaceDreamStage;
    stages[stage] = parseStage(value.stages[stage], stage, runId);
  }
  const runRevision = integer(value.runRevision, 'runRevision', 0);
  if (runRevision === 0 && Object.keys(stages).length > 0) {
    throw new Error('Waiting Dream projection cannot contain stage files.');
  }
  const complete = REQUIRED_STAGES.every((stage) => stages[stage] !== undefined);
  if (
    typeof value.confirmationAccepted !== 'boolean'
    || typeof value.confirmationDispatched !== 'boolean'
    || (value.confirmationDispatched && !value.confirmationAccepted)
  ) {
    throw new Error('Dream files response has inconsistent confirmation facts.');
  }
  const canConfirm = complete && !value.confirmationAccepted;
  if (typeof value.canConfirm !== 'boolean' || value.canConfirm !== canConfirm) {
    throw new Error('Dream files response has inconsistent canConfirm.');
  }
  if (value.confirmationLabel !== '确认并继续') {
    throw new Error('Dream files response has invalid confirmationLabel.');
  }
  return {
    storyWorkspaceRunId: runId,
    threadId: requiredString(value.threadId, 'threadId'),
    source: parseSource(value.source),
    requiredStages: [...REQUIRED_STAGES],
    runRevision,
    stages,
    confirmationAccepted: value.confirmationAccepted,
    confirmationDispatched: value.confirmationDispatched,
    canConfirm: value.canConfirm,
    confirmationLabel: '确认并继续',
    agentActivity: safeParseAgentActivity(value.agentActivity),
  };
}

export function storyWorkspaceDreamFilesEndpoint(runId: string): string {
  return `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/dream-files`;
}

export interface StoryWorkspaceDreamFilesFetchOptions {
  fetchImpl?: typeof fetch;
  token?: string | null;
  signal?: AbortSignal;
}

/** Fetch one authoritative Dream snapshot; HTTP/JSON/contract failures reject. */
export async function storyWorkspaceFetchDreamFiles(
  endpoint: string,
  options: StoryWorkspaceDreamFilesFetchOptions = {},
): Promise<StoryWorkspaceDreamFilesResponse> {
  const headers = new Headers({ Accept: 'application/json' });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);
  const response = await (options.fetchImpl ?? fetch)(endpoint, {
    credentials: 'include',
    headers,
    signal: options.signal ?? null,
  });
  if (!response.ok) throw new Error(`Dream files request failed (${response.status}).`);
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Dream files response is not valid JSON.');
  }
  return storyWorkspaceParseDreamFiles(payload);
}

export function storyWorkspaceShouldPollDreamFiles(
  state: StoryWorkspaceDreamLifecycleState,
): boolean {
  return state === 'story-workspace-dream-waiting-files'
    || state === 'story-workspace-dream-editing'
    || state === 'story-workspace-dream-running';
}

/** SSE notices carry identity only; their content never replaces a REST snapshot. */
export function storyWorkspaceShouldInvalidateDreamFiles(
  event: unknown,
  runId: string,
): boolean {
  if (!isRecord(event) || event.type !== 'story-workspace-output') return false;
  const eventRunId = event.runId ?? event.storyWorkspaceRunId;
  return typeof eventRunId === 'string' && eventRunId === runId;
}

export interface StoryWorkspaceDreamFilesFetchState {
  data: StoryWorkspaceDreamFilesResponse | null;
  error: Error | null;
  isLoading: boolean;
  generation: number;
}

export type StoryWorkspaceDreamFilesFetchAction =
  | { type: 'reset' }
  | { type: 'start'; generation: number }
  | { type: 'success'; generation: number; data: StoryWorkspaceDreamFilesResponse }
  | { type: 'error'; generation: number; error: Error };

const EMPTY_FETCH_STATE: StoryWorkspaceDreamFilesFetchState = {
  data: null,
  error: null,
  isLoading: false,
  generation: 0,
};

/** Pure stale-response gate; an error intentionally retains the last snapshot. */
export function storyWorkspaceReduceDreamFilesFetch(
  state: StoryWorkspaceDreamFilesFetchState,
  action: StoryWorkspaceDreamFilesFetchAction,
): StoryWorkspaceDreamFilesFetchState {
  if (action.type === 'reset') return EMPTY_FETCH_STATE;
  if (action.generation < state.generation) return state;
  if (action.type === 'start') {
    return { ...state, error: null, isLoading: true, generation: action.generation };
  }
  if (action.type === 'success') {
    return { data: action.data, error: null, isLoading: false, generation: action.generation };
  }
  return { ...state, error: action.error, isLoading: false, generation: action.generation };
}

export interface StoryWorkspaceDreamFilesUseOptions {
  lifecycleState: StoryWorkspaceDreamLifecycleState;
  enabled?: boolean;
  updatesEnabled?: boolean;
  pollIntervalMs?: number;
  fetchImpl?: typeof fetch;
  token?: string | null;
}

export interface StoryWorkspaceDreamFilesState {
  data: StoryWorkspaceDreamFilesResponse | null;
  error: Error | null;
  isLoading: boolean;
  refresh: () => void;
}

/**
 * Read Dream files for one run. Initial/poll/SSE/manual loads share the same
 * AbortController and monotonic generation so old responses cannot overwrite
 * a newer snapshot.
 */
export function useStoryWorkspaceDreamFiles(
  runId: string | null | undefined,
  options: StoryWorkspaceDreamFilesUseOptions,
): StoryWorkspaceDreamFilesState {
  const [state, dispatch] = useReducer(
    storyWorkspaceReduceDreamFilesFetch,
    EMPTY_FETCH_STATE,
  );
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const enabled = options.enabled !== false;
  const updatesEnabled = options.updatesEnabled ?? enabled;

  const refresh = useCallback(() => {
    if (!runId || !enabled) return;
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    generation.current += 1;
    const nextGeneration = generation.current;
    dispatch({ type: 'start', generation: nextGeneration });
    void storyWorkspaceFetchDreamFiles(apiUrl(storyWorkspaceDreamFilesEndpoint(runId)), {
      fetchImpl: options.fetchImpl,
      token: options.token === undefined ? getAuthToken() : options.token,
      signal: nextController.signal,
    }).then((data) => {
      if (!nextController.signal.aborted) {
        dispatch({ type: 'success', generation: nextGeneration, data });
      }
    }).catch((reason: unknown) => {
      if (!nextController.signal.aborted) {
        dispatch({
          type: 'error',
          generation: nextGeneration,
          error: reason instanceof Error ? reason : new Error('Dream files request failed.'),
        });
      }
    });
  }, [enabled, options.fetchImpl, options.token, runId]);

  useEffect(() => {
    controller.current?.abort();
    generation.current += 1;
    dispatch({ type: 'reset' });
  }, [runId]);

  useEffect(() => {
    if (!runId || !enabled) {
      controller.current?.abort();
      return;
    }
    refresh();
    return () => controller.current?.abort();
  }, [enabled, refresh, runId]);

  useEffect(() => {
    if (!runId || !updatesEnabled || !storyWorkspaceShouldPollDreamFiles(options.lifecycleState)) return;
    const intervalMs = Math.max(options.pollIntervalMs ?? 5000, 5000);
    const interval = window.setInterval(refresh, intervalMs);
    return () => window.clearInterval(interval);
  }, [options.lifecycleState, options.pollIntervalMs, refresh, runId, updatesEnabled]);

  useEffect(() => {
    if (!runId || !updatesEnabled) return;
    const handleOutput = (event: Event) => {
      const detail = (event as CustomEvent<unknown>).detail;
      if (storyWorkspaceShouldInvalidateDreamFiles(detail, runId)) refresh();
    };
    window.addEventListener(DREAM_OUTPUT_EVENT, handleOutput);
    return () => window.removeEventListener(DREAM_OUTPUT_EVENT, handleOutput);
  }, [refresh, runId, updatesEnabled]);

  return {
    data: state.data,
    error: state.error,
    isLoading: state.isLoading,
    refresh,
  };
}
