// [Input] Persisted Dream auto-repair chat-message SSE boundaries and canonical history rows.
// [Output] Verify real-time insertion, first-attempt rollback, refresh recovery,
//          idempotent de-duplication, and typed exhausted-error preservation.
// [Pos] Shared Chat/Dream reconnect reducer regression test.
// [Sync] 2026-09-01: initial visible auto-repair user message coverage.
// [Sync] 2026-09-01: preserve the typed public reason for a bounded exhausted repair.

import { expect, test } from '@playwright/test';
import type { UIMessage } from 'ai';
import type { UIMessageChunk } from 'ai';
import {
  applyBackendEventToMessages,
  type BackendEvent,
} from '../../../lib/claude-agent-sse-utils';
import {
  ClaudeAgentChatTransport,
  ClaudeAgentTransportError,
  readClaudeAgentErrorText,
} from '../../../lib/claude-agent-transport';

const metadata = {
  kind: 'story-workspace-dream-auto-repair',
  schemaVersion: 'story-workspace-dream-auto-repair/v1',
  originatingMessageId: 'origin-message',
  originatingTurnId: 'origin-turn',
  workflowRunId: `run_${'a'.repeat(32)}`,
  repairAttempt: 1,
  validationCode: 'PROJECT_STORY_SLUG_MISMATCH',
  idempotencyKey: 'dream-auto-repair/v1:stable',
  dispatch_status: 'dispatched',
};

const repairEvent: BackendEvent = {
  type: 'chat-message',
  message: {
    id: 'dream_repair_stable',
    role: 'user',
    parts: [{ type: 'text', text: '请修正 workspace slug。' }],
    metadata,
  },
};

const origin: UIMessage = {
  id: 'origin-message',
  role: 'user',
  parts: [{ type: 'text', text: '生成项目' }],
};

test('live auto-repair boundary removes unpersisted assistant and inserts exact user fact', () => {
  const firstAttempt: UIMessage = {
    id: 'reconnect-asst-first-attempt',
    role: 'assistant',
    parts: [{ type: 'text', text: '未通过后置校验的结果' }],
  };

  const next = applyBackendEventToMessages([origin, firstAttempt], repairEvent);

  expect(next).toEqual([
    origin,
    {
      id: 'dream_repair_stable',
      role: 'user',
      parts: [{ type: 'text', text: '请修正 workspace slug。' }],
      metadata,
    },
  ]);
});

test('refresh history plus replayed boundary stays single-valued by message id', () => {
  const hydrated = applyBackendEventToMessages([origin], repairEvent);
  const replayed = applyBackendEventToMessages(hydrated, repairEvent);
  const withRepairAssistant = applyBackendEventToMessages(replayed, {
    type: 'text-delta',
    id: 'repair-text',
    delta: '已完成修正',
  });

  expect(replayed.filter((message) => message.id === 'dream_repair_stable')).toHaveLength(1);
  expect(withRepairAssistant.map((message) => message.role)).toEqual([
    'user',
    'user',
    'assistant',
  ]);
  expect(withRepairAssistant.at(-1)?.parts).toEqual([
    { type: 'text', text: '已完成修正' },
  ]);
});

test('malformed or client-forged chat-message boundary is ignored', () => {
  const forged = applyBackendEventToMessages([origin], {
    ...repairEvent,
    message: {
      ...(repairEvent.message as Record<string, unknown>),
      id: 'public-message',
    },
  });

  expect(forged).toEqual([origin]);
});

test('direct POST transport closes cleanly at the persisted user boundary', async () => {
  class ExposedTransport extends ClaudeAgentChatTransport {
    convert(stream: ReadableStream<Uint8Array>): ReadableStream<UIMessageChunk> {
      return this.processResponseStream(stream);
    }
  }
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode([
        'data: {"type":"text-start","id":"first"}',
        'data: {"type":"text-delta","id":"first","delta":"uncommitted"}',
        `data: ${JSON.stringify(repairEvent)}`,
        'data: {"type":"text-delta","id":"repair","delta":"must use reconnect"}',
        '',
      ].join('\n\n')));
      controller.close();
    },
  });
  const reader = new ExposedTransport().convert(stream).getReader();
  const chunks: UIMessageChunk[] = [];
  while (true) {
    const result = await reader.read();
    if (result.done) break;
    chunks.push(result.value);
  }

  expect(chunks.some((chunk) => (
    chunk.type === 'text-delta' && chunk.delta === 'uncommitted'
  ))).toBe(true);
  expect(chunks.some((chunk) => (
    chunk.type === 'text-delta' && chunk.delta === 'must use reconnect'
  ))).toBe(false);
  expect(chunks.at(-1)).toMatchObject({ type: 'finish', finishReason: 'stop' });
});

test('typed exhausted error preserves only the server-authored public reason', () => {
  const error = new ClaudeAgentTransportError({
    type: 'error',
    errorText: '最终错误：DREAM_STAGE_ENTITY_ID_DUPLICATE；已停止自动修正。',
    errorCode: 'DREAM_WORKBENCH_AUTO_REPAIR_FAILED',
    retryable: false,
  });

  expect(readClaudeAgentErrorText(error)).toContain(
    'DREAM_STAGE_ENTITY_ID_DUPLICATE',
  );
  expect(readClaudeAgentErrorText(new Error('internal stack'))).toBeNull();
});
