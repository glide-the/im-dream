// [Input] Actor-scoped canonical Dream run collection payloads.
// [Output] Strict transport parsing that preserves the server-provided group and order.
// [Pos] Story Workspace Dream re-entry Node seam (U2 Red).

import { expect, test } from '@playwright/test';
import {
  storyWorkspaceParseDreamRuns,
  storyWorkspaceDreamRunsEndpoint,
} from '../useStoryWorkspaceDreamRuns';

const response = {
  runs: [
    {
      storyWorkspaceRunId: 'run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      deckId: 'deck-a',
      deckDisplayName: '雨夜站台',
      workflowDisplayName: 'Dream',
      deckPluginVersion: '1.4.0',
      lifecycle: 'waiting_confirmation',
      group: 'in_progress',
      stageRevisions: { characters: 1, scenes: 1, storyboards: 1 },
      confirmationAccepted: false,
      confirmationDispatched: false,
      lastActivityAt: '2026-08-05T10:00:00Z',
      createdAt: '2026-08-05T09:00:00Z',
      sortKey: '01:2026-08-05T10:00:00Z:2026-08-05T09:00:00Z:run_a',
      href: '/story-workspace/dream?run=run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    },
    {
      storyWorkspaceRunId: 'run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
      deckId: 'deck-b',
      deckDisplayName: '海边旧城',
      workflowDisplayName: 'Dream',
      deckPluginVersion: '1.4.0',
      lifecycle: 'recent',
      group: 'recent',
      stageRevisions: { characters: 1, scenes: 1, storyboards: 1 },
      confirmationAccepted: true,
      confirmationDispatched: true,
      lastActivityAt: '2026-08-04T10:00:00Z',
      createdAt: '2026-08-04T09:00:00Z',
      sortKey: '03:2026-08-04T10:00:00Z:2026-08-04T09:00:00Z:run_b',
      href: '/story-workspace/dream?run=run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    },
  ],
};

test('canonical Dream runs endpoint and parser preserve server ordering', () => {
  expect(storyWorkspaceDreamRunsEndpoint).toBe('/api/story-workspace/dream-runs');
  const parsed = storyWorkspaceParseDreamRuns(response);
  expect(parsed.runs.map((run) => run.storyWorkspaceRunId)).toEqual([
    'run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
  ]);
  expect(parsed.runs.map((run) => run.group)).toEqual(['in_progress', 'recent']);
});

test('canonical Dream runs parser rejects browser-invented lifecycle/group combinations', () => {
  expect(() => storyWorkspaceParseDreamRuns({
    runs: [{ ...response.runs[0], lifecycle: 'recent', group: 'in_progress' }],
  })).toThrow(/recent/i);
});
