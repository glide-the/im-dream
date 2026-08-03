// [Input] Router-parsed `?run=` param values + stubbed run reads (Playwright
//          node-side runner).
// [Output] Contract tests for the Dream page ?run= deep link: actor-scoped
//          resolution with toast fallback semantics (design_004 §4.3). Query
//          parsing moved to the router (storyWorkspacePath.ts, Task 5 Step 0);
//          its seam tests live in src/router/__tests__/.
// [Pos] story-workspace run deep-link test node (Task 4 Step 5; Task 5 Step 0
//       absorbed parsing into the router)
// [Sync] 2026-08-04: resolveRunDeepLink now takes the parsed run id directly;
//                    the hook is a thin React wrapper (initial positioning
//                    only, no freeze) that clears state on route switch.

import { expect, test } from '@playwright/test';
import type { WorkflowRun } from '../../../api/storyWorkspaceApi';
import {
  createRunDeepLinkResolveGate,
  resolveRunDeepLink,
} from '../useRunDeepLink';

function stubRun(runId: string): WorkflowRun {
  return {
    workflow_run_id: runId,
    deck_plugin_id: 'ink.dream.story-workflow',
    deck_plugin_version: '1.0.1',
    workflow_definition_ref: 'dream',
    deck_runtime_snapshot_id: 'snap-1',
    runtime_plugin_lock_id: 'lock-1',
    runtime_load_receipt_id: null,
    workflow_preflight_id: 'pf-1',
    status: 'continuing',
    status_version: 3,
    failed_step: null,
    error_code: null,
    retry_of_run_id: null,
    created_at: '2026-08-04T00:00:00Z',
    started_at: null,
    completed_at: null,
  };
}

test('resolve without a run param is a no-op (default view, no fetch)', async () => {
  let called = 0;
  const resolution = await resolveRunDeepLink(null, {
    getRun: async () => {
      called += 1;
      return stubRun('r1');
    },
  });
  expect(resolution).toEqual({ status: 'none' });
  expect(called).toBe(0);
});

test('run owned by the current user resolves as the selected run', async () => {
  const seen: string[] = [];
  const resolution = await resolveRunDeepLink('r1', {
    getRun: async (runId) => {
      seen.push(runId);
      return stubRun(runId);
    },
  });
  expect(seen).toEqual(['r1']);
  expect(resolution).toEqual({ status: 'resolved', run: stubRun('r1') });
});

test('missing / foreign / failing runs degrade to the toast fallback', async () => {
  const notFound = await resolveRunDeepLink('gone', {
    getRun: async () => {
      throw new Error('404');
    },
  });
  expect(notFound).toEqual({ status: 'missing', runId: 'gone' });

  const forbidden = await resolveRunDeepLink('other-user-run', {
    getRun: async () => {
      throw new Error('403');
    },
  });
  expect(forbidden).toEqual({ status: 'missing', runId: 'other-user-run' });

  const emptyPayload = await resolveRunDeepLink('r1', {
    getRun: async () => null as unknown as WorkflowRun,
  });
  expect(emptyPayload).toEqual({ status: 'missing', runId: 'r1' });
});

test('resolve-once gate latches only after the resolution is applied (F-2)', async () => {
  const gate = createRunDeepLinkResolveGate();
  const seen: string[] = [];
  const getRun = async (runId: string) => {
    seen.push(runId);
    return stubRun(runId);
  };

  // First setup begins an attempt; it must not latch the cursor yet.
  expect(gate.begin('r1')).toBe(true);
  expect(gate.begin('r1')).toBe(false); // same attempt already in flight

  const resolution = await resolveRunDeepLink('r1', { getRun });
  expect(resolution.status).toBe('resolved');
  gate.markResolved('r1');

  // Only after the applied resolution does the once-per-run-id latch hold.
  expect(gate.begin('r1')).toBe(false);
  expect(gate.begin('r2')).toBe(true);
  expect(seen).toEqual(['r1']);
});

test('gate reopens after abort so a StrictMode second setup can resolve (F-2)', async () => {
  const gate = createRunDeepLinkResolveGate();
  const seen: string[] = [];
  const getRun = async (runId: string) => {
    seen.push(runId);
    return stubRun(runId);
  };

  // StrictMode dev double-effect: setup → cleanup(abort) → setup. The first
  // attempt is cancelled before its resolution applies; the second setup must
  // not early-return on a pre-latched cursor.
  expect(gate.begin('r1')).toBe(true);
  const cancelledAttempt = resolveRunDeepLink('r1', { getRun });
  gate.abort();
  await cancelledAttempt; // resolves, but the effect cleanup dropped it

  expect(gate.begin('r1')).toBe(true);
  const resolution = await resolveRunDeepLink('r1', { getRun });
  expect(resolution.status).toBe('resolved');
  gate.markResolved('r1');
  expect(gate.begin('r1')).toBe(false);
  expect(seen).toEqual(['r1', 'r1']);
});

test('gate reset clears both slots (route switch)', () => {
  const gate = createRunDeepLinkResolveGate();
  expect(gate.begin('r1')).toBe(true);
  gate.markResolved('r1');
  gate.reset();
  expect(gate.begin('r1')).toBe(true);
  gate.abort();
  gate.reset();
  expect(gate.begin('r1')).toBe(true);
});
