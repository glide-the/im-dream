// [Input] Synthetic Dream stage snapshots and local field edits (Playwright
//          node-side runner).
// [Output] Contract tests for the pure Dream draft seam: three-stage hydrate,
//          field-level drafts, revision staleness, and one confirmation.
// [Pos] Story Workspace Dream local-state seam (Task 3 F1).
// [Sync] 2026-08-04: initial Red coverage for design_006/design_007.

import { expect, test } from '@playwright/test';
import {
  acceptStoryWorkspaceDreamConfirmation,
  beginStoryWorkspaceDreamConfirmation,
  canConfirmStoryWorkspaceDream,
  completeStoryWorkspaceDream,
  createStoryWorkspaceDreamState,
  editStoryWorkspaceDreamField,
  hydrateStoryWorkspaceDreamState,
  readStoryWorkspaceDreamField,
  resetStoryWorkspaceDreamField,
  STORY_WORKSPACE_DREAM_STAGES,
  STORY_WORKSPACE_DREAM_STATES,
  type StoryWorkspaceDreamStage,
  type StoryWorkspaceDreamStageSnapshot,
} from '../dreamState';

const RUN_ID = 'run_0123456789abcdef0123456789abcdef';
const THREAD_ID = 'thread_dream';

function stageSnapshot(
  stage: StoryWorkspaceDreamStage,
  revision: number,
  fields: Readonly<Record<string, string>> = {},
): StoryWorkspaceDreamStageSnapshot {
  return {
    stage,
    revision,
    items: [
      {
        entityId: `${stage}_primary`,
        fields: {
          displayName: `${stage} primary`,
          summary: `${stage} summary r${revision}`,
          notes: `${stage} notes r${revision}`,
          ...fields,
        },
        editableFields: ['summary', 'notes'],
      },
    ],
  };
}

function readyState() {
  return hydrateStoryWorkspaceDreamState(
    createStoryWorkspaceDreamState({
      storyWorkspaceRunId: RUN_ID,
      threadId: THREAD_ID,
    }),
    [
      stageSnapshot('characters', 2),
      stageSnapshot('scenes', 3),
      stageSnapshot('storyboards', 5),
    ],
  );
}

test('Dream exposes only the five design_007 lifecycle states', () => {
  expect(STORY_WORKSPACE_DREAM_STATES).toEqual([
    'waiting-files',
    'editing',
    'confirming',
    'continuing',
    'completed',
  ]);
  expect(STORY_WORKSPACE_DREAM_STAGES).toEqual([
    'characters',
    'scenes',
    'storyboards',
  ]);
});

test('the three required stages hydrate one by one and only the complete set is confirmable', () => {
  let state = createStoryWorkspaceDreamState({
    storyWorkspaceRunId: RUN_ID,
    threadId: THREAD_ID,
  });

  expect(state.status).toBe('waiting-files');
  expect(state.availableStages).toEqual([]);
  expect(canConfirmStoryWorkspaceDream(state)).toBe(false);

  state = hydrateStoryWorkspaceDreamState(state, [stageSnapshot('characters', 2)]);
  expect(state.status).toBe('waiting-files');
  expect(state.availableStages).toEqual(['characters']);
  expect(state.baseRevisions).toEqual({ characters: 2 });
  expect(canConfirmStoryWorkspaceDream(state)).toBe(false);

  state = hydrateStoryWorkspaceDreamState(state, [stageSnapshot('scenes', 3)]);
  expect(state.status).toBe('waiting-files');
  expect(state.availableStages).toEqual(['characters', 'scenes']);
  expect(canConfirmStoryWorkspaceDream(state)).toBe(false);

  state = hydrateStoryWorkspaceDreamState(state, [stageSnapshot('storyboards', 5)]);
  expect(state.status).toBe('editing');
  expect(state.availableStages).toEqual(STORY_WORKSPACE_DREAM_STAGES);
  expect(state.baseRevisions).toEqual({
    characters: 2,
    scenes: 3,
    storyboards: 5,
  });
  expect(state.latestRevisions).toEqual(state.baseRevisions);
  expect(canConfirmStoryWorkspaceDream(state)).toBe(true);
});

test('hydrate stores server fields while field edits and resets remain local and count dirty fields', () => {
  let state = readyState();
  expect(readStoryWorkspaceDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('characters summary r2');

  state = editStoryWorkspaceDreamField(
    state,
    'characters',
    'characters_primary',
    'summary',
    'locally rewritten character',
  );
  state = editStoryWorkspaceDreamField(
    state,
    'characters',
    'characters_primary',
    'notes',
    'local notes',
  );
  expect(state.dirtyCount).toBe(2);
  expect(readStoryWorkspaceDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('locally rewritten character');

  state = resetStoryWorkspaceDreamField(
    state,
    'characters',
    'characters_primary',
    'summary',
  );
  expect(state.dirtyCount).toBe(1);
  expect(readStoryWorkspaceDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('characters summary r2');

  state = resetStoryWorkspaceDreamField(
    state,
    'characters',
    'characters_primary',
    'notes',
  );
  expect(state.dirtyCount).toBe(0);
});

test('a newer server revision preserves a dirty field, refreshes clean fields, and marks update/stale', () => {
  let state = editStoryWorkspaceDreamField(
    readyState(),
    'characters',
    'characters_primary',
    'summary',
    'keep my local character',
  );

  state = hydrateStoryWorkspaceDreamState(state, [stageSnapshot('characters', 4, {
    summary: 'server character r4',
    notes: 'server notes r4',
  })]);

  expect(readStoryWorkspaceDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('keep my local character');
  expect(readStoryWorkspaceDreamField(state, 'characters', 'characters_primary', 'notes'))
    .toBe('server notes r4');
  expect(state.baseRevisions.characters).toBe(2);
  expect(state.latestRevisions.characters).toBe(4);
  expect(state.workspaceUpdatedStages).toEqual(['characters']);
  expect(state.staleStages).toEqual(['characters']);
  expect(state.hasRevisionConflict).toBe(true);
  expect(canConfirmStoryWorkspaceDream(state)).toBe(false);
  expect(() => beginStoryWorkspaceDreamConfirmation(state, 'swc_conflict')).toThrow(/revision/i);

  state = resetStoryWorkspaceDreamField(
    state,
    'characters',
    'characters_primary',
    'summary',
  );
  expect(readStoryWorkspaceDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('server character r4');
  expect(state.baseRevisions.characters).toBe(4);
  expect(state.latestRevisions.characters).toBe(4);
  expect(state.workspaceUpdatedStages).toEqual(['characters']);
  expect(state.staleStages).toEqual([]);
  expect(state.hasRevisionConflict).toBe(false);
  expect(canConfirmStoryWorkspaceDream(state)).toBe(true);
});

test('a clean stage rebases to its latest server revision without creating a conflict', () => {
  const state = hydrateStoryWorkspaceDreamState(readyState(), [stageSnapshot('scenes', 7)]);
  expect(state.baseRevisions.scenes).toBe(7);
  expect(state.latestRevisions.scenes).toBe(7);
  expect(state.workspaceUpdatedStages).toEqual(['scenes']);
  expect(state.staleStages).toEqual([]);
  expect(canConfirmStoryWorkspaceDream(state)).toBe(true);
});

test('the editable-field whitelist is enforced before confirmation payload construction', () => {
  const state = readyState();
  expect(() => editStoryWorkspaceDreamField(
    state,
    'characters',
    'characters_primary',
    'displayName',
    'attempt to change a read-only field',
  )).toThrow(/editable/i);
  expect(() => editStoryWorkspaceDreamField(
    state,
    'characters',
    'characters_primary',
    'summary',
    Number.NaN,
  )).toThrow(/JSON/i);
});

test('confirmation builds one camelCase payload, prevents double-click, and accepted continues', () => {
  let state = editStoryWorkspaceDreamField(
    readyState(),
    'characters',
    'characters_primary',
    'summary',
    'final character summary',
  );
  state = editStoryWorkspaceDreamField(
    state,
    'storyboards',
    'storyboards_primary',
    'notes',
    'final shot note',
  );

  const confirmation = beginStoryWorkspaceDreamConfirmation(state, 'swc_123');
  expect(confirmation.state.status).toBe('confirming');
  expect(confirmation.state.confirmationPayload).toBe(confirmation.payload);
  expect(confirmation.payload).toEqual({
    storyWorkspaceRunId: RUN_ID,
    threadId: THREAD_ID,
    baseRevisions: {
      characters: 2,
      scenes: 3,
      storyboards: 5,
    },
    edits: [
      {
        stage: 'characters',
        entityId: 'characters_primary',
        fields: { summary: 'final character summary' },
      },
      {
        stage: 'storyboards',
        entityId: 'storyboards_primary',
        fields: { notes: 'final shot note' },
      },
    ],
    idempotencyKey: 'swc_123',
  });
  expect(Object.keys(confirmation.payload)).toEqual([
    'storyWorkspaceRunId',
    'threadId',
    'baseRevisions',
    'edits',
    'idempotencyKey',
  ]);
  expect(() => beginStoryWorkspaceDreamConfirmation(
    confirmation.state,
    'swc_second_click',
  )).toThrow(/already|confirming/i);

  state = acceptStoryWorkspaceDreamConfirmation(confirmation.state);
  expect(state.status).toBe('continuing');
  expect(state.confirmationPayload).toBe(confirmation.payload);
  expect(() => editStoryWorkspaceDreamField(
    state,
    'characters',
    'characters_primary',
    'summary',
    'too late',
  )).toThrow(/continuing/i);

  state = completeStoryWorkspaceDream(state);
  expect(state.status).toBe('completed');
});
