// [Input] Browser runtime API/WS configuration and a deterministic frontend origin.
// [Output] Regression proof that runtime config remains authoritative for REST, SSE, and voice WebSocket URLs.
// [Pos] task_411-01 browser-boundary contract test for the root Next compatibility shell.
// [Sync] 2026-09-05: cover the Vite-env exit without changing runtime-config or same-origin fallback semantics.

import { expect, test } from '@playwright/test';

import { apiUrl, webSocketUrl } from '../apiBase';

test('runtime config stays authoritative for REST and voice WebSocket URLs', () => {
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
    expect(apiUrl('/api/claude-agent')).toBe('https://api.example.test/api/claude-agent');
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
