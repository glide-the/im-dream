// [Input] Existing Chat/task/Dream DTO fixtures and an explicit display clock.
// [Output] Provider-free contracts for inclusive recency, day range, truthful priority, source deduplication and menu projection.
// [Pos] Activity presentation tests; Dream Project/Episode/publication/Hook/DB and Agent transport are outside this change.
// [Sync] 2026-10-07: cover five-minute/cross-midnight behavior without duplicating production conversion or scan logic.
import { expect, test } from '@playwright/test';
import type { ChatHistoryThread } from '../../../api/chatHistoryApi';
import type { ScheduledTask, ScheduledTrigger } from '../../../api/scheduledTaskApi';
import type { StoryWorkspaceDreamReentryItem } from '../../../hooks/story-workspace/contracts';
import { ACTIVITY_SIDEBAR_POLICY, activityLocalDay, activityTimestamp, buildActivityRows, DEFAULT_ACTIVITY_FILTERS,
  deduplicateActivityThreads, isRecentActivity, recentChatBatch, scheduledActivityRows } from '../activitySidebarModel';

const now = Date.parse('2026-10-07T16:00:00Z');
const iso = (at: number) => new Date(at).toISOString();
const thread = (id: string, at = now): ChatHistoryThread => ({ id, title: id, created_at: iso(at), updated_at: iso(at) });
const task = (id: string, status: ScheduledTask['status'] = 'active'): ScheduledTask => ({
  id, title: id, source_thread_id: 'source', prompt: 'fixture', rule: { kind: 'daily', local_time: '09:00', time_zone: 'Asia/Shanghai' },
  next_run_at: null, status, revision: 3, created_at: iso(now), updated_at: iso(now - 120000),
});
const trigger = (id: string, taskId: string, status: ScheduledTrigger['status'], at = now - 120000): ScheduledTrigger => ({
  id, task_id: taskId, title: taskId, kind: 'scheduled', scheduled_at: iso(at), definition_revision: 3, source_thread_id: 'source',
  time_zone: 'Asia/Shanghai', status, task_session_id: null, target_thread_id: null, input_message_id: null, target_turn_id: null,
  final_message_id: null, error_code: null, skipped_from_at: null, skipped_through_at: null, created_at: iso(at), updated_at: iso(at),
});
const dream = (id: string, lifecycle: StoryWorkspaceDreamReentryItem['lifecycle'], at = now - 60000): StoryWorkspaceDreamReentryItem => ({
  storyWorkspaceRunId: id, displayTitle: id, goalPrefix: 'fixture', deckId: 'fixture-deck', deckDisplayName: 'Fixture', workflowDisplayName: 'Dream',
  deckPluginVersion: 'fixture', lifecycle, outcome: ['running', 'recent'].includes(lifecycle) ? 'in_progress' : 'initial', group: lifecycle === 'recent' ? 'recent' : 'in_progress', stageRevisions: {}, confirmationAccepted: ['running', 'recent'].includes(lifecycle),
  confirmationDispatched: lifecycle === 'recent', lastActivityAt: iso(at), createdAt: iso(at), sortKey: 'server-order', href: ['running', 'recent'].includes(lifecycle) ? `/story-workspace/runs/${id}/execution` : `/story-workspace/dream?run=${id}`,
});
const base = { now, chats: [], dreams: [], scheduled: null, stale: { scheduled: false, chat: false, dream: false }, filters: { ...DEFAULT_ACTIVITY_FILTERS } };

test('the requested window includes exactly five minutes and rejects old, invalid and future values across midnight', () => {
  expect(isRecentActivity(iso(now - ACTIVITY_SIDEBAR_POLICY.recentWindowMs), now)).toBe(true);
  expect(isRecentActivity(iso(now - ACTIVITY_SIDEBAR_POLICY.recentWindowMs - 1), now)).toBe(false);
  expect(isRecentActivity(iso(now + 1), now)).toBe(false);
  expect(isRecentActivity('invalid', now)).toBe(false);
  expect(activityTimestamp('2026-10-07 15:59:00')).toBe(now - 60000);
  expect(activityLocalDay(now - 1, 'Asia/Shanghai')).toBe('2026-10-07');
  expect(activityLocalDay(now, 'Asia/Shanghai')).toBe('2026-10-08');
  expect(buildActivityRows({ ...base, chats: [thread('before-midnight', now - 1000)] })).toHaveLength(1);
});

test('descending Chat batches stop only at a valid old record or empty response and preserve the raw batch size', () => {
  const first = [thread('future', now + 1), { ...thread('invalid'), updated_at: 'invalid' }, ...Array.from({ length: 70 }, (_, index) => thread(String(index), now - index))];
  expect(recentChatBatch(first, now).rows).toHaveLength(70);
  expect(recentChatBatch(first, now).stop).toBe(false);
  const final = [thread('boundary', now - 300000), thread('old', now - 300001)];
  expect(recentChatBatch(final, now).rows.map((row) => row.id)).toEqual(['boundary']);
  expect(recentChatBatch(final, now).stop).toBe(true);
  expect(recentChatBatch([], now).stop).toBe(true);
  expect(first).toHaveLength(72);
  expect(deduplicateActivityThreads([thread('same', now - 2), thread('same'), thread('other')]).find((row) => row.id === 'same')?.updated_at).toBe(iso(now));
});

test('today task definitions and all triggers merge by task ID, prioritize running, and never invent an orphan snapshot', () => {
  const rows = scheduledActivityRows({ tasks: [task('one'), task('deleted', 'deleted'), task('deleted-running', 'deleted')], triggers: [
    trigger('old-running', 'one', 'running', now - 200000), trigger('latest-done', 'one', 'succeeded', now),
    trigger('running', 'deleted-running', 'running'), trigger('orphan', 'orphan-task', 'failed'),
  ] }, false);
  expect(rows).toHaveLength(3);
  expect(rows.find((row) => row.id === 'one')).toMatchObject({ priority: 0, state: 'running', activityAt: now });
  expect(rows.find((row) => row.id === 'orphan-task')).toMatchObject({ snapshot: null, title: 'orphan-task' });
  expect(rows.find((row) => row.id === 'one')?.snapshot).toMatchObject({ revision: 3 });
});

test('real task running is first, Dream business stages are second, remaining rows use time and stable source IDs', () => {
  const rows = buildActivityRows({ ...base, chats: [thread('shared'), thread('a')], dreams: [dream('shared', 'running'), dream('waiting', 'waiting_confirmation', now)],
    scheduled: { tasks: [task('enabled')], triggers: [trigger('run', 'active-task', 'running', now - 200000)] } });
  expect(rows.map((row) => row.key)).toEqual(['scheduled:active-task', 'dream:shared', 'chat:a', 'chat:shared', 'dream:waiting', 'scheduled:enabled']);
  expect(rows.find((row) => row.source === 'chat')?.state).toBeNull();
  expect(rows.filter((row) => row.id === 'shared')).toHaveLength(2);
});

test('failed source snapshots keep valid rows but old task/Dream states leave the current execution levels', () => {
  const rows = buildActivityRows({ ...base, stale: { scheduled: true, chat: true, dream: true }, chats: [thread('valid'), thread('expired', now - 300001)],
    dreams: [dream('stage', 'generating')], scheduled: { tasks: [], triggers: [trigger('running', 'task', 'running')] } });
  expect(rows.map((row) => row.key)).toEqual(['chat:valid', 'dream:stage', 'scheduled:task']);
  expect(rows.every((row) => row.priority === 2 && row.stale)).toBe(true);
});

test('display choices only project priority and leave caller-owned history and server Dream order intact', () => {
  const chats = [thread('one')]; const dreams = [dream('b', 'generating'), dream('a', 'generating')];
  expect(buildActivityRows({ ...base, chats, dreams, filters: { ...DEFAULT_ACTIVITY_FILTERS, chat: false } }).map((row) => row.source)).toEqual(['dream', 'dream']);
  expect(buildActivityRows({ ...base, chats, dreams, filters: { ...DEFAULT_ACTIVITY_FILTERS, priority: false } })).toEqual([]);
  expect(dreams.map((row) => row.storyWorkspaceRunId)).toEqual(['b', 'a']);
  expect(chats).toHaveLength(1);
});
