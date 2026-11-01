// [Input] Original PlanPanel refresh cadence and Todo collapse presentation.
// [Output] Shared Web/Native UI defaults; no task scheduling, execution or quota policy.
// [Pos] Task activity presentation constants copied from the existing Web panel.
export const TASK_ACTIVITY_REFRESH_INTERVAL_MS = 8_000;
export const TASK_TODO_VISIBLE_COUNT = 3;

import type {TFunction} from 'i18next';
import {getDateLocale} from '../../i18n';

export function formatTaskRelativeTime(value: string, t: TFunction, language?: string): string {
  const date = new Date(value.includes('T') ? value : value.replace(' ', 'T'));
  if (Number.isNaN(date.getTime())) return '';
  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) return t('chat.planPanel.justNow');
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return t('chat.planPanel.justNow');
  if (minutes < 60) return t('chat.planPanel.minutesAgo', { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t('chat.planPanel.hoursAgo', { count: hours });
  const days = Math.floor(hours / 24);
  if (days < 7) return t('chat.planPanel.daysAgo', { count: days });
  return new Intl.DateTimeFormat(getDateLocale(language), { month: 'numeric', day: 'numeric' }).format(date);
}
