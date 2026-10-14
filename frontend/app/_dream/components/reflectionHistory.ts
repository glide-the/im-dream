// [Input] Strict public history report DTOs and existing ReflectionResult payloads.
// [Output] Shared saved-report projection with independent identities and true creation time.
// [Pos] AnalysisView and TimelinePage history presentation seam; no transport or state machine.
// [Sync] 2026-10-14: preserve server microsecond ordering; never merge same-day analyses.
import type { AnalysisHistoryReport, ReflectionResult, ReflectionSectionKey, ReflectionAnalysisContentSummary } from '../api/voiceApi';

// Product-owned preview boundary: latest three analyses (docs/prd/memory/reflections-history-prd.md).
export const ANALYSIS_HISTORY_PREVIEW_LIMIT = 3;
export interface AnalysisReport {
  id: string | number;
  taskId?: string;
  failedSections?: ReflectionSectionKey[];
  analysisContent?: ReflectionAnalysisContentSummary | null;
  echoes: ReflectionResult[];
  traits: ReflectionResult[];
  patterns: ReflectionResult[];
  timestamp: number;
  createdAt?: string;
  stats: { days: number; entries: number; words: number };
}

export function historyReportForReading(report: AnalysisHistoryReport): AnalysisReport {
  return {
    id: report.id, taskId: report.task_id ?? undefined,
    createdAt: report.analysis_created_at, timestamp: new Date(report.analysis_created_at).getTime(),
    echoes: report.report_data?.echoes ?? [], traits: report.report_data?.traits ?? [], patterns: report.report_data?.patterns ?? [],
    failedSections: report.report_data?.failed_sections, analysisContent: report.report_data?.analysis_content,
    stats: report.report_data?.stats ?? { days: 0, entries: 0, words: 0 },
  };
}

/** Append server-ordered pages by stable identity; preserve the original page order including microseconds. */
export function appendHistoryReports(previous: AnalysisReport[], incoming: AnalysisReport[]): AnalysisReport[] {
  const seen = new Set(previous.map(report => String(report.id)));
  return [...previous, ...incoming.filter(report => {
    const id = String(report.id);
    if (seen.has(id)) return false;
    seen.add(id); return true;
  })];
}
