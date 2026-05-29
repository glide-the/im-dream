// [Input] window.matchMedia for system preference; localStorage for persisted preference.
// [Output] Theme token ('light' | 'dark') applied as data-theme on <html>, persisted to localStorage.
// [Pos] theme utility in frontend/src/utils
// [Sync] 2026-05-29: created; implements initTheme / getTheme / setTheme / toggleTheme.

const STORAGE_KEY = 'ink-theme';

export type Theme = 'light' | 'dark';

/** Read the active theme from localStorage, falling back to system preference. */
export function getTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/** Apply a theme to the document root and persist it. */
export function setTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === 'dark') {
    root.setAttribute('data-theme', 'dark');
  } else {
    root.setAttribute('data-theme', 'light');
  }
  localStorage.setItem(STORAGE_KEY, theme);
}

/** Toggle between light and dark, return the new theme. */
export function toggleTheme(): Theme {
  const next = getTheme() === 'dark' ? 'light' : 'dark';
  setTheme(next);
  return next;
}

/** Call once on app start to apply the persisted / system-preferred theme. */
export function initTheme(): void {
  setTheme(getTheme());
}
