// [Input] Current business Thread, owner-filtered task links/status, and the existing subagent store.
// [Output] Separate task-session and subagent cards for the Plan/Todo activity popover.
// [Pos] Current-Thread activity content; PlanButton owns the trigger and popover shell.
// [Sync] 2026-09-28: separate independent task sessions and subagents from unchanged Environment info.
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useThreadSubagents } from '../../hooks/useThreadSubagents';
import { SubagentButton } from './SubagentPanel';
import { IconChevronDown, IconChevronRight } from './Icons';
import {
  fetchTaskSessionDetail,
  fetchTaskSessionLinks,
  type TaskSessionLink,
  type TaskSessionStatus,
} from './taskSessionLinks';
import './TaskActivityContent.css';

interface TaskActivityContentProps {
  active: boolean;
  threadId: string;
  subagentSidebarOpen: boolean;
  onToggleSubagents: () => void;
  onNavigateThread: (threadId: string) => void;
  onRequestClose: () => void;
}

function TaskStatusIcon({ status }: { status: TaskSessionStatus }) {
  if (status === 'completed') {
    return (
      <svg className="task-activity__status-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="9" fill="var(--color-text-primary)" />
        <polyline points="8.5 12.5 11 15 15.5 9.5" fill="none" stroke="var(--color-bg-surface-solid)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (status === 'running') {
    return (
      <svg className="task-activity__status-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" fill="none" stroke="var(--color-action-link)" strokeWidth="2" />
        <circle cx="12" cy="12" r="3.5" fill="var(--color-action-link)" />
      </svg>
    );
  }
  if (status === 'failed') {
    return (
      <svg className="task-activity__status-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" fill="none" stroke="var(--color-state-error)" strokeWidth="2" />
        <path d="M9 9l6 6m0-6-6 6" fill="none" stroke="var(--color-state-error)" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg className="task-activity__status-icon" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" fill="none" stroke="var(--color-text-muted)" strokeWidth="2" />
    </svg>
  );
}

export default function TaskActivityContent({
  active,
  threadId,
  subagentSidebarOpen,
  onToggleSubagents,
  onNavigateThread,
  onRequestClose,
}: TaskActivityContentProps) {
  const { t } = useTranslation();
  const [links, setLinks] = useState<TaskSessionLink[] | null>(null);
  const [statuses, setStatuses] = useState<Record<string, TaskSessionStatus>>({});
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [tasksExpanded, setTasksExpanded] = useState(true);
  const requestRef = useRef(0);
  const subagents = useThreadSubagents(threadId);

  const refresh = useCallback(async () => {
    const request = ++requestRef.current;
    setLoading(true);
    setFailed(false);
    try {
      const next = await fetchTaskSessionLinks(threadId);
      if (request !== requestRef.current) return;
      setLinks(next.created);
      setStatuses({});
      const statusPairs = await Promise.all(next.created.map(async (link): Promise<[string, TaskSessionStatus]> => {
        if (link.launch_status === 'failed') return [link.task_id, 'failed'];
        if (link.launch_status === 'pending') return [link.task_id, 'pending'];
        try {
          const detail = await fetchTaskSessionDetail(threadId, link.task_id);
          return [link.task_id, detail.task_id === link.task_id && detail.thread_id === link.thread_id ? detail.status : 'state_unknown'];
        } catch {
          return [link.task_id, 'state_unknown'];
        }
      }));
      if (request === requestRef.current) setStatuses(Object.fromEntries(statusPairs));
    } catch {
      if (request === requestRef.current) setFailed(true);
    } finally {
      if (request === requestRef.current) setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    if (!active) return undefined;
    void refresh();
    const onVisibility = () => { if (document.visibilityState === 'visible') void refresh(); };
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      requestRef.current += 1;
    };
  }, [active, refresh]);

  return (
    <div className="task-activity__content" aria-label={t('chat.taskActivity.sectionsAria')}>
      <div className="task-activity__section">
        <button
          type="button"
          className="task-activity__section-heading task-activity__section-toggle"
          aria-expanded={tasksExpanded}
          onClick={() => setTasksExpanded((value) => !value)}
        >
          <span>{t('chat.taskActivity.createdTasks')}</span>
          <span className="task-activity__section-summary">
            {links && links.length > 0 ? <span>{links.length}</span> : null}
            <IconChevronDown className={tasksExpanded ? 'task-activity__chevron task-activity__chevron--open' : 'task-activity__chevron'} />
          </span>
        </button>
        {tasksExpanded && links && links.length > 0 ? (
          <ul className="task-activity__tasks">
            {links.map((link) => {
              const status = statuses[link.task_id] ?? (link.launch_status === 'failed' ? 'failed' : link.launch_status === 'pending' ? 'pending' : 'state_unknown');
              return (
                <li key={link.task_id}>
                  <button
                    type="button"
                    className="task-activity__task"
                    data-task-status={status}
                    onClick={() => { onRequestClose(); onNavigateThread(link.thread_id); }}
                    title={link.title}
                  >
                    <TaskStatusIcon status={status} />
                    <span className="task-activity__task-title">{link.title}</span>
                    <span className="task-activity__task-status">{t(`chat.taskActivity.status.${status}`)}</span>
                    <IconChevronRight style={{ width: '0.9rem', height: '0.9rem' }} />
                  </button>
                </li>
              );
            })}
          </ul>
        ) : tasksExpanded && !loading && !failed ? <p className="task-activity__note">{t('chat.taskActivity.noTasks')}</p> : null}
        {tasksExpanded && loading ? <p className="task-activity__note" role="status">{t('chat.taskActivity.loading')}</p> : null}
        {tasksExpanded && failed ? <div className="task-activity__failure" role="status"><span>{t('chat.taskActivity.unavailable')}</span><button type="button" onClick={() => void refresh()}>{t('chat.taskActivity.retry')}</button></div> : null}
      </div>
      <div className="task-activity__section">
        <div className="task-activity__section-heading"><h3>{t('chat.subagents.title')}</h3></div>
        <SubagentButton threadId={threadId} open={subagentSidebarOpen} inInfoCard autoRefresh={false} onToggle={() => { onRequestClose(); onToggleSubagents(); }} />
        {!subagents.exists ? <p className="task-activity__note">{subagents.error ? t('chat.subagents.unavailable') : subagents.loading ? t('chat.subagents.loading') : t('chat.subagents.empty')}</p> : null}
      </div>
    </div>
  );
}
