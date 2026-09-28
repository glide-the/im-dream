// [Input] An owned task Thread id and the shared Chat Thread hydration/runtime endpoints.
// [Output] Right-side independent ChatPanel with persisted history and live reconnect.
// [Pos] Task-session side-chat surface; reuses the same ChatPanel and transport.
// [Sync] 2026-09-27: forward persisted task-relation navigation through the owning Chat surface.
// [Sync] 2026-09-27: open a selected queued message as a separate top-level Chat Thread.
'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ChatPanel, { type ChatPanelRecoverySnapshot } from './ChatPanel';
import { hydrateClaudeThreadSession, type ClaudeThreadHydrationSnapshot } from './threadSessionHydration';
import { IconX } from './Icons';

export default function TaskSessionSidebar({ threadId, onClose, onOpenTaskThread, onNavigateThread }: { threadId: string; onClose: () => void; onOpenTaskThread: (threadId: string) => void; onNavigateThread: (threadId: string) => void }) {
  const { t } = useTranslation();
  const [snapshot, setSnapshot] = useState<ClaudeThreadHydrationSnapshot | null>(null);
  const [error, setError] = useState(false);
  const [reconnectNonce, setReconnectNonce] = useState(0);
  const recover = useCallback(async (): Promise<ChatPanelRecoverySnapshot> => {
    const next = await hydrateClaudeThreadSession(threadId);
    setSnapshot(next);
    setError(false);
    return {
      messages: next.messages,
      settledToolCallIds: next.settledToolCallIds,
      runtimePendingToolCallIds: next.runtimePendingToolCallIds,
      running: next.running,
      toolConfirmationKnown: next.status?.tool_confirmation_observation === 'known',
      historyPage: { nextCursor: next.nextCursor, hasMore: next.hasMore, latestMessageId: next.latestMessageId },
    };
  }, [threadId]);
  useEffect(() => {
    let active = true;
    let connected = false;
    setSnapshot(null);
    setError(false);
    const load = async () => {
      try {
        const next = await hydrateClaudeThreadSession(threadId);
        if (!active) return;
        setSnapshot(next);
        setError(false);
        if (next.running && !connected) {
          connected = true;
          setReconnectNonce((value) => value + 1);
        }
      } catch { if (active) setError(true); }
    };
    void load();
    const timer = window.setInterval(() => { if (active && !connected) void load(); }, 2000);
    return () => { active = false; window.clearInterval(timer); };
  }, [threadId]);
  return (
    <aside aria-label={t('chat.inputQueue.sideChat')} style={{ width: 'min(42vw, 38rem)', minWidth: 'min(23rem, 90vw)', maxWidth: '90vw', height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column', flexShrink: 0, borderLeft: '1px solid var(--color-border-paper)', background: 'var(--color-bg-app)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', minHeight: '3.5rem', padding: '0.5rem 1rem', borderBottom: '1px solid var(--color-border-paper)' }}>
        <strong style={{ overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{snapshot?.thread?.title ?? t('chat.inputQueue.sideChat')}</strong>
        <button type="button" onClick={onClose} aria-label={t('chat.inputQueue.closeSideChat')} style={{ border: 0, background: 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer' }}><IconX style={{ width: '1.2rem', height: '1.2rem' }} /></button>
      </div>
      {snapshot ? <ChatPanel
        key={`${threadId}-${snapshot.messages.length}`}
        threadId={threadId}
        initialMessages={snapshot.messages}
        initialRuntimeRunning={snapshot.running}
        initialSettledToolCallIds={snapshot.settledToolCallIds}
        initialRuntimePendingToolCallIds={snapshot.runtimePendingToolCallIds}
        initialToolConfirmationKnown={snapshot.status?.tool_confirmation_observation === 'known'}
        initialHistoryPage={{ nextCursor: snapshot.nextCursor, hasMore: snapshot.hasMore, latestMessageId: snapshot.latestMessageId }}
        reconnectStreamNonce={reconnectNonce}
        onReconnectComplete={recover}
        onOpenTaskThread={onOpenTaskThread}
        onNavigateThread={onNavigateThread}
        deckId={snapshot.thread?.deck_id ?? undefined}
        voiceId={snapshot.thread?.voice_id ?? undefined}
        className="task-session-side-chat"
      /> : <div role={error ? 'alert' : 'status'} style={{ padding: '1rem', color: 'var(--color-text-secondary)' }}>
        {error ? <button type="button" onClick={() => void recover()}>{t('chat.historyTurn.retry')}</button> : t('chat.historyTurn.loading')}
      </div>}
    </aside>
  );
}
