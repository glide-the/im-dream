// [Input] EditorEngine WritingSuggestionCell commands, Session Thread identity, and persisted EditorState snapshots.
// [Output] Verify Cell sequencing, incremental updates, retry recovery, stale isolation, reload recovery, and prose-metric exclusion.
// [Pos] Persistent Writing suggestion engine regression test in frontend/src/engine/__tests__.
// [Sync] 2026-09-01: add deterministic coverage for the manual suggestion Cell state machine.

import { expect, test } from '@playwright/test';
import { computeWeight, EditorEngine, type EditorState } from '../EditorEngine';

function firstTextCell(engine: EditorEngine) {
  const cell = engine.getState().cells.find((candidate) => candidate.type === 'text');
  if (!cell || cell.type !== 'text') throw new Error('Missing TextCell');
  return cell;
}

test('manual insertion creates a streaming suggestion Cell followed by a writable TextCell', () => {
  const engine = new EditorEngine('session-a');
  const text = firstTextCell(engine);
  engine.updateTextCell(text.id, '我开始留意雨声。');

  const suggestion = engine.insertWritingSuggestionAfterTextCell(text.id, text.content, 'request-a');

  expect(suggestion).toMatchObject({
    type: 'writing-suggestion',
    status: 'streaming',
    content: '',
    requestId: 'request-a',
    anchor: { textCellId: text.id, textSnapshot: '我开始留意雨声。' },
  });
  const cells = engine.getState().cells;
  expect(cells.map((cell) => cell.type)).toEqual(['text', 'writing-suggestion', 'text']);
  expect(engine.insertWritingSuggestionAfterTextCell(text.id, text.content, 'duplicate')).toBeNull();
});

test('ordered deltas and finish update only the bound suggestion Cell', () => {
  const engine = new EditorEngine('session-a');
  const text = firstTextCell(engine);
  engine.updateTextCell(text.id, '一段正文');
  engine.setWritingThreadId('session-a', 'thread-a');
  const suggestion = engine.insertWritingSuggestionAfterTextCell(text.id, text.content, 'request-a');
  if (!suggestion) throw new Error('Missing suggestion');

  expect(engine.appendWritingSuggestionDelta('session-a', suggestion.id, 'request-a', 'thread-a', '先听')).toBe(true);
  expect(engine.appendWritingSuggestionDelta('session-a', suggestion.id, 'request-a', 'thread-a', '雨声')).toBe(true);
  expect(engine.completeWritingSuggestion('session-a', suggestion.id, 'request-a', 'thread-a')).toBe(true);

  expect(engine.getWritingSuggestionCell(suggestion.id)).toMatchObject({
    content: '先听雨声',
    status: 'completed',
    requestId: undefined,
  });
});

test('Refresh reuses the Cell and restores completed content when replacement fails', () => {
  const engine = new EditorEngine('session-a');
  const text = firstTextCell(engine);
  engine.updateTextCell(text.id, '一段正文');
  engine.setWritingThreadId('session-a', 'thread-a');
  const suggestion = engine.insertWritingSuggestionAfterTextCell(text.id, text.content, 'request-a');
  if (!suggestion) throw new Error('Missing suggestion');
  engine.appendWritingSuggestionDelta('session-a', suggestion.id, 'request-a', 'thread-a', '旧建议');
  engine.completeWritingSuggestion('session-a', suggestion.id, 'request-a', 'thread-a');

  const retried = engine.beginWritingSuggestionRetry(suggestion.id, 'request-b');
  expect(retried?.id).toBe(suggestion.id);
  expect(retried).toMatchObject({ content: '', previousContent: '旧建议', status: 'streaming' });
  engine.failWritingSuggestion('session-a', suggestion.id, 'request-b', {
    code: 'WRITING_REQUEST_FAILED',
    message: 'failed',
    retryable: true,
  }, 'thread-a');

  expect(engine.getWritingSuggestionCell(suggestion.id)).toMatchObject({
    id: suggestion.id,
    content: '旧建议',
    status: 'failed',
    previousContent: undefined,
  });
});

test('late events from a previous request cannot overwrite a newer Refresh', () => {
  const engine = new EditorEngine('session-a');
  const text = firstTextCell(engine);
  engine.updateTextCell(text.id, '一段正文');
  engine.setWritingThreadId('session-a', 'thread-a');
  const suggestion = engine.insertWritingSuggestionAfterTextCell(text.id, text.content, 'request-a');
  if (!suggestion) throw new Error('Missing suggestion');
  engine.failWritingSuggestion('session-a', suggestion.id, 'request-a', {
    code: 'WRITING_SSE_INTERRUPTED', message: 'failed', retryable: true,
  }, 'thread-a');
  engine.beginWritingSuggestionRetry(suggestion.id, 'request-b');

  expect(engine.appendWritingSuggestionDelta('session-a', suggestion.id, 'request-a', 'thread-a', 'stale')).toBe(false);
  expect(engine.completeWritingSuggestion('session-a', suggestion.id, 'request-a', 'thread-a')).toBe(false);
  expect(engine.appendWritingSuggestionDelta('session-a', suggestion.id, 'request-b', 'thread-a', 'fresh')).toBe(true);
  expect(engine.completeWritingSuggestion('session-a', suggestion.id, 'request-b', 'thread-a')).toBe(true);
  expect(engine.getWritingSuggestionCell(suggestion.id)?.content).toBe('fresh');
});

test('suggestion content never contributes to Weight or Energy', () => {
  const engine = new EditorEngine('session-a');
  const text = firstTextCell(engine);
  const prose = '正文。';
  engine.updateTextCell(text.id, prose);
  const entryBeforeSuggestion = engine.getState().weightPath.at(-1);
  engine.setWritingThreadId('session-a', 'thread-a');
  const suggestion = engine.insertWritingSuggestionAfterTextCell(text.id, prose, 'request-a');
  if (!suggestion) throw new Error('Missing suggestion');
  engine.appendWritingSuggestionDelta('session-a', suggestion.id, 'request-a', 'thread-a', '非常长的建议，不属于正文。');
  engine.completeWritingSuggestion('session-a', suggestion.id, 'request-a', 'thread-a');

  expect(engine.getState().weightPath.at(-1)).toEqual(entryBeforeSuggestion);
  expect(entryBeforeSuggestion?.weight).toBe(computeWeight(prose));
});

test('reload restores the Session Thread and converts an interrupted stream to recoverable failure', () => {
  const source = new EditorEngine('session-a');
  const text = firstTextCell(source);
  source.updateTextCell(text.id, '正文');
  source.setWritingThreadId('session-a', 'thread-a');
  const suggestion = source.insertWritingSuggestionAfterTextCell(text.id, text.content, 'request-a');
  if (!suggestion) throw new Error('Missing suggestion');
  source.appendWritingSuggestionDelta('session-a', suggestion.id, 'request-a', 'thread-a', '部分建议');

  const restored = new EditorEngine('temporary');
  restored.loadState(JSON.parse(JSON.stringify(source.getState())) as EditorState);

  expect(restored.getState().writingThreadId).toBe('thread-a');
  expect(restored.getWritingSuggestionCell(suggestion.id)).toMatchObject({
    content: '部分建议',
    status: 'failed',
    requestId: undefined,
    error: { code: 'WRITING_SSE_INTERRUPTED', retryable: true },
  });
});

test('clearing all prose removes derived suggestions and the Session Thread association', () => {
  const engine = new EditorEngine('session-a');
  const text = firstTextCell(engine);
  engine.updateTextCell(text.id, '正文');
  engine.setWritingThreadId('session-a', 'thread-a');
  engine.insertWritingSuggestionAfterTextCell(text.id, text.content, 'request-a');

  engine.updateTextCell(text.id, '');

  expect(engine.getState().cells).toHaveLength(1);
  expect(engine.getState().cells[0]).toMatchObject({ type: 'text', content: '' });
  expect(engine.getState().writingThreadId).toBeUndefined();
});
