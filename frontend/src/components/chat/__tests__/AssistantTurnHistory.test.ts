// [Input] Hydrated assistant UIMessage parts and persisted turn metadata.
// [Output] Fail-closed process/final grouping and stable turn identity regressions.
// [Pos] Provider-free pure contract test for the shared Chat/Dream history projector.
// [Sync] 2026-09-02: cover full and final-only completed turns plus fail-closed shapes.

import { expect, test } from '@playwright/test';
import type { UIMessage } from 'ai';
import {
  projectHistoricalAssistantTurn,
  resolveCompletedFinalPartIndex,
} from '../assistantTurnHistory';

function assistant(
  parts: unknown[],
  metadata?: Record<string, unknown>,
): UIMessage {
  return {
    id: 'message-assistant',
    role: 'assistant',
    parts: parts as UIMessage['parts'],
    metadata,
  };
}

const processAndFinal = [
  { type: 'reasoning', text: '先分析' },
  { type: 'text', text: '中间说明' },
  {
    type: 'dynamic-tool',
    toolCallId: 'tool-1',
    toolName: 'Read',
    state: 'output-available',
    input: { file_path: 'story.md' },
    output: { text: 'large tool JSON' },
  },
  { type: 'text', text: '最终正文' },
];

test('new completed envelope uses the protocol final and stable turn key', () => {
  const projection = projectHistoricalAssistantTurn(assistant(processAndFinal, {
    turnId: 'turn-stable',
    turnStatus: 'completed',
    finalPartIndex: 3,
    durationMs: 2300,
  }));

  expect(projection).toEqual({
    turnKey: 'turn-stable',
    finalPartIndex: 3,
    processPartIndexes: [0, 1, 2],
    processAvailable: true,
    deferredProcess: false,
    durationMs: 2300,
  });
});

test('final-only v1 projection defers process while retaining canonical turn identity', () => {
  expect(projectHistoricalAssistantTurn(assistant(
    [{ type: 'text', text: '最终正文' }],
    {
      turnId: 'turn-stable',
      turnStatus: 'completed',
      finalPartIndex: 3,
      durationMs: 2300,
      historyProjectionVersion: 1,
      historyProcessAvailable: true,
    },
  ))).toEqual({
    turnKey: 'turn-stable',
    finalPartIndex: 0,
    processPartIndexes: [],
    processAvailable: true,
    deferredProcess: true,
    durationMs: 2300,
  });
  expect(projectHistoricalAssistantTurn(assistant(
    [{ type: 'text', text: '最终正文' }],
    {
      turnId: 'turn-stable',
      turnStatus: 'completed',
      finalPartIndex: 3,
      historyProjectionVersion: 1,
      historyProcessAvailable: false,
    },
  ))).toBeNull();
});

test('legacy completed shape infers only one strict text suffix', () => {
  const projection = projectHistoricalAssistantTurn(assistant(processAndFinal));
  expect(projection?.turnKey).toBe('message-assistant');
  expect(projection?.finalPartIndex).toBe(3);
  expect(projection?.durationMs).toBeNull();
  expect(resolveCompletedFinalPartIndex(assistant(processAndFinal))).toBe(3);
});

test('tool-ended, multi-text suffix, partial, and malformed new envelopes stay diagnostic', () => {
  expect(projectHistoricalAssistantTurn(assistant(processAndFinal.slice(0, 3)))).toBeNull();
  expect(projectHistoricalAssistantTurn(assistant([
    { type: 'reasoning', text: '分析' },
    { type: 'text', text: '正文一' },
    { type: 'text', text: '正文二' },
  ]))).toBeNull();
  expect(projectHistoricalAssistantTurn(assistant(processAndFinal, {
    is_partial: true,
    turnId: 'turn-error',
    turnStatus: 'error',
  }))).toBeNull();
  // Presence of a malformed new envelope forbids the permissive legacy path.
  expect(projectHistoricalAssistantTurn(assistant(processAndFinal, {
    turnId: 'turn-stable',
    turnStatus: 'completed',
  }))).toBeNull();
  expect(projectHistoricalAssistantTurn(assistant(processAndFinal, {
    turnProjectionInvalid: true,
  }))).toBeNull();
});

test('duration has no invented fallback or arbitrary size threshold', () => {
  expect(projectHistoricalAssistantTurn(assistant(processAndFinal, {
    turnId: 'turn-zero-duration',
    turnStatus: 'completed',
    finalPartIndex: 3,
    durationMs: 0,
  }))?.durationMs).toBe(0);
  expect(projectHistoricalAssistantTurn(assistant(processAndFinal, {
    turnId: 'turn-no-duration',
    turnStatus: 'completed',
    finalPartIndex: 3,
  }))?.durationMs).toBeNull();
});
