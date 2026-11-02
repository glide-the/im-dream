// [Input] Original Chat Thread dates, translation function and optional actor-local day.
// [Output] Original date labels and stable, input-ordered history groups shared by Web/native.
// [Pos] Presentation helpers extracted from ChatView without changing date boundaries or sorting.
import type {TFunction} from 'i18next';
import {getDateLocale} from '../../i18n';
import type {ChatHistoryThread} from '../../api/chatHistoryApi';

function parseThreadDate(value: string): Date | null {
  const date = new Date(value.includes('T') ? value : value.replace(' ', 'T'));
  return Number.isNaN(date.getTime()) ? null : date;
}

function dayDiffFromToday(value: string, localDayKey?: string): number | null {
  const date = parseThreadDate(value);
  if (!date) return null;
  const today = localDayKey ? new Date(`${localDayKey}T00:00:00`) : new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const dateStart = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  return Math.floor((todayStart - dateStart) / 86400000);
}

export function formatThreadDateLabel(value: string, t: TFunction, language?: string): string {
  const diff = dayDiffFromToday(value);
  if (diff === 0) return t('chat.dateGroup.today');
  if (diff === 1) return t('chat.dateGroup.yesterday');
  if (diff !== null && diff > 1 && diff < 7) return t('chat.dateGroup.daysAgo', {count: diff});
  const date = parseThreadDate(value);
  if (!date) return '';
  return new Intl.DateTimeFormat(getDateLocale(language), {month: 'numeric', day: 'numeric'}).format(date);
}

function getThreadDateGroup(value: string, t: TFunction, localDayKey?: string): string {
  const diff = dayDiffFromToday(value, localDayKey);
  if (diff === 0) return t('chat.dateGroup.today');
  if (diff === 1) return t('chat.dateGroup.yesterday');
  if (diff !== null && diff > 1 && diff < 7) return t('chat.dateGroup.last7Days');
  if (diff !== null && diff < 30) return t('chat.dateGroup.last30Days');
  return t('chat.dateGroup.earlier');
}

export interface ChatHistoryGroup<T extends ChatHistoryThread = ChatHistoryThread> {
  label: string;
  threads: T[];
}

export function groupChatThreadsByDate<T extends ChatHistoryThread>(threads: T[], t: TFunction, localDayKey?: string): ChatHistoryGroup<T>[] {
  const groups: ChatHistoryGroup<T>[] = [];
  const byLabel = new Map<string, T[]>();
  threads.forEach(thread => {
    const label = getThreadDateGroup(thread.updated_at, t, localDayKey);
    if (!byLabel.has(label)) {
      byLabel.set(label, []);
      groups.push({label, threads: byLabel.get(label) ?? []});
    }
    byLabel.get(label)?.push(thread);
  });
  return groups;
}
