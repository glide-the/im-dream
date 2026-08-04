// [Input] Run-scoped Dream file projections and editable text values.
// [Output] Pure view-model mapping coverage for the Dream business page.
// [Pos] Story Workspace Dream page view-model test node (Task 3 F4)

import { expect, test } from '@playwright/test';
import type { StoryWorkspaceDreamFilesResponse } from '../../../hooks/story-workspace/contracts';
import {
  dreamStageSnapshotsFromFiles,
  storyWorkspaceDreamLifecycleFromPersistence,
  storyWorkspaceDreamPersistenceNotice,
  parseStoryWorkspaceDreamEditorValue,
  storyWorkspaceDreamEditorValue,
} from '../dreamViewModel';

const RUN_ID = `run_${'1'.repeat(32)}`;

function projection(): StoryWorkspaceDreamFilesResponse {
  return {
    storyWorkspaceRunId: RUN_ID,
    threadId: 'thread-1',
    source: {
      deckPluginBindingId: 'binding-1',
      bindingRevision: 1,
      deckPluginVersion: '1.0.0',
      deckRuntimeSnapshotId: 'snapshot-1',
      runtimePluginLockId: 'lock-1',
    },
    requiredStages: ['characters', 'scenes', 'storyboards'],
    runRevision: 1,
    stages: {
      characters: {
        stage: 'characters',
        revision: 2,
        sourceFiles: ['assets/characters/lead.md'],
        page: { title: '人物', entryRoute: `/story-workspace/characters?run=${RUN_ID}` },
        items: [{
          entityId: 'lead',
          displayName: '林默',
          summary: '在雨夜等待真相。',
          sourceFile: 'assets/characters/lead.md',
          relations: ['苏遥'],
        }],
      },
    },
    confirmationAccepted: false,
    confirmationDispatched: false,
    canConfirm: false,
    confirmationLabel: '确认并继续',
  };
}

test('maps only the three server-whitelisted editable fields into local state', () => {
  const snapshots = dreamStageSnapshotsFromFiles(projection());
  expect(snapshots).toHaveLength(1);
  expect(snapshots[0]).toEqual({
    stage: 'characters',
    revision: 2,
    items: [{
      entityId: 'lead',
      fields: {
        displayName: '林默',
        summary: '在雨夜等待真相。',
        relations: ['苏遥'],
      },
      editableFields: ['displayName', 'summary', 'relations'],
    }],
  });
});

test('restores the one-confirm lifecycle from durable confirmation and run facts', () => {
  const editing = projection();
  expect(storyWorkspaceDreamLifecycleFromPersistence(
    editing,
    'running',
    'story-workspace-dream-editing',
  )).toBe('story-workspace-dream-editing');

  const saved = {
    ...editing,
    confirmationAccepted: true,
    confirmationDispatched: false,
  };
  expect(storyWorkspaceDreamLifecycleFromPersistence(
    saved,
    'failed',
    'story-workspace-dream-editing',
  )).toBe('story-workspace-dream-continuing');
  expect(storyWorkspaceDreamPersistenceNotice(saved, 'continuing')).toBe(
    '命令已保存，等待同一 Agent 接续',
  );
  expect(storyWorkspaceDreamLifecycleFromPersistence(
    saved,
    'completed',
    'story-workspace-dream-editing',
  )).toBe('story-workspace-dream-continuing');
  expect(storyWorkspaceDreamPersistenceNotice(saved, 'completed')).toBe(
    '命令已保存，等待同一 Agent 接续',
  );

  const dispatched = { ...saved, confirmationDispatched: true };
  expect(storyWorkspaceDreamPersistenceNotice(dispatched, 'continuing')).toBe(
    '同一 Chat Agent 正在继续',
  );
  expect(storyWorkspaceDreamLifecycleFromPersistence(
    dispatched,
    'completed',
    'story-workspace-dream-editing',
  )).toBe('story-workspace-dream-completed');
  expect(storyWorkspaceDreamPersistenceNotice(dispatched, 'completed')).toBe(
    '同一 Chat Agent 已完成后续执行',
  );
});

test('formats editor values and parses relations without empty duplicates', () => {
  expect(storyWorkspaceDreamEditorValue(['林默', '苏遥'])).toBe('林默，苏遥');
  expect(storyWorkspaceDreamEditorValue(null)).toBe('');
  expect(parseStoryWorkspaceDreamEditorValue('relations', '林默, 苏遥，林默'))
    .toEqual(['林默', '苏遥']);
  expect(parseStoryWorkspaceDreamEditorValue('summary', '')).toBeNull();
  expect(parseStoryWorkspaceDreamEditorValue('displayName', '  林默  ')).toBe('林默');
  expect(() => parseStoryWorkspaceDreamEditorValue('displayName', '   ')).toThrow();
});
