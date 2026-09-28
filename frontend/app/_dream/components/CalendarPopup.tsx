// [Input] Calendar storage, auth context, i18n locale, timezone utils.
// [Output] Modal calendar popup with note entries and authorized scheduled Chat cards.
// [Pos] calendar-popup component in frontend/app/_dream/components
// [Sync] 2026-05-29: replace all hardcoded colors with CSS tokens / color-mix for dark theme support.
// [Sync] 2026-08-31: derive missing session day keys from persisted timestamps instead of today.
// [Sync] 2026-09-28: show planned/actual scheduled tasks for a date and revision-checked actions.
import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../i18n';
import {
  getCalendarData,
  getDateKey,
  getTodayKey,
  deleteEntry,
  type CalendarEntry,
} from '../utils/calendarStorage';
import type { UserSession } from '../api/voiceApi';
import { useAuth } from '../contexts/AuthContext';
import { getLocalDayKey, parseFlexibleTimestamp } from '../utils/timezone';
import {
  getScheduledDay, getScheduledHistory, getScheduledTask, updateScheduledTask,
  type ScheduledTask, type ScheduledTrigger, type ScheduledRule,
  type ScheduledTaskAction, ScheduledTaskApiError,
} from '../api/scheduledTaskApi';

interface Props {
  onLoadEntry: (entry: CalendarEntry) => void;
  onClose: () => void;
  currentEntryId?: string | null;
  onEntryDeleted?: (entryId: string) => void;
  timezone: string;
  initialDateKey?: string | null;
  onOpenTaskThread?: (threadId: string) => void;
}

type CalendarListEntry = {
  id: string;
  timestamp: number;
  firstLine: string;
  state?: CalendarEntry['state'];
};

function ScheduledTaskCard({ task, triggers, onAction, onOpenThread, dateLocale }: {
  task: ScheduledTask;
  triggers: ScheduledTrigger[];
  onAction: (task: ScheduledTask, action: ScheduledTaskAction,
    desired?: { title: string; prompt: string; rule: ScheduledRule }) => Promise<void>;
  onOpenThread?: (threadId: string) => void;
  dateLocale: string;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(task.title);
  const [prompt, setPrompt] = useState(task.prompt);
  const [kind, setKind] = useState<ScheduledRule['kind']>(task.rule.kind);
  const [localDate, setLocalDate] = useState(task.rule.kind === 'once' ? task.rule.local_date : '');
  const [localTime, setLocalTime] = useState(task.rule.local_time);
  const [timeZone, setTimeZone] = useState(task.rule.time_zone);
  const [offset, setOffset] = useState(task.rule.kind === 'once' && task.rule.selected_offset_minutes !== null
    ? String(task.rule.selected_offset_minutes) : '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<ScheduledTrigger[] | null>(null);
  const [historyError, setHistoryError] = useState(false);

  const perform = async (action: ScheduledTaskAction) => {
    setBusy(true);
    setError(null);
    try {
      let desired: { title: string; prompt: string; rule: ScheduledRule } | undefined;
      if (action === 'edit') {
        const rule: ScheduledRule = kind === 'once'
          ? { kind, local_date: localDate, local_time: localTime, time_zone: timeZone,
              selected_offset_minutes: offset.trim() === '' ? null : Number(offset) }
          : { kind, local_time: localTime, time_zone: timeZone };
        desired = { title: title.trim(), prompt: prompt.trim(), rule };
      }
      await onAction(task, action, desired);
      if (action === 'edit') setEditing(false);
      if (historyOpen) {
        const result = await getScheduledHistory(task.id);
        setHistory(result.triggers);
      }
    } catch (cause) {
      setError(cause instanceof ScheduledTaskApiError && cause.code === 'SCHEDULE_REVISION_CONFLICT'
        ? t('calendar.scheduledConflict') : t('calendar.scheduledActionError'));
    } finally {
      setBusy(false);
    }
  };

  const loadHistory = async () => {
    setHistoryError(false);
    try {
      setHistory((await getScheduledHistory(task.id)).triggers);
    } catch {
      setHistoryError(true);
    }
  };

  const toggleHistory = async () => {
    if (historyOpen) { setHistoryOpen(false); return; }
    setHistoryOpen(true);
    await loadHistory();
  };

  const displayTriggers = historyOpen ? (history ?? []) : triggers;
  const label = (status: string) => t(`calendar.scheduledStatus.${status}`, { defaultValue: status });
  const formatTime = (value: string) => new Date(value).toLocaleString(dateLocale, {
    timeZone: task.rule.time_zone, month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  return (
    <article style={{ padding: '14px 16px', borderRadius: 10,
      background: 'var(--color-bg-surface-solid)', color: 'var(--color-text-body)',
      boxShadow: '0 2px 8px var(--color-shadow-soft)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
        <strong>{task.title}</strong>
        <span>{label(task.status)}</span>
      </div>
      <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginTop: 6 }}>
        {task.rule.kind === 'once'
          ? `${task.rule.local_date} ${task.rule.local_time}`
          : `${t('calendar.scheduledDaily')} ${task.rule.local_time}`}
        {' · '}{task.rule.time_zone}
      </div>
      {task.next_run_at && <div style={{ fontSize: 13, marginTop: 3 }}>
        {t('calendar.scheduledNext')}: {formatTime(task.next_run_at)}
      </div>}
      {editing && <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
        <label>{t('calendar.scheduledTitle')}<input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
        <label>{t('calendar.scheduledPrompt')}<textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={3} /></label>
        <label>{t('calendar.scheduledRule')}<select value={kind} onChange={(event) => setKind(event.target.value as ScheduledRule['kind'])}>
          <option value="once">{t('calendar.scheduledOnce')}</option>
          <option value="daily">{t('calendar.scheduledDaily')}</option>
        </select></label>
        {kind === 'once' && <label>{t('calendar.scheduledDate')}<input type="date" value={localDate} onChange={(event) => setLocalDate(event.target.value)} /></label>}
        <label>{t('calendar.scheduledTime')}<input type="time" value={localTime} onChange={(event) => setLocalTime(event.target.value)} /></label>
        <label>{t('calendar.scheduledTimeZone')}<input value={timeZone} onChange={(event) => setTimeZone(event.target.value)} /></label>
        {kind === 'once' && <label>{t('calendar.scheduledOffset')}<input type="number" value={offset} onChange={(event) => setOffset(event.target.value)} /></label>}
        <div style={{ display: 'flex', gap: 8 }}>
          <button disabled={busy} onClick={() => void perform('edit')}>{t('calendar.scheduledSave')}</button>
          <button disabled={busy} onClick={() => setEditing(false)}>{t('calendar.scheduledCancel')}</button>
        </div>
      </div>}
      {error && <div role="alert" style={{ color: 'var(--color-state-error)', marginTop: 8 }}>{error}</div>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
        {!editing && task.status !== 'deleted' && task.status !== 'exhausted' &&
          <button disabled={busy} onClick={() => setEditing(true)}>{t('calendar.scheduledEdit')}</button>}
        {task.status === 'active' && <button disabled={busy} onClick={() => void perform('pause')}>{t('calendar.scheduledPause')}</button>}
        {task.status === 'paused' && <button disabled={busy} onClick={() => void perform('resume')}>{t('calendar.scheduledResume')}</button>}
        {(task.status === 'active' || task.status === 'exhausted') &&
          <button disabled={busy} onClick={() => void perform('run')}>{t('calendar.scheduledRun')}</button>}
        {task.status !== 'deleted'
          ? <button disabled={busy} onClick={() => void perform('delete')}>{t('calendar.scheduledDelete')}</button>
          : <button disabled={busy} onClick={() => void perform('restore')}>{t('calendar.scheduledRestore')}</button>}
        <button onClick={() => void toggleHistory()}>{t('calendar.scheduledHistory')}</button>
      </div>
      {historyError && <div role="alert">{t('calendar.scheduledUnavailable')}
        <button onClick={() => void loadHistory()}>{t('calendar.scheduledRetry')}</button></div>}
      {displayTriggers.map((trigger) => <div key={trigger.id} style={{ borderTop: '1px solid var(--color-border-paper)', marginTop: 10, paddingTop: 8, fontSize: 13 }}>
        <span>{trigger.scheduled_at ? formatTime(trigger.scheduled_at) : t('calendar.scheduledManual')}</span>
        {' · '}{label(trigger.status)}
        {trigger.status === 'failed' && <> · {t('calendar.scheduledFailure')}</>}
        {trigger.status === 'state_unknown' && <> · {t('calendar.scheduledUnknown')}</>}
        {trigger.target_thread_id && onOpenThread && <button style={{ marginLeft: 8 }}
          onClick={() => onOpenThread(trigger.target_thread_id!)}>{t('calendar.scheduledOpenThread')}</button>}
      </div>)}
    </article>
  );
}

export default function CalendarPopup({ onLoadEntry, onClose, currentEntryId, onEntryDeleted, timezone, initialDateKey, onOpenTaskThread }: Props) {
  const { isAuthenticated } = useAuth();
  const { t, i18n } = useTranslation();
  const dateLocale = getDateLocale(i18n.language);
  const [currentMonth, setCurrentMonth] = useState(() => {
    if (initialDateKey) {
      const [y, m] = initialDateKey.split('-').map(Number);
      return new Date(y, m - 1, 1);
    }
    return new Date();
  });
  const [selectedDate, setSelectedDate] = useState<string | null>(initialDateKey ?? getTodayKey());
  const [calendarData, setCalendarData] = useState<Record<string, CalendarListEntry[]>>({});
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([]);
  const [scheduledTriggers, setScheduledTriggers] = useState<ScheduledTrigger[]>([]);
  const [scheduledError, setScheduledError] = useState(false);
  const [scheduledLoading, setScheduledLoading] = useState(false);
  const [scheduledRefresh, setScheduledRefresh] = useState(0);
  const manualRequestKeys = useRef(new Map<string, string>());

  useEffect(() => {
    if (!isAuthenticated || !selectedDate) {
      setScheduledTasks([]);
      setScheduledTriggers([]);
      setScheduledError(false);
      return;
    }
    let active = true;
    setScheduledLoading(true);
    getScheduledDay(selectedDate, timezone).then(async (result) => {
      const known = new Set(result.tasks.map((task) => task.id));
      const historicalIds = [...new Set(result.triggers.map((trigger) => trigger.task_id))]
        .filter((id) => !known.has(id));
      const historical = await Promise.all(historicalIds.map((id) => getScheduledTask(id).catch(() => null)));
      if (!active) return;
      setScheduledTasks([...result.tasks, ...historical.flatMap((item) => item?.task ? [item.task] : [])]);
      setScheduledTriggers(result.triggers);
      setScheduledError(false);
    }).catch(() => {
      if (active) setScheduledError(true);
    }).finally(() => {
      if (active) setScheduledLoading(false);
    });
    return () => { active = false; };
  }, [isAuthenticated, selectedDate, timezone, scheduledRefresh]);

  const refreshScheduled = useCallback(() => setScheduledRefresh((value) => value + 1), []);

  const actOnTask = useCallback(async (task: ScheduledTask, action: ScheduledTaskAction,
    desired?: { title: string; prompt: string; rule: ScheduledRule }) => {
    const manualRequestKey = action === 'run'
      ? (manualRequestKeys.current.get(task.id) ?? crypto.randomUUID()) : null;
    if (manualRequestKey) manualRequestKeys.current.set(task.id, manualRequestKey);
    try {
      const body = action === 'run'
        ? { manual_request_key: manualRequestKey! }
        : action === 'edit'
          ? { expected_revision: task.revision, ...desired! }
          : { expected_revision: task.revision };
      await updateScheduledTask(task.id, action, body);
      if (action === 'run') manualRequestKeys.current.delete(task.id);
      refreshScheduled();
    } catch (error) {
      if (error instanceof ScheduledTaskApiError && error.code === 'SCHEDULE_REVISION_CONFLICT') {
        const latest = await getScheduledTask(task.id).catch(() => null);
        if (latest?.task) setScheduledTasks((items) => items.map((item) => item.id === task.id ? latest.task! : item));
      }
      throw error;
    }
  }, [refreshScheduled]);

  useEffect(() => {
    if (initialDateKey) {
      setSelectedDate(initialDateKey);
      const [y, m] = initialDateKey.split('-').map(Number);
      setCurrentMonth(new Date(y, m - 1, 1));
    }
  }, [initialDateKey]);

  const refreshCalendarData = useCallback(async () => {
    if (isAuthenticated) {
      try {
        const { listSessions } = await import('../api/voiceApi');
        const sessions = await listSessions(timezone);
        const grouped: Record<string, CalendarListEntry[]> = {};

        sessions.forEach((session: UserSession) => {
          const dayTimestamp = session.created_at || session.updated_at;
          const dateKey = session.date_key || getLocalDayKey(dayTimestamp, timezone);
          if (!dateKey) return;
          const tsRaw = session.updated_at || session.created_at;
          const ts = parseFlexibleTimestamp(tsRaw)?.getTime() ?? Date.now();
          const firstLine = session.first_line || session.name || 'Untitled';
          if (!grouped[dateKey]) grouped[dateKey] = [];
          grouped[dateKey].push({
            id: session.id,
            timestamp: ts,
            firstLine
          });
        });

        setCalendarData(grouped);
        return;
      } catch (error) {
        console.error('Failed to load calendar from database:', error);
      }
    }
    const localData = getCalendarData();
    const mapped: Record<string, CalendarListEntry[]> = {};
    Object.entries(localData).forEach(([dateKey, entries]) => {
      mapped[dateKey] = entries.map((entry) => ({
        id: entry.id,
        timestamp: entry.timestamp,
        firstLine: entry.firstLine,
        state: entry.state
      }));
    });
    setCalendarData(mapped);
  }, [isAuthenticated, timezone]);

  useEffect(() => {
    refreshCalendarData();
  }, [refreshCalendarData]);

  const today = getTodayKey();
  const datesWithEntries = Object.keys(calendarData);

  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const daysInMonth = lastDay.getDate();
  const startingDayOfWeek = firstDay.getDay();

  const days: Array<{ date: number; dateKey: string; hasEntries: boolean; isToday: boolean } | null> = [];

  for (let i = 0; i < startingDayOfWeek; i++) {
    days.push(null);
  }

  for (let date = 1; date <= daysInMonth; date++) {
    const dateObj = new Date(year, month, date);
    const dateKey = getDateKey(dateObj);
    days.push({
      date,
      dateKey,
      hasEntries: datesWithEntries.includes(dateKey),
      isToday: dateKey === today
    });
  }

  const handlePrevMonth = () => {
    setCurrentMonth(new Date(year, month - 1));
  };

  const handleNextMonth = () => {
    setCurrentMonth(new Date(year, month + 1));
  };

  const handleDateClick = (dateKey: string) => {
    setSelectedDate(dateKey);
  };

  const weekdayFormatter = new Intl.DateTimeFormat(dateLocale, { weekday: 'short' });
  const weekdayLabels = Array.from({ length: 7 }, (_, idx) => weekdayFormatter.format(new Date(Date.UTC(2023, 0, idx + 1))));

  const handleDeleteEntry = async (dateKey: string, entryId: string) => {
    if (confirm(t('calendar.deleteConfirm'))) {
      if (isAuthenticated) {
        try {
          const { deleteSession } = await import('../api/voiceApi');
          await deleteSession(entryId);
          await refreshCalendarData();
          onEntryDeleted?.(entryId);
        } catch (error) {
          console.error('Failed to delete from database:', error);
          alert(t('calendar.deleteError'));
        }
      } else {
        deleteEntry(dateKey, entryId);
        setCalendarData(getCalendarData());
        onEntryDeleted?.(entryId);
      }
    }
  };

  const selectedEntries = selectedDate ? calendarData[selectedDate] || [] : [];

  const handleOpenEntry = async (entry: CalendarListEntry) => {
    if (isAuthenticated) {
      try {
        const { getSession } = await import('../api/voiceApi');
        const full = await getSession(entry.id);
        if (!full?.editor_state) {
          alert(t('calendar.loadError'));
          return;
        }
        const payload: CalendarEntry = {
          id: entry.id,
          timestamp: entry.timestamp,
          state: full.editor_state,
          firstLine: entry.firstLine
        };
        onLoadEntry(payload);
        onClose();
      } catch (error) {
        console.error('Failed to load session:', error);
        alert(t('calendar.loadError'));
      }
    } else if (entry.state) {
      onLoadEntry(entry as CalendarEntry);
      onClose();
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'var(--color-bg-overlay)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000,
        backdropFilter: 'blur(4px)'
      }}
      onClick={onClose}
    >
      <div
        role="presentation"
        style={{
          display: 'flex',
          gap: '24px',
          alignItems: 'flex-start',
          justifyContent: 'center',
          maxWidth: '1100px',
          width: 'min(94vw, 1100px)',
          maxHeight: '85vh',
          margin: '0 auto'
        }}
      >
        {/* Calendar grid - LEFT */}
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            flex: '0 0 auto',
            width: '460px',
            background: 'var(--color-bg-paper)',
            border: '2px solid var(--color-border-paper)',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: '0 12px 40px var(--color-shadow-medium)',
            fontFamily: "'Excalifont', 'Xiaolai', 'Georgia', serif"
          }}
        >
          {/* Month header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '20px'
          }}>
            <button
              onClick={handlePrevMonth}
              style={{
                border: 'none',
                background: 'transparent',
                cursor: 'pointer',
                fontSize: '20px',
                padding: '8px 12px',
                borderRadius: '8px',
                color: 'var(--color-text-secondary)',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-bg-hover)';
                e.currentTarget.style.color = 'var(--color-text-body)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = 'var(--color-text-secondary)';
              }}
            >
              ‹
            </button>
            <div style={{
              fontSize: '20px',
              fontWeight: 600,
              color: 'var(--color-text-primary)',
              letterSpacing: '0.5px'
            }}>
              {currentMonth.toLocaleDateString(dateLocale, { month: 'long', year: 'numeric' })}
            </div>
            <button
              onClick={handleNextMonth}
              style={{
                border: 'none',
                background: 'transparent',
                cursor: 'pointer',
                fontSize: '20px',
                padding: '8px 12px',
                borderRadius: '8px',
                color: 'var(--color-text-secondary)',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-bg-hover)';
                e.currentTarget.style.color = 'var(--color-text-body)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = 'var(--color-text-secondary)';
              }}
            >
              ›
            </button>
          </div>

          {/* Weekday headers */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            gap: '4px',
            marginBottom: '8px'
          }}>
            {weekdayLabels.map((label, idx) => (
              <div key={`${label}-${idx}`} style={{
                textAlign: 'center',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-text-muted)',
                padding: '8px 0',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                {label}
              </div>
            ))}
          </div>

          {/* Days grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            gap: '6px'
          }}>
            {days.map((day, idx) => {
              if (!day) {
                return <div key={`empty-${idx}`} style={{ aspectRatio: '1' }} />;
              }

              const isSelected = selectedDate === day.dateKey;

              return (
                <button
                  key={day.dateKey}
                  onClick={() => handleDateClick(day.dateKey)}
                  style={{
                    aspectRatio: '1',
                    background: day.hasEntries
                      ? 'var(--color-bg-surface-solid)'
                      : 'transparent',
                    border: isSelected
                      ? '2px solid var(--color-border-focus)'
                      : 'none',
                    borderRadius: '10px',
                    cursor: 'pointer',
                    fontSize: '15px',
                    fontFamily: "'Excalifont', 'Xiaolai', 'Georgia', serif",
                    position: 'relative',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s',
                    boxShadow: day.hasEntries
                      ? '0 2px 8px var(--color-shadow-soft)'
                      : 'none',
                    color: 'var(--color-text-body)',
                    fontWeight: day.isToday || isSelected ? 700 : 400
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.transform = 'scale(1.05)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.transform = 'scale(1)';
                    }
                  }}
                >
                  {day.isToday ? (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 28,
                      height: 28,
                      borderRadius: '50%',
                      border: '2px solid var(--color-state-warning)',
                      color: 'var(--color-text-body)',
                      background: isSelected ? 'var(--color-bg-surface-solid)' : 'transparent'
                    }}>
                      {day.date}
                    </span>
                  ) : (
                    <span>{day.date}</span>
                  )}
                    {day.hasEntries && (
                      <div style={{
                        position: 'absolute',
                        bottom: '6px',
                        width: '5px',
                        height: '5px',
                        borderRadius: '50%',
                        background: 'var(--color-action-link)'
                      }} />
                    )}
                  </button>
                );
              })}
          </div>
        </div>

        {/* Entry list - RIGHT */}
        {selectedDate && (
          <div
            style={{
              flex: '1 1 380px',
              minWidth: '320px',
              maxWidth: '480px',
              maxHeight: '70vh',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            {/* Header */}
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                background: 'var(--color-bg-paper)',
                borderRadius: '12px 12px 0 0',
                padding: '16px 20px',
                borderBottom: '1px solid var(--color-border-paper)',
                backdropFilter: 'blur(8px)',
                boxShadow: '0 -4px 20px var(--color-shadow-soft)'
              }}
            >
              <div style={{
                fontSize: '16px',
                fontWeight: 600,
                color: 'var(--color-text-body)',
                fontFamily: "'Excalifont', 'Xiaolai', 'Georgia', serif"
              }}>
                {selectedDate === today
                  ? t('calendar.todayLabel')
                  : new Date(selectedDate + 'T00:00:00').toLocaleDateString(dateLocale, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    weekday: 'short'
                  })}
              </div>
              {selectedEntries.length > 0 && (
                <div style={{
                  fontSize: '13px',
                  color: 'var(--color-text-secondary)',
                  marginTop: '4px'
                }}>
                  {t('calendar.entriesLabel', { count: selectedEntries.length })}
                </div>
              )}
            </div>

            {/* Entries list */}
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                background: 'var(--color-bg-paper)',
                borderRadius: '0 0 12px 12px',
                padding: '12px',
                flex: 1,
                overflow: 'auto',
                backdropFilter: 'blur(8px)',
                boxShadow: '0 12px 40px var(--color-shadow-medium)'
              }}
            >
              {selectedEntries.length === 0 && scheduledTasks.length === 0 && scheduledTriggers.length === 0 && !scheduledLoading && !scheduledError ? (
                <div style={{
                  textAlign: 'center',
                  color: 'var(--color-text-muted)',
                  padding: '32px 20px',
                  fontSize: '14px',
                  fontFamily: "'Excalifont', 'Xiaolai', 'Georgia', serif"
                }}>
                  {t('calendar.noEntriesForDate')}
                </div>
              ) : (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px'
                }}>
                  {selectedEntries.map((entry) => {
                    const isCurrentEntry = currentEntryId === entry.id;
                    const time = new Date(entry.timestamp).toLocaleTimeString(dateLocale, {
                      hour: '2-digit',
                      minute: '2-digit'
                    });

                    return (
                      <div
                        key={entry.id}
                        style={{
                          borderRadius: '10px',
                          padding: '14px 16px',
                          background: isCurrentEntry
                            ? 'color-mix(in srgb, var(--color-state-success) 10%, var(--color-bg-surface-solid))'
                            : 'var(--color-bg-surface-solid)',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: '12px',
                          boxShadow: isCurrentEntry
                            ? `0 2px 12px var(--color-shadow-soft), inset 0 0 0 2px var(--color-state-success)`
                            : '0 2px 8px var(--color-shadow-soft)',
                          transition: 'all 0.2s',
                          minWidth: 0
                        }}
                      >
                        <button
                          title={t('calendar.openButton')}
                          onClick={() => handleOpenEntry(entry)}
                          style={{
                            flex: 1,
                            textAlign: 'left',
                            border: 'none',
                            background: 'transparent',
                            cursor: 'pointer',
                            padding: 0,
                            fontFamily: "'Excalifont', 'Xiaolai', 'Georgia', serif",
                            minWidth: 0
                          }}
                        >
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            marginBottom: '6px'
                          }}>
                            <div style={{
                              fontSize: '12px',
                              color: 'var(--color-text-secondary)',
                              fontWeight: 500,
                              flexShrink: 0
                            }}>
                              {time}
                            </div>
                            {isCurrentEntry && (
                              <span style={{
                                fontSize: '10px',
                                letterSpacing: '0.05em',
                                textTransform: 'uppercase',
                                padding: '3px 8px',
                                borderRadius: '999px',
                                background: 'var(--color-state-success)',
                                color: 'var(--color-text-on-action)',
                                fontWeight: 600,
                                flexShrink: 0
                              }}>
                                {t('calendar.currentEntryLabel')}
                              </span>
                            )}
                          </div>
                          <div style={{
                            fontSize: '14px',
                            color: 'var(--color-text-body)',
                            lineHeight: 1.4,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            display: 'block',
                            maxWidth: '100%'
                          }}>
                            {entry.firstLine}
                          </div>
                        </button>
                        <button
                          onClick={() => handleDeleteEntry(selectedDate, entry.id)}
                          style={{
                            border: 'none',
                            background: 'transparent',
                            borderRadius: '6px',
                            padding: '6px 10px',
                            cursor: 'pointer',
                            fontSize: '12px',
                            color: 'var(--color-text-muted)',
                            fontFamily: "'Excalifont', 'Xiaolai', 'Georgia', serif",
                            transition: 'all 0.2s',
                            flexShrink: 0
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'color-mix(in srgb, var(--color-state-danger) 12%, transparent)';
                            e.currentTarget.style.color = 'var(--color-state-danger)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'transparent';
                            e.currentTarget.style.color = 'var(--color-text-muted)';
                          }}
                        >
                          {t('calendar.deleteButton')}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
              {isAuthenticated && <div style={{ display: 'grid', gap: 10, marginTop: 12 }}>
                {scheduledLoading && <div>{t('calendar.scheduledLoading')}</div>}
                {scheduledError && <div role="alert">{t('calendar.scheduledUnavailable')}
                  <button onClick={refreshScheduled}>{t('calendar.scheduledRetry')}</button>
                </div>}
                {scheduledTasks.map((task) => <ScheduledTaskCard
                  key={task.id}
                  task={task}
                  triggers={scheduledTriggers.filter((trigger) => trigger.task_id === task.id)}
                  onAction={actOnTask}
                  onOpenThread={onOpenTaskThread}
                  dateLocale={dateLocale}
                />)}
              </div>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
