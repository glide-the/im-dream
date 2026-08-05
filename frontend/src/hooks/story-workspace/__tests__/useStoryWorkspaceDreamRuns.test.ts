// [Input] Actor-scoped canonical Dream run collection payloads.
// [Output] Strict transport parsing that preserves the server-provided group and order.
// [Pos] Story Workspace Dream re-entry Node seam (U2 Red).

import { expect, test } from '@playwright/test';
import {
  storyWorkspaceParseDreamRuns,
  storyWorkspaceDreamRunsEndpoint,
} from '../useStoryWorkspaceDreamRuns';
import { storyWorkspaceFetchDreamRuns } from '../../../api/storyWorkspaceApi';

const response = {
  runs: [
    {
      storyWorkspaceRunId: 'run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      goalPrefix: '创作一个发生在雨夜车站的短篇故事',
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
      goalPrefix: '写一个关于海边旧城重逢的故事',
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

test('Dream runs from a pre-goalPrefix backend remain visible with the Deck title fallback', () => {
  const parsed = storyWorkspaceParseDreamRuns({
    runs: [{ ...response.runs[0], goalPrefix: undefined }],
  });
  expect(parsed.runs[0].goalPrefix).toBe('雨夜站台');
});

test('canonical Dream runs parser rejects browser-invented lifecycle/group combinations', () => {
  expect(() => storyWorkspaceParseDreamRuns({
    runs: [{ ...response.runs[0], lifecycle: 'recent', group: 'in_progress' }],
  })).toThrow(/recent/i);
});

test('canonical Dream runs parser rejects malformed IDs, unsafe booleans, unexpected stage keys and href drift', () => {
  const malformed = [
    { storyWorkspaceRunId: 'not-a-run' },
    { workflowDisplayName: 'Other workflow' },
    { confirmationAccepted: 'false' },
    { stageRevisions: { characters: 1, scenes: 1, storyboards: 1, raw: 1 } },
    { href: '/story-workspace/dream?run=run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' },
  ];
  for (const patch of malformed) {
    expect(() => storyWorkspaceParseDreamRuns({
      runs: [{ ...response.runs[0], ...patch }],
    })).toThrow();
  }
});

test('Dream run parser fails closed on naive dates and bounded display metadata', () => {
  const malformed = [
    { lastActivityAt: '2026-08-05T10:00:00' },
    { createdAt: 'not-a-date' },
    { goalPrefix: '' },
    { goalPrefix: 'x'.repeat(81) },
    { deckId: 'x'.repeat(256) },
    { deckDisplayName: 'x'.repeat(256) },
    { deckPluginVersion: 'x'.repeat(256) },
    { sortKey: 'x'.repeat(513) },
  ];
  for (const patch of malformed) {
    expect(() => storyWorkspaceParseDreamRuns({
      runs: [{ ...response.runs[0], ...patch }],
    })).toThrow();
  }
});

test('Dream run collection transport forwards an AbortSignal', async () => {
  const controller = new AbortController();
  let seenSignal: AbortSignal | null = null;
  await storyWorkspaceFetchDreamRuns({
    endpoint: storyWorkspaceDreamRunsEndpoint,
    token: null,
    signal: controller.signal,
    fetchImpl: async (_url, init) => {
      seenSignal = init?.signal as AbortSignal;
      return new Response(JSON.stringify(response), { status: 200 });
    },
  });
  expect(seenSignal).toBe(controller.signal);
});
