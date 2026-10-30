// [Sync] 2026-10-29: own original Deck color metadata for Web/native editor options; values and labels remain unchanged.
// [Input] Deck management interaction contract.
// [Output] Central UI policy values for Deck launch limits, list pagination, and original create defaults.
// [Pos] Deck presentation constants node in frontend/app/_dream/constants.
// [Sync] 2026-08-16: centralize list size, the fourteen-item enabled launch projection,
//                    and the original create-then-popup visual defaults.

export const DECK_ENABLED_LAUNCH_LIMIT = 14;
export const DECK_MANAGEMENT_PAGE_SIZE = 10;
export const DECK_RELATED_THREADS_PAGE_SIZE = 20;

export const DEFAULT_DECK_CREATE_VISUAL = Object.freeze({
  icon: 'brain',
  color: 'blue',
});

export const DECK_COLORS = {
  'blue': { hex: 'var(--color-action-link)', label: 'Blue' },
  'purple': { hex: 'var(--color-voice-purple)', label: 'Purple' },
  'pink': { hex: 'var(--color-voice-pink)', label: 'Pink' },
  'green': { hex: 'var(--color-voice-green)', label: 'Green' },
  'yellow': { hex: 'var(--color-state-warning)', label: 'Yellow' }
};
