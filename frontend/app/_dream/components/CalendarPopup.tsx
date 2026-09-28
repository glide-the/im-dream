// [Input] Calendar storage, authenticated diary/scheduled-task APIs, locale, timezone, and shared dialog/navigation boundaries.
// [Output] Accessible responsive date workspace with scheduled-task summary/actions before independent diary entries.
// [Pos] Calendar/date-workspace dialog in frontend/app/_dream/components; Admin remains schedule and trigger owner.
// [Sync] 2026-09-29: add cursor history, bounded visible-page refresh, and explicit daylight-saving validation feedback.
import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../i18n';
import { getCalendarData, getDateKey, getTodayKey, deleteEntry, type CalendarEntry } from '../utils/calendarStorage';
import type { UserSession } from '../api/voiceApi';
import { useAuth } from '../contexts/AuthContext';
import { getLocalDayKey, parseFlexibleTimestamp } from '../utils/timezone';
import {
  getScheduledDay, getScheduledHistory, getScheduledTask, updateScheduledTask,
  type ScheduledTask, type ScheduledTrigger, type ScheduledRule, type ScheduledTaskAction,
  type ScheduledTaskDefinitionResult, type ScheduledTaskRunResult, ScheduledTaskApiError,
} from '../api/scheduledTaskApi';
import Modal from './chat/Modal';
import { IconMoreHorizontal } from './chat/Icons';
import './CalendarPopup.css';

interface Props {
  onLoadEntry: (entry: CalendarEntry) => void;
  onClose: () => void;
  currentEntryId?: string | null;
  onEntryDeleted?: (entryId: string) => void;
  timezone: string;
  initialDateKey?: string | null;
  onOpenTaskThread?: (threadId: string) => void;
}

type CalendarListEntry = { id: string; timestamp: number; firstLine: string; state?: CalendarEntry['state'] };
type ScheduledTaskDesired = { title: string; prompt: string; rule: ScheduledRule };
type ScheduledTaskActionResult = ScheduledTaskDefinitionResult | ScheduledTaskRunResult;
type EditDraft = {
  title: string; prompt: string; kind: ScheduledRule['kind']; localDate: string;
  localTime: string; timeZone: string; selectedOffsetMinutes: number | null;
};
type EditField = 'title' | 'prompt' | 'localDate' | 'localTime' | 'timeZone';

const UNRESOLVED_TRIGGER_STATES = new Set<ScheduledTrigger['status']>(['claimed', 'queued', 'running', 'state_unknown']);
const ACTIVE_TRIGGER_STATES = new Set<ScheduledTrigger['status']>(['claimed', 'queued', 'running']);
const SCHEDULED_HISTORY_PAGE_SIZE = 20;
const SCHEDULED_ACTIVE_REFRESH_INTERVAL_MS = 2_000;
const SCHEDULED_ACTIVE_REFRESH_MAXIMUM = 15;

class ScheduledTaskConflictError extends Error {
  constructor(readonly latest: ScheduledTask) { super('SCHEDULE_REVISION_CONFLICT'); }
}

function getTodayKeyInTimeZone(timeZone: string): string {
  return getLocalDayKey(new Date().toISOString(), timeZone) ?? getTodayKey();
}

function parseDateKey(dateKey: string): Date {
  const [year, month, day] = dateKey.split('-').map(Number);
  return new Date(year, month - 1, day);
}

function draftFromTask(task: ScheduledTask): EditDraft {
  return {
    title: task.title,
    prompt: task.prompt,
    kind: task.rule.kind,
    localDate: task.rule.kind === 'once' ? task.rule.local_date : '',
    localTime: task.rule.local_time,
    timeZone: task.rule.time_zone,
    selectedOffsetMinutes: task.rule.kind === 'once' ? task.rule.selected_offset_minutes : null,
  };
}

function desiredFromDraft(draft: EditDraft): ScheduledTaskDesired {
  const rule: ScheduledRule = draft.kind === 'once'
    ? { kind: 'once', local_date: draft.localDate, local_time: draft.localTime, time_zone: draft.timeZone,
        selected_offset_minutes: draft.selectedOffsetMinutes }
    : { kind: 'daily', local_time: draft.localTime, time_zone: draft.timeZone };
  return { title: draft.title.trim(), prompt: draft.prompt.trim(), rule };
}

function draftsEqual(left: EditDraft | null, right: EditDraft | null): boolean {
  return left !== null && right !== null && left.title === right.title && left.prompt === right.prompt
    && left.kind === right.kind && left.localDate === right.localDate && left.localTime === right.localTime
    && left.timeZone === right.timeZone && left.selectedOffsetMinutes === right.selectedOffsetMinutes;
}

function isValidDateKey(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

function validateDraft(draft: EditDraft): Partial<Record<EditField, string>> {
  const errors: Partial<Record<EditField, string>> = {};
  if (!draft.title.trim()) errors.title = 'required';
  if (!draft.prompt.trim()) errors.prompt = 'required';
  if (draft.kind === 'once' && !isValidDateKey(draft.localDate)) errors.localDate = 'required';
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(draft.localTime)) errors.localTime = 'required';
  try { new Intl.DateTimeFormat('en', { timeZone: draft.timeZone.trim() }).format(new Date()); }
  catch { errors.timeZone = 'invalid'; }
  return errors;
}

function triggerTimestamp(trigger: ScheduledTrigger): number {
  return parseFlexibleTimestamp(trigger.created_at)?.getTime() ?? 0;
}

function recentTrigger(triggers: ScheduledTrigger[]): ScheduledTrigger | null {
  const priority: Record<ScheduledTrigger['status'], number> = {
    state_unknown: 0, failed: 1, running: 2, queued: 2, claimed: 2, succeeded: 3, skipped: 3,
  };
  return [...triggers].sort((left, right) => (
    priority[left.status] - priority[right.status] || triggerTimestamp(right) - triggerTimestamp(left)
  ))[0] ?? null;
}

function ScheduledTaskCard({ task, triggers, onAction, onOpenThread, onRefresh, onLayerChange,
  onDraftDirtyChange, onCardRef, dateLocale }: {
  task: ScheduledTask;
  triggers: ScheduledTrigger[];
  onAction: (task: ScheduledTask, action: ScheduledTaskAction, desired?: ScheduledTaskDesired) => Promise<ScheduledTaskActionResult>;
  onOpenThread?: (threadId: string) => void;
  onRefresh: () => void;
  onLayerChange: (key: string, closer: (() => void) | null) => void;
  onDraftDirtyChange: (taskId: string, dirty: boolean) => void;
  onCardRef: (taskId: string, element: HTMLElement | null) => void;
  dateLocale: string;
}) {
  const { t } = useTranslation();
  const editPanelId = useId();
  const historyPanelId = useId();
  const moreMenuId = useId();
  const moreButtonRef = useRef<HTMLButtonElement>(null);
  const moreMenuRef = useRef<HTMLDivElement>(null);
  const firstEditFieldRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<EditDraft | null>(null);
  const [defaultDraft, setDefaultDraft] = useState<EditDraft | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<EditField, string>>>({});
  const [conflictLatest, setConflictLatest] = useState<ScheduledTask | null>(null);
  const [busyAction, setBusyAction] = useState<ScheduledTaskAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runOutcomeUnknown, setRunOutcomeUnknown] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<ScheduledTrigger[] | null>(null);
  const [historyError, setHistoryError] = useState(false);
  const [historyHasMore, setHistoryHasMore] = useState(false);
  const [historyLoadingMore, setHistoryLoadingMore] = useState(false);
  const [historyLoadMoreError, setHistoryLoadMoreError] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const editing = draft !== null;
  const dirty = editing && !draftsEqual(draft, defaultDraft);

  const loadHistory = useCallback(async () => {
    setHistoryError(false); setHistoryLoadMoreError(false);
    try {
      const result = await getScheduledHistory(task.id, SCHEDULED_HISTORY_PAGE_SIZE);
      setHistory(result.triggers);
      setHistoryHasMore(result.triggers.length === SCHEDULED_HISTORY_PAGE_SIZE);
      return result.triggers;
    } catch { setHistoryError(true); return null; }
  }, [task.id]);

  const loadOlderHistory = useCallback(async () => {
    if (!history?.length || historyLoadingMore) return;
    setHistoryLoadingMore(true); setHistoryLoadMoreError(false);
    try {
      const oldestCreatedAt = [...history].sort((left, right) => triggerTimestamp(left) - triggerTimestamp(right))[0]?.created_at;
      if (!oldestCreatedAt) { setHistoryHasMore(false); return; }
      const result = await getScheduledHistory(task.id, SCHEDULED_HISTORY_PAGE_SIZE, oldestCreatedAt);
      setHistory((current) => {
        const merged = new Map((current ?? []).map((trigger) => [trigger.id, trigger]));
        result.triggers.forEach((trigger) => merged.set(trigger.id, trigger));
        return [...merged.values()];
      });
      setHistoryHasMore(result.triggers.length === SCHEDULED_HISTORY_PAGE_SIZE);
    } catch { setHistoryLoadMoreError(true); }
    finally { setHistoryLoadingMore(false); }
  }, [history, historyLoadingMore, task.id]);

  useEffect(() => {
    let active = true;
    getScheduledHistory(task.id, SCHEDULED_HISTORY_PAGE_SIZE).then((result) => { if (active) {
      setHistory(result.triggers); setHistoryHasMore(result.triggers.length === SCHEDULED_HISTORY_PAGE_SIZE);
    } })
      .catch(() => { if (active) setHistoryError(true); });
    return () => { active = false; };
  }, [task.id, task.revision]);

  useEffect(() => {
    onDraftDirtyChange(task.id, dirty);
    return () => onDraftDirtyChange(task.id, false);
  }, [dirty, onDraftDirtyChange, task.id]);

  const closeEditing = useCallback(() => {
    if (dirty && !window.confirm(t('calendar.scheduledDiscardConfirm'))) return;
    setDraft(null); setDefaultDraft(null); setFieldErrors({}); setConflictLatest(null);
    requestAnimationFrame(() => moreButtonRef.current?.focus());
  }, [dirty, t]);
  const closeHistory = useCallback(() => {
    setHistoryOpen(false); requestAnimationFrame(() => moreButtonRef.current?.focus());
  }, []);
  const closeMore = useCallback(() => {
    setMoreOpen(false); requestAnimationFrame(() => moreButtonRef.current?.focus());
  }, []);

  useEffect(() => {
    const layerKey = `scheduled-task-${task.id}`;
    if (moreOpen) onLayerChange(layerKey, closeMore);
    else if (editing) onLayerChange(layerKey, closeEditing);
    else if (historyOpen) onLayerChange(layerKey, closeHistory);
    else onLayerChange(layerKey, null);
    return () => onLayerChange(layerKey, null);
  }, [closeEditing, closeHistory, closeMore, editing, historyOpen, moreOpen, onLayerChange, task.id]);

  useEffect(() => { if (editing) requestAnimationFrame(() => firstEditFieldRef.current?.focus()); }, [editing]);

  const knownTriggers = useMemo(() => {
    const merged = new Map((history ?? []).map((trigger) => [trigger.id, trigger]));
    triggers.forEach((trigger) => merged.set(trigger.id, trigger));
    return [...merged.values()];
  }, [history, triggers]);
  const summaryTrigger = recentTrigger(knownTriggers);
  const unresolved = knownTriggers.some((trigger) => UNRESOLVED_TRIGGER_STATES.has(trigger.status));
  const stateUnknown = knownTriggers.some((trigger) => trigger.status === 'state_unknown');
  const actionLabel = (action: string) => t('calendar.scheduledActionAria', { action, title: task.title });
  const statusLabel = (status: string) => t(`calendar.scheduledStatus.${status}`, { defaultValue: status });
  const formatTime = (value: string) => new Date(value).toLocaleString(dateLocale, {
    timeZone: task.rule.time_zone, month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
  const formatTriggerTime = (trigger: ScheduledTrigger) => formatTime(trigger.scheduled_at ?? trigger.created_at);
  const planText = (definition: ScheduledTask = task) => definition.rule.kind === 'once'
    ? `${definition.rule.local_date} ${definition.rule.local_time} (${definition.rule.time_zone})`
    : `${t('calendar.scheduledDaily')} ${definition.rule.local_time} (${definition.rule.time_zone})`;

  const openEditing = () => {
    const nextDraft = draftFromTask(task);
    setDefaultDraft(nextDraft); setDraft(nextDraft); setFieldErrors({}); setConflictLatest(null);
    setError(null); setMoreOpen(false);
  };

  const toggleMore = () => {
    setMoreOpen((current) => {
      const next = !current;
      if (next) requestAnimationFrame(() => moreMenuRef.current?.querySelector<HTMLButtonElement>('button')?.focus());
      return next;
    });
  };
  const handleMoreKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const items = [...(moreMenuRef.current?.querySelectorAll<HTMLButtonElement>('button') ?? [])];
    if (items.length === 0) return;
    const current = Math.max(0, items.indexOf(document.activeElement as HTMLButtonElement));
    const next = event.key === 'ArrowDown' ? (current + 1) % items.length
      : event.key === 'ArrowUp' ? (current - 1 + items.length) % items.length
        : event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : null;
    if (next === null) return;
    event.preventDefault(); items[next].focus();
  };

  const perform = async (action: ScheduledTaskAction) => {
    let desired: ScheduledTaskDesired | undefined;
    if (action === 'edit') {
      if (!draft) return;
      const validation = validateDraft(draft);
      setFieldErrors(validation);
      if (Object.keys(validation).length > 0) return;
      desired = desiredFromDraft(draft);
    }
    setBusyAction(action); setError(null);
    try {
      const result = await onAction(action === 'edit' && conflictLatest ? conflictLatest : task, action, desired);
      if ('trigger' in result) {
        setHistory((items) => items
          ? [result.trigger, ...items.filter((item) => item.id !== result.trigger.id)]
          : [result.trigger]);
      }
      if (action === 'edit') { setDraft(null); setDefaultDraft(null); setConflictLatest(null); }
      if (action === 'run') setRunOutcomeUnknown(false);
      if (historyOpen) await loadHistory();
    } catch (cause) {
      if (cause instanceof ScheduledTaskConflictError && action === 'edit') {
        setConflictLatest(cause.latest); setError(t('calendar.scheduledConflict'));
      } else if (cause instanceof ScheduledTaskApiError && cause.code === 'SCHEDULE_LOCAL_TIME_MISSING') {
        setError(t('calendar.scheduledLocalTimeMissing'));
      } else if (cause instanceof ScheduledTaskApiError && cause.code === 'SCHEDULE_OFFSET_REQUIRED') {
        setError(t('calendar.scheduledOffsetRequired'));
      } else if (cause instanceof ScheduledTaskApiError && cause.code === 'SCHEDULE_OFFSET_INVALID') {
        setError(t('calendar.scheduledOffsetInvalid'));
      } else if (cause instanceof ScheduledTaskApiError
        && ['SCHEDULE_INPUT_INVALID', 'SCHEDULE_RULE_INVALID', 'SCHEDULE_DATE_INVALID',
          'SCHEDULE_TIME_INVALID', 'SCHEDULE_TIME_ZONE_INVALID'].includes(cause.code)) {
        setError(t('calendar.scheduledInputInvalid'));
      } else if (action === 'run' && !(cause instanceof ScheduledTaskApiError)) {
        setRunOutcomeUnknown(true); setError(t('calendar.scheduledRunOutcomeUnknown'));
      } else { setError(t('calendar.scheduledActionError')); }
    } finally { setBusyAction(null); }
  };

  const updateDraft = (change: Partial<EditDraft>, scheduleChanged = false) => {
    setDraft((current) => current ? { ...current, ...change,
      ...(scheduleChanged ? { selectedOffsetMinutes: null } : {}) } : current);
  };

  const conflictFields = useMemo(() => {
    if (!draft || !conflictLatest) return [];
    const latest = draftFromTask(conflictLatest);
    const fields: string[] = [];
    if (draft.title.trim() !== latest.title) fields.push(t('calendar.scheduledTitle'));
    if (draft.prompt.trim() !== latest.prompt) fields.push(t('calendar.scheduledPrompt'));
    if (draft.kind !== latest.kind) fields.push(t('calendar.scheduledRule'));
    if (draft.kind === 'once' && draft.localDate !== latest.localDate) fields.push(t('calendar.scheduledDate'));
    if (draft.localTime !== latest.localTime) fields.push(t('calendar.scheduledTime'));
    if (draft.timeZone.trim() !== latest.timeZone) fields.push(t('calendar.scheduledTimeZone'));
    return fields;
  }, [conflictLatest, draft, t]);

  if (task.status === 'deleted') {
    return <article ref={(element) => onCardRef(task.id, element)} tabIndex={-1}
      className="calendar-popup__undo-row" aria-label={`${statusLabel(task.status)}: ${task.title}`}>
      <div><strong>{t('calendar.scheduledDeletedTitle', { title: task.title })}</strong>
        {unresolved ? <span aria-live="polite">{t('calendar.scheduledDeletedRunning')}</span> : null}</div>
      <button type="button" className="calendar-popup__button calendar-popup__button--secondary"
        disabled={busyAction !== null} aria-label={actionLabel(t('calendar.scheduledRestore'))}
        onClick={() => void perform('restore')}>
        {busyAction === 'restore' ? t('calendar.scheduledSaving') : t('calendar.scheduledRestore')}
      </button>
      {error ? <div className="calendar-popup__alert" role="alert">{error}</div> : null}
    </article>;
  }

  const historyRows = [...(history ?? [])].sort((left, right) => triggerTimestamp(right) - triggerTimestamp(left));
  return <article ref={(element) => onCardRef(task.id, element)} tabIndex={-1}
    className={`calendar-popup__task calendar-popup__task--${summaryTrigger?.status ?? task.status}`}>
    <div className="calendar-popup__task-heading">
      <div><h4>{task.title}</h4><span className={`calendar-popup__status calendar-popup__status--${task.status}`}>
        {statusLabel(task.status)}</span></div>
      <div className="calendar-popup__more-wrap">
        <button ref={moreButtonRef} type="button" className="calendar-popup__icon-button"
          aria-label={actionLabel(t('calendar.scheduledMore'))} aria-haspopup="menu" aria-expanded={moreOpen}
          aria-controls={moreMenuId} disabled={busyAction !== null} onClick={toggleMore}>
          <IconMoreHorizontal aria-hidden="true" />
        </button>
        {moreOpen ? <div ref={moreMenuRef} id={moreMenuId} className="calendar-popup__more-menu" role="menu"
          onKeyDown={handleMoreKeyDown}>
          {(task.status === 'active' || task.status === 'paused') ?
            <button type="button" role="menuitem"
              aria-label={actionLabel(t('calendar.scheduledEdit'))} onClick={openEditing}>{t('calendar.scheduledEdit')}</button> : null}
          <button type="button" role="menuitem" aria-label={actionLabel(t('calendar.scheduledHistory'))} onClick={() => {
            setMoreOpen(false); setHistoryOpen(true); if (history === null) void loadHistory();
          }}>{t('calendar.scheduledHistory')}</button>
          <button type="button" role="menuitem" className="calendar-popup__danger-action"
            aria-label={actionLabel(t('calendar.scheduledDelete'))}
            onClick={() => { setMoreOpen(false); void perform('delete'); }}>{t('calendar.scheduledDelete')}</button>
        </div> : null}
      </div>
    </div>
    <dl className="calendar-popup__task-facts">
      <div><dt>{t('calendar.scheduledRule')}</dt><dd>{planText()}</dd></div>
      <div><dt>{t('calendar.scheduledNext')}</dt><dd>{task.next_run_at ? formatTime(task.next_run_at)
        : task.status === 'paused' ? t('calendar.scheduledNextPaused')
          : task.status === 'exhausted' ? t('calendar.scheduledNextExhausted')
            : t('calendar.scheduledNextUnavailable')}</dd></div>
    </dl>
    <div className="calendar-popup__recent" aria-live="polite">
      <span>{t('calendar.scheduledRecent')}</span>
      {summaryTrigger ? <div><strong>{statusLabel(summaryTrigger.status)}</strong><small>{formatTriggerTime(summaryTrigger)}</small>
        {summaryTrigger.status === 'failed' ? <p>{t('calendar.scheduledFailure')}</p> : null}
        {summaryTrigger.status === 'state_unknown' ? <p>{t('calendar.scheduledUnknown')}</p> : null}
        {summaryTrigger.status === 'skipped' ? <p>{t('calendar.scheduledSkipped')}</p> : null}</div>
        : <strong>{t('calendar.scheduledNeverRun')}</strong>}
    </div>
    <div className="calendar-popup__primary-actions">
      {(task.status === 'active' || task.status === 'exhausted') ? <button type="button"
        className="calendar-popup__button calendar-popup__button--primary"
        disabled={busyAction !== null || stateUnknown}
        aria-label={actionLabel(runOutcomeUnknown ? t('calendar.scheduledCheckRun') : t('calendar.scheduledRun'))}
        title={stateUnknown ? t('calendar.scheduledRunBlocked') : undefined} onClick={() => void perform('run')}>
        {busyAction === 'run' ? t('calendar.scheduledRequesting')
          : runOutcomeUnknown ? t('calendar.scheduledCheckRun') : t('calendar.scheduledRun')}</button> : null}
      {task.status === 'active' ? <button type="button" className="calendar-popup__button calendar-popup__button--secondary"
        disabled={busyAction !== null} aria-label={actionLabel(t('calendar.scheduledPause'))}
        onClick={() => void perform('pause')}>{t('calendar.scheduledPause')}</button> : null}
      {task.status === 'paused' ? <button type="button" className="calendar-popup__button calendar-popup__button--secondary"
        disabled={busyAction !== null} aria-label={actionLabel(t('calendar.scheduledResume'))}
        onClick={() => void perform('resume')}>{t('calendar.scheduledResume')}</button> : null}
      {summaryTrigger?.target_thread_id && onOpenThread && task.status !== 'exhausted' ? <button type="button"
        className="calendar-popup__button calendar-popup__button--quiet"
        aria-label={actionLabel(t('calendar.scheduledOpenThread'))}
        onClick={() => onOpenThread(summaryTrigger.target_thread_id!)}>{t('calendar.scheduledOpenThread')}</button> : null}
    </div>
    {stateUnknown ? <p className="calendar-popup__hint" aria-live="polite">{t('calendar.scheduledRunBlocked')}</p> : null}
    {error ? <div className="calendar-popup__alert" role="alert"><span>{error}</span></div> : null}

    {editing && draft ? <form id={editPanelId} className="calendar-popup__edit-panel"
      onSubmit={(event) => { event.preventDefault(); void perform('edit'); }}>
      <h5>{t('calendar.scheduledEditTitle', { title: task.title })}</h5>
      <label><span>{t('calendar.scheduledTitle')}</span><input ref={firstEditFieldRef} value={draft.title}
        aria-invalid={Boolean(fieldErrors.title)} onChange={(event) => updateDraft({ title: event.target.value })} />
        {fieldErrors.title ? <small role="alert">{t('calendar.scheduledFieldRequired')}</small> : null}</label>
      <label><span>{t('calendar.scheduledPrompt')}</span><textarea value={draft.prompt} rows={4}
        aria-invalid={Boolean(fieldErrors.prompt)} onChange={(event) => updateDraft({ prompt: event.target.value })} />
        {fieldErrors.prompt ? <small role="alert">{t('calendar.scheduledFieldRequired')}</small> : null}</label>
      <label><span>{t('calendar.scheduledRule')}</span><select value={draft.kind}
        onChange={(event) => updateDraft({ kind: event.target.value as ScheduledRule['kind'] }, true)}>
        <option value="once">{t('calendar.scheduledOnce')}</option><option value="daily">{t('calendar.scheduledDaily')}</option>
      </select></label>
      {draft.kind === 'once' ? <label><span>{t('calendar.scheduledDate')}</span><input type="date" value={draft.localDate}
        aria-invalid={Boolean(fieldErrors.localDate)} onChange={(event) => updateDraft({ localDate: event.target.value }, true)} />
        {fieldErrors.localDate ? <small role="alert">{t('calendar.scheduledFieldRequired')}</small> : null}</label> : null}
      <label><span>{t('calendar.scheduledTime')}</span><input type="time" value={draft.localTime}
        aria-invalid={Boolean(fieldErrors.localTime)} onChange={(event) => updateDraft({ localTime: event.target.value }, true)} />
        {fieldErrors.localTime ? <small role="alert">{t('calendar.scheduledFieldRequired')}</small> : null}</label>
      <label><span>{t('calendar.scheduledTimeZone')}</span><input value={draft.timeZone}
        aria-invalid={Boolean(fieldErrors.timeZone)} onChange={(event) => updateDraft({ timeZone: event.target.value }, true)} />
        {fieldErrors.timeZone ? <small role="alert">{t('calendar.scheduledTimeZoneInvalid')}</small> : null}</label>
      {draft.kind === 'once' && draft.selectedOffsetMinutes !== null ? <p className="calendar-popup__offset-note">
        {t('calendar.scheduledSelectedOffset', { offset: draft.selectedOffsetMinutes })}</p> : null}
      {conflictLatest ? <div className="calendar-popup__conflict" role="alert">
        <strong>{t('calendar.scheduledLatestEffective')}</strong><p>{conflictLatest.title} · {planText(conflictLatest)}</p>
        <p>{t('calendar.scheduledConflictFields', { fields: conflictFields.length > 0
          ? conflictFields.join(', ') : t('calendar.scheduledConflictNoFields') })}</p>
        <div><button type="submit" disabled={busyAction !== null}
          aria-label={actionLabel(t('calendar.scheduledRetryLatest'))}>{t('calendar.scheduledRetryLatest')}</button>
          <button type="button" aria-label={actionLabel(t('calendar.scheduledDiscardDraft'))}
            onClick={() => { setDraft(null); setDefaultDraft(null); setConflictLatest(null);
            setError(null); requestAnimationFrame(() => moreButtonRef.current?.focus()); }}>
            {t('calendar.scheduledDiscardDraft')}</button></div>
      </div> : null}
      <div className="calendar-popup__edit-actions"><button type="submit"
        className="calendar-popup__button calendar-popup__button--primary" disabled={busyAction !== null}
        aria-label={actionLabel(t('calendar.scheduledSave'))}>
        {busyAction === 'edit' ? t('calendar.scheduledSaving') : t('calendar.scheduledSave')}</button>
        <button type="button" className="calendar-popup__button calendar-popup__button--quiet"
          aria-label={actionLabel(t('calendar.scheduledCancel'))} onClick={closeEditing}>
          {t('calendar.scheduledCancel')}</button></div>
    </form> : null}

    {historyOpen ? <section id={historyPanelId} className="calendar-popup__history" aria-labelledby={`${historyPanelId}-title`}>
      <div className="calendar-popup__subpanel-heading"><h5 id={`${historyPanelId}-title`}>
        {t('calendar.scheduledHistoryTitle', { title: task.title })}</h5>
        <button type="button" className="calendar-popup__button calendar-popup__button--quiet"
          aria-label={actionLabel(t('calendar.scheduledClosePanel'))} onClick={closeHistory}>
          {t('calendar.scheduledClosePanel')}</button></div>
      {historyError ? <div className="calendar-popup__alert" role="alert">{t('calendar.scheduledHistoryUnavailable')}
        <button type="button" aria-label={actionLabel(t('calendar.scheduledRetry'))}
          onClick={() => void loadHistory()}>{t('calendar.scheduledRetry')}</button></div>
        : history === null ? <div className="calendar-popup__loading" aria-live="polite">{t('calendar.scheduledLoadingHistory')}</div>
          : historyRows.length === 0 ? <p>{t('calendar.scheduledNoHistory')}</p> : <ol>{historyRows.map((trigger) => <li key={trigger.id}>
            <div><strong>{trigger.kind === 'manual' ? t('calendar.scheduledManual') : t('calendar.scheduledPlanned')}</strong>
              <span className={`calendar-popup__status calendar-popup__status--${trigger.status}`}>{statusLabel(trigger.status)}</span></div>
            <time>{formatTriggerTime(trigger)}</time>
            {trigger.status === 'failed' ? <p>{t('calendar.scheduledFailure')}</p> : null}
            {trigger.status === 'state_unknown' ? <p>{t('calendar.scheduledUnknown')}</p> : null}
            {trigger.status === 'skipped' ? <p>{t('calendar.scheduledSkipped')}</p> : null}
            {trigger.target_thread_id && onOpenThread ? <button type="button"
              className="calendar-popup__button calendar-popup__button--quiet" aria-label={actionLabel(t('calendar.scheduledOpenThread'))}
              onClick={() => onOpenThread(trigger.target_thread_id!)}>{t('calendar.scheduledOpenThread')}</button> : null}
          </li>)}</ol>}
      {!historyError && history !== null && historyHasMore ? <button type="button"
        className="calendar-popup__button calendar-popup__button--secondary calendar-popup__history-more"
        disabled={historyLoadingMore} aria-label={actionLabel(t('calendar.scheduledLoadOlder'))}
        onClick={() => void loadOlderHistory()}>
        {historyLoadingMore ? t('calendar.scheduledLoadingOlder') : t('calendar.scheduledLoadOlder')}
      </button> : null}
      {historyLoadMoreError ? <div className="calendar-popup__alert" role="alert">
        {t('calendar.scheduledOlderHistoryUnavailable')}
        <button type="button" aria-label={actionLabel(t('calendar.scheduledRetry'))}
          onClick={() => void loadOlderHistory()}>{t('calendar.scheduledRetry')}</button>
      </div> : null}
    </section> : null}
    {runOutcomeUnknown ? <button type="button" className="calendar-popup__refresh-link" onClick={onRefresh}>
      {t('calendar.scheduledRefreshDate')}</button> : null}
  </article>;
}

export default function CalendarPopup({ onLoadEntry, onClose, currentEntryId, onEntryDeleted, timezone,
  initialDateKey, onOpenTaskThread }: Props) {
  const { isAuthenticated } = useAuth();
  const { t, i18n } = useTranslation();
  const dateLocale = getDateLocale(i18n.language);
  const initialSelectedDate = initialDateKey ?? getTodayKeyInTimeZone(timezone);
  const [currentMonth, setCurrentMonth] = useState(() => {
    const initial = parseDateKey(initialSelectedDate);
    return new Date(initial.getFullYear(), initial.getMonth(), 1);
  });
  const [selectedDate, setSelectedDate] = useState<string | null>(initialSelectedDate);
  const [calendarFocusKey, setCalendarFocusKey] = useState(initialSelectedDate);
  const [calendarData, setCalendarData] = useState<Record<string, CalendarListEntry[]>>({});
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([]);
  const [scheduledTriggers, setScheduledTriggers] = useState<ScheduledTrigger[]>([]);
  const [scheduledError, setScheduledError] = useState(false);
  const [scheduledLoading, setScheduledLoading] = useState(false);
  const [scheduledRefresh, setScheduledRefresh] = useState(0);
  const [documentVisible, setDocumentVisible] = useState(() => typeof document === 'undefined'
    || document.visibilityState === 'visible');
  const [activeRefreshExhausted, setActiveRefreshExhausted] = useState(false);
  const monthPrevRef = useRef<HTMLButtonElement>(null);
  const dateButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const pendingDateFocusRef = useRef<string | null>(null);
  const subpanelClosersRef = useRef(new Map<string, () => void>());
  const dirtyDraftsRef = useRef(new Map<string, boolean>());
  const taskCardRefs = useRef(new Map<string, HTMLElement>());
  const manualRequestKeys = useRef(new Map<string, string>());
  const activeRefreshCountRef = useRef(0);

  useEffect(() => {
    setScheduledTasks([]); setScheduledTriggers([]); setScheduledError(false); setScheduledLoading(false);
  }, [isAuthenticated, selectedDate, timezone]);

  useEffect(() => {
    if (!isAuthenticated || !selectedDate) return;
    let active = true;
    setScheduledError(false); setScheduledLoading(true);
    getScheduledDay(selectedDate, timezone).then(async (result) => {
      const known = new Set(result.tasks.map((task) => task.id));
      const historicalIds = [...new Set(result.triggers.map((trigger) => trigger.task_id))].filter((id) => !known.has(id));
      const historical = await Promise.all(historicalIds.map((id) => getScheduledTask(id).catch(() => null)));
      if (!active) return;
      setScheduledTasks([...result.tasks, ...historical.flatMap((item) => item?.task ? [item.task] : [])]);
      setScheduledTriggers(result.triggers);
    }).catch(() => { if (active) setScheduledError(true); })
      .finally(() => { if (active) setScheduledLoading(false); });
    return () => { active = false; };
  }, [isAuthenticated, selectedDate, timezone, scheduledRefresh]);

  const refreshScheduled = useCallback(() => setScheduledRefresh((value) => value + 1), []);
  const activeTriggerKey = scheduledTriggers.filter((trigger) => ACTIVE_TRIGGER_STATES.has(trigger.status))
    .map((trigger) => trigger.id).sort().join('|');

  useEffect(() => {
    const onVisibilityChange = () => setDocumentVisible(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, []);

  useEffect(() => {
    activeRefreshCountRef.current = 0;
    setActiveRefreshExhausted(false);
  }, [activeTriggerKey, selectedDate, timezone]);

  useEffect(() => {
    if (!isAuthenticated || !selectedDate || !documentVisible || scheduledLoading || !activeTriggerKey
      || activeRefreshCountRef.current >= SCHEDULED_ACTIVE_REFRESH_MAXIMUM) return;
    const timer = window.setTimeout(() => {
      activeRefreshCountRef.current += 1;
      if (activeRefreshCountRef.current >= SCHEDULED_ACTIVE_REFRESH_MAXIMUM) setActiveRefreshExhausted(true);
      refreshScheduled();
    }, SCHEDULED_ACTIVE_REFRESH_INTERVAL_MS);
    return () => window.clearTimeout(timer);
  }, [activeTriggerKey, documentVisible, isAuthenticated, refreshScheduled, scheduledLoading, selectedDate, timezone]);
  const actOnTask = useCallback(async (task: ScheduledTask, action: ScheduledTaskAction,
    desired?: ScheduledTaskDesired): Promise<ScheduledTaskActionResult> => {
    const manualRequestKey = action === 'run' ? (manualRequestKeys.current.get(task.id) ?? crypto.randomUUID()) : null;
    if (manualRequestKey) manualRequestKeys.current.set(task.id, manualRequestKey);
    try {
      let result: ScheduledTaskActionResult;
      if (action === 'run') {
        const runResult = await updateScheduledTask(task.id, 'run', { manual_request_key: manualRequestKey! });
        manualRequestKeys.current.delete(task.id);
        setScheduledTriggers((items) => [runResult.trigger, ...items.filter((item) => item.id !== runResult.trigger.id)]);
        result = runResult;
      } else if (action === 'edit') {
        const definitionResult = await updateScheduledTask(task.id, 'edit', { expected_revision: task.revision, ...desired! });
        setScheduledTasks((items) => items.map((item) => item.id === task.id ? definitionResult.task : item));
        result = definitionResult;
      } else {
        const definitionResult = await updateScheduledTask(task.id, action, { expected_revision: task.revision });
        setScheduledTasks((items) => items.map((item) => item.id === task.id ? definitionResult.task : item));
        result = definitionResult;
      }
      return result;
    } catch (error) {
      if (action === 'run' && error instanceof ScheduledTaskApiError) {
        manualRequestKeys.current.delete(task.id);
      }
      if (error instanceof ScheduledTaskApiError && error.code === 'SCHEDULE_REVISION_CONFLICT') {
        const latest = await getScheduledTask(task.id).catch(() => null);
        if (latest?.task) {
          setScheduledTasks((items) => items.map((item) => item.id === task.id ? latest.task! : item));
          throw new ScheduledTaskConflictError(latest.task);
        }
      }
      throw error;
    }
  }, []);

  useEffect(() => {
    if (!initialDateKey) return;
    const initial = parseDateKey(initialDateKey);
    setSelectedDate(initialDateKey); setCalendarFocusKey(initialDateKey);
    setCurrentMonth(new Date(initial.getFullYear(), initial.getMonth(), 1));
  }, [initialDateKey]);

  const refreshCalendarData = useCallback(async () => {
    if (isAuthenticated) {
      try {
        const { listSessions } = await import('../api/voiceApi');
        const sessions = await listSessions(timezone);
        const grouped: Record<string, CalendarListEntry[]> = {};
        sessions.forEach((session: UserSession) => {
          const dateKey = session.date_key || getLocalDayKey(session.created_at || session.updated_at, timezone);
          if (!dateKey) return;
          const timestamp = parseFlexibleTimestamp(session.updated_at || session.created_at)?.getTime() ?? Date.now();
          if (!grouped[dateKey]) grouped[dateKey] = [];
          grouped[dateKey].push({ id: session.id, timestamp,
            firstLine: session.first_line || session.name || t('calendar.untitled') });
        });
        setCalendarData(grouped); return;
      } catch (error) { console.error('Failed to load calendar from database:', error); }
    }
    const localData = getCalendarData();
    setCalendarData(Object.fromEntries(Object.entries(localData).map(([dateKey, entries]) => [dateKey,
      entries.map((entry) => ({ id: entry.id, timestamp: entry.timestamp, firstLine: entry.firstLine, state: entry.state }))])));
  }, [isAuthenticated, t, timezone]);
  useEffect(() => { void refreshCalendarData(); }, [refreshCalendarData]);

  const today = getTodayKeyInTimeZone(timezone);
  const datesWithEntries = Object.keys(calendarData);
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const days: Array<{ date: number; dateKey: string; hasEntries: boolean; isToday: boolean } | null> = [];
  for (let index = 0; index < firstDay.getDay(); index += 1) days.push(null);
  for (let date = 1; date <= daysInMonth; date += 1) {
    const dateKey = getDateKey(new Date(year, month, date));
    days.push({ date, dateKey, hasEntries: datesWithEntries.includes(dateKey), isToday: dateKey === today });
  }

  useEffect(() => {
    const pending = pendingDateFocusRef.current;
    if (!pending) return;
    const frame = requestAnimationFrame(() => { dateButtonRefs.current.get(pending)?.focus(); pendingDateFocusRef.current = null; });
    return () => cancelAnimationFrame(frame);
  }, [currentMonth]);

  const confirmDiscardDrafts = useCallback(() => ![...dirtyDraftsRef.current.values()].some(Boolean)
    || window.confirm(t('calendar.scheduledDiscardConfirm')), [t]);
  const handleDateClick = (dateKey: string) => {
    if (dateKey !== selectedDate && !confirmDiscardDrafts()) return;
    dirtyDraftsRef.current.clear(); setSelectedDate(dateKey); setCalendarFocusKey(dateKey);
  };
  const moveCalendarFocus = (dateKey: string, dayDelta: number) => {
    const target = parseDateKey(dateKey); target.setDate(target.getDate() + dayDelta);
    const targetKey = getDateKey(target); setCalendarFocusKey(targetKey); pendingDateFocusRef.current = targetKey;
    if (target.getMonth() !== month || target.getFullYear() !== year) {
      setCurrentMonth(new Date(target.getFullYear(), target.getMonth(), 1));
    } else requestAnimationFrame(() => { dateButtonRefs.current.get(targetKey)?.focus(); pendingDateFocusRef.current = null; });
  };
  const handleDateKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, dateKey: string) => {
    const delta = event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1
      : event.key === 'ArrowUp' ? -7 : event.key === 'ArrowDown' ? 7 : null;
    if (delta !== null) { event.preventDefault(); moveCalendarFocus(dateKey, delta); }
    else if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); handleDateClick(dateKey); }
  };

  const handleDeleteEntry = async (dateKey: string, entryId: string) => {
    if (!window.confirm(t('calendar.deleteConfirm'))) return;
    if (isAuthenticated) {
      try {
        const { deleteSession } = await import('../api/voiceApi'); await deleteSession(entryId);
        await refreshCalendarData(); onEntryDeleted?.(entryId);
      } catch (error) { console.error('Failed to delete from database:', error); window.alert(t('calendar.deleteError')); }
    } else { deleteEntry(dateKey, entryId); setCalendarData(getCalendarData()); onEntryDeleted?.(entryId); }
  };

  const selectedEntries = selectedDate ? calendarData[selectedDate] ?? [] : [];
  const handleOpenEntry = async (entry: CalendarListEntry) => {
    if (isAuthenticated) {
      try {
        const { getSession } = await import('../api/voiceApi'); const full = await getSession(entry.id);
        if (!full?.editor_state) { window.alert(t('calendar.loadError')); return; }
        onLoadEntry({ id: entry.id, timestamp: entry.timestamp, state: full.editor_state, firstLine: entry.firstLine }); onClose();
      } catch (error) { console.error('Failed to load session:', error); window.alert(t('calendar.loadError')); }
    } else if (entry.state) { onLoadEntry(entry as CalendarEntry); onClose(); }
  };

  const onLayerChange = useCallback((key: string, closer: (() => void) | null) => {
    if (!closer) { subpanelClosersRef.current.delete(key); return; }
    subpanelClosersRef.current.delete(key); subpanelClosersRef.current.set(key, closer);
  }, []);
  const onDraftDirtyChange = useCallback((taskId: string, dirty: boolean) => {
    if (dirty) dirtyDraftsRef.current.set(taskId, true); else dirtyDraftsRef.current.delete(taskId);
  }, []);
  const closeDialog = useCallback(() => {
    if (confirmDiscardDrafts()) onClose();
  }, [confirmDiscardDrafts, onClose]);

  useEffect(() => {
    const closeTopSubpanel = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      const layers = [...subpanelClosersRef.current.entries()];
      const current = layers[layers.length - 1];
      if (!current) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      current[1]();
    };
    window.addEventListener('keydown', closeTopSubpanel, true);
    return () => window.removeEventListener('keydown', closeTopSubpanel, true);
  }, []);

  const weekdayFormatter = new Intl.DateTimeFormat(dateLocale, { weekday: 'short', timeZone: 'UTC' });
  const weekdayLabels = Array.from({ length: 7 }, (_, index) => weekdayFormatter.format(new Date(Date.UTC(2023, 0, index + 1))));
  const attentionCount = scheduledTriggers.filter((trigger) => trigger.status === 'failed' || trigger.status === 'state_unknown').length;
  const firstAttentionTaskId = scheduledTriggers.find((trigger) =>
    trigger.status === 'state_unknown' || trigger.status === 'failed')?.task_id ?? null;
  const selectedDateLabel = selectedDate === today ? t('calendar.todayLabel') : selectedDate
    ? new Date(`${selectedDate}T12:00:00Z`).toLocaleDateString(dateLocale,
        { timeZone: 'UTC', year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' }) : '';

  return <Modal open title={t('calendar.title')} closeLabel={t('calendar.close')} onClose={closeDialog}
    initialFocusRef={monthPrevRef} surfaceClassName="calendar-popup-modal">
    <div className="calendar-popup">
      <section className="calendar-popup__calendar" aria-label={t('calendar.monthCalendarLabel')}>
        <header className="calendar-popup__month-heading">
          <button ref={monthPrevRef} type="button" aria-label={t('calendar.prev')}
            onClick={() => setCurrentMonth(new Date(year, month - 1, 1))}>‹</button>
          <h3>{currentMonth.toLocaleDateString(dateLocale, { month: 'long', year: 'numeric' })}</h3>
          <button type="button" aria-label={t('calendar.next')}
            onClick={() => setCurrentMonth(new Date(year, month + 1, 1))}>›</button>
        </header>
        <div className="calendar-popup__weekdays" aria-hidden="true">
          {weekdayLabels.map((label, index) => <span key={`${label}-${index}`}>{label}</span>)}
        </div>
        <div className="calendar-popup__grid" role="grid" aria-label={t('calendar.monthCalendarLabel')}>
          {days.map((day, index) => day ? <button key={day.dateKey}
            ref={(element) => { if (element) dateButtonRefs.current.set(day.dateKey, element); else dateButtonRefs.current.delete(day.dateKey); }}
            type="button" role="gridcell" className={['calendar-popup__day', day.hasEntries ? 'calendar-popup__day--has-entry' : '',
              day.isToday ? 'calendar-popup__day--today' : '', selectedDate === day.dateKey ? 'calendar-popup__day--selected' : '']
              .filter(Boolean).join(' ')}
            aria-label={new Date(`${day.dateKey}T12:00:00Z`).toLocaleDateString(dateLocale,
              { timeZone: 'UTC', year: 'numeric', month: 'long', day: 'numeric' })}
            aria-selected={selectedDate === day.dateKey} tabIndex={calendarFocusKey === day.dateKey ? 0 : -1}
            onFocus={() => setCalendarFocusKey(day.dateKey)} onClick={() => handleDateClick(day.dateKey)}
            onKeyDown={(event) => handleDateKeyDown(event, day.dateKey)}>
            <span>{day.date}</span>{day.hasEntries ? <i aria-hidden="true" /> : null}
          </button> : <span key={`empty-${index}`} className="calendar-popup__day-placeholder" aria-hidden="true" />)}
        </div>
      </section>

      {selectedDate ? <section className="calendar-popup__workspace" aria-labelledby="calendar-popup-date-title">
        <header className="calendar-popup__date-summary"><h3 id="calendar-popup-date-title">{selectedDateLabel}</h3>
          <div className="calendar-popup__counts" aria-live="polite">
            <span>{t('calendar.diaryCount', { count: selectedEntries.length })}</span>
            <span>{scheduledError ? t('calendar.taskCountUnknown') : scheduledLoading
              ? t('calendar.taskCountLoading') : t('calendar.taskCount', { count: scheduledTasks.length })}</span>
            {scheduledError ? <span>{t('calendar.attentionCountUnknown')}</span> : scheduledLoading
              ? <span>{t('calendar.attentionCountLoading')}</span>
              : attentionCount > 0 && firstAttentionTaskId
                ? <button type="button" className="calendar-popup__count-alert" onClick={() => {
                    taskCardRefs.current.get(firstAttentionTaskId)?.focus();
                  }}>{t('calendar.attentionCount', { count: attentionCount })}</button>
                : <span>{t('calendar.attentionCount', { count: attentionCount })}</span>}
          </div>
        </header>
        <div className="calendar-popup__workspace-scroll">
          {isAuthenticated && (scheduledLoading || scheduledError || scheduledTasks.length > 0)
            ? <section className="calendar-popup__section calendar-popup__task-section"
            aria-labelledby="calendar-popup-task-title">
            <div className="calendar-popup__section-heading"><h3 id="calendar-popup-task-title">{t('calendar.scheduledSectionTitle')}</h3>
              {!scheduledError ? <span>{scheduledTasks.length}</span> : null}</div>
            {scheduledLoading ? <div className="calendar-popup__loading" aria-busy="true" aria-live="polite">
              {t('calendar.scheduledLoading')}</div> : null}
            {scheduledError ? <div className="calendar-popup__alert" role="alert"><span>{t('calendar.scheduledUnavailable')}</span>
              <button type="button" onClick={refreshScheduled}>{t('calendar.scheduledRetry')}</button></div> : null}
            {!scheduledLoading && !scheduledError && scheduledTasks.length === 0
              ? <p className="calendar-popup__empty">{t('calendar.scheduledEmpty')}</p> : null}
            {activeRefreshExhausted && activeTriggerKey ? <div className="calendar-popup__hint" aria-live="polite">
              <span>{t('calendar.scheduledAutoRefreshPaused')}</span>
              <button type="button" className="calendar-popup__refresh-link" onClick={() => {
                activeRefreshCountRef.current = 0; setActiveRefreshExhausted(false); refreshScheduled();
              }}>{t('calendar.scheduledRefreshDate')}</button>
            </div> : null}
            <div className="calendar-popup__task-list">{scheduledTasks.map((task) => <ScheduledTaskCard key={task.id}
              task={task} triggers={scheduledTriggers.filter((trigger) => trigger.task_id === task.id)} onAction={actOnTask}
              onOpenThread={onOpenTaskThread} onRefresh={refreshScheduled} onLayerChange={onLayerChange}
              onDraftDirtyChange={onDraftDirtyChange} onCardRef={(taskId, element) => {
                if (element) taskCardRefs.current.set(taskId, element); else taskCardRefs.current.delete(taskId);
              }} dateLocale={dateLocale} />)}</div>
          </section> : null}

          <section className="calendar-popup__section calendar-popup__diary-section" aria-labelledby="calendar-popup-diary-title">
            <div className="calendar-popup__section-heading"><h3 id="calendar-popup-diary-title">{t('calendar.diarySectionTitle')}</h3>
              <span>{selectedEntries.length}</span></div>
            {selectedEntries.length === 0 ? <p className="calendar-popup__empty">{t('calendar.noEntriesForDate')}</p>
              : <div className="calendar-popup__diary-list">{selectedEntries.map((entry) => {
                const isCurrentEntry = currentEntryId === entry.id;
                const time = new Date(entry.timestamp).toLocaleTimeString(dateLocale, { hour: '2-digit', minute: '2-digit' });
                return <article key={entry.id} className={`calendar-popup__diary${isCurrentEntry ? ' calendar-popup__diary--current' : ''}`}>
                  <button type="button" className="calendar-popup__diary-open"
                    aria-label={`${t('calendar.openButton')}: ${entry.firstLine}`} onClick={() => void handleOpenEntry(entry)}>
                    <span>{time}</span>{isCurrentEntry ? <em>{t('calendar.currentEntryLabel')}</em> : null}<strong>{entry.firstLine}</strong>
                  </button>
                  <button type="button" className="calendar-popup__diary-delete"
                    aria-label={`${t('calendar.deleteButton')}: ${entry.firstLine}`}
                    onClick={() => void handleDeleteEntry(selectedDate, entry.id)}>{t('calendar.deleteButton')}</button>
                </article>;
              })}</div>}
          </section>
        </div>
      </section> : null}
    </div>
  </Modal>;
}
