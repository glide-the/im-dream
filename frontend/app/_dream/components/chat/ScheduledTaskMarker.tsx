// [Input] Strictly decoded successful create_scheduled_task snapshots and a Chat-owned detail action.
// [Output] Compact persisted task markers placed inside the assistant turn that created them.
// [Pos] Chat scheduled-task navigation affordance; details are owned by ChatView's right sidebar.
// [Sync] 2026-09-29: make each successful Tool marker one full-row button without parsing assistant prose.
'use client';

import { useTranslation } from 'react-i18next';
import { IconClock } from './Icons';
import { scheduledTaskMarkerSummary, type ScheduledTaskMarkerSnapshot } from './scheduledTaskMarkerModel';
import './ScheduledTaskMarker.css';

export default function ScheduledTaskMarkerList({ tasks, onOpen }: {
  tasks: ScheduledTaskMarkerSnapshot[];
  onOpen?: (task: ScheduledTaskMarkerSnapshot) => void;
}) {
  const { t } = useTranslation();
  if (tasks.length === 0) return null;
  return <div className="scheduled-task-markers" aria-label={t('chat.scheduledTask.createdList')}>
    {tasks.map((task) => <button type="button" className="scheduled-task-marker" key={`${task.id}:${task.revision}`}
      onClick={() => onOpen?.(task)} disabled={!onOpen}
      aria-label={t('chat.scheduledTask.openAria', { title: task.title })}>
      <span className="scheduled-task-marker__icon" aria-hidden="true"><IconClock /></span>
      <span className="scheduled-task-marker__copy">
        <strong>{task.title}</strong>
        <small>{scheduledTaskMarkerSummary(task, t('calendar.scheduledDaily'))}</small>
      </span>
      <span className="scheduled-task-marker__action" aria-hidden="true">{t('chat.scheduledTask.open')}</span>
    </button>)}
  </div>;
}
