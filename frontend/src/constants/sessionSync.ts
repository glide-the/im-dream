// [Input] Edit Session event-driven sync design.
// [Output] Centralized frontend timing values for session event reconnect/fallback.
// [Pos] edit-session sync constants in frontend/src/constants
// [Sync] 2026-06-14: add source-of-truth timings for Agent MCP write event sync.

export const SESSION_EVENT_RECONNECT_DELAY_MS = 1500;
export const EDITOR_WRITE_EVENT_FALLBACK_TIMEOUT_MS = 10_000;
export const EDITOR_WRITE_COMPLETED_TOOL_CACHE_MS = 60_000;
