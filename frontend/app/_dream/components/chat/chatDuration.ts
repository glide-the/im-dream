// [Input] Optional measured duration and the active UI language.
// [Output] Localized compact duration text, or an empty string when measurement is unavailable.
// [Pos] Shared pure formatter for Chat history turns and subagent summaries.
// [Sync] 2026-09-02: extracted from SubagentPanel so non-component consumers preserve Fast Refresh boundaries.

import { getDateLocale } from '../../i18n';

export function formatChatDuration(milliseconds: number | null, language?: string): string {
  if (milliseconds == null || !Number.isFinite(milliseconds)) return '';
  const locale = getDateLocale(language);
  const seconds = Math.max(0, Math.round(milliseconds / 1000));
  if (seconds < 60) {
    return new Intl.NumberFormat(locale, { style: 'unit', unit: 'second', unitDisplay: 'narrow' }).format(seconds);
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return new Intl.NumberFormat(locale, { style: 'unit', unit: 'minute', unitDisplay: 'narrow' }).format(minutes);
  }
  const hours = Math.round(minutes / 60);
  return new Intl.NumberFormat(locale, { style: 'unit', unit: 'hour', unitDisplay: 'narrow' }).format(hours);
}
