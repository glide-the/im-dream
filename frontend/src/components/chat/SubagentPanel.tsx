// [Input] Thread-keyed useThreadSubagents store and ChatView-controlled sidebar state.
// [Output] Compact subagent task header entry plus FileSidebar-shaped right detail panel.
// [Pos] claude-subagent summary/detail component in frontend/src/components/chat
// [Sync] 2026-08-04: task summary entry, chat-row task button, and focused active/completed/ended sidebar.
// [Sync] 2026-08-05: render the latest result through the shared ChatMarkdown/prose chain.
// [Sync] 2026-08-05: add a draggable/keyboard resize rail and readable operational typography.

import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../../i18n';
import {
  hydrateThreadSubagents,
  useThreadSubagents,
  type ThreadSubagentStatus,
  type ThreadSubagentTask,
} from '../../hooks/useThreadSubagents';
import ChatMarkdown from './ChatMarkdown';
import { IconLoader, IconSubagents, IconX } from './Icons';

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
  running: '#6ea8fe',
  completed: '#52c77e',
  failed: 'var(--color-state-error)',
  cancelled: 'var(--color-text-muted)',
};

function getSidebarWidthBounds(): { min: number; max: number } {
  if (typeof window === 'undefined') {
    return { min: MIN_SIDEBAR_WIDTH_PX, max: MAX_SIDEBAR_WIDTH_PX };
  }
  const responsiveMin = Math.min(MIN_SIDEBAR_WIDTH_PX, Math.max(280, window.innerWidth - MIN_CHAT_WIDTH_PX));
  const responsiveMax = Math.max(
    responsiveMin,
    Math.min(MAX_SIDEBAR_WIDTH_PX, window.innerWidth - MIN_CHAT_WIDTH_PX),
  );
  return { min: responsiveMin, max: responsiveMax };
}

function clampSidebarWidth(value: number): number {
  const { min, max } = getSidebarWidthBounds();
  return Math.min(max, Math.max(min, value));
}

function readInitialSidebarWidth(): number {
  if (typeof window === 'undefined') return DEFAULT_SIDEBAR_WIDTH_PX;
  try {
    const stored = Number(window.localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY));
    return clampSidebarWidth(Number.isFinite(stored) && stored > 0 ? stored : DEFAULT_SIDEBAR_WIDTH_PX);
  } catch {
    return clampSidebarWidth(DEFAULT_SIDEBAR_WIDTH_PX);
  }
}

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
  return (
    <li id={`thread-subagent-task-${task.taskId}`}>
      <button
        type="button"
        onClick={onSelect}
        aria-label={t('chat.subagents.openTask', { task: task.description })}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.8rem',
          minWidth: 0,
          padding: '0.9rem',
          borderRadius: '0.8rem',
          background: focused ? 'var(--color-bg-hover)' : 'var(--color-bg-paper)',
          border: '1px solid transparent',
          boxShadow: focused ? 'inset 3px 0 0 var(--color-action-link)' : 'none',
          color: 'inherit',
          cursor: 'pointer',
          font: 'inherit',
          textAlign: 'left',
          transition: 'background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease',
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
        <AgentAvatar task={task} size="2rem" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', minWidth: 0 }}>
            <span title={task.description} style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text-primary)', fontSize: '0.94rem', lineHeight: 1.35, fontWeight: 650 }}>
              {task.description}
            </span>
            <span style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: '0.3rem', color: STATUS_COLORS[task.status], fontSize: '0.74rem', fontWeight: 600 }}>
              <span style={{ width: '0.42rem', height: '0.42rem', borderRadius: '50%', background: 'currentColor' }} aria-hidden="true" />
              {t(`chat.subagents.status.${task.status}`)}
            </span>
          </div>
          <div title={task.summary ?? undefined} style={{ marginTop: '0.35rem', color: 'var(--color-text-muted)', fontSize: '0.82rem', lineHeight: 1.55, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
            {task.summary || task.agentType || t('chat.subagents.noSummary')}
          </div>
        </div>
        {duration ? (
          <span style={{ flexShrink: 0, paddingTop: '0.08rem', color: 'var(--color-text-muted)', fontSize: '0.76rem', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
            {duration}
          </span>
        ) : null}
        <span aria-hidden="true" style={{ flexShrink: 0, color: 'var(--color-text-muted)', fontSize: '1.05rem', lineHeight: 1.35 }}>›</span>
      </button>
    </li>
  );
}

function TaskGroup({ title, tasks, emptyLabel, focusedTaskId, onSelect }: { title: string; tasks: ThreadSubagentTask[]; emptyLabel?: string; focusedTaskId?: string | null; onSelect: (taskId: string) => void }) {
  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
      <h3 style={{ margin: 0, color: 'var(--color-text-secondary)', fontSize: '0.84rem', lineHeight: 1.4, fontWeight: 700, letterSpacing: '0.015em' }}>{title}</h3>
      {tasks.length > 0 ? (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
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
  const duration = formatDuration(task.durationMs, i18n.language) || t('chat.subagents.unknown');
  const startedAt = formatDateTime(task.startedAt, i18n.language) || t('chat.subagents.unknown');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.65rem' }}>
      <section style={{ padding: '1.2rem 1.25rem', borderRadius: '0.9rem', background: 'var(--color-bg-paper)', border: '1px solid var(--color-border-paper)', boxShadow: '0 1px 0 var(--color-shadow-soft)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.9rem' }}>
          <AgentAvatar task={task} size="2.5rem" />
          <div style={{ minWidth: 0, flex: 1 }}>
            <h2 style={{ margin: 0, color: 'var(--color-text-primary)', fontSize: '1.12rem', lineHeight: 1.4, fontWeight: 700, letterSpacing: '-0.01em' }}>{task.description}</h2>
            <div style={{ marginTop: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem', color: STATUS_COLORS[task.status], fontSize: '0.8rem', fontWeight: 650 }}>
              <span style={{ width: '0.42rem', height: '0.42rem', borderRadius: '50%', background: 'currentColor' }} aria-hidden="true" />
              {t(`chat.subagents.status.${task.status}`)}
            </div>
          </div>
        </div>

        <dl style={{ margin: '1.15rem 0 0', paddingTop: '1rem', borderTop: '1px solid var(--color-border-paper)', display: 'grid', gridTemplateColumns: 'minmax(6.5rem, auto) minmax(0, 1fr)', gap: '0.6rem 1.1rem', fontSize: '0.84rem', lineHeight: 1.45 }}>
          <dt style={{ color: 'var(--color-text-muted)', fontWeight: 550 }}>{t('chat.subagents.agentType')}</dt>
          <dd style={{ margin: 0, color: 'var(--color-text-secondary)', fontWeight: 550, overflowWrap: 'anywhere' }}>{task.agentType}</dd>
          <dt style={{ color: 'var(--color-text-muted)', fontWeight: 550 }}>{t('chat.subagents.startedAt')}</dt>
          <dd style={{ margin: 0, color: 'var(--color-text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{startedAt}</dd>
          <dt style={{ color: 'var(--color-text-muted)', fontWeight: 550 }}>{t('chat.subagents.duration')}</dt>
          <dd style={{ margin: 0, color: 'var(--color-text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{duration}</dd>
          {task.spawnDepth != null ? (
            <>
              <dt style={{ color: 'var(--color-text-muted)', fontWeight: 550 }}>{t('chat.subagents.spawnDepth')}</dt>
              <dd style={{ margin: 0, color: 'var(--color-text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{task.spawnDepth}</dd>
            </>
          ) : null}
        </dl>
      </section>

      {task.summary ? (
        <section>
          <h3 style={{ margin: '0 0 0.7rem', color: 'var(--color-text-secondary)', fontSize: '0.86rem', lineHeight: 1.4, fontWeight: 700, letterSpacing: '0.015em' }}>{t('chat.subagents.resultTitle')}</h3>
          <div style={{ padding: '1.1rem 1.15rem', borderRadius: '0.8rem', background: 'var(--color-bg-paper)', border: '1px solid color-mix(in srgb, var(--color-border-paper) 68%, transparent)', color: 'var(--color-text-primary)', fontSize: '0.94rem', lineHeight: 1.72, overflowWrap: 'anywhere' }}>
            <div className="prose prose-chat">
              <ChatMarkdown text={task.summary} />
            </div>
          </div>
        </section>
      ) : null}

      {task.error ? (
        <section style={{ padding: '1rem', borderRadius: '0.8rem', background: 'color-mix(in srgb, var(--color-state-error) 10%, transparent)', color: 'var(--color-state-error)', fontSize: '0.86rem', lineHeight: 1.6 }}>
          <strong style={{ display: 'block', marginBottom: '0.35rem' }}>{t('chat.subagents.errorTitle')}</strong>
          {task.error}
        </section>
      ) : null}

      <section>
        <h3 style={{ margin: '0 0 0.8rem', color: 'var(--color-text-secondary)', fontSize: '0.86rem', lineHeight: 1.4, fontWeight: 700, letterSpacing: '0.015em' }}>{t('chat.subagents.executionTitle')}</h3>
        {task.activity.length > 0 ? (
          <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column' }}>
            {task.activity.map((item, index) => {
              const timestamp = formatDateTime(item.timestamp, i18n.language);
              const label = item.kind === 'tool'
                ? t('chat.subagents.toolActivity', { tool: item.toolName || t('chat.subagents.toolFallback') })
                : t('chat.subagents.messageActivity');
              return (
                <li key={item.id} style={{ position: 'relative', display: 'grid', gridTemplateColumns: '1rem minmax(0, 1fr)', gap: '0.75rem', paddingBottom: index === task.activity.length - 1 ? 0 : '1rem' }}>
                  {index < task.activity.length - 1 ? <span aria-hidden="true" style={{ position: 'absolute', left: '0.47rem', top: '0.7rem', bottom: 0, width: '1px', background: 'var(--color-border-paper)' }} /> : null}
                  <span aria-hidden="true" style={{ position: 'relative', zIndex: 1, width: '0.55rem', height: '0.55rem', marginTop: '0.28rem', borderRadius: '50%', background: item.status === 'failed' ? 'var(--color-state-error)' : item.status === 'started' ? 'var(--color-action-link)' : 'var(--color-state-success)', border: '2px solid var(--color-bg-app)', boxSizing: 'content-box' }} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.9rem', color: 'var(--color-text-secondary)', fontSize: '0.84rem', lineHeight: 1.45, fontWeight: 650 }}>
                      <span>{label}</span>
                      {timestamp ? <time style={{ flexShrink: 0, color: 'var(--color-text-muted)', fontSize: '0.72rem', lineHeight: 1.5, fontWeight: 450, fontVariantNumeric: 'tabular-nums' }}>{timestamp}</time> : null}
                    </div>
                    {item.text ? <p style={{ margin: '0.3rem 0 0', color: 'var(--color-text-muted)', fontSize: '0.82rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.text}</p> : null}
                    {item.kind === 'tool' ? <div style={{ marginTop: '0.22rem', color: item.status === 'failed' ? 'var(--color-state-error)' : 'var(--color-text-muted)', fontSize: '0.74rem', lineHeight: 1.45 }}>{t(`chat.subagents.activityStatus.${item.status}`)}</div> : null}
                  </div>
                </li>
              );
            })}
          </ol>
        ) : (
          <div style={{ padding: '0.95rem 1rem', borderRadius: '0.75rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-muted)', fontSize: '0.84rem', lineHeight: 1.55 }}>{t('chat.subagents.noActivity')}</div>
        )}
      </section>
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
  const { t } = useTranslation();
  const state = useThreadSubagents(threadId);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(readInitialSidebarWidth);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeRailActive, setResizeRailActive] = useState(false);
  const sidebarWidthRef = useRef(sidebarWidth);
  const resizeStartRef = useRef<{ clientX: number; width: number } | null>(null);
  const bodyStyleRef = useRef<{ cursor: string; userSelect: string } | null>(null);

  useEffect(() => {
    sidebarWidthRef.current = sidebarWidth;
  }, [sidebarWidth]);

  const persistSidebarWidth = useCallback((width: number) => {
    try {
      window.localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(Math.round(width)));
    } catch {
      // Storage can be unavailable in hardened/private browser contexts.
    }
  }, []);

  const finishResize = useCallback(() => {
    if (!resizeStartRef.current) return;
    resizeStartRef.current = null;
    setIsResizing(false);
    persistSidebarWidth(sidebarWidthRef.current);
    if (bodyStyleRef.current) {
      document.body.style.cursor = bodyStyleRef.current.cursor;
      document.body.style.userSelect = bodyStyleRef.current.userSelect;
      bodyStyleRef.current = null;
    }
  }, [persistSidebarWidth]);

  const handleResizePointerDown = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    resizeStartRef.current = { clientX: event.clientX, width: sidebarWidthRef.current };
    bodyStyleRef.current = {
      cursor: document.body.style.cursor,
      userSelect: document.body.style.userSelect,
    };
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsResizing(true);
  }, []);

  const handleResizePointerMove = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    const start = resizeStartRef.current;
    if (!start) return;
    const nextWidth = clampSidebarWidth(start.width + start.clientX - event.clientX);
    sidebarWidthRef.current = nextWidth;
    setSidebarWidth(nextWidth);
  }, []);

  const handleResizePointerEnd = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    finishResize();
  }, [finishResize]);

  const resetSidebarWidth = useCallback(() => {
    const width = clampSidebarWidth(DEFAULT_SIDEBAR_WIDTH_PX);
    sidebarWidthRef.current = width;
    setSidebarWidth(width);
    persistSidebarWidth(width);
  }, [persistSidebarWidth]);

  const handleResizeKeyDown = useCallback((event: ReactKeyboardEvent<HTMLDivElement>) => {
    const { min, max } = getSidebarWidthBounds();
    const step = event.shiftKey ? 32 : 16;
    let nextWidth: number | null = null;
    if (event.key === 'ArrowLeft') nextWidth = sidebarWidthRef.current + step;
    if (event.key === 'ArrowRight') nextWidth = sidebarWidthRef.current - step;
    if (event.key === 'Home') nextWidth = min;
    if (event.key === 'End') nextWidth = max;
    if (nextWidth == null) return;
    event.preventDefault();
    const width = clampSidebarWidth(nextWidth);
    sidebarWidthRef.current = width;
    setSidebarWidth(width);
    persistSidebarWidth(width);
  }, [persistSidebarWidth]);

  useEffect(() => {
    if (!open) finishResize();
  }, [finishResize, open]);

  useEffect(() => {
    const handleWindowResize = () => {
      const width = clampSidebarWidth(sidebarWidthRef.current);
      sidebarWidthRef.current = width;
      setSidebarWidth(width);
    };
    window.addEventListener('resize', handleWindowResize);
    return () => window.removeEventListener('resize', handleWindowResize);
  }, []);

  useEffect(() => () => {
    resizeStartRef.current = null;
    if (bodyStyleRef.current) {
      document.body.style.cursor = bodyStyleRef.current.cursor;
      document.body.style.userSelect = bodyStyleRef.current.userSelect;
      bodyStyleRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (open) void hydrateThreadSubagents(threadId);
  }, [open, threadId]);

  const activeTasks = state.tasks.filter((task) => task.status === 'running');
  const completedTasks = state.tasks.filter((task) => task.status === 'completed');
  const endedTasks = state.tasks.filter((task) => task.status === 'failed' || task.status === 'cancelled');
  const focusedTaskId = state.tasks.find((task) => task.toolCallId === focusToolCallId)?.taskId ?? null;
  const selectedTask = state.tasks.find((task) => task.taskId === selectedTaskId) ?? null;
  const sidebarWidthBounds = getSidebarWidthBounds();

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
        width: open ? sidebarWidth : 0,
        minWidth: open ? sidebarWidth : 0,
        overflow: 'hidden',
        borderLeft: open ? '1px solid var(--color-border-paper)' : 'none',
        background: 'var(--color-bg-app)',
        transition: isResizing ? 'none' : 'width 0.25s ease, min-width 0.25s ease',
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
            aria-valuenow={Math.round(sidebarWidth)}
            aria-valuetext={`${Math.round(sidebarWidth)} px`}
            tabIndex={0}
            title={t('chat.subagents.resizeSidebar')}
            onPointerDown={handleResizePointerDown}
            onPointerMove={handleResizePointerMove}
            onPointerUp={handleResizePointerEnd}
            onPointerCancel={handleResizePointerEnd}
            onLostPointerCapture={finishResize}
            onDoubleClick={resetSidebarWidth}
            onKeyDown={handleResizeKeyDown}
            onMouseEnter={() => setResizeRailActive(true)}
            onMouseLeave={() => setResizeRailActive(false)}
            onFocus={() => setResizeRailActive(true)}
            onBlur={() => setResizeRailActive(false)}
            style={{
              position: 'absolute',
              inset: '0 auto 0 0',
              zIndex: 4,
              width: '0.65rem',
              cursor: 'col-resize',
              touchAction: 'none',
              outline: 'none',
              background: isResizing || resizeRailActive
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
                width: isResizing || resizeRailActive ? '0.15rem' : '1px',
                height: isResizing || resizeRailActive ? '4.5rem' : '100%',
                borderRadius: '999px',
                background: isResizing || resizeRailActive ? 'var(--color-action-link)' : 'var(--color-border-paper)',
                transform: 'translateY(-50%)',
                transition: 'height 0.14s ease, width 0.14s ease, background 0.14s ease',
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', minHeight: '3.75rem', padding: '0.9rem 1.25rem', borderBottom: '1px solid var(--color-border-paper)', boxSizing: 'border-box' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', color: 'var(--color-text-primary)' }}>
              {selectedTask ? (
                <button type="button" onClick={() => setSelectedTaskId(null)} aria-label={t('chat.subagents.backToTasks')} title={t('chat.subagents.backToTasks')} style={{ width: '1.8rem', height: '1.8rem', margin: '-0.35rem 0', border: 'none', borderRadius: '0.45rem', background: 'transparent', color: 'var(--color-text-secondary)', cursor: 'pointer', display: 'grid', placeItems: 'center', fontSize: '1.15rem' }}>←</button>
              ) : <IconSubagents style={{ width: '1.15rem', height: '1.15rem' }} />}
              <span style={{ fontSize: '0.96rem', lineHeight: 1.4, fontWeight: 700 }}>{selectedTask ? t('chat.subagents.detailTitle') : t('chat.subagents.title')}</span>
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

          <div style={{ flex: 1, overflowY: 'auto', padding: '1.35rem 1.4rem 1.75rem', display: 'flex', flexDirection: 'column', gap: '1.75rem' }} aria-live="polite">
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
