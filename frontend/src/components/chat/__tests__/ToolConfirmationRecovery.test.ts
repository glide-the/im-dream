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
  interpretToolConfirmationResponse,
  resolvePendingToolConfirmation,
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
