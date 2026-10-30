// [Input] In-memory native bridge responses for local request heads and pull-stream chunks.
// [Output] Provider-free evidence for path/header gates, streaming, and reader cancellation.
// [Pos] Browser-side mobile transport unit test; it does not start Python or a model runtime.
// [Sync] 2026-10-24: cover response validation and cancellation before a response head exists.
// [Sync] 2026-10-24: cover the first fetch-compatible pull-stream adapter.

import assert from 'node:assert/strict';
import test from 'node:test';

import { MOBILE_BRIDGE_VERSION, MobileBridge, MobileBridgeError } from './mobileBridge.ts';
import { createMobileRuntimeFetch, installMobileRuntimeFetch } from './mobileRuntimeTransport.ts';

type Posted = Record<string, unknown>;

async function nextPosted(posted: Posted[], index: number): Promise<Posted> {
  for (let attempt = 0; attempt < 20 && !posted[index]; attempt += 1) await new Promise((resolve) => setTimeout(resolve, 0));
  assert.ok(posted[index]);
  return posted[index];
}

test('turns pull chunks into a fetch-compatible response body', async () => {
  const posted: Posted[] = [];
  const bridge = new MobileBridge({ postMessage(message) { posted.push(message); } }, undefined, 'page_transport');
  const mobileFetch = createMobileRuntimeFetch(bridge);
  const responsePromise = mobileFetch('/api/threads/one', { headers: { accept: 'text/event-stream' } });
  const open = await nextPosted(posted, 0);
  bridge.receive({
    version: MOBILE_BRIDGE_VERSION, id: open.id, pageGeneration: 'page_transport', ok: true,
    result: { requestId: 'runtime_1', streamId: 'stream_1', status: 200, headers: { 'content-type': 'text/event-stream' } },
  });
  const response = await responsePromise;
  const textPromise = response.text();
  const read = await nextPosted(posted, 1);
  assert.equal(read.method, 'runtime.response.read');
  bridge.receive({
    version: MOBILE_BRIDGE_VERSION, id: read.id, pageGeneration: 'page_transport', ok: true,
    result: { dataBase64: btoa('data: ok\n\n'), done: true },
  });
  assert.equal(await textPromise, 'data: ok\n\n');
});

test('rejects absolute URLs and service credentials before bridge dispatch', async () => {
  const posted: Posted[] = [];
  const bridge = new MobileBridge({ postMessage(message) { posted.push(message); } }, undefined, 'page_gate');
  const mobileFetch = createMobileRuntimeFetch(bridge);
  await assert.rejects(mobileFetch('https://example.com/api/threads'), (error: unknown) => error instanceof MobileBridgeError && error.code === 'FORBIDDEN');
  await assert.rejects(mobileFetch('/api/threads', { headers: { authorization: 'Bearer forbidden' } }), (error: unknown) => error instanceof MobileBridgeError && error.code === 'FORBIDDEN');
  assert.equal(posted.length, 0);
});

test('cancels the runtime stream when the response reader cancels', async () => {
  const posted: Posted[] = [];
  const bridge = new MobileBridge({ postMessage(message) { posted.push(message); } }, undefined, 'page_cancel');
  const responsePromise = createMobileRuntimeFetch(bridge)('/api/stream');
  const open = await nextPosted(posted, 0);
  bridge.receive({
    version: MOBILE_BRIDGE_VERSION, id: open.id, pageGeneration: 'page_cancel', ok: true,
    result: { requestId: 'runtime_2', streamId: 'stream_2', status: 200 },
  });
  const reader = (await responsePromise).body?.getReader();
  assert.ok(reader);
  const cancelled = reader.cancel();
  const pendingRead = await nextPosted(posted, 1);
  assert.equal(pendingRead.method, 'runtime.response.read');
  bridge.receive({
    version: MOBILE_BRIDGE_VERSION, id: pendingRead.id, pageGeneration: 'page_cancel', ok: true,
    result: { dataBase64: '', done: false },
  });
  const cancel = await nextPosted(posted, 2);
  assert.equal(cancel.method, 'runtime.cancel');
  assert.deepEqual(cancel.params, { requestId: 'runtime_2', streamId: 'stream_2' });
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, id: cancel.id, pageGeneration: 'page_cancel', ok: true, result: {} });
  await cancelled;
});

test('installs a scoped router for relative Dream paths and restores the prior fetch', async () => {
  const posted: Posted[] = [];
  const bridge = new MobileBridge({ postMessage(message) { posted.push(message); } }, undefined, 'page_install');
  const originalFetch = globalThis.fetch;
  const delegated: unknown[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    delegated.push(input);
    return new Response('asset');
  }) as typeof fetch;
  const restore = installMobileRuntimeFetch(bridge);
  try {
    const runtimeResponse = fetch('/api/health');
    const open = await nextPosted(posted, 0);
    bridge.receive({
      version: MOBILE_BRIDGE_VERSION, id: open.id, pageGeneration: 'page_install', ok: true,
      result: { requestId: 'runtime_install', streamId: 'stream_install', status: 204 },
    });
    const cancel = await nextPosted(posted, 1);
    assert.equal(cancel.method, 'runtime.cancel');
    bridge.receive({ version: MOBILE_BRIDGE_VERSION, id: cancel.id, pageGeneration: 'page_install', ok: true, result: {} });
    assert.equal((await runtimeResponse).status, 204);
    assert.equal(delegated.length, 0);
    assert.equal(await (await fetch('data:text/plain,asset')).text(), 'asset');
    assert.deepEqual(delegated, ['data:text/plain,asset']);
  } finally {
    restore();
    globalThis.fetch = originalFetch;
  }
});

test('cancels by client request ID when abort happens before the response head', async () => {
  const posted: Posted[] = [];
  const bridge = new MobileBridge({ postMessage(message) { posted.push(message); } }, undefined, 'page_pre_head_cancel');
  const abort = new AbortController();
  const response = createMobileRuntimeFetch(bridge)('/api/stream', { signal: abort.signal });
  const open = await nextPosted(posted, 0);
  const clientRequestId = (open.params as Record<string, unknown>).clientRequestId;
  assert.equal(typeof clientRequestId, 'string');
  const rejection = assert.rejects(response, (error: unknown) => error instanceof DOMException && error.name === 'AbortError');
  abort.abort();
  const cancel = await nextPosted(posted, 1);
  assert.equal(cancel.method, 'runtime.cancel');
  assert.deepEqual(cancel.params, { requestId: clientRequestId });
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, id: cancel.id, pageGeneration: 'page_pre_head_cancel', ok: true, result: {} });
  await rejection;
});

test('rejects invalid status and oversized or empty non-terminal chunks', async () => {
  for (const invalidStatus of [101, 600]) {
    const posted: Posted[] = [];
    const bridge = new MobileBridge({ postMessage(message) { posted.push(message); } }, undefined, `page_status_${invalidStatus}`);
    const response = createMobileRuntimeFetch(bridge)('/api/status');
    const open = await nextPosted(posted, 0);
    bridge.receive({
      version: MOBILE_BRIDGE_VERSION, id: open.id, pageGeneration: `page_status_${invalidStatus}`, ok: true,
      result: { requestId: `runtime_${invalidStatus}`, streamId: `stream_${invalidStatus}`, status: invalidStatus },
    });
    await assert.rejects(response, (error: unknown) => error instanceof MobileBridgeError && error.code === 'INTERNAL_ERROR');
  }

  const posted: Posted[] = [];
  const bridge = new MobileBridge({ postMessage(message) { posted.push(message); } }, undefined, 'page_bad_chunk');
  const responsePromise = createMobileRuntimeFetch(bridge)('/api/chunk');
  const open = await nextPosted(posted, 0);
  bridge.receive({
    version: MOBILE_BRIDGE_VERSION, id: open.id, pageGeneration: 'page_bad_chunk', ok: true,
    result: { requestId: 'runtime_chunk', streamId: 'stream_chunk', status: 200 },
  });
  const textPromise = (await responsePromise).text();
  const read = await nextPosted(posted, 1);
  bridge.receive({
    version: MOBILE_BRIDGE_VERSION, id: read.id, pageGeneration: 'page_bad_chunk', ok: true,
    result: { dataBase64: '', done: false },
  });
  const cancel = await nextPosted(posted, 2);
  assert.equal(cancel.method, 'runtime.cancel');
  bridge.receive({ version: MOBILE_BRIDGE_VERSION, id: cancel.id, pageGeneration: 'page_bad_chunk', ok: true, result: {} });
  await assert.rejects(textPromise, (error: unknown) => error instanceof MobileBridgeError && error.code === 'INTERNAL_ERROR');

  const oversizedPosted: Posted[] = [];
  const oversizedBridge = new MobileBridge(
    { postMessage(message) { oversizedPosted.push(message); } }, undefined, 'page_oversized_chunk',
  );
  const oversizedResponsePromise = createMobileRuntimeFetch(oversizedBridge)('/api/chunk');
  const oversizedOpen = await nextPosted(oversizedPosted, 0);
  oversizedBridge.receive({
    version: MOBILE_BRIDGE_VERSION, id: oversizedOpen.id, pageGeneration: 'page_oversized_chunk', ok: true,
    result: { requestId: 'runtime_large', streamId: 'stream_large', status: 200 },
  });
  const oversizedTextPromise = (await oversizedResponsePromise).text();
  const oversizedRead = await nextPosted(oversizedPosted, 1);
  oversizedBridge.receive({
    version: MOBILE_BRIDGE_VERSION, id: oversizedRead.id, pageGeneration: 'page_oversized_chunk', ok: true,
    result: { dataBase64: btoa('a'.repeat(65_537)), done: true },
  });
  const oversizedCancel = await nextPosted(oversizedPosted, 2);
  oversizedBridge.receive({
    version: MOBILE_BRIDGE_VERSION, id: oversizedCancel.id, pageGeneration: 'page_oversized_chunk', ok: true, result: {},
  });
  await assert.rejects(
    oversizedTextPromise,
    (error: unknown) => error instanceof MobileBridgeError && error.code === 'INTERNAL_ERROR',
  );
});
