// [Input] Chat message metadata carried on UIMessage / RawChatMessage rows.
// [Output] Predicate + list filter hiding story-workspace guidance rows from
//          every Chat rendering surface (DEC-032: guidance persists in
//          chat_message with metadata.kind="story-workspace-guidance" but must
//          never appear as a Chat bubble).
// [Pos] story-workspace guidance filter seam (Task 4 Step 0)
// [Sync] 2026-08-04: initial implementation; consumed by ChatView message
//                    loading and ChatPanel rendering/export seams.

export const STORY_WORKSPACE_GUIDANCE_KIND = 'story-workspace-guidance';

/**
 * True when a message metadata payload marks a story-workspace guidance row
 * persisted by POST /api/story-workspace/runs/{run_id}/guidance (Task 3).
 */
export function isStoryWorkspaceGuidanceMetadata(metadata: unknown): boolean {
  if (typeof metadata !== 'object' || metadata === null) return false;
  return (metadata as Record<string, unknown>).kind === STORY_WORKSPACE_GUIDANCE_KIND;
}

/**
 * Remove guidance rows from a message list, preserving order and the input
 * array. Applied at every Chat consumption seam (history load, live render,
 * share/export snapshot).
 */
export function filterStoryWorkspaceGuidanceMessages<T extends { metadata?: unknown }>(
  messages: readonly T[],
): T[] {
  return messages.filter((message) => !isStoryWorkspaceGuidanceMetadata(message.metadata));
}
