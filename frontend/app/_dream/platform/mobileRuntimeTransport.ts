// [Input] Relative Dream requests and a qualified versioned native mobile bridge.
// [Output] Fetch-compatible responses whose bodies pull bounded chunks from the in-process runtime.
// [Pos] Mobile DreamTransport adapter; the mobile entry owns its scoped installation and cleanup.
// [Sync] 2026-10-24: validate response heads/chunks, cancel pre-head requests by client ID, and close failed streams.
// [Sync] 2026-10-24: route existing relative Dream API calls only after all runtime capabilities qualify.
// [Sync] 2026-10-24: implement request-head, pull-stream, cancellation, and sensitive-header gates.

import { MobileBridge, MobileBridgeError } from './mobileBridge.ts';
import bridgeContract from '../../../shared/bridge/contract.json' with { type: 'json' };

type RuntimeResponseHead = Readonly<{
  requestId: string;
  streamId: string;
  status: number;
  headers?: Readonly<Record<string, string>>;
}>;

type RuntimeReadResult = Readonly<{
  dataBase64?: string;
  done: boolean;
}>;

const maximumResponseChunkBytes = 65_536;

const transportPolicy = bridgeContract.transportPolicy;
const forbiddenHeaders = new Set(transportPolicy.forbiddenHeaderNames);
const allowedMethods = new Set(transportPolicy.allowedMethods);

function allowedPath(input: RequestInfo | URL): string {
  if (typeof input !== 'string') {
    throw new MobileBridgeError('BAD_REQUEST', 'Mobile runtime requests require a relative string path.');
  }
  if (!input.startsWith('/') || input.startsWith('//') || input.includes('#') || /%(?:2e|2f|5c)/i.test(input)) {
    throw new MobileBridgeError('FORBIDDEN', 'Mobile runtime requests are limited to local Dream paths.');
  }
  const parsed = new URL(input, 'https://ink-mobile-runtime.invalid');
  if (!(parsed.pathname.startsWith('/api/') || parsed.pathname.startsWith('/auth/'))) {
    throw new MobileBridgeError('FORBIDDEN', 'Mobile runtime requests are limited to local Dream paths.');
  }
  return `${parsed.pathname}${parsed.search}`;
}

function allowedHeaders(input: HeadersInit | undefined): Record<string, string> {
  const result: Record<string, string> = {};
  const headers = new Headers(input);
  for (const [name, value] of headers.entries()) {
    const normalized = name.toLowerCase();
    if (forbiddenHeaders.has(normalized)
        || transportPolicy.forbiddenHeaderPrefixes.some((prefix) => normalized.startsWith(prefix))) {
      throw new MobileBridgeError('FORBIDDEN', `Header ${name} is owned by the native runtime.`);
    }
    result[name] = value;
  }
  return result;
}

function encodeBytes(bytes: Uint8Array): string {
  if (bytes.byteLength > transportPolicy.maximumInlineRequestBytes) {
    throw new MobileBridgeError('BAD_REQUEST', 'The inline request body exceeds the mobile transport policy.');
  }
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary);
}

function decodeBytes(value: string): Uint8Array {
  const binary = atob(value);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

function newClientRequestId(): string {
  return globalThis.crypto?.randomUUID?.().replaceAll('-', '')
    ?? `${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

async function encodeBody(body: BodyInit | null | undefined): Promise<string | null> {
  if (body == null) return null;
  if (typeof body === 'string') return encodeBytes(new TextEncoder().encode(body));
  if (body instanceof URLSearchParams) return encodeBytes(new TextEncoder().encode(body.toString()));
  if (body instanceof ArrayBuffer) return encodeBytes(new Uint8Array(body));
  if (ArrayBuffer.isView(body)) return encodeBytes(new Uint8Array(body.buffer, body.byteOffset, body.byteLength));
  if (body instanceof Blob) return encodeBytes(new Uint8Array(await body.arrayBuffer()));
  throw new MobileBridgeError('CAPABILITY_UNAVAILABLE', 'This request body type has no qualified mobile transport adapter.');
}

function validHead(value: RuntimeResponseHead): void {
  if (!value || typeof value.requestId !== 'string' || typeof value.streamId !== 'string'
      || !Number.isInteger(value.status) || value.status < 200 || value.status > 599) {
    throw new MobileBridgeError('INTERNAL_ERROR', 'The local runtime returned an invalid response head.');
  }
}

function validChunk(value: RuntimeReadResult): Uint8Array | undefined {
  if (!value || typeof value.done !== 'boolean'
      || (value.dataBase64 !== undefined && typeof value.dataBase64 !== 'string')) {
    throw new MobileBridgeError('INTERNAL_ERROR', 'The local runtime returned an invalid response chunk.');
  }
  if (value.done === false && !value.dataBase64) {
    throw new MobileBridgeError('INTERNAL_ERROR', 'The local runtime returned an empty non-terminal response chunk.');
  }
  if (!value.dataBase64) return undefined;
  let decoded: Uint8Array;
  try {
    decoded = decodeBytes(value.dataBase64);
  } catch {
    throw new MobileBridgeError('INTERNAL_ERROR', 'The local runtime returned invalid base64 response data.');
  }
  if (decoded.byteLength > maximumResponseChunkBytes) {
    throw new MobileBridgeError('INTERNAL_ERROR', 'The local runtime exceeded the response chunk limit.');
  }
  return decoded;
}

export function createMobileRuntimeFetch(bridge: MobileBridge): typeof fetch {
  return async (input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> => {
    const path = allowedPath(input);
    const method = (init.method ?? 'GET').toUpperCase();
    if (!allowedMethods.has(method)) {
      throw new MobileBridgeError('FORBIDDEN', 'The HTTP method is outside the mobile transport policy.');
    }
    const headers = allowedHeaders(init.headers);
    const bodyBase64 = await encodeBody(init.body);
    const clientRequestId = newClientRequestId();
    let head: RuntimeResponseHead;
    try {
      head = await bridge.call<RuntimeResponseHead>('runtime.request', {
        clientRequestId, path, method, headers, bodyBase64,
      }, { signal: init.signal ?? undefined });
      validHead(head);
    } catch (error) {
      void bridge.call('runtime.cancel', { requestId: clientRequestId }).catch(() => undefined);
      throw error;
    }

    let closed = false;
    let onAbort: (() => void) | undefined;
    const cancelRuntime = async () => {
      if (closed) return;
      closed = true;
      if (onAbort) init.signal?.removeEventListener('abort', onAbort);
      await bridge.call('runtime.cancel', { requestId: head.requestId, streamId: head.streamId }).catch(() => undefined);
    };
    onAbort = () => { void cancelRuntime(); };
    if (init.signal?.aborted) {
      await cancelRuntime();
      throw new DOMException('Aborted', 'AbortError');
    }
    init.signal?.addEventListener('abort', onAbort, { once: true });

    const bodyless = method === 'HEAD' || head.status === 204 || head.status === 205 || head.status === 304;
    const body = bodyless ? null : new ReadableStream<Uint8Array>({
          async pull(controller) {
            try {
              const chunk = await bridge.call<RuntimeReadResult>('runtime.response.read', {
                requestId: head.requestId,
                streamId: head.streamId,
                maximumBytes: maximumResponseChunkBytes,
              }, { signal: init.signal ?? undefined });
              const decoded = validChunk(chunk);
              if (decoded) controller.enqueue(decoded);
              if (chunk.done) {
                closed = true;
                if (onAbort) init.signal?.removeEventListener('abort', onAbort);
                controller.close();
              }
            } catch (error) {
              await cancelRuntime();
              controller.error(error);
            }
          },
          async cancel() {
            if (onAbort) init.signal?.removeEventListener('abort', onAbort);
            await cancelRuntime();
          },
        });

    if (bodyless) await cancelRuntime();
    return new Response(body, { status: head.status, headers: head.headers });
  };
}

export function installMobileRuntimeFetch(bridge: MobileBridge): () => void {
  const previousFetch = globalThis.fetch;
  const nativeRuntimeFetch = createMobileRuntimeFetch(bridge);
  const routedFetch: typeof fetch = (input, init) => {
    if (typeof input === 'string' && (input.startsWith('/api/') || input.startsWith('/auth/'))) {
      return nativeRuntimeFetch(input, init);
    }
    return previousFetch(input, init);
  };
  globalThis.fetch = routedFetch;
  return () => {
    if (globalThis.fetch === routedFetch) globalThis.fetch = previousFetch;
  };
}
