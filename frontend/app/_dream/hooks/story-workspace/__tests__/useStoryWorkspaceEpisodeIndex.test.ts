// [Input] Body-free Episode index wire fixtures and conditional GET responses.
// [Output] Verify strict IDs, contiguous ordering, active identity, and ETag handling.
// [Pos] Story Workspace Episode index frontend contract tests.
// [Sync] 2026-09-02: add EP01/EP02 index coverage.

import { expect, test } from '@playwright/test';
import { storyWorkspaceParseEpisodeIndexSurface } from '../contracts';
import {
  StoryWorkspaceEpisodeIndexContractError,
  storyWorkspaceEpisodeIndexEndpoint,
  storyWorkspaceFetchEpisodeIndex,
} from '../useStoryWorkspaceEpisodeIndex';

const RUN_ID = `run_${'1'.repeat(32)}`;
const EP01_ID = 'a'.repeat(32);
const EP02_ID = 'b'.repeat(32);
const ETAG = `sha256:${'c'.repeat(64)}`;

function indexSurface() {
  return {
    runId: RUN_ID,
    registryRevision: 3,
    activeEpisodeId: EP02_ID,
    etag: ETAG,
    episodes: [
      {
        opaqueEpisodeId: EP01_ID,
        episodeCode: 'EP01',
        active: false,
        availableArtifactCount: 4,
        hasArtifactIssues: false,
        updatedAt: '2026-09-02T06:30:00Z',
      },
      {
        opaqueEpisodeId: EP02_ID,
        episodeCode: 'EP02',
        active: true,
        availableArtifactCount: 0,
        hasArtifactIssues: false,
        updatedAt: null,
      },
    ],
  };
}

test('parses distinct stable EP01 and EP02 identities', () => {
  const parsed = storyWorkspaceParseEpisodeIndexSurface(indexSurface());
  expect(parsed.episodes.map((episode) => episode.episodeCode)).toEqual(['EP01', 'EP02']);
  expect(parsed.episodes[0].opaqueEpisodeId).not.toBe(parsed.episodes[1].opaqueEpisodeId);
  expect(parsed.activeEpisodeId).toBe(EP02_ID);
});

test('rejects non-contiguous codes and inconsistent active state', () => {
  expect(() => storyWorkspaceParseEpisodeIndexSurface({
    ...indexSurface(),
    episodes: [
      indexSurface().episodes[0],
      { ...indexSurface().episodes[1], episodeCode: 'EP03' },
    ],
  })).toThrow(/contiguous/i);
  expect(() => storyWorkspaceParseEpisodeIndexSurface({
    ...indexSurface(),
    activeEpisodeId: EP01_ID,
  })).toThrow(/active identity/i);
});

test('fetches the body-free index with matching response ETag', async () => {
  expect(storyWorkspaceEpisodeIndexEndpoint(RUN_ID)).toContain(`/workflow-runs/${RUN_ID}/episodes`);
  const result = await storyWorkspaceFetchEpisodeIndex('/episodes', {
    expectedRunId: RUN_ID,
    fetchImpl: (async () => new Response(JSON.stringify(indexSurface()), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ETag: `W/"${ETAG}"` },
    })) as typeof fetch,
  });
  expect(result).toEqual({ kind: 'index', data: indexSurface() });

  await expect(storyWorkspaceFetchEpisodeIndex('/episodes', {
    expectedRunId: RUN_ID,
    fetchImpl: (async () => new Response(JSON.stringify(indexSurface()), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ETag: `"sha256:${'d'.repeat(64)}"` },
    })) as typeof fetch,
  })).rejects.toBeInstanceOf(StoryWorkspaceEpisodeIndexContractError);
});
