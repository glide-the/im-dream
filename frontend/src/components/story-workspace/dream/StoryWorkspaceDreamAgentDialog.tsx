// [Input] Actor-scoped Story Workspace run and the shared Claude Agent thread.
// [Output] Dream business shell around the canonical Chat thread UI, with a
//          direct handoff to the same thread in the full Chat workspace.
// [Pos] Dream owns presentation only; it has no workflow action state machine.
// [Sync] 2026-08-13: expose an explicit full-Chat thread handoff beside close.
// [Sync] 2026-08-14: expose the Execution page's draft/sync presentation switch.

import { useEffect, useRef, useState, type RefObject } from 'react';
import { storyWorkspaceDreamAgentFocusCycleIndex } from './storyWorkspaceDreamAgentFocus';
import { StoryWorkspaceDreamThreadChat } from './StoryWorkspaceDreamThreadChat';

export type StoryWorkspaceExecutionView = 'draft' | 'sync';

export interface StoryWorkspaceDreamAgentDialogProps {
  readonly deckName: string;
  readonly runId: string;
  readonly threadId: string;
  readonly refreshNonce?: number;
  readonly expectedMessageId?: string | null;
  readonly onClose: () => void;
  readonly onOpenChatThread: (threadId: string) => void;
  readonly onWorkspaceViewChange: (view: StoryWorkspaceExecutionView) => void;
  readonly onSettled?: () => void;
  readonly restoreFocusRef: RefObject<HTMLButtonElement | null>;
  readonly workspaceView: StoryWorkspaceExecutionView;
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
  onClose,
  onOpenChatThread,
  onWorkspaceViewChange,
  onSettled,
  restoreFocusRef,
  workspaceView,
}: StoryWorkspaceDreamAgentDialogProps) {
  const [isNarrow, setIsNarrow] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

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
        onClose();
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
  }, [onClose]);

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

  const selectWorkspaceView = (view: StoryWorkspaceExecutionView) => {
    onWorkspaceViewChange(view);
    if (isNarrow) onClose();
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
        <div className="story-workspace-dream-agent-dialog__header-actions">
          <div
            aria-label="工作台视图"
            className="story-workspace-dream-agent-dialog__view-switch"
            role="group"
          >
            <button
              aria-controls="story-workspace-draft-surface"
              aria-pressed={workspaceView === 'draft'}
              onClick={() => selectWorkspaceView('draft')}
              type="button"
            >
              初稿
            </button>
            <button
              aria-controls="story-workspace-sync-surface"
              aria-pressed={workspaceView === 'sync'}
              onClick={() => selectWorkspaceView('sync')}
              type="button"
            >
              同步
            </button>
          </div>
          <button
            aria-label="在 Chat 中打开当前 thread"
            className="story-workspace-dream-agent-dialog__chat-link"
            onClick={() => onOpenChatThread(threadId)}
            title="在 Chat 中打开"
            type="button"
          >
            Chat ↗
          </button>
          <button aria-label="收起 Dream Agent" onClick={onClose} type="button">收起</button>
        </div>
      </header>
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
