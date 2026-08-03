// [Input] Synthetic run snapshots / execution projections (Playwright
//          node-side runner; component smoke via direct function-component
//          calls on hook-free leaves).
// [Output] Contract tests for the standalone execution page (Task 5,
//          design_004 §5): Gate redirect for unconfirmed runs (§5.5), the
//          five-state UI resolution (§5.4; awaiting-guidance is a projection
//          state, never a RunStatus), guidable-status gating, and state copy
//          required by the plan (任务进度 / 等待你的指导 / 执行完成 /
//          重试失败步骤 / 先完成审阅确认).
// [Pos] story-workspace execution page test node (Task 5 Step 1)
// [Sync] 2026-08-04: initial coverage — resolution seams + hook-free leaf
//                    component smoke; the routed page/sidebar carry hooks and
//                    are covered through these seams (Task 2/4 node-side
//                    precedent).

import { expect, test } from '@playwright/test';
import type { WorkflowRun, WorkflowRunStatus } from '../../../api/storyWorkspaceApi';
import {
  isStoryWorkspaceGuidableStatus,
  resolveStoryWorkspaceExecutionRedirect,
  resolveStoryWorkspaceExecutionState,
  STORY_WORKSPACE_EXECUTION_STATE_COPY,
} from '../../../components/story-workspace/executionState';
import { StoryWorkspaceExecutionAssetPanel } from '../../../components/story-workspace/StoryWorkspaceExecutionAssetPanel';
import { StoryWorkspaceExecutionProgressTable } from '../../../components/story-workspace/StoryWorkspaceExecutionProgressTable';
import type {
  StoryWorkspaceExecutionProjection,
} from '../../../hooks/story-workspace/contracts';

function runWith(status: WorkflowRunStatus): Pick<WorkflowRun, 'status'> {
  return { status };
}

function projection(overrides: Partial<StoryWorkspaceExecutionProjection> = {}): StoryWorkspaceExecutionProjection {
  return {
    run_id: 'r1',
    phase: 'continuing',
    steps: [],
    assets_ref: null,
    events: [],
    ...overrides,
  };
}

const NOT_CONFIRMED_STATUSES: WorkflowRunStatus[] = [
  'preflight',
  'queued',
  'running',
  'output_validating',
  'pending_review',
  'rejected',
];

test('unconfirmed / rejected runs resolve to the not-confirmed gate state (§5.5)', () => {
  for (const status of NOT_CONFIRMED_STATUSES) {
    expect(resolveStoryWorkspaceExecutionState(runWith(status), null)).toBe('not-confirmed');
  }
});

test('gate redirect targets the review deep link and carries the run (§5.5)', () => {
  expect(resolveStoryWorkspaceExecutionRedirect('r1', 'ep1'))
    .toBe('/story-workspace/episodes/ep1/review?run=r1');
  // Without an episode binding the deep link degrades to the Dream entry route
  // carrying ?run= (design_004 §4.4 degradation, reused from Task 4).
  expect(resolveStoryWorkspaceExecutionRedirect('r1'))
    .toBe('/story-workspace/dream?run=r1');
  expect(resolveStoryWorkspaceExecutionRedirect('r 1')).toContain('run=r%201');
});

test('confirmed and post-gate runs render the five-state UI (§5.4)', () => {
  // confirmed = Gate step 4 passed, execution not yet continuing → progress view.
  expect(resolveStoryWorkspaceExecutionState(runWith('confirmed'), null)).toBe('continuing');
  expect(resolveStoryWorkspaceExecutionState(runWith('continuing'), null)).toBe('continuing');
  expect(resolveStoryWorkspaceExecutionState(runWith('completed'), null)).toBe('completed');
  expect(resolveStoryWorkspaceExecutionState(runWith('failed'), null)).toBe('failed');
  // cancelled is a post-Gate terminal state the §5.4 table does not enumerate;
  // it renders its own terminal notice instead of redirecting (documented).
  expect(resolveStoryWorkspaceExecutionState(runWith('cancelled'), null)).toBe('cancelled');
});

test('awaiting-guidance is inferred from continuing + projection, never a RunStatus (D13)', () => {
  expect(
    resolveStoryWorkspaceExecutionState(runWith('continuing'), projection({ phase: 'awaiting-guidance' })),
  ).toBe('awaiting-guidance');
  expect(
    resolveStoryWorkspaceExecutionState(
      runWith('continuing'),
      projection({ steps: [{ name: 's2', status: 'blocked' }] }),
    ),
  ).toBe('awaiting-guidance');
  expect(
    resolveStoryWorkspaceExecutionState(
      runWith('continuing'),
      projection({ steps: [{ name: 's2', blocked: true }] }),
    ),
  ).toBe('awaiting-guidance');
  // A non-continuing run never upgrades to awaiting-guidance.
  expect(
    resolveStoryWorkspaceExecutionState(runWith('completed'), projection({ phase: 'awaiting-guidance' })),
  ).toBe('completed');
  // Without a projection the state degrades to plain continuing (no endpoint yet).
  expect(resolveStoryWorkspaceExecutionState(runWith('continuing'), null)).toBe('continuing');
});

test('state copy carries the plan-required five-state texts', () => {
  expect(STORY_WORKSPACE_EXECUTION_STATE_COPY.continuing.badge).toBe('执行中');
  expect(STORY_WORKSPACE_EXECUTION_STATE_COPY['awaiting-guidance'].banner).toContain('等待你的指导');
  expect(STORY_WORKSPACE_EXECUTION_STATE_COPY.completed.banner).toContain('执行完成');
  expect(STORY_WORKSPACE_EXECUTION_STATE_COPY.failed.banner).toContain('重试失败步骤');
  expect(STORY_WORKSPACE_EXECUTION_STATE_COPY['not-confirmed'].banner).toContain('先完成审阅确认');
});

test('guidable statuses match the Task 3 endpoint contract (continuing/failed)', () => {
  expect(isStoryWorkspaceGuidableStatus('continuing')).toBe(true);
  expect(isStoryWorkspaceGuidableStatus('failed')).toBe(true);
  for (const status of NOT_CONFIRMED_STATUSES) {
    expect(isStoryWorkspaceGuidableStatus(status)).toBe(false);
  }
  expect(isStoryWorkspaceGuidableStatus('completed')).toBe(false);
  expect(isStoryWorkspaceGuidableStatus('cancelled')).toBe(false);
});

test('hook-free leaf components render (direct function-component smoke)', () => {
  const progress = StoryWorkspaceExecutionProgressTable({
    run: runWith('continuing') as WorkflowRun,
    projection: null,
  });
  expect(progress).toBeTruthy();

  const assets = StoryWorkspaceExecutionAssetPanel({
    run: runWith('completed') as WorkflowRun,
    projection: null,
  });
  expect(assets).toBeTruthy();
});
