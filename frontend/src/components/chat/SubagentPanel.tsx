// [Input] Thread-keyed useThreadSubagents store and ChatView-controlled sidebar state.
// [Output] Compact subagent task header entry plus FileSidebar-shaped right detail panel.
// [Pos] claude-subagent summary/detail component in frontend/src/components/chat
// [Sync] 2026-08-04: initial task summary entry and active/completed/ended sidebar.

import { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../../i18n';
import {
  hydrateThreadSubagents,
  useThreadSubagents,
  type ThreadSubagentStatus,
  type ThreadSubagentTask,
} from '../../hooks/useThreadSubagents';
import { IconLoader, IconSubagents, IconX } from './Icons';

const SUBAGENT_REFRESH_INTERVAL_MS = 8000;
const RECENT_AGENT_LIMIT = 4;

interface SubagentButtonProps {
  threadId: string;
  open: boolean;
  onToggle: () => void;
}

interface SubagentSidebarProps {
  threadId: string;
  open: boolean;
  onClose: () => void;
}

const STATUS_COLORS: Record<ThreadSubagentStatus, string> = {
  running: '#6ea8fe',
  completed: '#52c77e',
  failed: 'var(--color-state-error)',
  cancelled: 'var(--color-text-muted)',
};

function avatarHue(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = ((hash << 5) - hash + value.charCodeAt(index)) | 0;
  }
  return Math.abs(hash) % 360;
}

function AgentAvatar({ task, size = '1.75rem' }: { task: ThreadSubagentTask; size?: string }) {
  const hue = avatarHue(task.agentType || task.agentId);
  return (
    <span
      title={task.agentType}
      style={{
        width: size,
        height: size,
        flexShrink: 0,
        borderRadius: '50%',
        display: 'grid',
        placeItems: 'center',
        color: `hsl(${hue} 65% 78%)`,
        background: `radial-gradient(circle at 32% 28%, hsl(${hue} 65% 44%), hsl(${(hue + 42) % 360} 55% 24%))`,
        border: '1px solid color-mix(in srgb, currentColor 34%, transparent)',
        boxSizing: 'border-box',
      }}
      aria-hidden="true"
    >
      <IconSubagents style={{ width: '58%', height: '58%' }} />
    </span>
  );
}

function formatDuration(milliseconds: number | null, language?: string): string {
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

function TaskRow({ task }: { task: ThreadSubagentTask }) {
  const { t, i18n } = useTranslation();
  const duration = formatDuration(task.durationMs, i18n.language);
  return (
    <li
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.7rem',
        minWidth: 0,
        padding: '0.72rem 0.75rem',
        borderRadius: '0.8rem',
        background: 'var(--color-bg-paper)',
      }}
    >
      <AgentAvatar task={task} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', minWidth: 0 }}>
          <span title={task.description} style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text-primary)', fontSize: '0.88rem', fontWeight: 600 }}>
            {task.description}
          </span>
          <span style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: '0.28rem', color: STATUS_COLORS[task.status], fontSize: '0.69rem' }}>
            <span style={{ width: '0.4rem', height: '0.4rem', borderRadius: '50%', background: 'currentColor' }} aria-hidden="true" />
            {t(`chat.subagents.status.${task.status}`)}
          </span>
        </div>
        <div title={task.summary ?? undefined} style={{ marginTop: '0.2rem', color: 'var(--color-text-muted)', fontSize: '0.77rem', lineHeight: 1.45, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {task.summary || task.agentType || t('chat.subagents.noSummary')}
        </div>
      </div>
      {duration ? (
        <span style={{ flexShrink: 0, paddingTop: '0.05rem', color: 'var(--color-text-muted)', fontSize: '0.74rem', whiteSpace: 'nowrap' }}>
          {duration}
        </span>
      ) : null}
    </li>
  );
}

function TaskGroup({ title, tasks, emptyLabel }: { title: string; tasks: ThreadSubagentTask[]; emptyLabel?: string }) {
  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
      <h3 style={{ margin: 0, color: 'var(--color-text-secondary)', fontSize: '0.82rem', fontWeight: 600 }}>{title}</h3>
      {tasks.length > 0 ? (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
          {tasks.map((task) => <TaskRow key={task.taskId} task={task} />)}
        </ul>
      ) : emptyLabel ? (
        <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', padding: '0.15rem 0' }}>{emptyLabel}</div>
      ) : null}
    </section>
  );
}

export function SubagentButton({ threadId, open, onToggle }: SubagentButtonProps) {
  const { t } = useTranslation();
  const state = useThreadSubagents(threadId);

  useEffect(() => {
    void hydrateThreadSubagents(threadId);
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void hydrateThreadSubagents(threadId);
    }, SUBAGENT_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [threadId]);

  const recentTasks = useMemo(() => {
    const byAgent = new Map<string, ThreadSubagentTask>();
    for (const task of state.tasks) {
      const key = task.agentType || task.agentId;
      if (!byAgent.has(key)) byAgent.set(key, task);
      if (byAgent.size === RECENT_AGENT_LIMIT) break;
    }
    return Array.from(byAgent.values());
  }, [state.tasks]);

  if (!state.exists) return null;
  const summary = state.counts.running > 0
    ? t('chat.subagents.runningSummary', { running: state.counts.running, completed: state.counts.completed })
    : state.counts.completed > 0
      ? t('chat.subagents.completedSummary', { count: state.counts.completed })
      : t('chat.subagents.taskSummary', { count: state.counts.total });

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-controls="thread-subagent-sidebar"
      aria-expanded={open}
      aria-label={t('chat.subagents.buttonAria', { summary })}
      title={t('chat.subagents.title')}
      style={{
        height: '2rem',
        minWidth: '2rem',
        border: '1px solid transparent',
        borderRadius: '0.55rem',
        background: open ? 'var(--color-bg-surface)' : 'transparent',
        color: open ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.38rem',
        padding: '0 0.45rem',
        fontSize: '0.75rem',
        transition: 'background 0.14s ease, color 0.14s ease',
      }}
      onMouseEnter={(event) => { event.currentTarget.style.background = 'var(--color-bg-surface)'; event.currentTarget.style.color = 'var(--color-text-primary)'; }}
      onMouseLeave={(event) => { if (!open) { event.currentTarget.style.background = 'transparent'; event.currentTarget.style.color = 'var(--color-text-secondary)'; } }}
    >
      <span style={{ display: 'flex', alignItems: 'center', paddingLeft: '0.08rem' }} aria-hidden="true">
        {recentTasks.map((task, index) => (
          <span key={task.agentId} style={{ display: 'inline-flex', marginLeft: index === 0 ? 0 : '-0.28rem' }}>
            <AgentAvatar task={task} size="1.15rem" />
          </span>
        ))}
      </span>
      <span style={{ whiteSpace: 'nowrap' }}>{summary}</span>
      {state.counts.running > 0 ? <span style={{ width: '0.4rem', height: '0.4rem', borderRadius: '50%', background: STATUS_COLORS.running }} aria-hidden="true" /> : null}
    </button>
  );
}

export function SubagentSidebar({ threadId, open, onClose }: SubagentSidebarProps) {
  const { t } = useTranslation();
  const state = useThreadSubagents(threadId);

  useEffect(() => {
    if (open) void hydrateThreadSubagents(threadId);
  }, [open, threadId]);

  const activeTasks = state.tasks.filter((task) => task.status === 'running');
  const completedTasks = state.tasks.filter((task) => task.status === 'completed');
  const endedTasks = state.tasks.filter((task) => task.status === 'failed' || task.status === 'cancelled');

  return (
    <aside
      id="thread-subagent-sidebar"
      aria-label={t('chat.subagents.title')}
      style={{
        width: open ? '26rem' : 0,
        minWidth: open ? '26rem' : 0,
        overflow: 'hidden',
        borderLeft: open ? '1px solid var(--color-border-paper)' : 'none',
        background: 'var(--color-bg-app)',
        transition: 'width 0.25s ease, min-width 0.25s ease',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {open ? (
        <>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', borderBottom: '1px solid var(--color-border-paper)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', color: 'var(--color-text-primary)' }}>
              <IconSubagents style={{ width: '1.15rem', height: '1.15rem' }} />
              <span style={{ fontWeight: 600 }}>{t('chat.subagents.title')}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <button type="button" onClick={() => void hydrateThreadSubagents(threadId)} aria-label={t('chat.subagents.refresh')} title={t('chat.subagents.refresh')} style={{ width: '1.8rem', height: '1.8rem', border: 'none', borderRadius: '0.45rem', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', display: 'grid', placeItems: 'center' }}>
                {state.loading ? <IconLoader style={{ width: '0.95rem', height: '0.95rem' }} /> : '↻'}
              </button>
              <button type="button" onClick={onClose} aria-label={t('common.close', { defaultValue: 'Close' })} style={{ width: '1.8rem', height: '1.8rem', border: 'none', borderRadius: '0.45rem', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', display: 'grid', placeItems: 'center' }}>
                <IconX style={{ width: '1rem', height: '1rem' }} />
              </button>
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }} aria-live="polite">
            {state.error ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', padding: '0.7rem 0.8rem', borderRadius: '0.7rem', background: 'color-mix(in srgb, var(--color-state-error) 10%, transparent)', color: 'var(--color-state-error)', fontSize: '0.78rem' }}>
                <span>{t('chat.subagents.unavailable')}</span>
                <button type="button" onClick={() => void hydrateThreadSubagents(threadId)} style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', fontWeight: 600 }}>{t('chat.subagents.retry')}</button>
              </div>
            ) : null}

            {state.loading && !state.exists ? (
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>{t('chat.subagents.loading')}</div>
            ) : !state.exists ? (
              <div style={{ minHeight: '12rem', display: 'grid', placeItems: 'center', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.84rem' }}>
                <div>
                  <IconSubagents style={{ width: '2rem', height: '2rem', margin: '0 auto 0.7rem' }} />
                  {t('chat.subagents.empty')}
                </div>
              </div>
            ) : (
              <>
                <TaskGroup title={t('chat.subagents.activeTitle')} tasks={activeTasks} emptyLabel={t('chat.subagents.noActive')} />
                <TaskGroup title={t('chat.subagents.completedTitle', { count: state.counts.completed })} tasks={completedTasks} />
                {endedTasks.length > 0 ? <TaskGroup title={t('chat.subagents.endedTitle', { count: state.counts.ended })} tasks={endedTasks} /> : null}
              </>
            )}
          </div>
        </>
      ) : null}
    </aside>
  );
}
