/**
 * [Input] voiceApi: analyzeEchoes, analyzeTraits, analyzePatterns, saveAnalysisReport,
 *         getAnalysisReports, listSessions, fetchSessionsAggregate
 * [Output] Reflections page — Ciridae authentic dark-noir design
 * [Pos] components/AnalysisView — full-page Reflections (Analysis) view
 * [Sync] 2026-06-05: Interaction redesign — dashboard shows analysis cards as primary;
 *         clicking any analysis item opens a "related notes" detail panel showing
 *         sessions filtered by label relevance to the clicked item.
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
  type UserSession
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

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────
interface Echo { title: string; description: string; examples?: string[] }
interface Trait { trait: string; strength: number; evidence: string }
interface Pattern { pattern: string; description: string; frequency: string }

type AnalysisItem =
  | { kind: 'echo'; data: Echo }
  | { kind: 'trait'; data: Trait }
  | { kind: 'pattern'; data: Pattern }

interface AnalysisReport {
  id: number;
  echoes: Echo[]; traits: Trait[]; patterns: Pattern[];
  timestamp: number;
  stats: { days: number; entries: number; words: number };
}

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────

/** Returns keywords from an analysis item for label matching */
function itemKeywords(item: AnalysisItem): string[] {
  const raw =
    item.kind === 'echo' ? `${item.data.title} ${item.data.description}` :
    item.kind === 'trait' ? `${item.data.trait} ${item.data.evidence}` :
    `${item.data.pattern} ${item.data.description}`;
  return raw.toLowerCase().split(/[\s,，。.!?、]+/).filter(w => w.length > 1);
}

function itemTitle(item: AnalysisItem): string {
  return item.kind === 'echo' ? item.data.title :
    item.kind === 'trait' ? item.data.trait :
    item.data.pattern;
}

function itemDesc(item: AnalysisItem): string {
  return item.kind === 'echo' ? item.data.description :
    item.kind === 'trait' ? item.data.evidence :
    item.data.description;
}

/** Score a session's relevance to an analysis item by label keyword overlap */
function sessionRelevance(session: UserSession, keywords: string[]): number {
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
// Main component
// ══════════════════════════════════════════════
export default function AnalysisView() {
  const { isAuthenticated } = useAuth();
  const { t, i18n } = useTranslation();
  const dateLocale = getDateLocale(i18n.language);
  const isMobile = useMobile();

  // ── State ──
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [echoes, setEchoes] = useState<Echo[]>([]);
  const [traits, setTraits] = useState<Trait[]>([]);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [loading, setLoading] = useState({ echoes: false, traits: false, patterns: false });
  const [error, setError] = useState('');
  const [stats, setStats] = useState({ totalDays: 0, totalWords: 0, totalEntries: 0 });
  const [savedReports, setSavedReports] = useState<AnalysisReport[]>([]);

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

  useEffect(() => {
    const loadStats = async () => {
      try {
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai';
        const agg = await fetchSessionsAggregate(tz);
        setStats({ totalDays: agg.stats.total_days, totalWords: agg.stats.total_words, totalEntries: agg.stats.total_entries });
      } catch (e) { console.error(e); }
    };

    const loadReports = async () => {
      if (isAuthenticated) {
        try {
          const db = await getAnalysisReports(MAX_SAVED_REPORTS);
          const fmt = db.map((r: any) => ({
            id: r.id, echoes: r.report_data?.echoes || [],
            traits: r.report_data?.traits || [], patterns: r.report_data?.patterns || [],
            timestamp: new Date(r.created_at).getTime(),
            stats: r.report_data?.stats || { days: 0, entries: 0, words: 0 }
          }));
          setSavedReports(fmt);
          if (fmt.length > 0) {
            setEchoes(fmt[0].echoes); setTraits(fmt[0].traits); setPatterns(fmt[0].patterns);
          }
        } catch (e) { console.error(e); }
      } else {
        const saved = localStorage.getItem(STORAGE_KEYS.ANALYSIS_REPORTS);
        if (saved) {
          try {
            const r = JSON.parse(saved);
            setSavedReports(r);
            if (r.length > 0) { setEchoes(r[0].echoes); setTraits(r[0].traits); setPatterns(r[0].patterns); }
          } catch (e) { console.error(e); }
        }
      }
    };

    loadStats(); loadReports(); loadSessions();
  }, [isAuthenticated, loadSessions]);

  // ── Generate analysis ──
  const handleAnalyzeAll = async () => {
    if (!isAuthenticated) { setError('Please log in to use reflections.'); return; }
    setError('');
    let er: Echo[] = [], tr: Trait[] = [], pr: Pattern[] = [];

    // @@@ Run one analysis task: set loading, call fn, update state, surface error
    const run = async <T extends any[]>(
      fn: () => Promise<T>,
      key: 'echoes' | 'traits' | 'patterns',
      cb: (r: T) => void,
    ): Promise<T> => {
      setLoading(p => ({ ...p, [key]: true }));
      try {
        const result = await fn();
        cb(result);
        return result;
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setError(prev => prev ? `${prev} | ${key}: ${msg}` : `${key}: ${msg}`);
        console.error(`[Reflections] ${key} analysis failed:`, e);
        return [] as unknown as T;
      } finally {
        setLoading(p => ({ ...p, [key]: false }));
      }
    };

    [er, tr, pr] = await Promise.all([
      run(() => analyzeEchoes() as Promise<Echo[]>, 'echoes', r => setEchoes(r)),
      run(() => analyzeTraits() as Promise<Trait[]>, 'traits', r => setTraits(r)),
      run(() => analyzePatterns() as Promise<Pattern[]>, 'patterns', r => setPatterns(r)),
    ]);

    // @@@ Warn if all three came back empty (likely JSON parse failure)
    if (er.length === 0 && tr.length === 0 && pr.length === 0) {
      setError(prev => prev || 'Analysis returned no results — the agent response may not have been valid JSON. Check the browser console for details.');
      return;
    }

    const report: AnalysisReport = {
      id: Date.now(), echoes: er, traits: tr, patterns: pr,
      timestamp: Date.now(),
      stats: { days: stats.totalDays, entries: stats.totalEntries, words: stats.totalWords }
    };

    if (isAuthenticated) {
      try {
        await saveAnalysisReport('full_analysis', {
          echoes: er, traits: tr, patterns: pr,
          stats: { days: stats.totalDays, entries: stats.totalEntries, words: stats.totalWords }
        });
        const db = await getAnalysisReports(MAX_SAVED_REPORTS);
        setSavedReports(db.map((r: any) => ({
          id: r.id, echoes: r.report_data?.echoes || [], traits: r.report_data?.traits || [],
          patterns: r.report_data?.patterns || [], timestamp: new Date(r.created_at).getTime(),
          stats: r.report_data?.stats || { days: 0, entries: 0, words: 0 }
        })));
      } catch (e) { console.error(e); }
    } else {
      const updated = [report, ...savedReports].slice(0, MAX_SAVED_REPORTS);
      localStorage.setItem(STORAGE_KEYS.ANALYSIS_REPORTS, JSON.stringify(updated));
      setSavedReports(updated);
    }
  };

  const anyLoading = loading.echoes || loading.traits || loading.patterns;
  const hasData = echoes.length > 0 || traits.length > 0 || patterns.length > 0;

  // ──────────────────────────────────────────────
  // NOTES DETAIL VIEW — shown when user clicks an analysis item
  // ──────────────────────────────────────────────
  if (selectedItem) {
    const keywords = itemKeywords(selectedItem);
    const scored = sessions
      .map(s => ({ session: s, score: sessionRelevance(s, keywords) }))
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

                    {/* Extra: echo examples */}
                    {selectedItem.kind === 'echo' && selectedItem.data.examples && selectedItem.data.examples.length > 0 && (
                      <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {selectedItem.data.examples.map((ex, i) => (
                          <div key={i} style={{
                            borderLeft: `1px solid ${C.ash}`,
                            paddingLeft: '14px',
                            fontFamily: C.fontCond, fontSize: '13px',
                            color: C.ash, fontStyle: 'italic', lineHeight: 1.55,
                          }}>
                            "{ex}"
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Extra: trait strength bar */}
                    {selectedItem.kind === 'trait' && (
                      <div style={{ display: 'flex', gap: '4px', marginTop: '1.25rem', maxWidth: '160px' }}>
                        {[1,2,3,4,5].map(i => (
                          <div key={i} style={{
                            flex: 1, height: '2px',
                            background: i <= (selectedItem.data as Trait).strength ? C.pure : C.ash + '33',
                          }} />
                        ))}
                      </div>
                    )}

                    {/* Extra: pattern frequency */}
                    {selectedItem.kind === 'pattern' && (
                      <div style={{
                        display: 'inline-flex', alignItems: 'center', gap: '6px',
                        borderRadius: '1440px', border: `1px solid ${C.glassBorder}`,
                        padding: '4px 14px', marginTop: '1.25rem',
                        fontFamily: C.fontMono, fontSize: '10px',
                        color: C.ash, textTransform: 'uppercase', letterSpacing: '0.04em',
                      }}>
                        FREQ · {(selectedItem.data as Pattern).frequency}
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
  // DASHBOARD VIEW — analysis as primary content
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
            <div style={{ display: 'flex', gap: isMobile ? '2rem' : '3.5rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
              <StatItem n={stats.totalDays} label={t('analysis.stats.days')} />
              <StatItem n={stats.totalEntries} label={t('analysis.stats.entries')} />
              <StatItem n={stats.totalWords.toLocaleString()} label={t('analysis.stats.words')} />
            </div>

            {/* Controls row */}
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
              <PillBtn onClick={handleAnalyzeAll} disabled={anyLoading}>
                {anyLoading ? `◌  ${t('analysis.actions.generating')}` : t('analysis.actions.generate')}
              </PillBtn>

              {/* Past report pills */}
              {savedReports.slice(0, 5).map((r, i) => (
                <PillBtn
                  key={r.id}
                  small
                  onClick={() => { setEchoes(r.echoes); setTraits(r.traits); setPatterns(r.patterns); }}
                >
                  <span style={{ fontFamily: C.fontMono, fontSize: '9px' }}>
                    {new Date(r.timestamp).toLocaleDateString(dateLocale, { month: 'short', day: 'numeric' })}
                  </span>
                  {i === 0 && <span style={{ color: C.ember, fontSize: '10px' }}>●</span>}
                </PillBtn>
              ))}
            </div>

            {error && (
              <p style={{ fontFamily: C.fontMono, fontSize: '11px', color: C.ember, margin: '1rem 0 0', letterSpacing: '-0.01em' }}>
                {error}
              </p>
            )}
          </div>
        </div>

        {/* ── Analysis content ── */}
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: isMobile ? '2rem 1.25rem 4rem' : '3rem 3rem 5rem' }}>

          {!hasData && !anyLoading && (
            <EmptyState />
          )}

          {anyLoading && (
            <div style={{ padding: '4rem 0', textAlign: 'center' }}>
              <StarMark size={40} glow />
              <p style={{ fontFamily: C.fontCond, fontSize: '16px', color: C.ash, textTransform: 'uppercase', letterSpacing: '-0.01em', marginTop: '1.5rem' }}>
                {t('analysis.actions.generating')}
              </p>
            </div>
          )}

          {/* Echoes */}
          {echoes.length > 0 && (
            <AnalysisSection
              eyebrow={t('analysis.papers.echoes.subtitle')}
              title={t('analysis.papers.echoes.title')}
              hint="Click any card to see related notes →"
            >
              {echoes.map((echo, i) => (
                <AnalysisCard
                  key={i} idx={i}
                  title={echo.title}
                  desc={echo.description}
                  onClick={() => setSelectedItem({ kind: 'echo', data: echo })}
                />
              ))}
            </AnalysisSection>
          )}

          {/* Traits */}
          {traits.length > 0 && (
            <AnalysisSection
              eyebrow={t('analysis.papers.traits.subtitle')}
              title={t('analysis.papers.traits.title')}
            >
              {traits.map((trait, i) => (
                <AnalysisCard
                  key={i} idx={i}
                  title={trait.trait}
                  desc={trait.evidence}
                  extra={
                    <div style={{ display: 'flex', gap: '3px', marginTop: '10px', maxWidth: '120px' }}>
                      {[1,2,3,4,5].map(n => (
                        <div key={n} style={{ flex: 1, height: '1px', background: n <= trait.strength ? C.pure : C.ash + '33' }} />
                      ))}
                    </div>
                  }
                  onClick={() => setSelectedItem({ kind: 'trait', data: trait })}
                />
              ))}
            </AnalysisSection>
          )}

          {/* Patterns */}
          {patterns.length > 0 && (
            <AnalysisSection
              eyebrow={t('analysis.papers.patterns.subtitle')}
              title={t('analysis.papers.patterns.title')}
            >
              {patterns.map((pattern, i) => (
                <AnalysisCard
                  key={i} idx={i}
                  title={pattern.pattern}
                  desc={pattern.description}
                  extra={
                    <div style={{
                      display: 'inline-flex', gap: '6px', alignItems: 'center',
                      borderRadius: '1440px', border: `1px solid ${C.glassBorder}`,
                      padding: '3px 12px', marginTop: '10px',
                      fontFamily: C.fontMono, fontSize: '9px',
                      color: C.ash, textTransform: 'uppercase', letterSpacing: '0.04em',
                    }}>
                      FREQ · {pattern.frequency}
                    </div>
                  }
                  onClick={() => setSelectedItem({ kind: 'pattern', data: pattern })}
                />
              ))}
            </AnalysisSection>
          )}
        </div>
      </div>
    </>
  );
}

// ──────────────────────────────────────────────
// Section wrapper
// ──────────────────────────────────────────────
function AnalysisSection({ eyebrow, title, hint, children }: {
  eyebrow: string; title: string; hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: '3.5rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <Eyebrow>{eyebrow}</Eyebrow>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '6px', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h2 style={{
            fontFamily: "'Barlow Condensed', 'Oswald', ui-sans-serif, sans-serif",
            fontWeight: 400, fontSize: '24px', lineHeight: 1.05,
            letterSpacing: '-0.02em', textTransform: 'uppercase',
            color: '#ffffff', margin: 0,
          }}>
            {title}
          </h2>
          {hint && (
            <span style={{ fontFamily: "'Roboto Mono', ui-monospace, monospace", fontSize: '10px', color: '#858585', letterSpacing: '-0.01em' }}>
              {hint}
            </span>
          )}
        </div>
        <div style={{ height: '1px', background: 'rgba(255,255,255,0.08)', marginTop: '1rem' }} />
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '12px',
      }}>
        {children}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Clickable analysis card
// ──────────────────────────────────────────────
function AnalysisCard({ idx, title, desc, extra, onClick }: {
  idx: number; title: string; desc: string;
  extra?: React.ReactNode; onClick: () => void;
}) {
  const [hov, setHov] = useState(false);
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
      {/* Number + arrow row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <NumBadge n={idx + 1} />
        <span style={{
          fontFamily: "'Roboto Mono', ui-monospace, monospace",
          fontSize: '11px', color: hov ? '#cecece' : '#858585',
          transition: 'color 0.2s, transform 0.2s',
          transform: hov ? 'translateX(2px)' : 'none',
        }}>
          →
        </span>
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
