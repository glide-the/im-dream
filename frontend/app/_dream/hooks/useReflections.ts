// [Input] Original AnalysisView state, authentication, timezone and concrete platform API/storage/navigation differences.
// [Output] One Reflections dashboard/report/reanalysis/config/task recovery state shared by Web/native.
// [Pos] State extracted from AnalysisView; original Web markup and native controls remain separate.
// [Sync] 2026-10-29: retain original task creation/recovery, diary selection and report saves; platform instances have stable owners.
import {useState,useEffect,useCallback,useRef} from 'react';
import {useTranslation} from 'react-i18next';
import * as browserApi from '../api/reflectionsApi';
import type {ReflectionAnalysisContentOptions,ReflectionResult,ReflectionSectionConfig,ReflectionSectionKey,ReflectionTaskEvent,ReflectionsApi,ReflectionsStorage} from '../api/reflectionsApi';
import {STORAGE_KEYS} from '../constants/storageKeys';
import {getDateLocale} from '../i18n';
import {getLocalDayKey} from '../utils/timezone';
import {historyReportForReading,localDateKey,type AnalysisReport} from '../components/reflectionHistory';
import {readStoryWorkspaceAnalysisSectionParam,storyWorkspaceAnalysisPathWithoutSection,type StoryWorkspaceAnalysisSection} from '../router/storyWorkspacePath';
type SectionKey=ReflectionSectionKey;
export type AnalysisSessionCandidate = {
  id: string;
  name?: string | null;
  created_at?: string;
  updated_at?: string;
  first_line?: string;
  date_key?: string | null;
  has_text?: boolean;
  word_count?: number;
};

interface ReanalysisDialogState {
  open: boolean;
  sessions: AnalysisSessionCandidate[];
  selectedIds: string[];
  error: string;
}

interface ActiveReflectionTaskState {
  taskId: string;
  sections: SectionKey[];
  lastEventId?: string;
  startedAt: number;
}

function isTerminalReflectionTaskStatus(status?: string): boolean {
  return status === 'COMPLETED' || status === 'PARTIAL_FAILED' || status === 'FAILED';
}


const browserStorage:ReflectionsStorage={getItem:key=>localStorage.getItem(key),setItem:(key,value)=>localStorage.setItem(key,value),removeItem:key=>localStorage.removeItem(key)};
function readBrowserSection(){return typeof window==='undefined'?null:readStoryWorkspaceAnalysisSectionParam(new URLSearchParams(window.location.search));}
function consumeBrowserSection(){const href=storyWorkspaceAnalysisPathWithoutSection(window.location.search);window.history.replaceState(window.history.state,'',href);window.dispatchEvent(new PopStateEvent('popstate'));}
function taskStore(localStorage:ReflectionsStorage){
function readActiveReflectionTask(): ActiveReflectionTaskState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.REFLECTIONS_ACTIVE_TASK);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ActiveReflectionTaskState>;
    if (!parsed.taskId) return null;
    const sections = Array.isArray(parsed.sections)
      ? parsed.sections.filter((s): s is SectionKey => s === 'echoes' || s === 'traits' || s === 'patterns')
      : [];
    return {
      taskId: parsed.taskId,
      sections,
      lastEventId: parsed.lastEventId,
      startedAt: typeof parsed.startedAt === 'number' ? parsed.startedAt : Date.now(),
    };
  } catch {
    return null;
  }
}

function writeActiveReflectionTask(state: ActiveReflectionTaskState): void {
  localStorage.setItem(STORAGE_KEYS.REFLECTIONS_ACTIVE_TASK, JSON.stringify(state));
}

function clearActiveReflectionTask(taskId?: string): void {
  const active = readActiveReflectionTask();
  if (!taskId || active?.taskId === taskId) {
    localStorage.removeItem(STORAGE_KEYS.REFLECTIONS_ACTIVE_TASK);
  }
}


return {readActiveReflectionTask,writeActiveReflectionTask,clearActiveReflectionTask};
}
export interface ReflectionsStateOptions {
  timezone:string;authenticated:boolean;authLoading?:boolean;api?:ReflectionsApi;storage?:ReflectionsStorage;
  readRequestedSection?:()=>StoryWorkspaceAnalysisSection|null;consumeRequestedSection?:()=>void;
}
export default function useReflections(options:ReflectionsStateOptions){
  const {timezone,authenticated:isAuthenticated,authLoading:isAuthLoading=false}=options;
  const {t,i18n}=useTranslation(),dateLocale=getDateLocale(i18n.language);
  const owners=useRef({api:options.api??browserApi,storage:options.storage??browserStorage,readSection:options.readRequestedSection??readBrowserSection,consumeSection:options.consumeRequestedSection??consumeBrowserSection});
  const {api,storage:localStorage,readSection:readRequestedSection,consumeSection:consumeRequestedSection}=owners.current;
  const {ensureReflectionTaskReport,getAnalysisHistory,fetchSessionsAggregate,getLatestReflections,getReflectionTask,getReflectionsSectionConfig,resumeReflectionsTask,runReflectionsTask,saveReflectionsSectionConfig,resetReflectionsSectionConfig}=api;
  const {readActiveReflectionTask,writeActiveReflectionTask,clearActiveReflectionTask}=useRef(taskStore(localStorage)).current;
  // ── State ──
  const [echoes, setEchoes]       = useState<ReflectionResult[]>([]);
  const [traits, setTraits]       = useState<ReflectionResult[]>([]);
  const [patterns, setPatterns]   = useState<ReflectionResult[]>([]);
  const [loading, setLoading]     = useState({ echoes: false, traits: false, patterns: false });
  const [streaming, setStreaming] = useState({ echoes: '', traits: '', patterns: '' });
  const [errors, setErrors]       = useState({ echoes: '', traits: '', patterns: '' });
  const [stats, setStats]         = useState({ totalDays: 0, totalWords: 0, totalEntries: 0 });
  const [savedReports, setSavedReports] = useState<AnalysisReport[]>([]);
  const statsRef = useRef(stats);
  statsRef.current = stats;
  const [analyzableSessions, setAnalyzableSessions] = useState<AnalysisSessionCandidate[]>([]);
  const [analysisContent, setAnalysisContent] = useState<ReflectionAnalysisContentOptions>({ include_notion: false });
  const submittingRef = useRef(false);
  const [reportSaveError, setReportSaveError] = useState('');
  const [reportRetryTaskId, setReportRetryTaskId] = useState<string>();
  const [reportSaving, setReportSaving] = useState(false);
  const [taskStatus, setTaskStatus] = useState('');
  const [activeRecoveryTick, setActiveRecoveryTick] = useState(0);
  const [preparedTask, setPreparedTask] = useState<ActiveReflectionTaskState | null>(null);
  const explicitStartTaskIdRef = useRef<string | null>(null);
  const recoveringTaskIdRef = useRef<string | null>(null);
  const [reanalysisDialog, setReanalysisDialog] = useState<ReanalysisDialogState>({
    open: false,
    sessions: [],
    selectedIds: [],
    error: '',
  });

  // View modes
  const [viewMode, setViewMode] = useState<'dashboard' | 'report' | 'blog'>('dashboard');
  const [currentPaper, setCurrentPaper] = useState(0);
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);
  const [savedReportsLoaded, setSavedReportsLoaded] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState(false);
  const historyRequestRef = useRef(0);
  const historyControllerRef = useRef<AbortController | null>(null);
  const [requestedBlogSection, setRequestedBlogSection] = useState<StoryWorkspaceAnalysisSection | null>(null);
  const requestedReflectionSectionRef = useRef<StoryWorkspaceAnalysisSection | null>(
    readRequestedSection(),
  );

  // Section config modal
  const [configModal, setConfigModal] = useState<{
    open: boolean;
    section: SectionKey;
    displayName: string;
    config: ReflectionSectionConfig | null;
    files: Record<string, string>;
    loading: boolean;
    saving: boolean;
    error: string;
  }>({
    open: false, section: 'echoes', displayName: 'Recurring Themes',
    config: null, files: {}, loading: false, saving: false, error: '',
  });

  // ── Load data ──
  const reloadSavedReports = useCallback(async () => {
    const hasActiveRecovery = Boolean(readActiveReflectionTask());
    if (!isAuthenticated) {
      setHistoryLoading(false); setSavedReportsLoaded(true);
      const saved = localStorage.getItem(STORAGE_KEYS.ANALYSIS_REPORTS);
      if (saved) {
        try {
          const reports: AnalysisReport[] = JSON.parse(saved);
          const ordered = reports.filter(report => Number.isFinite(report.timestamp))
            .sort((a, b) => b.timestamp - a.timestamp || (BigInt(b.id) > BigInt(a.id) ? 1 : BigInt(b.id) < BigInt(a.id) ? -1 : 0));
          setSavedReports(ordered);
          if (!hasActiveRecovery) {
            const latestEchoes = ordered.find(report => report.echoes.length > 0);
            const latestTraits = ordered.find(report => report.traits.length > 0);
            const latestPatterns = ordered.find(report => report.patterns.length > 0);
            if (latestEchoes) setEchoes(latestEchoes.echoes);
            if (latestTraits) setTraits(latestTraits.traits);
            if (latestPatterns) setPatterns(latestPatterns.patterns);
          }
        } catch { setHistoryError(true); }
      }
      return;
    }
    const request = ++historyRequestRef.current;
    historyControllerRef.current?.abort();
    const controller = new AbortController();
    historyControllerRef.current = controller;
    const isCurrent = () => !controller.signal.aborted && request === historyRequestRef.current;
    setHistoryLoading(true); setHistoryError(false); setSavedReportsLoaded(false);
    let individual: AnalysisReport[] = [];
    let cursor: import('../api/voiceApi').AnalysisHistoryCursor | null = null;
    let historyRead = false;
    try {
      const page = await getAnalysisHistory({ signal: controller.signal });
      individual = page.reports.map(historyReportForReading);
      const requestedSection = requestedReflectionSectionRef.current;
      cursor = page.next_cursor;
      // Preserve Chat's latest matching-section intent beyond the server's first history page.
      while (requestedSection && !individual.some(report => report[requestedSection].length > 0) && cursor) {
        const older = await getAnalysisHistory({ before: cursor, signal: controller.signal });
        individual = [...individual, ...older.reports.map(historyReportForReading)]; cursor = older.next_cursor;
      }
      if (!isCurrent()) return;
      historyRead = true;
      setSavedReports(individual);
      if (!hasActiveRecovery) {
        const latestEchoes = individual.find(report => report.echoes.length > 0);
        const latestTraits = individual.find(report => report.traits.length > 0);
        const latestPatterns = individual.find(report => report.patterns.length > 0);
        if (latestEchoes) setEchoes(latestEchoes.echoes);
        if (latestTraits) setTraits(latestTraits.traits);
        if (latestPatterns) setPatterns(latestPatterns.patterns);
      }
    } catch { if (isCurrent()) setHistoryError(true); }
    finally { if (isCurrent()) setHistoryLoading(false); }
    if (!isCurrent()) return;
    // History availability must not disable the existing task status/recovery path.
    try {
      const latest = await getLatestReflections();
      if (!isCurrent()) return;
      if (latest.task?.status === 'CREATED' && explicitStartTaskIdRef.current !== latest.task.task_id) {
        setPreparedTask({ taskId: latest.task.task_id, sections: latest.task.sections,
          startedAt: new Date(latest.task.created_at || Date.now()).getTime() });
        const active = readActiveReflectionTask();
        if (!submittingRef.current && (!active || active.taskId === latest.task.task_id)) {
          clearActiveReflectionTask(latest.task.task_id);
          setLoading({ echoes: false, traits: false, patterns: false });
          setStreaming({ echoes: '', traits: '', patterns: '' });
          setTaskStatus('');
        }
      }
      if (latest.task && latest.task.status !== 'CREATED' && !isTerminalReflectionTaskStatus(latest.task.status)) {
        const sections = latest.task.sections.length > 0 ? latest.task.sections : ['echoes', 'traits', 'patterns'] as SectionKey[];
        writeActiveReflectionTask({ taskId: latest.task.task_id, sections,
          startedAt: new Date(latest.task.started_at || latest.task.created_at || Date.now()).getTime() || Date.now() });
        setViewMode('dashboard'); setSelectedReport(null);
        setTaskStatus(`task · ${latest.task.status.toLowerCase()}`);
        setLoading({ echoes: sections.includes('echoes'), traits: sections.includes('traits'), patterns: sections.includes('patterns') });
        setStreaming({ echoes: '', traits: '', patterns: '' }); setActiveRecoveryTick(tick => tick + 1);
        return;
      }
      if (!hasActiveRecovery && latest.task && isTerminalReflectionTaskStatus(latest.task.status)
        && latest.results.length > 0 && latest.results.every(result => result.task_id === latest.task?.task_id)) {
        const latestEchoes = latest.results.filter(result => result.section === 'echoes');
        const latestTraits = latest.results.filter(result => result.section === 'traits');
        const latestPatterns = latest.results.filter(result => result.section === 'patterns');
        if (latestEchoes.length) setEchoes(latestEchoes);
        if (latestTraits.length) setTraits(latestTraits);
        if (latestPatterns.length) setPatterns(latestPatterns);
        // An updated older task can fall outside the preview. Verify its presence before offering save recovery.
        while (historyRead && !individual.some(report => report.taskId === latest.task?.task_id) && cursor) {
          const older = await getAnalysisHistory({ before: cursor, signal: controller.signal });
          individual = [...individual, ...older.reports.map(historyReportForReading)]; cursor = older.next_cursor;
        }
        if (!isCurrent()) return;
        if (historyRead && !individual.some(report => report.taskId === latest.task?.task_id)) {
          setReportRetryTaskId(latest.task.task_id);
          setReportSaveError(dateLocale.startsWith('zh') ? '分析结果已保留，报告暂未保存。请重试保存。' : 'The analysis result is available, but its report has not been saved.');
        }
      }
    } catch (error) { if (isCurrent()) console.warn('[Reflections] latest task load failed:', error); }
    finally { if (isCurrent() && historyRead) setSavedReportsLoaded(true); }
  }, [isAuthenticated, dateLocale]);

  useEffect(() => {
    if (isAuthLoading) {
      setSavedReportsLoaded(false);
      return;
    }
    let active = true;
    const loadStats = async () => {
      try {
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai';
        const agg = await fetchSessionsAggregate(tz);
        setStats({ totalDays: agg.stats.total_days, totalWords: agg.stats.total_words, totalEntries: agg.stats.total_entries });
        setAnalyzableSessions((agg.sessions || [])
          .filter(session => session.has_text)
          .map(session => ({
            id: session.id,
            name: session.name,
            created_at: session.created_at,
            updated_at: session.updated_at,
            date_key: undefined,
            first_line: session.name,
            has_text: session.has_text,
            word_count: session.word_count,
          })));
      } catch (e) { console.error(e); }
    };
    setSavedReportsLoaded(false);
    void Promise.all([loadStats(), reloadSavedReports()]).finally(() => {
      if (active) setHistoryLoading(false);
    });
    return () => { active = false; historyControllerRef.current?.abort(); historyRequestRef.current += 1; };
  }, [isAuthLoading, isAuthenticated, reloadSavedReports]);

  // ── Config modal handlers ──
  const handleOpenConfig = useCallback(async (section: SectionKey) => {
    const DISPLAY: Record<SectionKey, string> = {
      echoes: 'Recurring Themes', traits: 'Character Traits', patterns: 'Behavioral Patterns',
    };
    setConfigModal(p => ({
      ...p, open: true, section, displayName: DISPLAY[section],
      loading: true, error: '', config: null, files: {},
    }));
    try {
      const cfg = await getReflectionsSectionConfig(section);
      setConfigModal(p => ({ ...p, config: cfg, files: { ...cfg.prompt_files }, loading: false }));
    } catch (e) {
      setConfigModal(p => ({ ...p, loading: false, error: String(e) }));
    }
  }, []);

  const handleSaveConfig = useCallback(async () => {
    setConfigModal(p => ({ ...p, saving: true, error: '' }));
    try {
      await saveReflectionsSectionConfig(configModal.section, configModal.files);
      setConfigModal(p => ({ ...p, saving: false, open: false }));
    } catch (e) {
      setConfigModal(p => ({ ...p, saving: false, error: String(e) }));
    }
  }, [configModal.section, configModal.files]);

  const handleResetConfig = useCallback(async () => {
    setConfigModal(p => ({ ...p, saving: true, error: '' }));
    try {
      await resetReflectionsSectionConfig(configModal.section);
      const cfg = await getReflectionsSectionConfig(configModal.section);
      setConfigModal(p => ({ ...p, saving: false, config: cfg, files: { ...cfg.prompt_files } }));
    } catch (e) {
      setConfigModal(p => ({ ...p, saving: false, error: String(e) }));
    }
  }, [configModal.section]);

  const handleTaskEvent = useCallback((event: ReflectionTaskEvent) => {
    const section = typeof event.payload?.section === 'string' ? event.payload.section as SectionKey : undefined;
    const statusText = event.type
      .replace('reflection.', '')
      .replaceAll('.', ' · ')
      .replace('client · task · created', 'task · created');
    setTaskStatus(statusText);

    if (event.type === 'reflection.client.task.created') {
      const sections = Array.isArray(event.payload?.sections)
        ? event.payload.sections.filter((s): s is SectionKey => s === 'echoes' || s === 'traits' || s === 'patterns')
        : [];
      writeActiveReflectionTask({
        taskId: event.task_id,
        sections,
        lastEventId: event.id,
        startedAt: Date.now(),
      });
    } else if (event.id && event.task_id) {
      const active = readActiveReflectionTask();
      if (active?.taskId === event.task_id) {
        writeActiveReflectionTask({ ...active, lastEventId: event.id });
      }
    }

    if (event.type === 'reflection.task.completed' || event.type === 'reflection.task.partial_failed' || event.type === 'reflection.task.failed') {
      clearActiveReflectionTask(event.task_id);
    }

    if (section && ['echoes', 'traits', 'patterns'].includes(section)) {
      setStreaming(p => ({ ...p, [section]: statusText }));
    }
  }, []);

  const openReflectionBlogReport = useCallback((
    report: Omit<AnalysisReport, 'id' | 'timestamp'> & Partial<Pick<AnalysisReport, 'id' | 'timestamp'>>,
    initialSection: StoryWorkspaceAnalysisSection | null = null,
  ) => {
    const wrapped: AnalysisReport = {
      id: report.id ?? Date.now(),
      echoes: report.echoes,
      traits: report.traits,
      patterns: report.patterns,
      timestamp: report.timestamp ?? Date.now(),
      stats: report.stats,
      createdAt: report.createdAt,
      taskId: report.taskId,
      failedSections: report.failedSections,
      analysisContent: report.analysisContent,
    };
    setSelectedReport(wrapped);
    setRequestedBlogSection(initialSection);
    setViewMode('blog');
  }, []);

  useEffect(() => {
    const section = requestedReflectionSectionRef.current;
    if (!savedReportsLoaded || !section) return;

    requestedReflectionSectionRef.current = null;
    const matchingReport = savedReports.find((report) => report[section].length > 0);
    if (matchingReport) openReflectionBlogReport(matchingReport, section);

    consumeRequestedSection();
  }, [openReflectionBlogReport, savedReports, savedReportsLoaded]);

  const retryReportSave = useCallback(async (taskId: string) => {
    setReportSaving(true);
    try {
      await ensureReflectionTaskReport(taskId);
      await reloadSavedReports();
      setReportSaveError(''); setReportRetryTaskId(undefined);
    } catch (error) {
      setReportSaveError(error instanceof Error ? error.message : String(error));
      setReportRetryTaskId(taskId);
    } finally { setReportSaving(false); }
  }, [reloadSavedReports]);

  const openTaskReport = useCallback(async (entry: AnalysisReport) => {
    const taskId = entry.taskId ?? [...entry.echoes, ...entry.traits, ...entry.patterns].find(item => item.task_id)?.task_id;
    let report = entry;
    if (taskId) {
      try {
        const task = await getReflectionTask(taskId);
        if (!task.created_at || !Number.isFinite(new Date(task.created_at).getTime())) throw new Error(t('analysis.history.failed'));
        report = { ...entry, timestamp: new Date(task.created_at).getTime(), createdAt: task.created_at, taskId, failedSections: task.failed_sections, analysisContent: task.analysis_content };
      } catch (error) {
        setReportSaveError(error instanceof Error ? error.message : String(error));
        return;
      }
      await retryReportSave(taskId);
    }
    localStorage.setItem(STORAGE_KEYS.REFLECTIONS_ANALYSIS_CLICKED_DATE, localDateKey(entry.timestamp));
    openReflectionBlogReport(report);
  }, [openReflectionBlogReport, retryReportSave, t]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const active = readActiveReflectionTask();
    if (!active || recoveringTaskIdRef.current === active.taskId) return;

    let cancelled = false;
    recoveringTaskIdRef.current = active.taskId;
    setViewMode('dashboard');
    setSelectedReport(null);
    setTaskStatus('task · reconnecting');
    const sections = active.sections.length > 0 ? active.sections : ['echoes', 'traits', 'patterns'] as SectionKey[];
    setLoading({
      echoes: sections.includes('echoes'),
      traits: sections.includes('traits'),
      patterns: sections.includes('patterns'),
    });
    setStreaming({ echoes: '', traits: '', patterns: '' });

    const restore = async () => {
      let er: ReflectionResult[] = [], tr: ReflectionResult[] = [], pr: ReflectionResult[] = [];
      try {
        const snapshot = await getReflectionTask(active.taskId);
        if (cancelled) return;
        if (snapshot.status === 'CREATED' && explicitStartTaskIdRef.current !== active.taskId) {
          setPreparedTask(active);
          clearActiveReflectionTask(active.taskId);
          setTaskStatus('');
          recoveringTaskIdRef.current = null;
          return;
        }
        const bySection = await resumeReflectionsTask(active.taskId, {
          lastEventId: active.lastEventId,
          startPrepared: explicitStartTaskIdRef.current === active.taskId,
          onEvent: handleTaskEvent,
        });
        if (cancelled) return;
        er = bySection.echoes;
        tr = bySection.traits;
        pr = bySection.patterns;
        setEchoes(er);
        setTraits(tr);
        setPatterns(pr);
        clearActiveReflectionTask(active.taskId);
        setPreparedTask(null);
        explicitStartTaskIdRef.current = null;
        setTaskStatus('task · restored');
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : String(e);
          setErrors({ echoes: msg, traits: '', patterns: '' });
          setTaskStatus('task · reconnect failed');
        }
      } finally {
        if (!cancelled) {
          setLoading({ echoes: false, traits: false, patterns: false });
          setStreaming({ echoes: '', traits: '', patterns: '' });
        }
      }

      if (!cancelled && (er.length || tr.length || pr.length)) {
        const reportData = {
          echoes: er, traits: tr, patterns: pr,
          stats: { days: statsRef.current.totalDays, entries: statsRef.current.totalEntries, words: statsRef.current.totalWords },
        };
        const entry: AnalysisReport = { id: Date.now(), ...reportData, timestamp: Date.now() };
        await openTaskReport(entry);
      }
    };

    void restore();
    return () => {
      cancelled = true;
      if (recoveringTaskIdRef.current === active.taskId) recoveringTaskIdRef.current = null;
    };
  }, [activeRecoveryTick, handleTaskEvent, isAuthenticated, openReflectionBlogReport, reloadSavedReports, openTaskReport]);


  // ── One-click analyze all ──
  const runAnalyzeAll = async (sessionIds?: string[]) => {
    if (!isAuthenticated) {
      setErrors({ echoes: 'Please log in to use reflections.', traits: '', patterns: '' });
      return;
    }
    setReportSaveError(''); setReportRetryTaskId(undefined);
    setPreparedTask(null);
    setErrors({ echoes: '', traits: '', patterns: '' });
    setStreaming({ echoes: '', traits: '', patterns: '' });
    setTaskStatus('task · preparing');
    setViewMode('dashboard');
    setSelectedReport(null);
    setEchoes([]);
    setTraits([]);
    setPatterns([]);
    setLoading({ echoes: true, traits: true, patterns: true });

    let er: ReflectionResult[] = [], tr: ReflectionResult[] = [], pr: ReflectionResult[] = [];
    try {
      const bySection = await runReflectionsTask({
        language: i18n.language,
        sessionIds,
        analysisContent: { ...analysisContent },
        onEvent: handleTaskEvent,
      });
      er = bySection.echoes;
      tr = bySection.traits;
      pr = bySection.patterns;
      setEchoes(er);
      setTraits(tr);
      setPatterns(pr);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrors({ echoes: msg, traits: '', patterns: '' });
      if (!readActiveReflectionTask()) setTaskStatus('');
    } finally {
      setLoading({ echoes: false, traits: false, patterns: false });
      setStreaming({ echoes: '', traits: '', patterns: '' });
    }

    if (er.length || tr.length || pr.length) {
      const reportData = {
        echoes: er, traits: tr, patterns: pr,
        stats: { days: stats.totalDays, entries: stats.totalEntries, words: stats.totalWords },
      };
      const entry: AnalysisReport = { id: Date.now(), ...reportData, timestamp: Date.now() };
      await openTaskReport(entry);
    }
  };

  const handleAnalyzeAll = async () => {
    if (anyLoading || submittingRef.current) return;
    submittingRef.current = true;
    try {
    const active = readActiveReflectionTask();
    if (active?.taskId) {
      try {
        const task = await getReflectionTask(active.taskId);
        if (isTerminalReflectionTaskStatus(task.status) || task.status === 'CREATED') {
          if (task.status === 'CREATED') setPreparedTask(active);
          clearActiveReflectionTask(active.taskId);
        } else {
          const sections = active.sections.length > 0 ? active.sections : ['echoes', 'traits', 'patterns'] as SectionKey[];
          setReanalysisDialog(prev => ({ ...prev, open: false, error: '' }));
          setViewMode('dashboard');
          setSelectedReport(null);
          setTaskStatus('task · reconnecting');
          setLoading({
            echoes: sections.includes('echoes'),
            traits: sections.includes('traits'),
            patterns: sections.includes('patterns'),
          });
          setStreaming({ echoes: '', traits: '', patterns: '' });

          try {
            const bySection = await resumeReflectionsTask(active.taskId, {
              lastEventId: active.lastEventId,
              onEvent: handleTaskEvent,
            });
            const er = bySection.echoes;
            const tr = bySection.traits;
            const pr = bySection.patterns;
            setEchoes(er);
            setTraits(tr);
            setPatterns(pr);
            clearActiveReflectionTask(active.taskId);
            setTaskStatus('task · restored');
            if (er.length || tr.length || pr.length) {
              const reportData = {
                echoes: er, traits: tr, patterns: pr,
                stats: { days: stats.totalDays, entries: stats.totalEntries, words: stats.totalWords },
              };
              const entry: AnalysisReport = { id: Date.now(), ...reportData, timestamp: Date.now() };
              await openTaskReport(entry);
            }
          } catch (resumeError) {
            const msg = resumeError instanceof Error ? resumeError.message : String(resumeError);
            setErrors({ echoes: msg, traits: '', patterns: '' });
            setTaskStatus('task · reconnect failed');
          } finally {
            setLoading({ echoes: false, traits: false, patterns: false });
            setStreaming({ echoes: '', traits: '', patterns: '' });
          }
          return;
        }
      } catch (e) {
        console.warn('[Reflections] active task validation failed before analysis start:', e);
        setErrors({ echoes: e instanceof Error ? e.message : String(e), traits: '', patterns: '' });
        return;
      }
    }

    const todayKey = getLocalDayKey(Date.now(), timezone);
    const hasTodayReport = savedReports.some(report => getLocalDayKey(report.timestamp, timezone) === todayKey);
    if (hasTodayReport) {
      const candidates = analyzableSessions.filter(session => session.has_text !== false);
      setReanalysisDialog({
        open: true,
        sessions: candidates,
        selectedIds: candidates.map(session => session.id),
        error: candidates.length === 0 && !analysisContent.include_notion ? 'No analyzable diary entries are available.' : '',
      });
      return;
    }
    await runAnalyzeAll();
    } finally { submittingRef.current = false; }
  };

  const handleToggleReanalysisSession = useCallback((sessionId: string) => {
    setReanalysisDialog(prev => {
      const selected = new Set(prev.selectedIds);
      if (selected.has(sessionId)) selected.delete(sessionId);
      else selected.add(sessionId);
      return { ...prev, selectedIds: [...selected], error: '' };
    });
  }, []);

  const handleToggleAllReanalysisSessions = useCallback(() => {
    setReanalysisDialog(prev => ({
      ...prev,
      selectedIds: prev.selectedIds.length === prev.sessions.length ? [] : prev.sessions.map(session => session.id),
      error: '',
    }));
  }, []);

  const handleConfirmReanalysis = async () => {
    const selectedIds = reanalysisDialog.selectedIds;
    if (submittingRef.current) return;
    if (selectedIds.length === 0 && !analysisContent.include_notion) {
      setReanalysisDialog(prev => ({ ...prev, error: 'Select at least one diary entry before re-analyzing.' }));
      return;
    }
    setReanalysisDialog(prev => ({ ...prev, open: false, error: '' }));
    submittingRef.current = true;
    try { await runAnalyzeAll(selectedIds); } finally { submittingRef.current = false; }
  };

  const anyLoading = loading.echoes || loading.traits || loading.patterns;
  const hasAnyData = echoes.length > 0 || traits.length > 0 || patterns.length > 0;
  const anyError = errors.echoes || errors.traits || errors.patterns;


  const continuePreparedTask=()=>{
    if(!preparedTask)return;
    explicitStartTaskIdRef.current=preparedTask.taskId;
    recoveringTaskIdRef.current=null;
    writeActiveReflectionTask(preparedTask);
    setLoading({echoes:preparedTask.sections.includes('echoes'),traits:preparedTask.sections.includes('traits'),patterns:preparedTask.sections.includes('patterns')});
    setActiveRecoveryTick(tick=>tick+1);
  };
  return {continuePreparedTask,echoes,traits,patterns,loading,streaming,errors,stats,savedReports,analysisContent,setAnalysisContent,reportSaveError,reportRetryTaskId,reportSaving,taskStatus,setActiveRecoveryTick,preparedTask,explicitStartTaskIdRef,recoveringTaskIdRef,setLoading,writeActiveReflectionTask,reanalysisDialog,setReanalysisDialog,viewMode,setViewMode,currentPaper,setCurrentPaper,selectedReport,historyLoading,historyError,requestedBlogSection,setRequestedBlogSection,configModal,setConfigModal,reloadSavedReports,handleOpenConfig,handleSaveConfig,handleResetConfig,openReflectionBlogReport,retryReportSave,handleAnalyzeAll,handleToggleReanalysisSession,handleToggleAllReanalysisSessions,handleConfirmReanalysis,anyLoading,hasAnyData,anyError};
}
