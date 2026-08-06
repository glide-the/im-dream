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
  storyWorkspaceGarbageCollectDreamAgentConfirmationTombstones,
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
  toolConfirmationObservation: 'known',
  snapshotAt: '2026-08-05T12:00:00Z',
});

test('hydrates an ordered safe confirmation queue from the durable snapshot projection', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    pendingToolConfirmations: [{
      toolCallId: 'tool-write',
      kind: 'approval',
      toolName: 'Write',
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
});

test('snapshot reconciliation replaces stale local state, then overlays only later SSE mutations', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    pendingToolConfirmations: [{
      toolCallId: 'tool-a', kind: 'approval', toolName: 'Write',
    }, {
      toolCallId: 'tool-b', kind: 'approval', toolName: 'Bash',
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
      toolCallId: 'tool-new', kind: 'approval', toolName: 'Write',
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

test('parses only the backend-isomorphic Dream tool-confirmation projection', () => {
  const requested = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    JSON.stringify({
      turnId: 'turn-1',
      confirmation: {
        toolCallId: 'tool-1',
        kind: 'ask_user',
        toolName: 'AskUserQuestion',
        questions: [{
          id: 'q0',
          question: '采用哪一种视角？',
          type: 'radio',
          required: true,
          options: [{ label: '第一人称', value: 'first' }],
        }],
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
      questions: [{
        id: 'q0',
        question: '采用哪一种视角？',
        type: 'radio',
        required: true,
        options: [{ label: '第一人称', value: 'first' }],
      }],
    },
  });

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

test('rejects title, option description, raw input and path-shaped tool names', () => {
  for (const confirmation of [{
    toolCallId: 'tool-title', kind: 'approval', toolName: 'Write', title: '写入剧本',
  }, {
    toolCallId: 'tool-description',
    kind: 'ask_user',
    toolName: 'AskUserQuestion',
    questions: [{
      id: 'q0', question: '继续吗？', type: 'radio', required: true,
      options: [{ label: '继续', value: '继续', description: '内部说明' }],
    }],
  }, {
    toolCallId: 'tool-input', kind: 'approval', toolName: 'Write', input: { token: 'secret' },
  }, {
    toolCallId: 'tool-path', kind: 'approval', toolName: '/Users/private/script.md',
  }]) {
    expect(storyWorkspaceParseDreamAgentEvent(
      'tool_confirmation_requested',
      JSON.stringify({ turnId: 'turn-1', confirmation }),
      `turn-1:${confirmation.toolCallId}`,
    )).toBeNull();
  }

  expect(() => storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    pendingToolConfirmations: [{
      toolCallId: 'tool-input', kind: 'approval', toolName: 'Write', input: { token: 'secret' },
    }],
  })).toThrow(/invalid pending tool confirmation/);
});

test('replay de-duplicates a pending confirmation and clears it when resolved', () => {
  const requested = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    '{"turnId":"turn-1","confirmation":{"toolCallId":"tool-2","kind":"approval","toolName":"Bash"}}',
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

test('resolved tombstone wins over a differently-cursored request replay', () => {
  const resolved = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_resolved',
    '{"turnId":"turn-1","toolCallId":"tool-replayed"}',
    'turn-1:6',
  )!;
  const first = storyWorkspaceReduceDreamAgentEvents({
    snapshot: SNAPSHOT,
    streamText: '',
    streamTurnId: 'turn-1',
    pendingToolConfirmations: [{
      toolCallId: 'tool-replayed', kind: 'approval', toolName: 'Write',
    }],
    seenCursors: ['turn-1:5'],
  }, [resolved]);
  const replayedWithDifferentCursor = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    '{"turnId":"turn-1","confirmation":{"toolCallId":"tool-replayed","kind":"approval","toolName":"Write"}}',
    'turn-1:9',
  )!;

  const converged = storyWorkspaceReduceDreamAgentEvents(first, [replayedWithDifferentCursor]);
  expect(converged.pendingToolConfirmations).toEqual([]);
  expect(converged.seenCursors).toContain('turn-1:9');
});

test('reconciliation tombstone has priority over a later replay request', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    pendingToolConfirmations: [{
      toolCallId: 'tool-replayed', kind: 'approval', toolName: 'Write',
    }],
  });
  const resolved = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_resolved',
    '{"turnId":"turn-1","toolCallId":"tool-replayed"}',
    'turn-1:6',
  )!;
  const replayed = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    '{"turnId":"turn-1","confirmation":{"toolCallId":"tool-replayed","kind":"approval","toolName":"Write"}}',
    'turn-1:9',
  )!;

  expect(storyWorkspaceReconcileDreamAgentPendingToolConfirmations(
    snapshot,
    'turn-1',
    [resolved, replayed],
  )).toEqual([]);
});

test('a turn-2 mutation supersedes an idle snapshot taken after turn-1', () => {
  const idle = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    lifecycle: 'idle',
    activeTurnId: null,
    pendingToolConfirmations: [],
  });
  const turn2 = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    '{"turnId":"turn-2","confirmation":{"toolCallId":"tool-turn-2","kind":"approval","toolName":"Write"}}',
    'turn-2:1',
  )!;

  expect(storyWorkspaceReconcileDreamAgentPendingToolConfirmations(
    idle,
    'turn-1',
    [turn2],
  ).map((item) => item.toolCallId)).toEqual(['tool-turn-2']);
});

test('a turn-1 tombstone cannot resolve the same tool id owned by turn-2', () => {
  const turn2Snapshot = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    activeTurnId: 'turn-2',
    pendingToolConfirmations: [{
      toolCallId: 'tool-shared', kind: 'approval', toolName: 'Write',
    }],
  });
  const lateTurn1Resolved = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_resolved',
    '{"turnId":"turn-1","toolCallId":"tool-shared"}',
    'turn-1:10',
  )!;

  const reduced = storyWorkspaceReduceDreamAgentEvents({
    snapshot: turn2Snapshot,
    streamText: '',
    streamTurnId: 'turn-2',
    seenCursors: [],
  }, [lateTurn1Resolved]);
  expect(reduced.pendingToolConfirmations.map((item) => item.toolCallId)).toEqual(['tool-shared']);
});

test('server observation bounds tombstones without treating unknown as absence', () => {
  const toolA = JSON.stringify(['turn-1', 'tool-a']);
  const toolB = JSON.stringify(['turn-1', 'tool-b']);
  const unknown = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    toolConfirmationObservation: 'unknown',
    pendingToolConfirmations: [],
  });
  expect(storyWorkspaceGarbageCollectDreamAgentConfirmationTombstones(
    [toolA, toolB],
    unknown,
  )).toEqual([toolA, toolB]);
  const manyUnknown = Array.from(
    { length: 300 },
    (_, index) => JSON.stringify(['turn-1', `tool-${index}`]),
  );
  const boundedUnknown = storyWorkspaceGarbageCollectDreamAgentConfirmationTombstones(
    manyUnknown,
    unknown,
  );
  expect(boundedUnknown).toHaveLength(256);
  expect(boundedUnknown[0]).toBe(JSON.stringify(['turn-1', 'tool-44']));

  const known = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    toolConfirmationObservation: 'known',
    pendingToolConfirmations: [{
      toolCallId: 'tool-b', kind: 'approval', toolName: 'Write',
    }],
  });
  expect(storyWorkspaceGarbageCollectDreamAgentConfirmationTombstones(
    [toolA, toolB],
    known,
  )).toEqual([toolA, toolB]);

  const replacement = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    activeTurnId: 'turn-2',
    toolConfirmationObservation: 'known',
    pendingToolConfirmations: [],
  });
  expect(storyWorkspaceGarbageCollectDreamAgentConfirmationTombstones(
    [toolA, toolB],
    replacement,
  )).toEqual([]);

  const idle = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    lifecycle: 'idle',
    activeTurnId: null,
    toolConfirmationObservation: 'known',
    pendingToolConfirmations: [],
  });
  expect(storyWorkspaceGarbageCollectDreamAgentConfirmationTombstones(
    [toolA, toolB],
    idle,
  )).toEqual([]);
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
