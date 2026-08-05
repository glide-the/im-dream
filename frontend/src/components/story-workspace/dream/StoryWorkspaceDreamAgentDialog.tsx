// [Input] Safe Dream Agent view model, not generic Chat messages or transport.
// [Output] Floating Dream workbench extension with focus-safe input and history.
// [Pos] Dream Agent dialog (design_008 §8/§15).

import { useEffect, useRef, useState } from 'react';
import {
  storyWorkspaceNewDreamAgentIdempotencyKey,
  type StoryWorkspaceDreamAgentViewModel,
} from '../../../hooks/story-workspace';
import { storyWorkspaceDreamAgentFocusCycleIndex } from './storyWorkspaceDreamAgentFocus';
import { StoryWorkspaceDreamAgentMessageList } from './StoryWorkspaceDreamAgentMessageList';
import { StoryWorkspaceDreamToolConfirmation } from './StoryWorkspaceDreamToolConfirmation';
import {
  storyWorkspaceDreamAgentContentRevision,
  useStoryWorkspaceDreamAgentAnnouncement,
  useStoryWorkspaceDreamAgentScroll,
} from './useStoryWorkspaceDreamAgentScroll';

export interface StoryWorkspaceDreamAgentDialogProps {
  readonly agent: StoryWorkspaceDreamAgentViewModel;
  readonly deckName: string;
  readonly runId: string;
  readonly onClose: () => void;
  readonly restoreFocusRef: React.RefObject<HTMLButtonElement | null>;
}

function storyWorkspaceDreamAgentInputHint(agent: StoryWorkspaceDreamAgentViewModel): string | null {
  switch (agent.snapshot?.sendBlockReason) {
    case 'generating': return 'Dream Agent 正在完成初始创作。';
    case 'waiting_confirmation': return '请先在页面修改并确认；留言不会代替确认。';
    case 'confirming': return '正在保存本次确认。';
    case 'continuing': return 'Dream Agent 正在根据已确认内容继续。';
    case 'busy': return 'Dream Agent 正在处理上一条消息。';
    default: return null;
  }
}

function storyWorkspaceDreamAgentDialogStatus(agent: StoryWorkspaceDreamAgentViewModel) {
  if (agent.snapshot?.lifecycle === 'streaming') {
    return { icon: '◌', label: 'Dream Agent 正在执行' };
  }
  if (agent.snapshot?.canSend) {
    return { icon: '✓', label: 'Dream Agent 已完成本轮输出' };
  }
  return { icon: '◇', label: storyWorkspaceDreamAgentInputHint(agent) ?? 'Dream Agent 正在准备内容' };
}

export function StoryWorkspaceDreamAgentDialog({
  agent, deckName, runId, onClose, restoreFocusRef,
}: StoryWorkspaceDreamAgentDialogProps) {
  const [draft, setDraft] = useState('');
  const [isNarrow, setIsNarrow] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const pendingKeyRef = useRef<string | null>(null);
  const inputHint = storyWorkspaceDreamAgentInputHint(agent);
  const status = storyWorkspaceDreamAgentDialogStatus(agent);
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
    messageCount: snapshot?.messages.length ?? 0,
    streamText,
  });

  useEffect(() => {
    if (agent.pendingToolConfirmation) {
      dialogRef.current?.querySelector<HTMLElement>(
        '.story-workspace-dream-tool-confirmation button:not(:disabled), .story-workspace-dream-tool-confirmation input:not(:disabled), .story-workspace-dream-tool-confirmation select:not(:disabled), .story-workspace-dream-tool-confirmation textarea:not(:disabled)',
      )?.focus();
    } else if (!snapshot?.canSend) headingRef.current?.focus();
    else inputRef.current?.focus();
    const media = window.matchMedia('(max-width: 767px)');
    const syncNarrow = () => setIsNarrow(media.matches);
    syncNarrow();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); return; }
      if (event.key !== 'Tab' || !media.matches) return;
      const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]',
      );
      if (!focusable?.length) return;
      const currentIndex = Array.from(focusable).indexOf(document.activeElement as HTMLElement);
      const nextIndex = storyWorkspaceDreamAgentFocusCycleIndex(currentIndex, focusable.length, event.shiftKey);
      if (nextIndex !== currentIndex) { event.preventDefault(); focusable[nextIndex]?.focus(); }
    };
    document.addEventListener('keydown', onKeyDown);
    media.addEventListener('change', syncNarrow);
    return () => { document.removeEventListener('keydown', onKeyDown); media.removeEventListener('change', syncNarrow); };
  }, [agent.pendingToolConfirmation, onClose, snapshot?.canSend]);

  useEffect(() => () => { restoreFocusRef.current?.focus(); }, [restoreFocusRef]);

  useEffect(() => {
    markRead();
  }, [markRead, snapshot?.messages, streamText]);

  useEffect(() => {
    if (!isNarrow) return undefined;
    const previousOverflow = document.body.style.overflow;
    const background: Array<{
      element: HTMLElement;
      previousAriaHidden: string | null;
      previousInert: boolean;
    }> = [];
    let branch: HTMLElement | null = dialogRef.current;
    while (branch?.parentElement && branch.parentElement !== document.body) {
      const parent: HTMLElement = branch.parentElement;
      for (const sibling of Array.from(parent.children)) {
        if (!(sibling instanceof HTMLElement) || sibling === branch) continue;
        background.push({
          element: sibling,
          previousAriaHidden: sibling.getAttribute('aria-hidden'),
          previousInert: sibling.inert,
        });
        sibling.inert = true;
        sibling.setAttribute('aria-hidden', 'true');
      }
      branch = parent;
    }
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
      for (const { element, previousAriaHidden, previousInert } of background) {
        element.inert = previousInert;
        if (previousAriaHidden === null) element.removeAttribute('aria-hidden');
        else element.setAttribute('aria-hidden', previousAriaHidden);
      }
    };
  }, [isNarrow]);

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
    <div
      aria-labelledby="story-workspace-dream-agent-dialog-title"
      aria-modal={isNarrow}
      className="story-workspace-dream-agent-dialog"
      id="story-workspace-dream-agent-dialog"
      ref={dialogRef}
      role="dialog"
    >
      <header className="story-workspace-dream-agent-dialog__header">
        <div>
          <p>Dream Agent</p>
          <h2 id="story-workspace-dream-agent-dialog-title" ref={headingRef} tabIndex={-1}>Dream Agent</h2>
          <span>{deckName} · Run …{runId.slice(-6)}</span>
          <p className="story-workspace-dream-agent-dialog__status" role="status">
            <b aria-hidden="true">{status.icon}</b>{status.label}
          </p>
        </div>
        <button aria-label="收起 Dream Agent" onClick={onClose} type="button">收起</button>
      </header>
      <div className="story-workspace-dream-agent-dialog__history-shell">
        <div className="story-workspace-dream-agent-dialog__history" onScroll={handleHistoryScroll} ref={historyRef}>
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
      <p className="story-workspace-dream-agent-dialog__stream-announcement" aria-atomic="false" aria-live="polite">{announcement}</p>
      {agent.pendingToolConfirmation ? (
        <StoryWorkspaceDreamToolConfirmation
          confirmation={agent.pendingToolConfirmation}
          errorMessage={agent.error ? '本次确认尚未提交，请检查连接后再试。' : null}
          isResolving={agent.isConfirmingTool}
          onResolve={agent.confirmTool}
        />
      ) : (
        <form className="story-workspace-dream-agent-dialog__composer" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
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
              ref={inputRef}
              rows={3}
              value={draft}
            />
          </label>
          <button disabled={!canSend} type="submit">{agent.isSending ? '发送中…' : '发送'}</button>
        </form>
      )}
    </div>
  );
}
