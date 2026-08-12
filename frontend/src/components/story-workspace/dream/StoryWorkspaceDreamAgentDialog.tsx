/* eslint-disable react-refresh/only-export-components -- deterministic workflow action seam. */
// [Input] Actor-scoped threadId plus independent Episode business actions.
// [Output] Dream dialog composing canonical ChatPanel and workflow controls.
// [Pos] Dream business shell; it owns no Agent transport/parser/reducer/state machine.

import { useEffect, useId, useRef, useState, type RefObject } from 'react';
import { storyWorkspaceDreamAgentFocusCycleIndex } from './storyWorkspaceDreamAgentFocus';
import { StoryWorkspaceDreamThreadChat } from './StoryWorkspaceDreamThreadChat';

export interface StoryWorkspaceDreamAgentDialogProps {
  readonly deckName: string;
  readonly runId: string;
  readonly threadId: string;
  readonly refreshNonce?: number;
  readonly expectedMessageId?: string | null;
  readonly workflowActions: readonly StoryWorkspaceDreamAgentWorkflowActionViewModel[];
  readonly onRequestWorkflowAction: (identity: string) => void;
  readonly onClose: () => void;
  readonly onSettled?: () => void;
  readonly restoreFocusRef: RefObject<HTMLButtonElement | null>;
  readonly initialWorkflowFocus?: {
    readonly actionId: string;
    readonly wasOverflow: boolean;
  } | null;
}

export interface StoryWorkspaceDreamAgentWorkflowActionViewModel {
  readonly id: string;
  readonly label: string;
  readonly displayCommand: string;
  readonly isCurrent: boolean;
  readonly canDispatch: boolean;
  readonly pending: boolean;
  readonly disabledReason: string | null;
  readonly availability?: 'executable' | 'preview' | 'blocked';
  readonly description?: string;
  readonly targetEpisodeLabel?: string;
  readonly isRecommended?: boolean;
}

export function storyWorkspaceSplitDreamAgentWorkflowActions(
  actions: readonly StoryWorkspaceDreamAgentWorkflowActionViewModel[],
): {
  readonly direct: readonly StoryWorkspaceDreamAgentWorkflowActionViewModel[];
  readonly overflow: readonly StoryWorkspaceDreamAgentWorkflowActionViewModel[];
} {
  return { direct: actions.slice(0, 2), overflow: actions.slice(2) };
}

function visibleFocusables(root: HTMLElement | null): readonly HTMLElement[] {
  if (root === null) return [];
  const candidates = root.querySelectorAll<HTMLElement>(
    'button:not(:disabled):not([tabindex="-1"]), input:not(:disabled):not([tabindex="-1"]), select:not(:disabled):not([tabindex="-1"]), textarea:not(:disabled):not([tabindex="-1"]), [tabindex]:not([tabindex="-1"])',
  );
  return Array.from(candidates).filter((element) => {
    if (element.closest('[hidden], [inert], [aria-hidden="true"]') !== null) return false;
    const style = window.getComputedStyle(element);
    return style.display !== 'none'
      && style.visibility !== 'hidden'
      && style.visibility !== 'collapse'
      && element.getClientRects().length > 0;
  });
}

export function StoryWorkspaceDreamAgentDialog({
  deckName,
  runId,
  threadId,
  refreshNonce = 0,
  expectedMessageId = null,
  workflowActions,
  onRequestWorkflowAction,
  onClose,
  onSettled,
  restoreFocusRef,
  initialWorkflowFocus = null,
}: StoryWorkspaceDreamAgentDialogProps) {
  const [isNarrow, setIsNarrow] = useState(false);
  const [workflowOverflowOpen, setWorkflowOverflowOpen] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const workflowOverflowId = useId();
  const workflowOverflowTriggerRef = useRef<HTMLButtonElement>(null);
  const workflowActionRefs = useRef(new Map<string, HTMLButtonElement>());
  const pendingInitialWorkflowFocusRef = useRef(initialWorkflowFocus);
  const workflowActionGroups = storyWorkspaceSplitDreamAgentWorkflowActions(workflowActions);
  const workflowActionIdentity = workflowActions.map((action) => action.id).join('\u0000');

  useEffect(() => {
    const media = window.matchMedia('(max-width: 767px)');
    const syncNarrow = () => setIsNarrow(media.matches);
    syncNarrow();
    media.addEventListener('change', syncNarrow);
    return () => media.removeEventListener('change', syncNarrow);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
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
      const focusable = visibleFocusables(dialogRef.current);
      if (focusable.length === 0) return;
      const currentIndex = focusable.indexOf(document.activeElement as HTMLElement);
      const nextIndex = storyWorkspaceDreamAgentFocusCycleIndex(
        currentIndex,
        focusable.length,
        event.shiftKey,
      );
      if (nextIndex !== currentIndex) {
        event.preventDefault();
        focusable[nextIndex]?.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose, workflowOverflowOpen]);

  useEffect(() => {
    if (workflowActionGroups.overflow.length === 0) setWorkflowOverflowOpen(false);
  }, [workflowActionGroups.overflow.length]);

  useEffect(() => {
    pendingInitialWorkflowFocusRef.current = initialWorkflowFocus;
    if (initialWorkflowFocus?.wasOverflow && workflowActionGroups.overflow.length > 0) {
      setWorkflowOverflowOpen(true);
    }
  }, [initialWorkflowFocus, workflowActionGroups.overflow.length]);

  useEffect(() => {
    const pendingFocus = pendingInitialWorkflowFocusRef.current;
    if (pendingFocus === null) return undefined;
    if (pendingFocus.wasOverflow
      && workflowActionGroups.overflow.length > 0
      && !workflowOverflowOpen) return undefined;
    pendingInitialWorkflowFocusRef.current = null;
    const frame = requestAnimationFrame(() => {
      const target = workflowActionRefs.current.get(pendingFocus.actionId);
      if (target) target.focus();
      else if (pendingFocus.wasOverflow) workflowOverflowTriggerRef.current?.focus();
      else headingRef.current?.focus();
    });
    return () => cancelAnimationFrame(frame);
  }, [workflowActionGroups.overflow.length, workflowActionIdentity, workflowOverflowOpen]);

  useEffect(() => () => {
    requestAnimationFrame(() => restoreFocusRef.current?.focus());
  }, [restoreFocusRef]);

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
      const parent = branch.parentElement;
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

  const workflowActionButton = (
    action: StoryWorkspaceDreamAgentWorkflowActionViewModel,
  ) => {
    const availability = action.availability
      ?? (action.isCurrent ? (action.canDispatch ? 'executable' : 'blocked') : 'preview');
    const isRecommended = action.isRecommended ?? action.isCurrent;
    const disabled = !action.canDispatch || action.pending;
    const disabledReason = action.pending
      ? '已交给 Dream Agent，等待服务端事实更新'
      : action.disabledReason;
    return (
      <button
        aria-current={action.isCurrent ? 'step' : undefined}
        className="story-workspace-dream-agent-dialog__workflow-action"
        disabled={disabled}
        key={action.id}
        onClick={() => onRequestWorkflowAction(action.id)}
        ref={(element) => {
          if (element === null) workflowActionRefs.current.delete(action.id);
          else workflowActionRefs.current.set(action.id, element);
        }}
        title={disabledReason ?? undefined}
        type="button"
      >
        <span>
          <strong>{action.label}</strong>
          {action.description && (
            <small className="story-workspace-dream-agent-dialog__workflow-description">
              {action.description}
            </small>
          )}
          <small className="story-workspace-dream-agent-dialog__workflow-command">
            {action.displayCommand}
          </small>
        </span>
        <b>{action.pending
          ? '处理中'
          : availability === 'executable'
            ? isRecommended ? '推荐操作 · 当前可执行' : '当前可执行'
            : availability === 'blocked' ? '暂不可用' : '未来可用'}</b>
      </button>
    );
  };

  return (
    <div
      aria-labelledby="story-workspace-dream-agent-dialog-title"
      aria-modal={isNarrow}
      className="story-workspace-dream-agent-dialog story-workspace-dream-agent-dialog--conversation"
      id="story-workspace-dream-agent-dialog"
      ref={dialogRef}
      role="dialog"
    >
      <header className="story-workspace-dream-agent-dialog__header">
        <div className="story-workspace-dream-agent-dialog__heading-copy">
          <div className="story-workspace-dream-agent-dialog__kicker">
            <p>Dream Agent</p>
            <span>{deckName} · Run …{runId.slice(-6)}</span>
          </div>
          <h2 id="story-workspace-dream-agent-dialog-title" ref={headingRef} tabIndex={-1}>
            Dream Agent
          </h2>
          <p className="story-workspace-dream-agent-dialog__status" role="status">
            与 Chat 共用同一 thread
          </p>
        </div>
        <button aria-label="收起 Dream Agent" onClick={onClose} type="button">收起</button>
      </header>
      {workflowActions.length > 0 && (
        <div
          aria-label="Episode 工作流操作"
          className="story-workspace-dream-agent-dialog__workflow-actions"
          role="group"
        >
          <p>当前与后续 Episode</p>
          <div className="story-workspace-dream-agent-dialog__workflow-primary">
            {workflowActionGroups.direct.map(workflowActionButton)}
          </div>
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
      <div className="story-workspace-dream-agent-dialog__thread-chat">
        <StoryWorkspaceDreamThreadChat
          expectedMessageId={expectedMessageId}
          onSettled={onSettled}
          refreshNonce={refreshNonce}
          threadId={threadId}
        />
      </div>
    </div>
  );
}
