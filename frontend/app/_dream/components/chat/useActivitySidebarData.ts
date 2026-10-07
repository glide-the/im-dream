// [Input] Chat activity open state and existing authenticated public read APIs.
// [Output] Independently recoverable recent Chat, today's tasks and Dream snapshots with one visible-session clock.
// [Pos] Chat-local read coordinator; original Dream landing hook and Agent send/recovery lifecycle remain separate.
// [Sync] 2026-10-07: stop activity timers/reads on close, hidden page or unmount and reject stale sequences/day responses.

import { useCallback, useEffect, useRef, useState } from 'react';
import { listChatThreads, type ChatHistoryThread } from '../../api/chatHistoryApi';
import { getScheduledDay } from '../../api/scheduledTaskApi';
import { storyWorkspaceFetchDreamRuns } from '../../api/storyWorkspaceApi';
import type { StoryWorkspaceDreamReentryItem } from '../../hooks/story-workspace/contracts';
import { ACTIVITY_SIDEBAR_POLICY, activityLocalDay, deduplicateActivityThreads, recentChatBatch,
  type ActivitySource, type ScheduledDayData } from './activitySidebarModel';

export interface ActivityReadState<T> {
  data: T;
  isLoading: boolean;
  error: Error | null;
  hasSuccess: boolean;
}
const initialRead = <T,>(data: T): ActivityReadState<T> => ({ data, isLoading: false, error: null, hasSuccess: false });
const readError = (reason: unknown) => reason instanceof Error ? reason : new Error('Activity read unavailable');

export function useActivitySidebarData(open: boolean) {
  const [now, setNow] = useState(Date.now);
  const [visible, setVisible] = useState(() => typeof document === 'undefined' || document.visibilityState !== 'hidden');
  const [chat, setChat] = useState(() => initialRead<ChatHistoryThread[]>([]));
  const [scheduled, setScheduled] = useState(() => initialRead<ScheduledDayData | null>(null));
  const [scheduledDay, setScheduledDay] = useState<string | null>(null);
  const [dream, setDream] = useState(() => initialRead<readonly StoryWorkspaceDreamReentryItem[]>([]));
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  // Reopening after midnight must not reuse a frozen clock to label yesterday's task cache as today.
  const displayNow = activeClock(open && visible, now);
  const day = activityLocalDay(displayNow, timeZone);
  const session = useRef(0);
  const sequences = useRef<Record<ActivitySource, number>>({ chat: 0, scheduled: 0, dream: 0 });
  const controllers = useRef<Partial<Record<ActivitySource, AbortController>>>({});
  const reading = useRef<Partial<Record<ActivitySource, boolean>>>({});
  const currentDay = useRef(day);
  const deletedThreads = useRef(new Set<string>());
  const active = open && visible;
  const activeRef = useRef(active);
  activeRef.current = active;
  currentDay.current = day;

  useEffect(() => {
    const onVisibility = () => setVisible(document.visibilityState !== 'hidden');
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, []);

  const read = useCallback((source: ActivitySource, force = true) => {
    if (!activeRef.current || (!force && reading.current[source])) return;
    controllers.current[source]?.abort();
    const controller = new AbortController();
    controllers.current[source] = controller;
    reading.current[source] = true;
    const sequence = ++sequences.current[source];
    const readSession = session.current;
    const readNow = Date.now();
    const readDay = activityLocalDay(readNow, timeZone);
    const valid = () => activeRef.current && !controller.signal.aborted && session.current === readSession
      && sequences.current[source] === sequence && (source !== 'scheduled' || currentDay.current === readDay);
    const begin = <T,>(previous: ActivityReadState<T>) => ({ ...previous, isLoading: true });
    if (source === 'chat') setChat(begin);
    if (source === 'scheduled') setScheduled(begin);
    if (source === 'dream') setDream(begin);
    void (async () => {
      let partial: ChatHistoryThread[] = [];
      try {
        if (source === 'chat') {
          let offset = 0;
          while (valid()) {
            const batch = await listChatThreads({ limit: ACTIVITY_SIDEBAR_POLICY.chatPageSize, offset }, { signal: controller.signal });
            if (!valid()) return;
            const result = recentChatBatch(batch, readNow);
            partial = deduplicateActivityThreads([...partial, ...result.rows]).filter((row) => !deletedThreads.current.has(row.id));
            offset += batch.length;
            if (result.stop) {
              setChat({ data: partial, isLoading: false, error: null, hasSuccess: true });
              break;
            }
            setChat((previous) => ({ ...previous, data: deduplicateActivityThreads([...previous.data, ...partial]) }));
          }
        } else if (source === 'scheduled') {
          const data = await getScheduledDay(readDay, timeZone, { signal: controller.signal });
          if (valid()) { setScheduledDay(readDay); setScheduled({ data, isLoading: false, error: null, hasSuccess: true }); }
        } else {
          const data = await storyWorkspaceFetchDreamRuns({ signal: controller.signal });
          if (valid()) setDream({ data: data.runs, isLoading: false, error: null, hasSuccess: true });
        }
      } catch (reason) {
        if (!valid()) return;
        const error = readError(reason);
        if (source === 'chat') setChat((previous) => ({ ...previous,
          data: deduplicateActivityThreads([...previous.data, ...partial]).filter((row) => !deletedThreads.current.has(row.id)), isLoading: false, error }));
        if (source === 'scheduled') setScheduled((previous) => ({ ...previous, isLoading: false, error }));
        if (source === 'dream') setDream((previous) => ({ ...previous, isLoading: false, error }));
      } finally {
        if (sequences.current[source] === sequence) reading.current[source] = false;
      }
    })();
  }, [timeZone]);

  useEffect(() => {
    const ownedSequences = sequences.current;
    const ownedControllers = controllers.current;
    const ownedReading = reading.current;
    session.current += 1;
    if (!active) return;
    setNow(Date.now());
    for (const source of ['chat', 'scheduled', 'dream'] as const) read(source);
    const clockTimer = window.setInterval(() => setNow(Date.now()), ACTIVITY_SIDEBAR_POLICY.clockIntervalMs);
    const refreshTimer = window.setInterval(() => {
      for (const source of ['chat', 'scheduled', 'dream'] as const) read(source, false);
    }, ACTIVITY_SIDEBAR_POLICY.refreshIntervalMs);
    return () => {
      session.current += 1;
      window.clearInterval(clockTimer);
      window.clearInterval(refreshTimer);
      for (const source of ['chat', 'scheduled', 'dream'] as const) {
        ownedSequences[source] += 1;
        ownedControllers[source]?.abort();
        ownedReading[source] = false;
      }
    };
  }, [active, read]);

  const previousDay = useRef(day);
  useEffect(() => {
    if (previousDay.current === day) return;
    previousDay.current = day;
    // Yesterday's task snapshot cannot be represented as today's tasks; the continuous recent window remains intact.
    setScheduled(initialRead(null));
    setScheduledDay(null);
    if (active) read('scheduled');
  }, [active, day, read]);

  const refresh = useCallback(() => {
    setNow(Date.now());
    for (const source of ['chat', 'scheduled', 'dream'] as const) read(source);
  }, [read]);
  const removeChat = useCallback((id: string) => {
    deletedThreads.current.add(id);
    setChat((previous) => ({ ...previous, data: previous.data.filter((row) => row.id !== id) }));
  }, []);
  const displayScheduled = scheduledDay === day ? scheduled : { ...scheduled, data: null, hasSuccess: false };
  return { now: displayNow, day, chat, scheduled: displayScheduled, dream, active, refresh, retry: read, removeChat };
}

function activeClock(active: boolean, lastTick: number): number {
  return active ? Math.max(lastTick, Date.now()) : lastTick;
}
