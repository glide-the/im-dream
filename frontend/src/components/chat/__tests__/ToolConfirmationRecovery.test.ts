// [Input] Chat tool confirmation response decoder and pending-part classifier.
// [Output] Regression coverage for already-resolved confirmations after SSE reconnect.
// [Pos] Generic Chat confirmation recovery TDD seam.

import { expect, test } from '@playwright/test';
import type { DynamicToolUIPart } from 'ai';
import { ClaudeAgentChatTransport } from '../../../lib/claude-agent-transport';
import {
  consumeClaudeAgentSseStream,
  parseClaudeAgentSseBuffer,
} from '../../../lib/claude-agent-sse-utils';
import {
  shouldApplyChatHistoryRecoverySnapshot,
} from '../chatRecovery';
import {
  deriveSettledToolCallIdsFromHistory,
  interpretToolConfirmationResponse,
  loadChatHistoryThenRuntimeStatus,
  parseChatThreadStatus,
  resolvePendingToolConfirmation,
  runtimePendingToolCallIdsFromStatus,
} from '../toolConfirmation';

const stalePart: DynamicToolUIPart = {
  type: 'dynamic-tool',
  toolCallId: 'call-stale',
  toolName: 'Agent',
  state: 'input-available',
  input: { description: 'Compute sha256 project slug' },
  toolMetadata: { approvalRequested: true },
};

test('a locally settled replayed tool part cannot reopen the confirmation dock', () => {
  expect(resolvePendingToolConfirmation(stalePart, 'auto')).toBe('confirm');
  expect(resolvePendingToolConfirmation(
    stalePart,
    'auto',
    new Set(['call-stale']),
  )).toBeNull();
});

test('known runtime status settles only historical tool calls that are no longer pending', () => {
  const history = [{
    id: 'assistant-history',
    role: 'assistant' as const,
    parts: [
      stalePart,
      { ...stalePart, toolCallId: 'call-pending' },
    ],
  }];
  const status = parseChatThreadStatus({
    running: true,
    lifecycle: 'running',
    turn_count: 2,
    pending_tool_call_ids: ['call-pending'],
    tool_confirmation_observation: 'known',
  });

  const settled = deriveSettledToolCallIdsFromHistory(history, status);
  const runtimePending = runtimePendingToolCallIdsFromStatus(status);

  expect([...settled]).toEqual(['call-stale']);
  expect(resolvePendingToolConfirmation(stalePart, 'manual', settled)).toBeNull();
  expect(resolvePendingToolConfirmation(
    { ...stalePart, toolCallId: 'call-pending', toolMetadata: undefined },
    'auto',
    settled,
    runtimePending,
  )).toBe('confirm');
  expect(resolvePendingToolConfirmation(
    { ...stalePart, toolCallId: 'call-live-new' },
    'manual',
    settled,
  )).toBe('confirm');
});

test('known empty idle status settles stale history while unknown status settles nothing', () => {
  const history = [{ id: 'assistant-history', role: 'assistant' as const, parts: [stalePart] }];
  const known = parseChatThreadStatus({
    running: false,
    lifecycle: 'idle',
    turn_count: 3,
    pending_tool_call_ids: [],
    tool_confirmation_observation: 'known',
  });
  const unknown = parseChatThreadStatus({
    running: true,
    lifecycle: 'running',
    turn_count: 3,
    pending_tool_call_ids: [],
    tool_confirmation_observation: 'unknown',
  });

  expect([...deriveSettledToolCallIdsFromHistory(history, known)]).toEqual(['call-stale']);
  expect([...deriveSettledToolCallIdsFromHistory(history, unknown)]).toEqual([]);
});

test('malformed status cannot be interpreted as a known-empty observation', () => {
  const base = {
    running: false,
    lifecycle: 'idle',
    turn_count: 3,
    pending_tool_call_ids: [],
    tool_confirmation_observation: 'known',
  };
  expect(parseChatThreadStatus(base)?.tool_confirmation_observation).toBe('known');
  expect(parseChatThreadStatus({ ...base, pending_tool_call_ids: 'call-stale' })).toBeNull();
  expect(parseChatThreadStatus({ ...base, pending_tool_call_ids: [''] })).toBeNull();
  expect(parseChatThreadStatus({
    ...base,
    lifecycle: 'running',
    running: true,
    pending_tool_call_ids: Array.from({ length: 257 }, (_, index) => `call-${index}`),
  })).toBeNull();
  expect(parseChatThreadStatus({ ...base, tool_confirmation_observation: 'settled' })).toBeNull();
  expect(parseChatThreadStatus({ ...base, running: 'false' })).toBeNull();
  expect(parseChatThreadStatus({ ...base, lifecycle: 'unknown' })).toBeNull();
  expect(parseChatThreadStatus({ ...base, turn_count: -1 })).toBeNull();
});

test('recovery samples runtime confirmation ownership only after history resolves', async () => {
  const order: string[] = [];
  const recovery = await loadChatHistoryThenRuntimeStatus(
    async () => {
      order.push('history:start');
      await Promise.resolve();
      order.push('history:end');
      return [{ id: 'assistant-history' }];
    },
    async () => {
      order.push('status');
      return null;
    },
  );

  expect(order).toEqual(['history:start', 'history:end', 'status']);
  expect(recovery.history).toEqual([{ id: 'assistant-history' }]);
  expect(recovery.status).toBeNull();
});

test('idle observed after history reloads the terminal turn before Chat resumes', async () => {
  const order: string[] = [];
  let historyRead = 0;
  const recovery = await loadChatHistoryThenRuntimeStatus(
    async () => {
      historyRead += 1;
      order.push(`history:${historyRead}`);
      return historyRead === 1
        ? [{ id: 'dream-user' }]
        : [{ id: 'dream-user' }, { id: 'dream-assistant-terminal' }];
    },
    async () => {
      order.push('status:idle');
      return {
        running: false,
        lifecycle: 'idle',
        turn_count: 1,
        pending_tool_call_ids: [],
        tool_confirmation_observation: 'known',
      };
    },
  );

  expect(order).toEqual(['history:1', 'status:idle', 'history:2']);
  expect(recovery.history).toEqual([
    { id: 'dream-user' },
    { id: 'dream-assistant-terminal' },
  ]);
});

test('a delayed reconnect snapshot cannot overwrite a newer local turn', () => {
  const requestedAt = { threadId: 'thread-1', reconnectNonce: 4, turnGeneration: 7 };
  const refreshed = [{ id: 'persisted-terminal-assistant' }];
  expect(shouldApplyChatHistoryRecoverySnapshot(requestedAt, requestedAt, refreshed)).toBe(true);
  expect(shouldApplyChatHistoryRecoverySnapshot(
    requestedAt,
    { ...requestedAt, turnGeneration: 8 },
    refreshed,
  )).toBe(false);
  expect(shouldApplyChatHistoryRecoverySnapshot(
    requestedAt,
    { ...requestedAt, reconnectNonce: 5 },
    refreshed,
  )).toBe(false);
  expect(shouldApplyChatHistoryRecoverySnapshot(
    requestedAt,
    { ...requestedAt, threadId: 'thread-2' },
    refreshed,
  )).toBe(false);
  expect(shouldApplyChatHistoryRecoverySnapshot(requestedAt, requestedAt, undefined)).toBe(false);
});

test('a finish frame does not make history recoverable until the stream reaches EOF', async () => {
  let streamController: ReadableStreamDefaultController<Uint8Array> | undefined;
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      streamController = controller;
      controller.enqueue(new TextEncoder().encode('data: {"type":"finish"}\n\n'));
    },
  });
  const seenEvents: string[] = [];
  let reachedEof = false;
  const consumption = consumeClaudeAgentSseStream(stream.getReader(), (event) => {
    seenEvents.push(event.type);
  }).then(() => {
    reachedEof = true;
  });

  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(seenEvents).toEqual(['finish']);
  expect(reachedEof).toBe(false);

  streamController?.close();
  await consumption;
  expect(reachedEof).toBe(true);
});

test('SSE consumption preserves an event split across arbitrary UTF-8 network chunks', async () => {
  const raw = [
    ': keepalive\r\n\r\n',
    'data: {"type":"text-delta","id":"text-1","delta":"中文🙂\\nquoted: \\"ok\\""}\r\n\r\n',
    'data: {"type":"finish","finishReason":"stop"}\r\n\r\n',
  ].join('');
  const encoded = new TextEncoder().encode(raw);
  const splitPoints = [1, 7, 19, 43, 44, 47, 70, encoded.length - 3];
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      let offset = 0;
      for (const end of [...splitPoints, encoded.length]) {
        controller.enqueue(encoded.slice(offset, end));
        offset = end;
      }
      controller.close();
    },
  });
  const events: Array<Record<string, unknown>> = [];

  await consumeClaudeAgentSseStream(stream.getReader(), (event) => {
    events.push(event);
  });

  expect(events).toEqual([
    { type: 'text-delta', id: 'text-1', delta: '中文🙂\nquoted: "ok"' },
    { type: 'finish', finishReason: 'stop' },
  ]);
});

test('primary chat transport converts a text delta split across network chunks', async () => {
  class TestTransport extends ClaudeAgentChatTransport {
    convert(stream: ReadableStream<Uint8Array>) {
      return this.processResponseStream(stream);
    }
  }

  const encoded = new TextEncoder().encode([
    'data: {"type":"text-start","id":"text-main"}\n\n',
    'data: {"type":"text-delta","id":"text-main","delta":"逐步输出"}\n\n',
    'data: {"type":"text-end","id":"text-main"}\n\n',
    'data: {"type":"finish","finishReason":"stop"}\n\n',
  ].join(''));
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (let offset = 0; offset < encoded.length; offset += 5) {
        controller.enqueue(encoded.slice(offset, Math.min(offset + 5, encoded.length)));
      }
      controller.close();
    },
  });
  const reader = new TestTransport().convert(stream).getReader();
  const chunks: Array<Record<string, unknown>> = [];
  while (true) {
    const next = await reader.read();
    if (next.done) break;
    chunks.push(next.value as unknown as Record<string, unknown>);
  }

  expect(chunks).toContainEqual({
    type: 'text-delta',
    id: 'text-main',
    delta: '逐步输出',
  });
  expect(chunks.at(-1)).toEqual({ type: 'finish', finishReason: 'stop' });
});

test('primary Chat transport preserves 334 deltas across unrelated network chunks', async () => {
  class TestTransport extends ClaudeAgentChatTransport {
    convert(stream: ReadableStream<Uint8Array>) {
      return this.processResponseStream(stream);
    }
  }

  const expected = Array.from(
    { length: 334 },
    (_, index) => `消息-${index}-中文🙂\n`,
  );
  const raw = [
    'data: {"type":"text-start","id":"text-main"}\n\n',
    ...expected.map((delta) => `data: ${JSON.stringify({
      type: 'text-delta',
      id: 'text-main',
      delta,
    })}\n\n`),
    'data: {"type":"text-end","id":"text-main"}\n\n',
    'data: {"type":"finish","finishReason":"stop"}\n\n',
  ].join('');
  const encoded = new TextEncoder().encode(raw);
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      let offset = 0;
      let sequence = 0;
      while (offset < encoded.length) {
        const width = (sequence * 17) % 53 + 1;
        controller.enqueue(encoded.slice(offset, Math.min(offset + width, encoded.length)));
        offset += width;
        sequence += 1;
      }
      controller.close();
    },
  });
  const reader = new TestTransport().convert(stream).getReader();
  const observed: string[] = [];
  while (true) {
    const next = await reader.read();
    if (next.done) break;
    if (next.value.type === 'text-delta') {
      observed.push(next.value.delta);
    }
  }

  expect(observed).toEqual(expected);
});

test('SSE parser joins multiline data and accepts multiple events in one chunk', () => {
  const events = parseClaudeAgentSseBuffer([
    'event: message',
    'data: {"type":"text-delta",',
    'data: "id":"text-2","delta":"hello"}',
    '',
    'data:{"type":"finish","finishReason":"stop"}',
    '',
    '',
  ].join('\n'));

  expect(events).toEqual([
    { type: 'text-delta', id: 'text-2', delta: 'hello' },
    { type: 'finish', finishReason: 'stop' },
  ]);
});

test('SSE consumption accepts mixed line endings at frame boundaries', async () => {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(
        'data: {"type":"text-delta","id":"mixed","delta":"A"}\r\n\n'
        + 'data: {"type":"finish","finishReason":"stop"}\n\r\n',
      ));
      controller.close();
    },
  });
  const events: Array<Record<string, unknown>> = [];

  await consumeClaudeAgentSseStream(stream.getReader(), (event) => {
    events.push(event);
  });

  expect(events.map((event) => event.type)).toEqual(['text-delta', 'finish']);
});

test('SSE consumption parses a complete EOF tail without a final blank line', async () => {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(
        'data: {"type":"error","errorText":"upstream closed"}',
      ));
      controller.close();
    },
  });
  const events: Array<Record<string, unknown>> = [];

  await consumeClaudeAgentSseStream(stream.getReader(), (event) => {
    events.push(event);
  });

  expect(events).toEqual([{ type: 'error', errorText: 'upstream closed' }]);
});

test('typed not-pending conflict is recoverable but ownership failures are not', () => {
  expect(interpretToolConfirmationResponse(200, { ok: true, approved: true })).toEqual({
    state: 'resolved',
    approved: true,
  });
  expect(interpretToolConfirmationResponse(409, {
    detail: {
      code: 'TOOL_CONFIRMATION_NOT_PENDING',
      tool_call_id: 'call-stale',
    },
  }, 'call-stale')).toEqual({ state: 'not-pending' });
  expect(interpretToolConfirmationResponse(409, {
    detail: {
      code: 'TOOL_CONFIRMATION_NOT_PENDING',
      tool_call_id: 'call-other',
    },
  }, 'call-stale')).toEqual({
    state: 'error',
    message: 'Tool confirmation failed.',
  });
  expect(interpretToolConfirmationResponse(404, { detail: 'Thread not found' })).toEqual({
    state: 'error',
    message: 'Thread not found',
  });
});
