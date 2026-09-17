// [Input] Browser runtime API/WS configuration and a deterministic frontend origin.
// [Output] Regression proof that REST/SSE stays on Next origin while explicit disabled-ASR WS selection is retained.
// [Pos] task_411-01 browser-boundary contract test for the root Next compatibility shell.
// [Sync] 2026-09-05: cover the Vite-env exit without changing runtime-config or same-origin fallback semantics.
// [Sync] 2026-09-14: cross-origin runtime API configuration cannot bypass BFF credentials.

import { expect, test } from '@playwright/test';

import { apiUrl, webSocketUrl } from '../apiBase';

test('REST stays same-origin and explicit voice WebSocket selection is retained', () => {
  const previousWindow = globalThis.window;
  Object.defineProperty(globalThis, 'window', {
    configurable: true,
    value: {
      __INK_RUNTIME_CONFIG__: {
        apiBaseUrl: 'https://api.example.test/',
        wsBaseUrl: 'wss://voice.example.test/',
      },
      location: new URL('https://web.example.test/story-workspace/chat'),
    },
  });

  try {
    expect(apiUrl('/api/claude-agent')).toBe('/api/claude-agent');
    expect(webSocketUrl('/ws/speech-recognition')).toBe('wss://voice.example.test/ws/speech-recognition');
  } finally {
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: previousWindow,
    });
  }
});

test('same-origin fallback derives the secure voice WebSocket origin', () => {
  const previousWindow = globalThis.window;
  Object.defineProperty(globalThis, 'window', {
    configurable: true,
    value: {
      __INK_RUNTIME_CONFIG__: {},
      location: new URL('https://web.example.test/story-workspace/chat'),
    },
  });

  try {
    expect(apiUrl('/api/me')).toBe('/api/me');
    expect(webSocketUrl('/ws/speech-recognition')).toBe('wss://web.example.test/ws/speech-recognition');
  } finally {
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: previousWindow,
    });
  }
});
