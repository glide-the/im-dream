// [Input] Production history DTO projection, page identities and account timezone utilities.
// [Output] Deterministic independent-report, precise-order, identity and date-boundary assertions.
// [Pos] Provider-free history presentation tests; no browser, storage or model calls.
// [Sync] 2026-10-14: verify independent same-day reports and preserve server microsecond order.
import { expect, test } from '@playwright/test';
import { appendHistoryReports, historyReportForReading } from '../reflectionHistory';
import type { AnalysisHistoryReport } from '../../api/voiceApi';
import { getLocalDayKey } from '../../utils/timezone';

const saved = (id: string, created: string): AnalysisHistoryReport => ({
  id, created_at: '2026-12-01T00:00:00Z', analysis_created_at: created, task_id: '80000000-0000-4000-8000-000000000001',
  report_data: { echoes: [], traits: [], patterns: [], stats: { days: 90, entries: 120, words: 20 } },
});

test('only true analysis creation drives reading and account-local grouping', () => {
  const report = historyReportForReading(saved('9007199254740993', '2026-09-30T16:00:00.123456Z'));
  expect(report.id).toBe('9007199254740993');
  expect(report.createdAt).toBe('2026-09-30T16:00:00.123456Z');
  expect(getLocalDayKey(report.createdAt, 'Asia/Shanghai')).toBe('2026-10-01');
  expect(getLocalDayKey(report.createdAt, 'America/Los_Angeles')).toBe('2026-09-30');
  expect(report.timestamp).toBe(Date.parse('2026-09-30T16:00:00.123456Z'));
});

test('same-day and sub-millisecond analyses stay independent and preserve server order across duplicate pages', () => {
  const newest = historyReportForReading(saved('9007199254740993', '2026-10-01T00:00:00.123457Z'));
  const older = historyReportForReading(saved('9007199254740994', '2026-10-01T00:00:00.123456Z'));
  expect(newest.timestamp).toBe(older.timestamp);
  const merged = appendHistoryReports([newest], [newest, older, older]);
  expect(merged.map(item => item.id)).toEqual([newest.id, older.id]);
  expect(appendHistoryReports(merged, [])).toEqual(merged);
});
