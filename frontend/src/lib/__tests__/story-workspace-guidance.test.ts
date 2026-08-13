// [Input] Synthetic chat message metadata shapes (Playwright node-side runner).
// [Output] Contract tests proving Dream business rows persist and render in the
//          exact shared Chat transcript without a frontend visibility filter.
// [Pos] Story Workspace message classification/pass-through contract tests.
// [Sync] 2026-08-04: initial coverage - predicate + list filter semantics.

import { expect, test } from '@playwright/test';
import {
  filterStoryWorkspaceGuidanceMessages,
  isSystemHiddenMessageMetadata,
  isStoryWorkspacePrivateEpisodeActionMetadata,
  isStoryWorkspaceGuidanceMetadata,
  STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
  STORY_WORKSPACE_EPISODE_ACTION_SCHEMA,
  STORY_WORKSPACE_GUIDANCE_KIND,
  SYSTEM_HIDDEN_MESSAGE_VISIBILITY,
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

test('recognizes only the explicit system-hidden visibility marker', () => {
  expect(isSystemHiddenMessageMetadata({
    kind: STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
    visibility: SYSTEM_HIDDEN_MESSAGE_VISIBILITY,
  })).toBe(true);
  expect(isSystemHiddenMessageMetadata({ visibility: 'public' })).toBe(false);
  expect(isSystemHiddenMessageMetadata(null)).toBe(false);
});

test('Chat compatibility seam preserves every Dream business row', () => {
  const messages = [
    { id: 'm1', role: 'user', metadata: undefined },
    { id: 'guide_k-1', role: 'user', metadata: { kind: 'story-workspace-guidance', actor: '11' } },
    { id: 'm2', role: 'assistant', metadata: { kind: 'other' } },
    { id: 'dream_k-1', role: 'user', metadata: { kind: 'story-workspace-dream-confirmation' } },
    {
      id: 'dream_launch_goal',
      role: 'user',
      metadata: {
        kind: STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        visibility: SYSTEM_HIDDEN_MESSAGE_VISIBILITY,
      },
    },
    {
      id: 'dream_agent_private',
      role: 'user',
      metadata: {
        kind: STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        story_workspace_episode_action: {
          schema: STORY_WORKSPACE_EPISODE_ACTION_SCHEMA,
          action: 'review_script',
        },
      },
    },
    {
      id: 'dream_agent_human',
      role: 'user',
      metadata: { kind: STORY_WORKSPACE_DREAM_AGENT_USER_KIND },
    },
    {
      id: 'dream_json_control',
      role: 'user',
      parts: [{
        type: 'text',
        text: '{"action":"confirm_and_continue","run":"run_abc"}',
      }],
      metadata: {
        kind: 'story-workspace-dream-confirmation',
        visibility: SYSTEM_HIDDEN_MESSAGE_VISIBILITY,
      },
    },
    { id: 'm3', role: 'assistant' },
    { id: 'guide_k-2', role: 'user', metadata: { kind: 'story-workspace-guidance' } },
  ];

  const visible = filterStoryWorkspaceGuidanceMessages(messages);
  expect(visible.map((message) => message.id)).toEqual([
    'm1',
    'guide_k-1',
    'm2',
    'dream_k-1',
    'dream_launch_goal',
    'dream_agent_private',
    'dream_agent_human',
    'dream_json_control',
    'm3',
    'guide_k-2',
  ]);
  expect(visible.find((message) => message.id === 'dream_json_control')?.parts).toEqual([{
    type: 'text',
    text: '{"action":"confirm_and_continue","run":"run_abc"}',
  }]);
});

test('recognizes only server-attested private episode actions', () => {
  expect(isStoryWorkspacePrivateEpisodeActionMetadata({
    kind: STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
    story_workspace_episode_action: {
      schema: STORY_WORKSPACE_EPISODE_ACTION_SCHEMA,
    },
  })).toBe(true);
  expect(isStoryWorkspacePrivateEpisodeActionMetadata({
    kind: STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
  })).toBe(false);
  expect(isStoryWorkspacePrivateEpisodeActionMetadata({
    kind: STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
    story_workspace_episode_action: { schema: 'untrusted/v1' },
  })).toBe(false);
});

test('filter preserves the input array and handles empty lists', () => {
  const messages = [{ id: 'm1', metadata: { kind: 'story-workspace-guidance' } }];
  const visible = filterStoryWorkspaceGuidanceMessages(messages);
  expect(visible).toEqual(messages);
  expect(visible).not.toBe(messages);
  expect(messages).toHaveLength(1);
  expect(filterStoryWorkspaceGuidanceMessages([])).toEqual([]);
});
