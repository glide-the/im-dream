/* eslint-disable react-refresh/only-export-components -- R3 exports a deterministic menu split seam. */
// [Input] Safe Dream Agent view model, not generic Chat messages or transport.
// [Output] Floating Dream workbench extension with focus-safe input and history.
// [Pos] Dream Agent dialog (design_008 §8/§15).

import { useEffect, useId, useRef, useState } from 'react';
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
  readonly workflowActions: readonly StoryWorkspaceDreamAgentWorkflowActionViewModel[];
  readonly onRequestWorkflowAction: (identity: string) => void;
  readonly onClose: () => void;
  readonly restoreFocusRef: React.RefObject<HTMLButtonElement | null>;
}

export interface StoryWorkspaceDreamAgentWorkflowActionViewModel {
  readonly id: string;
  readonly label: string;
  readonly displayCommand: string;
  readonly isCurrent: boolean;
  readonly canDispatch: boolean;
  readonly pending: boolean;
  readonly disabledReason: string | null;
}

export function storyWorkspaceSplitDreamAgentWorkflowActions(
  actions: readonly StoryWorkspaceDreamAgentWorkflowActionViewModel[],
): {
  readonly direct: readonly StoryWorkspaceDreamAgentWorkflowActionViewModel[];
  readonly overflow: readonly StoryWorkspaceDreamAgentWorkflowActionViewModel[];
} {
  return { direct: actions.slice(0, 2), overflow: actions.slice(2) };
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

function storyWorkspaceDreamAgentVisibleFocusables(root: HTMLElement | null): readonly HTMLElement[] {
  if (root === null) return [];
  const candidates = root.querySelectorAll<HTMLElement>(
    'button:not(:disabled):not([tabindex="-1"]), input:not(:disabled):not([tabindex="-1"]), select:not(:disabled):not([tabindex="-1"]), textarea:not(:disabled):not([tabindex="-1"]), [tabindex]:not([tabindex="-1"])',
  );
  return Array.from(candidates).filter((element) => {
    if (element.matches(':disabled')) return false;
    if (element.closest('[hidden], [inert], [aria-hidden="true"]') !== null) return false;
    const style = window.getComputedStyle(element);
    return style.display !== 'none'
      && style.visibility !== 'hidden'
      && style.visibility !== 'collapse'
      && element.getClientRects().length > 0;
  });
}

export function StoryWorkspaceDreamAgentDialog({
  agent, deckName, runId, workflowActions, onRequestWorkflowAction, onClose, restoreFocusRef,
}: StoryWorkspaceDreamAgentDialogProps) {
  const [draft, setDraft] = useState('');
  const [isNarrow, setIsNarrow] = useState(false);
  const [workflowOverflowOpen, setWorkflowOverflowOpen] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const pendingKeyRef = useRef<string | null>(null);
  const workflowOverflowId = useId();
  const workflowOverflowTriggerRef = useRef<HTMLButtonElement>(null);
  const inputHint = storyWorkspaceDreamAgentInputHint(agent);
  const status = storyWorkspaceDreamAgentDialogStatus(agent);
  const { markRead, snapshot, streamText } = agent;
  const contentRevision = storyWorkspaceDreamAgentContentRevision(agent.streamContent);
  const announcement = useStoryWorkspaceDreamAgentAnnouncement({
    streamContent: agent.streamContent,
    streamText: agent.streamText,
  });
  const canSend = Boolean(agent.snapshot?.canSend && draft.trim() && !agent.isSending);
  const workflowActionGroups = storyWorkspaceSplitDreamAgentWorkflowActions(workflowActions);
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
  }, [agent.pendingToolConfirmation, snapshot?.canSend]);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 767px)');
    const syncNarrow = () => setIsNarrow(media.matches);
    syncNarrow();
    media.addEventListener('change', syncNarrow);
    return () => media.removeEventListener('change', syncNarrow);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        if (workflowOverflowOpen) {
          setWorkflowOverflowOpen(false);
          requestAnimationFrame(() => workflowOverflowTriggerRef.current?.focus());
        } else {
          onClose();
        }
        return;
      }
      if (event.key !== 'Tab' || !window.matchMedia('(max-width: 767px)').matches) return;
      const focusable = storyWorkspaceDreamAgentVisibleFocusables(dialogRef.current);
      if (focusable.length === 0) return;
      const currentIndex = focusable.indexOf(document.activeElement as HTMLElement);
      const nextIndex = storyWorkspaceDreamAgentFocusCycleIndex(currentIndex, focusable.length, event.shiftKey);
      if (nextIndex !== currentIndex) { event.preventDefault(); focusable[nextIndex]?.focus(); }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose, workflowOverflowOpen]);

  useEffect(() => {
    if (workflowActionGroups.overflow.length === 0) setWorkflowOverflowOpen(false);
  }, [workflowActionGroups.overflow.length]);

  useEffect(() => () => {
    requestAnimationFrame(() => restoreFocusRef.current?.focus());
  }, [restoreFocusRef]);

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

  const workflowActionButton = (
    action: StoryWorkspaceDreamAgentWorkflowActionViewModel,
  ) => {
    const agentBusy = !agent.snapshot?.canSend || agent.isSending;
    const disabled = !action.canDispatch || action.pending || agentBusy;
    const disabledReason = action.pending
      ? '已交给 Dream Agent，等待服务端事实更新'
      : agentBusy && action.canDispatch
        ? 'Dream Agent 完成本轮后可继续'
        : action.disabledReason;
    return (
      <button
        aria-current={action.isCurrent ? 'step' : undefined}
        className="story-workspace-dream-agent-dialog__workflow-action"
        disabled={disabled}
        key={action.id}
        onClick={() => onRequestWorkflowAction(action.id)}
        title={disabledReason ?? undefined}
        type="button"
      >
        <span>
          <strong>{action.label}</strong>
          <small>{action.displayCommand}</small>
        </span>
        <b>{
          action.pending
            ? '处理中'
            : action.isCurrent
              ? action.canDispatch ? '当前可执行' : '当前暂不可执行'
              : '后续，完成当前步骤后可用'
        }</b>
      </button>
    );
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
          {workflowActions.length > 0 && (
            <div
              aria-label="Episode 工作流操作"
              className="story-workspace-dream-agent-dialog__workflow-actions"
              role="group"
            >
              <p>第一集创作流程</p>
              <div>{workflowActionGroups.direct.map(workflowActionButton)}</div>
              {workflowActionGroups.overflow.length > 0 && (
                <>
                  <button
                    aria-controls={workflowOverflowId}
                    aria-expanded={workflowOverflowOpen}
                    className="story-workspace-dream-agent-dialog__workflow-disclosure"
                    onClick={() => setWorkflowOverflowOpen((open) => !open)}
                    ref={workflowOverflowTriggerRef}
                    type="button"
                  >更多工作流操作（{workflowActionGroups.overflow.length}）</button>
                  <div
                    aria-label="更多 Episode 工作流操作"
                    className="story-workspace-dream-agent-dialog__workflow-overflow"
                    hidden={!workflowOverflowOpen}
                    id={workflowOverflowId}
                    role="group"
                  >{workflowActionGroups.overflow.map(workflowActionButton)}</div>
                </>
              )}
            </div>
          )}
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
