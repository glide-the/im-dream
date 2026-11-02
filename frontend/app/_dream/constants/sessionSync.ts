// [Input] Edit Session event-driven sync design.
// [Output] Centralized frontend timing values for session event reconnect/fallback and auto-save debounce.
// [Pos] edit-session sync constants in frontend/app/_dream/constants
// [Sync] 2026-06-14: add source-of-truth timings for Agent MCP write event sync.
// [Sync] 2026-06-14: add source-of-truth auto-save debounce timing.
// [Sync] 2026-11-01: bound the native Writing save/context handshake without changing auto-save or Agent execution timeouts.

export const EDIT_SESSION_AUTO_SAVE_DEBOUNCE_MS = 3000;
export const SESSION_EVENT_RECONNECT_DELAY_MS = 1500;
export const EDITOR_WRITE_EVENT_FALLBACK_TIMEOUT_MS = 10_000;
export const EDITOR_WRITE_COMPLETED_TOOL_CACHE_MS = 60_000;
export const WRITING_CHAT_CONTEXT_TIMEOUT_MS = 30_000;
