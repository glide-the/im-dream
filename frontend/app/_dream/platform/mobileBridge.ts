// [Input] WKWebView script-message handler or Android WebMessage listener and v1 bridge envelopes.
// [Output] Generation-correlated typed calls, cancellation, stable errors, and sequenced platform events.
// [Pos] Sole browser adapter for native mobile capabilities.
// [Sync] 2026-10-25: remove native auth RPCs; the existing web BFF owns login and session state.
// [Sync] 2026-10-24: keep startup timeout in the mobile entry and remove generic timeout policy.
// [Sync] 2026-10-24: keep bridge-call abort local until a runtime request ID exists.
// [Sync] 2026-10-24: add page-generation rejection and monotonic event sequencing.

export const MOBILE_BRIDGE_VERSION = '1.0' as const;

export const mobileBridgeMethodNames = [
  'app.getInfo', 'runtime.getCapabilities', 'runtime.request', 'runtime.response.read', 'runtime.cancel',
  'lifecycle.getState',
  'file.pick', 'file.save', 'share.open', 'external.open',
] as const;
export type MobileBridgeMethod = typeof mobileBridgeMethodNames[number];

export const mobileBridgeEventNames = [
  'lifecycle.changed', 'network.changed', 'runtime.changed',
] as const;
export type MobileBridgeEvent = typeof mobileBridgeEventNames[number];

export type MobileCapabilityState = 'available' | 'starting' | 'unavailable' | 'failed';
export type MobileCapabilityName = 'python' | 'claudeRuntime' | 'localTransport' | 'files';
export const requiredApplicationCapabilityNames: readonly MobileCapabilityName[] = [
  'python', 'localTransport',
];

export type MobileCapability = Readonly<{
  state: MobileCapabilityState;
  reasonCode?: string;
}>;

export type MobileRuntimeCapabilities = Readonly<{
  revision: string;
  capabilities: Readonly<Record<MobileCapabilityName, MobileCapability>>;
}>;

export type MobileAppInfo = Readonly<{
  platform: 'ios' | 'android';
  appVersion: string;
  buildNumber: string;
  bridgeVersion: typeof MOBILE_BRIDGE_VERSION;
}>;

type BridgeRequest = Readonly<{
  version: typeof MOBILE_BRIDGE_VERSION;
  id: string;
  pageGeneration: string;
  method: MobileBridgeMethod;
  params: Readonly<Record<string, unknown>>;
}>;

type BridgeResponse = Readonly<{
  version: string;
  id: string;
  pageGeneration: string;
  ok: boolean;
  result?: unknown;
  error?: { code?: unknown; message?: unknown };
}>;

type BridgeEventEnvelope = Readonly<{
  version: string;
  pageGeneration: string;
  sequence: string;
  event: string;
  payload?: unknown;
}>;

type PendingCall = {
  resolve: (value: unknown) => void;
  reject: (error: unknown) => void;
  cleanup: () => void;
};

type IOSBridgeHandler = { postMessage(message: BridgeRequest): void };
type AndroidBridgeHandler = { postMessage(message: string): void; onmessage: ((event: { data: string }) => void) | null };

declare global {
  interface Window {
    webkit?: { messageHandlers?: { inkBridge?: IOSBridgeHandler } };
    inkBridge?: AndroidBridgeHandler;
    __INK_MOBILE_PAGE_GENERATION__?: string;
    __inkBridgeReceive?: (message: unknown) => void;
  }
}

export class MobileBridgeError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = 'MobileBridgeError';
    this.code = code;
  }
}

function requestId(): string {
  return globalThis.crypto?.randomUUID?.().replaceAll('-', '')
    ?? `${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

function pageGeneration(): string {
  const injected = window.__INK_MOBILE_PAGE_GENERATION__;
  return injected && /^[A-Za-z0-9_-]{1,96}$/.test(injected) ? injected : `page_${requestId()}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseIncoming(message: unknown): BridgeResponse | BridgeEventEnvelope | null {
  let value = message;
  if (typeof value === 'string') {
    try { value = JSON.parse(value); } catch { return null; }
  }
  if (!isRecord(value) || value.version !== MOBILE_BRIDGE_VERSION) return null;
  if (typeof value.id === 'string' && typeof value.ok === 'boolean') return value as BridgeResponse;
  if (typeof value.event === 'string') return value as BridgeEventEnvelope;
  return null;
}

export class MobileBridge {
  readonly #ios: IOSBridgeHandler | undefined;
  readonly #android: AndroidBridgeHandler | undefined;
  readonly #pending = new Map<string, PendingCall>();
  readonly #listeners = new Map<MobileBridgeEvent, Set<(payload: unknown) => void>>();
  readonly #pageGeneration: string;
  #lastEventSequence = -1n;

  constructor(ios?: IOSBridgeHandler, android?: AndroidBridgeHandler, generation = pageGeneration()) {
    if (!ios && !android) throw new MobileBridgeError('CAPABILITY_UNAVAILABLE', 'Native mobile bridge is unavailable.');
    if (!/^[A-Za-z0-9_-]{1,96}$/.test(generation)) throw new MobileBridgeError('BAD_REQUEST', 'Page generation is invalid.');
    this.#ios = ios;
    this.#android = android;
    this.#pageGeneration = generation;
    if (android) android.onmessage = (event) => this.receive(event.data);
  }

  call<T>(method: MobileBridgeMethod, params: Readonly<Record<string, unknown>> = {}, options: { signal?: AbortSignal } = {}): Promise<T> {
    if (!mobileBridgeMethodNames.includes(method)) {
      return Promise.reject(new MobileBridgeError('FORBIDDEN', 'The requested native capability is not allowlisted.'));
    }
    if (options.signal?.aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'));
    const id = requestId();
    const request: BridgeRequest = { version: MOBILE_BRIDGE_VERSION, id, pageGeneration: this.#pageGeneration, method, params };
    return new Promise<T>((resolve, reject) => {
      const onAbort = () => {
        this.#pending.delete(id);
        cleanup();
        reject(new DOMException('Aborted', 'AbortError'));
      };
      const cleanup = () => options.signal?.removeEventListener('abort', onAbort);
      this.#pending.set(id, { resolve: (value) => resolve(value as T), reject, cleanup });
      options.signal?.addEventListener('abort', onAbort, { once: true });
      try { this.#post(request); }
      catch (error) { this.#pending.delete(id); cleanup(); reject(error); }
    });
  }

  on(event: MobileBridgeEvent, listener: (payload: unknown) => void): () => void {
    if (!mobileBridgeEventNames.includes(event)) throw new MobileBridgeError('FORBIDDEN', 'The requested native event is not allowlisted.');
    const listeners = this.#listeners.get(event) ?? new Set();
    listeners.add(listener);
    this.#listeners.set(event, listeners);
    return () => listeners.delete(listener);
  }

  receive(message: unknown): void {
    const envelope = parseIncoming(message);
    if (!envelope) return;
    if (envelope.pageGeneration !== this.#pageGeneration) return;
    if ('id' in envelope) {
      const pending = this.#pending.get(envelope.id);
      if (!pending) return;
      this.#pending.delete(envelope.id);
      pending.cleanup();
      if (envelope.ok) pending.resolve(envelope.result);
      else {
        const code = typeof envelope.error?.code === 'string' ? envelope.error.code : 'INTERNAL_ERROR';
        const message = typeof envelope.error?.message === 'string' ? envelope.error.message : 'Native capability failed.';
        pending.reject(new MobileBridgeError(code, message));
      }
      return;
    }
    if (!mobileBridgeEventNames.includes(envelope.event as MobileBridgeEvent) || !/^\d+$/.test(envelope.sequence)) return;
    const sequence = BigInt(envelope.sequence);
    if (sequence <= this.#lastEventSequence) return;
    this.#lastEventSequence = sequence;
    for (const listener of this.#listeners.get(envelope.event as MobileBridgeEvent) ?? []) listener(envelope.payload);
  }

  #post(request: BridgeRequest): void {
    if (this.#ios) this.#ios.postMessage(request);
    else if (this.#android) this.#android.postMessage(JSON.stringify(request));
    else throw new MobileBridgeError('CAPABILITY_UNAVAILABLE', 'Native mobile bridge is unavailable.');
  }
}

let installedBridge: MobileBridge | null | undefined;

export function getMobileBridge(): MobileBridge | null {
  if (installedBridge !== undefined) return installedBridge;
  const ios = window.webkit?.messageHandlers?.inkBridge;
  const android = window.inkBridge;
  if (!ios && !android) {
    installedBridge = null;
    return installedBridge;
  }
  installedBridge = new MobileBridge(ios, android);
  window.__inkBridgeReceive = (message) => installedBridge?.receive(message);
  return installedBridge;
}

export function resetMobileBridgeForTests(): void {
  installedBridge = undefined;
  delete window.__inkBridgeReceive;
}
