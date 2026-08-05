// [Input] Dream workbench and Story Workspace router sources.
// [Output] Static regression coverage for canonical re-entry and context ownership.
// [Pos] Story Workspace Dream re-entry Node seam (U2 Red).

// @ts-expect-error Playwright has Node built-ins; the browser app tsconfig intentionally omits Node types.
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import { resolveRunDeepLink } from '../../../hooks/story-workspace/useRunDeepLink';
import { storyWorkspaceDreamResolvedRunId } from '../../../router/storyWorkspacePath';

const LAUNCH_SOURCE = readFileSync(new URL('../StoryWorkspaceDreamLaunch.tsx', import.meta.url), 'utf8');
const ROUTER_SOURCE = readFileSync(new URL('../../../router/story-workspace.tsx', import.meta.url), 'utf8');
const LAYOUT_SOURCE = readFileSync(new URL('../../../components/story-workspace/layout/StoryWorkspaceLayout.tsx', import.meta.url), 'utf8');
const DECK_SOURCE = readFileSync(new URL('../../../components/DeckEditorModal.tsx', import.meta.url), 'utf8');
const APP_SOURCE = readFileSync(new URL('../../../App.tsx', import.meta.url), 'utf8');

test('no-run Dream workbench renders durable re-entry list before the new Dream form', () => {
  expect(LAUNCH_SOURCE).toContain('useStoryWorkspaceDreamRuns');
  expect(LAUNCH_SOURCE).toContain('进行中的 Dream');
  expect(LAUNCH_SOURCE).toContain('最近的 Dream');
  expect(LAUNCH_SOURCE).toContain('story-workspace-dream-reentry');
  expect(LAUNCH_SOURCE).not.toContain('localStorage');
});

test('Dream route removes the top WorkflowContextBar while non-Dream route support remains', () => {
  expect(ROUTER_SOURCE).toContain('workflowContext={isDreamRoute\n        ? null');
  expect(LAYOUT_SOURCE).toContain('<WorkflowContextBar {...workflowContext} />');
});

test('Deck editor offers only canonical Dream workbench navigation', () => {
  expect(DECK_SOURCE).toContain('onOpenDreamWithDeck');
  expect(APP_SOURCE).toContain('/story-workspace/dream?deck=');
  expect(DECK_SOURCE).not.toContain('ChatView');
});

test('403/404 deep links resolve to no run so Dream renders the recovery workbench, never a raw run page', async () => {
  for (const status of [403, 404]) {
    const resolution = await resolveRunDeepLink('run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', {
      getRun: async () => { throw new Error(String(status)); },
    });
    expect(resolution.status).toBe('missing');
  }
  expect(storyWorkspaceDreamResolvedRunId(null)).toBeNull();
  expect(storyWorkspaceDreamResolvedRunId({
    workflow_run_id: 'run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  })).toBe('run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
  expect(ROUTER_SOURCE).toContain('storyWorkspaceDreamPathWithoutRun');
});
