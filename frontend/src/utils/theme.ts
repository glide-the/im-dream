// [Input] window.matchMedia for system preference; localStorage for persisted preference.
// [Output] Theme token ('light' | 'dark') applied as data-theme on <html>, persisted to localStorage.
// [Pos] theme utility in frontend/src/utils
// [Sync] 2026-05-29: created; implements initTheme / getTheme / setTheme / toggleTheme.
// [Sync] 2026-06-01: initTheme no longer persists system preference; removes data-theme when no explicit pref so CSS media query auto-follows system. Added onThemeChange() for live system updates.

import { STORAGE_KEYS } from '../constants/storageKeys';

export type Theme = 'light' | 'dark';

/** Read the active theme: explicit user preference or current system preference. */
export function getTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEYS.THEME) as Theme | null;
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/** Whether the user has explicitly chosen a theme (vs. following system). */
export function hasExplicitTheme(): boolean {
  const stored = localStorage.getItem(STORAGE_KEYS.THEME);
  return stored === 'light' || stored === 'dark';
}

/** Apply a theme to the document root and persist it as an explicit user preference. */
export function setTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(STORAGE_KEYS.THEME, theme);
}

/** Toggle between light and dark, return the new theme. */
export function toggleTheme(): Theme {
  const next = getTheme() === 'dark' ? 'light' : 'dark';
  setTheme(next);
  return next;
}

/**
 * Subscribe to effective theme changes caused by system preference changes.
 * Callback is only invoked when there is no explicit user preference in storage,
 * so the UI icon can stay in sync when following the system.
 * Returns a cleanup function to remove the listener.
 */
export function onSystemThemeChange(callback: (theme: Theme) => void): () => void {
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const handler = (e: MediaQueryListEvent) => {
    if (!hasExplicitTheme()) {
      callback(e.matches ? 'dark' : 'light');
    }
  };
  mq.addEventListener('change', handler);
  return () => mq.removeEventListener('change', handler);
}

/**
 * Call once on app start to apply the persisted theme.
 * When no explicit user preference exists, data-theme is removed so that
 * the CSS `@media (prefers-color-scheme: dark)` rule handles it automatically
 * and continues to respond to system changes in real time.
 */
export function initTheme(): void {
  const stored = localStorage.getItem(STORAGE_KEYS.THEME) as Theme | null;
  if (stored === 'light' || stored === 'dark') {
    document.documentElement.setAttribute('data-theme', stored);
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
}
