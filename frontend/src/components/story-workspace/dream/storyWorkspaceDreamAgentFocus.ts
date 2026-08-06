// [Input] Current focus state within a Dream Agent interaction surface.
// [Output] Boundary-only dialog wrapping and inline Panel confirmation focus decisions.
// [Pos] Pure accessibility seam shared by Dream Agent surfaces.

export type StoryWorkspaceDreamAgentPanelFocusZone =
  'composer' | 'confirmation' | 'history' | 'navigation' | 'outside';

type StoryWorkspaceDreamAgentPanelFocusTarget = 'composer' | 'confirmation' | null;

interface StoryWorkspaceDreamAgentPanelFocusState {
  readonly focusFellOut: boolean;
  readonly isOpen: boolean;
  readonly lastFocusedZone: StoryWorkspaceDreamAgentPanelFocusZone;
  readonly pendingToolCallId: string | null;
  readonly previousToolCallId: string | null;
  readonly wasOpen: boolean;
}

/** Select a Panel focus target without stealing focus from history or navigation. */
export function storyWorkspaceDreamAgentPanelFocusTarget({
  focusFellOut,
  isOpen,
  lastFocusedZone,
  pendingToolCallId,
  previousToolCallId,
  wasOpen,
}: StoryWorkspaceDreamAgentPanelFocusState): StoryWorkspaceDreamAgentPanelFocusTarget {
  if (!isOpen) return null;
  if (!pendingToolCallId) {
    if (!previousToolCallId) return null;
    return lastFocusedZone === 'composer'
      || lastFocusedZone === 'confirmation'
      || focusFellOut
      ? 'composer'
      : null;
  }
  if (!wasOpen) return 'confirmation';
  if (previousToolCallId && previousToolCallId !== pendingToolCallId) return 'confirmation';
  if (!previousToolCallId && (lastFocusedZone === 'composer' || focusFellOut)) return 'confirmation';
  return null;
}

/** Return a wrapped focus index only at the modal boundary. */
export function storyWorkspaceDreamAgentFocusCycleIndex(
  currentIndex: number,
  length: number,
  shiftKey: boolean,
): number {
  if (length <= 0) return 0;
  if (shiftKey && currentIndex === 0) return length - 1;
  if (!shiftKey && currentIndex === length - 1) return 0;
  return currentIndex;
}
