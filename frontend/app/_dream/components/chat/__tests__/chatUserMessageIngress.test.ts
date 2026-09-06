// [Input] Pure Chat user-message ingress coordinator and observable callback fakes.
// [Output] Regression evidence for ordering, metadata, Editor persistence, and empty-message rejection.
// [Pos] Unit contract for composer, queued-prompt, and MCP Apps UI-message convergence.
// [Sync] 2026-09-06: prove MCP-originated messages cannot bypass the normal Chat turn boundary.

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  sendCoordinatedChatUserMessage,
  type ChatUserMessage,
} from '../chatUserMessageIngress.ts';

test('coordinated ingress applies Chat state and persistence before transport dispatch', async () => {
  const order: string[] = [];
  const message: ChatUserMessage = {
    role: 'user',
    parts: [{ type: 'text', text: 'Use this App selection' }],
  };
  const dispatched = await sendCoordinatedChatUserMessage(
    message,
    { rawAttachments: ['attachment-a'], toolChoice: 'manual' },
    {
      onConversationStart: () => order.push('conversation'),
      setToolChoice: (choice) => order.push(`tool:${choice}`),
      setPendingData: (value) => order.push(`pending:${value.rawAttachments.join(',')}`),
      ensureEditorSessionPersisted: async () => { order.push('editor'); },
      incrementTurnGeneration: () => order.push('generation'),
      dispatch: async (value) => {
        assert.equal(value, message);
        order.push('dispatch');
      },
    },
  );

  assert.equal(dispatched, true);
  assert.deepEqual(order, [
    'conversation',
    'tool:manual',
    'pending:attachment-a',
    'editor',
    'generation',
    'dispatch',
  ]);
});

test('coordinated ingress rejects an empty message without mutating Chat state', async () => {
  const calls: string[] = [];
  const dispatched = await sendCoordinatedChatUserMessage(
    { role: 'user', parts: [] },
    {},
    {
      onConversationStart: () => calls.push('conversation'),
      setToolChoice: () => calls.push('tool'),
      setPendingData: () => calls.push('pending'),
      ensureEditorSessionPersisted: async () => { calls.push('editor'); },
      incrementTurnGeneration: () => calls.push('generation'),
      dispatch: async () => { calls.push('dispatch'); },
    },
  );

  assert.equal(dispatched, false);
  assert.deepEqual(calls, []);
});
