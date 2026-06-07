/**
 * [Input] voiceApi: analyzeEchoes, analyzeTraits, analyzePatterns, saveAnalysisReport,
 *         getAnalysisReports, listSessions, fetchSessionsAggregate, ReflectionResult,
 *         getReflectionsSectionConfig, saveReflectionsSectionConfig, resetReflectionsSectionConfig,
 *         ReflectionSectionConfig
 * [Output] Reflections page — warm paper / vintage journal design (CSS design tokens)
 * [Pos] components/AnalysisView — full-page Reflections (Analysis) view
 * [Sync] 2026-06-07: Restore warm paper theme (develop branch aesthetic: Georgia font,
 *         var(--color-bg-app) palette, PaperStack 3D stacked-paper animation).
 *         Types migrated to unified ReflectionResult[]; confidence replaces strength/frequency.
 *         Per-section streaming analyze + ⚙ SectionConfigModal retained.
 *         One-click 「Generate Reflections」 button in dashboard header retained.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  analyzeEchoes,
  analyzeTraits,
  analyzePatterns,
  saveAnalysisReport,
  getAnalysisReports,
  listSessions,
  fetchSessionsAggregate,
  getReflectionsSectionConfig,
  saveReflectionsSectionConfig,
  resetReflectionsSectionConfig,
  type UserSession,
  type ReflectionResult,
  type ReflectionSectionConfig,
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
type SectionKey = 'echoes' | 'traits' | 'patterns';

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
  const [sessions, setSessions]   = useState<UserSession[]>([]);
  const [echoes, setEchoes]       = useState<ReflectionResult[]>([]);
  const [traits, setTraits]       = useState<ReflectionResult[]>([]);
  const [patterns, setPatterns]   = useState<ReflectionResult[]>([]);
  const [loading, setLoading]     = useState({ echoes: false, traits: false, patterns: false });
  const [streaming, setStreaming] = useState({ echoes: '', traits: '', patterns: '' });
  const [errors, setErrors]       = useState({ echoes: '', traits: '', patterns: '' });
  const [stats, setStats]         = useState({ totalDays: 0, totalWords: 0, totalEntries: 0 });
  const [savedReports, setSavedReports] = useState<AnalysisReport[]>([]);

  // View modes
  const [viewMode, setViewMode] = useState<'dashboard' | 'report'>('dashboard');
  const [currentPaper, setCurrentPaper] = useState(0);

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
  const loadSessions = useCallback(async () => {
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai';
      const data = await listSessions(tz);
      setSessions([...data].sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ));
    } catch (e) { console.error('Failed to load sessions:', e); }
  }, []);

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
    loadSessions();
  }, [isAuthenticated, loadSessions, reloadSavedReports]);

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
    const fn = section === 'echoes' ? analyzeEchoes : section === 'traits' ? analyzeTraits : analyzePatterns;

    try {
      const results = await fn((delta) => {
        setStreaming(p => ({ ...p, [section]: p[section] + delta }));
      });
      setter(results);
      setStreaming(p => ({ ...p, [section]: '' }));
      if (results.length === 0) {
        setErrors(p => ({ ...p, [section]: 'No results — the agent response may not have contained valid JSON.' }));
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
    let er: ReflectionResult[] = [], tr: ReflectionResult[] = [], pr: ReflectionResult[] = [];

    const run = async (
      fn: () => Promise<ReflectionResult[]>,
      key: SectionKey extends 'echo' ? never : 'echoes' | 'traits' | 'patterns',
      cb: (r: ReflectionResult[]) => void,
    ): Promise<ReflectionResult[]> => {
      setLoading(p => ({ ...p, [key]: true }));
      try {
        const result = await fn();
        cb(result);
        return result;
      } catch (e) {
        setErrors(p => ({ ...p, [key]: e instanceof Error ? e.message : String(e) }));
        return [];
      } finally {
        setLoading(p => ({ ...p, [key]: false }));
      }
    };

    [er, tr, pr] = await Promise.all([
      run(() => analyzeEchoes(), 'echoes', r => setEchoes(r)),
      run(() => analyzeTraits(), 'traits',  r => setTraits(r)),
      run(() => analyzePatterns(), 'patterns', r => setPatterns(r)),
    ]);

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
            loading={loading} streaming={streaming} errors={errors}
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
                    if (report.echoes.length) setEchoes(report.echoes);
                    if (report.traits.length) setTraits(report.traits);
                    if (report.patterns.length) setPatterns(report.patterns);
                    setViewMode('report'); setCurrentPaper(0);
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
              Reading memory workspace…
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
  loading, streaming, errors, isAuthenticated, onAnalyzeSection, onConfigClick,
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
  errors: Record<string, string>;
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
    right: isLeft ? 'auto' : (isMobile ? '12px' : 'auto'),
    marginLeft: (!isMobile && !isLeft) ? '530px' : undefined,
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
