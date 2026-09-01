// [Input] Public React hook modules owned by frontend/src/hooks.
// [Output] Stable barrel exports for editor/session/interaction hooks.
// [Pos] Hook package entrypoint.
// [Sync] 2026-09-01: replace the retired automatic inspiration export with the manual Writing suggestion controller.

export { useSessionLifecycle } from './useSessionLifecycle';
export { useWritingSuggestions } from './useWritingSuggestions';
export { useComments } from './useComments';
export { useTextCells } from './useTextCells';
export type { UseTextCellsOptions, UseTextCellsReturn } from './useTextCells';
export { useVoiceInput } from './useVoiceInput';
export type { UseVoiceInputOptions, UseVoiceInputReturn } from './useVoiceInput';
export { useCopy } from './useCopy';
export { useDebounce } from './useDebounce';
export { useFileUpload } from './useFileUpload';
