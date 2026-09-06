// [Input] Shared local/authoritative runtime facts.
// [Output] Stop visibility and strict stop response semantics.
// [Pos] Chat/Dream main-turn lifecycle contract seam.

import { expect, test } from '@playwright/test';
import {
  chatMainTurnCanStop,
  chatReconnectNonceForHydratedThread,
  claimChatReconnect,
  chatStopMayAbortLocalReaders,
  parseThreadStopResponse,
} from '../chatRuntimeState';

test('Stop is driven only by a cancellable main turn, never historical subagent transcript state', () => {
  expect(chatMainTurnCanStop('ready', false, false)).toBe(false);
  expect(chatMainTurnCanStop('submitted', false, false)).toBe(true);
  expect(chatMainTurnCanStop('streaming', false, false)).toBe(true);
  expect(chatMainTurnCanStop('ready', true, false)).toBe(true);
  expect(chatMainTurnCanStop('ready', false, true)).toBe(true);
});

test('Stop response requires explicit canonical acknowledgement', () => {
  expect(parseThreadStopResponse({ ok: true, stop_requested: true }))
    .toEqual({ stopRequested: true });
  expect(parseThreadStopResponse({ ok: true, stop_requested: false }))
    .toEqual({ stopRequested: false });
  expect(parseThreadStopResponse({ ok: true })).toBeNull();
  expect(parseThreadStopResponse({ ok: false, stop_requested: true })).toBeNull();
  expect(parseThreadStopResponse('ok')).toBeNull();
});

test('an unending local reader is aborted only by typed acknowledgement or authoritative idle', () => {
  expect(chatStopMayAbortLocalReaders(true, true)).toBe(true);
  expect(chatStopMayAbortLocalReaders(false, false)).toBe(true);
  expect(chatStopMayAbortLocalReaders(false, true)).toBe(false);
  expect(chatStopMayAbortLocalReaders(null, true)).toBe(false);
  expect(chatStopMayAbortLocalReaders(null, null)).toBe(false);
});

test('switching from a running thread cannot leak its reconnect nonce into an idle thread', () => {
  expect(chatReconnectNonceForHydratedThread(true, 7)).toBe(7);
  expect(chatReconnectNonceForHydratedThread(false, 7)).toBe(0);
});

test('two direct EOF recoveries each reconnect while authoritative idle creates no extra GET', () => {
  const initial = { external: 0, retry: 0 };
  const first = claimChatReconnect(true, 0, 1, initial);
  expect(first).toEqual({ external: 0, retry: 1 });
  expect(claimChatReconnect(false, 0, 1, first!)).toBeNull();

  const second = claimChatReconnect(true, 0, 2, first!);
  expect(second).toEqual({ external: 0, retry: 2 });
  expect(claimChatReconnect(false, 0, 2, second!)).toBeNull();
});

test('external reconnect consumption cannot race a later local POST before EOF', () => {
  const external = claimChatReconnect(
    true,
    4,
    2,
    { external: 0, retry: 0 },
  );
  expect(external).toEqual({ external: 4, retry: 2 });
  expect(claimChatReconnect(false, 0, 2, external!)).toBeNull();
  // A new primary POST marks runtime running, but retry=2 was already consumed
  // by the external stream and must not open a concurrent GET.
  expect(claimChatReconnect(true, 0, 2, external!)).toBeNull();
  // Only POST EOF/recovery advancing retry to 3 owns the next GET.
  expect(claimChatReconnect(true, 0, 3, external!))
    .toEqual({ external: 4, retry: 3 });
});
