// [Input] Actor-scoped threadId from the Dream files projection.
// [Output] Dream shell composition of the canonical ChatPanel/session contract.
// [Pos] Business-surface adapter only; owns no transport, parser, or live reducer.
// [Sync] 2026-09-02: pass the shared message-page cursor through hydration/recovery.

import { useCallback, useEffect, useRef, useState } from 'react';
import ChatPanel, {
  type ChatPanelRecoverySnapshot,
} from '../../chat/ChatPanel';
import { SubagentSidebar } from '../../chat/SubagentPanel';
import {
  claudeThreadExpectedDispatchIsTerminal,
  claudeThreadHydrationRetryDelayMs,
  hydrateClaudeThreadSession,
  type ClaudeThreadHydrationSnapshot,
} from '../../chat/threadSessionHydration';
import { chatReconnectNonceForHydratedThread } from '../../chat/chatRuntimeState';

const SCHEDULED_TURN_OBSERVATION_INTERVAL_MS = 250;

export interface StoryWorkspaceDreamThreadChatProps {
  readonly threadId: string;
  readonly refreshNonce?: number;
  readonly expectedMessageId?: string | null;
  readonly onSettled?: () => void;
}

export function StoryWorkspaceDreamThreadChat({
  threadId,
  refreshNonce = 0,
  expectedMessageId = null,
  onSettled,
}: StoryWorkspaceDreamThreadChatProps) {
  const [snapshot, setSnapshot] = useState<ClaudeThreadHydrationSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hydrationFailed, setHydrationFailed] = useState(false);
  const [manualHydrationNonce, setManualHydrationNonce] = useState(0);
  const [reconnectStreamNonce, setReconnectStreamNonce] = useState(0);
  const [terminalHistoryGeneration, setTerminalHistoryGeneration] = useState(0);
  const [subagentSidebarOpen, setSubagentSidebarOpen] = useState(false);
  const [focusedSubagentToolCallId, setFocusedSubagentToolCallId] = useState<string | null>(null);
  const generationRef = useRef(0);
  const hydratedThreadIdRef = useRef<string | null>(null);
  const settledExpectedMessageIdsRef = useRef(new Set<string>());
  const onSettledRef = useRef(onSettled);
  onSettledRef.current = onSettled;

  const notifySettled = useCallback(() => {
    if (expectedMessageId) {
      if (settledExpectedMessageIdsRef.current.has(expectedMessageId)) return;
      settledExpectedMessageIdsRef.current.add(expectedMessageId);
    }
    onSettledRef.current?.();
  }, [expectedMessageId]);

  const hydrate = useCallback(async (): Promise<ClaudeThreadHydrationSnapshot | undefined> => {
    const generation = generationRef.current;
    let next: ClaudeThreadHydrationSnapshot;
    try {
      next = await hydrateClaudeThreadSession(threadId);
    } catch {
      return undefined;
    }
    if (generation !== generationRef.current) return undefined;
    setSnapshot(next);
    setIsLoading(false);
    setHydrationFailed(false);
    return next;
  }, [threadId]);

  useEffect(() => {
    generationRef.current += 1;
    const threadChanged = hydratedThreadIdRef.current !== threadId;
    hydratedThreadIdRef.current = threadId;
    if (threadChanged) setSnapshot(null);
    setIsLoading(true);
    setHydrationFailed(false);
    setSubagentSidebarOpen(false);
    setFocusedSubagentToolCallId(null);
    const generation = generationRef.current;
    let observationTimer: number | null = null;
    let reconnectClaimed = false;
    let hydrationAttempt = 0;

    const schedule = (task: () => void) => {
      observationTimer = window.setTimeout(
        task,
        claudeThreadHydrationRetryDelayMs(hydrationAttempt),
      );
      hydrationAttempt += 1;
    };

    const applyInitial = (next: ClaudeThreadHydrationSnapshot) => {
      if (generation !== generationRef.current) return;
      setHydrationFailed(false);
      setSnapshot(next);
      if (expectedMessageId === null) setIsLoading(false);
      if (next.running) {
        reconnectClaimed = true;
        setIsLoading(false);
        setReconnectStreamNonce((value) => value + 1);
        return;
      }
      if (claudeThreadExpectedDispatchIsTerminal(next, expectedMessageId)) {
        setIsLoading(false);
        setTerminalHistoryGeneration((value) => value + 1);
        notifySettled();
        return;
      }
      // An exact server-owned message id is the only proof that a business
      // command is still awaiting dispatch. refreshNonce merely requests a
      // fresh hydration; a historical non-zero nonce must never manufacture a
      // second scheduled turn after the parent clears expectedMessageId.
      if (expectedMessageId === null) return;
      const observeScheduledTurn = async () => {
        let observed: ClaudeThreadHydrationSnapshot;
        try {
          observed = await hydrateClaudeThreadSession(threadId);
          hydrationAttempt = 0;
        } catch {
          if (generation === generationRef.current && !reconnectClaimed) {
            schedule(() => void observeScheduledTurn());
          }
          return;
        }
        if (generation !== generationRef.current || reconnectClaimed) return;
        setSnapshot(observed);
        if (observed.running === true) {
          reconnectClaimed = true;
          setIsLoading(false);
          setReconnectStreamNonce((value) => value + 1);
          return;
        }
        if (claudeThreadExpectedDispatchIsTerminal(observed, expectedMessageId)) {
          setIsLoading(false);
          setTerminalHistoryGeneration((value) => value + 1);
          notifySettled();
          return;
        }
        observationTimer = window.setTimeout(
          () => void observeScheduledTurn(),
          SCHEDULED_TURN_OBSERVATION_INTERVAL_MS,
        );
      };
      observationTimer = window.setTimeout(
        () => void observeScheduledTurn(),
        SCHEDULED_TURN_OBSERVATION_INTERVAL_MS,
      );
    };

    const loadInitial = async () => {
      try {
        const next = await hydrateClaudeThreadSession(threadId);
        hydrationAttempt = 0;
        applyInitial(next);
      } catch {
        if (generation === generationRef.current) {
          setHydrationFailed(true);
          schedule(() => void loadInitial());
        }
      }
    };
    void loadInitial();
    return () => {
      generationRef.current += 1;
      if (observationTimer !== null) window.clearTimeout(observationTimer);
    };
  }, [expectedMessageId, hydrate, manualHydrationNonce, notifySettled, refreshNonce, threadId]);

  const recover = useCallback(async (): Promise<ChatPanelRecoverySnapshot | undefined> => {
    const next = await hydrate();
    if (!next) return undefined;
    return {
      messages: next.messages,
      settledToolCallIds: next.settledToolCallIds,
      runtimePendingToolCallIds: next.runtimePendingToolCallIds,
      running: next.running,
      historyPage: {
        nextCursor: next.nextCursor,
        hasMore: next.hasMore,
        latestMessageId: next.latestMessageId,
      },
      toolConfirmationKnown: next.status?.tool_confirmation_observation === 'known',
    };
  }, [hydrate]);

  if (snapshot === null) {
    return hydrationFailed ? (
      <div className="story-workspace-dream-thread-chat__loading" role="alert">
        <p>历史消息加载失败。</p>
        <button type="button" onClick={() => setManualHydrationNonce((value) => value + 1)}>重试</button>
      </div>
    ) : <p className="story-workspace-dream-thread-chat__loading" role="status">正在读取同一 Agent 会话…</p>;
  }

  return (
    <div className="story-workspace-dream-thread-chat" data-thread-id={threadId}>
      <ChatPanel
        key={`${threadId}:${terminalHistoryGeneration}`}
        threadId={threadId}
        initialMessages={snapshot.messages}
        initialRuntimePendingToolCallIds={snapshot.runtimePendingToolCallIds}
        initialRuntimeRunning={snapshot.running}
        initialSettledToolCallIds={snapshot.settledToolCallIds}
        initialToolConfirmationKnown={snapshot.status?.tool_confirmation_observation === 'known'}
        initialHistoryPage={{
          nextCursor: snapshot.nextCursor,
          hasMore: snapshot.hasMore,
          latestMessageId: snapshot.latestMessageId,
        }}
        inputPlaceholder="给 Dream Agent 留言…"
        isLoading={isLoading}
        onConversationSettled={notifySettled}
        onOpenSubagentTask={(toolCallId) => {
          setFocusedSubagentToolCallId(toolCallId);
          setSubagentSidebarOpen(true);
        }}
        onReconnectComplete={recover}
        reconnectStreamNonce={chatReconnectNonceForHydratedThread(
          snapshot.running,
          reconnectStreamNonce,
        )}
      />
      <SubagentSidebar
        focusToolCallId={focusedSubagentToolCallId}
        onClose={() => setSubagentSidebarOpen(false)}
        open={subagentSidebarOpen}
        threadId={threadId}
      />
    </div>
  );
}
