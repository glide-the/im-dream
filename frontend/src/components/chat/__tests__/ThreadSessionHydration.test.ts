// [Input] Persisted canonical thread rows shared by Chat and Dream.
// [Output] Exact private-row and visible-part filtering contract.
// [Pos] Shared thread hydration visibility regression seam.

import { expect, test } from '@playwright/test';
import type { UIMessage } from 'ai';
import {
  ClaudeThreadHydrationUnknownError,
  claudeThreadExpectedDispatchIsTerminal,
  claudeThreadHydrationRetryDelayMs,
  claudeThreadPartIsVisible,
  fetchClaudeThreadMessages,
  fetchClaudeThreadStatus,
  filterClaudeThreadVisibleMessages,
  type ClaudeThreadHydrationSnapshot,
} from '../threadSessionHydration';

test('failed and malformed hydration samples are typed unknown, never empty/idle', async () => {
  const originalFetch = globalThis.fetch;
  const originalLocalStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  try {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: { getItem: () => 'test-token' },
    });
    globalThis.fetch = (async () => new Response('{}', { status: 503 })) as typeof fetch;
    await expect(fetchClaudeThreadMessages('thread-unknown')).rejects.toMatchObject({
      name: 'ClaudeThreadHydrationUnknownError',
      stage: 'messages',
    });
    expect(new ClaudeThreadHydrationUnknownError('messages', 'non-2xx', { httpStatus: 503 }))
      .toMatchObject({ stage: 'messages', httpStatus: 503 });

    globalThis.fetch = (async () => new Response('{}', {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })) as typeof fetch;
    await expect(fetchClaudeThreadStatus('thread-unknown')).rejects
      .toBeInstanceOf(ClaudeThreadHydrationUnknownError);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalLocalStorage) {
      Object.defineProperty(globalThis, 'localStorage', originalLocalStorage);
    } else {
      delete (globalThis as { localStorage?: Storage }).localStorage;
    }
  }
});

test('hydration retry uses bounded exponential backoff', () => {
  expect([0, 1, 2, 3, 4, 20].map(claudeThreadHydrationRetryDelayMs))
    .toEqual([250, 500, 1_000, 2_000, 4_000, 4_000]);
});

const message = (
  id: string,
  parts: unknown[],
  metadata?: Record<string, unknown>,
): UIMessage => ({
  id,
  role: 'assistant',
  parts: parts as UIMessage['parts'],
  metadata,
});

test('visibility matches ChatMessageList renderers and retains workspace file attachments', () => {
  expect(claudeThreadPartIsVisible({ type: 'text', text: '中文正文' })).toBe(true);
  expect(claudeThreadPartIsVisible({ type: 'reasoning', text: 'reasoning' })).toBe(true);
  expect(claudeThreadPartIsVisible({
    type: 'file',
    filename: 'story.md',
    mediaType: 'text/markdown',
    url: '/api/workspace/files/story.md',
    workspacePath: 'story.md',
  })).toBe(true);
  expect(claudeThreadPartIsVisible({
    type: 'dynamic-tool',
    toolCallId: 'tool-1',
    toolName: 'Bash',
    state: 'input-available',
    input: { command: 'pwd' },
  })).toBe(true);
  expect(claudeThreadPartIsVisible({ type: 'text', text: '  \n ' })).toBe(false);
  expect(claudeThreadPartIsVisible({ type: 'step-start' })).toBe(false);
  // ChatMessageList has no source-url renderer; an unsupported part alone must
  // not create an empty bubble during history hydration.
  expect(claudeThreadPartIsVisible({ type: 'source-url', url: 'https://example.test' }))
    .toBe(false);
});

test('preserves every Dream business row and drops only zero-visible-part rows', () => {
  const visible = filterClaudeThreadVisibleMessages([
    message('dream-launch', [{ type: 'text', text: 'private launch goal' }], {
      kind: 'story-workspace-dream-agent-user',
      visibility: 'system-hidden',
    }),
    message('guidance', [{ type: 'text', text: 'private guidance' }], {
      kind: 'story-workspace-guidance',
    }),
    message('confirmation', [{ type: 'text', text: 'private confirm' }], {
      kind: 'story-workspace-dream-confirmation',
    }),
    message('episode-action', [{ type: 'text', text: 'private action' }], {
      kind: 'story-workspace-dream-agent-user',
      story_workspace_episode_action: { schema: 'story-workspace-episode-action/v1' },
    }),
    message('blank', [{ type: 'text', text: '' }, { type: 'step-start' }]),
    message('unsupported-only', [{ type: 'source-url', url: 'https://example.test' }]),
    message('human-dream', [{ type: 'text', text: '保留这条 Dream 对话' }], {
      kind: 'story-workspace-dream-agent-user',
    }),
    message('user-json-control', [{
      type: 'text',
      text: '{"action":"confirm_and_continue","run":"run_abc"}',
    }], {
      kind: 'story-workspace-dream-confirmation',
      visibility: 'system-hidden',
    }),
    message('workspace-file', [{
      type: 'file',
      filename: 'episode-outline.md',
      mediaType: 'text/markdown',
      url: '/api/workspace/files/episode-outline.md',
    }]),
  ]);

  expect(visible.map((item) => item.id)).toEqual([
    'dream-launch',
    'guidance',
    'confirmation',
    'episode-action',
    'human-dream',
    'user-json-control',
    'workspace-file',
  ]);
  expect(visible.find((item) => item.id === 'user-json-control')?.parts).toEqual([{
    type: 'text',
    text: '{"action":"confirm_and_continue","run":"run_abc"}',
  }]);
});

test('only the exact persisted internal command can settle an idle pre-mounted observer', () => {
  const snapshot = (dispatchStatus: 'dispatching' | 'dispatched' | 'failed') => ({
    messages: [],
    dispatchStatusByMessageId: { 'expected-command': dispatchStatus },
    status: {
      running: false,
      lifecycle: 'idle',
      turn_count: 4,
      pending_tool_call_ids: [],
      tool_confirmation_observation: 'known',
    },
    settledToolCallIds: new Set<string>(),
    runtimePendingToolCallIds: new Set<string>(),
    running: false,
  }) satisfies ClaudeThreadHydrationSnapshot;

  expect(claudeThreadExpectedDispatchIsTerminal(snapshot('dispatching'), 'expected-command'))
    .toBe(false);
  expect(claudeThreadExpectedDispatchIsTerminal(snapshot('dispatched'), 'expected-command'))
    .toBe(true);
  expect(claudeThreadExpectedDispatchIsTerminal(snapshot('failed'), 'expected-command'))
    .toBe(true);
  expect(claudeThreadExpectedDispatchIsTerminal({
    ...snapshot('failed'),
    status: { ...snapshot('failed').status, lifecycle: 'not_found' },
  }, 'expected-command')).toBe(true);
  expect(claudeThreadExpectedDispatchIsTerminal(snapshot('dispatched'), 'other-command'))
    .toBe(false);
  expect(claudeThreadExpectedDispatchIsTerminal({
    ...snapshot('dispatched'),
    status: { ...snapshot('dispatched').status, running: true },
    running: true,
  }, 'expected-command'))
    .toBe(false);
});
