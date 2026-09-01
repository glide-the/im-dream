// [Input] Product-neutral Claude Agent SSE requests, mocked protocol frames, and historical Voice chat compatibility.
// [Output] Verify shared-parser streaming, structured errors, missing-finish recovery, and absence of random-Voice Writing transport.
// [Pos] Writing Claude Agent browser transport regression test in frontend/src/api/__tests__.
// [Sync] 2026-09-01: replace random Voice inspiration tests with product-level manual Writing SSE contracts.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source only; browser app omits Node types.
import { readFileSync } from 'node:fs';
import { chatWithVoice, streamClaudeAgentTurn, type VoiceConfig } from '../voiceApi';
import { createChatThread } from '../chatHistoryApi';
import { readClaudeAgentErrorCode } from '../../lib/claude-agent-transport';

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

const voice: VoiceConfig = {
  name: '历史评论 Voice',
  systemPrompt: '只用于历史评论对话。',
  enabled: true,
  icon: 'brain',
  color: 'blue',
  thread_id: 'thread-comment',
};

function sseResponse(frames: Array<Record<string, unknown>>): Response {
  const body = frames.map((frame) => `data: ${JSON.stringify(frame)}\r\n\r\n`).join('');
  return new Response(body, {
    status: 200,
    headers: { 'content-type': 'text/event-stream; charset=utf-8' },
  });
}

test.describe.configure({ mode: 'serial' });

test.beforeEach(() => {
  Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true });
  Object.defineProperty(globalThis, 'window', {
    value: { __INK_RUNTIME_CONFIG__: { apiBaseUrl: 'https://dream.test' } },
    configurable: true,
  });
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('Writing creates an unbound product Thread with only its localized title', async () => {
  let payload: Record<string, unknown> = {};
  globalThis.fetch = (async (_input, init) => {
    payload = JSON.parse(String(init?.body)) as Record<string, unknown>;
    return new Response(JSON.stringify({ thread_id: 'thread-writing' }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  }) as typeof fetch;

  await expect(createChatThread(undefined, undefined, 'Writing suggestions')).resolves.toBe(
    'thread-writing',
  );
  expect(payload).toEqual({ title: 'Writing suggestions' });
});

test('manual Writing turn streams ordered deltas on the supplied Session Thread', async () => {
  const calls: Array<{ input: string; init?: RequestInit }> = [];
  const deltas: string[] = [];
  let completed = '';
  globalThis.fetch = (async (input, init) => {
    calls.push({ input: String(input), init });
    return sseResponse([
      { type: 'text-start', id: 'writing-text' },
      { type: 'text-delta', id: 'writing-text', delta: '先写' },
      { type: 'text-delta', id: 'writing-text', delta: '雨声' },
      { type: 'text-end', id: 'writing-text' },
      { type: 'finish', finishReason: 'stop' },
    ]);
  }) as typeof fetch;

  await streamClaudeAgentTurn({
    threadId: 'thread-writing',
    message: 'snapshot:正文',
    systemPrompt: 'Ink & Memory Writing Suggestions',
    onDelta: (delta) => deltas.push(delta),
    onComplete: (text) => { completed = text; },
    onError: (error) => { throw error; },
  });

  expect(calls).toHaveLength(1);
  expect(calls[0].input).toBe('https://dream.test/api/claude-agent');
  expect(deltas).toEqual(['先写', '雨声']);
  expect(completed).toBe('先写雨声');
  const payload = JSON.parse(String(calls[0].init?.body)) as Record<string, unknown>;
  expect(payload.id).toBe('thread-writing');
  expect(payload.resume).toBe(true);
  expect(payload).not.toHaveProperty('deckId');
  expect(payload).not.toHaveProperty('voiceId');
});

test('structured Claude SSE errors keep their code and retryability', async () => {
  globalThis.fetch = (async () => sseResponse([
    {
      type: 'error',
      errorText: '当前模型不可用',
      errorCode: 'MODEL_NOT_AVAILABLE',
      retryable: false,
    },
  ])) as typeof fetch;
  let captured: Error | null = null;

  await streamClaudeAgentTurn({
    threadId: 'thread-writing',
    message: 'snapshot:正文',
    systemPrompt: 'Writing',
    onDelta: () => undefined,
    onComplete: () => undefined,
    onError: (error) => { captured = error; },
  });

  expect(readClaudeAgentErrorCode(captured)).toBe('MODEL_NOT_AVAILABLE');
  expect((captured as unknown as { retryable: boolean }).retryable).toBe(false);
});

test('a stream that ends without finish is a recoverable interruption, not completion', async () => {
  globalThis.fetch = (async () => sseResponse([
    { type: 'text-delta', id: 'writing-text', delta: 'partial' },
  ])) as typeof fetch;
  let completed = false;
  let errorMessage = '';

  await streamClaudeAgentTurn({
    threadId: 'thread-writing',
    message: 'snapshot:正文',
    systemPrompt: 'Writing',
    onDelta: () => undefined,
    onComplete: () => { completed = true; },
    onError: (error) => { errorMessage = error.message; },
  });

  expect(completed).toBe(false);
  expect(errorMessage).toContain('before finish');
});

test('historical comment chat still reuses its explicit Voice Thread', async () => {
  globalThis.fetch = (async () => sseResponse([
    { type: 'text-delta', id: 'comment', delta: '继续具体一点。' },
    { type: 'finish', finishReason: 'stop' },
  ])) as typeof fetch;

  const result = await chatWithVoice(
    'voice-comment',
    voice,
    [{ role: 'assistant', content: '你观察到了什么？' }],
    '我注意到了变化。',
    '原文。',
  );

  expect(result).toEqual({ response: '继续具体一点。', thread_id: 'thread-comment' });
});

test('voiceApi no longer owns random-Voice Writing suggestion selection or a second SSE parser', () => {
  const source = readFileSync(new URL('../voiceApi.ts', import.meta.url), 'utf8');
  expect(source).not.toContain('function getSuggestion');
  expect(source).not.toContain('Math.floor(Math.random() * enabledVoices.length)');
  expect(source).toContain('consumeClaudeAgentSseStream(reader');
  expect(source).not.toContain('buffer.split(/\\n\\n+/)');
});
