// [Input] Current focus position within the narrow Dream Agent dialog.
// [Output] Boundary-only tab wrapping; ordinary tab order stays native.
// [Pos] Pure accessibility seam for StoryWorkspaceDreamAgentDialog.

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
