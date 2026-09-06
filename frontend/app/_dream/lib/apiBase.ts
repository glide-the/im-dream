// [Input] Browser runtime config, optional Next public fallback config, and current window origin.
// [Output] Centralized REST/SSE/WebSocket endpoint base URLs for frontend API callers.
// [Pos] frontend API base-url utility node
// [Sync] 2026-06-12: add runtime API_BASE_URL / WS_BASE_URL support for cross-origin deployments.
// [Sync] 2026-06-12: resolve API_BASE lazily so runtime-config load timing cannot lock the app to same-origin paths.
// [Sync] 2026-06-15: remove /ink-and-memory same-origin fallback prefix; root deploy uses /api directly.
// [Sync] 2026-09-05: replace Vite-only import.meta fallbacks while keeping startup runtime config authoritative.
// [Sync] 2026-09-05: guard Next public fallbacks so provider-free browser harnesses do not require a process global.

type RuntimeConfig = {
  apiBaseUrl?: string;
  wsBaseUrl?: string;
};

declare global {
  interface Window {
    __INK_RUNTIME_CONFIG__?: RuntimeConfig;
  }
}

const DEFAULT_API_BASE = '';

function nextPublicApiBase(): string | undefined {
  return typeof process === 'undefined' ? undefined : process.env.NEXT_PUBLIC_API_BASE_URL;
}

function nextPublicWebSocketBase(): string | undefined {
  return typeof process === 'undefined' ? undefined : process.env.NEXT_PUBLIC_WS_BASE_URL;
}

function cleanBaseUrl(value: string | undefined | null): string | undefined {
  const trimmed = value?.trim();
  if (!trimmed) return undefined;
  return trimmed.replace(/\/+$/, '');
}

function getRuntimeConfig(): RuntimeConfig {
  if (typeof window === 'undefined') return {};
  return window.__INK_RUNTIME_CONFIG__ ?? {};
}

export function getApiBase(): string {
  return cleanBaseUrl(
    getRuntimeConfig().apiBaseUrl || nextPublicApiBase(),
  ) ?? DEFAULT_API_BASE;
}

export const API_BASE = {
  toString: getApiBase,
  valueOf: getApiBase,
  [Symbol.toPrimitive]: getApiBase,
} as unknown as string;

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${getApiBase()}${normalizedPath}`;
}

function websocketProtocolFor(protocol: string): string {
  return protocol === 'https:' ? 'wss:' : 'ws:';
}

function deriveWebSocketBase(): string {
  const explicit = cleanBaseUrl(
    getRuntimeConfig().wsBaseUrl || nextPublicWebSocketBase(),
  );
  if (explicit) return explicit;

  if (typeof window === 'undefined') return '';

  try {
    const api = new URL(getApiBase(), window.location.origin);
    api.protocol = websocketProtocolFor(api.protocol);
    return `${api.protocol}//${api.host}`;
  } catch {
    const protocol = websocketProtocolFor(window.location.protocol);
    return `${protocol}//${window.location.host}`;
  }
}

export function webSocketUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${deriveWebSocketBase()}${normalizedPath}`;
}
