// [Sync] 2026-10-07: visible serial snapshot-version checks, distinct observed/loaded/verification guards and compact single-count safe-link content.
// [Sync] 2026-10-06: show connector snapshot immediately, allow historical creation dates and verify today updates only while visible.
// [Input] Calendar active/date/timezone, authenticated actor, shared connector transport and selected-day DTO.
// [Output] Read-only local-state Notion panel with snapshot-first reads, explicit refresh, recovery and guarded response submission.
// [Pos] Calendar-owned metadata consumer; Settings owns connection and Agent owns selected body access.
// [Sync] 2026-10-05: implement Search-scope today journeys, context invalidation and hidden-panel query suspension.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { getDateLocale } from '../i18n';
import { getLocalDayKey } from '../utils/timezone';
import { getNotionToday, type NotionTodayResponse } from '../api/notionTodayApi';
import { listConnectors, ResourceConnectorApiError, RESOURCE_CONNECTORS_CHANGED_EVENT, type ResourceConnector } from '../api/resourceConnectorApi';
import { IconFile } from './chat/Icons';

type Phase = 'loading' | 'success' | 'unconnected' | 'pending' | 'expired' | 'ambiguous' | 'failed';
type Snapshot = { key: string; phase: Phase; data?: NotionTodayResponse; connectorContext?: string;
  error?: string; retryUntil?: number; failureStage?: 'probe' | 'read' | 'verify'; syncStatus?: 'applied' | 'syncing' | 'error' | 'disabled' };
type Identity = { key: string; context: string; version: string | null | undefined };
// Existing browser date-check cadence; only public local connector metadata is probed.
const DATE_CHECK_INTERVAL_MS = 60_000;
const connectorContext = (connector: ResourceConnector) => JSON.stringify([connector.id, connector.updatedAt,
  connector.auth.status, connector.sources.map((source) => [source.type, source.id]).sort()]);

export default function CalendarNotionPanel({ active, dateKey, timeZone, onSettings }: {
  active: boolean; dateKey: string; timeZone: string; onToday: (date: string) => void; onSettings: () => void;
}) {
  const { user, isAuthenticated } = useAuth();
  const { t, i18n } = useTranslation();
  const [visible, setVisible] = useState(() => typeof document === 'undefined' || document.visibilityState === 'visible');
  const [now, setNow] = useState(Date.now());
  const [serverDay, setServerDay] = useState<{ owner: string; date: string; zone: string; localDate: string | null } | null>(null);
  const owner = JSON.stringify([user?.id, timeZone]);
  const effectiveZone = serverDay?.owner === owner ? serverDay.zone : timeZone;
  let today: string | null = null;
  try { today = getLocalDayKey(new Date(Math.max(now, Date.now())), effectiveZone); } catch { /* Date feedback below. */ }
  if (serverDay?.owner === owner && today === serverDay.localDate) today = serverDay.date;
  const key = JSON.stringify([isAuthenticated, user?.id, dateKey, effectiveZone, today]);
  const currentKeyRef = useRef(key); currentKeyRef.current = key;
  const canStartRef = useRef(false); canStartRef.current = active && visible && isAuthenticated && today !== null;
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [readCycle, setReadCycle] = useState(0);
  const requestedRef = useRef('');
  const completedReadRef = useRef('');
  const observedRef = useRef<Identity | null>(null);
  const loadedRef = useRef<Identity | null>(null);
  const needsReadRef = useRef(true);
  const verifiedRef = useRef('');
  const verifyingRef = useRef('');
  const verificationFailedRef = useRef('');
  const generationRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const probeControllerRef = useRef<AbortController | null>(null);
  const probeGenerationRef = useRef(0);
  const storedRef = useRef<Snapshot | null>(null); storedRef.current = snapshot;
  const current = snapshot?.key === key ? snapshot : null;
  const dateAllowed = today !== null;

  useEffect(() => {
    const changed = () => setVisible(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', changed);
    return () => document.removeEventListener('visibilitychange', changed);
  }, []);
  useEffect(() => {
    setSnapshot(null); needsReadRef.current = true;
    return () => {
      generationRef.current += 1; controllerRef.current?.abort();
      probeGenerationRef.current += 1; probeControllerRef.current?.abort();
      requestedRef.current = ''; completedReadRef.current = ''; observedRef.current = null; loadedRef.current = null;
      verifiedRef.current = ''; verifyingRef.current = ''; verificationFailedRef.current = '';
    };
  }, [key]);
  useEffect(() => {
    if (!active || !visible) return;
    const deadline = current?.data ? Date.parse(current.data.intervalEnd) : Infinity;
    const retry = current?.retryUntil ?? Infinity;
    const delay = Math.min(DATE_CHECK_INTERVAL_MS, deadline > Date.now() ? deadline - Date.now() : DATE_CHECK_INTERVAL_MS,
      retry > Date.now() ? retry - Date.now() : DATE_CHECK_INTERVAL_MS);
    const timer = window.setTimeout(() => setNow(Date.now()), Math.max(1, delay));
    return () => window.clearTimeout(timer);
  }, [active, visible, current?.data, current?.retryUntil, now]);

  const invalidate = useCallback(() => {
    generationRef.current += 1; controllerRef.current?.abort();
    probeGenerationRef.current += 1; probeControllerRef.current?.abort();
    requestedRef.current = ''; completedReadRef.current = ''; observedRef.current = null; loadedRef.current = null;
    verifiedRef.current = ''; verifyingRef.current = ''; verificationFailedRef.current = ''; needsReadRef.current = true;
    setSnapshot(null); setReadCycle((value) => value + 1);
  }, []);
  useEffect(() => {
    window.addEventListener(RESOURCE_CONNECTORS_CHANGED_EVENT, invalidate);
    return () => window.removeEventListener(RESOURCE_CONNECTORS_CHANGED_EVENT, invalidate);
  }, [invalidate]);

  // A probe has its own cancellation owner: an unchanged observation must not
  // cancel a valid snapshot read or metadata verification already in progress.
  useEffect(() => {
    if (!active || !visible || !isAuthenticated || !dateAllowed) return;
    let stopped = false;
    let timer: number;
    const probeGeneration = ++probeGenerationRef.current;
    const schedule = () => {
      if (!stopped) timer = window.setTimeout(() => { setNow(Date.now()); void check(); }, DATE_CHECK_INTERVAL_MS);
    };
    const check = async () => {
      if (stopped || !canStartRef.current || currentKeyRef.current !== key) return;
      if ((storedRef.current?.retryUntil ?? 0) > Date.now()) { schedule(); return; }
      const controller = new AbortController(); probeControllerRef.current = controller;
      const accepts = () => !stopped && !controller.signal.aborted && canStartRef.current
        && probeGenerationRef.current === probeGeneration && currentKeyRef.current === key;
      try {
        const connectors = (await listConnectors(controller.signal)).filter((item) => item.platform === 'notion');
        if (!accepts()) return;
        if (connectors.length !== 1 || connectors[0].auth.status !== 'authenticated') {
          generationRef.current += 1; controllerRef.current?.abort(); loadedRef.current = null; observedRef.current = null;
          requestedRef.current = ''; completedReadRef.current = ''; verifiedRef.current = ''; verifyingRef.current = ''; verificationFailedRef.current = '';
          needsReadRef.current = true;
          setSnapshot({ key, phase: connectors.length !== 1 ? connectors.length ? 'ambiguous' : 'unconnected'
            : ['authenticating', 'idle'].includes(connectors[0].auth.status) ? 'pending' : 'expired' });
          return;
        }
        const connector = connectors[0];
        const observed = { key, context: connectorContext(connector), version: connector.currentSnapshotVersion };
        const before = observedRef.current;
        observedRef.current = observed;
        const contextChanged = before?.key !== key || before.context !== observed.context;
        const versionChanged = before?.version !== observed.version;
        const loaded = loadedRef.current;
        const alreadyLoaded = observed.version !== undefined && loaded?.key === key
          && loaded.context === observed.context && loaded.version === observed.version;
        if (contextChanged || versionChanged && !alreadyLoaded) {
          generationRef.current += 1; controllerRef.current?.abort(); requestedRef.current = ''; verifyingRef.current = '';
          if (contextChanged) {
            loadedRef.current = null; completedReadRef.current = ''; verifiedRef.current = ''; verificationFailedRef.current = '';
            setSnapshot(null);
          }
          needsReadRef.current = true;
        } else {
          setSnapshot((previous) => previous?.key === key && previous.connectorContext === observed.context
            ? { ...previous, syncStatus: connector.syncPolicy?.status,
              ...(previous.failureStage === 'probe' && previous.data ? { phase: 'success' as const, error: undefined, retryUntil: undefined, failureStage: undefined } : {}) } : previous);
        }
        if (!requestedRef.current && !verifyingRef.current && (needsReadRef.current || observed.version === undefined
          || loaded?.key !== key || loaded.context !== observed.context || loaded.version !== observed.version)) {
          setReadCycle((value) => value + 1);
        }
      } catch (cause) {
        if (!accepts()) return;
        const error = cause instanceof ResourceConnectorApiError ? cause : null;
        const temporary = !error || error.status >= 500 || error.status === 429;
        if (!temporary) {
          generationRef.current += 1; controllerRef.current?.abort(); loadedRef.current = null; observedRef.current = null;
          requestedRef.current = ''; completedReadRef.current = ''; verifiedRef.current = ''; verifyingRef.current = ''; verificationFailedRef.current = '';
          needsReadRef.current = true;
        }
        setSnapshot((previous) => ({ key, phase: 'failed', failureStage: 'probe', data: temporary && previous?.key === key ? previous.data : undefined,
          connectorContext: temporary && previous?.key === key ? previous.connectorContext : undefined,
          syncStatus: previous?.syncStatus, error: error?.code || (error?.status === 401 ? 'DREAM_AUTH_REQUIRED'
            : error?.status === 403 ? 'CONNECTOR_PERMISSION_DENIED' : 'NETWORK_FAILED'),
          retryUntil: error?.retryAfter ? Date.now() + error.retryAfter * 1000 : undefined }));
      } finally { if (probeControllerRef.current === controller) probeControllerRef.current = null; schedule(); }
    };
    if (observedRef.current?.key === key) void check(); else schedule();
    return () => { stopped = true; window.clearTimeout(timer); probeControllerRef.current?.abort(); };
  }, [active, visible, dateAllowed, isAuthenticated, key]);

  useEffect(() => {
    if (!active || !visible || !isAuthenticated || !dateAllowed || (storedRef.current?.retryUntil ?? 0) > Date.now()) return;
    const requestKey = `${key}:${refresh}:${readCycle}`;
    if (requestedRef.current === requestKey || completedReadRef.current === requestKey && !needsReadRef.current) return;
    requestedRef.current = requestKey;
    controllerRef.current?.abort();
    const controller = new AbortController(); controllerRef.current = controller;
    const generation = ++generationRef.current;
    let context: string | undefined;
    const accepts = () => !controller.signal.aborted && generationRef.current === generation && currentKeyRef.current === key
      && (!context || observedRef.current?.context === context);
    let old = storedRef.current?.key === key ? storedRef.current : null;
    setSnapshot({ key, phase: 'loading', data: old?.data, connectorContext: old?.connectorContext, syncStatus: old?.syncStatus });
    void (async () => {
      try {
        const connectors = (await listConnectors(controller.signal)).filter((item) => item.platform === 'notion');
        if (!accepts()) return;
        if (connectors.length !== 1) {
          loadedRef.current = null; observedRef.current = null; completedReadRef.current = ''; verifiedRef.current = ''; verifyingRef.current = ''; verificationFailedRef.current = ''; needsReadRef.current = true;
          setSnapshot({ key, phase: connectors.length ? 'ambiguous' : 'unconnected' }); return;
        }
        const connector = connectors[0];
        if (connector.auth.status !== 'authenticated') {
          loadedRef.current = null; observedRef.current = null; completedReadRef.current = ''; verifiedRef.current = ''; verifyingRef.current = ''; verificationFailedRef.current = ''; needsReadRef.current = true;
          setSnapshot({ key, phase: ['authenticating', 'idle'].includes(connector.auth.status) ? 'pending' : 'expired' }); return;
        }
        context = connectorContext(connector);
        observedRef.current = { key, context, version: connector.currentSnapshotVersion };
        if (old?.connectorContext !== context) {
          old = null; loadedRef.current = null; completedReadRef.current = ''; verifiedRef.current = ''; verificationFailedRef.current = ''; verifyingRef.current = '';
        }
        setSnapshot({ key, phase: 'loading', data: old?.data, connectorContext: context, syncStatus: connector.syncPolicy?.status });
        if (!canStartRef.current) { needsReadRef.current = true; return; }
        const response = await getNotionToday(connector.id, dateKey, controller.signal);
        if (!accepts()) return;
        if (response.connectorId !== connector.id || response.dateKey !== dateKey) {
          throw new ResourceConnectorApiError(409, 'Connection context changed', 'NOTION_CONTEXT_CHANGED');
        }
        if (response.timeZone !== effectiveZone || response.todayKey !== today) {
          throw new ResourceConnectorApiError(409, 'Date context changed', 'NOTION_DATE_CONTEXT_CHANGED', response);
        }
        loadedRef.current = connector.currentSnapshotVersion === undefined ? null : { key, context, version: response.snapshotVersion };
        needsReadRef.current = connector.currentSnapshotVersion === undefined;
        completedReadRef.current = requestKey; verificationFailedRef.current = '';
        setSnapshot({ key, phase: 'success', data: response, connectorContext: context, syncStatus: connector.syncPolicy?.status,
          retryUntil: response.retryAfter ? Date.now() + response.retryAfter * 1000 : undefined });
      } catch (cause) {
        if (!accepts()) return;
        needsReadRef.current = true;
        const error = cause instanceof ResourceConnectorApiError ? cause : null;
        if (error?.code === 'NOTION_DATE_CONTEXT_CHANGED' && typeof error.context.todayKey === 'string'
          && typeof error.context.timeZone === 'string') {
          setSnapshot(null); setServerDay({ owner, date: error.context.todayKey, zone: error.context.timeZone, localDate: getLocalDayKey(new Date(), error.context.timeZone) }); return;
        }
        const temporary = !error || error.status >= 500 || error.status === 429;
        if (!temporary) {
          loadedRef.current = null; observedRef.current = null; completedReadRef.current = ''; verifiedRef.current = ''; verifyingRef.current = ''; verificationFailedRef.current = '';
        }
        setSnapshot({ key, phase: 'failed', failureStage: 'read', data: temporary ? old?.data : undefined,
          connectorContext: temporary ? old?.connectorContext : undefined, syncStatus: old?.syncStatus,
          error: error?.code || (error?.status === 401 ? 'DREAM_AUTH_REQUIRED' : error?.status === 403 ? 'CONNECTOR_PERMISSION_DENIED'
            : error?.status === 404 ? 'NOTION_CONNECTOR_UNAVAILABLE' : 'NETWORK_FAILED'),
          retryUntil: error?.retryAfter ? Date.now() + error.retryAfter * 1000 : undefined });
      } finally { if (requestedRef.current === requestKey) requestedRef.current = ''; }
    })();
  }, [active, visible, dateAllowed, dateKey, effectiveZone, isAuthenticated, key, owner, refresh, readCycle, today]);

  useEffect(() => {
    const data = current?.data;
    if (!active || !visible || current?.phase !== 'success' || data?.verificationState !== 'pending' || !data.snapshotVersion
      || (current.retryUntil ?? 0) > Date.now()) return;
    const verificationKey = `${key}:${current.connectorContext}:${refresh}:${data.snapshotVersion}`;
    if (verifiedRef.current === verificationKey || verifyingRef.current === verificationKey || verificationFailedRef.current === verificationKey) return;
    verifyingRef.current = verificationKey;
    const controller = new AbortController(); controllerRef.current = controller;
    const generation = ++generationRef.current;
    const accepts = () => !controller.signal.aborted && generationRef.current === generation && currentKeyRef.current === key
      && observedRef.current?.context === current.connectorContext;
    setSnapshot({ ...current, key, phase: 'loading' });
    void getNotionToday(data.connectorId, dateKey, controller.signal, data.snapshotVersion).then((response) => {
      if (!accepts()) return;
      if (response.connectorId !== data.connectorId || response.dateKey !== dateKey || response.timeZone !== effectiveZone
        || response.todayKey !== data.todayKey || response.snapshotVersion !== data.snapshotVersion) {
        throw new ResourceConnectorApiError(409, 'Verification context changed', 'NOTION_CONTEXT_CHANGED');
      }
      if (['complete', 'not_required'].includes(response.verificationState)) verifiedRef.current = verificationKey;
      setSnapshot({ key, phase: 'success', data: response, connectorContext: current.connectorContext, syncStatus: current.syncStatus,
        retryUntil: response.retryAfter ? Date.now() + response.retryAfter * 1000 : undefined });
    }).catch((cause: unknown) => {
      if (!accepts()) return;
      verificationFailedRef.current = verificationKey;
      const error = cause instanceof ResourceConnectorApiError ? cause : null;
      if (error?.code === 'NOTION_DATE_CONTEXT_CHANGED' && typeof error.context.todayKey === 'string'
        && typeof error.context.timeZone === 'string') {
        setSnapshot(null); setServerDay({ owner, date: error.context.todayKey, zone: error.context.timeZone,
          localDate: getLocalDayKey(new Date(), error.context.timeZone) }); return;
      }
      const temporary = !error || error.status >= 500 || error.status === 429;
      if (!temporary) {
        needsReadRef.current = true; loadedRef.current = null; observedRef.current = null;
        completedReadRef.current = ''; verifiedRef.current = '';
      }
      setSnapshot({ key, phase: 'failed', failureStage: 'verify', data: temporary ? data : undefined,
        connectorContext: temporary ? current.connectorContext : undefined, syncStatus: current.syncStatus,
        error: error?.code ?? 'NETWORK_FAILED', retryUntil: error?.retryAfter ? Date.now() + error.retryAfter * 1000 : undefined });
    }).finally(() => { if (verifyingRef.current === verificationKey) verifyingRef.current = ''; });
  }, [active, visible, current, dateKey, effectiveZone, key, owner, refresh]);

  const errorCopy: Record<string, string> = {
    NOTION_AUTH_EXPIRED: 'expired', NOTION_PERMISSION_DENIED: 'permission', NOTION_RESOURCE_UNAVAILABLE: 'resourceUnavailable',
    NOTION_RATE_LIMITED: 'rateLimited', NOTION_UPSTREAM_UNAVAILABLE: 'upstream', NOTION_TIMEZONE_UNAVAILABLE: 'timezone',
    NOTION_API_VERSION_UNCONFIGURED: 'settingsUnavailable', NOTION_CONTEXT_CHANGED: 'contextChanged',
    NOTION_SNAPSHOT_CHANGED: 'contextChanged', NOTION_DATE_INVALID: 'timezone', NOTION_CONNECTOR_UNAVAILABLE: 'contextChanged', DREAM_AUTH_REQUIRED: 'login', INVALID_ACCESS_TOKEN: 'login',
    CONNECTOR_PERMISSION_DENIED: 'adminPermission', ADMIN_FORBIDDEN: 'adminPermission', ADMIN_PERMISSION_DENIED: 'adminPermission',
    NOTION_AUTH_PENDING: 'pending', ADMIN_DATA_UNAVAILABLE: 'settingsUnavailable', ADMIN_CAPABILITY_UNAVAILABLE: 'settingsUnavailable',
    ADMIN_CONFIGURATION_INVALID: 'settingsUnavailable', ADMIN_UNAVAILABLE: 'settingsUnavailable', ADMIN_RESPONSE_INVALID: 'settingsUnavailable',
  };
  const data = dateAllowed && isAuthenticated ? current?.data : undefined;
  const locale = getDateLocale(i18n.language);
  const localTime = (value: string) => new Date(value).toLocaleTimeString(locale, { timeZone: effectiveZone, hour: '2-digit', minute: '2-digit' });
  const refreshDisabled = current?.phase === 'loading' || (current?.retryUntil ?? 0) > now;
  const needsSync = data?.partialReasons.some((reason) => ['snapshot_unavailable', 'metadata_missing'].includes(reason));
  const syncRecovery = current?.syncStatus === 'error' ? 'syncError' : current?.syncStatus === 'disabled' ? 'syncDisabled'
    : current?.syncStatus === 'syncing' && data && (data.items.length === 0 || data.paginationState === 'partial') ? 'syncIncomplete' : null;
  const settings = <button type="button" className="calendar-popup__button" onClick={onSettings}>{t('calendar.notion.settings')}</button>;

  return <>
    <header className="calendar-popup__section-heading">
      <h3>{t('calendar.notion.title')}</h3>
      {data ? <span className="calendar-popup__card-count" data-notion-count>
        {t(data.paginationState === 'partial' ? 'calendar.notion.knownCount' : 'calendar.notion.count', { count: data.counts.total })}
      </span> : null}
      {dateAllowed && isAuthenticated ? <button type="button" className="calendar-popup__refresh-link"
        disabled={refreshDisabled} onClick={() => { needsReadRef.current = true; setRefresh((value) => value + 1); }}>{t('calendar.notion.refresh')}</button> : null}
    </header>
    <div className="calendar-popup__card-body" aria-busy={dateAllowed && current?.phase === 'loading'}>
      {!today ? <p role="alert">{t('calendar.notion.timezone')}</p> : !isAuthenticated ? <><p>{t('calendar.notion.login')}</p>{settings}</>
        : !current || current.phase === 'loading' ? !data ? <p role="status">{t('calendar.notion.loading')}</p> : null
          : ['unconnected', 'pending', 'expired', 'ambiguous'].includes(current.phase) ? <>
            <p>{t(`calendar.notion.${current.phase}`)}</p>{settings}</>
            : current.phase === 'failed' ? <div className="calendar-popup__alert" role="alert">
              <span>{t(`calendar.notion.${errorCopy[current.error ?? ''] ?? 'failed'}`)}</span>
              {data ? <span>{t('calendar.notion.stale')}</span> : null}
              {['NOTION_AUTH_EXPIRED', 'NOTION_AUTH_PENDING', 'NOTION_PERMISSION_DENIED', 'DREAM_AUTH_REQUIRED', 'CONNECTOR_PERMISSION_DENIED', 'NOTION_CONNECTOR_UNAVAILABLE'].includes(current.error ?? '') ? settings : null}
            </div> : null}
      {data ? <>
        {needsSync || syncRecovery ? <p role="status">{t(`calendar.notion.${needsSync ? 'needsSync' : syncRecovery}`)} {settings}</p> : null}
        {data.paginationState === 'partial' && !needsSync && !syncRecovery ? <p role="status">{t('calendar.notion.partial')}</p>
          : data.paginationState !== 'partial' && !needsSync && !syncRecovery && data.items.length === 0
            ? <p>{t(data.candidateCount === 0 ? 'calendar.notion.noCandidates' : dateKey === today ? 'calendar.notion.noToday' : 'calendar.notion.noDate')}</p> : null}
        {(['created', 'edited'] as const).map((group) => {
          if (group === 'edited' && dateKey !== today) return null;
          const rows = data.items.filter((item) => item.group === group);
          if (!rows.length) return null;
          return <section key={group} className="calendar-popup__notion-group" aria-label={t(`calendar.notion.${group}`)}>
            <h4>{t(`calendar.notion.${group}`)}</h4>
            <ul>{rows.map((item) => <li key={item.pageId}>
              <span aria-hidden="true">{item.emoji || <IconFile />}</span>
              <div>{item.url ? <a className="calendar-popup__notion-title" href={item.url} target="_blank" rel="noopener noreferrer"
                aria-label={t('calendar.notion.openAria', { title: item.title || t('calendar.notion.untitled') })}>
                <strong>{item.title || t('calendar.notion.untitled')}</strong></a>
                : <strong>{item.title || t('calendar.notion.untitled')}</strong>}
                <div className="calendar-popup__notion-meta">
                  {item.createdOnDate && item.createdTime ? <span>{t('calendar.notion.createdMark')} {localTime(item.createdTime)}</span> : null}
                  {item.editedOnDate && item.lastEditedTime ? <span>{t('calendar.notion.editedMark')} {localTime(item.lastEditedTime)}</span> : null}
                </div>
                {!item.url ? <p>{t('calendar.notion.urlUnavailable')}</p> : null}
              </div>
            </li>)}</ul>
          </section>;
        })}
      </> : null}
    </div>
  </>;
}
