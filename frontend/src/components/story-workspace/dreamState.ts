// [Input] Actor-scoped Dream stage snapshots plus local field edit/reset and
//         lifecycle commands.
// [Output] A pure, immutable local-draft state and the single camelCase Dream
//          confirmation payload consumed by the future page/API adapter.
// [Pos] Story Workspace Dream state seam (Task 3 F1); this file deliberately
//       owns no REST contract and imports neither React nor canonical types.
// [Sync] 2026-08-04: initial design_006/design_007 five-state implementation.

export const STORY_WORKSPACE_DREAM_STAGES = [
  'characters',
  'scenes',
  'storyboards',
] as const;

export type StoryWorkspaceDreamStage = typeof STORY_WORKSPACE_DREAM_STAGES[number];

export const STORY_WORKSPACE_DREAM_STATES = [
  'waiting-files',
  'editing',
  'confirming',
  'continuing',
  'completed',
] as const;

export type StoryWorkspaceDreamStatus = typeof STORY_WORKSPACE_DREAM_STATES[number];

export type StoryWorkspaceDreamFieldValue =
  | string
  | number
  | boolean
  | null
  | readonly StoryWorkspaceDreamFieldValue[]
  | { readonly [key: string]: StoryWorkspaceDreamFieldValue };

export interface StoryWorkspaceDreamStageItemSnapshot {
  entityId: string;
  fields: Readonly<Record<string, StoryWorkspaceDreamFieldValue>>;
  editableFields: readonly string[];
}

/**
 * Pure seam input shaped for state hydration, not the canonical REST contract.
 * An adapter may map the eventual hooks/story-workspace contract into it.
 */
export interface StoryWorkspaceDreamStageSnapshot {
  stage: StoryWorkspaceDreamStage;
  revision: number;
  items: readonly StoryWorkspaceDreamStageItemSnapshot[];
}

interface StoryWorkspaceDreamHydratedItem {
  entityId: string;
  fields: Readonly<Record<string, StoryWorkspaceDreamFieldValue>>;
  editableFields: readonly string[];
}

interface StoryWorkspaceDreamHydratedStage {
  stage: StoryWorkspaceDreamStage;
  revision: number;
  items: readonly StoryWorkspaceDreamHydratedItem[];
}

interface StoryWorkspaceDreamLocalEdit {
  stage: StoryWorkspaceDreamStage;
  entityId: string;
  field: string;
  value: StoryWorkspaceDreamFieldValue;
}

export interface StoryWorkspaceDreamConfirmationEdit {
  stage: StoryWorkspaceDreamStage;
  entityId: string;
  fields: Readonly<Record<string, StoryWorkspaceDreamFieldValue>>;
}

export interface StoryWorkspaceDreamConfirmationPayload {
  storyWorkspaceRunId: string;
  threadId: string;
  baseRevisions: Readonly<Record<StoryWorkspaceDreamStage, number>>;
  edits: readonly StoryWorkspaceDreamConfirmationEdit[];
  idempotencyKey: string;
}

export interface StoryWorkspaceDreamState {
  status: StoryWorkspaceDreamStatus;
  storyWorkspaceRunId: string;
  threadId: string;
  availableStages: readonly StoryWorkspaceDreamStage[];
  baseRevisions: Readonly<Partial<Record<StoryWorkspaceDreamStage, number>>>;
  latestRevisions: Readonly<Partial<Record<StoryWorkspaceDreamStage, number>>>;
  dirtyCount: number;
  workspaceUpdatedStages: readonly StoryWorkspaceDreamStage[];
  staleStages: readonly StoryWorkspaceDreamStage[];
  hasRevisionConflict: boolean;
  confirmationPayload: StoryWorkspaceDreamConfirmationPayload | null;
  /** Internal seam data; page components should use the exported operations. */
  readonly stageData: Readonly<Partial<Record<StoryWorkspaceDreamStage, StoryWorkspaceDreamHydratedStage>>>;
  /** Internal seam data; one row represents one locally changed field. */
  readonly localEdits: readonly StoryWorkspaceDreamLocalEdit[];
}

export interface StoryWorkspaceDreamConfirmationStart {
  state: StoryWorkspaceDreamState;
  payload: StoryWorkspaceDreamConfirmationPayload;
}

const STAGE_ORDER: Readonly<Record<StoryWorkspaceDreamStage, number>> = {
  characters: 0,
  scenes: 1,
  storyboards: 2,
};

const FORBIDDEN_FIELD_NAMES: ReadonlySet<string> = new Set([
  '__proto__',
  'constructor',
  'prototype',
]);

function orderedStages(stages: ReadonlySet<StoryWorkspaceDreamStage>): StoryWorkspaceDreamStage[] {
  return STORY_WORKSPACE_DREAM_STAGES.filter((stage) => stages.has(stage));
}

function availableStages(
  stageData: StoryWorkspaceDreamState['stageData'],
): StoryWorkspaceDreamStage[] {
  return STORY_WORKSPACE_DREAM_STAGES.filter((stage) => stageData[stage] !== undefined);
}

function isComplete(
  stageData: StoryWorkspaceDreamState['stageData'],
): boolean {
  return STORY_WORKSPACE_DREAM_STAGES.every((stage) => stageData[stage] !== undefined);
}

function deriveStatus(
  status: StoryWorkspaceDreamStatus,
  stageData: StoryWorkspaceDreamState['stageData'],
): StoryWorkspaceDreamStatus {
  if (status !== 'waiting-files' && status !== 'editing') return status;
  return isComplete(stageData) ? 'editing' : 'waiting-files';
}

function hasOwn(value: object, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function isJsonValue(value: unknown, ancestors: ReadonlySet<object> = new Set()): value is StoryWorkspaceDreamFieldValue {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return true;
  if (typeof value === 'number') return Number.isFinite(value);
  if (typeof value !== 'object') return false;
  if (ancestors.has(value)) return false;

  const nextAncestors = new Set(ancestors);
  nextAncestors.add(value);
  if (Array.isArray(value)) {
    return value.every((item) => isJsonValue(item, nextAncestors));
  }

  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) return false;
  return Object.entries(value).every(([key, item]) => (
    !FORBIDDEN_FIELD_NAMES.has(key) && isJsonValue(item, nextAncestors)
  ));
}

function cloneValue(value: StoryWorkspaceDreamFieldValue): StoryWorkspaceDreamFieldValue {
  if (Array.isArray(value)) return value.map((item) => cloneValue(item));
  if (value !== null && typeof value === 'object') {
    const clone: Record<string, StoryWorkspaceDreamFieldValue> = {};
    for (const [key, item] of Object.entries(value)) clone[key] = cloneValue(item);
    return clone;
  }
  return value;
}

function equalValues(
  left: StoryWorkspaceDreamFieldValue,
  right: StoryWorkspaceDreamFieldValue,
): boolean {
  if (Object.is(left, right)) return true;
  if (Array.isArray(left) || Array.isArray(right)) {
    return Array.isArray(left)
      && Array.isArray(right)
      && left.length === right.length
      && left.every((item, index) => equalValues(item, right[index]));
  }
  if (left === null || right === null || typeof left !== 'object' || typeof right !== 'object') {
    return false;
  }

  const leftRecord = left as Readonly<Record<string, StoryWorkspaceDreamFieldValue>>;
  const rightRecord = right as Readonly<Record<string, StoryWorkspaceDreamFieldValue>>;
  const leftKeys = Object.keys(leftRecord).sort();
  const rightKeys = Object.keys(rightRecord).sort();
  return leftKeys.length === rightKeys.length
    && leftKeys.every((key, index) => (
      key === rightKeys[index]
      && hasOwn(rightRecord, key)
      && equalValues(leftRecord[key], rightRecord[key])
    ));
}

function validateFieldName(field: string): void {
  if (field.trim() === '' || FORBIDDEN_FIELD_NAMES.has(field)) {
    throw new Error(`Dream field "${field}" is not a safe editable field`);
  }
}

function hydrateItem(
  item: StoryWorkspaceDreamStageItemSnapshot,
  seenEntityIds: Set<string>,
): StoryWorkspaceDreamHydratedItem {
  if (item.entityId.trim() === '') throw new Error('Dream entityId must not be empty');
  if (seenEntityIds.has(item.entityId)) {
    throw new Error(`Duplicate Dream entityId: ${item.entityId}`);
  }
  seenEntityIds.add(item.entityId);

  if (!isJsonValue(item.fields)) throw new Error(`Dream fields for ${item.entityId} must be JSON values`);

  const fields: Record<string, StoryWorkspaceDreamFieldValue> = {};
  for (const [field, value] of Object.entries(item.fields)) {
    validateFieldName(field);
    fields[field] = cloneValue(value);
  }

  const editableFields = [...new Set(item.editableFields)];
  for (const field of editableFields) {
    validateFieldName(field);
    if (!hasOwn(fields, field)) {
      throw new Error(`Editable Dream field "${field}" is missing from ${item.entityId}`);
    }
  }

  return {
    entityId: item.entityId,
    fields,
    editableFields,
  };
}

function validateAndCloneStage(
  snapshot: StoryWorkspaceDreamStageSnapshot,
): StoryWorkspaceDreamHydratedStage {
  if (!STORY_WORKSPACE_DREAM_STAGES.includes(snapshot.stage)) {
    throw new Error(`Unknown Dream stage: ${String(snapshot.stage)}`);
  }
  if (!Number.isSafeInteger(snapshot.revision) || snapshot.revision < 1) {
    throw new Error(`Dream stage revision must be a positive safe integer: ${snapshot.revision}`);
  }

  const seenEntityIds = new Set<string>();
  return {
    stage: snapshot.stage,
    revision: snapshot.revision,
    items: snapshot.items.map((item) => hydrateItem(item, seenEntityIds)),
  };
}

function findItem(
  state: StoryWorkspaceDreamState,
  stage: StoryWorkspaceDreamStage,
  entityId: string,
): StoryWorkspaceDreamHydratedItem {
  const stageSnapshot = state.stageData[stage];
  if (stageSnapshot === undefined) throw new Error(`Dream stage ${stage} is not available`);
  const item = stageSnapshot.items.find((candidate) => candidate.entityId === entityId);
  if (item === undefined) throw new Error(`Dream entity ${entityId} is not available in ${stage}`);
  return item;
}

function findLocalEdit(
  state: StoryWorkspaceDreamState,
  stage: StoryWorkspaceDreamStage,
  entityId: string,
  field: string,
): StoryWorkspaceDreamLocalEdit | undefined {
  return state.localEdits.find((edit) => (
    edit.stage === stage && edit.entityId === entityId && edit.field === field
  ));
}

function stageHasLocalEdits(
  localEdits: readonly StoryWorkspaceDreamLocalEdit[],
  stage: StoryWorkspaceDreamStage,
): boolean {
  return localEdits.some((edit) => edit.stage === stage);
}

function withDerivedState(
  state: StoryWorkspaceDreamState,
  updates: Partial<StoryWorkspaceDreamState>,
): StoryWorkspaceDreamState {
  const stageData = updates.stageData ?? state.stageData;
  const localEdits = updates.localEdits ?? state.localEdits;
  const staleStages = updates.staleStages ?? state.staleStages;
  return {
    ...state,
    ...updates,
    status: deriveStatus(updates.status ?? state.status, stageData),
    availableStages: availableStages(stageData),
    dirtyCount: localEdits.length,
    hasRevisionConflict: staleStages.length > 0,
    stageData,
    localEdits,
    staleStages,
  };
}

export function createStoryWorkspaceDreamState({
  storyWorkspaceRunId,
  threadId,
}: {
  storyWorkspaceRunId: string;
  threadId: string;
}): StoryWorkspaceDreamState {
  if (storyWorkspaceRunId.trim() === '') throw new Error('storyWorkspaceRunId must not be empty');
  if (threadId.trim() === '') throw new Error('threadId must not be empty');
  return {
    status: 'waiting-files',
    storyWorkspaceRunId,
    threadId,
    availableStages: [],
    baseRevisions: {},
    latestRevisions: {},
    dirtyCount: 0,
    workspaceUpdatedStages: [],
    staleStages: [],
    hasRevisionConflict: false,
    confirmationPayload: null,
    stageData: {},
    localEdits: [],
  };
}

function hydrateOneStage(
  state: StoryWorkspaceDreamState,
  snapshot: StoryWorkspaceDreamStageSnapshot,
): StoryWorkspaceDreamState {
  const incoming = validateAndCloneStage(snapshot);
  const current = state.stageData[incoming.stage];
  if (current !== undefined && incoming.revision <= current.revision) return state;

  const stageData = { ...state.stageData, [incoming.stage]: incoming };
  const latestRevisions = { ...state.latestRevisions, [incoming.stage]: incoming.revision };
  const baseRevisions = { ...state.baseRevisions };
  const workspaceUpdated = new Set(state.workspaceUpdatedStages);
  const stale = new Set(state.staleStages);
  const isServerUpdate = current !== undefined;

  if (isServerUpdate) workspaceUpdated.add(incoming.stage);
  if (isServerUpdate && stageHasLocalEdits(state.localEdits, incoming.stage)) {
    stale.add(incoming.stage);
  } else {
    baseRevisions[incoming.stage] = incoming.revision;
    stale.delete(incoming.stage);
  }

  return withDerivedState(state, {
    stageData,
    latestRevisions,
    baseRevisions,
    workspaceUpdatedStages: orderedStages(workspaceUpdated),
    staleStages: orderedStages(stale),
  });
}

/**
 * Merge full or partial REST refreshes. Lower/same revisions are ignored.
 * Newer server data replaces clean fields; local edits stay in localEdits and
 * therefore win reads until reset, while the stage becomes revision-stale.
 */
export function hydrateStoryWorkspaceDreamState(
  state: StoryWorkspaceDreamState,
  snapshots: readonly StoryWorkspaceDreamStageSnapshot[],
): StoryWorkspaceDreamState {
  return snapshots.reduce(hydrateOneStage, state);
}

export function readStoryWorkspaceDreamField(
  state: StoryWorkspaceDreamState,
  stage: StoryWorkspaceDreamStage,
  entityId: string,
  field: string,
): StoryWorkspaceDreamFieldValue {
  const localEdit = findLocalEdit(state, stage, entityId, field);
  if (localEdit !== undefined) return cloneValue(localEdit.value);

  const item = findItem(state, stage, entityId);
  if (!hasOwn(item.fields, field)) {
    throw new Error(`Dream field ${field} is not available on ${entityId}`);
  }
  return cloneValue(item.fields[field]);
}

function assertLocallyEditable(state: StoryWorkspaceDreamState): void {
  if (state.status !== 'waiting-files' && state.status !== 'editing') {
    throw new Error(`Dream fields cannot be edited while ${state.status}`);
  }
}

function rebaseCleanStage(
  state: StoryWorkspaceDreamState,
  localEdits: readonly StoryWorkspaceDreamLocalEdit[],
  stage: StoryWorkspaceDreamStage,
): Pick<StoryWorkspaceDreamState, 'baseRevisions' | 'staleStages'> {
  if (stageHasLocalEdits(localEdits, stage)) {
    return {
      baseRevisions: state.baseRevisions,
      staleStages: state.staleStages,
    };
  }

  const latestRevision = state.latestRevisions[stage];
  const baseRevisions = latestRevision === undefined
    ? state.baseRevisions
    : { ...state.baseRevisions, [stage]: latestRevision };
  const staleStages = state.staleStages.filter((candidate) => candidate !== stage);
  return { baseRevisions, staleStages };
}

export function editStoryWorkspaceDreamField(
  state: StoryWorkspaceDreamState,
  stage: StoryWorkspaceDreamStage,
  entityId: string,
  field: string,
  value: StoryWorkspaceDreamFieldValue,
): StoryWorkspaceDreamState {
  assertLocallyEditable(state);
  const item = findItem(state, stage, entityId);
  validateFieldName(field);
  if (!item.editableFields.includes(field)) {
    throw new Error(`Dream field "${field}" is not editable for ${entityId}`);
  }
  if (!isJsonValue(value)) throw new Error(`Dream field "${field}" must be a finite JSON value`);

  const withoutField = state.localEdits.filter((edit) => !(
    edit.stage === stage && edit.entityId === entityId && edit.field === field
  ));
  const serverValue = item.fields[field];
  const localEdits = equalValues(value, serverValue)
    ? withoutField
    : [...withoutField, { stage, entityId, field, value: cloneValue(value) }];
  const rebase = rebaseCleanStage(state, localEdits, stage);

  return withDerivedState(state, {
    localEdits,
    ...rebase,
  });
}

export function resetStoryWorkspaceDreamField(
  state: StoryWorkspaceDreamState,
  stage: StoryWorkspaceDreamStage,
  entityId: string,
  field: string,
): StoryWorkspaceDreamState {
  assertLocallyEditable(state);
  const localEdits = state.localEdits.filter((edit) => !(
    edit.stage === stage && edit.entityId === entityId && edit.field === field
  ));
  if (localEdits.length === state.localEdits.length) return state;
  const rebase = rebaseCleanStage(state, localEdits, stage);
  return withDerivedState(state, {
    localEdits,
    ...rebase,
  });
}

function compareLocalEdits(
  left: StoryWorkspaceDreamLocalEdit,
  right: StoryWorkspaceDreamLocalEdit,
): number {
  return STAGE_ORDER[left.stage] - STAGE_ORDER[right.stage]
    || left.entityId.localeCompare(right.entityId)
    || left.field.localeCompare(right.field);
}

function validateLocalEdits(state: StoryWorkspaceDreamState): void {
  for (const edit of state.localEdits) {
    const item = findItem(state, edit.stage, edit.entityId);
    if (!item.editableFields.includes(edit.field)) {
      throw new Error(`Dream field "${edit.field}" is not in the current editable whitelist`);
    }
    if (!isJsonValue(edit.value)) {
      throw new Error(`Dream field "${edit.field}" must be a finite JSON value`);
    }
  }
}

function completeBaseRevisions(
  state: StoryWorkspaceDreamState,
): Record<StoryWorkspaceDreamStage, number> {
  const characters = state.baseRevisions.characters;
  const scenes = state.baseRevisions.scenes;
  const storyboards = state.baseRevisions.storyboards;
  if (characters === undefined || scenes === undefined || storyboards === undefined) {
    throw new Error('All required Dream stage revisions must exist before confirmation');
  }
  return { characters, scenes, storyboards };
}

function buildConfirmationEdits(
  state: StoryWorkspaceDreamState,
): StoryWorkspaceDreamConfirmationEdit[] {
  validateLocalEdits(state);
  const grouped = new Map<string, {
    stage: StoryWorkspaceDreamStage;
    entityId: string;
    fields: Record<string, StoryWorkspaceDreamFieldValue>;
  }>();

  for (const edit of [...state.localEdits].sort(compareLocalEdits)) {
    const key = `${edit.stage}\u0000${edit.entityId}`;
    const group = grouped.get(key) ?? {
      stage: edit.stage,
      entityId: edit.entityId,
      fields: {},
    };
    group.fields[edit.field] = cloneValue(edit.value);
    grouped.set(key, group);
  }
  return [...grouped.values()];
}

export function canConfirmStoryWorkspaceDream(state: StoryWorkspaceDreamState): boolean {
  if (state.status !== 'editing' || state.confirmationPayload !== null) return false;
  if (!isComplete(state.stageData) || state.hasRevisionConflict) return false;
  for (const stage of STORY_WORKSPACE_DREAM_STAGES) {
    if (state.baseRevisions[stage] !== state.latestRevisions[stage]) return false;
  }
  try {
    validateLocalEdits(state);
    return true;
  } catch {
    return false;
  }
}

export function beginStoryWorkspaceDreamConfirmation(
  state: StoryWorkspaceDreamState,
  idempotencyKey: string,
): StoryWorkspaceDreamConfirmationStart {
  if (state.status === 'confirming' || state.confirmationPayload !== null) {
    throw new Error('Dream confirmation is already in progress');
  }
  if (state.status !== 'editing') {
    throw new Error(`Dream cannot be confirmed while ${state.status}`);
  }
  if (!isComplete(state.stageData)) {
    throw new Error('All required Dream stage files must exist before confirmation');
  }
  if (state.hasRevisionConflict) {
    throw new Error('Dream confirmation is disabled by a stage revision conflict');
  }
  if (!idempotencyKey.startsWith('swc_') || idempotencyKey.length <= 4) {
    throw new Error('Dream confirmation idempotencyKey must start with swc_');
  }
  if (!canConfirmStoryWorkspaceDream(state)) {
    throw new Error('Dream confirmation requirements are not satisfied');
  }

  const payload: StoryWorkspaceDreamConfirmationPayload = {
    storyWorkspaceRunId: state.storyWorkspaceRunId,
    threadId: state.threadId,
    baseRevisions: completeBaseRevisions(state),
    edits: buildConfirmationEdits(state),
    idempotencyKey,
  };
  const confirming = withDerivedState(state, {
    status: 'confirming',
    confirmationPayload: payload,
  });
  return { state: confirming, payload };
}

export function acceptStoryWorkspaceDreamConfirmation(
  state: StoryWorkspaceDreamState,
): StoryWorkspaceDreamState {
  if (state.status !== 'confirming' || state.confirmationPayload === null) {
    throw new Error(`Dream confirmation cannot be accepted while ${state.status}`);
  }
  return withDerivedState(state, { status: 'continuing' });
}

export function completeStoryWorkspaceDream(
  state: StoryWorkspaceDreamState,
): StoryWorkspaceDreamState {
  if (state.status !== 'continuing') {
    throw new Error(`Dream cannot be completed while ${state.status}`);
  }
  return withDerivedState(state, { status: 'completed' });
}
