// [Input] Synthetic Dream confirmation commands/responses and chat metadata.
// [Output] Node-side contracts for the single-confirmation transport and hidden rows.
// [Pos] story-workspace Dream confirmation test node (Task 3 F3)

import { expect, test } from '@playwright/test';
import {
  storyWorkspaceDreamConfirmationEndpoint,
  storyWorkspaceNewDreamConfirmationIdempotencyKey,
  storyWorkspaceParseDreamConfirmationAccepted,
  storyWorkspaceSubmitDreamConfirmation,
} from '../useStoryWorkspaceDreamConfirmation';
import {
  filterStoryWorkspaceControlMessages,
  isStoryWorkspaceDreamConfirmationMetadata,
} from '../../../lib/story-workspace-guidance';

const RUN_ID = `run_${'1'.repeat(32)}`;
const command = {
  storyWorkspaceRunId: RUN_ID,
  threadId: 'thread-1',
  baseRevisions: { characters: 2, scenes: 1, storyboards: 3 },
  edits: [{
    stage: 'characters' as const,
    entityId: 'lead',
    fields: { summary: '新的摘要' },
  }],
  idempotencyKey: 'swc_test-1',
};

test('builds the run-scoped confirmation endpoint and swc idempotency keys', () => {
  expect(storyWorkspaceDreamConfirmationEndpoint(RUN_ID)).toBe(
    `/api/story-workspace/workflow-runs/${RUN_ID}/dream-confirmation`,
  );
  expect(storyWorkspaceDreamConfirmationEndpoint('run/a?b')).toContain('run%2Fa%3Fb');
  expect(storyWorkspaceNewDreamConfirmationIdempotencyKey(() => 'uuid-1'))
    .toBe('swc_uuid-1');
});

test('submits exactly one camelCase command and parses the 202 response', async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const responsePayload = {
    messageId: 'dream_confirm_hash',
    storyWorkspaceRunId: RUN_ID,
    threadId: 'thread-1',
    status: 'accepted',
    replayed: false,
    dispatched: true,
    requestId: 'request-1',
  };
  const fetchImpl = (async (url: unknown, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify(responsePayload), {
      status: 202,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as unknown as typeof fetch;

  const accepted = await storyWorkspaceSubmitDreamConfirmation(RUN_ID, command, {
    fetchImpl,
    token: 'token-1',
  });
  expect(accepted).toEqual(responsePayload);
  expect(JSON.parse(String(calls[0].init?.body))).toEqual(command);
  expect(calls[0].init?.method).toBe('POST');
  expect(new Headers(calls[0].init?.headers).get('Authorization')).toBe('Bearer token-1');
});

test('rejects URL/body drift, non-202 responses, and malformed accepted payloads', async () => {
  await expect(storyWorkspaceSubmitDreamConfirmation(
    `run_${'2'.repeat(32)}`,
    command,
    { fetchImpl: (() => { throw new Error('must not call'); }) as unknown as typeof fetch },
  )).rejects.toThrow();

  await expect(storyWorkspaceSubmitDreamConfirmation(RUN_ID, command, {
    fetchImpl: (async () => new Response('{}', { status: 409 })) as unknown as typeof fetch,
  })).rejects.toThrow();
  expect(() => storyWorkspaceParseDreamConfirmationAccepted({
    messageId: 'm1',
    storyWorkspaceRunId: RUN_ID,
    threadId: 'thread-1',
    status: 'failed',
    replayed: false,
    dispatched: false,
    requestId: 'r1',
  })).toThrow();
});

test('Dream confirmation rows are hidden together with guidance rows', () => {
  expect(isStoryWorkspaceDreamConfirmationMetadata({
    kind: 'story-workspace-dream-confirmation',
    story_workspace_run_id: RUN_ID,
  })).toBe(true);
  expect(isStoryWorkspaceDreamConfirmationMetadata({ kind: 'story-workspace-guidance' }))
    .toBe(false);

  const visible = filterStoryWorkspaceControlMessages([
    { id: 'normal', metadata: null },
    { id: 'dream', metadata: { kind: 'story-workspace-dream-confirmation' } },
    { id: 'guidance', metadata: { kind: 'story-workspace-guidance' } },
  ]);
  expect(visible.map((message) => message.id)).toEqual(['normal']);
});
