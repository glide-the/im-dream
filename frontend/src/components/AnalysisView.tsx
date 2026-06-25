/**
 * [Input] voiceApi: analyzeEchoes, analyzeTraits, analyzePatterns, saveAnalysisReport,
 *         getAnalysisReports, fetchSessionsAggregate, ReflectionResult,
 *         getReflectionsSectionConfig, saveReflectionsSectionConfig, resetReflectionsSectionConfig,
 *         ReflectionSectionConfig
 * [Output] Reflections page — warm paper / vintage journal design (CSS design tokens)
 * [Pos] components/AnalysisView — full-page Reflections (Analysis) view
 * [Sync] 2026-06-07: Restore warm paper theme (develop branch aesthetic: Georgia font,
 *         var(--color-bg-app) palette, PaperStack 3D stacked-paper animation).
 *         Types migrated to unified ReflectionResult[]; confidence replaces strength/frequency.
 *         Per-section streaming analyze + ⚙ SectionConfigModal retained.
 *         One-click 「Generate Reflections」 button in dashboard header retained.
 * [Sync] 2026-06-09: Past Reflections cards now open a full-page blog view (ReflectionBlogPage)
 *         instead of the PaperStack popup. viewMode extends to 'blog'; selectedReport state tracks
 *         which report is being read. Color spec: docs/prd/color_system/reflection-blog.md
 * [Sync] 2026-06-12: remove obsolete session cache and unused blog card after saved-report flow moved
 *         to aggregate/report APIs.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  saveAnalysisReport,
  getAnalysisReports,
  fetchSessionsAggregate,
  getLatestReflections,
  getReflectionsSectionConfig,
  runReflectionsTask,
  saveReflectionsSectionConfig,
  resetReflectionsSectionConfig,
  type ReflectionResult,
  type ReflectionSectionConfig,
  type ReflectionSectionKey,
  type ReflectionTaskEvent,
} from '../api/voiceApi';
import { useAuth } from '../contexts/AuthContext';
import { STORAGE_KEYS } from '../constants/storageKeys';
import { getDateLocale } from '../i18n';
import { useMobile } from '../utils/mobileDetect';

// ──────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────
const MAX_SAVED_REPORTS = 10;

const PROMPT_FILE_ORDER = [
  'WORKFLOW.md',
  'MEMORY_QUERY_PROMPT.md',
  'MEMORY_Distiller_PROMPT.md',
  'MEMORY_ANSWER_PROMPT.md',
  'DEFAULT_UPDATE_MEMORY_PROMPT.md',
] as const;

const PROMPT_FILE_LABELS: Record<string, string> = {
  'WORKFLOW.md': 'Analysis Workflow',
  'MEMORY_QUERY_PROMPT.md': 'Signal Query',
  'MEMORY_Distiller_PROMPT.md': 'Distillation Rules',
  'MEMORY_ANSWER_PROMPT.md': 'Output Format',
  'DEFAULT_UPDATE_MEMORY_PROMPT.md': 'Update Rules',
};

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────
type SectionKey = ReflectionSectionKey;

interface AnalysisReport {
  id: number;
  echoes: ReflectionResult[];
  traits: ReflectionResult[];
  patterns: ReflectionResult[];
  timestamp: number;
  stats: { days: number; entries: number; words: number };
}

// ──────────────────────────────────────────────
// Section config modal
// ──────────────────────────────────────────────
interface SectionConfigModalProps {
  open: boolean;
  section: SectionKey;
  displayName: string;
  files: Record<string, string>;
  loading: boolean;
  saving: boolean;
  isCustom: boolean;
  error: string;
  onClose: () => void;
  onSave: () => void;
  onReset: () => void;
  onFileChange: (filename: string, content: string) => void;
}

function SectionConfigModal({
  open, section: _section, displayName, files, loading, saving, isCustom, error,
  onClose, onSave, onReset, onFileChange,
}: SectionConfigModalProps) {
  if (!open) return null;
  const borderColor = 'var(--color-border-paper)';
  const muted = 'var(--color-text-muted)';
  const body = 'var(--color-text-body)';
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'var(--color-bg-overlay)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--color-bg-paper)', border: `1px solid ${borderColor}`,
          borderRadius: '12px', width: '100%', maxWidth: '680px',
          maxHeight: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden',
          boxShadow: '0 16px 48px var(--color-shadow-medium)',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '1.25rem 1.5rem', borderBottom: `1px solid ${borderColor}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{
              fontSize: '10px', fontWeight: 600, letterSpacing: '1.5px',
              textTransform: 'uppercase', color: muted,
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            }}>
              CONFIGURE
            </span>
            <span style={{
              fontFamily: 'Georgia, serif', fontStyle: 'italic',
              fontSize: '18px', color: body,
            }}>
              {displayName}
            </span>
            {isCustom && (
              <span style={{
                fontSize: '10px', fontWeight: 600, letterSpacing: '0.5px',
                color: 'var(--color-state-warning)',
                background: 'color-mix(in srgb, var(--color-state-warning) 12%, transparent)',
                padding: '3px 8px', borderRadius: '6px',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              }}>
                CUSTOM
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: muted, fontSize: '20px', padding: '2px 6px',
              fontFamily: 'inherit',
            }}
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1.5rem' }}>
          {loading ? (
            <div style={{
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              fontSize: '13px', color: muted, textAlign: 'center', padding: '2rem 0',
            }}>
              Loading…
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {PROMPT_FILE_ORDER.map(filename => (
                <div key={filename}>
                  <label style={{
                    display: 'block',
                    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    fontSize: '10px', letterSpacing: '1px',
                    textTransform: 'uppercase', color: muted, marginBottom: '6px',
                  }}>
                    {PROMPT_FILE_LABELS[filename] ?? filename}
                    <span style={{ color: 'color-mix(in srgb, var(--color-text-muted) 50%, transparent)', marginLeft: '6px' }}>{filename}</span>
                  </label>
                  <textarea
                    value={files[filename] ?? ''}
                    onChange={e => onFileChange(filename, e.target.value)}
                    rows={6}
                    style={{
                      width: '100%',
                      background: 'var(--color-bg-surface)',
                      border: `1px solid ${borderColor}`,
                      borderRadius: '6px',
                      color: body,
                      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                      fontSize: '12px', lineHeight: 1.6,
                      padding: '10px 12px', resize: 'vertical', outline: 'none',
                      boxSizing: 'border-box', transition: 'border-color 0.15s',
                    }}
                    onFocus={e => (e.currentTarget.style.borderColor = 'var(--color-border-focus)')}
                    onBlur={e => (e.currentTarget.style.borderColor = borderColor)}
                  />
                </div>
              ))}
            </div>
          )}
          {error && (
            <p style={{
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              fontSize: '12px', color: 'var(--color-state-danger)', marginTop: '1rem',
            }}>
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '1rem 1.5rem', borderTop: `1px solid ${borderColor}`,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0,
        }}>
          <button
            onClick={saving ? undefined : onReset}
            disabled={saving || !isCustom}
            style={{
              padding: '8px 18px', borderRadius: '20px',
              border: `1px solid ${borderColor}`,
              background: 'transparent', cursor: (saving || !isCustom) ? 'not-allowed' : 'pointer',
              color: muted, fontSize: '13px',
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              opacity: (saving || !isCustom) ? 0.5 : 1,
            }}
          >
            Reset to Default
          </button>
          <button
            onClick={saving ? undefined : onSave}
            disabled={saving}
            style={{
              padding: '8px 20px', borderRadius: '20px',
              border: `1px solid var(--color-action-primary)`,
              background: 'var(--color-action-primary)', cursor: saving ? 'not-allowed' : 'pointer',
              color: 'var(--color-text-on-action)', fontSize: '13px',
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              fontWeight: 500, opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════
// Main component
// ══════════════════════════════════════════════
export default function AnalysisView() {
  const { isAuthenticated } = useAuth();
  const { t, i18n } = useTranslation();
  const dateLocale = getDateLocale(i18n.language);
  const isMobile = useMobile();

  const formatDaysLabel    = (n: number) => t('analysis.statsLabels.daysCount', { count: n });
  const formatEntriesLabel = (n: number) => t('analysis.statsLabels.entriesCount', { count: n });
  const formatWordsLabel   = (n: number) => t('analysis.statsLabels.wordsCount', { value: n.toLocaleString() });

  // ── State ──
  const [echoes, setEchoes]       = useState<ReflectionResult[]>([]);
  const [traits, setTraits]       = useState<ReflectionResult[]>([]);
  const [patterns, setPatterns]   = useState<ReflectionResult[]>([]);
  const [loading, setLoading]     = useState({ echoes: false, traits: false, patterns: false });
  const [streaming, setStreaming] = useState({ echoes: '', traits: '', patterns: '' });
  const [errors, setErrors]       = useState({ echoes: '', traits: '', patterns: '' });
  const [stats, setStats]         = useState({ totalDays: 0, totalWords: 0, totalEntries: 0 });
  const [savedReports, setSavedReports] = useState<AnalysisReport[]>([]);
  const [taskStatus, setTaskStatus] = useState('');

  // View modes
  const [viewMode, setViewMode] = useState<'dashboard' | 'report' | 'blog'>('dashboard');
  const [currentPaper, setCurrentPaper] = useState(0);
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);

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
    if (isAuthenticated) {
      try {
        const db = await getAnalysisReports(MAX_SAVED_REPORTS);
        const individual: AnalysisReport[] = db.map((r: any) => ({
          id: r.id,
          echoes:   (r.report_data?.echoes   || []) as ReflectionResult[],
          traits:   (r.report_data?.traits   || []) as ReflectionResult[],
          patterns: (r.report_data?.patterns || []) as ReflectionResult[],
          timestamp: new Date(r.created_at).getTime(),
          stats: r.report_data?.stats || { days: 0, entries: 0, words: 0 },
        }));
        const byDay = new Map<string, AnalysisReport>();
        for (const r of individual) {
          const day = new Date(r.timestamp).toDateString();
          const existing = byDay.get(day);
          if (!existing) {
            byDay.set(day, { ...r });
          } else {
            if (r.timestamp > existing.timestamp) existing.timestamp = r.timestamp;
            if (existing.echoes.length === 0 && r.echoes.length > 0) existing.echoes = r.echoes;
            if (existing.traits.length === 0 && r.traits.length > 0) existing.traits = r.traits;
            if (existing.patterns.length === 0 && r.patterns.length > 0) existing.patterns = r.patterns;
          }
        }
        const grouped = [...byDay.values()].sort((a, b) => b.timestamp - a.timestamp);
        setSavedReports(grouped);
        const latestEchoes   = individual.find(r => r.echoes.length > 0);
        const latestTraits   = individual.find(r => r.traits.length > 0);
        const latestPatterns = individual.find(r => r.patterns.length > 0);
        if (latestEchoes)   setEchoes(latestEchoes.echoes);
        if (latestTraits)   setTraits(latestTraits.traits);
        if (latestPatterns) setPatterns(latestPatterns.patterns);
        try {
          const latest = await getLatestReflections();
          if (latest.results.length > 0) {
            const latestEchoesFromTask = latest.results.filter(r => r.section === 'echoes');
            const latestTraitsFromTask = latest.results.filter(r => r.section === 'traits');
            const latestPatternsFromTask = latest.results.filter(r => r.section === 'patterns');
            if (latestEchoesFromTask.length) setEchoes(latestEchoesFromTask);
            if (latestTraitsFromTask.length) setTraits(latestTraitsFromTask);
            if (latestPatternsFromTask.length) setPatterns(latestPatternsFromTask);
            const taskTime = latest.task?.completed_at || latest.task?.updated_at || new Date().toISOString();
            const taskReport: AnalysisReport = {
              id: Number(new Date(taskTime)) || Date.now(),
              echoes: latestEchoesFromTask,
              traits: latestTraitsFromTask,
              patterns: latestPatternsFromTask,
              timestamp: new Date(taskTime).getTime() || Date.now(),
              stats: { days: 0, entries: 0, words: 0 },
            };
            setSavedReports(prev => {
              const withoutDuplicate = prev.filter(r => r.timestamp !== taskReport.timestamp);
              return [taskReport, ...withoutDuplicate].slice(0, MAX_SAVED_REPORTS);
            });
          }
        } catch (e) {
          console.warn('[Reflections] latest task load failed:', e);
        }
      } catch (e) { console.error(e); }
    } else {
      const saved = localStorage.getItem(STORAGE_KEYS.ANALYSIS_REPORTS);
      if (saved) {
        try {
          const r: AnalysisReport[] = JSON.parse(saved);
          setSavedReports(r);
          const le = r.find(x => x.echoes.length > 0);
          const lt = r.find(x => x.traits.length > 0);
          const lp = r.find(x => x.patterns.length > 0);
          if (le) setEchoes(le.echoes);
          if (lt) setTraits(lt.traits);
          if (lp) setPatterns(lp.patterns);
        } catch (e) { console.error(e); }
      }
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai';
        const agg = await fetchSessionsAggregate(tz);
        setStats({ totalDays: agg.stats.total_days, totalWords: agg.stats.total_words, totalEntries: agg.stats.total_entries });
      } catch (e) { console.error(e); }
    };
    loadStats();
    reloadSavedReports();
  }, [isAuthenticated, reloadSavedReports]);

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
    if (section && ['echoes', 'traits', 'patterns'].includes(section)) {
      setStreaming(p => ({ ...p, [section]: statusText }));
    }
  }, []);

  // ── Per-section analysis with streaming ──
  const handleAnalyzeSection = async (section: SectionKey) => {
    if (!isAuthenticated) {
      setErrors(p => ({ ...p, [section]: 'Please log in to use reflections.' }));
      return;
    }
    setErrors(p => ({ ...p, [section]: '' }));
    setStreaming(p => ({ ...p, [section]: '' }));
    setLoading(p => ({ ...p, [section]: true }));

    const setter = section === 'echoes' ? setEchoes : section === 'traits' ? setTraits : setPatterns;

    try {
      const bySection = await runReflectionsTask({
        sections: [section],
        onEvent: handleTaskEvent,
      });
      const results = bySection[section];
      setter(results);
      setStreaming(p => ({ ...p, [section]: '' }));
      if (results.length === 0) {
        setErrors(p => ({ ...p, [section]: 'No results — the Reflections task completed without section output.' }));
        return;
      }
      if (isAuthenticated) {
        try {
          await saveAnalysisReport(`reflections_${section}`, {
            [section]: results,
            stats: { days: stats.totalDays, entries: stats.totalEntries, words: stats.totalWords },
          });
          await reloadSavedReports();
        } catch (e) { console.warn('[Reflections] save failed:', e); }
      } else {
        const entry: AnalysisReport = {
          id: Date.now(),
          echoes:   section === 'echoes'   ? results : [],
          traits:   section === 'traits'   ? results : [],
          patterns: section === 'patterns' ? results : [],
          timestamp: Date.now(),
          stats: { days: stats.totalDays, entries: stats.totalEntries, words: stats.totalWords },
        };
        const updated = [entry, ...savedReports].slice(0, MAX_SAVED_REPORTS);
        localStorage.setItem(STORAGE_KEYS.ANALYSIS_REPORTS, JSON.stringify(updated));
        setSavedReports(updated);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrors(p => ({ ...p, [section]: msg }));
      setStreaming(p => ({ ...p, [section]: '' }));
    } finally {
      setLoading(p => ({ ...p, [section]: false }));
    }
  };

  // ── One-click analyze all ──
  const handleAnalyzeAll = async () => {
    if (!isAuthenticated) {
      setErrors({ echoes: 'Please log in to use reflections.', traits: '', patterns: '' });
      return;
    }
    setErrors({ echoes: '', traits: '', patterns: '' });
    setStreaming({ echoes: '', traits: '', patterns: '' });
    setLoading({ echoes: true, traits: true, patterns: true });

    let er: ReflectionResult[] = [], tr: ReflectionResult[] = [], pr: ReflectionResult[] = [];
    try {
      const bySection = await runReflectionsTask({ onEvent: handleTaskEvent });
      er = bySection.echoes;
      tr = bySection.traits;
      pr = bySection.patterns;
      setEchoes(er);
      setTraits(tr);
      setPatterns(pr);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrors({ echoes: msg, traits: '', patterns: '' });
    } finally {
      setLoading({ echoes: false, traits: false, patterns: false });
      setStreaming({ echoes: '', traits: '', patterns: '' });
    }

    if (er.length || tr.length || pr.length) {
      const reportData = {
        echoes: er, traits: tr, patterns: pr,
        stats: { days: stats.totalDays, entries: stats.totalEntries, words: stats.totalWords },
      };
      if (isAuthenticated) {
        try {
          await saveAnalysisReport('full_analysis', reportData);
          await reloadSavedReports();
        } catch (e) { console.error(e); }
      } else {
        const entry: AnalysisReport = { id: Date.now(), ...reportData, timestamp: Date.now() };
        const updated = [entry, ...savedReports].slice(0, MAX_SAVED_REPORTS);
        localStorage.setItem(STORAGE_KEYS.ANALYSIS_REPORTS, JSON.stringify(updated));
        setSavedReports(updated);
      }
      setViewMode('report');
      setCurrentPaper(0);
    }
  };

  const anyLoading = loading.echoes || loading.traits || loading.patterns;
  const hasAnyData = echoes.length > 0 || traits.length > 0 || patterns.length > 0;
  const anyError = errors.echoes || errors.traits || errors.patterns;

  // ──────────────────────────────────────────────
  // BLOG VIEW — full-page editorial layout for a single Past Reflection
  // ──────────────────────────────────────────────
  if (viewMode === 'blog' && selectedReport) {
    return (
      <ReflectionBlogPage
        report={selectedReport}
        onBack={() => setViewMode('dashboard')}
        isMobile={isMobile}
        t={t}
        dateLocale={dateLocale}
        formatDaysLabel={formatDaysLabel}
        formatEntriesLabel={formatEntriesLabel}
        formatWordsLabel={formatWordsLabel}
      />
    );
  }

  // ──────────────────────────────────────────────
  // REPORT VIEW — PaperStack 3D stacked-paper display
  // ──────────────────────────────────────────────
  if (viewMode === 'report' && hasAnyData) {
    return (
      <div style={{
        width: '100%', height: '100%',
        background: 'linear-gradient(180deg, var(--color-bg-app) 0%, var(--color-bg-paper) 100%)',
        fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif",
        position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column',
      }}>
        {/* Back button */}
        <button
          onClick={() => setViewMode('dashboard')}
          style={{
            position: 'absolute', top: isMobile ? '1rem' : '2rem', left: isMobile ? '1rem' : '2rem',
            padding: isMobile ? '10px 16px' : '12px 24px', borderRadius: '24px',
            background: 'var(--color-bg-surface-solid)', border: '1px solid var(--color-border-paper)',
            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
            fontSize: '14px', fontWeight: 500, color: 'var(--color-text-body)',
            transition: 'all 0.3s', boxShadow: '0 4px 16px var(--color-shadow-soft)', zIndex: 30,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 8px 24px var(--color-shadow-medium)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 16px var(--color-shadow-soft)';
          }}
        >
          <span>←</span>
          <span>{t('analysis.backButton')}</span>
        </button>

        <DecorativeInkSpots />

        <div style={{
          flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: isMobile ? '1rem' : '2rem', marginTop: isMobile ? '0' : '-60px',
        }}>
          <PaperStack
            echoes={echoes} traits={traits} patterns={patterns}
            currentPaper={currentPaper} onPaperChange={setCurrentPaper}
            isMobile={isMobile} t={t}
            loading={loading} streaming={streaming}
            isAuthenticated={isAuthenticated}
            onAnalyzeSection={handleAnalyzeSection}
            onConfigClick={handleOpenConfig}
          />
        </div>
      </div>
    );
  }

  // ──────────────────────────────────────────────
  // DASHBOARD VIEW — warm vintage journal design
  // ──────────────────────────────────────────────
  return (
    <div style={{
      width: '100%', height: '100%', overflowY: 'auto',
      background: 'linear-gradient(180deg, var(--color-bg-app) 0%, var(--color-bg-paper) 100%)',
      fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif",
      padding: isMobile ? '1.75rem 1rem 2.5rem' : '3rem 2rem',
      position: 'relative',
    }}>
      <DecorativeInkSpots />

      <div style={{ maxWidth: '1100px', margin: '0 auto', position: 'relative' }}>
        {/* Header */}
        <div style={{ marginBottom: '3rem', textAlign: 'center', position: 'relative' }}>
          <h1 style={{
            fontSize: isMobile ? '32px' : '48px', fontWeight: 400,
            color: 'var(--color-text-primary)', marginBottom: '0.75rem',
            fontFamily: 'Georgia, serif', fontStyle: 'italic', letterSpacing: '-0.5px',
            textShadow: '2px 2px 0px var(--color-shadow-soft)',
          }}>
            {t('analysis.title')}
          </h1>
          <div style={{
            width: '80px', height: '3px',
            background: 'linear-gradient(90deg, transparent, var(--color-text-muted), transparent)',
            margin: '0 auto 1rem', opacity: 0.4,
          }} />
          <p style={{
            fontSize: isMobile ? '14px' : '15px', color: 'var(--color-text-secondary)',
            lineHeight: 1.8, fontStyle: 'italic', maxWidth: '500px', margin: '0 auto',
          }}>
            {t('analysis.subtitle')}
          </p>
        </div>

        {/* Stats */}
        <div style={{
          display: 'flex', justifyContent: 'center',
          gap: isMobile ? '1rem' : '2rem', marginBottom: '3rem', flexWrap: 'wrap',
        }}>
          <VintageStatLabel label={t('analysis.stats.days')} value={stats.totalDays} />
          <VintageStatLabel label={t('analysis.stats.entries')} value={stats.totalEntries} />
          <VintageStatLabel label={t('analysis.stats.words')} value={stats.totalWords.toLocaleString()} />
        </div>

        {/* Past reports */}
        {savedReports.length > 0 && (
          <div style={{ marginBottom: '3rem' }}>
            <h2 style={{
              fontSize: '20px', fontWeight: 500, color: 'var(--color-text-body)',
              marginBottom: '1.5rem', textAlign: 'center',
              fontFamily: 'Georgia, serif', fontStyle: 'italic',
            }}>
              {t('analysis.pastReflections')}
            </h2>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: isMobile ? '1rem' : '1.5rem', marginBottom: '2rem',
            }}>
              {savedReports.slice(0, 3).map((report, idx) => (
                <div
                  key={report.id}
                  onClick={() => {
                    setSelectedReport(report);
                    setViewMode('blog');
                  }}
                  style={{
                    padding: '1.5rem', background: 'var(--color-bg-surface)',
                    borderRadius: '16px',
                    border: '1px solid color-mix(in srgb, var(--color-border-paper) 60%, transparent)',
                    cursor: 'pointer', transition: 'all 0.3s', backdropFilter: 'blur(10px)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = '0 8px 24px color-mix(in srgb, var(--color-border-paper) 60%, transparent)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                    <div style={{ fontSize: '13px', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                      {new Date(report.timestamp).toLocaleDateString(dateLocale, {
                        month: 'short', day: 'numeric', year: 'numeric',
                      })}
                    </div>
                    {idx === 0 && (
                      <div style={{
                        fontSize: '10px', fontWeight: 600, color: 'var(--color-state-success)',
                        background: 'color-mix(in srgb, var(--color-state-success) 10%, transparent)',
                        padding: '4px 8px', borderRadius: '8px', textTransform: 'uppercase', letterSpacing: '0.5px',
                        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                      }}>
                        {t('analysis.report.latest')}
                      </div>
                    )}
                  </div>
                  <div style={{
                    display: 'flex', gap: '1rem', fontSize: '12px',
                    color: 'var(--color-text-secondary)', marginBottom: '0.75rem',
                    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                  }}>
                    <div>{formatDaysLabel(report.stats?.days || 0)}</div>
                    <div>·</div>
                    <div>{formatEntriesLabel(report.stats?.entries || 0)}</div>
                    <div>·</div>
                    <div>{formatWordsLabel(report.stats?.words || 0)}</div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {report.echoes?.length > 0 && (
                      <span style={{
                        fontSize: '11px', padding: '4px 10px',
                        background: 'color-mix(in srgb, var(--color-border-paper) 30%, transparent)',
                        borderRadius: '12px', color: 'var(--color-text-body)',
                        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                      }}>
                        {t('analysis.reportCounts.echoes', { count: report.echoes.length })}
                      </span>
                    )}
                    {report.traits?.length > 0 && (
                      <span style={{
                        fontSize: '11px', padding: '4px 10px',
                        background: 'color-mix(in srgb, var(--color-border-paper) 30%, transparent)',
                        borderRadius: '12px', color: 'var(--color-text-body)',
                        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                      }}>
                        {t('analysis.reportCounts.traits', { count: report.traits.length })}
                      </span>
                    )}
                    {report.patterns?.length > 0 && (
                      <span style={{
                        fontSize: '11px', padding: '4px 10px',
                        background: 'color-mix(in srgb, var(--color-border-paper) 30%, transparent)',
                        borderRadius: '12px', color: 'var(--color-text-body)',
                        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                      }}>
                        {t('analysis.reportCounts.patterns', { count: report.patterns.length })}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* One-click analyze button */}
        <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
          <button
            onClick={handleAnalyzeAll}
            disabled={anyLoading}
            style={{
              padding: '16px 48px',
              background: anyLoading ? 'color-mix(in srgb, var(--color-text-muted) 50%, transparent)' : 'transparent',
              color: anyLoading ? 'var(--color-text-muted)' : 'var(--color-text-body)',
              border: '2px solid',
              borderColor: anyLoading ? 'var(--color-border-neutral)' : 'var(--color-text-muted)',
              borderRadius: '30px',
              cursor: anyLoading ? 'not-allowed' : 'pointer',
              fontSize: '15px', fontWeight: 500, fontFamily: 'Georgia, serif',
              transition: 'all 0.3s', letterSpacing: '1px', textTransform: 'uppercase',
            }}
            onMouseEnter={e => {
              if (!anyLoading) {
                e.currentTarget.style.background = 'color-mix(in srgb, var(--color-border-paper) 36%, transparent)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 20px color-mix(in srgb, var(--color-border-paper) 60%, transparent)';
              }
            }}
            onMouseLeave={e => {
              if (!anyLoading) {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }
            }}
          >
            {anyLoading ? t('analysis.actions.generating') : t('analysis.actions.generate')}
          </button>
          {taskStatus && (
            <div style={{
              marginTop: '0.75rem',
              fontSize: '12px',
              color: 'var(--color-text-muted)',
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              fontStyle: 'italic',
            }}>
              Backend task: {taskStatus}
            </div>
          )}
        </div>

        {/* Per-section controls + streaming */}
        <SectionControlsRow
          loading={loading} streaming={streaming} errors={errors}
          isAuthenticated={isAuthenticated} isMobile={isMobile}
          onAnalyze={handleAnalyzeSection}
          onConfig={handleOpenConfig}
          t={t}
        />

        {/* Global error display */}
        {anyError && !anyLoading && (
          <div style={{
            padding: '1rem',
            background: 'color-mix(in srgb, var(--color-state-danger) 8%, transparent)',
            border: '1px solid color-mix(in srgb, var(--color-state-danger) 25%, transparent)',
            borderRadius: '8px', color: 'var(--color-state-danger)',
            marginBottom: '2rem', textAlign: 'center',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            fontSize: '13px',
          }}>
            {[errors.echoes, errors.traits, errors.patterns].filter(Boolean).join(' | ')}
          </div>
        )}

        {/* Empty state */}
        {!hasAnyData && !anyLoading && (
          <div style={{ textAlign: 'center', padding: '5rem 2rem', position: 'relative' }}>
            <div style={{
              position: 'absolute', top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '300px', height: '300px', borderRadius: '50%',
              background: 'radial-gradient(circle, color-mix(in srgb, var(--color-border-paper) 18%, transparent) 0%, transparent 70%)',
              filter: 'blur(40px)', pointerEvents: 'none',
            }} />
            <div style={{ fontSize: '72px', marginBottom: '1.5rem', opacity: 0.3, filter: 'grayscale(100%)' }}>📖</div>
            <p style={{
              fontSize: '20px', marginBottom: '0.75rem', color: 'var(--color-text-body)',
              fontFamily: 'Georgia, serif', fontStyle: 'italic', fontWeight: 300,
            }}>
              {t('analysis.empty.title')}
            </p>
            <p style={{
              fontSize: '14px', color: 'var(--color-text-muted)',
              maxWidth: '400px', margin: '0 auto', lineHeight: 1.7,
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            }}>
              {t('analysis.empty.description')}
            </p>
          </div>
        )}

        {/* View report button if data exists */}
        {hasAnyData && viewMode === 'dashboard' && (
          <div style={{ textAlign: 'center', marginTop: '2rem' }}>
            <button
              onClick={() => { setViewMode('report'); setCurrentPaper(0); }}
              style={{
                padding: '12px 32px', borderRadius: '24px',
                background: 'var(--color-bg-surface-solid)',
                border: '1px solid var(--color-border-paper)',
                color: 'var(--color-text-body)', fontSize: '14px', cursor: 'pointer',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                fontWeight: 500, transition: 'all 0.3s',
                boxShadow: '0 4px 12px var(--color-shadow-soft)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 20px var(--color-shadow-medium)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 12px var(--color-shadow-soft)';
              }}
            >
              View Reflections →
            </button>
          </div>
        )}
      </div>

      {/* Section config modal */}
      <SectionConfigModal
        open={configModal.open}
        section={configModal.section}
        displayName={configModal.displayName}
        files={configModal.files}
        loading={configModal.loading}
        saving={configModal.saving}
        isCustom={!!(configModal.config?.usedCustomConfig)}
        error={configModal.error}
        onClose={() => setConfigModal(p => ({ ...p, open: false }))}
        onSave={handleSaveConfig}
        onReset={handleResetConfig}
        onFileChange={(filename, content) =>
          setConfigModal(p => ({ ...p, files: { ...p.files, [filename]: content } }))
        }
      />
    </div>
  );
}

// ──────────────────────────────────────────────
// Per-section controls row (dashboard area)
// ──────────────────────────────────────────────
function SectionControlsRow({
  loading, streaming, errors, isAuthenticated, isMobile, onAnalyze, onConfig, t,
}: {
  loading: Record<string, boolean>;
  streaming: Record<string, string>;
  errors: Record<string, string>;
  isAuthenticated: boolean;
  isMobile: boolean;
  onAnalyze: (s: SectionKey) => void;
  onConfig: (s: SectionKey) => void;
  t: (k: string, opts?: any) => string;
}) {
  const sections: { key: SectionKey; icon: string; titleKey: string }[] = [
    { key: 'echoes',   icon: '🔄', titleKey: 'analysis.papers.echoes.title' },
    { key: 'traits',   icon: '⭐', titleKey: 'analysis.papers.traits.title' },
    { key: 'patterns', icon: '🌀', titleKey: 'analysis.papers.patterns.title' },
  ];

  const anyActive = sections.some(s => loading[s.key] || streaming[s.key] || errors[s.key]);
  if (!isAuthenticated && !anyActive) return null;

  return (
    <div style={{
      display: 'flex', gap: isMobile ? '0.75rem' : '1rem',
      flexWrap: 'wrap', justifyContent: 'center',
      marginBottom: '2rem',
    }}>
      {sections.map(({ key, icon, titleKey }) => (
        <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: isMobile ? '100%' : '200px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
            <span style={{ fontSize: '14px' }}>{icon}</span>
            <span style={{
              fontSize: '12px', color: 'var(--color-text-muted)', fontWeight: 500,
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              textTransform: 'uppercase', letterSpacing: '0.8px',
            }}>
              {t(titleKey)}
            </span>
            {isAuthenticated && (
              <button
                onClick={() => onConfig(key)}
                title="Configure analysis prompts"
                style={{
                  background: 'none', border: '1px solid var(--color-border-paper)',
                  borderRadius: '50%', width: '22px', height: '22px', cursor: 'pointer',
                  color: 'var(--color-text-muted)', fontSize: '11px',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.2s', padding: 0,
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--color-action-primary)';
                  e.currentTarget.style.color = 'var(--color-action-primary)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--color-border-paper)';
                  e.currentTarget.style.color = 'var(--color-text-muted)';
                }}
              >
                ⚙
              </button>
            )}
            {isAuthenticated && (
              <button
                onClick={() => !loading[key] && onAnalyze(key)}
                disabled={loading[key]}
                style={{
                  padding: '3px 12px', borderRadius: '12px',
                  border: '1px solid var(--color-border-paper)',
                  background: 'transparent', cursor: loading[key] ? 'not-allowed' : 'pointer',
                  color: 'var(--color-text-body)', fontSize: '11px',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                  opacity: loading[key] ? 0.6 : 1, transition: 'all 0.2s',
                }}
                onMouseEnter={e => {
                  if (!loading[key]) e.currentTarget.style.background = 'color-mix(in srgb, var(--color-border-paper) 30%, transparent)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                {loading[key] ? '◌' : 'Analyze'}
              </button>
            )}
          </div>

          {/* Streaming progress */}
          {loading[key] && streaming[key] && (
            <div style={{
              background: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-paper)',
              borderRadius: '8px', padding: '10px 12px',
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              fontSize: '11px', color: 'var(--color-text-muted)',
              lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              maxHeight: '120px', overflowY: 'auto',
            }}>
              {streaming[key].slice(-800)}<span style={{ opacity: 0.4 }}>▌</span>
            </div>
          )}
          {loading[key] && !streaming[key] && (
            <div style={{
              fontSize: '11px', color: 'var(--color-text-muted)', textAlign: 'center',
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              fontStyle: 'italic',
            }}>
              Waiting for backend Reflections task…
            </div>
          )}
          {errors[key] && !loading[key] && (
            <div style={{
              fontSize: '11px', color: 'var(--color-state-danger)', textAlign: 'center',
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            }}>
              {errors[key]}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ──────────────────────────────────────────────
// Decorative ink spot background
// ──────────────────────────────────────────────
function DecorativeInkSpots() {
  return (
    <>
      <div style={{
        position: 'absolute', top: '10%', right: '5%',
        width: '120px', height: '120px', borderRadius: '50%',
        background: 'radial-gradient(circle, color-mix(in srgb, var(--color-border-paper) 24%, transparent) 0%, rgba(139,115,85,0) 70%)',
        filter: 'blur(20px)', pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: '20%', left: '8%',
        width: '150px', height: '150px', borderRadius: '50%',
        background: 'radial-gradient(circle, color-mix(in srgb, var(--color-border-paper) 18%, transparent) 0%, rgba(160,130,109,0) 70%)',
        filter: 'blur(25px)', pointerEvents: 'none',
      }} />
    </>
  );
}

// ──────────────────────────────────────────────
// PaperStack — 3D stacked paper animation
// ──────────────────────────────────────────────
function PaperStack({
  echoes, traits, patterns, currentPaper, onPaperChange, isMobile, t,
  loading, streaming, isAuthenticated, onAnalyzeSection, onConfigClick,
}: {
  echoes: ReflectionResult[];
  traits: ReflectionResult[];
  patterns: ReflectionResult[];
  currentPaper: number;
  onPaperChange: (i: number) => void;
  isMobile: boolean;
  t: (k: string, opts?: any) => string;
  loading: Record<string, boolean>;
  streaming: Record<string, string>;
  isAuthenticated: boolean;
  onAnalyzeSection: (s: SectionKey) => void;
  onConfigClick: (s: SectionKey) => void;
}) {
  const contentMaxHeight = isMobile ? '280px' : '420px';
  const papers: { title: string; subtitle: string; icon: string; section: SectionKey; content: React.ReactNode }[] = [];

  if (echoes.length > 0) {
    papers.push({
      title: t('analysis.papers.echoes.title'),
      subtitle: t('analysis.papers.echoes.subtitle'),
      icon: '🔄', section: 'echoes',
      content: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: contentMaxHeight, overflowY: 'auto', paddingRight: '0.5rem' }}>
          {echoes.map((r, i) => <ResultCard key={i} result={r} kind="echo" />)}
        </div>
      ),
    });
  }
  if (traits.length > 0) {
    papers.push({
      title: t('analysis.papers.traits.title'),
      subtitle: t('analysis.papers.traits.subtitle'),
      icon: '⭐', section: 'traits',
      content: (
        <div style={{
          display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: '1rem', maxHeight: contentMaxHeight, overflowY: 'auto', paddingRight: '0.5rem',
        }}>
          {traits.map((r, i) => <ResultCard key={i} result={r} kind="trait" />)}
        </div>
      ),
    });
  }
  if (patterns.length > 0) {
    papers.push({
      title: t('analysis.papers.patterns.title'),
      subtitle: t('analysis.papers.patterns.subtitle'),
      icon: '🌀', section: 'patterns',
      content: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: contentMaxHeight, overflowY: 'auto', paddingRight: '0.5rem' }}>
          {patterns.map((r, i) => <ResultCard key={i} result={r} kind="pattern" />)}
        </div>
      ),
    });
  }

  const totalPapers = papers.length;
  if (totalPapers === 0) return null;

  return (
    <div style={{
      position: 'relative', width: '100%',
      maxWidth: isMobile ? '520px' : '1100px',
      height: isMobile ? '520px' : '650px',
      margin: '0 auto', perspective: '1200px',
    }}>
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        marginLeft: isMobile ? '0' : '-30px',
        width: '100%', maxWidth: isMobile ? '520px' : '900px',
        height: isMobile ? '480px' : '600px',
      }}>
        {papers.map((paper, idx) => {
          const isActive = idx === currentPaper;
          const isBehind = idx < currentPaper;
          const offset = isActive ? 0 : isBehind ? -10 : 10;
          const zIndex = isActive ? 10 : isBehind ? totalPapers - idx : idx;
          const sectionLoading = loading[paper.section];
          const sectionStreaming = streaming[paper.section];

          return (
            <div
              key={idx}
              style={{
                position: 'absolute', top: 0, left: '50%',
                transform: `translateX(-50%) translateY(${offset}px) rotate(${isActive ? 0 : isBehind ? -0.5 : 0.5}deg)`,
                width: '100%', height: '100%',
                transition: 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)',
                opacity: isActive ? 1 : 0.4,
                pointerEvents: isActive ? 'auto' : 'none',
                zIndex,
              }}
            >
              <div style={{
                width: '100%', height: '100%',
                background: 'linear-gradient(135deg, var(--color-bg-surface-solid) 0%, var(--color-bg-paper) 100%)',
                borderRadius: '3px',
                boxShadow: `
                  0 1px 3px var(--color-shadow-soft),
                  0 4px 12px var(--color-shadow-soft),
                  0 10px 30px var(--color-shadow-medium),
                  inset 0 1px 0 var(--color-bg-surface-solid)
                `,
                border: '1px solid var(--color-border-paper)',
                padding: isMobile ? '1.5rem' : '2.5rem 3rem',
                overflow: 'hidden', position: 'relative',
              }}>
                {/* Paper texture overlay */}
                <div style={{
                  position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                  backgroundImage: `
                    repeating-linear-gradient(0deg, color-mix(in srgb, var(--color-border-paper) 4%, transparent) 0px, transparent 2px),
                    repeating-linear-gradient(90deg, color-mix(in srgb, var(--color-border-paper) 3%, transparent) 0px, transparent 2px)
                  `,
                  pointerEvents: 'none', opacity: 0.7,
                }} />
                {/* Watercolor wash */}
                <div style={{
                  position: 'absolute', top: '10%', right: '5%',
                  width: '150px', height: '150px', borderRadius: '50%',
                  background: 'radial-gradient(circle, color-mix(in srgb, var(--color-border-paper) 18%, transparent) 0%, transparent 70%)',
                  filter: 'blur(30px)', pointerEvents: 'none',
                }} />

                <div style={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', flexDirection: 'column' }}>
                  {/* Paper header */}
                  <div style={{
                    marginBottom: '1.5rem',
                    borderBottom: '2px solid color-mix(in srgb, var(--color-border-paper) 45%, transparent)',
                    paddingBottom: '1rem', flexShrink: 0,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ fontSize: '28px' }}>{paper.icon}</span>
                        <div>
                          <h2 style={{
                            fontSize: isMobile ? '20px' : '26px', fontWeight: 400,
                            color: 'var(--color-text-primary)', fontFamily: 'Georgia, serif',
                            fontStyle: 'italic', letterSpacing: '-0.3px', margin: 0, lineHeight: 1.2,
                          }}>
                            {paper.title}
                          </h2>
                          <div style={{
                            fontSize: '11px', color: 'var(--color-text-muted)',
                            textTransform: 'uppercase', letterSpacing: '1.5px',
                            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                            fontWeight: 500,
                          }}>
                            {paper.subtitle}
                          </div>
                        </div>
                      </div>
                      {/* Per-paper controls */}
                      {isAuthenticated && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                          <button
                            onClick={() => onConfigClick(paper.section)}
                            title="Configure prompts"
                            style={{
                              background: 'none', border: '1px solid var(--color-border-paper)',
                              borderRadius: '50%', width: '26px', height: '26px', cursor: 'pointer',
                              color: 'var(--color-text-muted)', fontSize: '12px',
                              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                              transition: 'all 0.2s', padding: 0,
                            }}
                            onMouseEnter={e => {
                              e.currentTarget.style.borderColor = 'var(--color-action-primary)';
                              e.currentTarget.style.color = 'var(--color-action-primary)';
                            }}
                            onMouseLeave={e => {
                              e.currentTarget.style.borderColor = 'var(--color-border-paper)';
                              e.currentTarget.style.color = 'var(--color-text-muted)';
                            }}
                          >
                            ⚙
                          </button>
                          <button
                            onClick={() => !sectionLoading && onAnalyzeSection(paper.section)}
                            disabled={sectionLoading}
                            style={{
                              padding: '4px 14px', borderRadius: '14px',
                              border: '1px solid var(--color-border-paper)',
                              background: 'transparent', cursor: sectionLoading ? 'not-allowed' : 'pointer',
                              color: 'var(--color-text-body)', fontSize: '11px',
                              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                              opacity: sectionLoading ? 0.6 : 1, transition: 'all 0.2s',
                            }}
                            onMouseEnter={e => {
                              if (!sectionLoading) e.currentTarget.style.background = 'color-mix(in srgb, var(--color-border-paper) 30%, transparent)';
                            }}
                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                          >
                            {sectionLoading ? '◌ Analyzing…' : 'Re-analyze'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Streaming / loading state */}
                  {sectionLoading && (
                    <div style={{ marginBottom: '1rem', flexShrink: 0 }}>
                      {sectionStreaming ? (
                        <div style={{
                          background: 'var(--color-bg-surface)', borderRadius: '8px',
                          padding: '10px 12px', border: '1px solid var(--color-border-paper)',
                          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                          fontSize: '11px', color: 'var(--color-text-muted)',
                          maxHeight: '100px', overflowY: 'auto',
                          whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.5,
                        }}>
                          {sectionStreaming.slice(-600)}<span style={{ opacity: 0.4 }}>▌</span>
                        </div>
                      ) : (
                        <p style={{
                          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                          fontSize: '12px', color: 'var(--color-text-muted)', fontStyle: 'italic',
                        }}>
                          Reading memory workspace and analysing…
                        </p>
                      )}
                    </div>
                  )}

                  {/* Paper body */}
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    {paper.content}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Navigation */}
      {totalPapers > 1 && (
        <>
          <NavArrow
            direction="left" disabled={currentPaper === 0}
            onClick={() => onPaperChange(Math.max(0, currentPaper - 1))}
            isMobile={isMobile}
          />
          <NavArrow
            direction="right" disabled={currentPaper === totalPapers - 1}
            onClick={() => onPaperChange(Math.min(totalPapers - 1, currentPaper + 1))}
            isMobile={isMobile}
          />
          {/* Dot indicators */}
          <div style={{
            position: 'absolute', bottom: isMobile ? '-24px' : '-40px',
            left: '50%', transform: 'translateX(-50%)',
            display: 'flex', gap: '10px', zIndex: 20,
          }}>
            {papers.map((_, idx) => (
              <button
                key={idx}
                onClick={() => onPaperChange(idx)}
                style={{
                  width: '12px', height: '12px', borderRadius: '50%',
                  background: idx === currentPaper
                    ? 'var(--color-text-muted)'
                    : 'color-mix(in srgb, var(--color-text-muted) 40%, transparent)',
                  border: 'none', cursor: 'pointer', transition: 'all 0.3s', padding: 0,
                }}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────
// Navigation arrow for PaperStack
// ──────────────────────────────────────────────
function NavArrow({ direction, disabled, onClick, isMobile }: {
  direction: 'left' | 'right'; disabled: boolean; onClick: () => void; isMobile: boolean;
}) {
  const isLeft = direction === 'left';
  const size = isMobile ? '40px' : '48px';
  const arrowStyle: React.CSSProperties = {
    position: 'absolute',
    left: isLeft ? (isMobile ? '12px' : 'calc(50% - 540px)') : 'auto',
    right: isLeft ? 'auto' : (isMobile ? '12px' : 'calc(50% - 540px)'),
    top: '50%', transform: 'translateY(-50%)',
    width: size, height: size, borderRadius: '50%',
    background: disabled
      ? 'color-mix(in srgb, var(--color-border-paper) 30%, transparent)'
      : 'var(--color-bg-surface-solid)',
    border: '2px solid color-mix(in srgb, var(--color-border-paper) 60%, transparent)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: isMobile ? '18px' : '20px',
    color: disabled ? 'var(--color-border-neutral)' : 'var(--color-text-body)',
    transition: 'all 0.3s',
    boxShadow: disabled ? 'none' : '0 4px 12px color-mix(in srgb, var(--color-border-paper) 45%, transparent)',
    zIndex: 20,
  };
  return (
    <button style={arrowStyle} onClick={onClick} disabled={disabled}
      onMouseEnter={e => {
        if (!disabled) {
          e.currentTarget.style.transform = 'translateY(-50%) scale(1.1)';
          e.currentTarget.style.boxShadow = '0 6px 20px color-mix(in srgb, var(--color-shadow-medium) 60%, transparent)';
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(-50%) scale(1)';
        e.currentTarget.style.boxShadow = disabled ? 'none' : '0 4px 12px color-mix(in srgb, var(--color-border-paper) 45%, transparent)';
      }}
    >
      {isLeft ? '←' : '→'}
    </button>
  );
}

// ──────────────────────────────────────────────
// Result card (echoes / traits / patterns unified)
// ──────────────────────────────────────────────
function ResultCard({ result, kind }: { result: ReflectionResult; kind: 'echo' | 'trait' | 'pattern' }) {
  const confidenceFill = result.confidence === 'high' ? 5 : result.confidence === 'low' ? 1 : 3;
  return (
    <div style={{
      background: 'var(--color-bg-surface)',
      padding: '1.5rem', borderRadius: '14px',
      border: '1px solid color-mix(in srgb, var(--color-border-paper) 60%, transparent)',
      transition: 'all 0.3s', position: 'relative', backdropFilter: 'blur(8px)',
    }}>
      <h3 style={{
        fontSize: '17px', fontWeight: 500, color: 'var(--color-text-primary)',
        marginBottom: '0.75rem', fontFamily: 'Georgia, serif', fontStyle: 'italic',
        margin: '0 0 0.75rem',
      }}>
        {result.title}
      </h3>
      <p style={{
        color: 'var(--color-text-body)', lineHeight: 1.75,
        marginBottom: kind === 'echo' ? '0.5rem' : '1rem', fontSize: '13px',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        margin: `0 0 ${kind === 'echo' ? '0.5rem' : '1rem'}`,
      }}>
        {kind === 'trait' ? result.evidence : result.description}
      </p>

      {/* Confidence bar for traits */}
      {kind === 'trait' && (
        <>
          <div style={{ display: 'flex', gap: '6px', marginBottom: '0.75rem' }}>
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} style={{
                flex: 1, height: '5px', borderRadius: '3px',
                background: i <= confidenceFill
                  ? 'linear-gradient(90deg, var(--color-text-muted), color-mix(in srgb, var(--color-text-muted) 50%, transparent))'
                  : 'color-mix(in srgb, var(--color-border-paper) 30%, transparent)',
                opacity: i <= confidenceFill ? 1 : 0.4,
              }} />
            ))}
          </div>
          <div style={{
            fontSize: '11px', color: 'var(--color-text-muted)',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          }}>
            {result.evidence}
          </div>
        </>
      )}

      {/* Confidence / frequency pill for patterns */}
      {kind === 'pattern' && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
          fontSize: '11px', color: 'var(--color-text-muted)',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          background: 'color-mix(in srgb, var(--color-border-paper) 24%, transparent)',
          padding: '4px 12px', borderRadius: '16px',
          border: '1px solid color-mix(in srgb, var(--color-border-paper) 45%, transparent)',
        }}>
          <span style={{ fontWeight: 600 }}>Confidence:</span>
          <span style={{ fontStyle: 'italic' }}>{result.confidence}</span>
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────
// Vintage stat label
// ──────────────────────────────────────────────
function VintageStatLabel({ label, value }: { label: string; value: number | string }) {
  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
      <div style={{
        fontSize: '36px', fontWeight: 300, color: 'var(--color-text-body)',
        fontFamily: 'Georgia, serif', lineHeight: 1,
      }}>
        {value}
      </div>
      <div style={{
        fontSize: '11px', color: 'var(--color-text-muted)', fontWeight: 500,
        textTransform: 'uppercase', letterSpacing: '1.5px',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        borderTop: '1px solid color-mix(in srgb, var(--color-text-muted) 50%, transparent)',
        paddingTop: '0.5rem',
      }}>
        {label}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════
// ReflectionBlogPage — full-page editorial blog layout
// Nav right: section tabs (switch which section is shown)
// Main area: single scrollable page — hero + item list + detail below on click
// Detail view (image2 layout) renders BELOW the list, no mode switching
// Player bar: sticky at viewport bottom when an item is selected
// Color spec: docs/prd/color_system/reflection-blog.md
// Feature PRD: docs/prd/reflection-blog.md
// ══════════════════════════════════════════════

// ══════════════════════════════════════════════
// ReflectionBlogPage — left-right split layout
// Left panel: section nav (Recurring Themes / Traits / Patterns)
// Right panel: title list for active section; click title → detail below
// Detail area (image2): description left | related notes right | player bar
// Color spec: docs/prd/color_system/reflection-blog.md
// Feature PRD: docs/prd/reflection-blog.md
// ══════════════════════════════════════════════

// ══════════════════════════════════════════════
// ReflectionBlogPage — left/right split layout (PRD v3)
// Left  : Hero (cover art + date + stats)
// Right : Section tabs (top) + title-only list (below)
// Below : Detail area (description | related notes + player bar)
// Color spec : docs/prd/color_system/reflection-blog.md
// Feature PRD: docs/prd/reflection-blog.md
// ══════════════════════════════════════════════

// ══════════════════════════════════════════════
// ReflectionBlogPage — fixed-height flex layout (PRD v4)
// Layout: flex column, overflow hidden, no outer page scroll
// Left  : Hero (cover art + date + stats), overflow-y auto
// Right : Section tabs (flex-shrink:0) + title list (flex:1, overflow-y:auto)
// Detail: fixed height below split, internal scroll per column
// Player: flex-shrink:0 at very bottom, floats above content
// Refs  : docs/prd/reflection-blog.md, docs/prd/color_system/reflection-blog.md
// ══════════════════════════════════════════════
function ReflectionBlogPage({
  report, onBack, isMobile, t, dateLocale,
  formatDaysLabel, formatEntriesLabel, formatWordsLabel,
}: {
  report: AnalysisReport;
  onBack: () => void;
  isMobile: boolean;
  t: (k: string, opts?: any) => string;
  dateLocale: string;
  formatDaysLabel: (n: number) => string;
  formatEntriesLabel: (n: number) => string;
  formatWordsLabel: (n: number) => string;
}) {
  const date = new Date(report.timestamp);

  const blogSections: { key: SectionKey; icon: string; items: ReflectionResult[]; kind: 'echo' | 'trait' | 'pattern' }[] = [
    ...(report.echoes.length > 0 ? [{ key: 'echoes' as SectionKey, icon: '🔄', items: report.echoes, kind: 'echo' as const }] : []),
    ...(report.traits.length > 0 ? [{ key: 'traits' as SectionKey, icon: '⭐', items: report.traits, kind: 'trait' as const }] : []),
    ...(report.patterns.length > 0 ? [{ key: 'patterns' as SectionKey, icon: '🌀', items: report.patterns, kind: 'pattern' as const }] : []),
  ];

  const firstKey = (blogSections[0]?.key ?? 'echoes') as SectionKey;
  const [activeSection, setActiveSection] = useState<SectionKey>(firstKey);
  const [selectedItemIdx, setSelectedItemIdx] = useState<number | null>(null);

  const activeSectionObj = blogSections.find(s => s.key === activeSection) ?? blogSections[0];
  const activeItems = activeSectionObj?.items ?? [];
  const selectedItem = selectedItemIdx !== null ? (activeItems[selectedItemIdx] ?? null) : null;

  const monthStr    = date.toLocaleDateString('en', { month: 'short' }).toUpperCase();
  const dayStr      = date.getDate();
  const yearStr     = date.getFullYear();
  const fullDateStr = date.toLocaleDateString(dateLocale, {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  const handleSectionChange = (key: SectionKey) => { setActiveSection(key); setSelectedItemIdx(null); };
  const goToPrev = () => { if (selectedItemIdx !== null && selectedItemIdx > 0) setSelectedItemIdx(selectedItemIdx - 1); };
  const goToNext = () => { if (selectedItemIdx !== null && selectedItemIdx < activeItems.length - 1) setSelectedItemIdx(selectedItemIdx + 1); };
  const cfill = (c?: string) => c === 'high' ? 5 : c === 'low' ? 1 : 3;

  const coverArt = (size: number) => (
    <div style={{
      flexShrink: 0, width: size, height: size,
      background: 'linear-gradient(145deg, var(--color-bg-surface-solid) 0%, color-mix(in srgb, var(--color-border-paper) 40%, var(--color-bg-surface-solid)) 100%)',
      border: '1px solid var(--color-border-paper)', borderRadius: '8px',
      boxShadow: '0 4px 16px var(--color-shadow-medium), 0 1px 4px var(--color-shadow-soft)',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: size > 80 ? '4px' : '2px', position: 'relative', overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', inset: 0, backgroundImage: 'repeating-linear-gradient(0deg, color-mix(in srgb, var(--color-border-paper) 5%, transparent) 0px, transparent 2px)', pointerEvents: 'none' }} />
      <span style={{ fontSize: size > 80 ? '11px' : '8px', letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--color-text-muted)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', fontWeight: 600, position: 'relative' }}>{monthStr}</span>
      <span style={{ fontSize: size > 80 ? '44px' : '24px', fontWeight: 300, fontFamily: 'Georgia, serif', lineHeight: 1, color: 'var(--color-text-primary)', position: 'relative' }}>{dayStr}</span>
      <span style={{ fontSize: size > 80 ? '11px' : '8px', color: 'var(--color-text-muted)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', position: 'relative' }}>{yearStr}</span>
    </div>
  );

  return (
    <div style={{
      width: '100%', height: '100%',
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
      background: 'var(--color-bg-app)',
      fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif",
    }}>

      {/* ── Sticky Nav ── */}
      <div style={{
        flexShrink: 0, zIndex: 100,
        background: 'color-mix(in srgb, var(--color-bg-surface-solid) 92%, transparent)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--color-border-paper)',
        padding: isMobile ? '0.5rem 1rem' : '0.5rem 1.5rem',
        display: 'flex', alignItems: 'center',
      }}>
        <button
          onClick={onBack}
          style={{ background: 'none', border: '1px solid var(--color-border-paper)', borderRadius: '20px', padding: '4px 14px', cursor: 'pointer', color: 'var(--color-text-body)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', transition: 'all 0.2s', whiteSpace: 'nowrap' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'none'; }}
        >
          <span>←</span>
          <span>{t('analysis.pastReflections')}</span>
        </button>
      </div>

      {/* ── Main content area (flex:1, no outer scroll) ── */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>

        {/* ── Left / Right split (flex:1, shrinks when detail opens) ── */}
        <div style={{
          flex: 1, overflow: 'hidden', minHeight: 0,
          display: 'flex', flexDirection: isMobile ? 'column' : 'row',
        }}>

          {/* LEFT: Hero */}
          <div style={{
            flexShrink: 0,
            width: isMobile ? '100%' : '240px',
            overflowY: isMobile ? 'hidden' : 'auto',
            borderRight: isMobile ? 'none' : '1px solid var(--color-border-paper)',
            borderBottom: isMobile ? '1px solid var(--color-border-paper)' : 'none',
            background: 'linear-gradient(180deg, var(--color-bg-surface-solid) 0%, var(--color-bg-app) 100%)',
            padding: isMobile ? '0.875rem 1.25rem' : '2rem 1.75rem',
            display: 'flex',
            flexDirection: isMobile ? 'row' : 'column',
            alignItems: isMobile ? 'center' : 'flex-start',
            gap: isMobile ? '1rem' : '0',
          }}>
            {coverArt(isMobile ? 56 : 120)}

            <div style={{ marginTop: isMobile ? 0 : '1.25rem', minWidth: 0 }}>
              <div style={{ fontSize: '9px', letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--color-text-muted)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', fontWeight: 600, marginBottom: isMobile ? '0.25rem' : '0.4rem' }}>
                Reflection
              </div>
              <div style={{ fontSize: isMobile ? '14px' : '18px', fontFamily: 'Georgia, serif', fontStyle: 'italic', color: 'var(--color-text-primary)', lineHeight: 1.3, marginBottom: isMobile ? '0.375rem' : '0.875rem' }}>
                {fullDateStr}
              </div>
              <div style={{
                display: 'flex', flexDirection: isMobile ? 'row' : 'column',
                gap: isMobile ? '0.375rem' : '0.2rem',
                flexWrap: isMobile ? 'wrap' : undefined,
                fontSize: '11px', color: 'var(--color-text-secondary)',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              }}>
                <span>{formatDaysLabel(report.stats?.days || 0)}</span>
                {isMobile && <span style={{ color: 'var(--color-border-paper)' }}>·</span>}
                <span>{formatEntriesLabel(report.stats?.entries || 0)}</span>
                {isMobile && <span style={{ color: 'var(--color-border-paper)' }}>·</span>}
                <span>{formatWordsLabel(report.stats?.words || 0)}</span>
              </div>
            </div>
          </div>

          {/* RIGHT: Section tabs + title list */}
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>

            {/* Section tabs */}
            <div style={{ display: 'flex', borderBottom: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface)', flexShrink: 0 }}>
              {blogSections.map(s => {
                const isActive = s.key === activeSection;
                return (
                  <button
                    key={s.key}
                    onClick={() => handleSectionChange(s.key)}
                    style={{
                      flex: isMobile ? '1' : 'none',
                      padding: isMobile ? '0.5rem 0.375rem' : '0.75rem 1.25rem',
                      background: 'transparent',
                      borderTop: 'none', borderLeft: 'none', borderRight: 'none',
                      borderBottom: `2px solid ${isActive ? 'var(--color-text-muted)' : 'transparent'}`,
                      cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: isMobile ? 'center' : 'flex-start',
                      gap: '5px',
                      transition: 'all 0.2s',
                      color: isActive ? 'var(--color-text-body)' : 'var(--color-text-muted)',
                    }}
                    onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    <span style={{ fontSize: isMobile ? '14px' : '13px' }}>{s.icon}</span>
                    {!isMobile && <span style={{ fontSize: '12px', fontWeight: isActive ? 600 : 400, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', whiteSpace: 'nowrap' }}>{t(`analysis.papers.${s.key}.title`)}</span>}
                    <span style={{ fontSize: '10px', fontWeight: 600, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', background: isActive ? 'color-mix(in srgb, var(--color-border-paper) 50%, transparent)' : 'color-mix(in srgb, var(--color-border-paper) 28%, transparent)', padding: '1px 5px', borderRadius: '10px' }}>{s.items.length}</span>
                  </button>
                );
              })}
            </div>

            {/* Title-only list — independent scroll */}
            <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, padding: isMobile ? '0.25rem 1.25rem' : '0.25rem 1.75rem' }}>
              {activeItems.map((item, i) => {
                const isSelected = selectedItemIdx === i;
                const num = String(i + 1).padStart(2, '0');
                return (
                  <button
                    key={i}
                    onClick={() => setSelectedItemIdx(isSelected ? null : i)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.875rem',
                      padding: '0.8rem 0',
                      width: '100%', textAlign: 'left',
                      background: isSelected ? 'color-mix(in srgb, var(--color-border-paper) 7%, transparent)' : 'transparent',
                      borderTop: 'none', borderLeft: 'none', borderRight: 'none',
                      borderBottom: `1px solid color-mix(in srgb, var(--color-border-paper) 35%, transparent)`,
                      cursor: 'pointer', transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'color-mix(in srgb, var(--color-border-paper) 6%, transparent)'; }}
                    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <span style={{ flexShrink: 0, fontSize: '11px', fontWeight: 600, letterSpacing: '1px', color: 'var(--color-text-muted)', fontFamily: 'Georgia, serif', minWidth: '20px', opacity: isSelected ? 1 : 0.5 }}>{num}</span>
                    <span style={{ flex: 1, minWidth: 0, fontSize: isMobile ? '14px' : '15px', fontFamily: 'Georgia, serif', fontStyle: 'italic', color: isSelected ? 'var(--color-text-primary)' : 'var(--color-text-body)', fontWeight: isSelected ? 500 : 400, lineHeight: 1.4, transition: 'color 0.2s' }}>
                      {item.title}
                    </span>
                    <span style={{ flexShrink: 0, fontSize: '13px', color: 'var(--color-text-muted)', display: 'inline-block', transition: 'transform 0.25s', transform: isSelected ? 'rotate(90deg)' : 'rotate(0deg)' }}>→</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Detail area: fixed height, below split ── */}
        {selectedItem !== null && (
          <div style={{
            flexShrink: 0,
            height: isMobile ? '52vh' : '45vh',
            overflow: 'hidden',
            display: 'flex', flexDirection: 'column',
            borderTop: '2px solid var(--color-border-paper)',
            background: 'var(--color-bg-surface)',
          }}>
            {/* Detail header */}
            <div style={{ flexShrink: 0, padding: isMobile ? '0.625rem 1.25rem' : '0.875rem 2rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid color-mix(in srgb, var(--color-border-paper) 50%, transparent)' }}>
              <div style={{ fontSize: '10px', letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--color-text-muted)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>{activeSectionObj?.icon}</span>
                <span>{t(`analysis.papers.${activeSection}.title`)}</span>
                <span style={{ color: 'var(--color-border-paper)' }}>·</span>
                <span>{selectedItemIdx! + 1} / {activeItems.length}</span>
              </div>
              <button onClick={() => setSelectedItemIdx(null)} style={{ background: 'none', border: '1px solid var(--color-border-paper)', borderRadius: '50%', width: '22px', height: '22px', cursor: 'pointer', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', padding: 0, transition: 'all 0.2s', flexShrink: 0 }} onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--color-text-muted)'; }} onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--color-border-paper)'; }}>×</button>
            </div>

            {/* Two-column content with independent scroll */}
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: isMobile ? 'column' : 'row', minHeight: 0 }}>
              {/* Left: description */}
              <div style={{ flex: isMobile ? 'none' : '6', overflowY: 'auto', minHeight: 0, padding: isMobile ? '1rem 1.25rem' : '1.25rem 2rem', borderRight: isMobile ? 'none' : '1px solid var(--color-border-paper)', borderBottom: isMobile ? '1px solid var(--color-border-paper)' : 'none', height: isMobile ? '50%' : '100%' }}>
                <h2 style={{ fontSize: isMobile ? '17px' : '22px', fontWeight: 400, fontFamily: 'Georgia, serif', fontStyle: 'italic', color: 'var(--color-text-primary)', margin: '0 0 0.875rem', lineHeight: 1.3 }}>{selectedItem.title}</h2>
                <p style={{ fontSize: '13px', lineHeight: 1.85, color: 'var(--color-text-body)', margin: '0 0 1rem', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
                  {activeSectionObj?.kind === 'trait' ? selectedItem.evidence : selectedItem.description}
                </p>
                {activeSectionObj?.kind === 'trait' && (() => {
                  const fill = cfill(selectedItem.confidence);
                  return (
                    <>
                      <div style={{ display: 'flex', gap: '4px', marginBottom: '0.5rem' }}>
                        {[1, 2, 3, 4, 5].map(n => (<div key={n} style={{ flex: 1, height: '3px', borderRadius: '2px', background: n <= fill ? 'var(--color-text-muted)' : 'color-mix(in srgb, var(--color-border-paper) 40%, transparent)', opacity: n <= fill ? 0.8 : 0.4 }} />))}
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', lineHeight: 1.7, margin: 0, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>{selectedItem.evidence}</p>
                    </>
                  );
                })()}
                {(activeSectionObj?.kind === 'echo' || activeSectionObj?.kind === 'pattern') && selectedItem.confidence && (
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontSize: '11px', color: 'var(--color-text-muted)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', background: 'color-mix(in srgb, var(--color-border-paper) 20%, transparent)', padding: '3px 10px', borderRadius: '12px', border: '1px solid color-mix(in srgb, var(--color-border-paper) 40%, transparent)' }}>
                    <span style={{ fontWeight: 600 }}>Confidence</span><span>·</span><span style={{ fontStyle: 'italic' }}>{selectedItem.confidence}</span>
                  </div>
                )}
              </div>

              {/* Right: related notes */}
              <div style={{ flex: isMobile ? 'none' : '4', overflowY: 'auto', minHeight: 0, padding: isMobile ? '1rem 1.25rem' : '1.25rem 1.75rem', height: isMobile ? '50%' : '100%' }}>
                <div style={{ fontSize: '10px', letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--color-text-muted)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', fontWeight: 600, marginBottom: '0.875rem' }}>Related Notes</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '0.625rem' }}>
                  {[75, 60, 68].map((w, idx) => (
                    <div key={idx} style={{ padding: '0.75rem', background: 'var(--color-bg-surface-solid)', borderRadius: '8px', border: '1px solid color-mix(in srgb, var(--color-border-paper) 50%, transparent)', opacity: 0.45 }}>
                      <div style={{ height: '8px', borderRadius: '4px', background: 'color-mix(in srgb, var(--color-border-paper) 60%, transparent)', marginBottom: '0.35rem', width: `${w}%` }} />
                      <div style={{ height: '6px', borderRadius: '3px', background: 'color-mix(in srgb, var(--color-border-paper) 40%, transparent)', width: `${w - 15}%` }} />
                    </div>
                  ))}
                </div>
                <div style={{ color: 'var(--color-text-muted)', fontSize: '11px', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', fontStyle: 'italic' }}>Related notes coming soon</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Player Bar: floating at bottom (outside scroll area) ── */}
      {selectedItem !== null && (
        <div style={{
          flexShrink: 0,
          background: 'var(--color-bg-surface-solid)',
          borderTop: '1px solid var(--color-border-paper)',
          padding: isMobile ? '0.5rem 1rem' : '0.625rem 1.75rem',
          display: 'flex', alignItems: 'center', gap: isMobile ? '0.5rem' : '1.25rem',
          boxShadow: '0 -3px 12px var(--color-shadow-soft)',
          zIndex: 10,
        }}>
          {/* Track info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: 0 }}>
            <div style={{ width: '32px', height: '32px', flexShrink: 0, background: 'linear-gradient(135deg, var(--color-bg-surface-solid) 0%, color-mix(in srgb, var(--color-border-paper) 40%, var(--color-bg-surface-solid)) 100%)', border: '1px solid var(--color-border-paper)', borderRadius: '5px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>
              {activeSectionObj?.icon}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-text-body)', fontFamily: 'Georgia, serif', fontStyle: 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selectedItem.title}</div>
              <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>{t(`analysis.papers.${activeSection}.title`)}</div>
            </div>
          </div>
          {/* Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', flexShrink: 0 }}>
            <button onClick={goToPrev} disabled={selectedItemIdx === 0} style={{ background: 'none', border: '1px solid var(--color-border-paper)', borderRadius: '50%', width: '28px', height: '28px', cursor: selectedItemIdx === 0 ? 'not-allowed' : 'pointer', color: selectedItemIdx === 0 ? 'var(--color-border-paper)' : 'var(--color-text-body)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', transition: 'all 0.2s', padding: 0 }}>◀</button>
            <div style={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
              {activeItems.map((_, n) => (
                <button key={n} onClick={() => setSelectedItemIdx(n)} style={{ width: n === selectedItemIdx ? '14px' : '5px', height: '5px', borderRadius: '3px', background: n === selectedItemIdx ? 'var(--color-text-muted)' : 'color-mix(in srgb, var(--color-text-muted) 35%, transparent)', border: 'none', cursor: 'pointer', padding: 0, transition: 'all 0.3s', flexShrink: 0 }} />
              ))}
            </div>
            <button onClick={goToNext} disabled={selectedItemIdx === activeItems.length - 1} style={{ background: 'none', border: '1px solid var(--color-border-paper)', borderRadius: '50%', width: '28px', height: '28px', cursor: selectedItemIdx === activeItems.length - 1 ? 'not-allowed' : 'pointer', color: selectedItemIdx === activeItems.length - 1 ? 'var(--color-border-paper)' : 'var(--color-text-body)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', transition: 'all 0.2s', padding: 0 }}>▶</button>
          </div>
          {/* Counter */}
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', letterSpacing: '0.5px', flexShrink: 0 }}>
            {selectedItemIdx! + 1} / {activeItems.length}
          </span>
        </div>
      )}
    </div>
  );
}
