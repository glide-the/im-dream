// [Input] Existing actor-scoped Chat, today's scheduled-task and Dream re-entry DTOs plus one display clock.
// [Output] Pure activity rows, source-local identity deduplication and recent-Chat scan stopping evidence.
// [Pos] Chat activity presentation policy; it neither reads transport nor changes Dream run ordering.
// [Sync] 2026-10-07: unify the requested inclusive five-minute window and truthful task/Dream priority levels.

import type { ChatHistoryThread } from '../../api/chatHistoryApi';
import type { ScheduledTask, ScheduledTrigger } from '../../api/scheduledTaskApi';
import type { StoryWorkspaceDreamReentryItem } from '../../hooks/story-workspace/contracts';
import type { ScheduledTaskMarkerSnapshot } from './scheduledTaskMarkerModel';
import { getLocalDayKey, parseFlexibleTimestamp } from '../../utils/timezone';

export const ACTIVITY_SIDEBAR_POLICY = Object.freeze({
  recentWindowMs: 5 * 60 * 1000,
  chatPageSize: 50,
  refreshIntervalMs: 30 * 1000,
  clockIntervalMs: 1000,
});

export type ActivitySource = 'scheduled' | 'chat' | 'dream';
export type ActivityFilters = Record<ActivitySource | 'priority', boolean>;
export const DEFAULT_ACTIVITY_FILTERS: ActivityFilters = { priority: true, scheduled: true, chat: true, dream: true };
export interface ScheduledDayData { tasks: ScheduledTask[]; triggers: ScheduledTrigger[] }
export interface ActivityRow {
  key: string;
  id: string;
  source: ActivitySource;
  title: string | null;
  activityAt: number;
  priority: number;
  state: string | null;
  stale: boolean;
  href?: string;
  snapshot?: ScheduledTaskMarkerSnapshot | null;
}

export function activityTimestamp(value: string | null | undefined): number | null {
  if (!value) return null;
  return parseFlexibleTimestamp(value)?.getTime() ?? null;
}

export function isRecentActivity(value: string, now: number): boolean {
  const at = activityTimestamp(value);
  return at !== null && now >= at && now - at <= ACTIVITY_SIDEBAR_POLICY.recentWindowMs;
}

export function deduplicateActivityThreads(threads: readonly ChatHistoryThread[]): ChatHistoryThread[] {
  const byId = new Map<string, ChatHistoryThread>();
  for (const thread of threads) {
    const current = byId.get(thread.id);
    if (!current || (activityTimestamp(thread.updated_at) ?? -Infinity) > (activityTimestamp(current.updated_at) ?? -Infinity)) {
      byId.set(thread.id, thread);
    }
  }
  return [...byId.values()];
}

/** Invalid/future timestamps are excluded but cannot establish the descending scan's old-record boundary. */
export function recentChatBatch(batch: readonly ChatHistoryThread[], now: number): { rows: ChatHistoryThread[]; stop: boolean } {
  const boundary = now - ACTIVITY_SIDEBAR_POLICY.recentWindowMs;
  return {
    rows: batch.filter((thread) => isRecentActivity(thread.updated_at, now)),
    stop: batch.length === 0 || batch.some((thread) => {
      const at = activityTimestamp(thread.updated_at);
      return at !== null && at < boundary;
    }),
  };
}

export function activityLocalDay(now: number, timeZone: string): string {
  return getLocalDayKey(now, timeZone)!;
}

export function scheduledActivityRows(data: ScheduledDayData | null, stale: boolean): ActivityRow[] {
  if (!data) return [];
  const definitions = new Map(data.tasks.map((task) => [task.id, task]));
  const triggers = new Map<string, ScheduledTrigger[]>();
  for (const trigger of data.triggers) triggers.set(trigger.task_id, [...(triggers.get(trigger.task_id) ?? []), trigger]);
  const ids = new Set([...definitions.keys(), ...triggers.keys()]);
  const rows: ActivityRow[] = [];
  for (const id of ids) {
    const definition = definitions.get(id);
    const executions = [...(triggers.get(id) ?? [])].sort((a, b) => (
      Number(b.status === 'running') - Number(a.status === 'running')
      || (activityTimestamp(b.updated_at) ?? -Infinity) - (activityTimestamp(a.updated_at) ?? -Infinity)
      || a.id.localeCompare(b.id)
    ));
    const selected = executions[0];
    const running = executions.some((trigger) => trigger.status === 'running');
    if (definition?.status === 'deleted' && !running) continue;
    const times = [definition?.updated_at, ...executions.map((trigger) => trigger.updated_at)]
      .map(activityTimestamp).filter((at): at is number => at !== null);
    rows.push({
      key: `scheduled:${id}`, id, source: 'scheduled', title: definition?.title ?? selected?.title ?? null,
      activityAt: times.length ? Math.max(...times) : -Infinity,
      priority: running && !stale ? 0 : 2,
      state: selected?.status ?? definition?.status ?? null, stale,
      snapshot: definition ? {
        id: definition.id, title: definition.title, rule: definition.rule,
        nextRunAt: definition.next_run_at, status: definition.status, revision: definition.revision,
      } : null,
    });
  }
  return rows;
}

export function buildActivityRows(input: {
  now: number;
  chats: readonly ChatHistoryThread[];
  dreams: readonly StoryWorkspaceDreamReentryItem[];
  scheduled: ScheduledDayData | null;
  stale: Record<ActivitySource, boolean>;
  filters: ActivityFilters;
}): ActivityRow[] {
  if (!input.filters.priority) return [];
  const rows: ActivityRow[] = input.filters.scheduled ? scheduledActivityRows(input.scheduled, input.stale.scheduled) : [];
  if (input.filters.chat) {
    for (const thread of deduplicateActivityThreads(input.chats)) {
      if (!isRecentActivity(thread.updated_at, input.now)) continue;
      rows.push({ key: `chat:${thread.id}`, id: thread.id, source: 'chat', title: thread.title,
        activityAt: activityTimestamp(thread.updated_at)!, priority: 2, state: null, stale: input.stale.chat });
    }
  }
  if (input.filters.dream) {
    const runs = new Map<string, StoryWorkspaceDreamReentryItem>();
    for (const run of input.dreams) {
      const previous = runs.get(run.storyWorkspaceRunId);
      if (!previous || (activityTimestamp(run.lastActivityAt) ?? -Infinity) > (activityTimestamp(previous.lastActivityAt) ?? -Infinity)) runs.set(run.storyWorkspaceRunId, run);
    }
    for (const run of runs.values()) {
      if (!isRecentActivity(run.lastActivityAt, input.now)) continue;
      rows.push({ key: `dream:${run.storyWorkspaceRunId}`, id: run.storyWorkspaceRunId, source: 'dream', title: run.displayTitle,
        activityAt: activityTimestamp(run.lastActivityAt)!, priority: !input.stale.dream && ['generating', 'running'].includes(run.lifecycle) ? 1 : 2,
        state: run.lifecycle, stale: input.stale.dream, href: run.href });
    }
  }
  return rows.sort((a, b) => a.priority - b.priority || b.activityAt - a.activityAt || a.key.localeCompare(b.key));
}
