// [Input] Production task-session link adapter and authenticated Browser request helpers.
// [Output] Verify strict relation/status parsing, read-only transport and malformed-response failure.
// [Pos] Provider-free task-session navigation transport regression.
// [Sync] 2026-09-27: add source/created relation read coverage without model or database writes.
// [Sync] 2026-09-27: cover owner-scoped runtime status and reject private or contradictory fields.
// [Sync] 2026-09-28: accept the server's completed status for committed task results.

import { expect, test } from '@playwright/test';
import { fetchTaskSessionDetail, fetchTaskSessionLinks, TaskSessionLinksError } from '../taskSessionLinks';

const link = {
  task_id: 'task-one', source_thread_id: 'source-thread', thread_id: 'child-thread',
  title: 'Review task', launch_status: 'starting' as const, launch_error_code: null,
  created_at: '2026-09-27T00:00:00Z',
};

test('task-session link adapter reads the current Thread without a mutation', async () => {
  const originalFetch = globalThis.fetch;
  const calls: Array<{ url: string; init: RequestInit }> = [];
  globalThis.fetch = (async (input, init) => {
    calls.push({ url: String(input), init: init ?? {} });
    return new Response(JSON.stringify({
      source: { ...link, source_title: 'Source conversation' }, created: [link],
    }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }) as typeof fetch;
  try {
    const result = await fetchTaskSessionLinks('thread/with spaces');
    expect(result.source?.source_title).toBe('Source conversation');
    expect(result.created).toEqual([link]);
    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe('/api/claude-agent/threads/thread%2Fwith%20spaces/task-links');
    expect(calls[0].init.method).toBeUndefined();
    expect(calls[0].init.cache).toBe('no-store');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('task-session link adapter rejects leaked or malformed fields', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => new Response(JSON.stringify({
    source: null, created: [{ ...link, user_id: '42' }],
  }), { status: 200, headers: { 'Content-Type': 'application/json' } })) as typeof fetch;
  try {
    await expect(fetchTaskSessionLinks('source-thread')).rejects.toMatchObject<Partial<TaskSessionLinksError>>({ status: 502 });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('task detail reads the server status for the exact business task', async () => {
  const originalFetch = globalThis.fetch;
  const calls: string[] = [];
  globalThis.fetch = (async (input) => {
    calls.push(String(input));
    return new Response(JSON.stringify({
      task_id: 'task-one', thread_id: 'child-thread', title: 'Review task',
      launch_status: 'starting', error_code: null, status: 'idle', running: false,
      result_message_id: 'assistant-result', result_text: 'Task finished.',
    }), { status: 200 });
  }) as typeof fetch;
  try {
    const detail = await fetchTaskSessionDetail('source/thread', 'task/one');
    expect(detail.status).toBe('idle');
    expect('result_text' in detail).toBe(false);
    expect(calls).toEqual(['/api/claude-agent/threads/source%2Fthread/tasks/task%2Fone']);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('task detail rejects client-visible private fields and contradictory running state', async () => {
  const originalFetch = globalThis.fetch;
  const base = { task_id: 'task-one', thread_id: 'child-thread', title: 'Review task', launch_status: 'starting', error_code: null, status: 'idle', running: false };
  try {
    for (const value of [{ ...base, session_id: 'private' }, { ...base, running: true }]) {
      globalThis.fetch = (async () => new Response(JSON.stringify(value), { status: 200 })) as typeof fetch;
      await expect(fetchTaskSessionDetail('source', 'task-one')).rejects.toMatchObject<Partial<TaskSessionLinksError>>({ status: 502 });
    }
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('task detail presents the server completed status without exposing result body', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => new Response(JSON.stringify({
    task_id: 'task-one', thread_id: 'child-thread', title: 'Review task',
    launch_status: 'starting', error_code: null, status: 'completed', running: false,
    result_message_id: 'final-message', result_text: 'Private complete result',
  }), { status: 200 })) as typeof fetch;
  try {
    const detail = await fetchTaskSessionDetail('source-thread', 'task-one');
    expect(detail.status).toBe('completed');
    expect('result_text' in detail).toBe(false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
