// [Input] Safe Dream Agent tool-confirmation SSE frames and run-scoped decisions.
// [Output] Contract tests for parsing, replay reduction and trusted confirmation dispatch.
// [Pos] Dream Agent adapter tool-confirmation TDD seam.

import { expect, test } from '@playwright/test';
import {
  storyWorkspaceBuildDreamAgentToolConfirmationPayload,
  storyWorkspaceDreamAgentToolConfirmationEndpoint,
  storyWorkspaceParseDreamAgentEvent,
  storyWorkspaceReduceDreamAgentEvents,
  storyWorkspaceSubmitDreamAgentToolConfirmation,
} from '../useStoryWorkspaceDreamAgent';
import { storyWorkspaceParseDreamAgentSnapshot } from '../useStoryWorkspaceDreamAgent';

const RUN_ID = 'run_0123456789abcdef0123456789abcdef';
const SNAPSHOT = storyWorkspaceParseDreamAgentSnapshot({
  storyWorkspaceRunId: RUN_ID,
  lifecycle: 'streaming',
  activeTurnId: 'turn-1',
  canSend: false,
  sendBlockReason: 'busy',
  messages: [],
  snapshotAt: '2026-08-05T12:00:00Z',
});

test('parses only the allowlisted Dream tool-confirmation projection', () => {
  const requested = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    JSON.stringify({
      turnId: 'turn-1',
      confirmation: {
        toolCallId: 'tool-1',
        kind: 'ask_user',
        toolName: 'AskUserQuestion',
        title: '选择叙事视角',
        questions: [{
          id: 'q0',
          question: '采用哪一种视角？',
          type: 'radio',
          required: true,
          options: [{ label: '第一人称', value: 'first', description: '贴近主角' }],
        }],
        credential: 'must-not-survive',
      },
    }),
    'turn-1:4',
  );

  expect(requested).toEqual({
    type: 'tool_confirmation_requested',
    cursor: 'turn-1:4',
    turnId: 'turn-1',
    confirmation: {
      toolCallId: 'tool-1',
      kind: 'ask_user',
      toolName: 'AskUserQuestion',
      title: '选择叙事视角',
      questions: [{
        id: 'q0',
        question: '采用哪一种视角？',
        type: 'radio',
        required: true,
        options: [{ label: '第一人称', value: 'first', description: '贴近主角' }],
      }],
    },
  });
  expect(JSON.stringify(requested)).not.toContain('must-not-survive');
});

test('replay de-duplicates a pending confirmation and clears it when resolved', () => {
  const requested = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    '{"turnId":"turn-1","confirmation":{"toolCallId":"tool-2","kind":"approval","toolName":"Bash","title":"运行创作工具"}}',
    'turn-1:5',
  );
  const resolved = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_resolved',
    '{"turnId":"turn-1","toolCallId":"tool-2"}',
    'turn-1:6',
  );
  expect(requested).not.toBeNull();
  expect(resolved).not.toBeNull();

  const pending = storyWorkspaceReduceDreamAgentEvents({
    snapshot: SNAPSHOT,
    streamText: '',
    streamTurnId: null,
    pendingToolConfirmation: null,
    seenCursors: [],
  }, [requested!, requested!]);
  expect(pending.pendingToolConfirmation?.toolCallId).toBe('tool-2');
  expect(pending.seenCursors).toEqual(['turn-1:5']);

  const cleared = storyWorkspaceReduceDreamAgentEvents(pending, [resolved!]);
  expect(cleared.pendingToolConfirmation).toBeNull();
  expect(cleared.seenCursors).toEqual(['turn-1:5', 'turn-1:6']);
});

test('builds a run-scoped confirmation command without exposing thread context', async () => {
  expect(storyWorkspaceDreamAgentToolConfirmationEndpoint(RUN_ID)).toBe(
    `/api/story-workspace/workflow-runs/${RUN_ID}/dream-agent/tool-confirm`,
  );
  expect(storyWorkspaceBuildDreamAgentToolConfirmationPayload(
    RUN_ID,
    'tool-3',
    true,
    undefined,
    { '采用哪一种视角？': '第一人称' },
  )).toEqual({
    endpoint: `/api/story-workspace/workflow-runs/${RUN_ID}/dream-agent/tool-confirm`,
    body: {
      toolCallId: 'tool-3',
      approved: true,
      answers: { '采用哪一种视角？': '第一人称' },
    },
  });

  let requestBody = '';
  await storyWorkspaceSubmitDreamAgentToolConfirmation(
    RUN_ID,
    { toolCallId: 'tool-3', approved: false, reason: '用户取消' },
    {
      endpoint: 'https://example.test/dream-tool-confirm',
      token: 'token',
      fetchImpl: async (_input, init) => {
        requestBody = String(init?.body ?? '');
        return new Response(JSON.stringify({
          storyWorkspaceRunId: RUN_ID,
          toolCallId: 'tool-3',
          resolved: true,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      },
    },
  );
  expect(JSON.parse(requestBody)).toEqual({
    toolCallId: 'tool-3',
    approved: false,
    reason: '用户取消',
  });
  expect(requestBody).not.toContain('thread');
  expect(requestBody).not.toContain('deck');
});

