// [Input] Dream-safe snapshots and normalized, server-allowlisted SSE events.
// [Output] Node seam coverage for snapshot-first, terminal reconciliation and send boundaries.
// [Pos] Dream Agent adapter Red/Green contract tests (design_008 §9/§20).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses a built-in omitted from browser app types.
import { readFileSync } from 'node:fs';
import {
  STORY_WORKSPACE_DREAM_AGENT_BUSY_POLL_INTERVAL_MS,
  storyWorkspaceBuildDreamAgentSendPayload,
  storyWorkspaceComputeDreamAgentUnreadCount,
  storyWorkspaceDreamAgentHasSettledMessage,
  storyWorkspaceDreamAgentEventsEndpoint,
  storyWorkspaceFetchDreamAgentSnapshot,
  storyWorkspaceDreamAgentShouldPollSettlement,
  storyWorkspaceDreamAgentShouldPollBusy,
  storyWorkspaceReadDreamAgentEventStream,
  storyWorkspaceParseDreamAgentEvent,
  storyWorkspaceParseDreamAgentSnapshot,
  storyWorkspaceReconcileDreamAgentPendingToolConfirmations,
  storyWorkspaceReduceDreamAgentEvents,
} from '../useStoryWorkspaceDreamAgent';

const ADAPTER_SOURCE = readFileSync(new URL('../useStoryWorkspaceDreamAgent.ts', import.meta.url), 'utf8');

const RUN_ID = 'run_0123456789abcdef0123456789abcdef';

const SNAPSHOT = {
  storyWorkspaceRunId: RUN_ID,
  lifecycle: 'streaming',
  activeTurnId: 'turn-1',
  canSend: false,
  sendBlockReason: 'continuing',
  messages: [{ id: 'm1', role: 'assistant', text: '已保存的人物。', truncated: false, createdAt: '2026-08-05T00:00:00Z' }],
  pendingToolConfirmations: [],
  toolConfirmationObservation: 'known',
  snapshotAt: '2026-08-05T00:00:01Z',
};

test('idle busy snapshots request low-frequency REST reconciliation without treating time as completion', () => {
  expect(STORY_WORKSPACE_DREAM_AGENT_BUSY_POLL_INTERVAL_MS).toBeGreaterThanOrEqual(2_000);
  expect(storyWorkspaceDreamAgentShouldPollBusy({
    ...SNAPSHOT,
    lifecycle: 'idle',
    activeTurnId: null,
    sendBlockReason: 'busy',
  })).toBe(true);
  expect(storyWorkspaceDreamAgentShouldPollBusy({
    ...SNAPSHOT,
    lifecycle: 'streaming',
    sendBlockReason: 'busy',
  })).toBe(false);
  expect(storyWorkspaceDreamAgentShouldPollBusy({
    ...SNAPSHOT,
    lifecycle: 'idle',
    activeTurnId: null,
    canSend: true,
    sendBlockReason: null,
  })).toBe(false);
  expect(ADAPTER_SOURCE).toContain('void reconcile()');
  expect(ADAPTER_SOURCE).not.toMatch(/setTimeout\([^)]*setSnapshot\([^)]*canSend/s);
});

test('streaming snapshots keep a REST settlement watchdog when SSE has no terminal frame', () => {
  expect(storyWorkspaceDreamAgentShouldPollSettlement({ lifecycle: 'streaming' })).toBe(true);
  expect(storyWorkspaceDreamAgentShouldPollSettlement({ lifecycle: 'idle' })).toBe(false);
  expect(ADAPTER_SOURCE).toContain('storyWorkspaceDreamAgentShouldPollSettlement(candidate)');
});

test('accepted action settles from its persisted user message and an authoritative idle send gate', () => {
  const messageId = 'dream_agent_' + 'a'.repeat(64);
  const base = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    lifecycle: 'idle',
    activeTurnId: null,
    canSend: true,
    sendBlockReason: null,
    messages: [
      { id: 'assistant-before', role: 'assistant', text: '旧回复', truncated: false, createdAt: '2026-08-05T00:00:00Z' },
      { id: messageId, role: 'user', text: '受控 Episode 操作', truncated: false, createdAt: '2026-08-05T00:00:01Z' },
    ],
  });
  expect(storyWorkspaceDreamAgentHasSettledMessage(base, messageId)).toBe(true);
  expect(storyWorkspaceDreamAgentHasSettledMessage({
    ...base,
    canSend: false,
    sendBlockReason: 'busy',
  }, messageId)).toBe(false);
  expect(storyWorkspaceDreamAgentHasSettledMessage({
    ...base,
    lifecycle: 'streaming',
    activeTurnId: 'turn-after-accepted',
  }, messageId)).toBe(false);
  expect(storyWorkspaceDreamAgentHasSettledMessage(base, 'different-message')).toBe(false);
});

test('snapshot is a safe, complete first render before any increment is reduced', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot(SNAPSHOT);
  const model = storyWorkspaceReduceDreamAgentEvents({ snapshot, streamText: '', streamTurnId: null, seenCursors: [] }, []);
  expect(model.snapshot.messages).toEqual(snapshot.messages);
  expect(model.streamText).toBe('');
});

test('a concurrent confirmation for a newer turn overlays an older in-flight snapshot', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot(SNAPSHOT);
  const requested = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_requested',
    '{"turnId":"turn-2","confirmation":{"toolCallId":"tool-turn-2","kind":"approval","toolName":"Write"}}',
    'turn-2:1',
  )!;

  expect(storyWorkspaceReconcileDreamAgentPendingToolConfirmations(
    snapshot,
    'turn-1',
    [requested],
  ).map((item) => item.toolCallId)).toEqual(['tool-turn-2']);
});

test('snapshot preserves safe text/activity order and drops untrusted extra fields', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot({
    ...SNAPSHOT,
    messages: [{
      ...SNAPSHOT.messages[0],
      content: [
        { kind: 'text', text: '先读取。', truncated: false, reasoning: 'hidden' },
        {
          kind: 'activity',
          id: 'dream_activity_0123456789abcdef0123456789abcdef',
          category: 'workspace_read',
          label: '读取工作区资料',
          status: 'completed',
          toolCallId: 'raw-call',
          input: { token: 'secret' },
        },
        { kind: 'text', text: '再继续。', truncated: false },
      ],
    }],
  });

  expect(snapshot.messages[0]?.content).toEqual([
    { kind: 'text', text: '先读取。', truncated: false },
    {
      kind: 'activity',
      id: 'dream_activity_0123456789abcdef0123456789abcdef',
      category: 'workspace_read',
      label: '读取工作区资料',
      status: 'completed',
    },
    { kind: 'text', text: '再继续。', truncated: false },
  ]);
});

test('safe activity lifecycle is cursor-de-duplicated and never accepts raw tool fields', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot(SNAPSHOT);
  const started = storyWorkspaceParseDreamAgentEvent(
    'agent_activity_started',
    JSON.stringify({
      turnId: 'turn-1',
      activity: {
        kind: 'activity',
        id: 'dream_activity_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        category: 'other',
        label: '处理 Dream 创作任务',
        status: 'running',
        toolName: 'Bash',
        input: { command: 'rm -rf /' },
      },
    }),
    'turn-1:4',
  );
  const finished = storyWorkspaceParseDreamAgentEvent(
    'agent_activity_finished',
    JSON.stringify({
      turnId: 'turn-1',
      activity: {
        kind: 'activity',
        id: 'dream_activity_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        category: 'other',
        label: '处理 Dream 创作任务',
        status: 'stopped',
        output: 'secret stack',
      },
    }),
    'turn-1:5',
  );
  expect(started).not.toBeNull();
  expect(finished).not.toBeNull();
  const running = storyWorkspaceReduceDreamAgentEvents({
    snapshot, streamText: '', streamTurnId: null, seenCursors: [],
  }, [started!, started!]);
  expect(running.streamContent).toEqual([{
    kind: 'activity',
    id: 'dream_activity_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    category: 'other',
    label: '处理 Dream 创作任务',
    status: 'running',
  }]);
  const stopped = storyWorkspaceReduceDreamAgentEvents(running, [finished!]);
  expect(stopped.streamContent).toEqual([{
    kind: 'activity',
    id: 'dream_activity_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    category: 'other',
    label: '处理 Dream 创作任务',
    status: 'stopped',
  }]);
  expect(JSON.stringify(stopped)).not.toContain('rm -rf');
  expect(JSON.stringify(stopped)).not.toContain('secret stack');
});

test('activity parser rejects non-fixed labels and raw reasoning events', () => {
  expect(storyWorkspaceParseDreamAgentEvent(
    'agent_activity_started',
    JSON.stringify({
      turnId: 'turn-1',
      activity: {
        kind: 'activity',
        id: 'dream_activity_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
        category: 'dream_write',
        label: '角色阶段已经完成',
        status: 'running',
      },
    }),
    'turn-1:6',
  )).toBeNull();
  expect(storyWorkspaceParseDreamAgentEvent(
    'reasoning-delta',
    '{"turnId":"turn-1","delta":"hidden"}',
    'turn-1:7',
  )).toBeNull();
});

test('confirmation resolution and activity completion use independent stable subcursors', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot(SNAPSHOT);
  const resolved = storyWorkspaceParseDreamAgentEvent(
    'tool_confirmation_resolved',
    '{"turnId":"turn-1","toolCallId":"tool-write"}',
    'turn-1:8:0',
  );
  const finished = storyWorkspaceParseDreamAgentEvent(
    'agent_activity_finished',
    JSON.stringify({
      turnId: 'turn-1',
      activity: {
        kind: 'activity',
        id: 'dream_activity_cccccccccccccccccccccccccccccccc',
        category: 'dream_write',
        label: '更新 Dream 内容',
        status: 'completed',
      },
    }),
    'turn-1:8:1',
  );
  expect(resolved).not.toBeNull();
  expect(finished).not.toBeNull();
  const reduced = storyWorkspaceReduceDreamAgentEvents({
    snapshot,
    streamText: '',
    streamTurnId: 'turn-1',
    pendingToolConfirmations: [{
      toolCallId: 'tool-write', kind: 'approval', toolName: 'write dream stage',
    }],
    seenCursors: [],
  }, [resolved!, finished!, resolved!, finished!]);
  expect(reduced.pendingToolConfirmations).toEqual([]);
  expect(reduced.streamContent).toEqual([{
    kind: 'activity',
    id: 'dream_activity_cccccccccccccccccccccccccccccccc',
    category: 'dream_write',
    label: '更新 Dream 内容',
    status: 'completed',
  }]);
  expect(reduced.seenCursors).toEqual(['turn-1:8:0', 'turn-1:8:1']);
});

test('replayed cursor is de-duplicated and terminal event requests durable reconciliation', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot(SNAPSHOT);
  const delta = storyWorkspaceParseDreamAgentEvent('assistant_text_delta', '{"turnId":"turn-1","delta":"继续写场景"}', 'turn-1:7');
  const committed = storyWorkspaceParseDreamAgentEvent('assistant_message_committed', '{"turnId":"turn-1"}', 'turn-1:8');
  expect(delta).not.toBeNull();
  expect(committed).not.toBeNull();
  const first = storyWorkspaceReduceDreamAgentEvents({ snapshot, streamText: '', streamTurnId: null, seenCursors: [] }, [delta!, delta!]);
  expect(first.streamText).toBe('继续写场景');
  expect(first.shouldReconcile).toBe(false);
  const terminal = storyWorkspaceReduceDreamAgentEvents(first, [committed!]);
  expect(terminal.shouldReconcile).toBe(true);
  expect(terminal.streamText).toBe('');
});

test('safe failed and cancelled terminal events parse without exposing backend details', () => {
  const failed = storyWorkspaceParseDreamAgentEvent(
    'agent_turn_failed',
    JSON.stringify({ turnId: 'turn-failed', code: 'DREAM_AGENT_TURN_FAILED' }),
    'turn-failed:7',
  );
  const cancelled = storyWorkspaceParseDreamAgentEvent(
    'agent_turn_cancelled',
    JSON.stringify({ turnId: 'turn-cancelled' }),
    'turn-cancelled:8',
  );
  const leaked = storyWorkspaceParseDreamAgentEvent(
    'agent_turn_failed',
    JSON.stringify({
      turnId: 'turn-failed',
      code: 'DREAM_AGENT_TURN_FAILED',
      errorText: '/private/path provider-secret',
    }),
    'turn-failed:9',
  );

  expect(failed).toEqual({
    type: 'agent_turn_failed',
    cursor: 'turn-failed:7',
    turnId: 'turn-failed',
    code: 'DREAM_AGENT_TURN_FAILED',
  });
  expect(cancelled).toEqual({
    type: 'agent_turn_cancelled',
    cursor: 'turn-cancelled:8',
    turnId: 'turn-cancelled',
  });
  expect(leaked).toEqual({
    type: 'agent_turn_failed',
    cursor: 'turn-failed:9',
    turnId: 'turn-failed',
    code: 'DREAM_AGENT_TURN_FAILED',
  });
  expect(JSON.stringify(leaked)).not.toContain('provider-secret');
  expect(JSON.stringify(leaked)).not.toContain('/private/path');
});

test('failed terminal de-duplicates by cursor and reconciles transient output', () => {
  const terminal = storyWorkspaceParseDreamAgentEvent(
    'agent_turn_failed',
    JSON.stringify({ turnId: 'turn-1', code: 'DREAM_AGENT_TURN_FAILED' }),
    'turn-1:failure',
  );
  expect(terminal).not.toBeNull();
  const reduced = storyWorkspaceReduceDreamAgentEvents({
    snapshot: storyWorkspaceParseDreamAgentSnapshot({
      ...SNAPSHOT,
      lifecycle: 'streaming',
      activeTurnId: 'turn-1',
      canSend: false,
      sendBlockReason: 'generating',
    }),
    streamText: 'partial',
    streamTurnId: 'turn-1',
    seenCursors: [],
  }, [terminal!, terminal!]);

  expect(reduced.shouldReconcile).toBe(true);
  expect(reduced.streamText).toBe('');
  expect(reduced.streamTurnId).toBeNull();
  expect(reduced.seenCursors).toEqual(['turn-1:failure']);
});

test('send payload has only text and idempotency key and is bound by run path', () => {
  expect(storyWorkspaceBuildDreamAgentSendPayload(RUN_ID, '  保持雨夜氛围  ', 'key-1')).toEqual({
    endpoint: `/api/story-workspace/workflow-runs/${RUN_ID}/dream-agent/messages`,
    body: { text: '保持雨夜氛围', idempotencyKey: 'key-1' },
  });
  expect(storyWorkspaceBuildDreamAgentSendPayload(RUN_ID, ' ', 'key-1')).toBeNull();
});

test('SSE stream is fetched with the authenticated transport and terminal reconcile waits for durable assistant history', async () => {
  const calls: RequestInit[] = [];
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(
        'id: turn-1:1\nevent: assistant_text_delta\ndata: {"turnId":"turn-1","delta":"第一段"}\n\n'
        + 'id: turn-1:2\nevent: assistant_message_committed\ndata: {"turnId":"turn-1"}\n\n',
      ));
      controller.close();
    },
  });
  const events = await storyWorkspaceReadDreamAgentEventStream(RUN_ID, {
    token: 'token-1',
    endpoint: '/api/test-dream-events',
    fetchImpl: (async (_url: unknown, init?: RequestInit) => {
      calls.push(init ?? {});
      return new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
    }) as unknown as typeof fetch,
  });
  expect(calls[0]?.credentials).toBe('include');
  expect(new Headers(calls[0]?.headers).get('Authorization')).toBe('Bearer token-1');
  expect(events.map((event) => event.type)).toEqual(['assistant_text_delta', 'assistant_message_committed']);
});

test('unread state is view-local: opening reads the current assistant history while a later stream becomes unread', () => {
  const messages = storyWorkspaceParseDreamAgentSnapshot({ ...SNAPSHOT, lifecycle: 'idle', activeTurnId: null, messages: [
    ...SNAPSHOT.messages,
    { id: 'm2', role: 'assistant', text: '第二条。', truncated: false, createdAt: '2026-08-05T00:01:00Z' },
  ] }).messages;
  expect(storyWorkspaceComputeDreamAgentUnreadCount(messages, 'm2', null, null, '')).toBe(0);
  expect(storyWorkspaceComputeDreamAgentUnreadCount(messages, 'm2', 'turn-2', null, '新输出')).toBe(1);
});

test('terminal state keeps cursor evidence while requesting a durable snapshot reconciliation', () => {
  const snapshot = storyWorkspaceParseDreamAgentSnapshot(SNAPSHOT);
  const terminal = storyWorkspaceReduceDreamAgentEvents({
    snapshot, streamText: '尚未持久化', streamTurnId: 'turn-1', seenCursors: ['turn-1:1'], shouldReconcile: false,
  }, [{ type: 'assistant_message_committed', turnId: 'turn-1' }]);
  expect(terminal.shouldReconcile).toBe(true);
  expect(terminal.seenCursors).toEqual(['turn-1:1']);
});

test('reconnect reconciles a snapshot then re-subscribes after cursor A, de-duplicating replay A and retaining B', async () => {
  const calls: string[] = [];
  const snapshot = storyWorkspaceParseDreamAgentSnapshot({ ...SNAPSHOT, activeTurnId: 'turn-1' });
  const fetchImpl = (async (url: unknown, init?: RequestInit) => {
    const endpoint = String(url);
    calls.push(endpoint);
    const accept = new Headers(init?.headers).get('Accept');
    if (accept === 'application/json') {
      return new Response(JSON.stringify({ ...SNAPSHOT, snapshotAt: '2026-08-05T00:00:02Z' }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    }
    const isReconnect = endpoint.includes('after=turn-1%3A1');
    const frames = isReconnect
      ? 'id: turn-1:1\nevent: assistant_text_delta\ndata: {"turnId":"turn-1","delta":"A"}\n\n'
        + 'id: turn-1:2\nevent: assistant_text_delta\ndata: {"turnId":"turn-1","delta":"B"}\n\n'
      : 'id: turn-1:1\nevent: assistant_text_delta\ndata: {"turnId":"turn-1","delta":"A"}\n\n';
    return new Response(frames, { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
  }) as unknown as typeof fetch;

  const first = await storyWorkspaceReadDreamAgentEventStream(RUN_ID, {
    endpoint: '/api/test-dream-events', fetchImpl, token: 'token-1',
  });
  expect(first.map((event) => event.type)).toEqual(['assistant_text_delta']);
  const firstCursor = (first[0] as Extract<typeof first[number], { type: 'assistant_text_delta' }>).cursor;
  expect(firstCursor).toBe('turn-1:1');

  const reconciled = await storyWorkspaceFetchDreamAgentSnapshot(RUN_ID, {
    endpoint: '/api/test-dream-snapshot', fetchImpl, token: 'token-1',
  });
  expect(reconciled.snapshotAt).toBe('2026-08-05T00:00:02Z');

  const replay = await storyWorkspaceReadDreamAgentEventStream(RUN_ID, {
    endpoint: storyWorkspaceDreamAgentEventsEndpoint(RUN_ID, firstCursor),
    after: firstCursor,
    fetchImpl,
    token: 'token-1',
  });
  expect(calls.at(-1)).toContain('after=turn-1%3A1');
  const reduced = storyWorkspaceReduceDreamAgentEvents(
    storyWorkspaceReduceDreamAgentEvents({ snapshot, streamText: '', streamTurnId: null, seenCursors: [] }, first),
    replay,
  );
  expect(reduced.streamText).toBe('AB');
  expect(reduced.seenCursors).toEqual(['turn-1:1', 'turn-1:2']);
  expect(replay.at(-1)).toMatchObject({ type: 'assistant_text_delta', cursor: 'turn-1:2', delta: 'B' });
});
