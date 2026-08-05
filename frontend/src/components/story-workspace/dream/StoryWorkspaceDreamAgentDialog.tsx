// [Input] Safe Dream Agent view model, not generic Chat messages or transport.
// [Output] Floating Dream workbench extension with focus-safe input and history.
// [Pos] Dream Agent dialog (design_008 §8/§15).

import { useEffect, useRef, useState } from 'react';
import {
  storyWorkspaceNewDreamAgentIdempotencyKey,
  type StoryWorkspaceDreamAgentViewModel,
} from '../../../hooks/story-workspace';
import { storyWorkspaceDreamAgentFocusCycleIndex } from './storyWorkspaceDreamAgentFocus';

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
  const canSend = Boolean(agent.snapshot?.canSend && draft.trim() && !agent.isSending);

  useEffect(() => {
    const disabled = !snapshot?.canSend;
    if (disabled) headingRef.current?.focus();
    else inputRef.current?.focus();
    const media = window.matchMedia('(max-width: 767px)');
    const syncNarrow = () => setIsNarrow(media.matches);
    syncNarrow();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); return; }
      if (event.key !== 'Tab' || !media.matches) return;
      const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), textarea:not(:disabled), [tabindex]',
      );
      if (!focusable?.length) return;
      const currentIndex = Array.from(focusable).indexOf(document.activeElement as HTMLElement);
      const nextIndex = storyWorkspaceDreamAgentFocusCycleIndex(currentIndex, focusable.length, event.shiftKey);
      if (nextIndex !== currentIndex) { event.preventDefault(); focusable[nextIndex]?.focus(); }
    };
    document.addEventListener('keydown', onKeyDown);
    media.addEventListener('change', syncNarrow);
    return () => { document.removeEventListener('keydown', onKeyDown); media.removeEventListener('change', syncNarrow); };
  }, [onClose, snapshot?.canSend]);

  useEffect(() => () => { restoreFocusRef.current?.focus(); }, [restoreFocusRef]);

  useEffect(() => {
    markRead();
  }, [markRead, snapshot?.messages, streamText]);

  useEffect(() => {
    if (!isNarrow) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previousOverflow; };
  }, [isNarrow]);

  const [announcedStreamText, setAnnouncedStreamText] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => setAnnouncedStreamText(streamText), 500);
    return () => clearTimeout(timer);
  }, [streamText]);

  const submit = async () => {
    if (!canSend) return;
    if (!pendingKeyRef.current) pendingKeyRef.current = storyWorkspaceNewDreamAgentIdempotencyKey();
    const accepted = await agent.send(draft, pendingKeyRef.current);
    if (accepted) { setDraft(''); pendingKeyRef.current = null; }
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
      <div className="story-workspace-dream-agent-dialog__history">
        {agent.snapshot?.messages.map((message) => (
          <article className={`story-workspace-dream-agent-dialog__message story-workspace-dream-agent-dialog__message--${message.role}`} key={message.id}>
            <small>{message.role === 'assistant' ? 'Dream Agent' : '你'}</small>
            <p>{message.text}{message.truncated ? '…' : ''}</p>
          </article>
        ))}
        {agent.streamText && (
          <article className="story-workspace-dream-agent-dialog__message story-workspace-dream-agent-dialog__message--assistant">
            <small>Dream Agent 正在输出</small><p>{agent.streamText}</p>
          </article>
        )}
        {!agent.snapshot?.messages.length && !agent.streamText && <p className="story-workspace-dream-agent-dialog__empty">正在准备可展示的 Dream Agent 消息。</p>}
      </div>
      <p className="story-workspace-dream-agent-dialog__stream-announcement" aria-atomic="false" aria-live="polite">{announcedStreamText}</p>
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
    </div>
  );
}
