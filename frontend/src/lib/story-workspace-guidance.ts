// [Input] Chat message metadata carried on UIMessage / RawChatMessage rows.
// [Output] Predicates + list filters hiding story-workspace control rows from
//          every Chat rendering surface. Guidance and the Dream confirmation
//          persist for audit/Agent continuation but never appear as bubbles.
// [Pos] story-workspace guidance filter seam (Task 4 Step 0)
// [Sync] 2026-08-04: initial implementation; consumed by ChatView message
//                    loading and ChatPanel rendering/export seams.
// [Sync] 2026-08-04: hide the one Dream confirmation command through the same seam.
// [Sync] 2026-08-11: hide server-owned episode action envelopes while preserving
//                    human-authored Dream Agent messages in ordinary Chat history.

export const STORY_WORKSPACE_GUIDANCE_KIND = 'story-workspace-guidance';
export const STORY_WORKSPACE_DREAM_CONFIRMATION_KIND = 'story-workspace-dream-confirmation';
export const STORY_WORKSPACE_DREAM_AGENT_USER_KIND = 'story-workspace-dream-agent-user';
export const STORY_WORKSPACE_EPISODE_ACTION_SCHEMA = 'story-workspace-episode-action/v1';

/**
 * True when a message metadata payload marks a story-workspace guidance row
 * persisted by POST /api/story-workspace/runs/{run_id}/guidance (Task 3).
 */
export function isStoryWorkspaceGuidanceMetadata(metadata: unknown): boolean {
  if (typeof metadata !== 'object' || metadata === null) return false;
  return (metadata as Record<string, unknown>).kind === STORY_WORKSPACE_GUIDANCE_KIND;
}

export function isStoryWorkspaceDreamConfirmationMetadata(metadata: unknown): boolean {
  if (typeof metadata !== 'object' || metadata === null) return false;
  return (metadata as Record<string, unknown>).kind
    === STORY_WORKSPACE_DREAM_CONFIRMATION_KIND;
}

/**
 * Episode actions are server-generated private execution envelopes. They share
 * the Dream Agent user kind with human-authored workbench messages, so the
 * nested, server-attested provenance schema is the compatibility boundary.
 */
export function isStoryWorkspacePrivateEpisodeActionMetadata(metadata: unknown): boolean {
  if (typeof metadata !== 'object' || metadata === null) return false;
  const value = metadata as Record<string, unknown>;
  if (value.kind !== STORY_WORKSPACE_DREAM_AGENT_USER_KIND) return false;
  const action = value.story_workspace_episode_action;
  return typeof action === 'object'
    && action !== null
    && (action as Record<string, unknown>).schema === STORY_WORKSPACE_EPISODE_ACTION_SCHEMA;
}

/** Hide every server-owned Story Workspace command from Chat rendering. */
export function filterStoryWorkspaceControlMessages<T extends { metadata?: unknown }>(
  messages: readonly T[],
): T[] {
  return messages.filter((message) => (
    !isStoryWorkspaceGuidanceMetadata(message.metadata)
    && !isStoryWorkspaceDreamConfirmationMetadata(message.metadata)
    && !isStoryWorkspacePrivateEpisodeActionMetadata(message.metadata)
  ));
}

/**
 * Remove guidance rows from a message list, preserving order and the input
 * array. Applied at every Chat consumption seam (history load, live render,
 * share/export snapshot).
 */
export function filterStoryWorkspaceGuidanceMessages<T extends { metadata?: unknown }>(
  messages: readonly T[],
): T[] {
  return filterStoryWorkspaceControlMessages(messages);
}
