// [Input] A scheduled-task id, optional creation snapshot, and authenticated scheduled-task APIs.
// [Output] Read-only right detail sidebar with task information, owned conversations, schedule, retry, and exact Thread navigation.
// [Pos] Chat-owned scheduled-task detail surface, mutually exclusive with file/subagent/task-session sidebars.
// [Sync] 2026-10-07: display v3 repeat, source/new Chat mode and captured model without duplicating a reused source conversation.
'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getScheduledHistory, getScheduledTask, type ScheduledTask, type ScheduledTrigger } from '../../api/scheduledTaskApi';
import { parseFlexibleTimestamp } from '../../utils/timezone';
import { IconClock, IconX } from './Icons';
import type { ScheduledTaskMarkerSnapshot } from './scheduledTaskMarkerModel';
import './ScheduledTaskDetailSidebar.css';

function timestamp(trigger: ScheduledTrigger): number {
  return parseFlexibleTimestamp(trigger.created_at)?.getTime() ?? 0;
}

export default function ScheduledTaskDetailSidebar({ taskId, snapshot, onClose, onOpenThread }: {
  taskId: string;
  snapshot?: ScheduledTaskMarkerSnapshot | null;
  onClose: () => void;
  onOpenThread: (threadId: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const [task, setTask] = useState<ScheduledTask | null>(null);
  const [triggers, setTriggers] = useState<ScheduledTrigger[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const load = useCallback(async () => {
    setLoading(true); setError(false);
    try {
      const [definition, history] = await Promise.all([getScheduledTask(taskId), getScheduledHistory(taskId, 20)]);
      if (!definition.task) throw new Error('Scheduled task was not found.');
      setTask(definition.task); setTriggers(history.triggers);
    } catch { setError(true); }
    finally { setLoading(false); }
  }, [taskId]);
  useEffect(() => { void load(); }, [load]);
  const conversations = useMemo(() => {
    const rows = [...triggers].filter((trigger) => Boolean(trigger.target_thread_id)
      && trigger.target_thread_id !== task?.source_thread_id).sort((left, right) => timestamp(right) - timestamp(left));
    return [...new Map(rows.map((trigger) => [trigger.target_thread_id!, trigger])).values()];
  }, [task?.source_thread_id, triggers]);
  const title = task?.title ?? snapshot?.title ?? t('chat.scheduledTask.detailTitle');
  const rule = task?.rule ?? snapshot?.rule;
  const ruleText = rule?.kind === 'once'
    ? `${rule.local_date} · ${rule.local_time} · ${rule.time_zone}`
    : rule?.kind === 'daily' ? `${t('calendar.scheduledDaily')} · ${rule.local_time} · ${rule.time_zone}`
      : rule?.kind === 'interval' ? `${t('calendar.scheduledIntervalSummary', { count: rule.interval_minutes })} · ${rule.time_zone}`
        : rule?.kind === 'hourly' ? `${t('calendar.scheduledHourlySummary', { count: rule.interval_hours, minute: rule.minute })} · ${rule.time_zone}`
          : rule?.kind === 'weekly' ? `${t('calendar.scheduledWeeklySummary', { days: rule.weekdays.map((day) => t(`calendar.scheduledWeekday.${day}`)).join('、'), time: rule.local_time })} · ${rule.time_zone}` : '—';
  const status = task?.status ?? snapshot?.status;
  const formatDate = (value: string | null | undefined) => value ? new Date(value).toLocaleString(i18n.language) : '—';
  return <aside className="scheduled-task-detail" aria-label={t('chat.scheduledTask.detailTitle')}>
    <header className="scheduled-task-detail__header">
      <span className="scheduled-task-detail__icon" aria-hidden="true"><IconClock /></span>
      <div><strong>{title}</strong><small>{ruleText}</small></div>
      <button type="button" onClick={onClose} aria-label={t('chat.scheduledTask.close')}><IconX /></button>
    </header>
    <div className="scheduled-task-detail__body">
      {loading ? <p role="status">{t('chat.scheduledTask.loading')}</p> : null}
      {error ? <div className="scheduled-task-detail__error" role="alert"><span>{t('chat.scheduledTask.unavailable')}</span>
        <button type="button" onClick={() => void load()}>{t('calendar.scheduledRetry')}</button></div> : null}
      {!loading && !error ? <>
        <section><h3>{t('chat.scheduledTask.taskInfo')}</h3><dl>
          <div><dt>{t('calendar.scheduledStatusLabel')}</dt><dd>{status ? t(`calendar.scheduledStatus.${status}`, { defaultValue: status }) : '—'}</dd></div>
          <div><dt>{t('chat.scheduledTask.runMode')}</dt><dd>{task?.run_thread_mode === 'new_thread_each_run'
            ? t('chat.scheduledTask.newConversation') : t('chat.scheduledTask.reuseSource')}</dd></div>
          <div><dt>{t('chat.scheduledTask.model')}</dt><dd>{task?.model_alias ?? t('chat.scheduledTask.legacyModel')}</dd></div>
        </dl>{task?.prompt ? <p className="scheduled-task-detail__prompt">{task.prompt}</p> : null}</section>
        <section><h3>{t('chat.scheduledTask.conversations')}</h3>
          <div className="scheduled-task-detail__conversations">
            {task?.source_thread_id ? <button type="button" onClick={() => onOpenThread(task.source_thread_id)}>
              <span><strong>{t('chat.scheduledTask.sourceConversation')}</strong><small>{title}</small></span>
              <span aria-hidden="true">›</span>
            </button> : null}
            {conversations.map((trigger) => <button type="button" key={trigger.id}
              onClick={() => onOpenThread(trigger.target_thread_id!)}>
              <span><strong>{t('chat.scheduledTask.runConversation')}</strong>
                <small>{formatDate(trigger.scheduled_at ?? trigger.created_at)} · {t(`calendar.scheduledStatus.${trigger.status}`, { defaultValue: trigger.status })}</small></span>
              <span aria-hidden="true">›</span>
            </button>)}
            {!task?.source_thread_id && conversations.length === 0
              ? <p>{t('chat.scheduledTask.noConversations')}</p> : null}
          </div>
        </section>
        <section><h3>{t('chat.scheduledTask.taskCycle')}</h3><dl>
          <div><dt>{t('calendar.scheduledRule')}</dt><dd>{ruleText}</dd></div>
          <div><dt>{t('calendar.scheduledNext')}</dt><dd>{formatDate(task?.next_run_at ?? snapshot?.nextRunAt)}</dd></div>
        </dl></section>
      </> : null}
    </div>
  </aside>;
}
