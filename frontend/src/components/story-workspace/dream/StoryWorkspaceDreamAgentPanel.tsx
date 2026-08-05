// [Input] Safe Dream Agent message view model for the current run.
// [Output] Inline Dream workbench panel hosted by the Dream editor rail.
// [Pos] Dream route-only expanded Agent interaction; never a generic Chat view.

import { useEffect, useRef, useState } from 'react';
import {
  storyWorkspaceNewDreamAgentIdempotencyKey,
  type StoryWorkspaceDreamAgentViewModel,
} from '../../../hooks/story-workspace';
import { StoryWorkspaceDreamToolConfirmation } from './StoryWorkspaceDreamToolConfirmation';
import { useStoryWorkspaceDreamAgentScroll } from './useStoryWorkspaceDreamAgentScroll';

export const STORY_WORKSPACE_DREAM_AGENT_PANEL_ID = 'story-workspace-dream-agent-panel';

export interface StoryWorkspaceDreamAgentPanelProps {
  readonly agent: StoryWorkspaceDreamAgentViewModel;
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly restoreFocusRef: React.RefObject<HTMLElement | null>;
}

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
  const [announcedStreamText, setAnnouncedStreamText] = useState('');
  const pendingKeyRef = useRef<string | null>(null);
  const inputHint = storyWorkspaceDreamAgentPanelHint(agent);
  const { markRead, snapshot, streamText } = agent;
  const canSend = Boolean(agent.snapshot?.canSend && draft.trim() && !agent.isSending);
  const {
    bottomRef,
    handleHistoryScroll,
    historyRef,
    scrollToLatest,
    showScrollToLatest,
  } = useStoryWorkspaceDreamAgentScroll({
    enabled: isOpen,
    messageCount: snapshot?.messages.length ?? 0,
    streamText,
  });

  useEffect(() => {
    if (isOpen) markRead();
  }, [isOpen, markRead, snapshot?.messages, streamText]);

  useEffect(() => {
    const timer = setTimeout(() => setAnnouncedStreamText(streamText), 500);
    return () => clearTimeout(timer);
  }, [streamText]);

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
    >
      <header>
        <div>
          <p>Dream Agent</p>
          <strong>当前 Dream 对话</strong>
        </div>
        <button onClick={closePanel} type="button">收起</button>
      </header>
      <div className="story-workspace-dream-agent-panel__history-shell">
        <div className="story-workspace-dream-agent-panel__history" onScroll={handleHistoryScroll} ref={historyRef}>
          {agent.snapshot?.messages.map((message) => (
            <article className={`story-workspace-dream-agent-panel__message story-workspace-dream-agent-panel__message--${message.role}`} key={message.id}>
              <small>{message.role === 'assistant' ? 'Dream Agent' : '你'}</small>
              <p>{message.text}{message.truncated ? '…' : ''}</p>
            </article>
          ))}
          {agent.streamText && (
            <article className="story-workspace-dream-agent-panel__message story-workspace-dream-agent-panel__message--assistant">
              <small>Dream Agent 正在输出</small><p>{agent.streamText}</p>
            </article>
          )}
          {!agent.snapshot?.messages.length && !agent.streamText && <p className="story-workspace-dream-agent-panel__empty">正在准备可展示的 Dream Agent 消息。</p>}
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
      <p className="story-workspace-dream-agent-panel__announcement" aria-atomic="false" aria-live="polite">{announcedStreamText}</p>
      {agent.pendingToolConfirmation ? (
        <StoryWorkspaceDreamToolConfirmation
          confirmation={agent.pendingToolConfirmation}
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
