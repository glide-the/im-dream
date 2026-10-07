// [Input] Existing browser storage keys and App's login/local-import cleanup boundaries.
// [Output] Central storage registry and explicit cleanup list that preserves browser display preferences.
// [Pos] Frontend storage-key and local-data cleanup policy owner.
// [Sync] 2026-10-07: exclude language/theme from completed-login, migration and skip cleanup.
/**
 * Storage keys constants
 *
 * Single source of truth for localStorage keys used across the application.
 * Using const assertion for type safety and autocomplete.
 */

// [Sync] 2026-07-04: add resource connector storage key for frontend fallback state.

export const STORAGE_KEYS = {
  // Auth
  AUTH_TOKEN: 'auth_token',
  MIGRATION_COMPLETED: 'migration_completed',

  // Editor State
  EDITOR_STATE: 'ink_memory_state',
  SELECTED_STATE: 'selected-state',

  // Voice Configuration
  VOICE_CONFIGS: 'voice-configs',
  META_PROMPT: 'meta-prompt',
  STATE_CONFIG: 'state-config',

  // Calendar & Pictures
  CALENDAR_ENTRIES: 'calendarEntries',
  DAILY_PICTURES: 'daily-pictures',
  SELECTED_FRIEND: 'ink-selected-friend',
  RECENT_FRIENDS: 'ink-recent-friends',
  RESOURCE_CONNECTORS: 'ink-resource-connectors',

  // Analysis
  ANALYSIS_REPORTS: 'analysisReports',
  REFLECTIONS_ANALYSIS_CLICKED_DATE: 'reflections-analysis-clicked-date',
  REFLECTIONS_ACTIVE_TASK: 'reflections-active-task',

  // Language
  LANGUAGE: 'ink-language',

  // Theme
  THEME: 'ink-theme'
} as const;

// Existing account/import data and retired credentials cleared by App after completed login/import.
// Browser display preferences are deliberately absent; new keys require an explicit cleanup decision.
export const LOCAL_IMPORT_CLEANUP_KEYS = [
  STORAGE_KEYS.AUTH_TOKEN,
  STORAGE_KEYS.MIGRATION_COMPLETED,
  STORAGE_KEYS.EDITOR_STATE,
  STORAGE_KEYS.SELECTED_STATE,
  STORAGE_KEYS.VOICE_CONFIGS,
  STORAGE_KEYS.META_PROMPT,
  STORAGE_KEYS.STATE_CONFIG,
  STORAGE_KEYS.CALENDAR_ENTRIES,
  STORAGE_KEYS.DAILY_PICTURES,
  STORAGE_KEYS.SELECTED_FRIEND,
  STORAGE_KEYS.RECENT_FRIENDS,
  STORAGE_KEYS.RESOURCE_CONNECTORS,
  STORAGE_KEYS.ANALYSIS_REPORTS,
  STORAGE_KEYS.REFLECTIONS_ANALYSIS_CLICKED_DATE,
  STORAGE_KEYS.REFLECTIONS_ACTIVE_TASK,
] as const;

// Type for autocomplete
export type StorageKey = typeof STORAGE_KEYS[keyof typeof STORAGE_KEYS];
