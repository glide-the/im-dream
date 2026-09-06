// [Input] Synthetic Story Workspace route matches and actor-scoped run reads.
// [Output] Regression coverage for Dream -> original Chat thread handoff.
// [Pos] Pure navigation bridge contract test.

import { expect, test } from '@playwright/test';
import { storyWorkspaceDreamChatThread } from '../storyWorkspaceChatBridge';
import { resolveStoryWorkspacePath } from '../storyWorkspacePath';

test('Dream hands its actor-scoped source thread to Chat', () => {
  const dream = resolveStoryWorkspacePath('/story-workspace/dream', '?run=run-1');
  expect(dream).not.toBeNull();
  expect(storyWorkspaceDreamChatThread(dream!, 'chat', {
    source_voice_thread_id: ' thread-dream-1 ',
  })).toBe('thread-dream-1');
});

test('non-Dream routes and non-Chat destinations do not hijack Chat selection', () => {
  const decks = resolveStoryWorkspacePath('/story-workspace/decks');
  const dream = resolveStoryWorkspacePath('/story-workspace/dream');
  expect(decks).not.toBeNull();
  expect(dream).not.toBeNull();
  expect(storyWorkspaceDreamChatThread(decks!, 'chat', {
    source_voice_thread_id: 'thread-1',
  })).toBeNull();
  expect(storyWorkspaceDreamChatThread(dream!, 'timeline', {
    source_voice_thread_id: 'thread-1',
  })).toBeNull();
  expect(storyWorkspaceDreamChatThread(dream!, 'chat', {
    source_voice_thread_id: '   ',
  })).toBeNull();
});
