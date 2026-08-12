// [Input] Run-scoped Dream file projections and editable text values.
// [Output] Pure view-model mapping coverage for the Dream business page.
// [Pos] Story Workspace Dream page view-model test node (Task 3 F4)

import { expect, test } from '@playwright/test';
import type { StoryWorkspaceDreamFilesResponse } from '../../../hooks/story-workspace/contracts';
import {
  storyWorkspaceDreamStageSnapshotsFromFiles,
  storyWorkspaceDreamAgentActivityNotice,
  storyWorkspaceDreamLifecycleFromPersistence,
  storyWorkspaceDreamPersistenceNotice,
  storyWorkspaceDreamRunFailureNotice,
  storyWorkspaceParseDreamEditorValue,
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
    agentActivity: null,
  };
}

test('maps content-free Observer hints to display copy without lifecycle state', () => {
  const operationId = 'a'.repeat(64);
  expect(storyWorkspaceDreamAgentActivityNotice({
    activity: 'activity_started_hint',
    sequence: 3,
    terminalOutcome: null,
    needsReconcile: false,
    operationScope: 'content_generation',
    operationState: 'started',
    operationId,
  })).toBe('Dream 内容生成正在运行');
  expect(storyWorkspaceDreamAgentActivityNotice({
    activity: 'activity_settled_hint',
    sequence: 4,
    terminalOutcome: null,
    needsReconcile: false,
    operationScope: 'workflow_operation',
    operationState: 'failed',
    operationId,
  })).toBe('Dream 工作流操作执行失败');
  expect(storyWorkspaceDreamAgentActivityNotice({
    activity: 'reconcile_requested',
    sequence: -1,
    terminalOutcome: null,
    needsReconcile: true,
    operationScope: null,
    operationState: null,
    operationId: null,
  })).toBe('正在校验 Dream 业务投影');
  expect(storyWorkspaceDreamAgentActivityNotice(null)).toBeNull();
});

test('does not turn Agent lifecycle, confirmation, subagent, or generic tool hints into business copy', () => {
  const operationId = 'b'.repeat(64);
  expect(storyWorkspaceDreamAgentActivityNotice({
    activity: 'turn_settled_hint',
    sequence: 7,
    terminalOutcome: 'completed',
    needsReconcile: false,
    operationScope: null,
    operationState: null,
    operationId: null,
  })).toBeNull();
  expect(storyWorkspaceDreamAgentActivityNotice({
    activity: 'waiting_confirmation_hint',
    sequence: 8,
    terminalOutcome: null,
    needsReconcile: false,
    operationScope: 'workflow_operation',
    operationState: 'waiting_confirmation',
    operationId,
  })).toBeNull();
  for (const operationScope of ['subagent', 'tool'] as const) {
    expect(storyWorkspaceDreamAgentActivityNotice({
      activity: 'activity_started_hint',
      sequence: 9,
      terminalOutcome: null,
      needsReconcile: false,
      operationScope,
      operationState: 'started',
      operationId,
    })).toBeNull();
  }
});

test('maps only the three server-whitelisted editable fields into local state', () => {
  const snapshots = storyWorkspaceDreamStageSnapshotsFromFiles(projection());
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
  )).toBe('story-workspace-dream-editing');
  expect(storyWorkspaceDreamPersistenceNotice(saved, 'running')).toBe(
    '命令已保存，等待同一 Dream Agent 接续',
  );
  expect(storyWorkspaceDreamLifecycleFromPersistence(
    saved,
    'completed',
    'story-workspace-dream-editing',
  )).toBe('story-workspace-dream-running');
  expect(storyWorkspaceDreamPersistenceNotice(saved, 'completed')).toBe(
    '命令已保存，等待同一 Dream Agent 接续',
  );

  const dispatched = { ...saved, confirmationDispatched: true };
  expect(storyWorkspaceDreamPersistenceNotice(dispatched, 'running')).toBe(
    '同一 Dream Agent 正在执行',
  );
  expect(storyWorkspaceDreamLifecycleFromPersistence(
    dispatched,
    'completed',
    'story-workspace-dream-editing',
  )).toBe('story-workspace-dream-completed');
  expect(storyWorkspaceDreamPersistenceNotice(dispatched, 'completed')).toBe(
    '同一 Dream Agent 已完成后续执行',
  );
});

test('renders a safe durable Workflow failure instead of running copy', () => {
  expect(storyWorkspaceDreamRunFailureNotice({
    status: 'failed',
    error_code: 'GATEWAY_UNAVAILABLE',
    failed_step: 'dream_agent_dispatch',
  })).toBe('Dream Agent 暂时无法连接平台模型服务。运行已安全停止，未完成的步骤不会显示为成功。');
  expect(storyWorkspaceDreamRunFailureNotice({
    status: 'running',
    error_code: null,
    failed_step: null,
  })).toBeNull();
});

test('formats editor values and parses relations without empty duplicates', () => {
  expect(storyWorkspaceDreamEditorValue(['林默', '苏遥'])).toBe('林默，苏遥');
  expect(storyWorkspaceDreamEditorValue(null)).toBe('');
  expect(storyWorkspaceParseDreamEditorValue('relations', '林默, 苏遥，林默'))
    .toEqual(['林默', '苏遥']);
  expect(storyWorkspaceParseDreamEditorValue('summary', '')).toBeNull();
  expect(storyWorkspaceParseDreamEditorValue('displayName', '  林默  ')).toBe('林默');
  expect(() => storyWorkspaceParseDreamEditorValue('displayName', '   ')).toThrow();
});
