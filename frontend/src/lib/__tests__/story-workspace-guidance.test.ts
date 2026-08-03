// [Input] Synthetic chat message metadata shapes (Playwright node-side runner).
// [Output] Contract tests for the story-workspace guidance filter: DEC-032
//          requires guidance rows (metadata.kind="story-workspace-guidance")
//          to persist in chat_message yet never render as Chat bubbles.
// [Pos] story-workspace guidance filter test node (Task 4 Step 0)
// [Sync] 2026-08-04: initial coverage - predicate + list filter semantics.

import { expect, test } from '@playwright/test';
import {
  filterStoryWorkspaceGuidanceMessages,
  isStoryWorkspaceGuidanceMetadata,
  STORY_WORKSPACE_GUIDANCE_KIND,
} from '../story-workspace-guidance';

test('kind constant matches the Task 3 persistence marker', () => {
  expect(STORY_WORKSPACE_GUIDANCE_KIND).toBe('story-workspace-guidance');
});

test('recognizes guidance metadata including full audit fields', () => {
  expect(isStoryWorkspaceGuidanceMetadata({
    kind: 'story-workspace-guidance',
    story_workspace_run_id: 'run_abc',
    actor: '11',
    request_id: 'req-1',
    idempotency_key: 'k-1',
    command_kind: 'free-text',
    text_summary: '第二集节奏放慢',
    review_action: 'guide',
  })).toBe(true);
});

test('rejects non-guidance and malformed metadata shapes', () => {
  expect(isStoryWorkspaceGuidanceMetadata(undefined)).toBe(false);
  expect(isStoryWorkspaceGuidanceMetadata(null)).toBe(false);
  expect(isStoryWorkspaceGuidanceMetadata('story-workspace-guidance')).toBe(false);
  expect(isStoryWorkspaceGuidanceMetadata({})).toBe(false);
  expect(isStoryWorkspaceGuidanceMetadata({ kind: 'story-workspace-output' })).toBe(false);
  expect(isStoryWorkspaceGuidanceMetadata({ kind: 42 })).toBe(false);
});

test('filter drops guidance rows and keeps every other message in order', () => {
  const messages = [
    { id: 'm1', role: 'user', metadata: undefined },
    { id: 'guide_k-1', role: 'user', metadata: { kind: 'story-workspace-guidance', actor: '11' } },
    { id: 'm2', role: 'assistant', metadata: { kind: 'other' } },
    { id: 'm3', role: 'assistant' },
    { id: 'guide_k-2', role: 'user', metadata: { kind: 'story-workspace-guidance' } },
  ];

  const visible = filterStoryWorkspaceGuidanceMessages(messages);
  expect(visible.map((message) => message.id)).toEqual(['m1', 'm2', 'm3']);
});

test('filter preserves the input array and handles empty lists', () => {
  const messages = [{ id: 'm1', metadata: { kind: 'story-workspace-guidance' } }];
  const visible = filterStoryWorkspaceGuidanceMessages(messages);
  expect(visible).toEqual([]);
  expect(messages).toHaveLength(1);
  expect(filterStoryWorkspaceGuidanceMessages([])).toEqual([]);
});
