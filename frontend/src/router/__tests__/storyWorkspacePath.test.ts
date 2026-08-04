// [Input] Synthetic pathnames / search strings (Playwright node-side runner).
// [Output] Contract tests for the story-workspace state-router path seams
//          (Task 5 Step 0, C10): parameterized segment matching for
//          /story-workspace/runs/:storyWorkspaceRunId/execution and
//          /story-workspace/episodes/:storyWorkspaceEpisodeId/review, query
//          parsing/retention, and the unified ?run= deep-link param seam
//          (absorbing Task 4 R2's local URLSearchParams parsing).
// [Pos] story-workspace router path test node (Task 5 Step 0)
// [Sync] 2026-08-04: initial coverage — resolution seams only; history
//                    pushState/replaceState integration stays in the tsx
//                    adapter (window-dependent, not node-testable).

import { expect, test } from '@playwright/test';
import { storyWorkspaceExecutionDeepLink } from '../../components/story-workspace/surfaceLink';
import {
  matchStoryWorkspaceRoutePattern,
  parseStoryWorkspaceRunParam,
  resolveStoryWorkspacePath,
  storyWorkspaceDreamStageForRoute,
  storyWorkspaceAllowsLegacyReviewPanel,
  STORY_WORKSPACE_PATHS,
  STORY_WORKSPACE_ROUTE_PATTERNS,
  storyWorkspaceEpisodeReviewPath,
  storyWorkspaceExecutionPath,
} from '../storyWorkspacePath';

test('static routes resolve exactly as before (no regression)', () => {
  expect(resolveStoryWorkspacePath('/story-workspace')).toMatchObject({
    canonicalPath: STORY_WORKSPACE_PATHS.dream,
    route: 'dream',
    params: {},
  });
  expect(resolveStoryWorkspacePath('/story-workspace/dashboard')).toMatchObject({
    canonicalPath: STORY_WORKSPACE_PATHS.dream,
    route: 'dream',
  });
  expect(resolveStoryWorkspacePath('/story-workspace/dream')).toMatchObject({
    route: 'dream',
  });
  expect(resolveStoryWorkspacePath('/story-workspace/dream/')).toMatchObject({
    canonicalPath: STORY_WORKSPACE_PATHS.dream,
    route: 'dream',
  });
  expect(resolveStoryWorkspacePath('/story-workspace/stories')).toMatchObject({ route: 'stories' });
  expect(resolveStoryWorkspacePath('/story-workspace/characters')).toMatchObject({ route: 'characters' });
  expect(resolveStoryWorkspacePath('/story-workspace/scenes')).toMatchObject({ route: 'scenes' });
});

test('run-bound character and scene routes target their Dream file stages', () => {
  const characters = resolveStoryWorkspacePath(
    '/story-workspace/characters',
    '?run=run_characters',
  );
  const scenes = resolveStoryWorkspacePath('/story-workspace/scenes', '?run=run_scenes');
  const characterList = resolveStoryWorkspacePath('/story-workspace/characters');

  expect(characters && storyWorkspaceDreamStageForRoute(characters)).toBe('characters');
  expect(scenes && storyWorkspaceDreamStageForRoute(scenes)).toBe('scenes');
  expect(characterList && storyWorkspaceDreamStageForRoute(characterList)).toBeNull();
});

test('Dream run surfaces never mount the legacy review panel', () => {
  const cases = [
    resolveStoryWorkspacePath('/story-workspace/dream'),
    resolveStoryWorkspacePath('/story-workspace/dream', '?run=run_1'),
    resolveStoryWorkspacePath('/story-workspace/characters', '?run=run_1'),
    resolveStoryWorkspacePath('/story-workspace/scenes', '?run=run_1'),
    resolveStoryWorkspacePath('/story-workspace/runs/run_1/execution'),
  ];
  expect(cases.every((match) => match && !storyWorkspaceAllowsLegacyReviewPanel(match))).toBe(true);
  expect(storyWorkspaceAllowsLegacyReviewPanel(
    resolveStoryWorkspacePath('/story-workspace/characters')!,
  )).toBe(true);
  expect(storyWorkspaceAllowsLegacyReviewPanel(
    resolveStoryWorkspacePath('/story-workspace/stories')!,
  )).toBe(true);
});

test('execution route resolves with the run id param (C10-②)', () => {
  const match = resolveStoryWorkspacePath('/story-workspace/runs/run_abc123/execution');
  expect(match).not.toBeNull();
  expect(match?.route).toBe('run-execution');
  expect(match?.params).toEqual({ storyWorkspaceRunId: 'run_abc123' });
  expect(match?.canonicalPath).toBe('/story-workspace/runs/run_abc123/execution');
});

test('execution route decodes URI-encoded params', () => {
  const match = resolveStoryWorkspacePath('/story-workspace/runs/run%20x%2Fy/execution');
  expect(match?.params).toEqual({ storyWorkspaceRunId: 'run x/y' });
});

test('episode review route resolves with the episode id param (C10-②)', () => {
  const match = resolveStoryWorkspacePath('/story-workspace/episodes/ep1/review');
  expect(match).not.toBeNull();
  expect(match?.route).toBe('episode-review');
  expect(match?.params).toEqual({ storyWorkspaceEpisodeId: 'ep1' });
  expect(match?.canonicalPath).toBe('/story-workspace/episodes/ep1/review');
});

test('query string is parsed and carried on the match (C10-③)', () => {
  const withRun = resolveStoryWorkspacePath('/story-workspace/dream', '?run=r1&foo=bar');
  expect(withRun?.query.get('run')).toBe('r1');
  expect(withRun?.query.get('foo')).toBe('bar');

  const execution = resolveStoryWorkspacePath('/story-workspace/runs/r1/execution', '?tab=assets');
  expect(execution?.query.get('tab')).toBe('assets');

  const noSearch = resolveStoryWorkspacePath('/story-workspace/dream');
  expect(noSearch?.query.toString()).toBe('');
});

test('parameterized patterns reject partial / extra segments', () => {
  expect(resolveStoryWorkspacePath('/story-workspace/runs/run_abc')).toBeNull();
  expect(resolveStoryWorkspacePath('/story-workspace/runs/run_abc/execution/extra')).toBeNull();
  expect(resolveStoryWorkspacePath('/story-workspace/runs//execution')).toBeNull();
  expect(resolveStoryWorkspacePath('/story-workspace/episodes/ep1')).toBeNull();
  expect(resolveStoryWorkspacePath('/story-workspace/episodes/ep1/review/2')).toBeNull();
  expect(resolveStoryWorkspacePath('/story-workspace/unknown')).toBeNull();
  expect(resolveStoryWorkspacePath('/other/route')).toBeNull();
});

test('pattern matcher compares segments literally outside :param slots', () => {
  expect(
    matchStoryWorkspaceRoutePattern(
      STORY_WORKSPACE_ROUTE_PATTERNS['run-execution'],
      '/story-workspace/runs/r1/execution',
    ),
  ).toEqual({ storyWorkspaceRunId: 'r1' });
  expect(
    matchStoryWorkspaceRoutePattern(
      STORY_WORKSPACE_ROUTE_PATTERNS['run-execution'],
      '/story-workspace/runs/r1/review',
    ),
  ).toBeNull();
  expect(
    matchStoryWorkspaceRoutePattern(
      STORY_WORKSPACE_ROUTE_PATTERNS['episode-review'],
      '/story-workspace/episodes/ep1/review',
    ),
  ).toEqual({ storyWorkspaceEpisodeId: 'ep1' });
});

test('canonical path builders stay identical to the surface-link deep links', () => {
  expect(storyWorkspaceExecutionPath('r1')).toBe('/story-workspace/runs/r1/execution');
  expect(storyWorkspaceExecutionPath('r 1')).toBe('/story-workspace/runs/r%201/execution');
  // Router matching and Task 4 deep-link generation must never diverge (Task 4
  // record handoff note).
  expect(storyWorkspaceExecutionPath('r1')).toBe(storyWorkspaceExecutionDeepLink('r1'));
  expect(storyWorkspaceEpisodeReviewPath('ep1')).toBe('/story-workspace/episodes/ep1/review');
  expect(storyWorkspaceEpisodeReviewPath('ep 1')).toBe('/story-workspace/episodes/ep%201/review');
});

test('parseStoryWorkspaceRunParam is the unified ?run= seam (absorbs Task 4 R2)', () => {
  expect(parseStoryWorkspaceRunParam('?run=r1')).toBe('r1');
  expect(parseStoryWorkspaceRunParam('?foo=1&run=r2&bar=2')).toBe('r2');
  expect(parseStoryWorkspaceRunParam('?run=%2Frun%20x')).toBe('/run x');
  expect(parseStoryWorkspaceRunParam('')).toBeNull();
  expect(parseStoryWorkspaceRunParam('?foo=1')).toBeNull();
  expect(parseStoryWorkspaceRunParam('?run=')).toBeNull();
  expect(parseStoryWorkspaceRunParam('?run=%20')).toBeNull();
});
