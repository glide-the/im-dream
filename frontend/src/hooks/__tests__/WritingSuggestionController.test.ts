// [Input] Manual WritingSuggestionController with injected Thread, persistence, and SSE transports.
// [Output] Verify explicit-only requests, Thread reuse/isolation, snapshot binding, retry, failure, and late-response rejection.
// [Pos] Writing suggestion side-effect orchestration regression test in frontend/src/hooks/__tests__.
// [Sync] 2026-09-01: add deterministic manual Session/Thread lifecycle coverage.

import { expect, test } from '@playwright/test';
import type { streamClaudeAgentTurn } from '../../api/voiceApi';
import { EditorEngine, type EditorState } from '../../engine/EditorEngine';
import {
  WritingSuggestionController,
  type WritingSuggestionControllerDependencies,
} from '../useWritingSuggestions';

type StreamOptions = Parameters<typeof streamClaudeAgentTurn>[0];

async function flushAsyncWork() {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await Promise.resolve();
}

function firstText(engine: EditorEngine) {
  const cell = engine.getState().cells.find((candidate) => candidate.type === 'text');
  if (!cell || cell.type !== 'text') throw new Error('Missing TextCell');
  return cell;
}

function makeController(options: {
  engine: EditorEngine;
  createThread?: () => Promise<string | null>;
  persistSession?: (state: EditorState) => Promise<unknown>;
  streamTurn?: (options: StreamOptions) => Promise<void>;
}) {
  const dependencies: WritingSuggestionControllerDependencies = {
    getEngine: () => options.engine,
    createThread: options.createThread ?? (async () => 'thread-a'),
    persistSession: options.persistSession ?? (async () => undefined),
    streamTurn: (options.streamTurn ?? (async (request) => {
      request.onDelta('建议');
      request.onComplete('建议');
    })) as typeof streamClaudeAgentTurn,
    buildPrompt: (textSnapshot) => ({
      message: `snapshot:${textSnapshot}`,
      systemPrompt: 'Writing product prompt',
    }),
  };
  return new WritingSuggestionController(dependencies);
}

test('ordinary input is request-free and one Go deeper click sends exactly one request', async () => {
  const engine = new EditorEngine('session-a');
  const text = firstText(engine);
  let streamCalls = 0;
  const controller = makeController({
    engine,
    streamTurn: async (request) => {
      streamCalls += 1;
      request.onComplete('建议');
    },
  });

  engine.updateTextCell(text.id, '普通输入\n只负责换行。');
  await new Promise((resolve) => setTimeout(resolve, 2100));
  expect(streamCalls).toBe(0);

  const suggestionId = controller.start(text.id);
  expect(suggestionId).toBeTruthy();
  expect(engine.getWritingSuggestionCell(suggestionId as string)?.status).toBe('streaming');
  expect(controller.start(text.id)).toBeNull();
  await flushAsyncWork();
  expect(streamCalls).toBe(1);
});

test('SSE deltas stay ordered in the immediately inserted Cell and finish completes it', async () => {
  const engine = new EditorEngine('session-a');
  const text = firstText(engine);
  engine.updateTextCell(text.id, '正文');
  const controller = makeController({
    engine,
    streamTurn: async (request) => {
      request.onDelta('第一段');
      request.onDelta('，第二段');
      request.onComplete('第一段，第二段');
    },
  });

  const suggestionId = controller.start(text.id) as string;
  expect(engine.getWritingSuggestionCell(suggestionId)?.status).toBe('streaming');
  await flushAsyncWork();
  expect(engine.getWritingSuggestionCell(suggestionId)).toMatchObject({
    content: '第一段，第二段',
    status: 'completed',
  });
});

test('one Session rejects a second suggestion submit while its current turn is streaming', async () => {
  const engine = new EditorEngine('session-a');
  const first = firstText(engine);
  engine.updateTextCell(first.id, '第一段正文');
  let releaseStream: (() => void) | undefined;
  const controller = makeController({
    engine,
    streamTurn: () => new Promise<void>((resolve) => { releaseStream = resolve; }),
  });

  expect(controller.start(first.id)).toBeTruthy();
  await flushAsyncWork();
  const continuation = [...engine.getState().cells].reverse().find((cell) => cell.type === 'text');
  if (!continuation || continuation.type !== 'text') throw new Error('Missing continuation');
  engine.updateTextCell(continuation.id, '生成期间继续写作');

  expect(controller.start(continuation.id)).toBeNull();
  expect(engine.getState().cells.filter((cell) => cell.type === 'writing-suggestion')).toHaveLength(1);
  releaseStream?.();
  await flushAsyncWork();
});

test('multiple suggestions in one Session share one Thread', async () => {
  const engine = new EditorEngine('session-a');
  const first = firstText(engine);
  engine.updateTextCell(first.id, '第一段正文');
  let createCalls = 0;
  const threads: string[] = [];
  const controller = makeController({
    engine,
    createThread: async () => { createCalls += 1; return 'thread-a'; },
    streamTurn: async (request) => {
      threads.push(request.threadId);
      request.onDelta('建议');
      request.onComplete('建议');
    },
  });

  controller.start(first.id);
  await flushAsyncWork();
  const continuation = [...engine.getState().cells].reverse().find((cell) => cell.type === 'text');
  if (!continuation || continuation.type !== 'text') throw new Error('Missing continuation');
  engine.updateTextCell(continuation.id, '第二段正文');
  controller.start(continuation.id);
  await flushAsyncWork();

  expect(createCalls).toBe(1);
  expect(threads).toEqual(['thread-a', 'thread-a']);
  expect(engine.getState().cells.filter((cell) => cell.type === 'writing-suggestion')).toHaveLength(2);
});

test('a new Writing Session creates a different Thread', async () => {
  const engine = new EditorEngine('session-a');
  let sequence = 0;
  const controller = makeController({
    engine,
    createThread: async () => `thread-${++sequence}`,
  });
  const first = firstText(engine);
  engine.updateTextCell(first.id, 'Session A');
  controller.start(first.id);
  await flushAsyncWork();
  expect(engine.getState().writingThreadId).toBe('thread-1');

  engine.loadState({
    id: 'session-b',
    cells: [{ id: 'text-b', type: 'text', content: 'Session B' }],
    commentors: [], tasks: [], weightPath: [], overlappedPhrases: [], notFoundPhrases: [],
  });
  controller.cancelRequestsOutsideSession('session-b');
  controller.start('text-b');
  await flushAsyncWork();
  expect(engine.getState().writingThreadId).toBe('thread-2');
});

test('a restored Session Thread is reused without creating another Thread', async () => {
  const engine = new EditorEngine('session-a');
  engine.setWritingThreadId('session-a', 'thread-restored');
  const text = firstText(engine);
  engine.updateTextCell(text.id, '恢复后的正文');
  let createCalls = 0;
  let usedThread = '';
  const controller = makeController({
    engine,
    createThread: async () => { createCalls += 1; return 'unexpected'; },
    streamTurn: async (request) => {
      usedThread = request.threadId;
      request.onComplete('建议');
    },
  });

  controller.start(text.id);
  await flushAsyncWork();
  expect(createCalls).toBe(0);
  expect(usedThread).toBe('thread-restored');
});

test('editing continuation prose during generation does not change the bound snapshot or Cell', async () => {
  const engine = new EditorEngine('session-a');
  const text = firstText(engine);
  engine.updateTextCell(text.id, '点击时正文');
  const captured: { stream?: StreamOptions; release?: () => void } = {};
  const controller = makeController({
    engine,
    streamTurn: (request) => {
      captured.stream = request;
      return new Promise<void>((resolve) => { captured.release = resolve; });
    },
  });

  const suggestionId = controller.start(text.id) as string;
  await flushAsyncWork();
  const continuation = [...engine.getState().cells].reverse().find((cell) => cell.type === 'text');
  if (!continuation || continuation.type !== 'text') throw new Error('Missing continuation');
  engine.updateTextCell(continuation.id, '生成期间的新正文');
  expect(captured.stream?.message).toContain('snapshot:点击时正文');
  captured.stream?.onDelta('绑定建议');
  captured.stream?.onComplete('绑定建议');
  captured.release?.();
  await flushAsyncWork();

  expect(engine.getWritingSuggestionCell(suggestionId)?.content).toBe('绑定建议');
  expect(continuation.content).toBe('生成期间的新正文');
});

test('late callbacks cannot overwrite a retried request and retry keeps the same Thread and Cell', async () => {
  const engine = new EditorEngine('session-a');
  const text = firstText(engine);
  engine.updateTextCell(text.id, '正文');
  let createCalls = 0;
  const streams: StreamOptions[] = [];
  const releases: Array<() => void> = [];
  const controller = makeController({
    engine,
    createThread: async () => { createCalls += 1; return 'thread-a'; },
    streamTurn: (request) => {
      streams.push(request);
      return new Promise<void>((resolve) => { releases.push(resolve); });
    },
  });

  const suggestionId = controller.start(text.id) as string;
  await flushAsyncWork();
  streams[0].onError(new Error('interrupted'));
  expect(engine.getWritingSuggestionCell(suggestionId)?.status).toBe('failed');
  expect(controller.retry(suggestionId)).toBe(true);
  await flushAsyncWork();

  streams[0].onDelta('过期');
  streams[0].onComplete('过期');
  streams[1].onDelta('新建议');
  streams[1].onComplete('新建议');
  releases.forEach((release) => release());
  await flushAsyncWork();

  expect(createCalls).toBe(1);
  expect(engine.getWritingSuggestionCell(suggestionId)).toMatchObject({
    id: suggestionId,
    content: '新建议',
    status: 'completed',
  });
});

test('Thread association persistence failure fails closed before SSE', async () => {
  const engine = new EditorEngine('session-a');
  const text = firstText(engine);
  engine.updateTextCell(text.id, '正文');
  let streamCalls = 0;
  const controller = makeController({
    engine,
    persistSession: async () => { throw new Error('database unavailable'); },
    streamTurn: async () => { streamCalls += 1; },
  });

  const suggestionId = controller.start(text.id) as string;
  await flushAsyncWork();
  expect(streamCalls).toBe(0);
  expect(engine.getWritingSuggestionCell(suggestionId)).toMatchObject({
    status: 'failed',
    error: { code: 'WRITING_THREAD_PERSIST_FAILED', retryable: true },
  });
});
