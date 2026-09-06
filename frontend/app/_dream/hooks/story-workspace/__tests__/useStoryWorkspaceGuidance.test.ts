// [Input] Synthetic guidance inputs / chat_message rows / stubbed fetch
//          responses (Playwright node-side runner).
// [Output] Contract tests for the guidance sidebar seams (Task 5, design_004
//          §5.3): idempotent payload construction (client idempotency key),
//          submit-result presentation including the dispatched:false
//          "已记录待拾取" state (Task 3 review leftover R2), guidance history
//          extraction from thread messages (metadata.kind reverse lookup), and
//          the POST /api/story-workspace/runs/{id}/guidance transport seam.
// [Pos] story-workspace guidance test node (Task 5 Step 1)
// [Sync] 2026-08-04: initial coverage — pure seams only; the React hook is a
//                    thin wrapper (Task 2/4 node-side precedent).

import { expect, test } from '@playwright/test';
import {
  buildStoryWorkspaceGuidancePayload,
  storyWorkspaceGuidanceEndpoint,
  describeStoryWorkspaceGuidanceResult,
  extractStoryWorkspaceGuidanceHistory,
  newStoryWorkspaceGuidanceIdempotencyKey,
  submitStoryWorkspaceGuidance,
} from '../useStoryWorkspaceGuidance';

test('buildStoryWorkspaceGuidancePayload builds a free-text command with an idempotency key', () => {
  const payload = buildStoryWorkspaceGuidancePayload({
    kind: 'free-text',
    actor: '11',
    text: '第二集节奏放慢',
  });
  expect(payload).toMatchObject({
    kind: 'free-text',
    actor: '11',
    text: '第二集节奏放慢',
  });
  expect(payload?.idempotency_key).toMatch(/^swg_/);
  expect(payload?.step_id).toBeUndefined();
});

test('buildStoryWorkspaceGuidancePayload respects a caller-provided idempotency key', () => {
  const payload = buildStoryWorkspaceGuidancePayload({
    kind: 'free-text',
    actor: '11',
    text: 'x',
    idempotencyKey: 'fixed-key-1',
  });
  expect(payload?.idempotency_key).toBe('fixed-key-1');
});

test('buildStoryWorkspaceGuidancePayload rejects invalid commands (contract parity)', () => {
  expect(buildStoryWorkspaceGuidancePayload({ kind: 'free-text', actor: '11', text: '  ' })).toBeNull();
  expect(buildStoryWorkspaceGuidancePayload({ kind: 'free-text', actor: '11' })).toBeNull();
  expect(buildStoryWorkspaceGuidancePayload({ kind: 'retry-step', actor: '11' })).toBeNull();
  expect(buildStoryWorkspaceGuidancePayload({ kind: 'retry-step', actor: '11', stepId: ' ' })).toBeNull();
  expect(buildStoryWorkspaceGuidancePayload({ kind: 'free-text', actor: ' ', text: 'x' })).toBeNull();
});

test('buildStoryWorkspaceGuidancePayload builds a retry-step command with optional note', () => {
  const payload = buildStoryWorkspaceGuidancePayload({
    kind: 'retry-step',
    actor: '11',
    stepId: 's3',
    text: '保持角色一致性',
  });
  expect(payload).toMatchObject({
    kind: 'retry-step',
    actor: '11',
    step_id: 's3',
    text: '保持角色一致性',
  });
  expect(payload?.idempotency_key).toMatch(/^swg_/);
});

test('newStoryWorkspaceGuidanceIdempotencyKey is unique and contract-sized', () => {
  const first = newStoryWorkspaceGuidanceIdempotencyKey();
  const second = newStoryWorkspaceGuidanceIdempotencyKey();
  expect(first).not.toBe(second);
  expect(first.startsWith('swg_')).toBe(true);
  expect(first.length).toBeLessThanOrEqual(255);
});

test('describeStoryWorkspaceGuidanceResult surfaces the dispatched:false pending state (R2)', () => {
    expect(
    describeStoryWorkspaceGuidanceResult({
      message_id: 'guide_k1',
      story_workspace_run_id: 'r1',
      review_action: 'guide',
      status: 'accepted',
      replayed: false,
      dispatched: true,
      request_id: 'req-1',
    }),
  ).toContain('已发送');
  const pending = describeStoryWorkspaceGuidanceResult({
    message_id: 'guide_k1',
    story_workspace_run_id: 'r1',
    review_action: 'guide',
    status: 'accepted',
    replayed: false,
    dispatched: false,
    request_id: 'req-1',
  });
  expect(pending).toContain('已记录');
  expect(pending).toContain('待执行 Agent 拾取');
  expect(
    describeStoryWorkspaceGuidanceResult({
      message_id: 'guide_k1',
      story_workspace_run_id: 'r1',
      review_action: 'guide',
      status: 'accepted',
      replayed: true,
      dispatched: false,
      request_id: 'req-1',
    }),
  ).toContain('幂等');
});

test('extractStoryWorkspaceGuidanceHistory reverse-looks guidance rows by metadata.kind', () => {
  const messages = [
    { id: 'm1', role: 'user', created_at: '2026-08-04T01:00:00Z', metadata: null },
    {
      id: 'guide_k1',
      role: 'user',
      created_at: '2026-08-04T01:01:00Z',
      metadata: {
        kind: 'story-workspace-guidance',
        story_workspace_run_id: 'r1',
        actor: '11',
        request_id: 'req-1',
        idempotency_key: 'k1',
        command_kind: 'free-text',
        step_id: null,
        text_summary: '第二集节奏放慢',
      },
    },
    {
      id: 'guide_k2',
      role: 'user',
      created_at: '2026-08-04T01:02:00Z',
      metadata: {
        kind: 'story-workspace-guidance',
        story_workspace_run_id: 'r1',
        actor: '11',
        request_id: 'req-2',
        idempotency_key: 'k2',
        command_kind: 'retry-step',
        step_id: 's3',
        text_summary: null,
      },
    },
    { id: 'm2', role: 'assistant', created_at: '2026-08-04T01:03:00Z', metadata: { kind: 'other' } },
  ];

  const history = extractStoryWorkspaceGuidanceHistory(messages);
  expect(history).toHaveLength(2);
  expect(history[0]).toEqual({
    messageId: 'guide_k1',
    createdAt: '2026-08-04T01:01:00Z',
    commandKind: 'free-text',
    stepId: null,
    textSummary: '第二集节奏放慢',
    requestId: 'req-1',
    idempotencyKey: 'k1',
  });
  expect(history[1]).toMatchObject({
    messageId: 'guide_k2',
    commandKind: 'retry-step',
    stepId: 's3',
  });
});

test('extractStoryWorkspaceGuidanceHistory skips malformed rows and keeps order', () => {
  expect(extractStoryWorkspaceGuidanceHistory([])).toEqual([]);
  const history = extractStoryWorkspaceGuidanceHistory([
    { id: 'x1', metadata: 'not-an-object' },
    { id: 'x2', metadata: { kind: 'story-workspace-guidance' } },
  ]);
  expect(history).toHaveLength(1);
  expect(history[0].messageId).toBe('x2');
  expect(history[0].commandKind).toBeNull();
});

function stubFetch(status: number, body: unknown): typeof fetch {
  return (async () => new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })) as typeof fetch;
}

test('submitStoryWorkspaceGuidance posts the idempotent command to the Task 3 endpoint', async () => {
  const calls: Array<{ url: string; init: RequestInit }> = [];
  const fetchImpl = (async (url: string, init: RequestInit) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({
      message_id: 'guide_k1',
      story_workspace_run_id: 'r1',
      review_action: 'guide',
      status: 'accepted',
      replayed: false,
      dispatched: false,
      request_id: 'req-1',
    }), { status: 202, headers: { 'Content-Type': 'application/json' } });
  }) as typeof fetch;

  const outcome = await submitStoryWorkspaceGuidance(storyWorkspaceGuidanceEndpoint('r1'), {
    kind: 'free-text',
    text: '放慢节奏',
    idempotency_key: 'k1',
    actor: '11',
  }, { fetchImpl, token: 'tk' });

  expect(outcome.ok).toBe(true);
  if (outcome.ok) {
    expect(outcome.result.dispatched).toBe(false);
    expect(outcome.result.request_id).toBe('req-1');
  }
  expect(calls).toHaveLength(1);
  expect(calls[0].url).toContain('/api/story-workspace/runs/r1/guidance');
  expect(calls[0].init.method).toBe('POST');
  expect((calls[0].init.headers as Headers).get('Authorization')).toBe('Bearer tk');
  expect(JSON.parse(String(calls[0].init.body))).toEqual({
    kind: 'free-text',
    text: '放慢节奏',
    idempotency_key: 'k1',
    actor: '11',
  });
});

test('submitStoryWorkspaceGuidance surfaces 409 error codes for the sidebar', async () => {
  const conflict = await submitStoryWorkspaceGuidance(storyWorkspaceGuidanceEndpoint('r1'), {
    kind: 'free-text',
    text: 'B',
    idempotency_key: 'k3',
    actor: '11',
  }, {
    fetchImpl: stubFetch(409, { error: { code: 'IDEMPOTENCY_CONFLICT' } }),
    token: 'tk',
  });
  expect(conflict).toEqual({ ok: false, status: 409, errorCode: 'IDEMPOTENCY_CONFLICT' });

  const notGuidable = await submitStoryWorkspaceGuidance(storyWorkspaceGuidanceEndpoint('r1'), {
    kind: 'free-text',
    text: 'x',
    idempotency_key: 'k4',
    actor: '11',
  }, {
    fetchImpl: stubFetch(409, { error: { code: 'WORKFLOW_RUN_NOT_GUIDABLE' } }),
    token: 'tk',
  });
  expect(notGuidable).toEqual({ ok: false, status: 409, errorCode: 'WORKFLOW_RUN_NOT_GUIDABLE' });

  const transport = await submitStoryWorkspaceGuidance(storyWorkspaceGuidanceEndpoint('r1'), {
    kind: 'free-text',
    text: 'x',
    idempotency_key: 'k5',
    actor: '11',
  }, {
    fetchImpl: (async () => {
      throw new Error('network down');
    }) as typeof fetch,
    token: 'tk',
  });
  expect(transport).toEqual({ ok: false, status: 0, errorCode: null });
});
