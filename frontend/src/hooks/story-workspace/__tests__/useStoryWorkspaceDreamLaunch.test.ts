// [Input] Synthetic Dream launch commands, HTTP responses, and concurrent clicks.
// [Output] Node-side coverage for Dream's dedicated start transport and in-flight seam.
// [Pos] Story Workspace Dream launch hook contract test node (Task 3 U4)

import { expect, test } from '@playwright/test';
import {
  storyWorkspaceDreamLaunchEndpoint,
  storyWorkspaceParseDreamLaunchAccepted,
  storyWorkspaceStartDreamRun,
} from '../../../api/storyWorkspaceApi';
import {
  createStoryWorkspaceDreamLauncher,
  storyWorkspaceDreamRunPath,
} from '../useStoryWorkspaceDreamLaunch';

const RUN_ID = `run_${'a'.repeat(32)}`;

test('posts only the three public camelCase launch fields', async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const fetchImpl = (async (url: unknown, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({
      workflowRunId: RUN_ID,
      threadId: 'thread-1',
    }), { status: 201, headers: { 'Content-Type': 'application/json' } });
  }) as unknown as typeof fetch;

  const accepted = await storyWorkspaceStartDreamRun({
    deckId: 'deck-1',
    goal: '雨夜车站的重逢',
    idempotencyKey: 'dream_test-1',
  }, { endpoint: storyWorkspaceDreamLaunchEndpoint, fetchImpl, token: 'token-1' });

  expect(accepted).toEqual({ workflowRunId: RUN_ID, threadId: 'thread-1' });
  expect(calls).toHaveLength(1);
  expect(calls[0].url).toBe(storyWorkspaceDreamLaunchEndpoint);
  expect(calls[0].init?.method).toBe('POST');
  expect(calls[0].init?.credentials).toBe('include');
  expect(new Headers(calls[0].init?.headers).get('Authorization')).toBe('Bearer token-1');
  expect(JSON.parse(String(calls[0].init?.body))).toEqual({
    deckId: 'deck-1',
    goal: '雨夜车站的重逢',
    idempotencyKey: 'dream_test-1',
  });
});

test('strictly parses canonical launch context with camelCase or snake_case ids', () => {
  expect(storyWorkspaceParseDreamLaunchAccepted({
    workflowRunId: RUN_ID,
    threadId: 'thread-1',
  })).toEqual({ workflowRunId: RUN_ID, threadId: 'thread-1' });
  expect(storyWorkspaceParseDreamLaunchAccepted({
    workflow_run_id: RUN_ID,
    thread_id: 'thread-1',
  })).toEqual({ workflowRunId: RUN_ID, threadId: 'thread-1' });

  expect(() => storyWorkspaceParseDreamLaunchAccepted({ threadId: 'thread-1' })).toThrow();
  expect(() => storyWorkspaceParseDreamLaunchAccepted({
    workflowRunId: RUN_ID,
    workflow_run_id: `run_${'b'.repeat(32)}`,
    threadId: 'thread-1',
  })).toThrow();
});

test('shares one in-flight launch and navigates with the accepted run id', async () => {
  let resolveRequest: (value: { workflowRunId: string; threadId: string }) => void = () => {
    throw new Error('transport was not called');
  };
  const commands: unknown[] = [];
  const transport = (command: unknown) => {
    commands.push(command);
    return new Promise<{ workflowRunId: string; threadId: string }>((resolve) => {
      resolveRequest = resolve;
    });
  };
  const launcher = createStoryWorkspaceDreamLauncher(
    transport,
    () => 'dream_uuid-1',
  );

  const first = launcher.start('deck-1', '  雨夜车站  ');
  const second = launcher.start('deck-1', '被忽略的双击');

  expect(first).toBe(second);
  expect(commands).toEqual([{
    deckId: 'deck-1',
    goal: '雨夜车站',
    idempotencyKey: 'dream_uuid-1',
  }]);

  resolveRequest({ workflowRunId: RUN_ID, threadId: 'thread-1' });
  await expect(first).resolves.toMatchObject({ workflowRunId: RUN_ID });
  expect(storyWorkspaceDreamRunPath(RUN_ID)).toBe(
    `/story-workspace/dream?run=${encodeURIComponent(RUN_ID)}`,
  );
});

test('rejects non-201 and malformed launch responses', async () => {
  await expect(storyWorkspaceStartDreamRun({
    deckId: 'deck-1',
    goal: '目标',
    idempotencyKey: 'dream_test-2',
  }, {
    fetchImpl: (async () => new Response('{}', { status: 409 })) as unknown as typeof fetch,
  })).rejects.toThrow();

  await expect(storyWorkspaceStartDreamRun({
    deckId: 'deck-1',
    goal: '目标',
    idempotencyKey: 'dream_test-3',
  }, {
    fetchImpl: (async () => new Response('{}', { status: 201 })) as unknown as typeof fetch,
  })).rejects.toThrow();
});
