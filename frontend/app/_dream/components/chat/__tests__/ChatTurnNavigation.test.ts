// [Sync] 2026-11-26: cover current and released dispatch receipts across devices.
// [Input] Visible Chat turns, server index entries, and streaming/repair metadata.
// [Output] Regression coverage for one marker per real user input and accurate live reply state.
// [Pos] Provider-free turn-navigation projection contract.
// [Sync] 2026-09-29: keep streamed text in progress and merge saved/live markers by message ID.
// [Sync] 2026-11-26: cover stopped replies saved after a queued input and failures without a reply row.

import { expect, test } from '@playwright/test';
import type { UIMessage } from 'ai';
import { mergeTurnNavigation, projectVisibleTurnNavigation } from '../chatTurnNavigationModel';

function textMessage(id: string, role: UIMessage['role'], text: string, metadata?: UIMessage['metadata']): UIMessage {
  return { id, role, parts: [{ type: 'text', text }], metadata };
}

test('visible navigation excludes system inputs and keeps streamed text in progress', () => {
  const visible = projectVisibleTurnNavigation([
    textMessage('user-1', 'user', 'First question'),
    textMessage('reply-1', 'assistant', 'First answer', {
      turnId: 'turn-1', turnStatus: 'completed', finalPartIndex: 0,
    }),
    textMessage('repair', 'user', 'Internal repair', { kind: 'story-workspace-dream-auto-repair' }),
    textMessage('user-2', 'user', 'Second question'),
    textMessage('reply-2', 'assistant', 'Partial answer'),
  ], true);
  expect(visible.map((item) => [item.messageId, item.status])).toEqual([
    ['user-1', 'answered'],
    ['user-2', 'running'],
  ]);
  expect(visible[1].assistantPreview).toBe('Partial answer');

  const merged = mergeTurnNavigation([
    { ...visible[0], assistantPreview: 'Saved answer' },
  ], visible);
  expect(merged.map((item) => item.messageId)).toEqual(['user-1', 'user-2']);
  expect(merged[0].assistantPreview).toBe('First answer');
});

test('visible navigation uses dispatch receipts to restore stopped and failed turns', () => {
  const visible = projectVisibleTurnNavigation([
    textMessage('first', 'user', 'First question'),
    textMessage('second', 'user', 'Queued question'),
    textMessage('stopped-reply', 'assistant', 'Partial reply', {
      turnId: 'first-turn', turnStatus: 'cancelled', is_partial: true,
    }),
    textMessage('second-reply', 'assistant', 'Answer to the queued question', {
      turnId: 'second-turn', turnStatus: 'completed', finalPartIndex: 0,
    }),
    textMessage('third', 'user', 'Question without a saved reply'),
  ], false, [
    { message_id: 'first', dispatch_turn_id: 'first-turn', status: 'failed' },
    { message_id: 'second', dispatch_turn_id: 'second-turn', status: 'consumed' },
    { message_id: 'third', dispatch_turn_id: 'third-turn', status: 'failed' },
  ]);

  expect(visible.map(({ messageId, status, assistantPreview }) => [messageId, status, assistantPreview])).toEqual([
    ['first', 'cancelled', null],
    ['second', 'answered', 'Answer to the queued question'],
    ['third', 'failed', null],
  ]);
});

test('an active dispatch is running on either device', () => {
  const messages = [textMessage('saved-input', 'user', 'Earlier message')];
  const input = { message_id: 'saved-input', dispatch_turn_id: 'saved-turn', status: 'dispatching' } as const;
  expect(projectVisibleTurnNavigation(messages, false, [input])[0].status).toBe('running');
  expect(projectVisibleTurnNavigation(messages, true, [input])[0].status).toBe('running');
  expect(projectVisibleTurnNavigation(messages, true, [{ ...input, status: 'state_unknown' }])[0].status)
    .toBe('state_unknown');
});
