// [Input] Synthetic Episode artifact wire surfaces, HTTP snapshots, and invalidation hints.
// [Output] Node-side contract coverage for strict parsing, ETag polling, and last-good recovery.
// [Pos] Story Workspace Episode artifact query seam test (U5)

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses a built-in omitted from browser app types.
import { readFileSync } from 'node:fs';
import {
  StoryWorkspaceEpisodeArtifactsHttpError,
  storyWorkspaceEpisodeArtifactsEndpoint,
  storyWorkspaceEpisodeArtifactsPollInterval,
  storyWorkspaceFetchEpisodeArtifacts,
  storyWorkspaceIsEpisodeArtifactsAbort,
  storyWorkspaceReduceEpisodeArtifactsFetch,
  storyWorkspaceShouldInvalidateEpisodeArtifacts,
} from '../useStoryWorkspaceEpisodeArtifacts';
import {
  storyWorkspaceParseEpisodeArtifactSurface,
} from '../contracts';

const RUN_ID = `run_${'1'.repeat(32)}`;
const OTHER_RUN_ID = `run_${'2'.repeat(32)}`;
const EPISODE_ID = 'e'.repeat(32);
const EPISODE_VIEW_ID = 'a'.repeat(32);
const ARC_ID = 'b'.repeat(32);
const BEAT_ID = 'c'.repeat(32);
const SCENE_ID = 'd'.repeat(32);
const SHOT_VIEW_ID = 'f'.repeat(32);
const PROMPT_ID = '1'.repeat(32);
const QUEUE_ID = '2'.repeat(32);
const RENDER_SECTION_ID = '3'.repeat(32);
const REVIEW_SECTION_ID = '4'.repeat(32);
const REVIEW_TARGET_ID = '5'.repeat(32);
const REVISION_1 = `sha256:${'1'.repeat(64)}`;
const REVISION_2 = `sha256:${'2'.repeat(64)}`;
const REVISION_3 = `sha256:${'3'.repeat(64)}`;
const REVISION_4 = `sha256:${'4'.repeat(64)}`;
const REVISION_5 = `sha256:${'5'.repeat(64)}`;
const CONTENT_REVISION = `sha256:${'a'.repeat(64)}`;

const ARTIFACT_SPECS = [
  ['episode-outline.md', 'plan_episode', ['episode_overview', 'storyline_navigator', 'narrative_workbench']],
  ['script.md', 'write_script', ['narrative_workbench', 'shot_inspector']],
  ['storyboard.yaml', 'regenerate_storyboard', ['narrative_workbench', 'shot_inspector']],
  ['prompts/', 'generate_prompts', ['shot_inspector', 'prompt_view']],
  ['renders/', 'prepare_render_guide', ['shot_inspector', 'render_view']],
  ['review-report.md', 'review_full_chain', ['review_view', 'shot_inspector']],
] as const;

function coverage(linked = 0, total = 0) {
  return total === 0
    ? { availability: 'unavailable', linked: 0, total: 0, ratio: null }
    : { availability: 'available', linked, total, ratio: linked / total };
}

function artifacts(available: readonly string[] = []) {
  return ARTIFACT_SPECS.map(([relativeKey, producerAction, consumers]) => ({
    relativeKey,
    availability: available.includes(relativeKey) ? 'available' : 'not_generated',
    contentRevision: available.includes(relativeKey) ? CONTENT_REVISION : null,
    mtime: available.includes(relativeKey) ? '2026-08-06T01:02:03Z' : null,
    size: available.includes(relativeKey) ? 128 : null,
    producerAction,
    consumers: [...consumers],
  }));
}

function boundSurface(
  revision = REVISION_1,
  available: readonly string[] = [],
): Record<string, unknown> {
  return {
    runId: RUN_ID,
    opaqueEpisodeId: EPISODE_ID,
    manifestRevision: revision,
    etag: revision,
    bindingAvailability: 'bound',
    bindingRecovery: {
      autoRepairAttempted: false,
      canDispatch: true,
      publicReason: null,
    },
    artifacts: artifacts(available),
    narrative: {
      episodeId: EPISODE_VIEW_ID,
      storyArcId: ARC_ID,
      overview: {
        title: available.includes('episode-outline.md') ? '雨夜重逢' : null,
        series: null,
        storyGoals: available.includes('episode-outline.md') ? ['重新建立信任'] : [],
        coreConflict: null,
        hook: null,
        sourceArtifact: available.includes('episode-outline.md') ? 'episode-outline.md' : null,
        sourceRevision: available.includes('episode-outline.md') ? CONTENT_REVISION : null,
        generatedFrom: null,
        characterBeats: [],
      },
      narrativeBeats: available.includes('episode-outline.md') ? [{
        id: BEAT_ID,
        sourceKey: 'SC-01',
        title: '失去控制',
        assetSceneRef: null,
        narrativeFunction: '建立冲突',
        emotionTone: null,
        summary: '车站相遇。',
        sceneGoals: ['重逢'],
        keyDialogueBeats: [],
        sourceArtifact: 'episode-outline.md',
        sourceRevision: CONTENT_REVISION,
        generatedFrom: null,
      }] : [],
      scenes: available.includes('script.md') ? [{
        id: SCENE_ID,
        sourceKey: 'S01',
        title: '车站外',
        heading: '外景·车站·夜',
        assetSceneRef: null,
        narrativeBeatId: BEAT_ID,
        declaredNarrativeBeatRef: 'SC-01',
        associationStatus: 'linked',
        actions: ['她停下脚步。'],
        dialogue: [{ speaker: '林默', qualifier: null, text: '你来了。' }],
        cameraCues: [],
        sourceArtifact: 'script.md',
        sourceRevision: CONTENT_REVISION,
        generatedFrom: null,
      }] : [],
      shots: available.includes('storyboard.yaml') ? [{
        id: SHOT_VIEW_ID,
        shotId: 'S01-E01-C01-SH001',
        assetSceneRef: null,
        declaredScriptSceneRef: 'S01',
        declaredNarrativeBeatRef: 'SC-01',
        scriptSceneId: SCENE_ID,
        narrativeBeatId: BEAT_ID,
        associationStatus: 'linked',
        shotType: 'medium',
        characters: [{
          ref: 'mc-01',
          displayName: '林默',
          depthPlane: 'front',
          action: '停步',
          emotion: '克制',
        }],
        camera: { angle: 'eye', height: null, movement: 'static', lens: '50mm' },
        visual: '雨夜车站。',
        dialogue: [{ speaker: '林默', line: '你来了。', type: 'spoken' }],
        timing: { durationSec: 3, transitionIn: null, transitionOut: 'cut' },
        sourceArtifact: 'storyboard.yaml',
        sourceRevision: CONTENT_REVISION,
        generatedFrom: 'script@v1',
      }] : [],
      associations: {
        beatSceneCoverage: coverage(
          available.includes('script.md') ? 1 : 0,
          available.includes('script.md') ? 1 : 0,
        ),
        sceneShotCoverage: coverage(
          available.includes('storyboard.yaml') ? 1 : 0,
          available.includes('storyboard.yaml') ? 1 : 0,
        ),
        missingLinks: [],
        orphanArtifacts: [],
      },
    },
    auxiliary: {
      manifestRevision: revision,
      prompts: {
        items: available.includes('prompts/') ? [{
          id: PROMPT_ID,
          shotId: 'S01-E01-C01-SH001',
          kind: 'video',
          shotViewId: SHOT_VIEW_ID,
          associationStatus: 'linked',
          positive: '雨夜车站，中景。',
          negative: null,
          parameters: {
            model: null,
            mode: null,
            durationSec: 3,
            motionStrength: null,
            cameraMotion: 'static',
            aspectRatio: '16:9',
          },
          generability: {
            characterAnchor: null,
            motionFeasibility: null,
            durationBudget: null,
            notes: null,
          },
          sourceArtifact: 'prompts/ep001-prompts.yml',
          sourceRevision: CONTENT_REVISION,
        }] : [],
        total: available.includes('prompts/') ? 1 : 0,
        nextCursor: null,
      },
      renderGuide: available.includes('renders/') ? {
        sections: [{
          id: RENDER_SECTION_ID,
          level: 2,
          title: '制作指导',
          text: '按镜头队列生成。',
          sourceArtifact: 'renders/render-guide.md',
          sourceRevision: CONTENT_REVISION,
        }],
        queue: {
          items: [{
            id: QUEUE_ID,
            shotId: 'S01-E01-C01-SH001',
            shotViewId: SHOT_VIEW_ID,
            associationStatus: 'linked',
            durationSec: 3,
            risk: null,
            priority: 'P1',
            renderer: null,
            status: 'pending',
            sourceArtifact: 'renders/render-guide.md',
            sourceRevision: CONTENT_REVISION,
          }],
          total: 1,
          nextCursor: null,
        },
        sourceArtifact: 'renders/render-guide.md',
        sourceRevision: CONTENT_REVISION,
      } : null,
      review: available.includes('review-report.md') ? {
        scope: 'full-chain',
        overallVerdict: 'APPROVED',
        reviewedArtifacts: ['script.md', 'storyboard.yaml'],
        sourceRevisions: [{ sourceArtifact: 'script.md', sourceRevision: CONTENT_REVISION }],
        sections: [{
          id: REVIEW_SECTION_ID,
          level: 2,
          title: '结论',
          text: '通过。',
          sourceArtifact: 'review-report.md',
          sourceRevision: CONTENT_REVISION,
        }],
        targets: [{
          id: REVIEW_TARGET_ID,
          kind: 'shot',
          sourceKey: 'S01-E01-C01-SH001',
          targetViewId: SHOT_VIEW_ID,
          associationStatus: 'linked',
          sectionId: REVIEW_SECTION_ID,
          sourceArtifact: 'review-report.md',
          sourceRevision: CONTENT_REVISION,
        }],
        sourceArtifact: 'review-report.md',
        sourceRevision: CONTENT_REVISION,
      } : null,
      associations: {
        shotPromptCoverage: coverage(
          available.includes('prompts/') ? 1 : 0,
          available.includes('storyboard.yaml') ? 1 : 0,
        ),
        shotRenderQueueCoverage: coverage(
          available.includes('renders/') ? 1 : 0,
          available.includes('storyboard.yaml') ? 1 : 0,
        ),
        totalPrompts: available.includes('prompts/') ? 1 : 0,
        totalQueueEntries: available.includes('renders/') ? 1 : 0,
        orphanPrompts: [],
        orphanQueueEntries: [],
        duplicateQueueShotIds: [],
      },
    },
  };
}

function unboundSurface(): Record<string, unknown> {
  return {
    runId: RUN_ID,
    opaqueEpisodeId: null,
    manifestRevision: null,
    etag: null,
    bindingAvailability: 'unbound',
    bindingRecovery: {
      autoRepairAttempted: true,
      canDispatch: false,
      publicReason: 'episode_binding_unproven',
    },
    artifacts: [],
    narrative: null,
    auxiliary: null,
  };
}

test('strictly parses missing, unbound, and each progressive Episode artifact revision', () => {
  const missing = storyWorkspaceParseEpisodeArtifactSurface(boundSurface());
  expect(missing.artifacts).toHaveLength(6);
  expect(missing.artifacts.every((artifact) => artifact.availability === 'not_generated')).toBe(true);

  const outline = storyWorkspaceParseEpisodeArtifactSurface(
    boundSurface(REVISION_1, ['episode-outline.md']),
  );
  expect(outline.narrative?.overview.title).toBe('雨夜重逢');
  expect(outline.narrative?.narrativeBeats).toHaveLength(1);
  expect(outline.narrative?.scenes).toEqual([]);

  const script = storyWorkspaceParseEpisodeArtifactSurface(
    boundSurface(REVISION_2, ['episode-outline.md', 'script.md']),
  );
  expect(script.narrative?.scenes[0]).toMatchObject({ id: SCENE_ID, narrativeBeatId: BEAT_ID });

  const storyboard = storyWorkspaceParseEpisodeArtifactSurface(
    boundSurface(REVISION_3, ['episode-outline.md', 'script.md', 'storyboard.yaml']),
  );
  expect(storyboard.narrative?.shots[0]).toMatchObject({
    id: SHOT_VIEW_ID,
    scriptSceneId: SCENE_ID,
  });

  const auxiliary = storyWorkspaceParseEpisodeArtifactSurface(boundSurface(REVISION_4, [
    'episode-outline.md',
    'script.md',
    'storyboard.yaml',
    'prompts/',
    'renders/',
    'review-report.md',
  ]));
  expect(auxiliary.auxiliary?.prompts.items[0]).toMatchObject({
    id: PROMPT_ID,
    shotViewId: SHOT_VIEW_ID,
  });
  expect(auxiliary.auxiliary?.renderGuide?.queue.items[0]).toMatchObject({
    id: QUEUE_ID,
    shotViewId: SHOT_VIEW_ID,
  });
  expect(auxiliary.auxiliary?.review?.targets[0]).toMatchObject({
    id: REVIEW_TARGET_ID,
    targetViewId: SHOT_VIEW_ID,
  });

  const unbound = storyWorkspaceParseEpisodeArtifactSurface(unboundSurface());
  expect(unbound.bindingAvailability).toBe('unbound');
  expect(unbound.artifacts).toEqual([]);
});

test('new revisions preserve stable entity identities without array-position inference', () => {
  const first = storyWorkspaceParseEpisodeArtifactSurface(boundSurface(REVISION_3, [
    'episode-outline.md', 'script.md', 'storyboard.yaml',
  ]));
  const second = storyWorkspaceParseEpisodeArtifactSurface(boundSurface(REVISION_4, [
    'episode-outline.md', 'script.md', 'storyboard.yaml', 'prompts/',
  ]));
  expect(second.narrative?.narrativeBeats[0].id).toBe(first.narrative?.narrativeBeats[0].id);
  expect(second.narrative?.scenes[0].id).toBe(first.narrative?.scenes[0].id);
  expect(second.narrative?.shots[0].id).toBe(first.narrative?.shots[0].id);
});

test('rejects unknown schema/enum, duplicate IDs, bad keys, inconsistent ETags, and path leaks', () => {
  expect(() => storyWorkspaceParseEpisodeArtifactSurface({
    ...boundSurface(),
    schema: 'episode-surface/v2',
  })).toThrow(/unknown field/i);

  expect(() => storyWorkspaceParseEpisodeArtifactSurface({
    ...boundSurface(),
    bindingAvailability: 'failed',
  })).toThrow(/bindingAvailability/i);

  const duplicate = boundSurface(REVISION_3, [
    'episode-outline.md', 'script.md', 'storyboard.yaml',
  ]);
  const narrative = duplicate.narrative as Record<string, unknown>;
  const shots = narrative.shots as Array<Record<string, unknown>>;
  narrative.shots = [shots[0], { ...shots[0] }];
  expect(() => storyWorkspaceParseEpisodeArtifactSurface(duplicate)).toThrow(/duplicate/i);

  const badKey = boundSurface();
  (badKey.artifacts as Array<Record<string, unknown>>)[0].relativeKey = '../episode-outline.md';
  expect(() => storyWorkspaceParseEpisodeArtifactSurface(badKey)).toThrow(/relativeKey/i);

  expect(() => storyWorkspaceParseEpisodeArtifactSurface({
    ...boundSurface(),
    etag: REVISION_2,
  })).toThrow(/etag/i);

  const leaked = boundSurface(REVISION_1, ['episode-outline.md']);
  const leakedNarrative = leaked.narrative as Record<string, unknown>;
  const overview = leakedNarrative.overview as Record<string, unknown>;
  overview.coreConflict = 'debug source: /Users/private/story/script.md';
  expect(() => storyWorkspaceParseEpisodeArtifactSurface(leaked)).toThrow(/sensitive path/i);
});

test('unbound surfaces cannot carry artifact content and available facts require metadata', () => {
  expect(() => storyWorkspaceParseEpisodeArtifactSurface({
    ...unboundSurface(),
    artifacts: artifacts(),
  })).toThrow(/unbound/i);

  const invalidAvailable = boundSurface();
  (invalidAvailable.artifacts as Array<Record<string, unknown>>)[0] = {
    ...(invalidAvailable.artifacts as Array<Record<string, unknown>>)[0],
    availability: 'available',
  };
  expect(() => storyWorkspaceParseEpisodeArtifactSurface(invalidAvailable)).toThrow(/metadata/i);
});

test('fetch seam sends a quoted If-None-Match and treats 304 as the same last-good snapshot', async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  let responseNumber = 0;
  const fetchImpl = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), init });
    responseNumber += 1;
    if (responseNumber === 2) return new Response(null, { status: 304 });
    return new Response(JSON.stringify(boundSurface()), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ETag: `"${REVISION_1}"` },
    });
  }) as typeof fetch;

  const first = await storyWorkspaceFetchEpisodeArtifacts('/api/episode', {
    fetchImpl,
    token: 'token-1',
  });
  expect(first.kind).toBe('surface');
  if (first.kind !== 'surface') throw new Error('expected a surface response');
  const second = await storyWorkspaceFetchEpisodeArtifacts('/api/episode', {
    fetchImpl,
    etag: first.data.etag,
  });
  expect(second).toEqual({ kind: 'not-modified', etag: REVISION_1 });
  expect(new Headers(calls[0].init?.headers).get('Authorization')).toBe('Bearer token-1');
  expect(new Headers(calls[1].init?.headers).get('If-None-Match')).toBe(`"${REVISION_1}"`);

  const initial = {
    runId: RUN_ID,
    data: null,
    diagnostic: null,
    error: null,
    isLoading: false,
    generation: 0,
  };
  const loaded = storyWorkspaceReduceEpisodeArtifactsFetch(initial, {
    type: 'success', runId: RUN_ID, generation: 1, data: first.data,
  });
  const unchanged = storyWorkspaceReduceEpisodeArtifactsFetch(loaded, {
    type: 'not-modified', runId: RUN_ID, generation: 2,
  });
  expect(unchanged.data).toBe(first.data);
});

test('invalid latest payload keeps only the mounted session last-good snapshot', () => {
  const good = storyWorkspaceParseEpisodeArtifactSurface(boundSurface());
  const initial = {
    runId: RUN_ID,
    data: null,
    diagnostic: null,
    error: null,
    isLoading: false,
    generation: 0,
  };
  const loaded = storyWorkspaceReduceEpisodeArtifactsFetch(initial, {
    type: 'success', runId: RUN_ID, generation: 1, data: good,
  });
  const diagnostic = { kind: 'invalid_payload' as const, message: 'Invalid Episode artifact surface.' };
  const stale = storyWorkspaceReduceEpisodeArtifactsFetch(loaded, {
    type: 'invalid', runId: RUN_ID, generation: 2, diagnostic,
  });
  expect(stale.data).toBe(good);
  expect(stale.diagnostic).toEqual(diagnostic);

  const refreshedHook = storyWorkspaceReduceEpisodeArtifactsFetch(initial, {
    type: 'invalid', runId: RUN_ID, generation: 1, diagnostic,
  });
  expect(refreshedHook.data).toBeNull();
  expect(refreshedHook.diagnostic?.kind).toBe('invalid_payload');

  const changedRun = storyWorkspaceReduceEpisodeArtifactsFetch(stale, {
    type: 'reset', runId: OTHER_RUN_ID,
  });
  expect(changedRun.data).toBeNull();
  expect(changedRun.diagnostic).toBeNull();
});

test('HTTP errors and aborts are safe and never parse response diagnostics as artifacts', async () => {
  for (const status of [401, 404, 422]) {
    await expect(storyWorkspaceFetchEpisodeArtifacts('/api/episode', {
      fetchImpl: (async () => new Response(JSON.stringify({
        detail: `/Users/private/${status}`,
      }), { status })) as typeof fetch,
    })).rejects.toMatchObject({
      name: 'StoryWorkspaceEpisodeArtifactsHttpError',
      status,
    });
  }
  expect(new StoryWorkspaceEpisodeArtifactsHttpError(404).message).not.toContain('/Users');

  const controller = new AbortController();
  const pending = storyWorkspaceFetchEpisodeArtifacts('/api/episode', {
    signal: controller.signal,
    fetchImpl: ((_: RequestInfo | URL, init?: RequestInit) => new Promise((_, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
    })) as typeof fetch,
  });
  controller.abort();
  await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  try {
    await pending;
  } catch (error) {
    expect(storyWorkspaceIsEpisodeArtifactsAbort(error)).toBe(true);
  }
});

test('polling is never faster than five seconds and SSE is identity-only invalidation', () => {
  expect(storyWorkspaceEpisodeArtifactsPollInterval()).toBe(5000);
  expect(storyWorkspaceEpisodeArtifactsPollInterval(10)).toBe(5000);
  expect(storyWorkspaceEpisodeArtifactsPollInterval(7000)).toBe(7000);
  expect(storyWorkspaceShouldInvalidateEpisodeArtifacts({
    type: 'story-workspace-output',
    runId: RUN_ID,
    artifact: { agentMessage: 'must be ignored' },
  }, RUN_ID)).toBe(true);
  expect(storyWorkspaceShouldInvalidateEpisodeArtifacts({
    type: 'story-workspace-output',
    runId: OTHER_RUN_ID,
  }, RUN_ID)).toBe(false);
  expect(storyWorkspaceShouldInvalidateEpisodeArtifacts({
    type: 'assistant_message',
    runId: RUN_ID,
    content: boundSurface(),
  }, RUN_ID)).toBe(false);
});

test('endpoint and source contain no browser storage, Agent artifact parser, or ChatView coupling', () => {
  expect(storyWorkspaceEpisodeArtifactsEndpoint(RUN_ID)).toBe(
    `/api/story-workspace/workflow-runs/${RUN_ID}/episode-artifacts`,
  );
  expect(storyWorkspaceEpisodeArtifactsEndpoint('run/a?b')).toContain('run%2Fa%3Fb');

  const source = readFileSync(
    new URL('../useStoryWorkspaceEpisodeArtifacts.ts', import.meta.url),
    'utf8',
  );
  expect(source).not.toContain('localStorage');
  expect(source).not.toContain('ChatView');
  expect(source).not.toContain('agentMessage');
  expect(source).not.toContain('messages');
});

test('response header ETag must equal the parsed manifest revision', async () => {
  await expect(storyWorkspaceFetchEpisodeArtifacts('/api/episode', {
    fetchImpl: (async () => new Response(JSON.stringify(boundSurface()), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ETag: `"${REVISION_5}"` },
    })) as typeof fetch,
  })).rejects.toThrow(/ETag/i);
});
