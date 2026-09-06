// [Input] Dream deep-link runs whose raw WorkflowRun.status may be a legacy branch.
// [Output] Safe WorkflowContextBar projection coverage for Dream surfaces.
// [Pos] Story Workspace Dream router context seam test (Task 3 F9).

import { expect, test } from '@playwright/test';
import type { WorkflowRunStatus } from '../../api/storyWorkspaceApi';
import { storyWorkspaceWorkflowContextLabel } from '../../components/story-workspace/workflow/storyWorkspaceWorkflowContext';
import {
  storyWorkspaceDreamWorkflowContext,
  type StoryWorkspaceDreamWorkflowContextRun,
} from '../storyWorkspaceDreamContext';

function run(status: WorkflowRunStatus): StoryWorkspaceDreamWorkflowContextRun {
  return {
    workflow_run_id: 'run-1',
    deck_plugin_display_name: 'Ink Dream Story',
    deck_plugin_version: '1.0.0',
    workflow_summary: '故事协作',
    status,
  };
}

for (const [status, legacyLabel] of [
  ['rejected', '已驳回'],
  ['failed', '运行失败'],
  ['cancelled', '已取消'],
] as const) {
  test(`Dream route hides raw ${status} behind its safe collaboration state`, () => {
    const context = storyWorkspaceDreamWorkflowContext(run(status));

    expect(context?.state).toBe('story_workspace_dream');
    expect(context).not.toHaveProperty('status');
    const label = storyWorkspaceWorkflowContextLabel(context!.state);
    expect(label).toBe('Dream 协作中');
    expect(label).not.toContain(legacyLabel);
  });
}

test('non-Dream WorkflowContextBar keeps its legacy status labels', () => {
  expect(storyWorkspaceWorkflowContextLabel('pending_review')).toBe('待审阅');
  expect(storyWorkspaceWorkflowContextLabel('rejected')).toBe('已驳回');
  expect(storyWorkspaceWorkflowContextLabel('failed')).toBe('运行失败');
  expect(storyWorkspaceWorkflowContextLabel('cancelled')).toBe('已取消');
});
