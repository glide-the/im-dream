// [Sync] 2026-10-29: project the original subscription action/progress token in all three palettes.
// [Sync] 2026-10-28: project the original light/dark Memory Yellow accent for native share controls.
// [Sync] 2026-10-28: project original success and Markdown code tokens for native message presentation.
// [Input] Original tokens.css light, explicit-dark and system-dark values.
// [Output] Native semantic colors with the original CSS token names.
// [Pos] Presentation-only platform projection; Web keeps its existing stylesheet.
// [Sync] 2026-10-28: include original light/dark soft-shadow tokens for the native composer card.
// [Sync] 2026-10-28: include the original Agent palette and popup border/shadow tokens; all values remain source-checked.
export type InkThemeMode = 'light' | 'dark' | 'system';
const light = {
  'color-bg-app':'#f6efe5', 'color-bg-paper':'#fffaf2', 'color-bg-surface':'rgba(255, 250, 242, 0.9)',
  'color-bg-surface-solid':'#fffdf8', 'color-border-paper':'#d8c7b3', 'color-border-focus':'#5f4a36',
  'color-text-primary':'#3f3429', 'color-text-secondary':'#7a6a59', 'color-text-muted':'#9a8a78',
  'color-bg-hover':'rgba(95, 74, 54, 0.06)', 'color-state-error':'#a86652', 'color-action-link':'#4a90e2',
  'color-disabled-bg':'#d6cbbb','color-state-danger':'#b35f50','color-text-on-action':'#ffffff',
  'color-shadow-soft':'rgba(91, 69, 44, 0.08)',
  'color-border-neutral':'#e6ddd0','color-shadow-medium':'rgba(91, 69, 44, 0.16)',
  'color-voice-yellow':'#f39c12','color-voice-purple':'#9b59b6','color-voice-pink':'#e91e63','color-voice-green':'#27ae60','color-state-warning':'#c78855',
  'color-text-body':'#4b3f33','color-action-primary':'#5f4a36',
  'color-state-success':'#7e9468','color-code-bg':'#2c2c2c','color-code-text':'#f3eee6','color-code-inline-bg':'rgba(0, 0, 0, 0.08)',
};
export type InkColors = typeof light;
const dark: InkColors = {
  'color-bg-app':'#1d1916', 'color-bg-paper':'#2a241f', 'color-bg-surface':'rgba(42, 37, 33, 0.82)',
  'color-bg-surface-solid':'#342d27', 'color-border-paper':'#5a4d3d', 'color-border-focus':'#ead8bd',
  'color-text-primary':'#f3e8d8', 'color-text-secondary':'#c8bcae', 'color-text-muted':'#9f9283',
  'color-bg-hover':'rgba(255, 255, 255, 0.08)', 'color-state-error':'#ff7a70', 'color-action-link':'#81b7d2',
  'color-disabled-bg':'#58504a','color-state-danger':'#ff8a7f','color-text-on-action':'#ffffff',
  'color-shadow-soft':'rgba(0, 0, 0, 0.32)',
  'color-border-neutral':'#4a4238','color-shadow-medium':'rgba(0, 0, 0, 0.45)',
  'color-voice-yellow':'#f7c96a','color-voice-purple':'#c99be1','color-voice-pink':'#ff8fbd','color-voice-green':'#7bdba0','color-state-warning':'#f7c96a',
  'color-text-body':'#eee8df','color-action-primary':'#f3e8d8',
  'color-state-success':'#7bcf8f','color-code-bg':'#0d1117','color-code-text':'#e6edf3','color-code-inline-bg':'rgba(0, 0, 0, 0.18)',
};
const systemDark: InkColors = {...dark,
  'color-bg-app':'#1f1b16', 'color-bg-paper':'#2a251e', 'color-bg-surface':'rgba(42, 37, 30, 0.82)',
  'color-action-primary':'#f3eee6','color-bg-surface-solid':'#332d25', 'color-border-focus':'#f3eee6', 'color-text-primary':'#f3eee6',
};
export function inkColors(mode: InkThemeMode, systemIsDark: boolean): InkColors {
  return mode === 'dark' ? dark : mode === 'light' ? light : systemIsDark ? systemDark : light;
}
