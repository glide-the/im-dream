// [Sync] 2026-10-06: validate selected-day snapshot DTO and version-bound metadata-only verification.
// [Input] Shared same-origin connector transport and the server-owned selected-day snapshot DTO.
// [Output] Validated read-only selected-day response; malformed metadata cannot become a successful empty list.
// [Pos] Calendar Notion API boundary in frontend/app/_dream/api.
// [Sync] 2026-10-05: add cancellable snapshot-first reads with count, identity and time consistency checks.
import { z } from 'zod';
import { fetchJson, ResourceConnectorApiError } from './resourceConnectorApi';

const instant = z.string().refine((value) => /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)));
const count = z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER);
const schema = z.object({
  connectorId: z.string().min(1), dateKey: z.string().regex(/^\d{4}-\d{2}-\d{2}$/), timeZone: z.string().min(1),
  intervalStart: instant, intervalEnd: instant, observedAt: instant,
  coverage: z.literal('connector_snapshot'), paginationState: z.enum(['complete', 'partial']),
  todayKey: z.string().regex(/^\d{4}-\d{2}-\d{2}$/), snapshotVersion: z.string().min(1).nullable(),
  snapshotFetchedAt: instant.nullable(), verificationState: z.enum(['not_required', 'pending', 'complete', 'partial']),
  partialReasons: z.array(z.string()), candidateCount: count, retryAfter: count.nullable(),
  counts: z.object({ created: count, edited: count, total: count }),
  items: z.array(z.object({
    pageId: z.string().min(1), title: z.string(), url: z.string().url().startsWith('https://').nullable(),
    createdTime: instant.nullable(), lastEditedTime: instant.nullable(), emoji: z.string().nullable(),
    group: z.enum(['created', 'edited']), createdOnDate: z.boolean(), editedOnDate: z.boolean(),
  })),
}).superRefine((value, context) => {
  const created = value.items.filter((item) => item.group === 'created').length;
  const start = Date.parse(value.intervalStart), end = Date.parse(value.intervalEnd);
  const within = (text: string | null) => text !== null && start <= Date.parse(text) && Date.parse(text) < end;
  if (start >= end || new Set(value.items.map((item) => item.pageId)).size !== value.items.length
    || value.counts.total !== value.items.length || value.counts.created !== created
    || value.counts.edited !== value.items.length - created || value.candidateCount < value.items.length
    || value.items.some((item) => item.createdOnDate !== within(item.createdTime)
      || item.editedOnDate !== within(item.lastEditedTime) || (!item.createdOnDate && !item.editedOnDate)
      || (item.group === 'created') !== item.createdOnDate
      || (value.dateKey !== value.todayKey && !item.createdOnDate))) {
    context.addIssue({ code: 'custom', message: 'Inconsistent document metadata' });
  }
});
export type NotionTodayResponse = z.infer<typeof schema>;

export async function getNotionToday(connectorId: string, dateKey: string, signal: AbortSignal, snapshotVersion?: string): Promise<NotionTodayResponse> {
  const query = new URLSearchParams({ date_key: dateKey });
  if (snapshotVersion !== undefined) { query.set('validate_remote', 'true'); query.set('snapshot_version', snapshotVersion); }
  const raw = await fetchJson<unknown>(`/api/connectors/${encodeURIComponent(connectorId)}/notion/documents?${query}`, { signal });
  const result = schema.safeParse(raw);
  if (!result.success) throw new ResourceConnectorApiError(502, 'Invalid document metadata', 'NOTION_RESPONSE_INVALID');
  return result.data;
}
