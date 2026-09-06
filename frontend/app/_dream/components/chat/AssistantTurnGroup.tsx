// [Input] One validated historical assistant turn projection plus process, persistent-result, and final renderers.
// [Output] Accessible process disclosure that never constructs collapsed process children while keeping promoted results mounted outside it.
// [Pos] Shared turn-level view beneath ChatMessageList for Chat and Dream hosts.
// [Sync] 2026-09-02: render process detail state only after explicit expansion.
// [Sync] 2026-09-06: keep promoted MCP App results outside the collapsible process region.

import { useId, useLayoutEffect, useRef, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { IconChevronRight } from './Icons';
import { formatChatDuration } from './chatDuration';
import type { HistoricalAssistantTurnProjection } from './assistantTurnHistory';
import {
  captureChatScrollAnchor,
  restoreChatScrollAnchor,
  type ChatScrollAnchor,
} from './chatHistoryWindow';
import './AssistantTurnGroup.css';

interface AssistantTurnGroupProps {
  readonly projection: HistoricalAssistantTurnProjection;
  readonly expanded: boolean;
  readonly onExpandedChange: (turnKey: string, expanded: boolean) => void;
  readonly renderPart: (partIndex: number, kind: 'process' | 'final') => ReactNode;
  readonly renderDeferredProcess?: () => ReactNode;
  readonly renderOutsideProcess?: () => ReactNode;
}

export default function AssistantTurnGroup({
  projection,
  expanded,
  onExpandedChange,
  renderPart,
  renderDeferredProcess,
  renderOutsideProcess,
}: AssistantTurnGroupProps) {
  const { t, i18n } = useTranslation();
  const processRegionId = useId();
  const toggleRef = useRef<HTMLButtonElement>(null);
  const pendingAnchorRef = useRef<ChatScrollAnchor | null>(null);
  const duration = formatChatDuration(projection.durationMs, i18n.language);
  const displayLabel = duration
    ? t('chat.historyTurn.duration', { duration })
    : t('chat.historyTurn.viewProcess');
  const ariaLabel = t(
    expanded
      ? duration ? 'chat.historyTurn.collapseAria' : 'chat.historyTurn.collapseAriaNoDuration'
      : duration ? 'chat.historyTurn.expandAria' : 'chat.historyTurn.expandAriaNoDuration',
    { label: displayLabel },
  );

  const toggle = () => {
    const button = toggleRef.current;
    const scroller = button?.closest<HTMLElement>('[data-chat-scroll-region="messages"]');
    if (button && scroller) {
      pendingAnchorRef.current = captureChatScrollAnchor(scroller, button);
    }
    onExpandedChange(projection.turnKey, !expanded);
  };

  useLayoutEffect(() => {
    const anchor = pendingAnchorRef.current;
    const button = toggleRef.current;
    if (!anchor || !button) return;
    restoreChatScrollAnchor(anchor);
    if (!expanded || !projection.deferredProcess) {
      pendingAnchorRef.current = null;
    }
  }, [expanded, projection.deferredProcess]);

  return (
    <section
      className="chat-assistant-turn"
      data-chat-assistant-turn={projection.turnKey}
    >
      <button
        ref={toggleRef}
        type="button"
        className="chat-assistant-turn__toggle"
        aria-expanded={expanded}
        aria-controls={processRegionId}
        aria-label={ariaLabel}
        onClick={toggle}
      >
        <span className="chat-assistant-turn__label">{displayLabel}</span>
        <IconChevronRight
          className="chat-assistant-turn__chevron"
          aria-hidden="true"
        />
      </button>

      {expanded ? (
        <div
          id={processRegionId}
          className="chat-assistant-turn__process"
          data-turn-process={projection.turnKey}
        >
          {projection.deferredProcess
            ? renderDeferredProcess?.()
            : projection.processPartIndexes.map((partIndex) => (
              renderPart(partIndex, 'process')
            ))}
        </div>
      ) : null}

      {renderOutsideProcess ? (
        <div
          className="chat-assistant-turn__outside-process"
          data-turn-outside-process={projection.turnKey}
        >
          {renderOutsideProcess()}
        </div>
      ) : null}

      <div className="chat-assistant-turn__final" data-turn-final={projection.turnKey}>
        {renderPart(projection.finalPartIndex, 'final')}
      </div>
    </section>
  );
}
