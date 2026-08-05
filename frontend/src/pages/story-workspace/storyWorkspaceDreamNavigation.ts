// [Input] Browser activation modifiers and the current History API state.
// [Output] Pure predicates for Dream's native-link-preserving return behavior.
// [Pos] Story Workspace Dream page-local navigation seam.

interface StoryWorkspaceDreamLinkActivation {
  readonly altKey: boolean;
  readonly button: number;
  readonly ctrlKey: boolean;
  readonly metaKey: boolean;
  readonly shiftKey: boolean;
}

const STORY_WORKSPACE_RETURN_KIND = 'story-workspace-push';
const STORY_WORKSPACE_RETURN_KEY = 'storyWorkspaceReturn';

interface StoryWorkspaceDreamReturnMarker {
  readonly kind: typeof STORY_WORKSPACE_RETURN_KIND;
  readonly sourceHref: string;
}

export function storyWorkspaceDreamReturnState(
  state: unknown,
  sourceHref: string | null,
): Record<string, unknown> {
  const nextState: Record<string, unknown> = state && typeof state === 'object'
    ? { ...state }
    : {};
  delete nextState[STORY_WORKSPACE_RETURN_KEY];
  if (sourceHref) {
    nextState[STORY_WORKSPACE_RETURN_KEY] = {
      kind: STORY_WORKSPACE_RETURN_KIND,
      sourceHref,
    } satisfies StoryWorkspaceDreamReturnMarker;
  }
  return nextState;
}

export function storyWorkspaceDreamIsPlainPrimaryActivation(
  event: StoryWorkspaceDreamLinkActivation,
): boolean {
  return event.button === 0
    && !event.metaKey
    && !event.ctrlKey
    && !event.shiftKey
    && !event.altKey;
}

export function storyWorkspaceDreamShouldReturnToHistory(state: unknown): boolean {
  if (!state || typeof state !== 'object') return false;
  if (!(STORY_WORKSPACE_RETURN_KEY in state)) return false;
  const marker = state[STORY_WORKSPACE_RETURN_KEY];
  if (!marker || typeof marker !== 'object') return false;
  if (!('kind' in marker) || marker.kind !== STORY_WORKSPACE_RETURN_KIND) return false;
  if (!('sourceHref' in marker) || typeof marker.sourceHref !== 'string') return false;
  return marker.sourceHref === '/story-workspace'
    || marker.sourceHref.startsWith('/story-workspace/');
}
