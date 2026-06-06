/**
 * [Input] voiceApi: analyzeEchoes, analyzeTraits, analyzePatterns, saveAnalysisReport,
 *         getAnalysisReports, listSessions, fetchSessionsAggregate, ReflectionResult,
 *         getReflectionsSectionConfig, saveReflectionsSectionConfig, resetReflectionsSectionConfig,
 *         ReflectionSectionConfig
 * [Output] Reflections page — Ciridae authentic dark-noir design
 * [Pos] components/AnalysisView — full-page Reflections (Analysis) view
 * [Sync] 2026-06-05: Interaction redesign — dashboard shows analysis cards as primary.
 * [Sync] 2026-06-06: Migrate analysis to per-section flow: create thread →
 *         POST /api/reflections/memory-init → POST /api/claude-agent SSE
 *         (tool_choice=auto so agent reads WORKFLOW.md) → parse JSON.
 *         Per-section independent analyze buttons + streaming progress display.
 *         ReflectionResult unified type; related notes driven by related_session_ids.
 * [Sync] 2026-06-06: Add SectionConfigModal + ⚙ gear icon per section; users can view
 *         and edit the 5 memory workspace prompt files from the UI (GET/PUT/DELETE
 *         /api/reflections/config/{section}). CUSTOM badge when user config is active.
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
// Ciridae design tokens
// ──────────────────────────────────────────────
const C = {
  void: '#0b0b0b',
  ash: '#858585',
  fog: '#cecece',
  pure: '#ffffff',
  ember: '#cc6437',
  glass: 'rgba(255,255,255,0.04)',
  glassBorder: 'rgba(255,255,255,0.08)',
  glassBorderHover: 'rgba(255,255,255,0.18)',
  fontCond: "'Barlow Condensed', 'Oswald', ui-sans-serif, sans-serif",
  fontMono: "'Roboto Mono', ui-monospace, monospace",
} as const;

const MAX_SAVED_REPORTS = 10;

// Ordered list of the 5 prompt files in memory workspace.
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

type SectionKind = 'echo' | 'trait' | 'pattern';

interface AnalysisItem {
  kind: SectionKind;
  data: ReflectionResult;
}

interface AnalysisReport {
  id: number;
  echoes: ReflectionResult[];
  traits: ReflectionResult[];
  patterns: ReflectionResult[];
  timestamp: number;
  stats: { days: number; entries: number; words: number };
}

/** Confidence dot color */
function confidenceColor(confidence: string): string {
  if (confidence === 'high') return '#6ee7b7';   // green
  if (confidence === 'low') return '#858585';     // grey
  return '#f59e0b';                               // amber for medium
}

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────

function itemTitle(item: AnalysisItem): string {
  return item.data.title;
}

function itemDesc(item: AnalysisItem): string {
  return item.data.description;
}

/**
 * Keywords from the item for label-based fallback matching.
 * Primary related notes come from related_session_ids; this is the fallback.
 */
function itemKeywords(item: AnalysisItem): string[] {
  const raw = `${item.data.title} ${item.data.description} ${item.data.evidence}`;
  return raw.toLowerCase().split(/[\s,，。.!?、]+/).filter(w => w.length > 1);
}

/** Score a session's relevance by matching against agent-provided session IDs first,
 *  then by label keyword overlap as a fallback. */
function sessionRelevance(
  session: UserSession,
  relatedIds: string[],
  keywords: string[],
): number {
  // Exact ID match from agent analysis — strongest signal.
  if (relatedIds.includes(session.id)) return 100;
  // Fallback: keyword match on labels.
  if (!session.labels.length) return 0;
  const labelText = session.labels.join(' ').toLowerCase();
  return keywords.filter(kw => labelText.includes(kw)).length;
}

// ──────────────────────────────────────────────
// Primitive UI components
// ──────────────────────────────────────────────

function FontInject() {
  return (
    <style>{`@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400&family=Roboto+Mono:wght@400&display=swap');`}</style>
  );
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontFamily: C.fontCond, fontWeight: 400,
      fontSize: '11px', letterSpacing: '0.10em',
      textTransform: 'uppercase', color: C.ash,
    }}>
      {children}
    </div>
  );
}

function NumBadge({ n }: { n: number }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      borderRadius: '1440px', border: `1px solid ${C.glassBorder}`,
      padding: '2px 9px',
      fontFamily: C.fontMono, fontSize: '10px', color: C.ash, letterSpacing: '-0.01em',
      userSelect: 'none', flexShrink: 0,
    }}>
      {String(n).padStart(2, '0')}
    </div>
  );
}

function StarMark({ size = 48, glow = false }: { size?: number; glow?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" aria-hidden
      style={glow ? { filter: 'drop-shadow(0 0 10px rgba(255,255,255,0.3))' } : undefined}>
      <path d="M50 10L53 47L90 50L53 53L50 90L47 53L10 50L47 47Z" fill={C.pure} />
      <path d="M75 18L76.5 25L84 26L76.5 27L75 34L73.5 27L66 26L73.5 25Z" fill={C.pure} opacity="0.6" />
      <path d="M25 66L26.2 71L32 72L26.2 73L25 78L23.8 73L18 72L23.8 71Z" fill={C.pure} opacity="0.4" />
      <path d="M65 8L65.8 11L69 11.5L65.8 12L65 15L64.2 12L61 11.5L64.2 11Z" fill={C.pure} opacity="0.35" />
    </svg>
  );
}

function PillBtn({
  children, onClick, disabled, accent, small,
}: {
  children: React.ReactNode; onClick?: () => void;
  disabled?: boolean; accent?: boolean; small?: boolean;
}) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        borderRadius: '1440px',
        border: `1px solid ${
          disabled ? C.ash + '44' :
          accent ? C.ember :
          hov ? C.pure + 'cc' : C.fog + '88'
        }`,
        background: hov && !disabled ? 'rgba(255,255,255,0.05)' : 'transparent',
        color: disabled ? C.ash : accent ? (hov ? C.pure : C.ember) : C.pure,
        fontFamily: C.fontCond, fontWeight: 400,
        fontSize: small ? '11px' : '13px',
        letterSpacing: '-0.01em', textTransform: 'uppercase',
        padding: small ? '4px 14px' : '7px 22px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'border-color 0.2s, background 0.2s, color 0.2s',
        display: 'inline-flex', alignItems: 'center', gap: '6px',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </button>
  );
}

function GlassCard({
  children, style, onClick, hoverable = true,
}: {
  children: React.ReactNode; style?: React.CSSProperties;
  onClick?: () => void; hoverable?: boolean;
}) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => hoverable && setHov(true)}
      onMouseLeave={() => hoverable && setHov(false)}
      style={{
        background: hov ? 'rgba(255,255,255,0.07)' : C.glass,
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: `1px solid ${hov ? C.glassBorderHover : C.glassBorder}`,
        borderRadius: '10px',
        transition: 'background 0.2s, border-color 0.2s',
        cursor: onClick ? 'pointer' : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

// ══════════════════════════════════════════════
// Section config modal — view / edit prompt files
// ══════════════════════════════════════════════
type SectionKey = 'echoes' | 'traits' | 'patterns';

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
  open, section, displayName, files, loading, saving, isCustom, error,
  onClose, onSave, onReset, onFileChange,
}: SectionConfigModalProps) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.88)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#111', border: `1px solid ${C.glassBorder}`,
          borderRadius: '4px', width: '100%', maxWidth: '680px',
          maxHeight: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '1.25rem 1.5rem', borderBottom: `1px solid ${C.glassBorder}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Eyebrow>CONFIGURE</Eyebrow>
            <span style={{
              fontFamily: C.fontCond, fontWeight: 400,
              fontSize: '18px', letterSpacing: '-0.02em', textTransform: 'uppercase', color: C.pure,
            }}>
              {displayName}
            </span>
            {isCustom && (
              <span style={{
                fontFamily: C.fontMono, fontSize: '9px', letterSpacing: '0.08em',
                textTransform: 'uppercase', color: C.ember,
                border: `1px solid ${C.ember}55`, padding: '2px 7px', borderRadius: '2px',
              }}>
                CUSTOM
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: C.ash, fontSize: '20px', padding: '2px 6px', fontFamily: C.fontMono,
            }}
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1.5rem' }}>
          {loading ? (
            <div style={{ fontFamily: C.fontMono, fontSize: '11px', color: C.ash, textAlign: 'center', padding: '2rem 0' }}>
              Loading…
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {PROMPT_FILE_ORDER.map(filename => (
                <div key={filename}>
                  <label style={{
                    display: 'block', fontFamily: C.fontMono, fontSize: '10px',
                    letterSpacing: '0.06em', textTransform: 'uppercase', color: C.ash, marginBottom: '6px',
                  }}>
                    {PROMPT_FILE_LABELS[filename] ?? filename}
                    <span style={{ color: C.ash + '66', marginLeft: '6px', fontWeight: 400 }}>{filename}</span>
                  </label>
                  <textarea
                    value={files[filename] ?? ''}
                    onChange={e => onFileChange(filename, e.target.value)}
                    rows={6}
                    style={{
                      width: '100%', background: C.glass, border: `1px solid ${C.glassBorder}`,
                      borderRadius: '2px', color: C.fog, fontFamily: C.fontMono, fontSize: '11px',
                      lineHeight: 1.6, padding: '10px 12px', resize: 'vertical', outline: 'none',
                      boxSizing: 'border-box', transition: 'border-color 0.15s',
                    }}
                    onFocus={e => (e.currentTarget.style.borderColor = C.glassBorderHover)}
                    onBlur={e => (e.currentTarget.style.borderColor = C.glassBorder)}
                  />
                </div>
              ))}
            </div>
          )}
          {error && (
            <p style={{ fontFamily: C.fontMono, fontSize: '10px', color: '#f87171', marginTop: '1rem' }}>
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '1rem 1.5rem', borderTop: `1px solid ${C.glassBorder}`,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0,
        }}>
          <PillBtn onClick={saving ? undefined : onReset} disabled={saving || !isCustom} small>
            Reset to Default
          </PillBtn>
          <PillBtn onClick={saving ? undefined : onSave} disabled={saving} accent small>
            {saving ? 'Saving…' : 'Save Changes'}
          </PillBtn>
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

  // ── State ──
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [echoes, setEchoes] = useState<ReflectionResult[]>([]);
  const [traits, setTraits] = useState<ReflectionResult[]>([]);
  const [patterns, setPatterns] = useState<ReflectionResult[]>([]);
  // Per-section loading and streaming text (shows partial agent output)
  const [loading, setLoading] = useState({ echoes: false, traits: false, patterns: false });
  const [streaming, setStreaming] = useState({ echoes: '', traits: '', patterns: '' });
  const [errors, setErrors] = useState({ echoes: '', traits: '', patterns: '' });
  const [stats, setStats] = useState({ totalDays: 0, totalWords: 0, totalEntries: 0 });
  const [savedReports, setSavedReports] = useState<AnalysisReport[]>([]);

  // Config modal state
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
    open: false,
    section: 'echoes',
    displayName: 'Recurring Themes',
    config: null,
    files: {},
    loading: false,
    saving: false,
    error: '',
  });

  // View: 'dashboard' = analysis list; 'notes' = related notes for clicked item
  const [selectedItem, setSelectedItem] = useState<AnalysisItem | null>(null);

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

  // Load (or reload) saved reports from DB / localStorage and group by day.
  const reloadSavedReports = useCallback(async () => {
    if (isAuthenticated) {
      try {
        const db = await getAnalysisReports(MAX_SAVED_REPORTS);

        // Each DB row may contain only one section (per-section saves).
        // Map to individual records first, then group by calendar day so
        // the history pills show one entry per analysis day with all
        // sections that were run that day.
        const individual = db.map((r: any) => ({
          id: r.id as number,
          echoes:   (r.report_data?.echoes   || []) as ReflectionResult[],
          traits:   (r.report_data?.traits   || []) as ReflectionResult[],
          patterns: (r.report_data?.patterns || []) as ReflectionResult[],
          timestamp: new Date(r.created_at).getTime(),
          stats: r.report_data?.stats || { days: 0, entries: 0, words: 0 },
        }));

        // Group by calendar day — DB is newest-first, so the first
        // non-empty section we encounter per day is the most recent.
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

        // Restore most recent result per section from individual rows.
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
          const latestEchoes   = r.find(x => x.echoes.length > 0);
          const latestTraits   = r.find(x => x.traits.length > 0);
          const latestPatterns = r.find(x => x.patterns.length > 0);
          if (latestEchoes)   setEchoes(latestEchoes.echoes);
          if (latestTraits)   setTraits(latestTraits.traits);
          if (latestPatterns) setPatterns(latestPatterns.patterns);
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

    loadStats(); reloadSavedReports(); loadSessions();
  }, [isAuthenticated, loadSessions, reloadSavedReports]);

  // ── Per-section analysis ──
  /**
   * Run analysis for one section.
   * Streams partial output (streaming state) while the agent is working.
   * On completion, saves the results and updates the section state.
   */
  const handleAnalyzeSection = async (section: 'echoes' | 'traits' | 'patterns') => {
    if (!isAuthenticated) {
      setErrors(p => ({ ...p, [section]: 'Please log in to use reflections.' }));
      return;
    }
    setErrors(p => ({ ...p, [section]: '' }));
    setStreaming(p => ({ ...p, [section]: '' }));
    setLoading(p => ({ ...p, [section]: true }));

    const setter = section === 'echoes' ? setEchoes : section === 'traits' ? setTraits : setPatterns;
    const analysisFn = section === 'echoes' ? analyzeEchoes : section === 'traits' ? analyzeTraits : analyzePatterns;

    try {
      const results = await analysisFn((delta) => {
        setStreaming(p => ({ ...p, [section]: p[section] + delta }));
      });

      setter(results);
      setStreaming(p => ({ ...p, [section]: '' }));

      if (results.length === 0) {
        setErrors(p => ({ ...p, [section]: 'No results — the agent response may not have contained valid JSON.' }));
        return;
      }

      // Persist section result.
      if (isAuthenticated) {
        try {
          await saveAnalysisReport(`reflections_${section}`, {
            [section]: results,
            stats: { days: stats.totalDays, entries: stats.totalEntries, words: stats.totalWords },
          });
          // Reload history pills from DB so the new report appears.
          await reloadSavedReports();
        } catch (e) { console.warn('[Reflections] save report failed:', e); }
      } else {
        const reportEntry: AnalysisReport = {
          id: Date.now(),
          echoes: section === 'echoes' ? results : [],
          traits: section === 'traits' ? results : [],
          patterns: section === 'patterns' ? results : [],
          timestamp: Date.now(),
          stats: { days: stats.totalDays, entries: stats.totalEntries, words: stats.totalWords },
        };
        const updated = [reportEntry, ...savedReports].slice(0, MAX_SAVED_REPORTS);
        localStorage.setItem(STORAGE_KEYS.ANALYSIS_REPORTS, JSON.stringify(updated));
        setSavedReports(updated);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrors(p => ({ ...p, [section]: msg }));
      console.error(`[Reflections] ${section} analysis failed:`, e);
      setStreaming(p => ({ ...p, [section]: '' }));
    } finally {
      setLoading(p => ({ ...p, [section]: false }));
    }
  };

  const anyLoading = loading.echoes || loading.traits || loading.patterns;
  const hasData = echoes.length > 0 || traits.length > 0 || patterns.length > 0;

  // ── Config modal handlers ──
  const handleOpenConfig = useCallback(async (section: SectionKey) => {
    const DISPLAY: Record<SectionKey, string> = {
      echoes: 'Recurring Themes',
      traits: 'Character Traits',
      patterns: 'Behavioral Patterns',
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

  // ──────────────────────────────────────────────
  // NOTES DETAIL VIEW — shown when user clicks an analysis item
  // ──────────────────────────────────────────────
  if (selectedItem) {
    const relatedIds = selectedItem.data.related_session_ids || [];
    const keywords = itemKeywords(selectedItem);
    const scored = sessions
      .map(s => ({ session: s, score: sessionRelevance(s, relatedIds, keywords) }))
      .sort((a, b) => b.score - a.score || new Date(b.session.created_at).getTime() - new Date(a.session.created_at).getTime());

    const related = scored.filter(x => x.score > 0).map(x => x.session);
    const others = scored.filter(x => x.score === 0 && x.session.labels.length > 0).map(x => x.session);

    return (
      <>
        <FontInject />
        <div style={{ width: '100%', height: '100%', background: C.void, display: 'flex', flexDirection: 'column', overflow: 'hidden', fontFamily: C.fontCond, color: C.pure }}>

          {/* Top bar */}
          <div style={{
            padding: isMobile ? '0.75rem 1rem' : '1rem 2rem',
            borderBottom: `1px solid ${C.glassBorder}`,
            display: 'flex', alignItems: 'center', gap: '1rem', flexShrink: 0,
          }}>
            <PillBtn onClick={() => setSelectedItem(null)}>← {t('analysis.backButton')}</PillBtn>
            <Eyebrow>
              {selectedItem.kind === 'echo' ? t('analysis.papers.echoes.subtitle') :
               selectedItem.kind === 'trait' ? t('analysis.papers.traits.subtitle') :
               t('analysis.papers.patterns.subtitle')}
              &nbsp;/ RELATED NOTES
            </Eyebrow>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: isMobile ? '1.5rem 1rem' : '2rem 2.5rem' }}>
            <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

              {/* Selected item card — large, prominent */}
              <div style={{
                position: 'relative', overflow: 'hidden',
                borderRadius: '10px',
                border: `1px solid ${C.glassBorder}`,
                background: C.glass,
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                padding: isMobile ? '1.5rem' : '2.5rem 3rem',
                marginBottom: isMobile ? '2rem' : '3rem',
              }}>
                {/* Atmospheric glow */}
                <div style={{
                  position: 'absolute', top: '-40%', right: '-10%',
                  width: '60%', height: '200%', pointerEvents: 'none',
                  background: 'radial-gradient(ellipse 60% 60% at 60% 50%, rgba(100,65,30,0.22) 0%, transparent 70%)',
                }} />

                <div style={{ position: 'relative', zIndex: 1, display: 'flex', gap: '2rem', alignItems: 'flex-start', flexWrap: isMobile ? 'wrap' : 'nowrap' }}>
                  <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
                    <StarMark size={isMobile ? 40 : 56} glow />
                    <NumBadge n={
                      selectedItem.kind === 'echo'
                        ? echoes.indexOf(selectedItem.data as Echo) + 1
                        : selectedItem.kind === 'trait'
                        ? traits.indexOf(selectedItem.data as Trait) + 1
                        : patterns.indexOf(selectedItem.data as Pattern) + 1
                    } />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Eyebrow>
                      {selectedItem.kind === 'echo' ? t('analysis.papers.echoes.title') :
                       selectedItem.kind === 'trait' ? t('analysis.papers.traits.title') :
                       t('analysis.papers.patterns.title')}
                    </Eyebrow>
                    <h2 style={{
                      fontFamily: C.fontCond, fontWeight: 400,
                      fontSize: isMobile ? '28px' : '40px', lineHeight: 0.95,
                      letterSpacing: '-0.03em', textTransform: 'uppercase',
                      color: C.pure, margin: '0.5rem 0 1rem',
                    }}>
                      {itemTitle(selectedItem)}
                    </h2>
                    <p style={{
                      fontFamily: C.fontCond, fontSize: '15px',
                      color: C.fog, lineHeight: 1.55, letterSpacing: '-0.01em',
                      margin: 0, maxWidth: '600px',
                    }}>
                      {itemDesc(selectedItem)}
                    </p>

                    {/* Evidence quote */}
                    {selectedItem.data.evidence && (
                      <div style={{
                        borderLeft: `1px solid ${C.ash}`,
                        paddingLeft: '14px',
                        marginTop: '1.25rem',
                        fontFamily: C.fontCond, fontSize: '13px',
                        color: C.ash, fontStyle: 'italic', lineHeight: 1.55,
                      }}>
                        "{selectedItem.data.evidence}"
                      </div>
                    )}

                    {/* Confidence badge */}
                    {selectedItem.data.confidence && (
                      <div style={{
                        display: 'inline-flex', alignItems: 'center', gap: '6px',
                        borderRadius: '1440px', border: `1px solid ${C.glassBorder}`,
                        padding: '4px 14px', marginTop: '1.25rem',
                        fontFamily: C.fontMono, fontSize: '10px',
                        color: confidenceColor(selectedItem.data.confidence),
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                      }}>
                        <span style={{
                          width: '6px', height: '6px', borderRadius: '50%',
                          background: confidenceColor(selectedItem.data.confidence),
                          display: 'inline-block', flexShrink: 0,
                        }} />
                        {selectedItem.data.confidence}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Related notes */}
              {related.length > 0 && (
                <div style={{ marginBottom: '2.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    <Eyebrow>Related Notes — {related.length}</Eyebrow>
                    <div style={{ flex: 1, height: '1px', background: C.glassBorder }} />
                  </div>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(320px, 1fr))',
                    gap: '1px', background: C.glassBorder,
                    borderRadius: '10px', overflow: 'hidden',
                  }}>
                    {related.map((s, i) => (
                      <NoteCard key={s.id} session={s} idx={i} dateLocale={dateLocale} highlightKeywords={keywords} />
                    ))}
                  </div>
                </div>
              )}

              {/* Other labeled notes */}
              {others.length > 0 && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    <Eyebrow>{related.length > 0 ? 'Other Notes' : `All Notes — ${others.length}`}</Eyebrow>
                    <div style={{ flex: 1, height: '1px', background: C.glassBorder }} />
                  </div>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(320px, 1fr))',
                    gap: '1px', background: C.glassBorder,
                    borderRadius: '10px', overflow: 'hidden',
                    opacity: 0.6,
                  }}>
                    {others.slice(0, 12).map((s, i) => (
                      <NoteCard key={s.id} session={s} idx={i} dateLocale={dateLocale} highlightKeywords={[]} />
                    ))}
                  </div>
                </div>
              )}

              {related.length === 0 && others.length === 0 && (
                <div style={{ textAlign: 'center', padding: '4rem 0' }}>
                  <StarMark size={36} />
                  <p style={{ fontFamily: C.fontCond, fontSize: '16px', color: C.ash, textTransform: 'uppercase', letterSpacing: '-0.01em', marginTop: '1rem' }}>
                    No labeled notes yet
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </>
    );
  }

  // ──────────────────────────────────────────────
  // DASHBOARD VIEW — per-section analysis controls
  // ──────────────────────────────────────────────
  return (
    <>
      <FontInject />
      <div style={{
        width: '100%', height: '100%', overflowY: 'auto',
        background: C.void, color: C.pure, fontFamily: C.fontCond,
      }}>

        {/* ── Atmospheric header ── */}
        <div style={{
          position: 'relative', overflow: 'hidden',
          padding: isMobile ? '2.5rem 1.25rem 2rem' : '4rem 3rem 2.5rem',
          borderBottom: `1px solid ${C.glassBorder}`,
        }}>
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            background: `
              radial-gradient(ellipse 65% 90% at 75% 50%, rgba(110,68,35,0.30) 0%, transparent 65%),
              radial-gradient(ellipse 35% 55% at 15% 25%, rgba(55,35,15,0.18) 0%, transparent 55%)
            `,
          }} />

          <div style={{ position: 'relative', zIndex: 1, maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <Eyebrow>INK &amp; MEMORY</Eyebrow>
              <StarMark size={isMobile ? 32 : 48} glow />
            </div>

            <h1 style={{
              fontFamily: C.fontCond, fontWeight: 400,
              fontSize: isMobile ? '48px' : '72px', lineHeight: 0.9,
              letterSpacing: '-0.03em', textTransform: 'uppercase',
              color: C.pure, margin: '0 0 1.25rem',
            }}>
              {t('analysis.title')}
            </h1>

            {/* Stats */}
            <div style={{ display: 'flex', gap: isMobile ? '2rem' : '3.5rem', flexWrap: 'wrap', marginBottom: savedReports.length > 0 ? '1.5rem' : 0 }}>
              <StatItem n={stats.totalDays} label={t('analysis.stats.days')} />
              <StatItem n={stats.totalEntries} label={t('analysis.stats.entries')} />
              <StatItem n={stats.totalWords.toLocaleString()} label={t('analysis.stats.words')} />
            </div>

            {/* Past report pills — click to restore a historical snapshot across all sections */}
            {savedReports.length > 0 && (
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{
                  fontFamily: C.fontMono, fontSize: '9px', color: C.ash,
                  letterSpacing: '0.06em', textTransform: 'uppercase', flexShrink: 0,
                }}>
                  History
                </span>
                {savedReports.slice(0, 5).map((r, i) => (
                  <PillBtn
                    key={r.id}
                    small
                    onClick={() => {
                      if (r.echoes.length) setEchoes(r.echoes);
                      if (r.traits.length) setTraits(r.traits);
                      if (r.patterns.length) setPatterns(r.patterns);
                    }}
                  >
                    <span style={{ fontFamily: C.fontMono, fontSize: '9px' }}>
                      {new Date(r.timestamp).toLocaleDateString(dateLocale, { month: 'short', day: 'numeric' })}
                    </span>
                    {i === 0 && <span style={{ color: C.ember, fontSize: '10px' }}>●</span>}
                  </PillBtn>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Analysis sections ── */}
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: isMobile ? '2rem 1.25rem 4rem' : '3rem 3rem 5rem' }}>

          {!hasData && !anyLoading && (
            <EmptyState />
          )}

          {/* Echoes */}
          <AnalysisSection
            eyebrow={t('analysis.papers.echoes.subtitle')}
            title={t('analysis.papers.echoes.title')}
            hint={echoes.length > 0 ? 'Click any card to see related notes →' : undefined}
            loading={loading.echoes}
            streamingText={streaming.echoes}
            error={errors.echoes}
            onAnalyze={isAuthenticated ? () => handleAnalyzeSection('echoes') : undefined}
            onConfigClick={isAuthenticated ? () => handleOpenConfig('echoes') : undefined}
            hasResults={echoes.length > 0}
          >
            {echoes.map((echo, i) => (
              <AnalysisCard
                key={i} idx={i}
                title={echo.title}
                desc={echo.description}
                confidence={echo.confidence}
                relatedCount={echo.related_session_ids?.length || 0}
                onClick={() => setSelectedItem({ kind: 'echo', data: echo })}
              />
            ))}
          </AnalysisSection>

          {/* Traits */}
          <AnalysisSection
            eyebrow={t('analysis.papers.traits.subtitle')}
            title={t('analysis.papers.traits.title')}
            loading={loading.traits}
            streamingText={streaming.traits}
            error={errors.traits}
            onAnalyze={isAuthenticated ? () => handleAnalyzeSection('traits') : undefined}
            onConfigClick={isAuthenticated ? () => handleOpenConfig('traits') : undefined}
            hasResults={traits.length > 0}
          >
            {traits.map((trait, i) => (
              <AnalysisCard
                key={i} idx={i}
                title={trait.title}
                desc={trait.description}
                confidence={trait.confidence}
                relatedCount={trait.related_session_ids?.length || 0}
                extra={
                  <div style={{ display: 'flex', gap: '3px', marginTop: '10px', maxWidth: '120px' }}>
                    {[1, 2, 3].map(n => {
                      const filled = trait.confidence === 'high' ? 3 : trait.confidence === 'medium' ? 2 : 1;
                      return <div key={n} style={{ flex: 1, height: '1px', background: n <= filled ? '#ffffff' : '#858585' + '33' }} />;
                    })}
                  </div>
                }
                onClick={() => setSelectedItem({ kind: 'trait', data: trait })}
              />
            ))}
          </AnalysisSection>

          {/* Patterns */}
          <AnalysisSection
            eyebrow={t('analysis.papers.patterns.subtitle')}
            title={t('analysis.papers.patterns.title')}
            loading={loading.patterns}
            streamingText={streaming.patterns}
            error={errors.patterns}
            onAnalyze={isAuthenticated ? () => handleAnalyzeSection('patterns') : undefined}
            onConfigClick={isAuthenticated ? () => handleOpenConfig('patterns') : undefined}
            hasResults={patterns.length > 0}
          >
            {patterns.map((pattern, i) => (
              <AnalysisCard
                key={i} idx={i}
                title={pattern.title}
                desc={pattern.description}
                confidence={pattern.confidence}
                relatedCount={pattern.related_session_ids?.length || 0}
                extra={
                  <div style={{
                    display: 'inline-flex', gap: '6px', alignItems: 'center',
                    borderRadius: '1440px', border: `1px solid rgba(255,255,255,0.08)`,
                    padding: '3px 12px', marginTop: '10px',
                    fontFamily: "'Roboto Mono', ui-monospace, monospace", fontSize: '9px',
                    color: '#858585', textTransform: 'uppercase', letterSpacing: '0.04em',
                  }}>
                    CONF · {pattern.confidence}
                  </div>
                }
                onClick={() => setSelectedItem({ kind: 'pattern', data: pattern })}
              />
            ))}
          </AnalysisSection>
        </div>
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
    </>
  );
}

// ──────────────────────────────────────────────
// Section wrapper — with independent analyze control
// ──────────────────────────────────────────────
function AnalysisSection({
  eyebrow, title, hint, children,
  loading, streamingText, error, onAnalyze, onConfigClick, hasResults,
}: {
  eyebrow: string; title: string; hint?: string;
  children: React.ReactNode;
  loading?: boolean;
  streamingText?: string;
  error?: string;
  onAnalyze?: () => void;
  onConfigClick?: () => void;
  hasResults?: boolean;
}) {
  const { t } = useTranslation();

  return (
    <div style={{ marginBottom: '3.5rem' }}>
      {/* Section header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <Eyebrow>{eyebrow}</Eyebrow>
        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', marginTop: '6px',
          flexWrap: 'wrap', gap: '0.75rem',
        }}>
          <h2 style={{
            fontFamily: "'Barlow Condensed', 'Oswald', ui-sans-serif, sans-serif",
            fontWeight: 400, fontSize: '24px', lineHeight: 1.05,
            letterSpacing: '-0.02em', textTransform: 'uppercase',
            color: '#ffffff', margin: 0,
          }}>
            {title}
          </h2>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
            {hint && !loading && (
              <span style={{
                fontFamily: "'Roboto Mono', ui-monospace, monospace",
                fontSize: '10px', color: '#858585', letterSpacing: '-0.01em',
              }}>
                {hint}
              </span>
            )}
            {onConfigClick && (
              <button
                onClick={onConfigClick}
                title="Configure analysis prompts"
                style={{
                  background: 'none', border: `1px solid rgba(255,255,255,0.15)`,
                  borderRadius: '50%', width: '28px', height: '28px',
                  cursor: 'pointer', color: '#858585',
                  fontFamily: 'inherit', fontSize: '13px', lineHeight: 1,
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'border-color 0.2s, color 0.2s', flexShrink: 0,
                  padding: 0,
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.4)';
                  (e.currentTarget as HTMLButtonElement).style.color = '#ffffff';
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.15)';
                  (e.currentTarget as HTMLButtonElement).style.color = '#858585';
                }}
              >
                ⚙
              </button>
            )}
            {onAnalyze && (
              <PillBtn onClick={loading ? undefined : onAnalyze} disabled={loading} small>
                {loading
                  ? <><span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>◌</span>&nbsp;{t('analysis.actions.generating')}</>
                  : hasResults ? t('analysis.actions.reanalyze', 'Re-analyze') : t('analysis.actions.generate')}
              </PillBtn>
            )}
          </div>
        </div>
        <div style={{ height: '1px', background: 'rgba(255,255,255,0.08)', marginTop: '1rem' }} />
      </div>

      {/* Error */}
      {error && (
        <p style={{
          fontFamily: "'Roboto Mono', ui-monospace, monospace",
          fontSize: '11px', color: '#cc6437', margin: '0 0 1rem',
          letterSpacing: '-0.01em',
        }}>
          {error}
        </p>
      )}

      {/* Streaming progress */}
      {loading && streamingText && (
        <div style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '8px',
          padding: '16px',
          marginBottom: '1rem',
          fontFamily: "'Roboto Mono', ui-monospace, monospace",
          fontSize: '11px', color: '#858585',
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          maxHeight: '160px', overflowY: 'auto',
        }}>
          {streamingText.slice(-1200)}
          <span style={{ opacity: 0.4 }}>▌</span>
        </div>
      )}

      {/* Loading placeholder (no streaming text yet) */}
      {loading && !streamingText && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '12px',
          padding: '2rem 0',
          fontFamily: "'Roboto Mono', ui-monospace, monospace",
          fontSize: '11px', color: '#858585', letterSpacing: '-0.01em',
        }}>
          <span>Reading memory workspace and analysing…</span>
        </div>
      )}

      {/* Cards grid */}
      {!loading && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '12px',
        }}>
          {children}
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────
// Clickable analysis card
// ──────────────────────────────────────────────
function AnalysisCard({ idx, title, desc, confidence, relatedCount, extra, onClick }: {
  idx: number; title: string; desc: string;
  confidence?: string; relatedCount?: number;
  extra?: React.ReactNode;
  onClick: () => void;
}) {
  const [hov, setHov] = useState(false);
  const confColor = confidence ? confidenceColor(confidence) : C.ash;
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: hov ? 'rgba(255,255,255,0.07)' : 'rgba(255,255,255,0.03)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: `1px solid ${hov ? 'rgba(255,255,255,0.20)' : 'rgba(255,255,255,0.08)'}`,
        borderRadius: '10px',
        padding: '20px',
        cursor: 'pointer',
        transition: 'background 0.2s, border-color 0.2s',
        display: 'flex', flexDirection: 'column', gap: 0,
        position: 'relative',
      }}
    >
      {/* Number + confidence + arrow row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <NumBadge n={idx + 1} />
          {confidence && (
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%',
              background: confColor, display: 'inline-block', flexShrink: 0,
              title: confidence,
            }} />
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {relatedCount != null && relatedCount > 0 && (
            <span style={{
              fontFamily: C.fontMono, fontSize: '9px', color: C.ash,
              letterSpacing: '0.04em',
            }}>
              {relatedCount}↗
            </span>
          )}
          <span style={{
            fontFamily: C.fontMono,
            fontSize: '11px', color: hov ? '#cecece' : '#858585',
            transition: 'color 0.2s, transform 0.2s',
            transform: hov ? 'translateX(2px)' : 'none',
          }}>
            →
          </span>
        </div>
      </div>

      {/* Title */}
      <h3 style={{
        fontFamily: "'Barlow Condensed', 'Oswald', ui-sans-serif, sans-serif",
        fontWeight: 400, fontSize: '18px', lineHeight: 1.1,
        letterSpacing: '-0.02em', textTransform: 'uppercase',
        color: '#ffffff', margin: '0 0 8px',
      }}>
        {title}
      </h3>

      {/* Description */}
      <p style={{
        fontFamily: "'Barlow Condensed', 'Oswald', ui-sans-serif, sans-serif",
        fontSize: '13px', color: '#858585', lineHeight: 1.55,
        letterSpacing: '-0.01em', margin: 0,
        display: '-webkit-box',
        WebkitLineClamp: 3,
        WebkitBoxOrient: 'vertical' as any,
        overflow: 'hidden',
      }}>
        {desc}
      </p>

      {extra}
    </div>
  );
}

// ──────────────────────────────────────────────
// Note card (in the detail panel)
// ──────────────────────────────────────────────
function NoteCard({ session, idx, dateLocale, highlightKeywords }: {
  session: UserSession; idx: number; dateLocale: string; highlightKeywords: string[];
}) {
  const [hov, setHov] = useState(false);
  const title = session.name || session.first_line || '—';
  const dateStr = new Date(session.created_at).toLocaleDateString(dateLocale, {
    year: 'numeric', month: '2-digit', day: '2-digit',
  });

  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: '16px 20px',
        background: hov ? 'rgba(255,255,255,0.04)' : '#0b0b0b',
        transition: 'background 0.18s',
        display: 'flex', flexDirection: 'column', gap: '10px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <NumBadge n={idx + 1} />
        <span style={{ fontFamily: "'Roboto Mono', ui-monospace, monospace", fontSize: '10px', color: '#858585' }}>
          {dateStr}
        </span>
      </div>

      <div style={{
        fontFamily: "'Barlow Condensed', 'Oswald', ui-sans-serif, sans-serif",
        fontSize: '14px', letterSpacing: '-0.01em',
        color: '#cecece',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>
        {title}
      </div>

      {/* Labels — highlight matching ones */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {session.labels.map(lbl => {
          const matched = highlightKeywords.length > 0 &&
            highlightKeywords.some(kw => lbl.toLowerCase().includes(kw));
          return (
            <span
              key={lbl}
              style={{
                borderRadius: '1440px',
                border: `1px solid ${matched ? C.ember + 'aa' : 'rgba(255,255,255,0.12)'}`,
                background: matched ? `${C.ember}14` : 'transparent',
                color: matched ? C.ember : '#858585',
                fontFamily: "'Barlow Condensed', 'Oswald', ui-sans-serif, sans-serif",
                fontSize: '11px', letterSpacing: '-0.01em',
                textTransform: 'uppercase', padding: '3px 10px',
              }}
            >
              {lbl}
            </span>
          );
        })}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Misc small components
// ──────────────────────────────────────────────
function StatItem({ n, label }: { n: number | string; label: string }) {
  return (
    <div>
      <div style={{
        fontFamily: "'Roboto Mono', ui-monospace, monospace",
        fontSize: '32px', lineHeight: 1, letterSpacing: '-0.04em', color: '#ffffff',
      }}>
        {n}
      </div>
      <div style={{
        fontFamily: "'Barlow Condensed', 'Oswald', ui-sans-serif, sans-serif",
        fontSize: '10px', letterSpacing: '0.08em', textTransform: 'uppercase',
        color: '#858585', marginTop: '5px',
      }}>
        {label}
      </div>
    </div>
  );
}

function EmptyState() {
  const { t } = useTranslation();
  return (
    <div style={{ padding: '5rem 0', textAlign: 'center' }}>
      <StarMark size={44} />
      <p style={{
        fontFamily: "'Barlow Condensed', 'Oswald', ui-sans-serif, sans-serif",
        fontWeight: 400, fontSize: '20px', letterSpacing: '-0.02em',
        color: '#858585', textTransform: 'uppercase', margin: '1.5rem 0 0.5rem',
      }}>
        {t('analysis.empty.title')}
      </p>
      <p style={{
        fontFamily: "'Roboto Mono', ui-monospace, monospace",
        fontSize: '11px', color: '#858585' + '77',
        maxWidth: '360px', margin: '0 auto', lineHeight: 1.6,
      }}>
        {t('analysis.empty.description')}
      </p>
    </div>
  );
}
