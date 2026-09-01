// [Input] Thread-keyed useThreadSubagents store and ChatView-controlled sidebar state.
// [Output] Compact subagent task header entry plus FileSidebar-shaped right detail panel.
// [Pos] claude-subagent summary/detail component in frontend/src/components/chat
// [Sync] 2026-08-04: task summary entry, chat-row task button, and focused active/completed/ended sidebar.
// [Sync] 2026-08-05: render the latest result through the shared ChatMarkdown/prose chain.
// [Sync] 2026-08-05: add a draggable/keyboard resize rail and readable operational typography.
// [Sync] 2026-08-05: compact task index and conversation-first readonly task detail.
// [Sync] 2026-08-31: reuse the shared right-panel resize hook without changing Subagent presentation.

import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../../i18n';
import { useResizableRightPanel } from '../../hooks/useResizableRightPanel';
import {
  hydrateThreadSubagents,
  useThreadSubagents,
  type ThreadSubagentStatus,
  type ThreadSubagentTask,
} from '../../hooks/useThreadSubagents';
import { IconLoader, IconSubagents, IconX } from './Icons';
import SubagentMessageTimeline from './SubagentMessageTimeline';

const SUBAGENT_REFRESH_INTERVAL_MS = 8000;
const RECENT_AGENT_LIMIT = 4;
const DEFAULT_SIDEBAR_WIDTH_PX = 480;
const MIN_SIDEBAR_WIDTH_PX = 352;
const MAX_SIDEBAR_WIDTH_PX = 768;
const MIN_CHAT_WIDTH_PX = 360;
const SIDEBAR_WIDTH_STORAGE_KEY = 'ink-subagent-sidebar-width';
const SIDEBAR_FONT_FAMILY = 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

interface SubagentButtonProps {
  threadId: string;
  open: boolean;
  onToggle: () => void;
}

interface SubagentSidebarProps {
  threadId: string;
  open: boolean;
  onClose: () => void;
  focusToolCallId?: string | null;
}

const STATUS_COLORS: Record<ThreadSubagentStatus, string> = {
  running: 'var(--color-action-link)',
  completed: 'var(--color-state-success)',
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

function TaskRow({ task, focused = false, onSelect }: { task: ThreadSubagentTask; focused?: boolean; onSelect: () => void }) {
  const { t, i18n } = useTranslation();
  const duration = formatDuration(task.durationMs, i18n.language);
  const status = t(`chat.subagents.status.${task.status}`);
  return (
    <li id={`thread-subagent-task-${task.taskId}`}>
      <button
        type="button"
        onClick={onSelect}
        aria-current={focused ? 'true' : undefined}
        aria-label={t('chat.subagents.openTaskAria', { task: task.description, status, duration: duration || t('chat.subagents.unknown') })}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: '0.65rem',
          minWidth: 0,
          minHeight: task.summary ? '4.5rem' : '3.75rem',
          padding: '0.6rem 0.7rem',
          borderRadius: '0.65rem',
          background: focused ? 'var(--color-bg-hover)' : 'var(--color-bg-paper)',
          border: '1px solid transparent',
          boxShadow: focused ? 'inset 2px 0 0 var(--color-action-link)' : 'none',
          color: 'inherit',
          cursor: 'pointer',
          font: 'inherit',
          textAlign: 'left',
          outlineOffset: '2px',
          transition: 'background 0.14s ease, border-color 0.14s ease, box-shadow 0.14s ease',
        }}
        onMouseEnter={(event) => {
          event.currentTarget.style.background = 'var(--color-bg-hover)';
          event.currentTarget.style.borderColor = 'var(--color-border-paper)';
        }}
        onMouseLeave={(event) => {
          event.currentTarget.style.background = focused ? 'var(--color-bg-hover)' : 'var(--color-bg-paper)';
          event.currentTarget.style.borderColor = 'transparent';
        }}
      >
        <AgentAvatar task={task} size="1.75rem" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div title={task.description} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text-primary)', fontSize: '0.86rem', lineHeight: 1.4, fontWeight: 650 }}>{task.description}</div>
          {task.summary ? <div title={task.summary} style={{ marginTop: '0.2rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text-muted)', fontSize: '0.76rem', lineHeight: 1.45 }}>{task.summary}</div> : null}
        </div>
        <span style={{ minWidth: '4.4rem', flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.18rem' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', color: STATUS_COLORS[task.status], fontSize: '0.7rem', fontWeight: 650, whiteSpace: 'nowrap' }}>
            <span style={{ width: '0.38rem', height: '0.38rem', borderRadius: '50%', background: 'currentColor' }} aria-hidden="true" />
            {status}
          </span>
          {duration ? <span style={{ color: 'var(--color-text-muted)', fontSize: '0.68rem', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>{duration}</span> : null}
        </span>
        <span aria-hidden="true" style={{ flexShrink: 0, color: 'var(--color-text-muted)', fontSize: '0.95rem', lineHeight: 1 }}>›</span>
      </button>
    </li>
  );
}

function TaskGroup({ title, tasks, emptyLabel, focusedTaskId, onSelect }: { title: string; tasks: ThreadSubagentTask[]; emptyLabel?: string; focusedTaskId?: string | null; onSelect: (taskId: string) => void }) {
  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <h3 style={{ margin: 0, color: 'var(--color-text-secondary)', fontSize: '0.76rem', lineHeight: 1.4, fontWeight: 700, letterSpacing: '0.015em' }}>{title}</h3>
      {tasks.length > 0 ? (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          {tasks.map((task) => <TaskRow key={task.taskId} task={task} focused={task.taskId === focusedTaskId} onSelect={() => onSelect(task.taskId)} />)}
        </ul>
      ) : emptyLabel ? (
        <div style={{ color: 'var(--color-text-muted)', fontSize: '0.84rem', lineHeight: 1.55, padding: '0.25rem 0' }}>{emptyLabel}</div>
      ) : null}
    </section>
  );
}

function formatDateTime(value: string | null, language?: string): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(getDateLocale(language), {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

function TaskDetail({ task }: { task: ThreadSubagentTask }) {
  const { t, i18n } = useTranslation();
  const legacy = task.projectionVersion < 2 || task.messages.some((message) => message.legacy);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--color-border-paper)', color: 'var(--color-text-muted)', fontSize: '0.72rem', lineHeight: 1.45 }}>
        <span>{t('chat.subagents.timeline.messageCount', { count: task.messageCount })}</span>
        {task.startedAt ? <time>{formatDateTime(task.startedAt, i18n.language)}</time> : null}
      </div>
      <SubagentMessageTimeline messages={task.messages} taskStatus={task.status} legacy={legacy} truncated={task.messagesTruncated} />
      {task.status === 'running' ? <div style={{ padding: '0.7rem 0', color: 'var(--color-action-link)', fontSize: '0.78rem' }}>{t('chat.subagents.timeline.running')}</div> : null}
    </div>
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

export function SubagentToolButton({
  task,
  description,
  onClick,
}: {
  task?: ThreadSubagentTask;
  description: string;
  onClick?: () => void;
}) {
  const { t } = useTranslation();
  const fallbackTask: ThreadSubagentTask = {
    taskId: 'pending',
    agentId: 'pending',
    agentType: 'Agent',
    description,
    summary: null,
    status: 'running',
    toolCallId: null,
    spawnDepth: null,
    startedAt: null,
    finishedAt: null,
    durationMs: null,
    error: null,
    activity: [],
    messages: [],
    messageCount: 0,
    messagesTruncated: false,
    projectionVersion: 1,
  };
  const displayTask = task ?? fallbackTask;
  const statusLabel = task
    ? t(`chat.subagents.status.${task.status}`)
    : t('chat.subagents.launched');

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      aria-label={t('chat.subagents.openTask', { task: description })}
      style={{
        maxWidth: '100%',
        width: 'fit-content',
        minHeight: '2.35rem',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        border: '1px solid var(--color-border-paper)',
        borderRadius: '999px',
        background: 'var(--color-bg-surface)',
        color: 'var(--color-text-primary)',
        padding: '0.28rem 0.72rem 0.28rem 0.32rem',
        cursor: onClick ? 'pointer' : 'default',
        font: 'inherit',
        textAlign: 'left',
        transition: 'background 0.14s ease, border-color 0.14s ease, transform 0.14s ease',
      }}
      onMouseEnter={(event) => {
        if (!onClick) return;
        event.currentTarget.style.background = 'var(--color-bg-hover)';
        event.currentTarget.style.borderColor = 'var(--color-action-link)';
      }}
      onMouseLeave={(event) => {
        event.currentTarget.style.background = 'var(--color-bg-surface)';
        event.currentTarget.style.borderColor = 'var(--color-border-paper)';
      }}
    >
      <AgentAvatar task={displayTask} size="1.45rem" />
      <span style={{ minWidth: 0, maxWidth: '22rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.86rem', fontWeight: 600 }}>
        {description}
      </span>
      <span style={{ flexShrink: 0, color: task ? STATUS_COLORS[task.status] : 'var(--color-text-muted)', fontSize: '0.78rem' }}>
        {statusLabel}
      </span>
      <span aria-hidden="true" style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>›</span>
    </button>
  );
}

export function SubagentSidebar({ threadId, open, onClose, focusToolCallId }: SubagentSidebarProps) {
  const { t, i18n } = useTranslation();
  const state = useThreadSubagents(threadId);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const resize = useResizableRightPanel({
    defaultWidth: DEFAULT_SIDEBAR_WIDTH_PX,
    minWidth: MIN_SIDEBAR_WIDTH_PX,
    maxWidth: MAX_SIDEBAR_WIDTH_PX,
    minSiblingWidth: MIN_CHAT_WIDTH_PX,
    storageKey: SIDEBAR_WIDTH_STORAGE_KEY,
  });
  const finishResize = resize.finishResize;

  useEffect(() => {
    if (!open) finishResize();
  }, [finishResize, open]);

  useEffect(() => {
    if (open) void hydrateThreadSubagents(threadId);
  }, [open, threadId]);

  const activeTasks = state.tasks.filter((task) => task.status === 'running');
  const completedTasks = state.tasks.filter((task) => task.status === 'completed');
  const endedTasks = state.tasks.filter((task) => task.status === 'failed' || task.status === 'cancelled');
  const focusedTaskId = state.tasks.find((task) => task.toolCallId === focusToolCallId)?.taskId ?? null;
  const selectedTask = state.tasks.find((task) => task.taskId === selectedTaskId) ?? null;
  const sidebarWidthBounds = resize.bounds;

  useEffect(() => {
    setSelectedTaskId(null);
  }, [threadId]);

  useEffect(() => {
    if (open && focusedTaskId) setSelectedTaskId(focusedTaskId);
  }, [focusedTaskId, open]);

  useEffect(() => {
    if (selectedTaskId && !state.tasks.some((task) => task.taskId === selectedTaskId)) {
      setSelectedTaskId(null);
    }
  }, [selectedTaskId, state.tasks]);

  useEffect(() => {
    if (!open || !focusedTaskId) return undefined;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById(`thread-subagent-task-${focusedTaskId}`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [focusedTaskId, open]);

  return (
    <aside
      id="thread-subagent-sidebar"
      aria-label={t('chat.subagents.title')}
      style={{
        width: open ? resize.width : 0,
        minWidth: open ? resize.width : 0,
        overflow: 'hidden',
        borderLeft: open ? '1px solid var(--color-border-paper)' : 'none',
        background: 'var(--color-bg-app)',
        transition: resize.isResizing ? 'none' : 'width 0.25s ease, min-width 0.25s ease',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        boxSizing: 'border-box',
        fontFamily: SIDEBAR_FONT_FAMILY,
      }}
    >
      {open ? (
        <>
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label={t('chat.subagents.resizeSidebar')}
            aria-valuemin={Math.round(sidebarWidthBounds.min)}
            aria-valuemax={Math.round(sidebarWidthBounds.max)}
            aria-valuenow={Math.round(resize.width)}
            aria-valuetext={`${Math.round(resize.width)} px`}
            tabIndex={0}
            title={t('chat.subagents.resizeSidebar')}
            onPointerDown={resize.handleResizePointerDown}
            onPointerMove={resize.handleResizePointerMove}
            onPointerUp={resize.handleResizePointerEnd}
            onPointerCancel={resize.handleResizePointerEnd}
            onLostPointerCapture={resize.finishResize}
            onDoubleClick={resize.resetWidth}
            onKeyDown={resize.handleResizeKeyDown}
            onMouseEnter={() => resize.setResizeRailActive(true)}
            onMouseLeave={() => resize.setResizeRailActive(false)}
            onFocus={() => resize.setResizeRailActive(true)}
            onBlur={() => resize.setResizeRailActive(false)}
            style={{
              position: 'absolute',
              inset: '0 auto 0 0',
              zIndex: 4,
              width: '0.65rem',
              cursor: 'col-resize',
              touchAction: 'none',
              outline: 'none',
              background: resize.isResizing || resize.resizeRailActive
                ? 'color-mix(in srgb, var(--color-action-link) 11%, transparent)'
                : 'transparent',
              transition: 'background 0.14s ease',
            }}
          >
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                left: '0.14rem',
                top: '50%',
                width: resize.isResizing || resize.resizeRailActive ? '0.15rem' : '1px',
                height: resize.isResizing || resize.resizeRailActive ? '4.5rem' : '100%',
                borderRadius: '999px',
                background: resize.isResizing || resize.resizeRailActive ? 'var(--color-action-link)' : 'var(--color-border-paper)',
                transform: 'translateY(-50%)',
                transition: 'height 0.14s ease, width 0.14s ease, background 0.14s ease',
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', minHeight: '3.75rem', padding: '0.65rem 0.85rem 0.65rem 1rem', borderBottom: '1px solid var(--color-border-paper)', boxSizing: 'border-box', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', color: 'var(--color-text-primary)', minWidth: 0, flex: 1 }}>
              {selectedTask ? (
                <button type="button" onClick={() => setSelectedTaskId(null)} aria-label={t('chat.subagents.backToTasks')} title={t('chat.subagents.backToTasks')} style={{ width: '2.2rem', height: '2.2rem', flexShrink: 0, border: 'none', borderRadius: '0.45rem', background: 'transparent', color: 'var(--color-text-secondary)', cursor: 'pointer', display: 'grid', placeItems: 'center', fontSize: '1.15rem' }}>←</button>
              ) : <IconSubagents style={{ width: '1.15rem', height: '1.15rem' }} />}
              {selectedTask ? <AgentAvatar task={selectedTask} size="1.8rem" /> : null}
              <span style={{ minWidth: 0, flex: 1 }}>
                <span title={selectedTask?.description} style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: selectedTask ? '0.88rem' : '0.96rem', lineHeight: 1.35, fontWeight: 700 }}>{selectedTask?.description ?? t('chat.subagents.title')}</span>
                {selectedTask ? <span style={{ display: 'block', marginTop: '0.1rem', color: 'var(--color-text-muted)', fontSize: '0.68rem', lineHeight: 1.3 }}>{selectedTask.agentType}</span> : null}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              {selectedTask ? <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.08rem', marginRight: '0.15rem', color: STATUS_COLORS[selectedTask.status], fontSize: '0.68rem', fontWeight: 650, whiteSpace: 'nowrap' }}>
                <span>{t(`chat.subagents.status.${selectedTask.status}`)}</span>
                <span style={{ color: 'var(--color-text-muted)', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{formatDuration(selectedTask.durationMs, i18n.language) || t('chat.subagents.unknown')}</span>
              </span> : null}
              <button type="button" onClick={() => void hydrateThreadSubagents(threadId)} aria-label={t('chat.subagents.refresh')} title={t('chat.subagents.refresh')} style={{ width: '2.2rem', height: '2.2rem', border: 'none', borderRadius: '0.45rem', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', display: 'grid', placeItems: 'center' }}>
                {state.loading ? <IconLoader style={{ width: '0.95rem', height: '0.95rem' }} /> : '↻'}
              </button>
              <button type="button" onClick={onClose} aria-label={t('common.close', { defaultValue: 'Close' })} style={{ width: '2.2rem', height: '2.2rem', border: 'none', borderRadius: '0.45rem', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', display: 'grid', placeItems: 'center' }}>
                <IconX style={{ width: '1rem', height: '1rem' }} />
              </button>
            </div>
          </div>

          <div data-subagent-view={selectedTask ? 'detail' : 'list'} style={{ flex: 1, overflowY: 'auto', padding: selectedTask ? '0.9rem 1rem 1.5rem' : '1rem 1rem 1.5rem', display: 'flex', flexDirection: 'column', gap: selectedTask ? '1rem' : '1.25rem' }}>
            {state.error ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', padding: '0.7rem 0.8rem', borderRadius: '0.7rem', background: 'color-mix(in srgb, var(--color-state-error) 10%, transparent)', color: 'var(--color-state-error)', fontSize: '0.78rem' }}>
                <span>{t('chat.subagents.unavailable')}</span>
                <button type="button" onClick={() => void hydrateThreadSubagents(threadId)} style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', fontWeight: 600 }}>{t('chat.subagents.retry')}</button>
              </div>
            ) : null}

            {selectedTask ? (
              <TaskDetail task={selectedTask} />
            ) : state.loading && !state.exists ? (
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
                <TaskGroup title={t('chat.subagents.activeTitle')} tasks={activeTasks} emptyLabel={t('chat.subagents.noActive')} focusedTaskId={focusedTaskId} onSelect={setSelectedTaskId} />
                <TaskGroup title={t('chat.subagents.completedTitle', { count: state.counts.completed })} tasks={completedTasks} focusedTaskId={focusedTaskId} onSelect={setSelectedTaskId} />
                {endedTasks.length > 0 ? <TaskGroup title={t('chat.subagents.endedTitle', { count: state.counts.ended })} tasks={endedTasks} focusedTaskId={focusedTaskId} onSelect={setSelectedTaskId} /> : null}
              </>
            )}
          </div>
        </>
      ) : null}
    </aside>
  );
}
