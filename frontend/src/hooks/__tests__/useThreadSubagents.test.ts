// [Input] Synthetic SubAgent API tasks/messages.
// [Output] Contract tests for deterministic sorting, de-duplication, unknown events and legacy fallback.
// [Pos] useThreadSubagents pure normalization regression tests.

import { expect, test } from '@playwright/test';
import { normalizeThreadSubagentMessages, normalizeThreadSubagentTask } from '../useThreadSubagents';

test('messages are de-duplicated and sorted by sequence before timestamps', () => {
  const messages = normalizeThreadSubagentMessages([
    { id: 'later', sequence: 3, kind: 'assistant', timestamp: '2026-08-05T10:00:03Z', text: 'later', status: null, tool_name: null, tool_call_id: null, input: null, output: null },
    { id: 'first', sequence: 1, kind: 'task', timestamp: '2026-08-05T10:00:01Z', text: 'task', status: null, tool_name: null, tool_call_id: null, input: null, output: null },
    { id: 'later', sequence: 2, kind: 'final', timestamp: '2026-08-05T10:00:02Z', text: 'replacement', status: 'completed', tool_name: null, tool_call_id: null, input: null, output: null },
  ]);

  expect(messages.map((message) => message.id)).toEqual(['first', 'later']);
  expect(messages[1]).toMatchObject({ kind: 'final', text: 'replacement', sequence: 2 });
});

test('unknown message kinds degrade to a system notice', () => {
  const [message] = normalizeThreadSubagentMessages([
    { id: 'unknown', sequence: null, kind: 'future-event', timestamp: null, text: 'ignored payload', status: null, tool_name: null, tool_call_id: null, input: null, output: null },
  ]);
  expect(message).toMatchObject({ kind: 'system', text: 'future-event' });
});

test('legacy tasks synthesize activity and one final summary without duplication', () => {
  const task = normalizeThreadSubagentTask({
    task_id: 'legacy-task',
    agent_id: 'agent-1',
    agent_type: 'reviewer',
    description: 'Review the change',
    summary: '## Done',
    status: 'completed',
    tool_call_id: 'call-agent',
    spawn_depth: 1,
    started_at: '2026-08-05T10:00:00Z',
    finished_at: '2026-08-05T10:01:00Z',
    duration_ms: 60_000,
    error: null,
    activity: [
      { id: 'same-summary', kind: 'message', status: 'completed', timestamp: '2026-08-05T10:01:00Z', text: '## Done', tool_name: null },
      { id: 'tool', kind: 'tool', status: 'completed', timestamp: '2026-08-05T10:00:30Z', text: null, tool_name: 'Read' },
    ],
  });

  expect(task).not.toBeNull();
  expect(task?.messages.filter((message) => message.kind === 'final')).toHaveLength(1);
  expect(task?.messages.filter((message) => message.text === '## Done')).toHaveLength(1);
  expect(task?.messages.every((message) => message.legacy)).toBe(true);
  expect(task?.projectionVersion).toBe(1);
});

