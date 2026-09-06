// [Input] Mocked plugin-load-receipt REST responses (Playwright node-side runner).
// [Output] Contract tests for useWorkspaceSurfaces seams: endpoint builder,
//          fetch helper (auth header / error degradation) and manifest→receipt resolver.
// [Pos] story-workspace hooks test node (DEC-026 / DEC-028 coverage)
// [Sync] 2026-08-04: Task 2 - consume workspace surfaces via plugin-load-receipt;
//                    pre-pack / legacy sessions must degrade to "no surface".

import { expect, test } from '@playwright/test';
import {
  fetchWorkspaceSurfaces,
  resolveWorkspaceSurfaces,
  workspaceSurfacesEndpoint,
} from '../useWorkspaceSurfaces';

const DREAM_SURFACE = {
  name: 'dream',
  protocol_dir: '.dream',
  entry_route: '/story-workspace/dream',
};

function mockReceiptEndpoint(body: unknown, status = 200) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const fetchImpl = (async (url: unknown, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as unknown as typeof fetch;
  return { fetchImpl, calls };
}

test('endpoint builder targets the existing plugin-load-receipt route', () => {
  expect(workspaceSurfacesEndpoint('thread-1')).toBe(
    '/api/claude-agent/threads/thread-1/plugin-load-receipt',
  );
  expect(workspaceSurfacesEndpoint('a/b?c')).toBe(
    '/api/claude-agent/threads/a%2Fb%3Fc/plugin-load-receipt',
  );
});

test('returns surfaces from launch_manifest when present', async () => {
  const { fetchImpl, calls } = mockReceiptEndpoint({
    thread_id: 't1',
    workspace_found: true,
    launch_manifest: { surfaces: [DREAM_SURFACE] },
    receipt: { surfaces: [{ name: 'stale', protocol_dir: '.stale', entry_route: '/story-workspace/stale' }] },
  });

  const surfaces = await fetchWorkspaceSurfaces(
    '/api/claude-agent/threads/t1/plugin-load-receipt',
    { fetchImpl, token: 'token-1' },
  );

  expect(surfaces).toEqual([DREAM_SURFACE]);
  expect(calls).toHaveLength(1);
  const headers = new Headers(calls[0].init?.headers);
  expect(headers.get('Authorization')).toBe('Bearer token-1');
  expect(headers.get('Accept')).toBe('application/json');
  expect(calls[0].init?.credentials).toBe('include');
});

test('falls back to receipt.surfaces when manifest lacks the key', async () => {
  const { fetchImpl } = mockReceiptEndpoint({
    workspace_found: true,
    launch_manifest: { plugins: [] },
    receipt: { surfaces: [DREAM_SURFACE] },
  });

  const surfaces = await fetchWorkspaceSurfaces('/api/x', { fetchImpl });
  expect(surfaces).toEqual([DREAM_SURFACE]);
});

test('pre-pack threads (workspace_found:false) degrade to no surface', async () => {
  const { fetchImpl } = mockReceiptEndpoint({
    thread_id: 't1',
    workspace_found: false,
    receipt: null,
    launch_manifest: null,
  });

  const surfaces = await fetchWorkspaceSurfaces('/api/x', { fetchImpl });
  expect(surfaces).toBeUndefined();
});

test('legacy sessions without surfaces keys degrade to no surface', async () => {
  const { fetchImpl } = mockReceiptEndpoint({
    workspace_found: true,
    launch_manifest: { schema_version: 'claude-launch/v1', plugins: [] },
    receipt: { plugins: [], frozen: false },
  });

  const surfaces = await fetchWorkspaceSurfaces('/api/x', { fetchImpl });
  expect(surfaces).toBeUndefined();
});

test('empty surfaces arrays are indistinguishable from no surface', async () => {
  const { fetchImpl } = mockReceiptEndpoint({
    workspace_found: true,
    launch_manifest: { surfaces: [] },
    receipt: { surfaces: [] },
  });

  const surfaces = await fetchWorkspaceSurfaces('/api/x', { fetchImpl });
  expect(surfaces).toBeUndefined();
});

test('404 (unknown thread) degrades to no surface instead of throwing', async () => {
  const { fetchImpl } = mockReceiptEndpoint({ detail: 'Thread not found' }, 404);
  const surfaces = await fetchWorkspaceSurfaces('/api/x', { fetchImpl });
  expect(surfaces).toBeUndefined();
});

test('malformed JSON degrades to no surface', async () => {
  const fetchImpl = (async () => new Response('not-json{{', {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })) as unknown as typeof fetch;

  const surfaces = await fetchWorkspaceSurfaces('/api/x', { fetchImpl });
  expect(surfaces).toBeUndefined();
});

test('network failure degrades to no surface', async () => {
  const fetchImpl = (async () => {
    throw new TypeError('fetch failed');
  }) as unknown as typeof fetch;

  const surfaces = await fetchWorkspaceSurfaces('/api/x', { fetchImpl });
  expect(surfaces).toBeUndefined();
});

test('malformed surface entries are filtered; all-invalid falls back then degrades', () => {
  const resolved = resolveWorkspaceSurfaces({
    thread_id: 't1',
    deck_id: null,
    workspace_found: true,
    launch_manifest: {
      surfaces: [
        { name: 'dream', protocol_dir: '.dream', entry_route: '/story-workspace/dream' },
        { name: 42, protocol_dir: '.bad', entry_route: '/story-workspace/bad' },
        'garbage',
      ] as unknown as never,
    },
    receipt: null,
  });
  expect(resolved).toEqual([DREAM_SURFACE]);

  expect(resolveWorkspaceSurfaces({
    thread_id: 't1',
    deck_id: null,
    workspace_found: true,
    launch_manifest: { surfaces: [{ name: 1 }] as unknown as never },
    receipt: { surfaces: [DREAM_SURFACE] },
  })).toEqual([DREAM_SURFACE]);
});

test('resolver returns undefined for null payload and non-true workspace_found', () => {
  expect(resolveWorkspaceSurfaces(null)).toBeUndefined();
  expect(resolveWorkspaceSurfaces(undefined)).toBeUndefined();
  expect(resolveWorkspaceSurfaces({
    thread_id: 't1',
    deck_id: null,
    workspace_found: false,
    launch_manifest: { surfaces: [DREAM_SURFACE] },
    receipt: { surfaces: [DREAM_SURFACE] },
  })).toBeUndefined();
});
