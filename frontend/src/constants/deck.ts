// [Input] Deck management interaction contract.
// [Output] Central UI policy values for Deck launch limits, list pagination, and original create defaults.
// [Pos] Deck presentation constants node in frontend/src/constants.
// [Sync] 2026-08-16: centralize list size, the fourteen-item enabled launch projection,
//                    and the original create-then-popup visual defaults.

export const DECK_ENABLED_LAUNCH_LIMIT = 14;
export const DECK_MANAGEMENT_PAGE_SIZE = 10;

export const DEFAULT_DECK_CREATE_VISUAL = Object.freeze({
  icon: 'brain',
  color: 'blue',
});
