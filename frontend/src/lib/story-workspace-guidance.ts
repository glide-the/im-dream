// [Input] Chat message metadata carried on UIMessage / RawChatMessage rows.
// [Output] Metadata predicates plus a compatibility pass-through preserving
//          every Dream business row in shared Chat history and live rendering.
// [Pos] Story Workspace message classification seam; not a visibility filter.
// [Sync] 2026-08-04: initial implementation; consumed by ChatView message
//                    loading and ChatPanel rendering/export seams.
// [Sync] 2026-08-04: hide the one Dream confirmation command through the same seam.
// [Sync] 2026-08-13: remove Dream body filtering; control JSON and user rows are
//                    visible in both Chat and Dream through the shared thread.

export const STORY_WORKSPACE_GUIDANCE_KIND = 'story-workspace-guidance';
export const STORY_WORKSPACE_DREAM_CONFIRMATION_KIND = 'story-workspace-dream-confirmation';
export const STORY_WORKSPACE_DREAM_AGENT_USER_KIND = 'story-workspace-dream-agent-user';
export const STORY_WORKSPACE_EPISODE_ACTION_SCHEMA = 'story-workspace-episode-action/v1';
export const SYSTEM_HIDDEN_MESSAGE_VISIBILITY = 'system-hidden';

/** Identify the legacy server-attested visibility marker without hiding it. */
export function isSystemHiddenMessageMetadata(metadata: unknown): boolean {
  if (typeof metadata !== 'object' || metadata === null) return false;
  return (metadata as Record<string, unknown>).visibility
    === SYSTEM_HIDDEN_MESSAGE_VISIBILITY;
}

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

/**
 * Compatibility seam retained for callers while Dream adopts the exact shared
 * Chat transcript.  No Dream business row is removed here: launch, guidance,
 * confirmation, episode action and human messages all remain user-visible.
 */
export function filterStoryWorkspaceControlMessages<T extends { metadata?: unknown }>(
  messages: readonly T[],
): T[] {
  return [...messages];
}

/**
 * Historical name retained while callers migrate. It preserves every row and
 * returns a new array so existing consumption semantics remain stable.
 */
export function filterStoryWorkspaceGuidanceMessages<T extends { metadata?: unknown }>(
  messages: readonly T[],
): T[] {
  return filterStoryWorkspaceControlMessages(messages);
}
