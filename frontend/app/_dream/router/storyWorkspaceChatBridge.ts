// [Input] The active Story Workspace route, its actor-scoped Dream run, and a
//         requested destination route.
// [Output] The trusted source Chat thread to reopen when Dream navigates to
//          /story-workspace/chat, or null when no Dream handoff applies.
// [Pos] Pure Dream -> Chat navigation bridge; protocol handling stays in Chat.

import type { WorkflowRun } from '../api/storyWorkspaceApi';
import {
  storyWorkspaceDreamStageForRoute,
  type StoryWorkspaceRoute,
  type StoryWorkspaceRouteMatch,
} from './storyWorkspacePath';

function isDreamSurface(match: StoryWorkspaceRouteMatch): boolean {
  return match.route === 'dream'
    || match.route === 'episode-review'
    || storyWorkspaceDreamStageForRoute(match) !== null;
}

/**
 * Preserve the run's original Chat thread when the user leaves a Dream
 * surface through the Story Workspace Chat navigation item. The run has
 * already been resolved through the actor-scoped API; the Chat endpoints
 * repeat ownership checks before returning history, status, or SSE.
 */
export function storyWorkspaceDreamChatThread(
  activeMatch: StoryWorkspaceRouteMatch,
  destinationRoute: StoryWorkspaceRoute,
  run: Pick<WorkflowRun, 'source_voice_thread_id'> | null | undefined,
): string | null {
  if (destinationRoute !== 'chat' || !isDreamSurface(activeMatch)) return null;
  const threadId = run?.source_voice_thread_id;
  return typeof threadId === 'string' && threadId.trim() ? threadId.trim() : null;
}
