// [Input] Safe Dream Agent tool-confirmation SSE frames and run-scoped decisions.
// [Output] Contract tests for parsing, replay reduction and trusted confirmation dispatch.
// [Pos] Dream Agent adapter tool-confirmation TDD seam.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses a built-in omitted from browser app types.
import { readFileSync } from 'node:fs';
import {
  storyWorkspaceBuildDreamAgentToolConfirmationPayload,
  storyWorkspaceDreamAgentReconnectDelay,
  storyWorkspaceDreamAgentToolConfirmationEndpoint,
  storyWorkspaceParseDreamAgentEvent,
  storyWorkspaceReduceDreamAgentEvents,
  storyWorkspaceReconcileDreamAgentPendingToolConfirmations,
  storyWorkspaceSubmitDreamAgentToolConfirmation,
} from '../useStoryWorkspaceDreamAgent';
import { storyWorkspaceParseDreamAgentSnapshot } from '../useStoryWorkspaceDreamAgent';

const RUN_ID = 'run_0123456789abcdef0123456789abcdef';
const ADAPTER_SOURCE = readFileSync(new URL('../useStoryWorkspaceDreamAgent.ts', import.meta.url), 'utf8');
const SNAPSHOT = storyWorkspaceParseDreamAgentSnapshot({
  storyWorkspaceRunId: RUN_ID,
  lifecycle: 'streaming',
  activeTurnId: 'turn-1',
  canSend: false,
  sendBlockReason: 'busy',
  messages: [],
  pendingToolConfirmations: [],
  snapshotAt: '2026-08-05T12:00:00Z',
});

test('hydrates an ordered safe confirmation queue from the durable snapshot projection', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    pendingToolConfirmations: [{
      toolCallId: 'tool-write',
      kind: 'approval',
      toolName: 'Write',
      title: '写入剧本文件',
      input: { file_path: '/Users/private/story/script.md', token: 'secret' },
    }, {
      toolCallId: 'tool-question',
      kind: 'ask_user',
      toolName: 'AskUserQuestion',
      questions: [{
        id: 'q0',
        question: '采用哪一种视角？',
        type: 'radio',
        required: true,
        options: [{ label: '第一人称', value: 'first' }],
      }],
    }],
  });

  expect(snapshot.pendingToolConfirmations.map((item) => item.toolCallId)).toEqual([
    'tool-write',
    'tool-question',
  ]);
  expect(snapshot.pendingToolConfirmations[0]).toEqual({
    toolCallId: 'tool-write',
    kind: 'approval',
    toolName: 'Write',
    title: '写入剧本文件',
  });
  const hydrated = storyWorkspaceReduceDreamAgentEvents({
    snapshot,
    streamText: '',
    streamTurnId: null,
    seenCursors: [],
  }, []);
  expect(hydrated.pendingToolConfirmations.map((item) => item.toolCallId)).toEqual([
    'tool-write',
    'tool-question',
  ]);
  expect(JSON.stringify(snapshot.pendingToolConfirmations)).not.toContain('/Users/private');
  expect(JSON.stringify(snapshot.pendingToolConfirmations)).not.toContain('secret');
});

test('snapshot reconciliation replaces stale local state, then overlays only later SSE mutations', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    pendingToolConfirmations: [{
      toolCallId: 'tool-a', kind: 'approval', toolName: 'Write', title: '写入文件',
    }, {
      toolCallId: 'tool-b', kind: 'approval', toolName: 'Bash', title: '运行创作工具',
    }],
  });
  const afterRequest = [
    storyWorkspaceParseDreamAgentEvent(
      'tool_confirmation_resolved',
      '{"turnId":"turn-1","toolCallId":"tool-a"}',
      'turn-1:8',
    )!,
    storyWorkspaceParseDreamAgentEvent(
      'tool_confirmation_requested',
      '{"turnId":"turn-1","confirmation":{"toolCallId":"tool-b","kind":"approval","toolName":"Bash"}}',
      'turn-1:9',
    )!,
    storyWorkspaceParseDreamAgentEvent(
      'tool_confirmation_requested',
      '{"turnId":"turn-1","confirmation":{"toolCallId":"tool-c","kind":"approval","toolName":"Write"}}',
      'turn-1:10',
    )!,
  ];

  expect(storyWorkspaceReconcileDreamAgentPendingToolConfirmations(
    snapshot,
    'turn-1',
    afterRequest,
  ).map((item) => item.toolCallId)).toEqual(['tool-b', 'tool-c']);
});

test('snapshot turn replacement ignores late replay from the replaced turn', () => {
  const replacement = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    activeTurnId: 'turn-2',
    pendingToolConfirmations: [{
      toolCallId: 'tool-new', kind: 'approval', toolName: 'Write', title: '写入剧本',
    }],
  });
  const oldReplay = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    '{"turnId":"turn-1","confirmation":{"toolCallId":"tool-old","kind":"approval","toolName":"Write"}}',
    'turn-1:99',
  )!;

  expect(storyWorkspaceReconcileDreamAgentPendingToolConfirmations(
    replacement,
    'turn-1',
    [oldReplay],
  ).map((item) => item.toolCallId)).toEqual(['tool-new']);
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

  const networkRequested = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    JSON.stringify({
      turnId: 'turn-1',
      confirmation: {
        toolCallId: 'tool-network',
        kind: 'sandbox_network',
        toolName: 'WebFetch',
        network: { host: 'example.test', policy: 'deny' },
      },
    }),
    'turn-1:5',
  );
  expect(networkRequested && 'confirmation' in networkRequested
    ? networkRequested.confirmation.network
    : null).toEqual({ host: 'example.test', policy: 'deny' });
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
    pendingToolConfirmations: [],
    seenCursors: [],
  }, [requested!, requested!, storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    '{"turnId":"turn-1","confirmation":{"toolCallId":"tool-3","kind":"approval","toolName":"Write"}}',
    'turn-1:7',
  )!]);
  expect(pending.pendingToolConfirmations.map((item) => item.toolCallId)).toEqual(['tool-2', 'tool-3']);
  expect(pending.seenCursors).toEqual(['turn-1:5', 'turn-1:7']);

  const cleared = storyWorkspaceReduceDreamAgentEvents(pending, [resolved!]);
  expect(cleared.pendingToolConfirmations.map((item) => item.toolCallId)).toEqual(['tool-3']);
  expect(cleared.seenCursors).toEqual(['turn-1:5', 'turn-1:7', 'turn-1:6']);
});

test('keeps reconnect backoff across immediate disconnects and resets only after stability', () => {
  expect(Array.from({ length: 7 }, (_, index) => storyWorkspaceDreamAgentReconnectDelay(index)))
    .toEqual([500, 1000, 2000, 4000, 8000, 8000, 8000]);
  expect(ADAPTER_SOURCE).toContain('onOpen: markStreamOpen');
  expect(ADAPTER_SOURCE).toContain('STORY_WORKSPACE_DREAM_AGENT_STABLE_CONNECTION_MS');
  expect(ADAPTER_SOURCE).not.toContain("const process = (parsed: StoryWorkspaceDreamAgentEvent) => {\n      if (!parsed || !active) return;\n      reconnectIndex = 0;");
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
    { q0: '第一人称' },
  )).toEqual({
    endpoint: `/api/story-workspace/workflow-runs/${RUN_ID}/dream-agent/tool-confirm`,
    body: {
      toolCallId: 'tool-3',
      approved: true,
      answers: { q0: '第一人称' },
    },
  });
  expect(storyWorkspaceBuildDreamAgentToolConfirmationPayload(
    RUN_ID,
    'tool-utf8',
    true,
    undefined,
    { q0: '梦'.repeat(3_000) },
  )).toBeNull();

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
