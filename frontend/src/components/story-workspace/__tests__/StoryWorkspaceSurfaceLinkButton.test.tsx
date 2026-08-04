// [Input] Synthetic surface link props (Playwright node-side runner; component
//          render smoke via react-dom/server).
// [Output] Contract tests for StoryWorkspaceSurfaceLinkButton: the four Dream
//          lifecycle bridge stages plus hidden legacy aggregate states.
// [Pos] story-workspace surface link test node (Task 4 Step 1)
// [Sync] 2026-08-04: initial coverage - resolution seam + render smoke.

import { expect, test } from '@playwright/test';
import type {
  StoryWorkspaceSurface,
  StoryWorkspaceSurfaceLinkStage,
} from '../../../hooks/story-workspace';
import {
  resolveStoryWorkspaceSurfaceLink,
  SURFACE_LINK_LABELS,
  storyWorkspaceExecutionDeepLink,
  storyWorkspaceReviewDeepLink,
  type StoryWorkspaceSurfaceLinkButtonProps,
} from '../surfaceLink';
import { StoryWorkspaceSurfaceLinkButton } from '../StoryWorkspaceSurfaceLinkButton';

const DREAM_SURFACE: StoryWorkspaceSurface = {
  name: 'dream',
  protocol_dir: '.dream',
  entry_route: '/story-workspace/dream',
};

function props(overrides: Partial<StoryWorkspaceSurfaceLinkButtonProps> = {}): StoryWorkspaceSurfaceLinkButtonProps {
  return {
    surfaces: [DREAM_SURFACE],
    runId: 'r1',
    episodeId: 'ep1',
    state: { stage: 'pending_review' },
    ...overrides,
  };
}

const STAGE_CASES: Array<[StoryWorkspaceSurfaceLinkStage, string, string]> = [
  ['pending_review', '打开 Dream 修改', '/story-workspace/episodes/ep1/review?run=r1'],
  ['confirmed', '进入后续执行', '/story-workspace/runs/r1/execution'],
  ['continuing', '查看执行内容', '/story-workspace/runs/r1/execution'],
  ['completed', '查看最新内容', '/story-workspace/runs/r1/execution'],
];

test('label table exposes only the four design_007 lifecycle bridge stages', () => {
  expect(Object.keys(SURFACE_LINK_LABELS).sort()).toEqual([
    'completed', 'confirmed', 'continuing', 'pending_review',
  ]);
});

for (const [stage, label, href] of STAGE_CASES) {
  test(`stage ${stage} resolves to "${label}" → ${href}`, () => {
    const model = resolveStoryWorkspaceSurfaceLink(props({ state: { stage } }));
    expect(model).toEqual({ primary: { label, href } });
  });
}

test('review deep link degrades to the surface entry_route when episodeId is missing', () => {
  const model = resolveStoryWorkspaceSurfaceLink(props({
    episodeId: null,
    state: { stage: 'pending_review' },
  }));
  expect(model?.primary.href).toBe('/story-workspace/dream?run=r1');
});

test('deep-link builders encode path/query segments', () => {
  expect(storyWorkspaceReviewDeepLink('r/1', 'ep?1')).toBe(
    '/story-workspace/episodes/ep%3F1/review?run=r%2F1',
  );
  expect(storyWorkspaceExecutionDeepLink('r 1')).toBe('/story-workspace/runs/r%201/execution');
});

test('hidden when the session has no dream surface', () => {
  expect(resolveStoryWorkspaceSurfaceLink(props({ surfaces: undefined }))).toBeUndefined();
  expect(resolveStoryWorkspaceSurfaceLink(props({
    surfaces: [{ name: 'other', protocol_dir: '.other', entry_route: '/story-workspace/other' }],
  }))).toBeUndefined();
  expect(resolveStoryWorkspaceSurfaceLink(props({ surfaces: [] }))).toBeUndefined();
});

test('hidden when the resource is not bound to a run or aggregation is absent', () => {
  expect(resolveStoryWorkspaceSurfaceLink(props({ runId: null }))).toBeUndefined();
  expect(resolveStoryWorkspaceSurfaceLink(props({ runId: undefined }))).toBeUndefined();
  expect(resolveStoryWorkspaceSurfaceLink(props({ runId: '' }))).toBeUndefined();
  // The frontend never infers stage: without server-aggregated state the
  // button stays hidden instead of guessing.
  expect(resolveStoryWorkspaceSurfaceLink(props({ state: null }))).toBeUndefined();
  expect(resolveStoryWorkspaceSurfaceLink(props({ state: undefined }))).toBeUndefined();
});

test('legacy aggregate branches and replaced attempts stay outside Dream UI', () => {
  expect(resolveStoryWorkspaceSurfaceLink(props({ state: { stage: 'failed' } })))
    .toBeUndefined();
  expect(resolveStoryWorkspaceSurfaceLink(props({ state: { stage: 'rejected' } })))
    .toBeUndefined();
  expect(resolveStoryWorkspaceSurfaceLink(props({
    state: { stage: 'pending_review', superseded: true, latestRunId: 'r2' },
  }))).toBeUndefined();
  expect(resolveStoryWorkspaceSurfaceLink(props({
    state: { stage: 'pending_review', superseded: true },
  }))).toBeUndefined();
  expect(resolveStoryWorkspaceSurfaceLink(props({
    state: { stage: 'pending_review', superseded: true, latestRunId: 'r1' },
  }))).toBeUndefined();
});

test('component renders content when visible and null when hidden', () => {
  // The node-side runner's JSX runtime is incompatible with react-dom/server,
  // so render coverage is limited to the null/non-null boundary; label/href
  // semantics are fully covered by resolveStoryWorkspaceSurfaceLink above.
  expect(StoryWorkspaceSurfaceLinkButton(props({ state: { stage: 'confirmed' } }))).not.toBeNull();
  expect(StoryWorkspaceSurfaceLinkButton(props({
    state: { stage: 'pending_review', superseded: true, latestRunId: 'r2' },
  }))).toBeNull();
  expect(StoryWorkspaceSurfaceLinkButton(props({ surfaces: undefined }))).toBeNull();
  expect(StoryWorkspaceSurfaceLinkButton(props({ state: null }))).toBeNull();
});
