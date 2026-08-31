// [Input] Enabled Voice configs and mocked Claude Agent SSE responses.
// [Output] Verify Writing inspiration and historical comment chat use Voice Thread SSE and preserve safe errors.
// [Pos] Writing Voice Thread browser transport regression test in frontend/src/api/__tests__
// [Sync] 2026-08-31: lock removal of the get_writing_suggestion PolyCLI transport.

import { expect, test } from '@playwright/test';
import { chatWithVoice, getSuggestion, type VoiceConfig } from '../voiceApi';

const originalFetch = globalThis.fetch;
const storageValues = new Map<string, string>([['auth_token', 'writing-token']]);
const storage: Storage = {
  get length() { return storageValues.size; },
  clear() { storageValues.clear(); },
  getItem(key) { return storageValues.get(key) ?? null; },
  key(index) { return [...storageValues.keys()][index] ?? null; },
  removeItem(key) { storageValues.delete(key); },
  setItem(key, value) { storageValues.set(key, value); },
};

const voices: Record<string, VoiceConfig> = {
  'voice-market': {
    name: '市场研究员专家',
    systemPrompt: '从市场研究角度提供简洁而具体的启发。',
    enabled: true,
    icon: 'brain',
    color: 'blue',
    thread_id: 'thread-market',
  },
};

function sseResponse(frames: Array<Record<string, unknown>>): Response {
  const body = frames.map((frame) => `data: ${JSON.stringify(frame)}\n\n`).join('');
  return new Response(body, {
    status: 200,
    headers: { 'content-type': 'text/event-stream; charset=utf-8' },
  });
}

test.describe.configure({ mode: 'serial' });

test.beforeEach(() => {
  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true,
  });
  Object.defineProperty(globalThis, 'window', {
    value: { __INK_RUNTIME_CONFIG__: { apiBaseUrl: 'https://dream.test' } },
    configurable: true,
  });
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('Writing inspiration posts to the existing Voice Thread and never calls PolyCLI', async () => {
  const calls: Array<{ input: string; init?: RequestInit }> = [];
  const partials: string[] = [];
  globalThis.fetch = (async (input, init) => {
    calls.push({ input: String(input), init });
    return sseResponse([
      { type: 'text-delta', delta: '也许继续' },
      { type: 'text-delta', delta: '写写这个发现' },
      { type: 'finish' },
    ]);
  }) as typeof fetch;

  const suggestion = await getSuggestion(
    '今天我重新观察了这个市场。',
    voices,
    '保持诚实、务实。',
    '用户现在很平静。',
    undefined,
    (partial) => partials.push(partial.inspiration),
  );

  expect(suggestion).toMatchObject({
    inspiration: '也许继续写写这个发现',
    voice: '市场研究员专家',
    voice_key: 'voice-market',
    thread_id: 'thread-market',
  });
  expect(calls).toHaveLength(1);
  expect(calls[0]?.input).toBe('https://dream.test/api/claude-agent');
  expect(calls[0]?.input).not.toContain('/polycli/');
  expect(partials).toEqual(['也许继续', '也许继续写写这个发现']);

  const payload = JSON.parse(String(calls[0]?.init?.body)) as {
    id: string;
    resume: boolean;
    systemPrompt: string;
    message: { parts: Array<{ text: string }> };
  };
  expect(payload.id).toBe('thread-market');
  expect(payload.resume).toBe(true);
  expect(payload.systemPrompt).toContain('市场研究员专家');
  expect(payload.systemPrompt).toContain('用户现在很平静。');
  expect(payload.message.parts[0]?.text).toContain('今天我重新观察了这个市场。');
});

test('Writing inspiration preserves a structured Claude SSE error code', async () => {
  globalThis.fetch = (async () => sseResponse([
    { type: 'error', errorText: '[MODEL_NOT_AVAILABLE] 当前模型不可用' },
  ])) as typeof fetch;

  await expect(getSuggestion('这是一段足够长的写作内容。', voices)).rejects.toThrow(
    '[MODEL_NOT_AVAILABLE] 当前模型不可用',
  );
});

test('explicit historical comment chat also reuses the Voice Claude Thread', async () => {
  const calls: string[] = [];
  globalThis.fetch = (async (input) => {
    calls.push(String(input));
    return sseResponse([
      { type: 'text-delta', delta: '继续具体一点。' },
      { type: 'finish' },
    ]);
  }) as typeof fetch;

  const result = await chatWithVoice(
    'voice-market',
    voices['voice-market'],
    [{ role: 'assistant', content: '你观察到了什么？' }],
    '我注意到了价格变化。',
    '市场开始重新定价。',
  );

  expect(result).toEqual({
    response: '继续具体一点。',
    thread_id: 'thread-market',
  });
  expect(calls).toEqual(['https://dream.test/api/claude-agent']);
});
