// [Input] Canonical Episode artifact GET snapshots and lifecycle signals.
// [Output] Contract, ETag, polling, invalidation, cancellation, and last-good coverage.
// [Pos] Story Workspace read-only Episode artifact query seam.

import { expect, test } from '@playwright/test';
import {
  StoryWorkspaceEpisodeArtifactsContractError,
  StoryWorkspaceEpisodeArtifactsHttpError,
  storyWorkspaceCreateEpisodeArtifactsRequestLifecycle,
  storyWorkspaceEpisodeArtifactsEndpoint,
  storyWorkspaceEpisodeArtifactsInitialState,
  storyWorkspaceEpisodeArtifactsPollInterval,
  storyWorkspaceFetchEpisodeArtifacts,
  storyWorkspaceIsEpisodeArtifactsAbort,
  storyWorkspaceReduceEpisodeArtifactsFetch,
  storyWorkspaceShouldInvalidateEpisodeArtifacts,
} from '../useStoryWorkspaceEpisodeArtifacts';
import { storyWorkspaceParseEpisodeArtifactSurface } from '../contracts';

const RUN_ID = `run_${'1'.repeat(32)}`;
const REVISION = `sha256:${'2'.repeat(64)}`;

const ARTIFACT_SPECS = [
  ['episode-outline.md', 'plan_episode', ['episode_overview', 'storyline_navigator', 'narrative_workbench']],
  ['script.md', 'write_script', ['narrative_workbench', 'shot_inspector']],
  ['storyboard.yaml', 'regenerate_storyboard', ['narrative_workbench', 'shot_inspector']],
  ['prompts/', 'generate_prompts', ['shot_inspector', 'prompt_view']],
  ['renders/', 'prepare_render_guide', ['shot_inspector', 'render_view']],
  ['review-report.md', 'review_full_chain', ['review_view', 'shot_inspector']],
] as const;

function unboundSurface() {
  return {
    runId: RUN_ID,
    opaqueEpisodeId: null,
    episodeCode: null,
    manifestRevision: null,
    etag: null,
    bindingAvailability: 'unbound',
    artifacts: [],
    documents: [],
    narrative: null,
    auxiliary: null,
  };
}

function boundSurface(availability: 'not_generated' | 'invalid' = 'not_generated') {
  return {
    runId: RUN_ID,
    opaqueEpisodeId: 'a'.repeat(32),
    episodeCode: 'EP01',
    manifestRevision: REVISION,
    etag: REVISION,
    bindingAvailability: 'bound',
    artifacts: ARTIFACT_SPECS.map(([relativeKey, producerAction, consumers]) => ({
      relativeKey,
      availability,
      contentRevision: null,
      mtime: null,
      size: null,
      producerAction,
      consumers,
    })),
    documents: [],
    narrative: null,
    auxiliary: null,
  };
}

test('parses the canonical bound and unbound surfaces without workflow action fields', () => {
  expect(storyWorkspaceParseEpisodeArtifactSurface(boundSurface()).episodeCode).toBe('EP01');
  expect(storyWorkspaceParseEpisodeArtifactSurface(unboundSurface()).bindingAvailability).toBe('unbound');
  expect(() => storyWorkspaceParseEpisodeArtifactSurface({
    ...boundSurface(),
    actionProjection: { recommendedActionId: 'write_script' },
  })).toThrow(/unknown field/i);
});

test('requires all canonical artifact roots for a bound Episode', () => {
  expect(() => storyWorkspaceParseEpisodeArtifactSurface({
    ...boundSurface(),
    artifacts: boundSurface().artifacts.slice(1),
  })).toThrow(/all six artifacts/i);
});

test('GET uses the run-scoped endpoint, bearer token, and exact quoted ETag', async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const result = await storyWorkspaceFetchEpisodeArtifacts(
    storyWorkspaceEpisodeArtifactsEndpoint(RUN_ID),
    {
      token: 'local-token',
      etag: REVISION,
      expectedRunId: RUN_ID,
      fetchImpl: (async (input: RequestInfo | URL, init?: RequestInit) => {
        calls.push({ url: String(input), init });
        return new Response(null, { status: 304, headers: { ETag: `"${REVISION}"` } });
      }) as typeof fetch,
    },
  );
  expect(result).toEqual({ kind: 'not-modified', etag: REVISION });
  expect(calls[0].url).toContain(`/workflow-runs/${RUN_ID}/episode-artifacts`);
  expect(new Headers(calls[0].init?.headers).get('Authorization')).toBe('Bearer local-token');
  expect(new Headers(calls[0].init?.headers).get('If-None-Match')).toBe(`"${REVISION}"`);
});

test('GET rejects mismatched run identity, malformed payload, and error status', async () => {
  await expect(storyWorkspaceFetchEpisodeArtifacts('/episode', {
    expectedRunId: `run_${'9'.repeat(32)}`,
    fetchImpl: (async () => new Response(JSON.stringify(unboundSurface()), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })) as typeof fetch,
  })).rejects.toBeInstanceOf(StoryWorkspaceEpisodeArtifactsContractError);

  await expect(storyWorkspaceFetchEpisodeArtifacts('/episode', {
    fetchImpl: (async () => new Response('{', { status: 200 })) as typeof fetch,
  })).rejects.toBeInstanceOf(StoryWorkspaceEpisodeArtifactsContractError);

  await expect(storyWorkspaceFetchEpisodeArtifacts('/episode', {
    fetchImpl: (async () => new Response(null, { status: 404 })) as typeof fetch,
  })).rejects.toBeInstanceOf(StoryWorkspaceEpisodeArtifactsHttpError);
});

test('only the exact run output event invalidates the GET snapshot', () => {
  expect(storyWorkspaceShouldInvalidateEpisodeArtifacts({ type: 'story-workspace-output', runId: RUN_ID }, RUN_ID)).toBe(true);
  expect(storyWorkspaceShouldInvalidateEpisodeArtifacts({ type: 'story-workspace-output', runId: 'other' }, RUN_ID)).toBe(false);
  expect(storyWorkspaceShouldInvalidateEpisodeArtifacts({ type: 'agent-delta', runId: RUN_ID }, RUN_ID)).toBe(false);
});

test('request lifecycle aborts stale requests after switching run', () => {
  const lifecycle = storyWorkspaceCreateEpisodeArtifactsRequestLifecycle(RUN_ID);
  const first = lifecycle.begin(RUN_ID);
  const otherRun = `run_${'3'.repeat(32)}`;
  lifecycle.activate(otherRun);
  expect(first.signal.aborted).toBe(true);
  expect(lifecycle.shouldCommit(first)).toBe(false);
  const second = lifecycle.begin(otherRun);
  expect(lifecycle.shouldCommit(second)).toBe(true);
  lifecycle.cleanup();
  expect(second.signal.aborted).toBe(true);
});

test('reducer keeps the last-good artifact while the latest root is invalid', () => {
  const initial = boundSurface();
  const available = {
    ...initial,
    artifacts: initial.artifacts.map((item) => ({
      ...item,
      availability: item.relativeKey === 'script.md' ? 'available' as const : item.availability,
      contentRevision: item.relativeKey === 'script.md' ? REVISION : null,
      mtime: item.relativeKey === 'script.md' ? '2026-08-13T00:00:00Z' : null,
      size: item.relativeKey === 'script.md' ? 10 : null,
    })),
  };
  let state = storyWorkspaceEpisodeArtifactsInitialState(RUN_ID);
  state = storyWorkspaceReduceEpisodeArtifactsFetch(state, {
    type: 'success', runId: RUN_ID, generation: 1,
    data: storyWorkspaceParseEpisodeArtifactSurface(available),
  });
  state = storyWorkspaceReduceEpisodeArtifactsFetch(state, {
    type: 'success', runId: RUN_ID, generation: 2,
    data: storyWorkspaceParseEpisodeArtifactSurface(boundSurface('invalid')),
  });
  expect(state.invalidArtifactKeys).toContain('script.md');
  expect(state.staleArtifactKeys).toContain('script.md');
});

test('poll interval is bounded and AbortError is recognized', () => {
  expect(storyWorkspaceEpisodeArtifactsPollInterval(1)).toBe(5000);
  expect(storyWorkspaceEpisodeArtifactsPollInterval(Number.POSITIVE_INFINITY)).toBe(2_147_483_647);
  expect(storyWorkspaceIsEpisodeArtifactsAbort(new DOMException('aborted', 'AbortError'))).toBe(true);
});
