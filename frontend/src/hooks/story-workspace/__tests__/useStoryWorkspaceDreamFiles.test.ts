// [Input] Synthetic Dream file projections, fetch responses, lifecycle states,
//         and story-workspace output notifications.
// [Output] Node-side contract coverage for the run-scoped Dream read seam.
// [Pos] story-workspace Dream file hook test node (Task 3 F2)

import { expect, test } from '@playwright/test';
import {
  dreamFilesEndpoint,
  fetchStoryWorkspaceDreamFiles,
  parseStoryWorkspaceDreamFiles,
  reduceStoryWorkspaceDreamFilesFetch,
  shouldInvalidateStoryWorkspaceDreamFiles,
  shouldPollStoryWorkspaceDreamFiles,
} from '../useStoryWorkspaceDreamFiles';

const RUN_ID = `run_${'1'.repeat(32)}`;

function fullProjection() {
  const item = {
    entityId: 'lead',
    displayName: '主角',
    summary: '人物摘要',
    sourceFile: 'assets/characters/lead.md',
    relations: [],
  };
  return {
    storyWorkspaceRunId: RUN_ID,
    threadId: 'thread-1',
    source: {
      deckPluginBindingId: 'binding-1',
      bindingRevision: 2,
      deckPluginVersion: '1.2.3',
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
        page: {
          title: '人物',
          entryRoute: `/story-workspace/characters?run=${RUN_ID}`,
        },
        items: [item],
      },
      scenes: {
        stage: 'scenes',
        revision: 1,
        sourceFiles: ['assets/scenes/home.md'],
        page: {
          title: '场景',
          entryRoute: `/story-workspace/scenes?run=${RUN_ID}`,
        },
        items: [{ ...item, entityId: 'home', sourceFile: 'assets/scenes/home.md' }],
      },
      storyboards: {
        stage: 'storyboards',
        revision: 3,
        sourceFiles: ['stories/demo/episodes/EP01/storyboard.yaml'],
        page: {
          title: '分镜',
          entryRoute: `/story-workspace/runs/${RUN_ID}/execution`,
        },
        items: [{
          ...item,
          entityId: 'shot-1',
          sourceFile: 'stories/demo/episodes/EP01/storyboard.yaml',
        }],
      },
    },
    confirmationAccepted: false,
    confirmationDispatched: false,
    canConfirm: true,
    confirmationLabel: '确认并继续',
  };
}

test('builds the canonical run-scoped endpoint', () => {
  expect(dreamFilesEndpoint(RUN_ID)).toBe(
    `/api/story-workspace/workflow-runs/${RUN_ID}/dream-files`,
  );
  expect(dreamFilesEndpoint('run/a?b')).toContain('run%2Fa%3Fb');
});

test('strictly parses waiting and complete camelCase projections', () => {
  const complete = parseStoryWorkspaceDreamFiles(fullProjection());
  expect(complete.canConfirm).toBe(true);
  expect(complete.confirmationAccepted).toBe(false);
  expect(complete.confirmationDispatched).toBe(false);
  expect(complete.stages.characters?.revision).toBe(2);

  const accepted = parseStoryWorkspaceDreamFiles({
    ...fullProjection(),
    confirmationAccepted: true,
    confirmationDispatched: false,
    canConfirm: false,
  });
  expect(accepted).toMatchObject({
    confirmationAccepted: true,
    confirmationDispatched: false,
    canConfirm: false,
  });

  const waiting = parseStoryWorkspaceDreamFiles({
    ...fullProjection(),
    runRevision: 0,
    stages: {},
    canConfirm: false,
  });
  expect(waiting.runRevision).toBe(0);
  expect(waiting.stages).toEqual({});

  expect(() => parseStoryWorkspaceDreamFiles({
    ...fullProjection(),
    requiredStages: ['characters', 'scenes', 'failed'],
  })).toThrow();
  expect(() => parseStoryWorkspaceDreamFiles({
    ...fullProjection(),
    stages: { characters: { ...fullProjection().stages.characters, revision: true } },
  })).toThrow();
  expect(() => parseStoryWorkspaceDreamFiles({
    ...fullProjection(),
    confirmationAccepted: true,
    confirmationDispatched: false,
    canConfirm: true,
  })).toThrow();
  expect(() => parseStoryWorkspaceDreamFiles({
    ...fullProjection(),
    confirmationAccepted: false,
    confirmationDispatched: true,
  })).toThrow();
  const withoutConfirmationFacts = { ...fullProjection() } as Record<string, unknown>;
  delete withoutConfirmationFacts.confirmationAccepted;
  expect(() => parseStoryWorkspaceDreamFiles(withoutConfirmationFacts)).toThrow();
});

test('fetch seam sends auth and rejects HTTP or malformed JSON', async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const fetchImpl = (async (url: unknown, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify(fullProjection()), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as unknown as typeof fetch;

  const projection = await fetchStoryWorkspaceDreamFiles('/api/dream', {
    fetchImpl,
    token: 'token-1',
  });
  expect(projection.storyWorkspaceRunId).toBe(RUN_ID);
  expect(new Headers(calls[0].init?.headers).get('Authorization')).toBe('Bearer token-1');
  expect(calls[0].init?.credentials).toBe('include');

  await expect(fetchStoryWorkspaceDreamFiles('/api/dream', {
    fetchImpl: (async () => new Response('{}', { status: 409 })) as unknown as typeof fetch,
  })).rejects.toThrow();
  await expect(fetchStoryWorkspaceDreamFiles('/api/dream', {
    fetchImpl: (async () => new Response('{bad', { status: 200 })) as unknown as typeof fetch,
  })).rejects.toThrow();
});

test('polling includes editing so Agent revision conflicts surface within five seconds', () => {
  expect(shouldPollStoryWorkspaceDreamFiles('story-workspace-dream-waiting-files')).toBe(true);
  expect(shouldPollStoryWorkspaceDreamFiles('story-workspace-dream-editing')).toBe(true);
  expect(shouldPollStoryWorkspaceDreamFiles('story-workspace-dream-continuing')).toBe(true);
  for (const state of [
    'story-workspace-dream-confirming',
    'story-workspace-dream-completed',
  ] as const) {
    expect(shouldPollStoryWorkspaceDreamFiles(state)).toBe(false);
  }
});

test('only same-run story-workspace output invalidates the REST snapshot', () => {
  expect(shouldInvalidateStoryWorkspaceDreamFiles({
    type: 'story-workspace-output',
    runId: RUN_ID,
    changedStages: ['characters'],
    revisions: { characters: 2 },
  }, RUN_ID)).toBe(true);
  expect(shouldInvalidateStoryWorkspaceDreamFiles({
    type: 'story-workspace-output',
    storyWorkspaceRunId: RUN_ID,
  }, RUN_ID)).toBe(true);
  expect(shouldInvalidateStoryWorkspaceDreamFiles({
    type: 'story-workspace-output',
    runId: `run_${'2'.repeat(32)}`,
  }, RUN_ID)).toBe(false);
  expect(shouldInvalidateStoryWorkspaceDreamFiles({
    type: 'story-workspace-output',
    story_id: 'legacy-proposal',
    review_status: 'pending',
  }, RUN_ID)).toBe(false);
});

test('fetch reducer ignores stale generations and preserves the last snapshot on error', () => {
  const projection = parseStoryWorkspaceDreamFiles(fullProjection());
  const initial = { data: null, error: null, isLoading: false, generation: 0 };
  const loading = reduceStoryWorkspaceDreamFilesFetch(initial, {
    type: 'start', generation: 2,
  });
  const stale = reduceStoryWorkspaceDreamFilesFetch(loading, {
    type: 'success', generation: 1, data: projection,
  });
  expect(stale).toEqual(loading);

  const loaded = reduceStoryWorkspaceDreamFilesFetch(loading, {
    type: 'success', generation: 2, data: projection,
  });
  const failed = reduceStoryWorkspaceDreamFilesFetch(loaded, {
    type: 'error', generation: 3, error: new Error('offline'),
  });
  expect(failed.data).toBe(projection);
  expect(failed.error?.message).toBe('offline');
});
