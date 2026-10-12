// [Sync] 2026-10-12: cover usage projection, clamping, model changes and stale history rejection.
// [Input] Production HTTP transport, public metadata frames and normal history projector.
// [Output] No-text progress, actual completion, strict decoding and legacy prose compatibility.
// [Pos] Provider-free source/transport contracts; no browser or real-model claim.
// [Sync] 2026-10-12: exercise public sendMessages and AI SDK message assembly.
import { expect, test } from '@playwright/test';
import { readUIMessageStream } from 'ai';
import { ClaudeAgentChatTransport } from '../claude-agent-transport';
import { contextUsagePercentage, decodeContextCompactions, decodeContextUsage, isCompactionCompletionText, latestContextUsage } from '../context-compaction';
import { projectHistoricalAssistantTurn } from '../../components/chat/assistantTurnHistory';
import { filterClaudeThreadVisibleMessages } from '../../components/chat/threadSessionHydration';
import { applyBackendEventToMessages } from '../claude-agent-sse-utils';

test('usage uses the closed input/window snapshot, rounds, clamps and rejects malformed data', () => {
  const available = { status: 'available' as const, model: 'alias', inputTokens: 420, contextWindow: 1000 };
  expect(contextUsagePercentage(available)).toBe(42);
  expect(contextUsagePercentage({ ...available, inputTokens: 0 })).toBe(0);
  expect(contextUsagePercentage({ ...available, inputTokens: 9999 })).toBe(100);
  expect(decodeContextUsage({ ...available, inputTokens: true })).toBeUndefined();
  expect(decodeContextUsage({ ...available, contextWindow: 0 })).toBeUndefined();
  expect(decodeContextUsage({ ...available, private: 'drop' })).toEqual(available);
});

test('latest reply and selected model govern usage without falling back to stale history', () => {
  const reply = { id: 'reply', role: 'assistant' as const, parts: [], metadata: {
    contextUsage: { status: 'available' as const, model: 'alias', inputTokens: 420, contextWindow: 1000 } } };
  expect(contextUsagePercentage(latestContextUsage([reply], 'alias', false))).toBe(42);
  expect(latestContextUsage([reply], 'changed-model', false)).toBeUndefined();
  expect(latestContextUsage([reply], 'alias', true)).toBeUndefined();
  expect(latestContextUsage([reply, { id: 'failed-input', role: 'user', parts: [] }], 'alias', false)).toBeUndefined();
  expect(latestContextUsage([reply, { id: 'new', role: 'assistant', parts: [] }], 'alias', false)).toBeUndefined();
  expect(latestContextUsage([reply, { ...reply, id: 'compact', metadata: { contextUsage: { status: 'unavailable' } } }], 'alias', false)).toBeUndefined();
});

test('reconnect carries usage and explicit invalidation through the original reducer', () => {
  const available = applyBackendEventToMessages([], { type: 'message-metadata', contextUsage: {
    status: 'available', model: 'alias', inputTokens: 420, contextWindow: 1000 } });
  expect(contextUsagePercentage(latestContextUsage(available, 'alias', false))).toBe(42);
  const invalidated = applyBackendEventToMessages(available, { type: 'message-metadata', contextUsage: { status: 'unavailable' } });
  expect(latestContextUsage(invalidated, 'alias', false)).toBeUndefined();
});

test('reconnect and history preserve a state-only reply without fabricated text', () => {
  const user = { id: 'u', role: 'user' as const, parts: [{ type: 'text' as const, text: '/compact' }] };
  const first = applyBackendEventToMessages([user], { type: 'message-metadata', turnId: 't',
    contextCompactions: [{ id: 'row', state: 'running', trigger: null }] });
  const completed = applyBackendEventToMessages(first, { type: 'message-metadata', turnId: 't',
    contextCompactions: [{ id: 'row', state: 'cancelled', trigger: null }] });
  expect(completed).toHaveLength(2);
  expect(completed[1].parts).toEqual([]);
  expect(completed[1].metadata).toMatchObject({ turnId: 't', contextCompactions: [{ id: 'row', state: 'cancelled' }] });
  expect(filterClaudeThreadVisibleMessages(completed)).toHaveLength(2);
  expect(filterClaudeThreadVisibleMessages([{ id: 'bad', role: 'assistant', parts: [], metadata: {
    contextCompactions: [{ id: 'row', state: 'completed', trigger: null }] } }])).toEqual([]);
});

test('only a completed row with an actual source is accepted', () => {
  expect(decodeContextCompactions([{ id: 'bad', state: 'completed', trigger: null }])).toEqual([]);
  expect(decodeContextCompactions([{ id: '', state: 'running', trigger: null }])).toEqual([]);
  expect(decodeContextCompactions([{ id: 'a', state: 'running', trigger: null }, { id: 'a', state: 'completed', trigger: 'auto' }])).toEqual([
    { id: 'a', state: 'completed', trigger: 'auto' },
  ]);
});

test('ordinary prose and legacy history are never hidden by the word Compacted', () => {
  expect(isCompactionCompletionText('Compacted', {})).toBe(false);
  const completed = { contextCompactions: [{ id: 'a', state: 'completed', trigger: 'manual' }] };
  expect(isCompactionCompletionText('Compacted', completed)).toBe(false);
  expect(isCompactionCompletionText('Compacted', { ...completed, compactCompletionText: 'Compacted' })).toBe(true);
  expect(isCompactionCompletionText('Compacted explanation', { ...completed, compactCompletionText: 'Compacted' })).toBe(false);
});

test('status-only metadata starts the original assistant stream and completes the same row', async () => {
  const frames = [
    { type: 'message-metadata', sessionId: 'owned', turnId: 'turn' },
    { type: 'message-metadata', sessionId: 'owned', turnId: 'turn', contextCompactions: [{ id: 'row', state: 'running', trigger: null }] },
    { type: 'message-metadata', sessionId: 'owned', turnId: 'turn', contextCompactions: [{ id: 'row', state: 'unconfirmed', trigger: null }] },
    { type: 'message-metadata', sessionId: 'owned', turnId: 'turn', contextCompactions: [{ id: 'row', state: 'completed', trigger: 'auto' }] },
    { type: 'finish', finishReason: 'stop' },
  ].map((frame) => `data: ${JSON.stringify(frame)}\n\n`).join('');
  const transport = new ClaudeAgentChatTransport({ fetch: async () => new Response(frames) });
  const stream = await transport.sendMessages({ trigger: 'submit-message', chatId: 'owned', messageId: undefined,
    abortSignal: undefined, messages: [{ id: 'u', role: 'user', parts: [{ type: 'text', text: 'Hello' }] }] });
  const messages = [];
  for await (const message of readUIMessageStream({ stream })) messages.push(structuredClone(message));
  expect(messages.some((message) => (message.metadata as { contextCompactions?: { state: string }[] })?.contextCompactions?.[0]?.state === 'running')).toBe(true);
  expect(messages.at(-1)?.parts).toEqual([{ type: 'step-start' }]);
  expect(messages.at(-1)?.metadata).toMatchObject({ contextCompactions: [{ id: 'row', state: 'completed', trigger: 'auto' }] });
});

test('final-first history keeps its original completion protocol with compaction metadata', () => {
  const message = { id: 'reply', role: 'assistant' as const, parts: [{ type: 'text' as const, text: 'Continue normally' }], metadata: {
    turnId: 'turn', turnStatus: 'completed' as const, finalPartIndex: 0, historyProjectionVersion: 1 as const,
    historyProcessAvailable: false, contextCompactions: [{ id: 'row', state: 'completed', trigger: 'auto' }],
  } };
  expect(projectHistoricalAssistantTurn(message)).toMatchObject({ finalPartIndex: 0, processAvailable: false });
  expect(message.parts[0].text).toBe('Continue normally');
});
