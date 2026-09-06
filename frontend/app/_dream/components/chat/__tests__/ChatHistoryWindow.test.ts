// [Input] Loaded message windows, overlapping latest pages, older pages, and concurrent live rows.
// [Output] Stable de-duplicated merge/prepend behavior without losing concurrent messages.
// [Pos] Provider-free pagination reducer regression seam.
// [Sync] 2026-09-02: created for page boundaries and concurrent live recovery.

import { expect, test } from '@playwright/test';
import type { UIMessage } from 'ai';
import {
  mergeRecoveredLatestPage,
  mergeCompleteHistoryWithLive,
  prependUniqueOlderMessages,
} from '../chatHistoryWindow';

function message(id: string, text = id, turnId?: string): UIMessage {
  return {
    id,
    role: 'assistant',
    parts: [{ type: 'text', text }],
    metadata: turnId ? { turnId } : undefined,
  };
}

test('older prepend de-duplicates the boundary and retains a concurrent live tail', () => {
  const current = [message('message-2'), message('message-3'), message('live-4')];
  const merged = prependUniqueOlderMessages(
    current,
    [message('message-1'), message('message-2', 'duplicate boundary')],
  );
  expect(merged.map((item) => item.id)).toEqual([
    'message-1',
    'message-2',
    'message-3',
    'live-4',
  ]);
  expect(merged.find((item) => item.id === 'message-2')?.parts[0]).toEqual({
    type: 'text',
    text: 'message-2',
  });
});

test('overlapping latest recovery refreshes persisted rows and keeps older/live window', () => {
  const recovered = mergeRecoveredLatestPage(
    [message('message-1'), message('message-2'), message('live-3')],
    [message('message-2', 'server-authoritative'), message('message-3')],
  );
  expect(recovered.overlapsLoadedWindow).toBe(true);
  expect(recovered.messages.map((item) => item.id)).toEqual([
    'message-1',
    'message-2',
    'live-3',
    'message-3',
  ]);
  expect(recovered.messages[1].parts[0]).toEqual({
    type: 'text',
    text: 'server-authoritative',
  });
});

test('persisted assistant replaces its live provisional id by stable turnId', () => {
  const recovered = mergeRecoveredLatestPage(
    [message('message-1'), message('live-assistant', 'streamed', 'turn-2')],
    [message('message-1'), message('persisted-assistant', 'complete', 'turn-2')],
  );
  expect(recovered.messages.map((item) => item.id)).toEqual([
    'message-1',
    'persisted-assistant',
  ]);
});

test('non-overlapping latest recovery resets an expired window instead of guessing order', () => {
  const recovered = mergeRecoveredLatestPage(
    [message('stale-1'), message('stale-2')],
    [message('latest-1'), message('latest-2')],
  );
  expect(recovered.overlapsLoadedWindow).toBe(false);
  expect(recovered.messages.map((item) => item.id)).toEqual(['latest-1', 'latest-2']);
});

test('whole-thread export retains older rows and replaces a persisted turn with live content', () => {
  const merged = mergeCompleteHistoryWithLive(
    [message('old-1'), message('persisted-assistant', 'persisted', 'turn-2')],
    [message('live-assistant', 'live', 'turn-2'), message('live-3')],
  );
  expect(merged.map((item) => item.id)).toEqual(['old-1', 'live-assistant', 'live-3']);
});
