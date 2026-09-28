// [Input] Visible Chat turns, server index entries, and streaming/repair metadata.
// [Output] Regression coverage for one marker per real user input and accurate live reply state.
// [Pos] Provider-free turn-navigation projection contract.
// [Sync] 2026-09-29: keep streamed text in progress and merge saved/live markers by message ID.

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
