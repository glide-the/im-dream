// [Input] Dream Agent message/stream changes and a Dream-owned scroll container.
// [Output] Near-bottom following state plus an explicit latest-message action.
// [Pos] Shared Dream Agent Panel/Dialog scrolling; independent from generic Chat UI.

import { useCallback, useEffect, useRef, useState, type UIEvent } from 'react';
import type {
  StoryWorkspaceDreamAgentContent,
  StoryWorkspaceDreamAgentActivityContent,
} from '../../../hooks/story-workspace/contracts';

export const STORY_WORKSPACE_DREAM_AGENT_BOTTOM_PROXIMITY_PX = 120;

export interface StoryWorkspaceDreamAgentScrollMetrics {
  readonly clientHeight: number;
  readonly scrollHeight: number;
  readonly scrollTop: number;
}

export interface StoryWorkspaceDreamAgentScrollPosition {
  readonly distanceFromBottom: number;
  readonly isNearBottom: boolean;
  readonly isScrollable: boolean;
}

export type StoryWorkspaceDreamAgentScrollUpdateMode = 'follow' | 'measure';

export function storyWorkspaceDreamAgentScrollUpdateMode(
  forceFollow: boolean,
  isNearBottom: boolean,
): StoryWorkspaceDreamAgentScrollUpdateMode {
  return forceFollow || isNearBottom ? 'follow' : 'measure';
}

/** Stable render revision that changes for text deltas and same-id activity status updates. */
export function storyWorkspaceDreamAgentContentRevision(
  content: readonly StoryWorkspaceDreamAgentContent[],
): string {
  return JSON.stringify(content.map((part) => part.kind === 'text'
    ? ['text', part.text, part.truncated]
    : ['activity', part.id, part.status]));
}

const STORY_WORKSPACE_DREAM_AGENT_ACTIVITY_STATUS_LABEL = {
  running: '进行中',
  completed: '已完成',
  stopped: '已停止',
} as const;

export interface StoryWorkspaceDreamAgentActivityAnnouncement {
  readonly key: string;
  readonly text: string;
}

/** Return only a newly added or status-changed safe activity, never private runtime data. */
export function storyWorkspaceDreamAgentNextActivityAnnouncement(
  previous: readonly StoryWorkspaceDreamAgentContent[],
  current: readonly StoryWorkspaceDreamAgentContent[],
): StoryWorkspaceDreamAgentActivityAnnouncement | null {
  const previousStatuses = new Map(previous.flatMap((part) => part.kind === 'activity'
    ? [[part.id, part.status] as const]
    : []));
  let changed: StoryWorkspaceDreamAgentActivityContent | null = null;
  for (const part of current) {
    if (part.kind === 'activity' && previousStatuses.get(part.id) !== part.status) {
      changed = part;
    }
  }
  if (!changed) return null;
  return {
    key: `${changed.id}:${changed.status}`,
    text: `${changed.label}，${STORY_WORKSPACE_DREAM_AGENT_ACTIVITY_STATUS_LABEL[changed.status]}`,
  };
}

export interface StoryWorkspaceDreamAgentAnnouncementOptions {
  readonly streamContent: readonly StoryWorkspaceDreamAgentContent[];
  readonly streamText: string;
}

/** Debounce safe activity/text updates into one quiet polite live-region string. */
export function useStoryWorkspaceDreamAgentAnnouncement({
  streamContent,
  streamText,
}: StoryWorkspaceDreamAgentAnnouncementOptions): string {
  const [announcement, setAnnouncement] = useState('');
  const previousContentRef = useRef<readonly StoryWorkspaceDreamAgentContent[]>([]);
  const pendingActivityRef = useRef<StoryWorkspaceDreamAgentActivityAnnouncement | null>(null);
  const lastAnnouncedKeyRef = useRef<string | null>(null);

  useEffect(() => {
    const activityAnnouncement = storyWorkspaceDreamAgentNextActivityAnnouncement(
      previousContentRef.current,
      streamContent,
    );
    previousContentRef.current = streamContent;
    if (activityAnnouncement) pendingActivityRef.current = activityAnnouncement;

    const pendingActivity = pendingActivityRef.current;
    const nextAnnouncement = pendingActivity?.text ?? streamText;
    const nextKey = pendingActivity?.key ?? (streamText ? `text:${streamText}` : null);
    if (!nextKey || !nextAnnouncement) {
      pendingActivityRef.current = null;
      lastAnnouncedKeyRef.current = null;
      setAnnouncement('');
      return undefined;
    }
    if (lastAnnouncedKeyRef.current === nextKey) return undefined;

    const timer = setTimeout(() => {
      lastAnnouncedKeyRef.current = nextKey;
      if (pendingActivityRef.current?.key === nextKey) pendingActivityRef.current = null;
      setAnnouncement(nextAnnouncement);
    }, 500);
    return () => clearTimeout(timer);
  }, [streamContent, streamText]);

  return announcement;
}

export function storyWorkspaceDreamAgentScrollBehavior(
  prefersReducedMotion: boolean,
): ScrollBehavior {
  return prefersReducedMotion ? 'auto' : 'smooth';
}

function storyWorkspaceDreamAgentPrefersReducedMotion(): boolean {
  return typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function storyWorkspaceDreamAgentScrollPosition(
  metrics: StoryWorkspaceDreamAgentScrollMetrics,
): StoryWorkspaceDreamAgentScrollPosition {
  const distanceFromBottom = metrics.scrollHeight - metrics.scrollTop - metrics.clientHeight;
  return {
    distanceFromBottom,
    isNearBottom: distanceFromBottom < STORY_WORKSPACE_DREAM_AGENT_BOTTOM_PROXIMITY_PX,
    isScrollable: metrics.scrollHeight - metrics.clientHeight > STORY_WORKSPACE_DREAM_AGENT_BOTTOM_PROXIMITY_PX,
  };
}

export interface StoryWorkspaceDreamAgentScrollOptions {
  readonly contentRevision: string;
  readonly enabled?: boolean;
  readonly messageCount: number;
  readonly streamText: string;
}

/** Follow new safe Dream messages only while the reader remains near the end. */
export function useStoryWorkspaceDreamAgentScroll({
  contentRevision,
  enabled = true,
  messageCount,
  streamText,
}: StoryWorkspaceDreamAgentScrollOptions) {
  const historyRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const forceFollowRef = useRef(false);
  const [showScrollToLatest, setShowScrollToLatest] = useState(false);

  const updateScrollPosition = useCallback((element: HTMLDivElement) => {
    const position = storyWorkspaceDreamAgentScrollPosition(element);
    if (forceFollowRef.current && position.isNearBottom) {
      forceFollowRef.current = false;
    }
    if (!forceFollowRef.current) {
      isNearBottomRef.current = position.isNearBottom;
    }
    setShowScrollToLatest(
      !forceFollowRef.current && position.isScrollable && !position.isNearBottom,
    );
  }, []);

  const handleHistoryScroll = useCallback((event: UIEvent<HTMLDivElement>) => {
    updateScrollPosition(event.currentTarget);
  }, [updateScrollPosition]);

  const scrollHistoryToLatest = useCallback(() => {
    const element = historyRef.current;
    if (!element) return;
    element.scrollTo({
      behavior: storyWorkspaceDreamAgentScrollBehavior(
        storyWorkspaceDreamAgentPrefersReducedMotion(),
      ),
      top: element.scrollHeight,
    });
  }, []);

  const scrollToLatest = useCallback(() => {
    if (!historyRef.current) return;
    forceFollowRef.current = true;
    isNearBottomRef.current = true;
    setShowScrollToLatest(false);
    scrollHistoryToLatest();
  }, [scrollHistoryToLatest]);

  useEffect(() => {
    const element = historyRef.current;
    if (!enabled || !element) {
      forceFollowRef.current = false;
      isNearBottomRef.current = true;
      setShowScrollToLatest(false);
      return undefined;
    }
    const updateMode = storyWorkspaceDreamAgentScrollUpdateMode(
      forceFollowRef.current,
      isNearBottomRef.current,
    );
    if (updateMode === 'follow') {
      setShowScrollToLatest(false);
      const frameId = requestAnimationFrame(() => {
        scrollHistoryToLatest();
      });
      return () => cancelAnimationFrame(frameId);
    }
    const frameId = requestAnimationFrame(() => updateScrollPosition(element));
    return () => cancelAnimationFrame(frameId);
  }, [enabled, contentRevision, messageCount, scrollHistoryToLatest, streamText, updateScrollPosition]);

  return {
    bottomRef,
    handleHistoryScroll,
    historyRef,
    scrollToLatest,
    showScrollToLatest,
  } as const;
}
