// [Input] Calendar storage, authenticated diary/scheduled-task APIs, locale, timezone, and shared dialog/navigation boundaries.
// [Output] Accessible responsive Calendar with a month paper, exclusive task/diary/Notion panels, retained local state and viewport-contained tooltips/modals.
// [Sync] 2026-10-07: edit Codex-style repeat presets through a secondary schedule dialog, plus source/new Chat mode and captured execution model.
// [Sync] 2026-10-06: borderless right-paper presentation is owned by CalendarPopup.css; component business and scroll/focus owners remain unchanged.
// [Sync] 2026-10-05: add mutually exclusive accessible tabs; preserve local owners and pause hidden queries/polling.
// [Pos] Calendar/date-workspace dialog in frontend/app/_dream/components; Admin remains schedule and trigger owner.
// [Sync] 2026-09-29: move date context into task/diary headings and remove the visible outer summary surface for the floating-paper layout.
// [Sync] 2026-09-29: add Chat handoff composer, latest-result replacement view, compact action rows, and independent task editor/history dialogs.
import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from 'react';
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
import { fetchGatewayModels, type GatewayModel } from '../api/gatewayModelsApi';
import Modal from './chat/Modal';
import CalendarNotionPanel from './CalendarNotionPanel';
import NotionMark from './NotionMark';
import { IconArrowUp, IconClock, IconEdit, IconFile, IconMoreHorizontal } from './chat/Icons';
import ChatMarkdown from './chat/ChatMarkdown';
import { fetchFullClaudeThreadMessages } from './chat/threadSessionHydration';
import './CalendarPopup.css';

interface Props {
  onLoadEntry: (entry: CalendarEntry) => void;
  onClose: () => void;
  currentEntryId?: string | null;
  onEntryDeleted?: (entryId: string) => void;
  timezone: string;
  initialDateKey?: string | null;
  onOpenTaskThread?: (threadId: string) => void;
  onArrangeTask?: (prompt: string) => void;
  onOpenSettings?: () => void;
}

type CalendarListEntry = { id: string; timestamp: number; firstLine: string; state?: CalendarEntry['state'] };
type ScheduledTaskDesired = Pick<ScheduledTask, 'title' | 'prompt' | 'rule' | 'run_thread_mode'> & { model_alias: string };
type ScheduledTaskActionResult = ScheduledTaskDefinitionResult | ScheduledTaskRunResult;
type Weekday = Extract<ScheduledRule, { kind: 'weekly' }>['weekdays'][number];
type RepeatPreset = 'hourly' | 'daily' | 'workdays' | 'weekly' | 'custom';
type EditDraft = {
  title: string; prompt: string; repeatPreset: RepeatPreset; kind: ScheduledRule['kind']; localDate: string;
  localTime: string; intervalMinutes: string; intervalHours: string; minute: string;
  weekdays: Weekday[]; timeZone: string; selectedOffsetMinutes: number | null;
  runThreadMode: ScheduledTask['run_thread_mode']; modelAlias: string;
};
type EditField = 'title' | 'prompt' | 'localDate' | 'localTime' | 'intervalMinutes'
  | 'intervalHours' | 'minute' | 'weekdays' | 'timeZone' | 'modelAlias';

const UNRESOLVED_TRIGGER_STATES = new Set<ScheduledTrigger['status']>(['claimed', 'queued', 'running', 'state_unknown']);
const ACTIVE_TRIGGER_STATES = new Set<ScheduledTrigger['status']>(['claimed', 'queued', 'running']);
const SCHEDULED_HISTORY_PAGE_SIZE = 20;
const SCHEDULED_ACTIVE_REFRESH_INTERVAL_MS = 2_000;
const SCHEDULED_ACTIVE_REFRESH_MAXIMUM = 15;
const SCHEDULE_FIELDS = new Set<EditField>([
  'localDate', 'localTime', 'intervalMinutes', 'intervalHours', 'minute', 'weekdays', 'timeZone',
]);

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

const WORKDAYS: Weekday[] = ['MO', 'TU', 'WE', 'TH', 'FR'];
const WEEKDAYS: Weekday[] = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'];

function sameWeekdays(left: Weekday[], right: Weekday[]): boolean {
  return left.length === right.length && left.every((day, index) => day === right[index]);
}

function repeatPresetFromRule(rule: ScheduledRule): RepeatPreset {
  if (rule.kind === 'hourly' && rule.interval_hours === 1 && rule.minute === 0) return 'hourly';
  if (rule.kind === 'daily') return 'daily';
  if (rule.kind === 'weekly' && sameWeekdays(rule.weekdays, WORKDAYS)) return 'workdays';
  if (rule.kind === 'weekly' && rule.weekdays.length === 1) return 'weekly';
  return 'custom';
}

function draftFromTask(task: ScheduledTask): EditDraft {
  return {
    title: task.title,
    prompt: task.prompt,
    repeatPreset: repeatPresetFromRule(task.rule),
    kind: task.rule.kind,
    localDate: task.rule.kind === 'once' ? task.rule.local_date : '',
    localTime: task.rule.kind === 'once' || task.rule.kind === 'daily' || task.rule.kind === 'weekly'
      ? task.rule.local_time : '09:00',
    intervalMinutes: task.rule.kind === 'interval' ? String(task.rule.interval_minutes) : '10',
    intervalHours: task.rule.kind === 'hourly' ? String(task.rule.interval_hours) : '1',
    minute: task.rule.kind === 'hourly' ? String(task.rule.minute) : '0',
    weekdays: task.rule.kind === 'weekly' ? task.rule.weekdays : ['MO'],
    timeZone: task.rule.time_zone,
    selectedOffsetMinutes: task.rule.kind === 'once' ? task.rule.selected_offset_minutes : null,
    runThreadMode: task.run_thread_mode,
    modelAlias: task.model_alias ?? '',
  };
}

function desiredFromDraft(draft: EditDraft): ScheduledTaskDesired {
  const rule: ScheduledRule = draft.kind === 'once'
    ? { kind: 'once', local_date: draft.localDate, local_time: draft.localTime, time_zone: draft.timeZone,
        selected_offset_minutes: draft.selectedOffsetMinutes }
    : draft.kind === 'daily' ? { kind: 'daily', local_time: draft.localTime, time_zone: draft.timeZone }
      : draft.kind === 'interval' ? { kind: 'interval', interval_minutes: Number(draft.intervalMinutes), time_zone: draft.timeZone }
        : draft.kind === 'hourly' ? { kind: 'hourly', interval_hours: Number(draft.intervalHours), minute: Number(draft.minute), time_zone: draft.timeZone }
          : { kind: 'weekly', weekdays: draft.weekdays, local_time: draft.localTime, time_zone: draft.timeZone };
  return { title: draft.title.trim(), prompt: draft.prompt.trim(), rule,
    run_thread_mode: draft.runThreadMode, model_alias: draft.modelAlias };
}

function draftsEqual(left: EditDraft | null, right: EditDraft | null): boolean {
  return left !== null && right !== null && left.title === right.title && left.prompt === right.prompt
    && left.repeatPreset === right.repeatPreset && left.kind === right.kind
    && left.localDate === right.localDate && left.localTime === right.localTime
    && left.intervalMinutes === right.intervalMinutes && left.intervalHours === right.intervalHours
    && left.minute === right.minute && sameWeekdays(left.weekdays, right.weekdays)
    && left.timeZone === right.timeZone && left.selectedOffsetMinutes === right.selectedOffsetMinutes
    && left.runThreadMode === right.runThreadMode && left.modelAlias === right.modelAlias;
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
  if (['once', 'daily', 'weekly'].includes(draft.kind) && !/^([01]\d|2[0-3]):[0-5]\d$/.test(draft.localTime)) errors.localTime = 'required';
  if (draft.kind === 'interval' && (!/^\d+$/.test(draft.intervalMinutes)
    || !Number.isSafeInteger(Number(draft.intervalMinutes)) || Number(draft.intervalMinutes) < 1)) errors.intervalMinutes = 'required';
  if (draft.kind === 'hourly' && (!/^\d+$/.test(draft.intervalHours)
    || !Number.isSafeInteger(Number(draft.intervalHours)) || Number(draft.intervalHours) < 1
    || Number(draft.intervalHours) > 35_791_394)) errors.intervalHours = 'required';
  if (draft.kind === 'hourly' && (!/^\d+$/.test(draft.minute)
    || Number(draft.minute) < 0 || Number(draft.minute) > 59)) errors.minute = 'required';
  if (draft.kind === 'weekly' && draft.weekdays.length === 0) errors.weekdays = 'required';
  if (!draft.modelAlias.trim()) errors.modelAlias = 'required';
  try { new Intl.DateTimeFormat('en', { timeZone: draft.timeZone.trim() }).format(new Date()); }
  catch { errors.timeZone = 'invalid'; }
  return errors;
}

function triggerTimestamp(trigger: ScheduledTrigger): number {
  return parseFlexibleTimestamp(trigger.created_at)?.getTime() ?? 0;
}

function recentTrigger(triggers: ScheduledTrigger[]): ScheduledTrigger | null {
  return [...triggers].sort((left, right) => triggerTimestamp(right) - triggerTimestamp(left))[0] ?? null;
}

function ScheduledTaskResult({ task, triggers, onBack, onOpenThread, dateLocale, active }: {
  active: boolean;
  task: ScheduledTask;
  triggers: ScheduledTrigger[];
  onBack: () => void;
  onOpenThread?: (threadId: string) => void;
  dateLocale: string;
}) {
  const { t } = useTranslation();
  const [latest, setLatest] = useState<ScheduledTrigger | null>(() => recentTrigger(triggers));
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const historyRequestRef = useRef('');
  const resultRequestRef = useRef('');
  const resultControllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);
  const historyKey = JSON.stringify([task.id, task.revision, triggers.map((item) => [item.id, item.status, item.updated_at])]);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; historyRequestRef.current = ''; resultRequestRef.current = ''; resultControllerRef.current?.abort(); };
  }, []);
  useEffect(() => {
    if (!active || historyRequestRef.current === historyKey) return;
    historyRequestRef.current = historyKey;
    getScheduledHistory(task.id, SCHEDULED_HISTORY_PAGE_SIZE).then((response) => {
      if (!mountedRef.current || historyRequestRef.current !== historyKey) return;
      const merged = new Map(triggers.map((trigger) => [trigger.id, trigger]));
      response.triggers.forEach((trigger) => merged.set(trigger.id, trigger));
      setLatest(recentTrigger([...merged.values()]));
    }).catch(() => { if (mountedRef.current && historyRequestRef.current === historyKey) setLatest(recentTrigger(triggers)); });
  }, [active, historyKey, task.id, triggers]);
  useEffect(() => {
    if (!active) return;
    if (!latest?.target_thread_id || !latest.final_message_id) {
      setResult(null); setLoading(false); setUnavailable(true); return;
    }
    const requestKey = JSON.stringify([latest.target_thread_id, latest.final_message_id]);
    if (resultRequestRef.current === requestKey) return;
    resultRequestRef.current = requestKey;
    resultControllerRef.current?.abort();
    const controller = new AbortController(); resultControllerRef.current = controller;
    setLoading(true); setUnavailable(false); setResult(null);
    fetchFullClaudeThreadMessages(latest.target_thread_id, controller.signal).then((snapshot) => {
      if (controller.signal.aborted || !mountedRef.current) return;
      const message = snapshot.messages.find((candidate) => candidate.id === latest.final_message_id
        && candidate.role === 'assistant');
      const text = message?.parts.flatMap((part) => part.type === 'text' && part.text ? [part.text] : []).join('\n\n').trim();
      if (!text) throw new Error('Scheduled final message is unavailable.');
      setResult(text);
    }).catch(() => { if (!controller.signal.aborted && mountedRef.current) setUnavailable(true); })
      .finally(() => { if (!controller.signal.aborted && mountedRef.current) setLoading(false); });
  }, [active, latest?.final_message_id, latest?.target_thread_id]);
  const latestTime = latest ? new Date(latest.scheduled_at ?? latest.created_at).toLocaleString(dateLocale, {
    timeZone: task.rule.time_zone,
  }) : null;
  return <div className="calendar-popup__task-result">
    <header>
      <button type="button" onClick={onBack}>{t('calendar.scheduledBackToList')}</button>
      <div><span>{t('calendar.scheduledResultTitle')}</span><strong>{task.title}</strong>
        {latestTime ? <small>{latestTime}</small> : null}</div>
    </header>
    <div className="calendar-popup__task-result-scroll">
      {loading ? <p role="status">{t('calendar.scheduledResultLoading')}</p> : null}
      {unavailable ? <p role="alert">{t('calendar.scheduledResultUnavailable')}</p> : null}
      {result && latest?.target_thread_id ? <ChatMarkdown text={result} workspaceSessionId={latest.target_thread_id} /> : null}
    </div>
    {latest?.target_thread_id && onOpenThread ? <footer><button type="button"
      onClick={() => onOpenThread(latest.target_thread_id!)}>{t('calendar.scheduledOpenThread')}</button></footer> : null}
  </div>;
}

function ScheduledTaskCard({ task, triggers, onAction, onOpenThread, onOpenResult,
  onLayerChange, onDraftDirtyChange, onCardRef, dateLocale, active }: {
  active: boolean;
  task: ScheduledTask;
  triggers: ScheduledTrigger[];
  onAction: (task: ScheduledTask, action: ScheduledTaskAction, desired?: ScheduledTaskDesired) => Promise<ScheduledTaskActionResult>;
  onOpenThread?: (threadId: string) => void;
  onOpenResult: () => void;
  onLayerChange: (key: string, closer: (() => void) | null) => void;
  onDraftDirtyChange: (taskId: string, dirty: boolean) => void;
  onCardRef: (taskId: string, element: HTMLElement | null) => void;
  dateLocale: string;
}) {
  const { t } = useTranslation();
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
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [models, setModels] = useState<GatewayModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState(false);
  const [scheduleEditorOpen, setScheduleEditorOpen] = useState(false);
  const [scheduleEditorSnapshot, setScheduleEditorSnapshot] = useState<EditDraft | null>(null);
  const editing = draft !== null;
  const dirty = editing && !draftsEqual(draft, defaultDraft);

  const loadHistory = useCallback(async () => {
    setHistoryError(false); setHistoryLoadMoreError(false);
    try {
      const response = await getScheduledHistory(task.id, SCHEDULED_HISTORY_PAGE_SIZE);
      setHistory(response.triggers); setHistoryHasMore(response.triggers.length === SCHEDULED_HISTORY_PAGE_SIZE);
      return response.triggers;
    } catch { setHistoryError(true); return null; }
  }, [task.id]);
  const loadOlderHistory = useCallback(async () => {
    if (!history?.length || historyLoadingMore) return;
    setHistoryLoadingMore(true); setHistoryLoadMoreError(false);
    try {
      const oldest = [...history].sort((left, right) => triggerTimestamp(left) - triggerTimestamp(right))[0]?.created_at;
      if (!oldest) { setHistoryHasMore(false); return; }
      const response = await getScheduledHistory(task.id, SCHEDULED_HISTORY_PAGE_SIZE, oldest);
      setHistory((current) => {
        const merged = new Map((current ?? []).map((trigger) => [trigger.id, trigger]));
        response.triggers.forEach((trigger) => merged.set(trigger.id, trigger));
        return [...merged.values()];
      });
      setHistoryHasMore(response.triggers.length === SCHEDULED_HISTORY_PAGE_SIZE);
    } catch { setHistoryLoadMoreError(true); }
    finally { setHistoryLoadingMore(false); }
  }, [history, historyLoadingMore, task.id]);
  const historyRequestRef = useRef('');
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; historyRequestRef.current = ''; };
  }, []);
  useEffect(() => {
    if (!active) { setMoreOpen(false); return; }
    const requestKey = `${task.id}:${task.revision}`;
    if (historyRequestRef.current === requestKey) return;
    historyRequestRef.current = requestKey;
    getScheduledHistory(task.id, SCHEDULED_HISTORY_PAGE_SIZE).then((response) => { if (mountedRef.current && historyRequestRef.current === requestKey) {
      setHistory(response.triggers); setHistoryHasMore(response.triggers.length === SCHEDULED_HISTORY_PAGE_SIZE);
    } }).catch(() => { if (mountedRef.current && historyRequestRef.current === requestKey) setHistoryError(true); });
  }, [active, task.id, task.revision]);
  useEffect(() => {
    onDraftDirtyChange(task.id, dirty);
    return () => onDraftDirtyChange(task.id, false);
  }, [dirty, onDraftDirtyChange, task.id]);

  const closeEditing = useCallback(() => {
    setDraft(null); setDefaultDraft(null); setFieldErrors({}); setConflictLatest(null); setError(null);
    setAdvancedOpen(false); setModels([]); setModelsLoading(false); setModelsError(false);
    setScheduleEditorOpen(false); setScheduleEditorSnapshot(null);
  }, []);
  const closeHistory = useCallback(() => {
    setHistoryOpen(false); requestAnimationFrame(() => moreButtonRef.current?.focus());
  }, []);
  const closeMore = useCallback(() => {
    setMoreOpen(false); requestAnimationFrame(() => moreButtonRef.current?.focus());
  }, []);
  useEffect(() => {
    const key = `scheduled-task-${task.id}`;
    if (moreOpen) onLayerChange(key, closeMore); else onLayerChange(key, null);
    return () => onLayerChange(key, null);
  }, [closeMore, moreOpen, onLayerChange, task.id]);

  const knownTriggers = useMemo(() => {
    const merged = new Map((history ?? []).map((trigger) => [trigger.id, trigger]));
    triggers.forEach((trigger) => merged.set(trigger.id, trigger));
    return [...merged.values()];
  }, [history, triggers]);
  const latest = recentTrigger(knownTriggers);
  const unresolved = knownTriggers.some((trigger) => UNRESOLVED_TRIGGER_STATES.has(trigger.status));
  const stateUnknown = knownTriggers.some((trigger) => trigger.status === 'state_unknown');
  const statusLabel = (status: string) => t(`calendar.scheduledStatus.${status}`, { defaultValue: status });
  const actionLabel = (action: string) => t('calendar.scheduledActionAria', { action, title: task.title });
  const formatTime = (value: string) => new Date(value).toLocaleString(dateLocale, {
    timeZone: task.rule.time_zone, month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
  const planText = (definition: ScheduledTask = task) => definition.rule.kind === 'once'
    ? `${definition.rule.local_date} · ${definition.rule.local_time}`
    : definition.rule.kind === 'daily'
      ? `${t('calendar.scheduledDaily')} · ${definition.rule.local_time}`
      : definition.rule.kind === 'interval'
        ? t('calendar.scheduledIntervalSummary', { count: definition.rule.interval_minutes })
        : definition.rule.kind === 'hourly'
          ? t('calendar.scheduledHourlySummary', { count: definition.rule.interval_hours, minute: definition.rule.minute })
          : t('calendar.scheduledWeeklySummary', { days: definition.rule.weekdays.map((day) => t(`calendar.scheduledWeekday.${day}`)).join('、'), time: definition.rule.local_time });
  const summary = latest && ACTIVE_TRIGGER_STATES.has(latest.status) ? statusLabel(latest.status)
    : latest?.status === 'failed' || latest?.status === 'state_unknown' ? statusLabel(latest.status)
    : task.status === 'paused' ? t('calendar.scheduledStatus.paused')
    : task.next_run_at ? `${planText()} · ${t('calendar.scheduledNext')} ${formatTime(task.next_run_at)}`
      : planText();

  const openEditing = () => {
    const next = draftFromTask(task);
    setDefaultDraft(next); setDraft(next); setFieldErrors({}); setConflictLatest(null); setError(null); setMoreOpen(false);
    setAdvancedOpen(false); setModelsLoading(true); setModelsError(false);
    fetchGatewayModels().then((catalog) => {
      if (!mountedRef.current) return;
      const callable = catalog.models.filter((model) => model.callable);
      setModels(callable);
      setDraft((current) => current ? {
        ...current,
        modelAlias: callable.some((model) => model.modelAlias === current.modelAlias)
          ? current.modelAlias : (catalog.defaultModelAlias ?? ''),
      } : current);
    }).catch(() => { if (mountedRef.current) { setModelsError(true); setAdvancedOpen(true); } })
      .finally(() => { if (mountedRef.current) setModelsLoading(false); });
  };
  const toggleMore = () => setMoreOpen((current) => {
    const next = !current;
    if (next) requestAnimationFrame(() => moreMenuRef.current?.querySelector<HTMLButtonElement>('button:not([disabled])')?.focus());
    return next;
  });
  const handleMoreKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const items = [...(moreMenuRef.current?.querySelectorAll<HTMLButtonElement>('button:not([disabled])') ?? [])];
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
      const validation = validateDraft(draft); setFieldErrors(validation);
      if (validation.modelAlias) setAdvancedOpen(true);
      if (Object.keys(validation).some((field) => SCHEDULE_FIELDS.has(field as EditField))) {
        setScheduleEditorSnapshot(draft); setScheduleEditorOpen(true);
      }
      if (Object.keys(validation).length) return;
      desired = desiredFromDraft(draft);
    }
    setBusyAction(action); setError(null);
    try {
      const result = await onAction(action === 'edit' && conflictLatest ? conflictLatest : task, action, desired);
      if ('trigger' in result) setHistory((items) => [result.trigger, ...(items ?? []).filter((item) => item.id !== result.trigger.id)]);
      if (action === 'edit') closeEditing();
      if (action === 'run') setRunOutcomeUnknown(false);
      if (historyOpen) await loadHistory();
    } catch (cause) {
      if (cause instanceof ScheduledTaskConflictError && action === 'edit') {
        setConflictLatest(cause.latest); setError(t('calendar.scheduledConflict'));
      } else if (cause instanceof ScheduledTaskApiError && cause.code === 'SCHEDULE_LOCAL_TIME_MISSING') setError(t('calendar.scheduledLocalTimeMissing'));
      else if (cause instanceof ScheduledTaskApiError && cause.code === 'SCHEDULE_OFFSET_REQUIRED') setError(t('calendar.scheduledOffsetRequired'));
      else if (cause instanceof ScheduledTaskApiError && cause.code === 'SCHEDULE_OFFSET_INVALID') setError(t('calendar.scheduledOffsetInvalid'));
      else if (cause instanceof ScheduledTaskApiError && ['SCHEDULE_INPUT_INVALID', 'SCHEDULE_RULE_INVALID', 'SCHEDULE_DATE_INVALID', 'SCHEDULE_TIME_INVALID', 'SCHEDULE_TIME_ZONE_INVALID'].includes(cause.code)) setError(t('calendar.scheduledInputInvalid'));
      else if (action === 'run' && !(cause instanceof ScheduledTaskApiError)) {
        setRunOutcomeUnknown(true); setError(t('calendar.scheduledRunOutcomeUnknown'));
      } else setError(t('calendar.scheduledActionError'));
    } finally { setBusyAction(null); }
  };
  const updateDraft = (change: Partial<EditDraft>, scheduleChanged = false) => setDraft((current) => current ? {
    ...current, ...change, ...(scheduleChanged ? { selectedOffsetMinutes: null } : {}),
  } : current);
  const applyRepeatPreset = (preset: RepeatPreset) => setDraft((current) => {
    if (!current) return current;
    if (preset === 'custom') return { ...current, repeatPreset: preset };
    if (preset === 'hourly') return { ...current, repeatPreset: preset, kind: 'hourly', intervalHours: '1', minute: '0' };
    if (preset === 'daily') return { ...current, repeatPreset: preset, kind: 'daily' };
    if (preset === 'workdays') return { ...current, repeatPreset: preset, kind: 'weekly', weekdays: [...WORKDAYS] };
    return { ...current, repeatPreset: preset, kind: 'weekly', weekdays: [current.weekdays[0] ?? 'MO'] };
  });
  const toggleWeekday = (day: Weekday) => setDraft((current) => current ? {
    ...current,
    weekdays: current.repeatPreset === 'weekly' ? [day] : current.weekdays.includes(day)
      ? current.weekdays.filter((candidate) => candidate !== day)
      : WEEKDAYS.filter((candidate) => candidate === day || current.weekdays.includes(candidate)),
  } : current);
  const openScheduleEditor = () => {
    if (!draft) return;
    setScheduleEditorSnapshot({ ...draft, weekdays: [...draft.weekdays] });
    setScheduleEditorOpen(true);
  };
  const cancelScheduleEditor = () => {
    if (scheduleEditorSnapshot) setDraft(scheduleEditorSnapshot);
    setScheduleEditorOpen(false); setScheduleEditorSnapshot(null);
  };
  const applyScheduleEditor = () => {
    if (!draft) return;
    const validation = validateDraft(draft);
    const scheduleErrors = Object.fromEntries(Object.entries(validation)
      .filter(([field]) => SCHEDULE_FIELDS.has(field as EditField))) as Partial<Record<EditField, string>>;
    setFieldErrors((current) => ({ ...current, ...scheduleErrors }));
    if (Object.keys(scheduleErrors).length > 0) return;
    setScheduleEditorOpen(false); setScheduleEditorSnapshot(null);
  };
  const scheduleSummary = draft ? (draft.repeatPreset === 'hourly'
    ? t('calendar.scheduledRepeatPreset.hourly')
    : draft.repeatPreset === 'daily' ? `${t('calendar.scheduledRepeatPreset.daily')} · ${draft.localTime}`
      : draft.repeatPreset === 'workdays' ? `${t('calendar.scheduledRepeatPreset.workdays')} · ${draft.localTime}`
        : draft.repeatPreset === 'weekly' ? `${draft.weekdays.map((day) => t(`calendar.scheduledWeekday.${day}`)).join('、')} · ${draft.localTime}`
          : draft.kind === 'once' ? `${draft.localDate} · ${draft.localTime}`
            : draft.kind === 'interval' ? t('calendar.scheduledIntervalSummary', { count: Number(draft.intervalMinutes) || 0 })
              : draft.kind === 'hourly' ? t('calendar.scheduledHourlySummary', { count: Number(draft.intervalHours) || 0, minute: Number(draft.minute) || 0 })
                : `${draft.weekdays.map((day) => t(`calendar.scheduledWeekday.${day}`)).join('、')} · ${draft.localTime}`) : '';
  const conflictFields = useMemo(() => {
    if (!draft || !conflictLatest) return [];
    const current = draftFromTask(conflictLatest); const fields: string[] = [];
    if (draft.title.trim() !== current.title) fields.push(t('calendar.scheduledTitle'));
    if (draft.prompt.trim() !== current.prompt) fields.push(t('calendar.scheduledPrompt'));
    if (draft.kind !== current.kind) fields.push(t('calendar.scheduledRule'));
    if (draft.kind === 'once' && draft.localDate !== current.localDate) fields.push(t('calendar.scheduledDate'));
    if (['once', 'daily', 'weekly'].includes(draft.kind) && draft.localTime !== current.localTime) fields.push(t('calendar.scheduledTime'));
    if (draft.kind === 'interval' && draft.intervalMinutes !== current.intervalMinutes) fields.push(t('calendar.scheduledIntervalMinutes'));
    if (draft.kind === 'hourly' && (draft.intervalHours !== current.intervalHours || draft.minute !== current.minute)) fields.push(t('calendar.scheduledHourly'));
    if (draft.kind === 'weekly' && !sameWeekdays(draft.weekdays, current.weekdays)) fields.push(t('calendar.scheduledWeekdays'));
    if (draft.timeZone.trim() !== current.timeZone) fields.push(t('calendar.scheduledTimeZone'));
    if (draft.runThreadMode !== current.runThreadMode) fields.push(t('calendar.scheduledNewChatEveryRun'));
    if (draft.modelAlias !== current.modelAlias) fields.push(t('calendar.scheduledModel'));
    return fields;
  }, [conflictLatest, draft, t]);

  if (task.status === 'deleted') return <article ref={(element) => onCardRef(task.id, element)} tabIndex={-1}
    className="calendar-popup__undo-row"><div><strong>{t('calendar.scheduledDeletedTitle', { title: task.title })}</strong>
      {unresolved ? <span>{t('calendar.scheduledDeletedRunning')}</span> : null}</div>
    <button type="button" disabled={busyAction !== null} onClick={() => void perform('restore')}>{t('calendar.scheduledRestore')}</button></article>;

  const historyRows = [...(history ?? [])].sort((left, right) => triggerTimestamp(right) - triggerTimestamp(left));
  return <>
    <article ref={(element) => onCardRef(task.id, element)} tabIndex={-1}
      className={`calendar-popup__task calendar-popup__task--${latest?.status ?? task.status}`}>
      <span className="calendar-popup__task-state" aria-label={statusLabel(task.status)}><IconClock aria-hidden="true" /></span>
      <button type="button" className="calendar-popup__task-open" onClick={onOpenResult}>
        <strong>{task.title}</strong><small>{summary}</small>
      </button>
      {task.status === 'active' || task.status === 'paused' ? <button type="button"
        className="calendar-popup__icon-button calendar-popup__edit-button"
        aria-label={actionLabel(t('calendar.scheduledEdit'))} onClick={openEditing}><IconEdit aria-hidden="true" /></button>
        : <span aria-hidden="true" />}
      <div className="calendar-popup__more-wrap">
        <button ref={moreButtonRef} type="button" className="calendar-popup__icon-button"
          aria-label={actionLabel(t('calendar.scheduledMore'))} aria-haspopup="menu" aria-expanded={moreOpen}
          aria-controls={moreMenuId} disabled={busyAction !== null} onClick={toggleMore}><IconMoreHorizontal aria-hidden="true" /></button>
        {moreOpen ? <div ref={moreMenuRef} id={moreMenuId} className="calendar-popup__more-menu" role="menu" onKeyDown={handleMoreKeyDown}>
          <button type="button" role="menuitem" disabled={stateUnknown || task.status === 'paused'} onClick={() => { setMoreOpen(false); void perform('run'); }}>{t('calendar.scheduledRun')}</button>
          <button type="button" role="menuitem" disabled={!latest?.target_thread_id || !onOpenThread} onClick={() => { setMoreOpen(false); if (latest?.target_thread_id) onOpenThread?.(latest.target_thread_id); }}>{t('calendar.scheduledOpenThread')}</button>
          <button type="button" role="menuitem" onClick={() => { setMoreOpen(false); setHistoryOpen(true); if (history === null) void loadHistory(); }}>{t('calendar.scheduledHistory')}</button>
          {task.status === 'active' ? <button type="button" role="menuitem" onClick={() => { setMoreOpen(false); void perform('pause'); }}>{t('calendar.scheduledPause')}</button> : null}
          {task.status === 'paused' ? <button type="button" role="menuitem" onClick={() => { setMoreOpen(false); void perform('resume'); }}>{t('calendar.scheduledResume')}</button> : null}
          <hr /><button type="button" role="menuitem" className="calendar-popup__danger-action" onClick={() => { setMoreOpen(false); void perform('delete'); }}>{t('calendar.scheduledDelete')}</button>
        </div> : null}
      </div>
      {error ? <div className="calendar-popup__alert" role="alert">{error}</div> : null}
      {runOutcomeUnknown ? <button type="button" className="calendar-popup__refresh-link"
        onClick={() => void perform('run')}>{t('calendar.scheduledCheckRun')}</button> : null}
    </article>

    <Modal open={active && editing} title={t('calendar.scheduledEditTitle', { title: task.title })} closeLabel={t('calendar.scheduledCancel')}
      onClose={closeEditing} initialFocusRef={firstEditFieldRef} surfaceClassName="calendar-popup-task-editor">
      {draft ? <form className="calendar-popup__edit-panel" onSubmit={(event) => { event.preventDefault(); void perform('edit'); }}>
        <p className="calendar-popup__editor-kicker">{t(`calendar.scheduledRepeatPreset.${draft.repeatPreset}`)}</p>
        <label><span>{t('calendar.scheduledTitle')}</span><input ref={firstEditFieldRef} value={draft.title}
          aria-invalid={Boolean(fieldErrors.title)} onChange={(event) => updateDraft({ title: event.target.value })} />
          {fieldErrors.title ? <small role="alert">{t('calendar.scheduledFieldRequired')}</small> : null}</label>
        <label><span>{t('calendar.scheduledPrompt')}</span><textarea value={draft.prompt} rows={8}
          aria-invalid={Boolean(fieldErrors.prompt)} onChange={(event) => updateDraft({ prompt: event.target.value })} />
          {fieldErrors.prompt ? <small role="alert">{t('calendar.scheduledFieldRequired')}</small> : null}</label>
        <label className="calendar-popup__setting-row"><span>{t('calendar.scheduledRepeat')}</span><select value={draft.repeatPreset}
          onChange={(event) => applyRepeatPreset(event.target.value as RepeatPreset)}>
          <option value="hourly">{t('calendar.scheduledRepeatPreset.hourly')}</option>
          <option value="daily">{t('calendar.scheduledRepeatPreset.daily')}</option>
          <option value="workdays">{t('calendar.scheduledRepeatPreset.workdays')}</option>
          <option value="weekly">{t('calendar.scheduledRepeatPreset.weekly')}</option>
          <option value="custom">{t('calendar.scheduledRepeatPreset.custom')}</option>
        </select></label>
        <button type="button" className="calendar-popup__schedule-row" onClick={openScheduleEditor}>
          <span>{t('calendar.scheduledAdvancedSchedule')}</span><span><small>{scheduleSummary}</small>{t('calendar.scheduledEditRule')}</span>
        </button>
        <button type="button" className="calendar-popup__advanced-toggle" aria-expanded={advancedOpen}
          onClick={() => setAdvancedOpen((current) => !current)}>{t('calendar.scheduledAdvanced')} <span aria-hidden="true">{advancedOpen ? '⌃' : '⌄'}</span></button>
        {advancedOpen ? <section className="calendar-popup__advanced-panel" aria-label={t('calendar.scheduledAdvanced')}>
          <label className="calendar-popup__switch-row"><span><strong>{t('calendar.scheduledNewChatEveryRun')}</strong>
            <small>{t('calendar.scheduledNewChatEveryRunHint')}</small></span><input type="checkbox"
              checked={draft.runThreadMode === 'new_thread_each_run'}
              onChange={(event) => updateDraft({ runThreadMode: event.target.checked ? 'new_thread_each_run' : 'source_thread' })} /></label>
          <label className="calendar-popup__setting-row"><span>{t('calendar.scheduledModel')}</span><select
            value={draft.modelAlias} disabled={modelsLoading || modelsError} aria-invalid={Boolean(fieldErrors.modelAlias)}
            onChange={(event) => updateDraft({ modelAlias: event.target.value })}>
            <option value="">{modelsLoading ? t('calendar.scheduledModelsLoading') : t('calendar.scheduledChooseModel')}</option>
            {models.map((model) => <option key={model.modelAlias} value={model.modelAlias}>{model.displayName}</option>)}
          </select>{fieldErrors.modelAlias ? <small role="alert">{t('calendar.scheduledChooseModel')}</small> : null}</label>
          {modelsError ? <div className="calendar-popup__alert" role="alert">{t('calendar.scheduledModelsUnavailable')}</div> : null}
        </section> : null}
        {conflictLatest ? <div className="calendar-popup__conflict" role="alert"><strong>{t('calendar.scheduledLatestEffective')}</strong>
          <p>{conflictLatest.title} · {planText(conflictLatest)}</p><p>{t('calendar.scheduledConflictFields', { fields: conflictFields.join(', ') || t('calendar.scheduledConflictNoFields') })}</p></div> : null}
        {error ? <div className="calendar-popup__alert" role="alert">{error}</div> : null}
        <div className="calendar-popup__edit-actions">
          {task.status === 'active' ? <button type="button" className="calendar-popup__button calendar-popup__button--secondary" disabled={busyAction !== null} onClick={() => void perform('pause')}>{t('calendar.scheduledPause')}</button> : null}
          {task.status === 'paused' ? <button type="button" className="calendar-popup__button calendar-popup__button--secondary" disabled={busyAction !== null} onClick={() => void perform('resume')}>{t('calendar.scheduledResume')}</button> : null}
          <button type="submit" className="calendar-popup__button calendar-popup__button--primary"
            disabled={busyAction !== null || modelsLoading || modelsError}>{busyAction === 'edit' ? t('calendar.scheduledSaving') : t('calendar.scheduledSave')}</button>
        </div>
      </form> : null}
    </Modal>

    <Modal open={active && editing && scheduleEditorOpen} title={t('calendar.scheduledAdvancedSchedule')}
      closeLabel={t('calendar.scheduledCancel')} onClose={cancelScheduleEditor} surfaceClassName="calendar-popup-schedule-editor">
      {draft ? <div className="calendar-popup__schedule-editor">
        {draft.repeatPreset === 'custom' ? <label><span>{t('calendar.scheduledCustomRule')}</span><select value={draft.kind}
          onChange={(event) => updateDraft({ kind: event.target.value as ScheduledRule['kind'] }, true)}>
          <option value="once">{t('calendar.scheduledOnce')}</option>
          <option value="interval">{t('calendar.scheduledIntervalMinutesOption')}</option>
          <option value="hourly">{t('calendar.scheduledIntervalHoursOption')}</option>
          <option value="weekly">{t('calendar.scheduledSelectedWeekdays')}</option>
        </select></label> : null}
        {draft.kind === 'once' ? <label><span>{t('calendar.scheduledDate')}</span><input type="date" value={draft.localDate}
          aria-invalid={Boolean(fieldErrors.localDate)} onChange={(event) => updateDraft({ localDate: event.target.value }, true)} /></label> : null}
        {draft.kind === 'interval' ? <label><span>{t('calendar.scheduledIntervalMinutes')}</span><input type="number" min="1" step="1"
          inputMode="numeric" value={draft.intervalMinutes} aria-invalid={Boolean(fieldErrors.intervalMinutes)}
          onChange={(event) => updateDraft({ intervalMinutes: event.target.value }, true)} /></label> : null}
        {draft.kind === 'hourly' && draft.repeatPreset === 'custom' ? <div className="calendar-popup__inline-fields">
          <label><span>{t('calendar.scheduledIntervalHours')}</span><input type="number" min="1" max="35791394" step="1"
            inputMode="numeric" value={draft.intervalHours} aria-invalid={Boolean(fieldErrors.intervalHours)}
            onChange={(event) => updateDraft({ intervalHours: event.target.value }, true)} /></label>
          <label><span>{t('calendar.scheduledMinute')}</span><input type="number" min="0" max="59" step="1"
            inputMode="numeric" value={draft.minute} aria-invalid={Boolean(fieldErrors.minute)}
            onChange={(event) => updateDraft({ minute: event.target.value }, true)} /></label>
        </div> : null}
        {draft.kind === 'weekly' && draft.repeatPreset !== 'workdays' ? <fieldset className="calendar-popup__weekdays" aria-invalid={Boolean(fieldErrors.weekdays)}>
          <legend>{t('calendar.scheduledWeekdays')}</legend>
          <div>{WEEKDAYS.map((day) => <label key={day}><input type="checkbox" checked={draft.weekdays.includes(day)}
            onChange={() => toggleWeekday(day)} /><span>{t(`calendar.scheduledWeekday.${day}`)}</span></label>)}</div>
          {fieldErrors.weekdays ? <small role="alert">{t('calendar.scheduledChooseWeekday')}</small> : null}
        </fieldset> : null}
        {['once', 'daily', 'weekly'].includes(draft.kind) ? <label><span>{t('calendar.scheduledTime')}</span><input type="time" value={draft.localTime}
          aria-invalid={Boolean(fieldErrors.localTime)} onChange={(event) => updateDraft({ localTime: event.target.value }, true)} /></label> : null}
        <label><span>{t('calendar.scheduledTimeZone')}</span><input value={draft.timeZone}
          aria-invalid={Boolean(fieldErrors.timeZone)} onChange={(event) => updateDraft({ timeZone: event.target.value }, true)} /></label>
        <div className="calendar-popup__schedule-actions">
          <button type="button" className="calendar-popup__button calendar-popup__button--secondary" onClick={cancelScheduleEditor}>{t('calendar.scheduledCancel')}</button>
          <button type="button" className="calendar-popup__button calendar-popup__button--primary" onClick={applyScheduleEditor}>{t('calendar.scheduledApplyRule')}</button>
        </div>
      </div> : null}
    </Modal>

    <Modal open={active && historyOpen} title={t('calendar.scheduledHistoryTitle', { title: task.title })}
      closeLabel={t('calendar.scheduledClosePanel')} onClose={closeHistory} surfaceClassName="calendar-popup-task-history">
      <section className="calendar-popup__history">
        {historyError ? <div className="calendar-popup__alert" role="alert">{t('calendar.scheduledHistoryUnavailable')}<button type="button" onClick={() => void loadHistory()}>{t('calendar.scheduledRetry')}</button></div>
          : history === null ? <p>{t('calendar.scheduledLoadingHistory')}</p>
            : historyRows.length === 0 ? <p>{t('calendar.scheduledNoHistory')}</p>
              : <ol>{historyRows.map((trigger) => <li key={trigger.id}><div><strong>{trigger.kind === 'manual' ? t('calendar.scheduledManual') : t('calendar.scheduledPlanned')}</strong><span>{statusLabel(trigger.status)}</span></div><time>{new Date(trigger.scheduled_at ?? trigger.created_at).toLocaleString(dateLocale)}</time>{trigger.target_thread_id && onOpenThread ? <button type="button" onClick={() => onOpenThread(trigger.target_thread_id!)}>{t('calendar.scheduledOpenThread')}</button> : null}</li>)}</ol>}
        {!historyError && history !== null && historyHasMore ? <button type="button" disabled={historyLoadingMore} onClick={() => void loadOlderHistory()}>{historyLoadingMore ? t('calendar.scheduledLoadingOlder') : t('calendar.scheduledLoadOlder')}</button> : null}
        {historyLoadMoreError ? <div role="alert">{t('calendar.scheduledOlderHistoryUnavailable')}</div> : null}
      </section>
    </Modal>
  </>;
}
export default function CalendarPopup({ onLoadEntry, onClose, currentEntryId, onEntryDeleted, timezone,
  initialDateKey, onOpenTaskThread, onArrangeTask, onOpenSettings }: Props) {
  const { isAuthenticated, user } = useAuth();
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
  const [selectedResultTaskId, setSelectedResultTaskId] = useState<string | null>(null);
  const [arrangePrompt, setArrangePrompt] = useState('');
  const [activeTab, setActiveTab] = useState<'tasks' | 'diary' | 'notion'>(() => isAuthenticated ? 'tasks' : 'diary');
  const [focusedTab, setFocusedTab] = useState<'tasks' | 'diary' | 'notion'>(() => isAuthenticated ? 'tasks' : 'diary');
  const [tooltipTab, setTooltipTab] = useState<string | null>(null);
  const tooltipRef = useRef<HTMLSpanElement | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ left: 0, top: 0 });
  const tabsId = useId();
  const tabRefs = useRef(new Map<string, HTMLButtonElement>());
  const tabFocusRef = useRef<string | null>(null);
  const panelRefs = useRef(new Map<string, HTMLElement>());
  const layoutRef = useRef<HTMLDivElement>(null);
  const mobileScrollRef = useRef(new Map<string, number>());
  const visibleTabs: Array<'tasks' | 'diary' | 'notion'> = isAuthenticated ? ['tasks', 'diary', 'notion'] : ['diary', 'notion'];
  useLayoutEffect(() => {
    if (!tooltipTab || tooltipTab === activeTab) return;
    const position = () => {
      const anchor = tabRefs.current.get(tooltipTab)?.getBoundingClientRect();
      const tip = tooltipRef.current?.getBoundingClientRect();
      if (!anchor || !tip) return;
      const gap = parseFloat(getComputedStyle(document.documentElement).fontSize) / 2;
      const left = Math.max(gap, Math.min(anchor.left + (anchor.width - tip.width) / 2, window.innerWidth - tip.width - gap));
      const below = anchor.bottom + gap;
      const top = Math.max(gap, Math.min(below + tip.height > window.innerHeight - gap ? anchor.top - tip.height - gap : below,
        window.innerHeight - tip.height - gap));
      setTooltipPosition({ left, top });
    };
    position(); window.addEventListener('resize', position); window.addEventListener('scroll', position, true);
    return () => { window.removeEventListener('resize', position); window.removeEventListener('scroll', position, true); };
  }, [activeTab, tooltipTab]);
  const tasksActive = activeTab === 'tasks' && isAuthenticated;
  const requestContext = JSON.stringify([isAuthenticated, user?.id, selectedDate, timezone]);
  const requestContextRef = useRef(requestContext);
  requestContextRef.current = requestContext;
  const scheduledRequestRef = useRef('');
  const scheduledGenerationRef = useRef(0);
  const scheduledMountedRef = useRef(true);
  useEffect(() => {
    scheduledMountedRef.current = true;
    return () => { scheduledMountedRef.current = false; scheduledRequestRef.current = ''; };
  }, []);
  useEffect(() => {
    if (isAuthenticated) return;
    const restoreFocus = activeTab === 'tasks' || tabFocusRef.current === 'tasks';
    if (activeTab === 'tasks') setActiveTab('diary');
    if (focusedTab === 'tasks') setFocusedTab('diary');
    if (restoreFocus) requestAnimationFrame(() => tabRefs.current.get('diary')?.focus());
  }, [activeTab, focusedTab, isAuthenticated]);
  const activateTab = (tab: 'tasks' | 'diary' | 'notion') => {
    if (tab === activeTab) return;
    const dialogs = document.querySelectorAll('[role="dialog"][aria-modal="true"]');
    if (dialogs.length > 1) return;
    if (layoutRef.current) mobileScrollRef.current.set(activeTab, layoutRef.current.scrollTop);
    setActiveTab(tab); setFocusedTab(tab); setTooltipTab(null);
    requestAnimationFrame(() => { if (layoutRef.current) layoutRef.current.scrollTop = mobileScrollRef.current.get(tab) ?? 0; });
  };

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
    scheduledRequestRef.current = ''; scheduledGenerationRef.current += 1;
    setScheduledTasks([]); setScheduledTriggers([]); setScheduledError(false); setScheduledLoading(false);
    setSelectedResultTaskId(null);
    panelRefs.current.forEach((panel) => { panel.scrollTop = 0; });
    mobileScrollRef.current.clear();
  }, [isAuthenticated, user?.id, selectedDate, timezone]);

  useEffect(() => {
    if (!isAuthenticated || !selectedDate || !tasksActive) return;
    const requestKey = `${requestContext}:${scheduledRefresh}`;
    if (scheduledRequestRef.current === requestKey) return;
    scheduledRequestRef.current = requestKey;
    const generation = ++scheduledGenerationRef.current;
    const accepts = () => scheduledMountedRef.current && scheduledGenerationRef.current === generation && requestContextRef.current === requestContext
      && scheduledRequestRef.current === requestKey;
    setScheduledError(false); setScheduledLoading(true);
    getScheduledDay(selectedDate, timezone).then(async (result) => {
      const known = new Set(result.tasks.map((task) => task.id));
      const historicalIds = [...new Set(result.triggers.map((trigger) => trigger.task_id))].filter((id) => !known.has(id));
      const historical = await Promise.all(historicalIds.map((id) => getScheduledTask(id).catch(() => null)));
      if (!accepts()) return;
      setScheduledTasks([...result.tasks, ...historical.flatMap((item) => item?.task ? [item.task] : [])]);
      setScheduledTriggers(result.triggers);
    }).catch(() => { if (accepts()) setScheduledError(true); })
      .finally(() => { if (accepts()) setScheduledLoading(false); });
  }, [isAuthenticated, selectedDate, timezone, scheduledRefresh, tasksActive, requestContext]);

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
    if (!tasksActive || !isAuthenticated || !selectedDate || !documentVisible || scheduledLoading || !activeTriggerKey
      || activeRefreshCountRef.current >= SCHEDULED_ACTIVE_REFRESH_MAXIMUM) return;
    const timer = window.setTimeout(() => {
      activeRefreshCountRef.current += 1;
      if (activeRefreshCountRef.current >= SCHEDULED_ACTIVE_REFRESH_MAXIMUM) setActiveRefreshExhausted(true);
      refreshScheduled();
    }, SCHEDULED_ACTIVE_REFRESH_INTERVAL_MS);
    return () => window.clearTimeout(timer);
  }, [activeTriggerKey, documentVisible, isAuthenticated, refreshScheduled, scheduledLoading, selectedDate, timezone, tasksActive]);
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

  const handleDateClick = (dateKey: string) => {
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
  const closeDialog = useCallback(() => onClose(), [onClose]);

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
    <div className="calendar-popup" ref={layoutRef}>
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

      {selectedDate ? <div className="calendar-popup__workspace">
        <div className="calendar-popup__tabs" role="tablist" aria-label={t('calendar.tabsLabel')}>
          {visibleTabs.map((tab) => {
            const label = tab === 'tasks' ? t('calendar.scheduledSectionTitle') : tab === 'diary' ? t('calendar.diarySectionTitle') : 'Notion';
            return <div className="calendar-popup__tab-wrap" key={tab}>
              <button type="button" role="tab" id={`${tabsId}-${tab}-tab`} aria-controls={`${tabsId}-${tab}-panel`}
                aria-label={label} aria-selected={activeTab === tab} tabIndex={focusedTab === tab ? 0 : -1}
                ref={(element) => { if (element) tabRefs.current.set(tab, element); else tabRefs.current.delete(tab); }}
                onFocus={() => { tabFocusRef.current = tab; setFocusedTab(tab); setTooltipTab(tab); }}
                onBlur={() => { tabFocusRef.current = null; setTooltipTab(null); }}
                onMouseEnter={() => setTooltipTab(tabFocusRef.current && tabFocusRef.current !== activeTab ? tabFocusRef.current : tab)}
                onMouseLeave={() => setTooltipTab(tabFocusRef.current)}
                onClick={() => activateTab(tab)} onKeyDown={(event) => {
                  const index = visibleTabs.indexOf(tab);
                  const next = event.key === 'ArrowRight' ? (index + 1) % visibleTabs.length
                    : event.key === 'ArrowLeft' ? (index - 1 + visibleTabs.length) % visibleTabs.length
                      : event.key === 'Home' ? 0 : event.key === 'End' ? visibleTabs.length - 1 : null;
                  if (next !== null) { event.preventDefault(); tabRefs.current.get(visibleTabs[next])?.focus(); }
                  else if (event.key === 'Escape' && tooltipTab !== null && activeTab !== tab) {
                    event.preventDefault(); event.stopPropagation(); setTooltipTab(null);
                  }
                }} aria-describedby={tooltipTab === tab && activeTab !== tab ? `${tabsId}-${tab}-tooltip` : undefined}>
                {tab === 'tasks' ? <IconClock aria-hidden="true" /> : tab === 'diary' ? <IconFile aria-hidden="true" /> : <NotionMark className="calendar-popup__notion-mark" />}
                {activeTab === tab ? <span>{label}</span> : null}
              </button>
              {tooltipTab === tab && activeTab !== tab ? <span ref={tooltipRef} role="tooltip" id={`${tabsId}-${tab}-tooltip`}
                style={tooltipPosition}>{label}</span> : null}
            </div>;
          })}
        </div>
        <div className="calendar-popup__workspace-scroll">
          {isAuthenticated ? <section className="calendar-popup__section calendar-popup__task-section"
            role="tabpanel" id={`${tabsId}-tasks-panel`} aria-labelledby={`${tabsId}-tasks-tab`}
            hidden={!tasksActive} inert={!tasksActive} ref={(element) => { if (element) panelRefs.current.set('tasks', element); }}>
            <header className="calendar-popup__section-heading calendar-popup__card-header">
              <h3 id="calendar-popup-task-title">{t('calendar.scheduledSectionTitleForDate', { date: selectedDateLabel })}</h3>
              <div className="calendar-popup__card-header-meta" aria-live="polite">
                {scheduledError ? <span className="calendar-popup__card-status">{t('calendar.taskCountUnknown')}</span>
                  : scheduledLoading ? <span className="calendar-popup__card-status">{t('calendar.taskCountLoading')}</span>
                    : <span className="calendar-popup__card-count">{t('calendar.scheduledCount', { count: scheduledTasks.length })}</span>}
                {!scheduledLoading && !scheduledError && attentionCount > 0 && firstAttentionTaskId
                  ? <button type="button" className="calendar-popup__count-alert" onClick={() => {
                      taskCardRefs.current.get(firstAttentionTaskId)?.focus();
                    }}>{t('calendar.attentionCount', { count: attentionCount })}</button>
                  : null}
              </div>
            </header>
            <div className="calendar-popup__card-body">
              {!selectedResultTaskId ? <form className="calendar-popup__arrange" onSubmit={(event) => {
                event.preventDefault();
                const prompt = arrangePrompt.trim();
                if (!prompt || !onArrangeTask) return;
                onArrangeTask(prompt);
              }}>
                <span aria-hidden="true">＋</span>
                <input value={arrangePrompt} onChange={(event) => setArrangePrompt(event.target.value)}
                  placeholder={t('calendar.scheduledArrangePlaceholder')} aria-label={t('calendar.scheduledArrangePlaceholder')} />
                <button type="submit" disabled={!arrangePrompt.trim() || !onArrangeTask}
                  aria-label={t('calendar.scheduledArrange')}><IconArrowUp aria-hidden="true" /></button>
              </form> : null}
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
              {selectedResultTaskId ? (() => {
                const task = scheduledTasks.find((candidate) => candidate.id === selectedResultTaskId);
                return task ? <ScheduledTaskResult active={tasksActive} task={task}
                  triggers={scheduledTriggers.filter((trigger) => trigger.task_id === task.id)}
                  onBack={() => setSelectedResultTaskId(null)} onOpenThread={onOpenTaskThread} dateLocale={dateLocale} />
                  : null;
              })() : <div className="calendar-popup__task-list">{scheduledTasks.map((task) => <ScheduledTaskCard active={tasksActive} key={task.id}
                task={task} triggers={scheduledTriggers.filter((trigger) => trigger.task_id === task.id)} onAction={actOnTask}
                onOpenThread={onOpenTaskThread} onOpenResult={() => setSelectedResultTaskId(task.id)}
                onLayerChange={onLayerChange}
                onDraftDirtyChange={onDraftDirtyChange} onCardRef={(taskId, element) => {
                  if (element) taskCardRefs.current.set(taskId, element); else taskCardRefs.current.delete(taskId);
                }} dateLocale={dateLocale} />)}</div>}
            </div>
          </section> : null}

          <section className="calendar-popup__section calendar-popup__diary-section" role="tabpanel"
            id={`${tabsId}-diary-panel`} aria-labelledby={`${tabsId}-diary-tab`} hidden={activeTab !== 'diary'} inert={activeTab !== 'diary'}
            ref={(element) => { if (element) panelRefs.current.set('diary', element); }}>
            <header className="calendar-popup__section-heading calendar-popup__card-header">
              <h3 id="calendar-popup-diary-title">{t('calendar.diarySectionTitleForDate', { date: selectedDateLabel })}</h3>
              <span className="calendar-popup__card-count" aria-live="polite">{t('calendar.entriesLabel', { count: selectedEntries.length })}</span>
            </header>
            <div className="calendar-popup__card-body">
              {selectedEntries.length === 0 ? <p className="calendar-popup__empty">{t('calendar.noEntriesForDate')}</p>
                : <div className="calendar-popup__diary-list">{selectedEntries.map((entry) => {
                  const isCurrentEntry = currentEntryId === entry.id;
                  const time = new Date(entry.timestamp).toLocaleTimeString(dateLocale, { hour: '2-digit', minute: '2-digit' });
                  return <article key={entry.id}
                    className={['calendar-popup__diary', isCurrentEntry ? 'calendar-popup__diary--current' : ''].filter(Boolean).join(' ')}>
                    <button type="button" className="calendar-popup__diary-open"
                      aria-label={t('calendar.openButton') + ': ' + entry.firstLine} onClick={() => void handleOpenEntry(entry)}>
                      <span>{time}</span>{isCurrentEntry ? <em>{t('calendar.currentEntryLabel')}</em> : null}
                      <strong>{entry.firstLine}</strong>
                    </button>
                    <button type="button" className="calendar-popup__diary-delete"
                      aria-label={t('calendar.deleteButton') + ': ' + entry.firstLine}
                      onClick={() => void handleDeleteEntry(selectedDate, entry.id)}>{t('calendar.deleteButton')}</button>
                  </article>;
                })}</div>}
            </div>
          </section>
          <section className="calendar-popup__section calendar-popup__notion-section" role="tabpanel"
            id={`${tabsId}-notion-panel`} aria-labelledby={`${tabsId}-notion-tab`} hidden={activeTab !== 'notion'} inert={activeTab !== 'notion'}
            ref={(element) => { if (element) panelRefs.current.set('notion', element); }}>
            <CalendarNotionPanel active={activeTab === 'notion'} dateKey={selectedDate} timeZone={timezone}
              onToday={(date) => { handleDateClick(date); const parsed = parseDateKey(date); setCurrentMonth(new Date(parsed.getFullYear(), parsed.getMonth(), 1)); }}
              onSettings={() => { onClose(); onOpenSettings?.(); }} />
          </section>
        </div>
      </div> : null}
    </div>
  </Modal>;
}
