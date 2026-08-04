// [Input] Synthetic Dream stage snapshots and local field edits (Playwright
//          node-side runner).
// [Output] Contract tests for the pure Dream draft seam: three-stage hydrate,
//          field-level drafts, revision staleness, and one confirmation.
// [Pos] Story Workspace Dream local-state seam (Task 3 F1).
// [Sync] 2026-08-04: canonical command/full-state values plus ack and explicit
//                    conflict resolution; readonly/deep-freeze, clone safety,
//                    JSON rejection, and ordinal command byte stability.

import { expect, test } from '@playwright/test';
import type {
  StoryWorkspaceDreamConfirmationEdit,
  StoryWorkspaceDreamConfirmationCommand,
  StoryWorkspaceDreamFieldValue,
  StoryWorkspaceDreamStage,
} from '../../../hooks/story-workspace/contracts';
import {
  storyWorkspaceAcceptDreamConfirmation,
  storyWorkspaceBeginDreamConfirmation,
  storyWorkspaceCanConfirmDream,
  storyWorkspaceCompleteDream,
  storyWorkspaceCreateDreamState,
  storyWorkspaceEditDreamField,
  storyWorkspaceHydrateDreamState,
  storyWorkspaceReadDreamField,
  storyWorkspaceResolveDreamRevisionConflict,
  storyWorkspaceResetDreamField,
  STORY_WORKSPACE_DREAM_STAGES,
  STORY_WORKSPACE_DREAM_STATES,
  type StoryWorkspaceDreamConfirmationStart,
  type StoryWorkspaceDreamState,
  type StoryWorkspaceDreamStageSnapshot,
} from '../dreamState';

type TypesEqual<Left, Right> =
  (<Value>() => Value extends Left ? 1 : 2) extends
  (<Value>() => Value extends Right ? 1 : 2) ? true : false;

type WritableKeys<Value> = {
  [Key in keyof Value]-?: TypesEqual<
    Pick<Value, Key>,
    { -readonly [Property in Key]: Value[Property] }
  > extends true ? Key : never;
}[keyof Value];

const DREAM_PUBLIC_STRUCTURES_ARE_READONLY: [
  WritableKeys<StoryWorkspaceDreamConfirmationCommand>,
  WritableKeys<StoryWorkspaceDreamConfirmationEdit>,
  WritableKeys<StoryWorkspaceDreamState>,
  WritableKeys<StoryWorkspaceDreamConfirmationStart>,
] extends [never, never, never, never] ? true : false = true;

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
  return storyWorkspaceHydrateDreamState(
    storyWorkspaceCreateDreamState({
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

function readyStateWithCharacterItems(
  items: StoryWorkspaceDreamStageSnapshot['items'],
) {
  return storyWorkspaceHydrateDreamState(
    storyWorkspaceCreateDreamState({
      storyWorkspaceRunId: RUN_ID,
      threadId: THREAD_ID,
    }),
    [
      { stage: 'characters', revision: 2, items },
      stageSnapshot('scenes', 3),
      stageSnapshot('storyboards', 5),
    ],
  );
}

function invalidCharactersSnapshot(value: unknown): StoryWorkspaceDreamStageSnapshot {
  return {
    stage: 'characters',
    revision: 1,
    items: [{
      entityId: 'invalid_character',
      fields: { summary: value as StoryWorkspaceDreamFieldValue },
      editableFields: ['summary'],
    }],
  };
}

test('Dream exposes only the five design_007 lifecycle states', () => {
  expect(DREAM_PUBLIC_STRUCTURES_ARE_READONLY).toBe(true);
  expect(STORY_WORKSPACE_DREAM_STATES).toEqual([
    'story-workspace-dream-waiting-files',
    'story-workspace-dream-editing',
    'story-workspace-dream-confirming',
    'story-workspace-dream-continuing',
    'story-workspace-dream-completed',
  ]);
  expect(STORY_WORKSPACE_DREAM_STAGES).toEqual([
    'characters',
    'scenes',
    'storyboards',
  ]);
});

test('the three required stages hydrate one by one and only the complete set is confirmable', () => {
  let state = storyWorkspaceCreateDreamState({
    storyWorkspaceRunId: RUN_ID,
    threadId: THREAD_ID,
  });

  expect(state.status).toBe('story-workspace-dream-waiting-files');
  expect(state.availableStages).toEqual([]);
  expect(storyWorkspaceCanConfirmDream(state)).toBe(false);

  state = storyWorkspaceHydrateDreamState(state, [stageSnapshot('characters', 2)]);
  expect(state.status).toBe('story-workspace-dream-waiting-files');
  expect(state.availableStages).toEqual(['characters']);
  expect(state.baseRevisions).toEqual({ characters: 2 });
  expect(storyWorkspaceCanConfirmDream(state)).toBe(false);

  state = storyWorkspaceHydrateDreamState(state, [stageSnapshot('scenes', 3)]);
  expect(state.status).toBe('story-workspace-dream-waiting-files');
  expect(state.availableStages).toEqual(['characters', 'scenes']);
  expect(storyWorkspaceCanConfirmDream(state)).toBe(false);

  state = storyWorkspaceHydrateDreamState(state, [stageSnapshot('storyboards', 5)]);
  expect(state.status).toBe('story-workspace-dream-editing');
  expect(state.availableStages).toEqual(STORY_WORKSPACE_DREAM_STAGES);
  expect(state.baseRevisions).toEqual({
    characters: 2,
    scenes: 3,
    storyboards: 5,
  });
  expect(state.latestRevisions).toEqual(state.baseRevisions);
  expect(storyWorkspaceCanConfirmDream(state)).toBe(true);
});

test('hydrate stores server fields while field edits and resets remain local and count dirty fields', () => {
  let state = readyState();
  expect(storyWorkspaceReadDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('characters summary r2');

  state = storyWorkspaceEditDreamField(
    state,
    'characters',
    'characters_primary',
    'summary',
    'locally rewritten character',
  );
  state = storyWorkspaceEditDreamField(
    state,
    'characters',
    'characters_primary',
    'notes',
    'local notes',
  );
  expect(state.dirtyCount).toBe(2);
  expect(storyWorkspaceReadDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('locally rewritten character');

  state = storyWorkspaceResetDreamField(
    state,
    'characters',
    'characters_primary',
    'summary',
  );
  expect(state.dirtyCount).toBe(1);
  expect(storyWorkspaceReadDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('characters summary r2');

  state = storyWorkspaceResetDreamField(
    state,
    'characters',
    'characters_primary',
    'notes',
  );
  expect(state.dirtyCount).toBe(0);
});

test('hydrate/edit clone inputs, operations preserve old state, and reads return deep clones', () => {
  const hydratedValue = { beats: ['server beat'] };
  const editableFields = ['details'];
  const characters = {
    stage: 'characters',
    revision: 1,
    items: [{
      entityId: 'character_clone',
      fields: { details: hydratedValue },
      editableFields,
    }],
  } satisfies StoryWorkspaceDreamStageSnapshot;
  const empty = storyWorkspaceCreateDreamState({
    storyWorkspaceRunId: RUN_ID,
    threadId: THREAD_ID,
  });
  const hydrated = storyWorkspaceHydrateDreamState(empty, [characters]);

  hydratedValue.beats.push('mutated after hydrate');
  editableFields.push('not_really_editable');
  expect(storyWorkspaceReadDreamField(hydrated, 'characters', 'character_clone', 'details'))
    .toEqual({ beats: ['server beat'] });
  expect(() => storyWorkspaceEditDreamField(
    hydrated,
    'characters',
    'character_clone',
    'not_really_editable',
    'blocked',
  )).toThrow(/editable/i);

  const editValue = { beats: ['local beat'] };
  const edited = storyWorkspaceEditDreamField(
    hydrated,
    'characters',
    'character_clone',
    'details',
    editValue,
  );
  editValue.beats.push('mutated after edit');

  expect(hydrated.dirtyCount).toBe(0);
  expect(storyWorkspaceReadDreamField(hydrated, 'characters', 'character_clone', 'details'))
    .toEqual({ beats: ['server beat'] });
  expect(edited.dirtyCount).toBe(1);
  expect(storyWorkspaceReadDreamField(edited, 'characters', 'character_clone', 'details'))
    .toEqual({ beats: ['local beat'] });

  const readValue = storyWorkspaceReadDreamField(
    edited,
    'characters',
    'character_clone',
    'details',
  ) as { beats: string[] };
  readValue.beats.push('mutated read clone');
  expect(storyWorkspaceReadDreamField(edited, 'characters', 'character_clone', 'details'))
    .toEqual({ beats: ['local beat'] });
});

test('all public states and the canonical command are deeply frozen against external mutation', () => {
  const created = storyWorkspaceCreateDreamState({
    storyWorkspaceRunId: RUN_ID,
    threadId: THREAD_ID,
  });
  const hydrated = readyState();
  const edited = storyWorkspaceEditDreamField(
    hydrated,
    'characters',
    'characters_primary',
    'summary',
    'frozen local summary',
  );
  const reset = storyWorkspaceResetDreamField(
    edited,
    'characters',
    'characters_primary',
    'summary',
  );
  const stale = storyWorkspaceHydrateDreamState(edited, [stageSnapshot('characters', 4)]);
  const resolved = storyWorkspaceResolveDreamRevisionConflict(stale, 'characters', 'keep-local');
  const confirmation = storyWorkspaceBeginDreamConfirmation(resolved, 'swc_frozen');
  const continuing = storyWorkspaceAcceptDreamConfirmation(confirmation.state);
  const completed = storyWorkspaceCompleteDream(continuing);

  for (const state of [created, hydrated, edited, reset, stale, resolved, confirmation.state, continuing, completed]) {
    expect(Object.isFrozen(state)).toBe(true);
    expect(Object.isFrozen(state.availableStages)).toBe(true);
    expect(Object.isFrozen(state.baseRevisions)).toBe(true);
    expect(Object.isFrozen(state.latestRevisions)).toBe(true);
    expect(Object.isFrozen(state.workspaceUpdatedStages)).toBe(true);
    expect(Object.isFrozen(state.staleStages)).toBe(true);
    expect(Object.isFrozen(state.stageData)).toBe(true);
    expect(Object.isFrozen(state.localEdits)).toBe(true);
  }
  const hydratedCharacter = hydrated.stageData.characters;
  expect(hydratedCharacter).toBeDefined();
  expect(Object.isFrozen(hydratedCharacter)).toBe(true);
  expect(Object.isFrozen(hydratedCharacter?.items)).toBe(true);
  expect(Object.isFrozen(hydratedCharacter?.items[0])).toBe(true);
  expect(Object.isFrozen(hydratedCharacter?.items[0]?.fields)).toBe(true);
  expect(Object.isFrozen(hydratedCharacter?.items[0]?.editableFields)).toBe(true);

  expect(Object.isFrozen(confirmation)).toBe(true);
  expect(Object.isFrozen(confirmation.command)).toBe(true);
  expect(Object.isFrozen(confirmation.command.baseRevisions)).toBe(true);
  expect(Object.isFrozen(confirmation.command.edits)).toBe(true);
  expect(Object.isFrozen(confirmation.command.edits[0])).toBe(true);
  expect(Object.isFrozen(confirmation.command.edits[0]?.fields)).toBe(true);

  expect(() => {
    (hydrated as unknown as { dirtyCount: number }).dirtyCount = 99;
  }).toThrow(TypeError);
  expect(() => {
    (hydratedCharacter?.items[0]?.fields as Record<string, StoryWorkspaceDreamFieldValue>).summary = 'hacked';
  }).toThrow(TypeError);
  expect(() => {
    (confirmation.command as unknown as { idempotencyKey: string }).idempotencyKey = 'swc_hacked';
  }).toThrow(TypeError);
  expect(hydrated.dirtyCount).toBe(0);
  expect(confirmation.command.idempotencyKey).toBe('swc_frozen');
});

test('hydrate and edit reject cycles, Date/non-plain objects, and nested reserved keys', () => {
  const cycle: Record<string, unknown> = {};
  cycle.self = cycle;
  const invalidValues: unknown[] = [
    cycle,
    new Date('2026-08-04T00:00:00Z'),
    Object.create({ inherited: true }),
    JSON.parse('{"nested":{"constructor":"blocked"}}'),
    JSON.parse('{"nested":{"prototype":"blocked"}}'),
    JSON.parse('{"nested":{"__proto__":"blocked"}}'),
  ];

  for (const invalidValue of invalidValues) {
    const empty = storyWorkspaceCreateDreamState({
      storyWorkspaceRunId: RUN_ID,
      threadId: THREAD_ID,
    });
    expect(() => storyWorkspaceHydrateDreamState(
      empty,
      [invalidCharactersSnapshot(invalidValue)],
    )).toThrow(/JSON/i);
    expect(() => storyWorkspaceEditDreamField(
      readyState(),
      'characters',
      'characters_primary',
      'summary',
      invalidValue as StoryWorkspaceDreamFieldValue,
    )).toThrow(/JSON/i);
  }
});

function revisionConflictState() {
  let state = storyWorkspaceEditDreamField(
    readyState(),
    'characters',
    'characters_primary',
    'summary',
    'keep my local character',
  );

  state = storyWorkspaceHydrateDreamState(state, [stageSnapshot('characters', 4, {
    summary: 'server character r4',
    notes: 'server notes r4',
  })]);
  return state;
}

test('a newer server revision preserves a dirty field, refreshes clean fields, and marks update/stale', () => {
  const state = revisionConflictState();

  expect(storyWorkspaceReadDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('keep my local character');
  expect(storyWorkspaceReadDreamField(state, 'characters', 'characters_primary', 'notes'))
    .toBe('server notes r4');
  expect(state.baseRevisions.characters).toBe(2);
  expect(state.latestRevisions.characters).toBe(4);
  expect(state.workspaceUpdatedStages).toEqual(['characters']);
  expect(state.staleStages).toEqual(['characters']);
  expect(state.hasRevisionConflict).toBe(true);
  expect(storyWorkspaceCanConfirmDream(state)).toBe(false);
  expect(() => storyWorkspaceBeginDreamConfirmation(state, 'swc_conflict')).toThrow(/revision/i);
});

test('keep-local explicitly rebases the dirty merge result onto the latest stage revision', () => {
  const state = storyWorkspaceResolveDreamRevisionConflict(
    revisionConflictState(),
    'characters',
    'keep-local',
  );
  expect(storyWorkspaceReadDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('keep my local character');
  expect(state.baseRevisions.characters).toBe(4);
  expect(state.latestRevisions.characters).toBe(4);
  expect(state.workspaceUpdatedStages).toEqual(['characters']);
  expect(state.staleStages).toEqual([]);
  expect(state.hasRevisionConflict).toBe(false);
  expect(storyWorkspaceCanConfirmDream(state)).toBe(true);
});

test('accept-server explicitly discards only that stage draft and rebases to authoritative data', () => {
  let state = storyWorkspaceEditDreamField(
    revisionConflictState(),
    'storyboards',
    'storyboards_primary',
    'notes',
    'unrelated local storyboard note',
  );
  state = storyWorkspaceResolveDreamRevisionConflict(state, 'characters', 'accept-server');

  expect(storyWorkspaceReadDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('server character r4');
  expect(storyWorkspaceReadDreamField(state, 'storyboards', 'storyboards_primary', 'notes'))
    .toBe('unrelated local storyboard note');
  expect(state.dirtyCount).toBe(1);
  expect(state.baseRevisions.characters).toBe(4);
  expect(state.staleStages).toEqual([]);
  expect(storyWorkspaceCanConfirmDream(state)).toBe(true);
});

test('a clean stage rebases to its latest server revision without creating a conflict', () => {
  const state = storyWorkspaceHydrateDreamState(readyState(), [stageSnapshot('scenes', 7)]);
  expect(state.baseRevisions.scenes).toBe(7);
  expect(state.latestRevisions.scenes).toBe(7);
  expect(state.workspaceUpdatedStages).toEqual(['scenes']);
  expect(state.staleStages).toEqual([]);
  expect(storyWorkspaceCanConfirmDream(state)).toBe(true);
});

test('the editable-field whitelist is enforced before confirmation payload construction', () => {
  const state = readyState();
  expect(() => storyWorkspaceEditDreamField(
    state,
    'characters',
    'characters_primary',
    'displayName',
    'attempt to change a read-only field',
  )).toThrow(/editable/i);
  expect(() => storyWorkspaceEditDreamField(
    state,
    'characters',
    'characters_primary',
    'summary',
    Number.NaN,
  )).toThrow(/JSON/i);
});

test('non-ASCII command ordering is ordinal and byte-stable across opposite edit insertion order', () => {
  const items: StoryWorkspaceDreamStageSnapshot['items'] = [
    {
      entityId: '角色乙',
      fields: { 摘要: 'old summary', 说明: 'old notes' },
      editableFields: ['摘要', '说明'],
    },
    {
      entityId: 'éclair',
      fields: { 描述: 'old description' },
      editableFields: ['描述'],
    },
  ];
  const operations = [
    ['characters', '角色乙', '摘要', 'new summary'],
    ['characters', 'éclair', '描述', 'new description'],
    ['characters', '角色乙', '说明', 'new notes'],
  ] as const;

  const buildCommand = (reverse: boolean) => {
    let state = readyStateWithCharacterItems(items);
    const edits = reverse ? [...operations].reverse() : operations;
    for (const [stage, entityId, field, value] of edits) {
      state = storyWorkspaceEditDreamField(state, stage, entityId, field, value);
    }
    return storyWorkspaceBeginDreamConfirmation(state, 'swc_ordinal').command;
  };

  const forward = buildCommand(false);
  const reverse = buildCommand(true);
  expect(reverse).toEqual(forward);
  expect(JSON.stringify(reverse)).toBe(JSON.stringify(forward));
  expect(forward.edits.map((edit) => edit.entityId)).toEqual(['éclair', '角色乙']);
  expect(Object.keys(forward.edits[1]?.fields ?? {})).toEqual(['摘要', '说明']);
});

test('confirmation builds one canonical camelCase Command and prevents double-click', () => {
  let state = storyWorkspaceEditDreamField(
    readyState(),
    'characters',
    'characters_primary',
    'summary',
    'final character summary',
  );
  state = storyWorkspaceEditDreamField(
    state,
    'storyboards',
    'storyboards_primary',
    'notes',
    'final shot note',
  );

  const confirmation = storyWorkspaceBeginDreamConfirmation(state, 'swc_123');
  const command: StoryWorkspaceDreamConfirmationCommand = confirmation.command;
  expect(confirmation.state.status).toBe('story-workspace-dream-confirming');
  expect(confirmation.state.confirmationCommand).toBe(command);
  expect(command).toEqual({
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
  expect(Object.keys(command)).toEqual([
    'storyWorkspaceRunId',
    'threadId',
    'baseRevisions',
    'edits',
    'idempotencyKey',
  ]);
  expect(() => storyWorkspaceBeginDreamConfirmation(
    confirmation.state,
    'swc_second_click',
  )).toThrow(/already|confirming/i);
});

test('accepted clears submitted drafts so a higher Agent revision becomes authoritative', () => {
  const edited = storyWorkspaceEditDreamField(
    readyState(),
    'characters',
    'characters_primary',
    'summary',
    'submitted character summary',
  );
  const confirmation = storyWorkspaceBeginDreamConfirmation(edited, 'swc_ack');
  let state = storyWorkspaceAcceptDreamConfirmation(confirmation.state);

  expect(state.status).toBe('story-workspace-dream-continuing');
  expect(state.confirmationCommand).toBe(confirmation.command);
  expect(state.dirtyCount).toBe(0);
  expect(state.localEdits).toEqual([]);
  expect(() => storyWorkspaceEditDreamField(
    state,
    'characters',
    'characters_primary',
    'summary',
    'too late',
  )).toThrow(/continuing/i);

  state = storyWorkspaceHydrateDreamState(state, [stageSnapshot('characters', 6, {
    summary: 'authoritative Agent character r6',
  })]);
  expect(storyWorkspaceReadDreamField(state, 'characters', 'characters_primary', 'summary'))
    .toBe('authoritative Agent character r6');
  expect(state.baseRevisions.characters).toBe(6);
  expect(state.latestRevisions.characters).toBe(6);
  expect(state.staleStages).toEqual([]);

  state = storyWorkspaceCompleteDream(state);
  expect(state.status).toBe('story-workspace-dream-completed');
});
