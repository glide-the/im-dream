// [Input] Existing scheduled definition/trigger DTOs, snapshot cadence and original translations.
// [Output] Original read-only detail cadence and related-conversation ordering/deduplication.
// [Pos] Shared presentation extracted from ScheduledTaskDetailSidebar; no transport or task control.
import type {TFunction} from 'i18next';
import type {ScheduledTask,ScheduledTrigger} from '../../api/scheduledTaskApi';
import type {ScheduledTaskMarkerSnapshot} from './scheduledTaskMarkerModel';
import {parseFlexibleTimestamp} from '../../utils/timezone';
export function scheduledTaskConversations(sourceThreadId:string|undefined,triggers:ScheduledTrigger[]) {
  const timestamp=(trigger:ScheduledTrigger)=>parseFlexibleTimestamp(trigger.created_at)?.getTime()??0;
  const rows=[...triggers].filter(trigger=>Boolean(trigger.target_thread_id)&&trigger.target_thread_id!==sourceThreadId).sort((left,right)=>timestamp(right)-timestamp(left));
  return [...new Map(rows.map(trigger=>[trigger.target_thread_id!,trigger])).values()];
}
export function scheduledTaskRuleText(rule:ScheduledTask['rule']|ScheduledTaskMarkerSnapshot['rule']|undefined,t:TFunction):string {
  return rule?.kind === 'once'
    ? `${rule.local_date} · ${rule.local_time} · ${rule.time_zone}`
    : rule?.kind === 'daily' ? `${t('calendar.scheduledDaily')} · ${rule.local_time} · ${rule.time_zone}`
      : rule?.kind === 'interval' ? `${t('calendar.scheduledIntervalSummary', { count: rule.interval_minutes })} · ${rule.time_zone}`
        : rule?.kind === 'hourly' ? `${t('calendar.scheduledHourlySummary', { count: rule.interval_hours, minute: rule.minute })} · ${rule.time_zone}`
          : rule?.kind === 'weekly' ? `${t('calendar.scheduledWeeklySummary', { days: rule.weekdays.map((day) => t(`calendar.scheduledWeekday.${day}`)).join('、'), time: rule.local_time })} · ${rule.time_zone}` : '—';
}
