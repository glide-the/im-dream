// [Input] Synthetic Story Index projections and HTTP responses.
// [Output] Strict contract, independent ETag, last-good, and reconcile-CAS coverage.
// [Pos] Story Workspace Story Index frontend query seam.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
import {
  STORY_WORKSPACE_STORY_INDEX_POLL_INTERVAL_MS,
  StoryWorkspaceStoryIndexHttpError,
  storyWorkspaceFetchStoryIndex,
  storyWorkspaceParseStoryIndexProjection,
  storyWorkspaceReconcileStoryIndex,
  storyWorkspaceReduceStoryIndexFetch,
  storyWorkspaceStoryIndexEndpoint,
  storyWorkspaceStoryIndexInitialState,
  storyWorkspaceStoryIndexQueryIdentity,
  storyWorkspaceStoryIndexReconcileEndpoint,
  storyWorkspaceShouldPollStoryIndex,
} from '../useStoryWorkspaceStoryIndex';
import type {
  StoryWorkspaceStoryIndexProjection,
  StoryWorkspaceStoryIndexStatus,
} from '../contracts';

const RUN_ID = `run_${'1'.repeat(32)}`;
const OTHER_RUN_ID = `run_${'2'.repeat(32)}`;
const STORY_ID = '123e4567-e89b-52d3-a456-426614174000';
const MANIFEST_1 = `sha256:${'1'.repeat(64)}`;
const MANIFEST_2 = `sha256:${'2'.repeat(64)}`;
const SCRIPT_1 = `sha256:${'3'.repeat(64)}`;
const SCRIPT_2 = `sha256:${'4'.repeat(64)}`;
const ETAG_1 = `sha256:${'5'.repeat(64)}`;
const ETAG_2 = `sha256:${'6'.repeat(64)}`;
const SOURCE = readFileSync(new URL('../useStoryWorkspaceStoryIndex.ts', import.meta.url), 'utf8');

function projection(status: StoryWorkspaceStoryIndexStatus): StoryWorkspaceStoryIndexProjection {
  const base: StoryWorkspaceStoryIndexProjection = {
    runId: RUN_ID,
    projectId: 'rainy-night',
    projectTitle: '雨夜归途',
    storyId: STORY_ID,
    status,
    observedManifestRevision: MANIFEST_1,
    observedScriptRevision: SCRIPT_1,
    indexedManifestRevision: MANIFEST_1,
    indexedScriptRevision: SCRIPT_1,
    episodeCount: 2,
    lastIndexedAt: '2026-08-10T01:02:03+00:00',
    errorCode: null,
    retryable: false,
    etag: ETAG_1,
  };
  if (status === 'missing') {
    return {
      ...base,
      storyId: null,
      indexedManifestRevision: null,
      indexedScriptRevision: null,
      lastIndexedAt: null,
      errorCode: 'story_index_row_missing',
      retryable: true,
    };
  }
  if (status === 'stale') {
    return {
      ...base,
      indexedManifestRevision: MANIFEST_2,
      indexedScriptRevision: SCRIPT_2,
      retryable: true,
    };
  }
  if (status === 'failed') {
    return {
      ...base,
      storyId: null,
      indexedManifestRevision: null,
      indexedScriptRevision: null,
      lastIndexedAt: null,
      errorCode: 'story_index_database_unavailable',
      retryable: true,
    };
  }
  return base;
}

test('strictly parses the four server states and keeps syncing client-only', () => {
  for (const status of ['indexed', 'stale', 'missing', 'failed'] as const) {
    expect(storyWorkspaceParseStoryIndexProjection(projection(status))).toEqual(
      projection(status),
    );
  }
  expect(() => storyWorkspaceParseStoryIndexProjection({
    ...projection('missing'),
    status: 'syncing',
  })).toThrow('Story index data is unavailable.');
});

test('fails closed on extra locators, unsafe identities, malformed revisions and unknown codes', () => {
  const invalid: unknown[] = [
    { ...projection('indexed'), sourceThreadRef: 'thread-private' },
    { ...projection('indexed'), projectId: '../../private' },
    { ...projection('indexed'), storyId: '123e4567-e89b-42d3-a456-426614174000' },
    { ...projection('indexed'), observedScriptRevision: 'sha256:not-a-revision' },
    { ...projection('failed'), errorCode: '/Users/private/story-index' },
    { ...projection('indexed'), lastIndexedAt: '2026-08-10' },
    { ...projection('indexed'), episodeCount: 1.5 },
    { ...projection('indexed'), episodeCount: 0 },
    {
      ...projection('indexed'),
      observedManifestRevision: null,
      indexedManifestRevision: null,
    },
    { ...projection('stale'), storyId: null },
  ];
  for (const value of invalid) {
    expect(() => storyWorkspaceParseStoryIndexProjection(value)).toThrow(
      'Story index data is unavailable.',
    );
  }
});

test('uses a run-scoped query identity and encoded dedicated endpoints', () => {
  expect(storyWorkspaceStoryIndexQueryIdentity(RUN_ID)).toEqual([
    'story-workspace', 'workflow-run', RUN_ID, 'story-index',
  ]);
  expect(storyWorkspaceStoryIndexEndpoint('run/a?b')).toBe(
    '/api/story-workspace/workflow-runs/run%2Fa%3Fb/story-index',
  );
  expect(storyWorkspaceStoryIndexReconcileEndpoint(RUN_ID)).toBe(
    `/api/story-workspace/workflow-runs/${RUN_ID}/story-index/reconcile`,
  );
});

test('polls the independent GET status every 30 seconds only while the page is visible', () => {
  expect(STORY_WORKSPACE_STORY_INDEX_POLL_INTERVAL_MS).toBe(30_000);
  expect(storyWorkspaceShouldPollStoryIndex(true, 'visible')).toBe(true);
  expect(storyWorkspaceShouldPollStoryIndex(true, 'hidden')).toBe(false);
  expect(storyWorkspaceShouldPollStoryIndex(false, 'visible')).toBe(false);
  expect(SOURCE).toContain("document.addEventListener('visibilitychange'");
  expect(SOURCE).toContain('window.setInterval(refresh, intervalMs)');
  expect(SOURCE).toContain('if (!enabled || !normalizedRunId) return;');
});

test('GET validates its own response ETag and exact 304 while retaining auth scope', async () => {
  const calls: RequestInit[] = [];
  const data = projection('indexed');
  const first = await storyWorkspaceFetchStoryIndex('/api/story-index', {
    token: 'safe-token',
    expectedRunId: RUN_ID,
    fetchImpl: (async (_input: RequestInfo | URL, init?: RequestInit) => {
      calls.push(init ?? {});
      return new Response(JSON.stringify(data), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ETag: `"${data.etag}"` },
      });
    }) as typeof fetch,
  });
  expect(first).toEqual({ kind: 'projection', data });
  expect(new Headers(calls[0]?.headers).get('Authorization')).toBe('Bearer safe-token');

  const unchanged = await storyWorkspaceFetchStoryIndex('/api/story-index', {
    etag: data.etag,
    fetchImpl: (async (_input: RequestInfo | URL, init?: RequestInit) => {
      calls.push(init ?? {});
      return new Response(null, { status: 304, headers: { ETag: `"${data.etag}"` } });
    }) as typeof fetch,
  });
  expect(unchanged).toEqual({ kind: 'not-modified', etag: data.etag });
  expect(new Headers(calls[1]?.headers).get('If-None-Match')).toBe(`"${data.etag}"`);

  await expect(storyWorkspaceFetchStoryIndex('/api/story-index', {
    etag: data.etag,
    fetchImpl: (async () => new Response(null, {
      status: 304,
      headers: { ETag: `"${ETAG_2}"` },
    })) as typeof fetch,
  })).rejects.toThrow('Story index data is unavailable.');
});

test('GET errors retain last-good data and never consume unsafe server detail', async () => {
  const good = projection('indexed');
  const loaded = storyWorkspaceReduceStoryIndexFetch(
    storyWorkspaceStoryIndexInitialState(RUN_ID),
    { type: 'read-success', runId: RUN_ID, generation: 1, data: good },
  );
  const error = new StoryWorkspaceStoryIndexHttpError(
    503,
    'story_index_database_unavailable',
  );
  const failed = storyWorkspaceReduceStoryIndexFetch(loaded, {
    type: 'read-error', runId: RUN_ID, generation: 2, error,
  });
  expect(failed.data).toBe(good);
  expect(failed.error).toBe(error);

  await expect(storyWorkspaceFetchStoryIndex('/api/story-index', {
    fetchImpl: (async () => new Response(JSON.stringify({
      error: {
        code: 'story_index_database_unavailable',
        message: '/Users/private/workspace/stories',
      },
    }), { status: 503, headers: { 'Content-Type': 'application/json' } })) as typeof fetch,
  })).rejects.toMatchObject({
    name: 'StoryWorkspaceStoryIndexHttpError',
    status: 503,
    errorCode: 'story_index_database_unavailable',
    message: 'Story index request failed (503).',
  });
});

test('POST sends only idempotencyKey with exact index If-Match and validates the new ETag', async () => {
  const calls: Array<{ readonly url: string; readonly init: RequestInit }> = [];
  const indexed = { ...projection('indexed'), etag: ETAG_2 };
  await expect(storyWorkspaceReconcileStoryIndex(RUN_ID, ETAG_1, {
    endpoint: '/api/story-index/reconcile',
    idempotencyKey: 'retry:one',
    token: 'safe-token',
    fetchImpl: (async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), init: init ?? {} });
      return new Response(JSON.stringify(indexed), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ETag: `"${ETAG_2}"` },
      });
    }) as typeof fetch,
  })).resolves.toEqual(indexed);

  expect(calls).toHaveLength(1);
  expect(calls[0]?.url).toBe('/api/story-index/reconcile');
  expect(calls[0]?.init.method).toBe('POST');
  expect(new Headers(calls[0]?.init.headers).get('If-Match')).toBe(`"${ETAG_1}"`);
  expect(JSON.parse(String(calls[0]?.init.body))).toEqual({ idempotencyKey: 'retry:one' });
  expect(String(calls[0]?.init.body)).not.toContain('projectId');
  expect(String(calls[0]?.init.body)).not.toContain('thread');
  expect(String(calls[0]?.init.body)).not.toContain('path');
});

test('POST surfaces one safe 409 and performs no blind retry', async () => {
  let requests = 0;
  const pending = storyWorkspaceReconcileStoryIndex(RUN_ID, ETAG_1, {
    idempotencyKey: 'retry:conflict',
    fetchImpl: (async () => {
      requests += 1;
      return new Response(JSON.stringify({
        error: {
          code: 'story_index_revision_conflict',
          message: '/private/current/revision',
        },
      }), { status: 409, headers: { 'Content-Type': 'application/json' } });
    }) as typeof fetch,
  });
  await expect(pending).rejects.toMatchObject({
    name: 'StoryWorkspaceStoryIndexHttpError',
    status: 409,
    errorCode: 'story_index_revision_conflict',
  });
  expect(requests).toBe(1);
});

test('stale generations and run switches cannot replace another run projection', () => {
  const newest = projection('stale');
  const loaded = storyWorkspaceReduceStoryIndexFetch(
    storyWorkspaceStoryIndexInitialState(RUN_ID),
    { type: 'read-success', runId: RUN_ID, generation: 2, data: newest },
  );
  expect(storyWorkspaceReduceStoryIndexFetch(loaded, {
    type: 'read-success', runId: RUN_ID, generation: 1, data: projection('indexed'),
  })).toBe(loaded);
  expect(storyWorkspaceReduceStoryIndexFetch(loaded, {
    type: 'read-success', runId: OTHER_RUN_ID, generation: 3, data: projection('indexed'),
  })).toBe(loaded);
  expect(storyWorkspaceReduceStoryIndexFetch(loaded, {
    type: 'reset', runId: OTHER_RUN_ID,
  }).data).toBeNull();
});

test('reconcile remains non-optimistic until the authoritative POST response arrives', () => {
  const current = projection('stale');
  const loaded = storyWorkspaceReduceStoryIndexFetch(
    storyWorkspaceStoryIndexInitialState(RUN_ID),
    { type: 'read-success', runId: RUN_ID, generation: 1, data: current },
  );
  const syncing = storyWorkspaceReduceStoryIndexFetch(loaded, {
    type: 'reconcile-start', runId: RUN_ID, generation: 1,
  });
  expect(syncing.data).toBe(current);
  expect(syncing.data?.status).toBe('stale');
  expect(syncing.isReconciling).toBe(true);

  const failed = storyWorkspaceReduceStoryIndexFetch(syncing, {
    type: 'reconcile-error',
    runId: RUN_ID,
    generation: 1,
    error: new StoryWorkspaceStoryIndexHttpError(409, 'story_index_revision_conflict'),
  });
  expect(failed.data).toBe(current);
  expect(failed.data?.status).toBe('stale');
  expect(failed.isReconciling).toBe(false);
});
