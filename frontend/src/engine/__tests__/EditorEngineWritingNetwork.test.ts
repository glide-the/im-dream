// [Input] EditorEngine text updates with a mocked global fetch boundary.
// [Output] Verify ordinary Writing edits stay local and never trigger retired analysis requests.
// [Pos] EditorEngine Writing network-boundary regression test in frontend/src/engine/__tests__
// [Sync] 2026-08-31: lock removal of automatic analyze_text calls.
// [Sync] 2026-09-01: include Enter/newline and a post-edit pause in the model-request-free boundary.

import { expect, test } from '@playwright/test';
import { EditorEngine } from '../EditorEngine';

test('ordinary text edits update local weight state without any network request', async () => {
  const originalFetch = globalThis.fetch;
  let fetchCalls = 0;
  globalThis.fetch = (async () => {
    fetchCalls += 1;
    return new Response('{}');
  }) as typeof fetch;

  try {
    const engine = new EditorEngine('writing-session');
    const textCell = engine.getState().cells[0];
    if (!textCell || textCell.type !== 'text') throw new Error('Missing text cell');

    engine.updateTextCell(textCell.id, '完成一个句子。\n再完成一个句子。');
    await new Promise((resolve) => setTimeout(resolve, 2100));

    expect(fetchCalls).toBe(0);
    expect(engine.getState().weightPath).toHaveLength(1);
    expect(engine.getState().tasks).toEqual([]);
    expect(engine.getState().commentors).toEqual([]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
