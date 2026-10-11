// [Input] Original POST transport and Stop endpoint with controlled admission order.
// [Output] Provider-free submission ownership, remount-independent Stop and retry isolation contracts.
// [Pos] Chat cancellation regression; no normal account, model or database.
// [Sync] 2026-10-12: cover Stop before headers/admission and unknown versus terminal outcomes.
import { expect, test } from '@playwright/test';
import {
  beginClaudeThreadSubmission, observeClaudeThreadSubmission,
  claudeThreadStopPending, requestClaudeSubmittedThreadStop, subscribeClaudeThreadStop,
} from '../threadStop';
import { ClaudeAgentChatTransport } from '../../../lib/claude-agent-transport';

const receipt = (thread: string, stopped = false) => new Response(JSON.stringify({
  ok: true, thread_id: thread, stop_requested: stopped, running: false, lifecycle: 'idle',
}), { headers: { 'content-type': 'application/json' } });
const tick = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

test('early idle retains Stop until the original POST emits a production frame', async () => {
  const thread = 'submission-stop-early';
  let releaseHeaders!: () => void;
  const headers = new Promise<void>((resolve) => { releaseHeaders = resolve; });
  const transport = new ClaudeAgentChatTransport({
    threadId: thread, headers: async () => { await headers; return {}; },
    prepareSendMessagesRequest: ({ messages }) => ({ body: { message: messages.at(-1) } }),
    fetch: async () => new Response('data: {"type":"message-metadata","turnId":"turn-original"}\n\ndata: {"type":"finish","finishReason":"stop"}\n\n'),
  });
  const submitted = transport.sendMessages({ trigger: 'submit-message', chatId: thread,
    messages: [{ id: 'original-user', role: 'user', parts: [{ type: 'text', text: 'image' }] }] });
  let calls = 0;
  const stopped = requestClaudeSubmittedThreadStop(thread, (async () => receipt(thread, ++calls > 1)) as typeof fetch);
  await tick();
  expect(calls).toBe(1);
  expect(claudeThreadStopPending(thread)).toBe(true);
  releaseHeaders();
  const reader = (await submitted).getReader();
  while (!(await reader.read()).done) { /* original stream only */ }
  await stopped;
  expect(claudeThreadStopPending(thread)).toBe(false);
  // A terminal may arrive before the deferred Stop; it also proves no late startup.
  expect(calls).toBeLessThanOrEqual(2);
});

test('pending Stop outlives subscriptions and performs one same-submission deferred Stop', async () => {
  const thread = 'submission-stop-remount';
  const ticket = beginClaudeThreadSubmission(thread, 'user-remount');
  let calls = 0;
  const unsubscribe = subscribeClaudeThreadStop(thread, () => {});
  const stopped = requestClaudeSubmittedThreadStop(thread, (async () => receipt(thread, ++calls > 1)) as typeof fetch);
  await tick(); unsubscribe();
  expect(claudeThreadStopPending(thread)).toBe(true);
  observeClaudeThreadSubmission(ticket, 'accepted');
  expect((await stopped).stopRequested).toBe(true);
  expect(calls).toBe(2);
  const retry = beginClaudeThreadSubmission(thread, 'new-user');
  observeClaudeThreadSubmission(retry, 'accepted');
  expect(claudeThreadStopPending(thread)).toBe(false);
  expect(calls).toBe(2);
});

test('HTTP rejection settles early Stop but unknown cannot become idle or a retry', async () => {
  for (const phase of ['rejected', 'unknown'] as const) {
    const thread = `submission-stop-${phase}`;
    const ticket = beginClaudeThreadSubmission(thread, 'original-user');
    let calls = 0;
    const stopped = requestClaudeSubmittedThreadStop(thread, (async () => { calls++; return receipt(thread); }) as typeof fetch);
    await tick(); observeClaudeThreadSubmission(ticket, phase);
    if (phase === 'unknown') {
      await expect(stopped).rejects.toMatchObject({ code: 'STOP_TRANSPORT_FAILED' });
      expect(claudeThreadStopPending(thread)).toBe(true);
      // Only a same-stream production terminal can settle this uncertainty.
      observeClaudeThreadSubmission(ticket, 'terminal');
    } else await stopped;
    expect(calls).toBe(1);
    expect(claudeThreadStopPending(thread)).toBe(false);
  }
});

test('a production terminal cannot unlock retry while the already sent Stop is unresolved', async () => {
  const thread = 'submission-stop-terminal';
  const ticket = beginClaudeThreadSubmission(thread, 'original-user');
  let release!: () => void;
  const wait = new Promise<void>((resolve) => { release = resolve; });
  const stopped = requestClaudeSubmittedThreadStop(thread, (async () => { await wait; return receipt(thread); }) as typeof fetch);
  observeClaudeThreadSubmission(ticket, 'terminal');
  expect(claudeThreadStopPending(thread)).toBe(true);
  release(); await stopped;
  expect(claudeThreadStopPending(thread)).toBe(false);
});

test('a pending Stop prevents a new submission replacing its owner', async () => {
  const thread = 'submission-stop-old';
  const old = beginClaudeThreadSubmission(thread, 'old-user');
  let calls = 0;
  const stopped = requestClaudeSubmittedThreadStop(thread, (async () => receipt(thread, ++calls > 1)) as typeof fetch);
  await tick();
  expect(() => beginClaudeThreadSubmission(thread, 'new-user')).toThrow();
  observeClaudeThreadSubmission(old, 'accepted');
  await stopped;
  expect(calls).toBe(2);
  beginClaudeThreadSubmission(thread, 'new-user');
  expect(claudeThreadStopPending(thread)).toBe(false);
});

test('admission before the early idle response arrives still requires same-submission Stop', async () => {
  const thread = 'submission-stop-stale-receipt';
  const ticket = beginClaudeThreadSubmission(thread, 'original-user');
  let release!: () => void;
  const delayed = new Promise<void>((resolve) => { release = resolve; });
  let calls = 0;
  const stopped = requestClaudeSubmittedThreadStop(thread, (async () => {
    calls++;
    if (calls === 1) { await delayed; return receipt(thread); }
    return receipt(thread, true);
  }) as typeof fetch);
  observeClaudeThreadSubmission(ticket, 'accepted');
  release();
  expect((await stopped).stopRequested).toBe(true);
  expect(calls).toBe(2);
});

test('interleaved response bodies retain their own submission identity', async () => {
  const thread = 'submission-stop-interleaved';
  const bodies = new Map<string, ReadableStreamDefaultController<Uint8Array>>();
  const transport = new ClaudeAgentChatTransport({ threadId: thread,
    prepareSendMessagesRequest: ({ messages }) => ({ body: { message: messages.at(-1) } }),
    fetch: async (_input, init) => {
      const id = JSON.parse(init?.body as string).message.id as string;
      return new Response(new ReadableStream<Uint8Array>({ start(controller) { bodies.set(id, controller); } }));
    },
  });
  const submit = (id: string) => transport.sendMessages({ trigger: 'submit-message', chatId: thread,
    messages: [{ id, role: 'user', parts: [{ type: 'text', text: 'image' }] }] });
  const first = submit('first-user');
  const second = submit('second-user');
  const read = async (stream: ReadableStream) => { const reader = stream.getReader(); while (!(await reader.read()).done) { /* Consume the original response only. */ } };
  const firstReader = read(await first);
  const secondReader = read(await second);
  let calls = 0;
  const stopped = requestClaudeSubmittedThreadStop(thread, (async () => receipt(thread, ++calls > 1)) as typeof fetch);
  await tick();
  const encode = (type: string) => new TextEncoder().encode(`data: ${JSON.stringify({ type, finishReason: 'stop' })}\n\n`);
  bodies.get('first-user')!.enqueue(encode('finish')); bodies.get('first-user')!.close();
  await firstReader; await tick();
  expect(claudeThreadStopPending(thread)).toBe(true);
  expect(calls).toBe(1);
  bodies.get('second-user')!.enqueue(encode('message-metadata'));
  expect((await stopped).stopRequested).toBe(true);
  expect(calls).toBe(2);
  bodies.get('second-user')!.enqueue(encode('finish')); bodies.get('second-user')!.close();
  await secondReader;
});
