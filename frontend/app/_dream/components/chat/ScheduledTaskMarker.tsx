// [Input] Strictly decoded create_scheduled_task or Admin relation snapshots and a Chat-owned detail action.
// [Output] Compact task markers shared by creating assistant replies and the current Thread activity.
// [Pos] Chat scheduled-task navigation affordance; details are owned by ChatView's right sidebar.
// [Sync] 2026-10-07: reuse task rows in activity with an optional list label and status detail.
// [Sync] 2026-10-07: show interval/hourly/weekly cadence in the full-row marker opened by the creating reply.
'use client';

import { useTranslation } from 'react-i18next';
import type { ReactNode } from 'react';
import { IconClock } from './Icons';
import { scheduledTaskMarkerSummary, type ScheduledTaskMarkerSnapshot } from './scheduledTaskMarkerModel';
import './ScheduledTaskMarker.css';

export default function ScheduledTaskMarkerList({ tasks, onOpen, ariaLabel, renderDetail }: {
  tasks: ScheduledTaskMarkerSnapshot[];
  onOpen?: (task: ScheduledTaskMarkerSnapshot) => void;
  ariaLabel?: string;
  renderDetail?: (task: ScheduledTaskMarkerSnapshot) => ReactNode;
}) {
  const { t } = useTranslation();
  if (tasks.length === 0) return null;
  return <div className="scheduled-task-markers" aria-label={ariaLabel ?? t('chat.scheduledTask.createdList')}>
    {tasks.map((task) => <button type="button" className="scheduled-task-marker" key={`${task.id}:${task.revision}`}
      onClick={() => onOpen?.(task)} disabled={!onOpen}
      aria-label={t('chat.scheduledTask.openAria', { title: task.title })}>
      <span className="scheduled-task-marker__icon" aria-hidden="true"><IconClock /></span>
      <span className="scheduled-task-marker__copy">
        <strong>{task.title}</strong>
        <small>{scheduledTaskMarkerSummary(task, t('calendar.scheduledDaily'),
          (count) => t('calendar.scheduledIntervalSummary', { count }),
          (count, minute) => t('calendar.scheduledHourlySummary', { count, minute }),
          (days, time) => t('calendar.scheduledWeeklySummary', {
            days: days.map((day) => t(`calendar.scheduledWeekday.${day}`)).join('、'), time,
          }))}</small>
        {renderDetail?.(task)}
      </span>
      <span className="scheduled-task-marker__action" aria-hidden="true">{t('chat.scheduledTask.open')}</span>
    </button>)}
  </div>;
}
