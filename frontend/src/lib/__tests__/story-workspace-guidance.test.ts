// [Input] Shared Chat message metadata and Dream business rows.
// [Output] Pass-through and classification coverage without body filtering.
// [Pos] Story Workspace compatibility seam; not a visibility reducer.

import { expect, test } from '@playwright/test';
import {
  filterStoryWorkspaceControlMessages,
  filterStoryWorkspaceGuidanceMessages,
  isStoryWorkspaceDreamConfirmationMetadata,
  isStoryWorkspaceGuidanceMetadata,
  isSystemHiddenMessageMetadata,
  STORY_WORKSPACE_DREAM_CONFIRMATION_KIND,
  STORY_WORKSPACE_GUIDANCE_KIND,
  SYSTEM_HIDDEN_MESSAGE_VISIBILITY,
} from '../story-workspace-guidance';

test('classifies only the explicit guidance, confirmation and legacy visibility markers', () => {
  expect(isStoryWorkspaceGuidanceMetadata({ kind: STORY_WORKSPACE_GUIDANCE_KIND })).toBe(true);
  expect(isStoryWorkspaceDreamConfirmationMetadata({
    kind: STORY_WORKSPACE_DREAM_CONFIRMATION_KIND,
  })).toBe(true);
  expect(isSystemHiddenMessageMetadata({ visibility: SYSTEM_HIDDEN_MESSAGE_VISIBILITY })).toBe(true);
  expect(isStoryWorkspaceGuidanceMetadata({ kind: 'other' })).toBe(false);
  expect(isStoryWorkspaceDreamConfirmationMetadata(null)).toBe(false);
});

test('shared Chat compatibility seams preserve every user and JSON control row', () => {
  const messages = [
    { id: 'normal', metadata: undefined },
    { id: 'guidance', metadata: { kind: STORY_WORKSPACE_GUIDANCE_KIND } },
    {
      id: 'legacy-hidden',
      metadata: { visibility: SYSTEM_HIDDEN_MESSAGE_VISIBILITY },
      parts: [{ type: 'text', text: '{"action":"confirm_and_continue"}' }],
    },
  ];
  expect(filterStoryWorkspaceControlMessages(messages)).toEqual(messages);
  expect(filterStoryWorkspaceGuidanceMessages(messages)).toEqual(messages);
});
