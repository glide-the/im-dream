// [Input] Dream Agent message/stream changes and a Dream-owned scroll container.
// [Output] Near-bottom following state plus an explicit latest-message action.
// [Pos] Shared Dream Agent Panel/Dialog scrolling; independent from generic Chat UI.

import { useCallback, useEffect, useRef, useState, type UIEvent } from 'react';

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
  readonly enabled?: boolean;
  readonly messageCount: number;
  readonly streamText: string;
}

/** Follow new safe Dream messages only while the reader remains near the end. */
export function useStoryWorkspaceDreamAgentScroll({
  enabled = true,
  messageCount,
  streamText,
}: StoryWorkspaceDreamAgentScrollOptions) {
  const historyRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const [showScrollToLatest, setShowScrollToLatest] = useState(false);

  const updateScrollPosition = useCallback((element: HTMLDivElement) => {
    const position = storyWorkspaceDreamAgentScrollPosition(element);
    isNearBottomRef.current = position.isNearBottom;
    setShowScrollToLatest(position.isScrollable && !position.isNearBottom);
  }, []);

  const handleHistoryScroll = useCallback((event: UIEvent<HTMLDivElement>) => {
    updateScrollPosition(event.currentTarget);
  }, [updateScrollPosition]);

  const scrollToLatest = useCallback(() => {
    const element = historyRef.current;
    if (!element) return;
    isNearBottomRef.current = true;
    setShowScrollToLatest(false);
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
      return;
    }
    element.scrollTo({ behavior: 'smooth', top: element.scrollHeight });
  }, []);

  useEffect(() => {
    const element = historyRef.current;
    if (!enabled || !element) {
      isNearBottomRef.current = true;
      setShowScrollToLatest(false);
      return undefined;
    }
    if (isNearBottomRef.current) {
      setShowScrollToLatest(false);
      const frameId = requestAnimationFrame(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      });
      return () => cancelAnimationFrame(frameId);
    }
    const frameId = requestAnimationFrame(() => updateScrollPosition(element));
    return () => cancelAnimationFrame(frameId);
  }, [enabled, messageCount, streamText, updateScrollPosition]);

  return {
    bottomRef,
    handleHistoryScroll,
    historyRef,
    scrollToLatest,
    showScrollToLatest,
  } as const;
}
