// [Input] Safe Dream Agent message view model for the current run.
// [Output] Inline Dream workbench panel hosted by the Dream editor rail.
// [Pos] Dream route-only expanded Agent interaction; never a generic Chat view.

import { useEffect, useRef, useState } from 'react';
import {
  storyWorkspaceNewDreamAgentIdempotencyKey,
  type StoryWorkspaceDreamAgentViewModel,
} from '../../../hooks/story-workspace';
import { StoryWorkspaceDreamAgentMessageList } from './StoryWorkspaceDreamAgentMessageList';
import { StoryWorkspaceDreamToolConfirmation } from './StoryWorkspaceDreamToolConfirmation';
import {
  storyWorkspaceDreamAgentContentRevision,
  useStoryWorkspaceDreamAgentAnnouncement,
  useStoryWorkspaceDreamAgentScroll,
} from './useStoryWorkspaceDreamAgentScroll';
import {
  storyWorkspaceDreamAgentPanelFocusTarget,
  type StoryWorkspaceDreamAgentPanelFocusZone,
} from './storyWorkspaceDreamAgentFocus';

export const STORY_WORKSPACE_DREAM_AGENT_PANEL_ID = 'story-workspace-dream-agent-panel';

export interface StoryWorkspaceDreamAgentPanelProps {
  readonly agent: StoryWorkspaceDreamAgentViewModel;
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly restoreFocusRef: React.RefObject<HTMLElement | null>;
}

const STORY_WORKSPACE_DREAM_CONFIRMATION_FOCUSABLE = [
  '.story-workspace-dream-tool-confirmation button:not(:disabled)',
  '.story-workspace-dream-tool-confirmation input:not(:disabled)',
  '.story-workspace-dream-tool-confirmation select:not(:disabled)',
  '.story-workspace-dream-tool-confirmation textarea:not(:disabled)',
].join(', ');

function storyWorkspaceDreamAgentPanelHint(agent: StoryWorkspaceDreamAgentViewModel): string | null {
  switch (agent.snapshot?.sendBlockReason) {
    case 'generating': return 'Dream Agent 正在完成初始创作。';
    case 'waiting_confirmation': return '请先在页面修改并确认；留言不会代替确认。';
    case 'confirming': return '正在保存本次确认。';
    case 'continuing': return 'Dream Agent 正在根据已确认内容继续。';
    case 'busy': return 'Dream Agent 正在处理上一条消息。';
    default: return null;
  }
}

/** Expand the current Dream Agent in place without changing page or run ownership. */
export function StoryWorkspaceDreamAgentPanel({ agent, isOpen, onClose, restoreFocusRef }: StoryWorkspaceDreamAgentPanelProps) {
  const [draft, setDraft] = useState('');
  const pendingKeyRef = useRef<string | null>(null);
  const panelRef = useRef<HTMLElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const previousToolCallIdRef = useRef<string | null>(null);
  const wasOpenRef = useRef(false);
  const lastFocusedZoneRef = useRef<StoryWorkspaceDreamAgentPanelFocusZone>('outside');
  const inputHint = storyWorkspaceDreamAgentPanelHint(agent);
  const pendingToolCallId = agent.pendingToolConfirmation?.toolCallId ?? null;
  const composerCanReceiveFocus = Boolean(agent.snapshot?.canSend && !agent.isSending);
  const { markRead, snapshot, streamText } = agent;
  const contentRevision = storyWorkspaceDreamAgentContentRevision(agent.streamContent);
  const announcement = useStoryWorkspaceDreamAgentAnnouncement({
    streamContent: agent.streamContent,
    streamText: agent.streamText,
  });
  const canSend = Boolean(agent.snapshot?.canSend && draft.trim() && !agent.isSending);
  const {
    bottomRef,
    handleHistoryScroll,
    historyRef,
    scrollToLatest,
    showScrollToLatest,
  } = useStoryWorkspaceDreamAgentScroll({
    contentRevision,
    enabled: isOpen,
    messageCount: snapshot?.messages.length ?? 0,
    streamText,
  });

  useEffect(() => {
    if (isOpen) markRead();
  }, [isOpen, markRead, snapshot?.messages, streamText]);

  useEffect(() => {
    const previousToolCallId = previousToolCallIdRef.current;
    const focusFellOut = document.activeElement === document.body || document.activeElement === null;
    const focusTarget = storyWorkspaceDreamAgentPanelFocusTarget({
      focusFellOut,
      isOpen,
      lastFocusedZone: lastFocusedZoneRef.current,
      pendingToolCallId,
      previousToolCallId,
      wasOpen: wasOpenRef.current,
    });
    let focusFrame: number | null = null;

    let retainPreviousToolCallId = false;
    if (focusTarget === 'confirmation') {
      focusFrame = requestAnimationFrame(() => {
        panelRef.current?.querySelector<HTMLElement>(STORY_WORKSPACE_DREAM_CONFIRMATION_FOCUSABLE)?.focus();
      });
    } else if (focusTarget === 'composer') {
      if (composerCanReceiveFocus) {
        focusFrame = requestAnimationFrame(() => textareaRef.current?.focus());
      } else {
        retainPreviousToolCallId = true;
      }
    }

    if (!retainPreviousToolCallId) previousToolCallIdRef.current = pendingToolCallId;
    wasOpenRef.current = isOpen;
    return () => {
      if (focusFrame !== null) cancelAnimationFrame(focusFrame);
    };
  }, [composerCanReceiveFocus, isOpen, pendingToolCallId]);

  const captureFocusZone = (event: React.FocusEvent<HTMLElement>) => {
    const target = event.target as HTMLElement;
    if (target === textareaRef.current) {
      lastFocusedZoneRef.current = 'composer';
    } else if (target.closest('.story-workspace-dream-tool-confirmation')) {
      lastFocusedZoneRef.current = 'confirmation';
    } else if (target.closest('.story-workspace-dream-agent-panel__history')) {
      lastFocusedZoneRef.current = 'history';
    } else {
      lastFocusedZoneRef.current = 'navigation';
    }
  };

  const captureFocusExit = (event: React.FocusEvent<HTMLElement>) => {
    const next = event.relatedTarget;
    if (!next || !panelRef.current?.contains(next as Node)) {
      lastFocusedZoneRef.current = 'outside';
    }
  };

  const closePanel = () => {
    onClose();
    requestAnimationFrame(() => restoreFocusRef.current?.focus());
  };

  const submit = async () => {
    if (!canSend) return;
    if (!pendingKeyRef.current) pendingKeyRef.current = storyWorkspaceNewDreamAgentIdempotencyKey();
    const accepted = await agent.send(draft, pendingKeyRef.current);
    if (accepted) {
      setDraft('');
      pendingKeyRef.current = null;
      scrollToLatest();
    }
  };

  return (
    <section
      aria-label="Dream Agent 完整消息"
      className="story-workspace-dream-agent-panel"
      hidden={!isOpen}
      id={STORY_WORKSPACE_DREAM_AGENT_PANEL_ID}
      onBlurCapture={captureFocusExit}
      onFocusCapture={captureFocusZone}
      ref={panelRef}
    >
      <div className="story-workspace-dream-agent-panel__controls">
        <button onClick={closePanel} type="button">← 返回 Dream 内容</button>
      </div>
      <div className="story-workspace-dream-agent-panel__history-shell">
        <div
          aria-label="Dream Agent 消息历史"
          className="story-workspace-dream-agent-panel__history"
          onScroll={handleHistoryScroll}
          ref={historyRef}
          role="region"
          tabIndex={0}
        >
          <StoryWorkspaceDreamAgentMessageList
            messages={agent.snapshot?.messages ?? []}
            streamContent={agent.streamContent}
            streamText={agent.streamText}
          />
          <div aria-hidden="true" ref={bottomRef} />
        </div>
        {showScrollToLatest && (
          <button
            aria-label="前往最新消息"
            className="story-workspace-dream-agent-scroll-to-latest"
            onClick={() => scrollToLatest()}
            title="前往最新消息"
            type="button"
          >↓ <span>前往最新消息</span></button>
        )}
      </div>
      <p className="story-workspace-dream-agent-panel__announcement" aria-atomic="false" aria-live="polite">{announcement}</p>
      {agent.pendingToolConfirmation ? (
        <StoryWorkspaceDreamToolConfirmation
          confirmation={agent.pendingToolConfirmation}
          errorMessage={agent.error ? '本次确认尚未提交，请检查连接后再试。' : null}
          isResolving={agent.isConfirmingTool}
          onResolve={agent.confirmTool}
        />
      ) : (
        <form onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          {inputHint && <p role="status">{inputHint}</p>}
          {agent.error && <p role="status">正在恢复 Dream Agent 消息。</p>}
          <label>
            <span>给 Dream Agent 留言</span>
            <textarea
              aria-label="给 Dream Agent 留言"
              disabled={!agent.snapshot?.canSend || agent.isSending}
              onChange={(event) => { pendingKeyRef.current = null; setDraft(event.currentTarget.value); }}
              onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void submit(); } }}
              placeholder="写下后续创作指令…"
              ref={textareaRef}
              rows={3}
              value={draft}
            />
          </label>
          <button disabled={!canSend} type="submit">{agent.isSending ? '发送中…' : '发送'}</button>
        </form>
      )}
    </section>
  );
}
