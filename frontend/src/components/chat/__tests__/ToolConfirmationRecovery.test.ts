// [Input] Chat tool confirmation response decoder and pending-part classifier.
// [Output] Regression coverage for already-resolved confirmations after SSE reconnect.
// [Pos] Generic Chat confirmation recovery TDD seam.

import { expect, test } from '@playwright/test';
import type { DynamicToolUIPart } from 'ai';
import { consumeClaudeAgentSseStream } from '../../../lib/claude-agent-sse-utils';
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
