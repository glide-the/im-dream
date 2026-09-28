// [Input] Production Thread input queue browser adapter and its persisted status DTO.
// [Output] Verify guide eligibility, stable message identity, revision and Browser session policy.
// [Pos] Provider-free Chat input queue state and transport contract regression.
// [Sync] 2026-09-26: active turn input uses an authenticated queue receipt rather than a second Chat stream.
// [Sync] 2026-09-27: retain ambiguous Admin outcomes so the UI asks for a status check before retry.
// [Sync] 2026-09-27: malformed success receipts fail closed before reaching Chat state.

import { expect, test } from '@playwright/test';
import { clearBrowserSession, loadBrowserSession } from '../../../lib/browserSession';
import {
  canGuideThreadInput, cancelThreadInput, enqueueThreadInput, fetchThreadInputs,
  moveThreadInputToSideTask, selectThreadInput, ThreadInputError, type ThreadInputEntry,
} from '../threadInputQueue';

const entry: ThreadInputEntry = {
  message_id: 'stable-message', thread_id: 'owned-thread', queue_sequence: '7',
  status: 'queued', revision: 3, dispatch_turn_id: null,
  created_at: '2026-09-26T00:00:00Z', text: 'please continue',
};

test('only a queued entry with the local owner can be selected for guidance', () => {
  for (const status of ['queued', 'selected', 'dispatching', 'consumed', 'cancelled', 'failed', 'state_unknown'] as const) {
    expect(canGuideThreadInput({ ...entry, status }, false)).toBe(false);
    expect(canGuideThreadInput({ ...entry, status }, true)).toBe(status === 'queued');
  }
});

test('queue adapter exposes an unknown write outcome without inventing a queued entry', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => new Response(JSON.stringify({
    detail: { error_code: 'ADMIN_DATA_UNAVAILABLE', outcome_unknown: true },
  }), { status: 503, headers: { 'Content-Type': 'application/json' } })) as typeof fetch;
  try {
    await expect(enqueueThreadInput('owned-thread', 'stable-message', 'please continue', 'auto', null, null))
      .rejects.toMatchObject<Partial<ThreadInputError>>({
        code: 'ADMIN_DATA_UNAVAILABLE', status: 503, outcomeUnknown: true,
      });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('queue adapter rejects a malformed successful snapshot', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => new Response('{}', {
    status: 200, headers: { 'Content-Type': 'application/json' },
  })) as typeof fetch;
  try {
    await expect(fetchThreadInputs('owned-thread')).rejects.toMatchObject<Partial<ThreadInputError>>({
      code: 'CHAT_INPUT_INVALID_RESPONSE', status: 502,
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('queue transport retains message ID and revision under the Browser session', async () => {
  const csrf = 'c'.repeat(43);
  await loadBrowserSession((async () => new Response(JSON.stringify({
    user: { id: '7', email: 'actor@example.test', display_name: 'Actor', avatar_url: null,
      role: 'user', created_at: '2026-09-26T00:00:00Z' },
    csrf_token: csrf,
  }), { status: 200, headers: { 'Content-Type': 'application/json' } })) as typeof fetch);
  const originalFetch = globalThis.fetch;
  const calls: Array<{ url: string; init: RequestInit }> = [];
  globalThis.fetch = (async (input, init) => {
    calls.push({ url: String(input), init: init ?? {} });
    const result = calls.length === 1 ? { entries: [entry], local_owner: true }
      : calls.length === 2 ? entry
      : calls.length === 3 ? { entry: { ...entry, status: 'selected', revision: 4 }, interrupt_signalled: true }
      : calls.length === 4 ? { ...entry, status: 'cancelled', revision: 4 }
      : { task_id: 'task-one', thread_id: 'child-thread', launch_status: 'starting', dispatch_started: true };
    return new Response(JSON.stringify(result), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }) as typeof fetch;
  try {
    expect((await fetchThreadInputs('owned-thread')).entries[0]).toEqual(entry);
    expect(await enqueueThreadInput('owned-thread', entry.message_id, entry.text, 'auto', null, null)).toEqual(entry);
    expect((await selectThreadInput('owned-thread', entry)).entry.status).toBe('selected');
    expect((await cancelThreadInput('owned-thread', entry)).status).toBe('cancelled');
    expect((await moveThreadInputToSideTask('owned-thread', entry)).thread_id).toBe('child-thread');
    expect(calls.map(call => call.url)).toEqual([
      '/api/claude-agent/threads/owned-thread/inputs',
      '/api/claude-agent/threads/owned-thread/inputs',
      '/api/claude-agent/threads/owned-thread/inputs/stable-message/select',
      '/api/claude-agent/threads/owned-thread/inputs/stable-message/cancel',
      '/api/claude-agent/threads/owned-thread/inputs/stable-message/side-task',
    ]);
    expect(calls[0].init.cache).toBe('no-store');
    expect(JSON.parse(String(calls[1].init.body)).message.id).toBe(entry.message_id);
    expect(JSON.parse(String(calls[2].init.body))).toEqual({ expected_revision: entry.revision });
    expect(JSON.parse(String(calls[3].init.body))).toEqual({ expected_revision: entry.revision });
    expect(JSON.parse(String(calls[4].init.body))).toEqual({ expected_revision: entry.revision });
    expect(new Headers(calls[1].init.headers).get('x-ink-csrf')).toBe(csrf);
  } finally {
    globalThis.fetch = originalFetch;
    clearBrowserSession();
  }
});
