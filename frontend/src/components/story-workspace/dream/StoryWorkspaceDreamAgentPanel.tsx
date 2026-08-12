// [Input] Actor-scoped Dream files threadId and business-shell visibility controls.
// [Output] Inline Dream rail hosting the canonical ChatPanel-first conversation.
// [Pos] Dream layout adapter; no Dream transport/parser/reducer lives here.

import { useEffect, useRef, type RefObject } from 'react';
import { StoryWorkspaceDreamThreadChat } from './StoryWorkspaceDreamThreadChat';

export const STORY_WORKSPACE_DREAM_AGENT_PANEL_ID = 'story-workspace-dream-agent-panel';

export interface StoryWorkspaceDreamAgentPanelProps {
  readonly threadId: string | null;
  readonly isOpen: boolean;
  readonly refreshNonce?: number;
  readonly expectedMessageId?: string | null;
  readonly onClose: () => void;
  readonly onSettled?: () => void;
  readonly restoreFocusRef: RefObject<HTMLElement | null>;
}

/** Expand the owned thread in place without creating a second Agent runtime. */
export function StoryWorkspaceDreamAgentPanel({
  threadId,
  isOpen,
  refreshNonce = 0,
  expectedMessageId = null,
  onClose,
  onSettled,
  restoreFocusRef,
}: StoryWorkspaceDreamAgentPanelProps) {
  const panelRef = useRef<HTMLElement>(null);
  const wasOpenRef = useRef(false);

  useEffect(() => {
    if (isOpen && !wasOpenRef.current) {
      requestAnimationFrame(() => {
        panelRef.current?.querySelector<HTMLElement>('textarea, button, [tabindex="0"]')?.focus();
      });
    }
    wasOpenRef.current = isOpen;
  }, [isOpen]);

  const closePanel = () => {
    onClose();
    requestAnimationFrame(() => restoreFocusRef.current?.focus());
  };

  return (
    <section
      aria-label="Dream Agent 完整消息"
      className="story-workspace-dream-agent-panel"
      hidden={!isOpen}
      id={STORY_WORKSPACE_DREAM_AGENT_PANEL_ID}
      ref={panelRef}
    >
      <div className="story-workspace-dream-agent-panel__controls">
        <button onClick={closePanel} type="button">← 返回 Dream 内容</button>
      </div>
      {threadId ? (
        <StoryWorkspaceDreamThreadChat
          expectedMessageId={expectedMessageId}
          onSettled={onSettled}
          refreshNonce={refreshNonce}
          threadId={threadId}
        />
      ) : (
        <p className="story-workspace-dream-thread-chat__loading" role="status">
          正在读取 Agent 会话绑定…
        </p>
      )}
    </section>
  );
}
