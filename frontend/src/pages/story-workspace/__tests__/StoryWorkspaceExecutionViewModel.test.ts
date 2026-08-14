// [Input] Run-scoped Dream file projections used after the single confirmation.
// [Output] Assets / Outline indexes, revision activity and focus navigation coverage.
// [Pos] Story Workspace execution collaboration view-model test (Task 3 F5)

import { expect, test } from '@playwright/test';
import type { StoryWorkspaceDreamFilesResponse } from '../../../hooks/story-workspace/contracts';
import {
  storyWorkspaceBuildExecutionWorkspace,
  storyWorkspaceCanAccessExecution,
  storyWorkspaceExecutionFocusNeighbors,
  storyWorkspaceResolveDreamDisplayTitle,
} from '../executionViewModel';

test('Dream display title prefers canonical Project and otherwise uses the goal prefix', () => {
  expect(storyWorkspaceResolveDreamDisplayTitle('  雾中黑海湖  ', '很长的创作目标'))
    .toBe('雾中黑海湖');
  expect(storyWorkspaceResolveDreamDisplayTitle(null, '  尚未初始化的创作目标  '))
    .toBe('尚未初始化的创作目标');
  expect(storyWorkspaceResolveDreamDisplayTitle(null, '甲'.repeat(100)))
    .toBe('甲'.repeat(80));
  expect(storyWorkspaceResolveDreamDisplayTitle(null, null)).toBe('故事协作工作台');
});

const RUN_ID = `run_${'2'.repeat(32)}`;

function files(): StoryWorkspaceDreamFilesResponse {
  return {
    storyWorkspaceRunId: RUN_ID,
    threadId: 'thread-execution',
    source: {
      deckPluginBindingId: 'binding-1',
      bindingRevision: 1,
      deckPluginVersion: '1.0.0',
      deckRuntimeSnapshotId: 'snapshot-1',
      runtimePluginLockId: 'lock-1',
    },
    requiredStages: ['characters', 'scenes', 'storyboards'],
    runRevision: 7,
    stages: {
      characters: {
        stage: 'characters', revision: 3,
        sourceFiles: ['assets/characters/lead.md'],
        page: { title: '人物', entryRoute: `/story-workspace/characters?run=${RUN_ID}` },
        items: [{
          entityId: 'lead', displayName: '林默', summary: '寻找真相。',
          content: '# 林默\n\n身份：调查记者。\n\n动机：寻找真相。',
          sourceFile: 'assets/characters/lead.md', relations: ['苏遥'],
        }],
      },
      scenes: {
        stage: 'scenes', revision: 2,
        sourceFiles: ['assets/scenes/station.md'],
        page: { title: '场景', entryRoute: `/story-workspace/scenes?run=${RUN_ID}` },
        items: [{
          entityId: 'station', displayName: '旧车站', summary: '雨夜站台。',
          sourceFile: 'assets/scenes/station.md', relations: ['林默'],
        }],
      },
      storyboards: {
        stage: 'storyboards', revision: 5,
        sourceFiles: ['storyboards/beat-01.md', 'storyboards/beat-02.md'],
        page: { title: '分镜', entryRoute: `/story-workspace/runs/${RUN_ID}/execution` },
        items: [
          {
            entityId: 'beat-01', displayName: '雨夜抵达', summary: '远景建立车站。',
            sourceFile: 'storyboards/beat-01.md', relations: ['林默', '旧车站'],
          },
          {
            entityId: 'beat-02', displayName: '冲突发生', summary: '苏遥出现。',
            sourceFile: 'storyboards/beat-02.md', relations: ['林默', '苏遥'],
          },
        ],
      },
    },
    confirmationAccepted: true,
    confirmationDispatched: true,
    canConfirm: false,
    confirmationLabel: '确认并继续',
    agentActivity: null,
  };
}

test('builds Assets and Outline from workspace files without approval states', () => {
  const workspace = storyWorkspaceBuildExecutionWorkspace(files());

  expect(workspace.assets.map((entry) => entry.title)).toEqual(['林默', '旧车站']);
  expect(workspace.outline.map((entry) => entry.title)).toEqual(['雨夜抵达', '冲突发生']);
  expect(workspace.outline[1]).toMatchObject({
    key: 'storyboards:beat-02',
    revision: 5,
    relations: ['林默', '苏遥'],
  });
  expect(workspace.assets[0]).toMatchObject({
    summary: '寻找真相。',
    content: '# 林默\n\n身份：调查记者。\n\n动机：寻找真相。',
  });
  expect(workspace.activity.map((entry) => entry.label)).toEqual([
    '分镜文件已写入 r5',
    '人物文件已写入 r3',
    '场景文件已写入 r2',
  ]);
  expect(Object.keys(workspace)).toEqual(['assets', 'outline', 'activity', 'runRevision']);
});

test('focus neighbors stay inside the ordered Outline manuscript', () => {
  const outline = storyWorkspaceBuildExecutionWorkspace(files()).outline;

  expect(storyWorkspaceExecutionFocusNeighbors(outline, 'storyboards:beat-01'))
    .toEqual({ previousKey: null, nextKey: 'storyboards:beat-02' });
  expect(storyWorkspaceExecutionFocusNeighbors(outline, 'storyboards:beat-02'))
    .toEqual({ previousKey: 'storyboards:beat-01', nextKey: null });
  expect(storyWorkspaceExecutionFocusNeighbors(outline, 'missing'))
    .toEqual({ previousKey: null, nextKey: null });
});

test('route gate uses the durable Dream confirmation fact, never WorkflowRun.status', () => {
  expect(storyWorkspaceCanAccessExecution(files())).toBe(true);
  expect(storyWorkspaceCanAccessExecution({
    ...files(),
    confirmationAccepted: false,
    confirmationDispatched: false,
    canConfirm: true,
  })).toBe(false);
});
