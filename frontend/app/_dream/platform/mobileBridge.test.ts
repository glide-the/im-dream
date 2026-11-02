// [Input] In-memory iOS/Android bridge doubles and v1 response/event envelopes.
// [Output] Contract evidence for request/generation correlation, cancellation, errors, and ordered events.
// [Pos] Provider-free mobile bridge unit test; it does not claim native runtime validation.
// [Sync] 2026-10-24: keep abort cleanup coverage for the startup-owned timeout.
// [Sync] 2026-10-24: verify generic aborts do not invent runtime cancellation identifiers.
// [Sync] 2026-10-24: cover generation rejection and monotonic event delivery.

import assert from 'node:assert/strict';
import test from 'node:test';

import { MOBILE_BRIDGE_VERSION, MobileBridge, MobileBridgeError } from './mobileBridge.ts';

test('correlates an iOS response with its request', async () => {
  let posted: Record<string, unknown> | undefined;
  const bridge = new MobileBridge({ postMessage(message) { posted = message; } }, undefined, 'page_1');
  const result = bridge.call<{ platform: string }>('app.getInfo');
  assert.equal(posted?.method, 'app.getInfo');
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, id: posted?.id, pageGeneration: 'page_1', ok: true, result: { platform: 'ios' } });
  assert.deepEqual(await result, { platform: 'ios' });
});

test('serializes Android requests and consumes Android responses', async () => {
  let posted = '';
  const android = { postMessage(message: string) { posted = message; }, onmessage: null as ((event: { data: string }) => void) | null };
  const bridge = new MobileBridge(undefined, android, 'page_2');
  const result = bridge.call<{ state: string }>('lifecycle.getState');
  const request = JSON.parse(posted);
  android.onmessage?.({ data: JSON.stringify({ version: MOBILE_BRIDGE_VERSION, id: request.id, pageGeneration: 'page_2', ok: true, result: { state: 'active' } }) });
  assert.deepEqual(await result, { state: 'active' });
});

test('maps stable native errors', async () => {
  let posted: Record<string, unknown> | undefined;
  const bridge = new MobileBridge({ postMessage(message) { posted = message; } }, undefined, 'page_3');
  const result = bridge.call('runtime.request', { path: '/api/health' });
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, id: posted?.id, pageGeneration: 'page_3', ok: false, error: { code: 'CAPABILITY_UNAVAILABLE', message: 'Python unavailable.' } });
  await assert.rejects(result, (error: unknown) => error instanceof MobileBridgeError && error.code === 'CAPABILITY_UNAVAILABLE');
});

test('drops an aborted bridge call without inventing a runtime request identifier', async () => {
  const posted: Array<Record<string, unknown>> = [];
  const bridge = new MobileBridge({ postMessage(message) { posted.push(message); } }, undefined, 'page_4');
  const abort = new AbortController();
  const result = bridge.call('file.pick', {}, { signal: abort.signal });
  abort.abort();
  await assert.rejects(result, { name: 'AbortError' });
  assert.equal(posted.length, 1);
});

test('delivers only current-generation events in monotonic order', () => {
  const bridge = new MobileBridge({ postMessage() {} }, undefined, 'page_5');
  const received: unknown[] = [];
  bridge.on('network.changed', (payload) => received.push(payload));
  bridge.receive({ version: '2.0', pageGeneration: 'page_5', sequence: '1', event: 'network.changed', payload: { reachable: false } });
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, pageGeneration: 'old_page', sequence: '2', event: 'network.changed', payload: { reachable: false } });
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, pageGeneration: 'page_5', sequence: '3', event: 'unknown.changed', payload: {} });
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, pageGeneration: 'page_5', sequence: '4', event: 'network.changed', payload: { reachable: false } });
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, pageGeneration: 'page_5', sequence: '4', event: 'network.changed', payload: { reachable: true } });
  assert.deepEqual(received, [{ reachable: false }]);
});

test('ignores a response from an older page generation', async () => {
  let posted: Record<string, unknown> | undefined;
  const bridge = new MobileBridge({ postMessage(message) { posted = message; } }, undefined, 'page_current');
  const result = bridge.call('app.getInfo');
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, id: posted?.id, pageGeneration: 'page_old', ok: true, result: {} });
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, id: posted?.id, pageGeneration: 'page_current', ok: true, result: { platform: 'ios' } });
  assert.deepEqual(await result, { platform: 'ios' });
});
