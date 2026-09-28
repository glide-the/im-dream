// [Input] Current Thread's owner-scoped turn index, reading position, and locate actions.
// [Output] Left message-tick rail with a hover/focus summary and a narrow-column list.
// [Pos] Read-only navigation beside ChatPanel's existing message scroll region.
// [Sync] 2026-09-29: animate a compact proximity-based tick rail and keep its preview beside the hovered row.

import { useEffect, useId, useRef, useState, type FocusEvent, type MouseEvent } from 'react';
import { useTranslation } from 'react-i18next';
import type { ChatTurnNavigationItem } from './chatTurnNavigationModel';
import './TurnNavigation.css';

interface TurnNavigationProps {
  items: readonly ChatTurnNavigationItem[];
  activeMessageId: string | null;
  loadingIndex: boolean;
  partialIndex: boolean;
  locatingMessageId: string | null;
  failedMessageId: string | null;
  onNavigate: (messageId: string) => void;
  onRetryIndex: () => void;
}

export default function TurnNavigation({
  items,
  activeMessageId,
  loadingIndex,
  partialIndex,
  locatingMessageId,
  failedMessageId,
  onNavigate,
  onRetryIndex,
}: TurnNavigationProps) {
  const { t } = useTranslation();
  const navRef = useRef<HTMLElement>(null);
  const ticksRef = useRef<HTMLDivElement>(null);
  const mobileToggleRef = useRef<HTMLButtonElement>(null);
  const mobileListId = useId();
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [hoverTop, setHoverTop] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const activeIndex = items.findIndex((item) => item.messageId === activeMessageId);
  const hoveredIndex = items.findIndex((item) => item.messageId === hoveredId);
  const emphasisIndex = hoveredIndex >= 0 ? hoveredIndex : activeIndex;
  const hovered = hoveredIndex >= 0 ? items[hoveredIndex] : null;

  useEffect(() => {
    if (failedMessageId) setMobileOpen(true);
  }, [failedMessageId]);

  useEffect(() => {
    const rail = ticksRef.current;
    const button = rail?.children[activeIndex] as HTMLElement | undefined;
    if (!rail || !button) return;
    const top = button.offsetTop;
    if (top < rail.scrollTop) rail.scrollTop = top;
    else if (top + button.offsetHeight > rail.scrollTop + rail.clientHeight) {
      rail.scrollTop = top + button.offsetHeight - rail.clientHeight;
    }
  }, [activeIndex, items.length]);

  if (items.length === 0) return null;

  const showItem = (item: ChatTurnNavigationItem, event: MouseEvent<HTMLButtonElement> | FocusEvent<HTMLButtonElement>) => {
    const nav = navRef.current;
    const rect = event.currentTarget.getBoundingClientRect();
    const navRect = nav?.getBoundingClientRect();
    setHoverTop(Math.max(4, Math.min(rect.top - (navRect?.top ?? 0) - 24, (nav?.clientHeight ?? 128) - 128)));
    setHoveredId(item.messageId);
  };
  const statusLabel = (item: ChatTurnNavigationItem) => t(`chat.turnNavigation.status.${item.status}`);
  const userPreview = (item: ChatTurnNavigationItem) => item.userPreview
    || t(item.hasAttachment ? 'chat.turnNavigation.attachment' : 'chat.turnNavigation.emptyInput');
  const selectItem = (messageId: string) => {
    setMobileOpen(false);
    onNavigate(messageId);
  };

  return (
    <nav
      ref={navRef}
      className="chat-turn-navigation"
      aria-label={t('chat.turnNavigation.label')}
      onMouseLeave={() => setHoveredId(null)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setHoveredId(null);
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          setHoveredId(null);
          if (mobileOpen) mobileToggleRef.current?.focus();
          setMobileOpen(false);
        }
      }}
    >
      <div className="chat-turn-navigation__desktop">
        <div ref={ticksRef} className="chat-turn-navigation__ticks" onScroll={() => setHoveredId(null)}>
          {items.map((item, index) => (
            <button
              key={item.messageId}
              type="button"
              className="chat-turn-navigation__tick"
              data-proximity={emphasisIndex < 0 ? 4 : Math.min(Math.abs(index - emphasisIndex), 4)}
              aria-label={t('chat.turnNavigation.itemAria', { index: index + 1, preview: userPreview(item) })}
              aria-current={activeMessageId === item.messageId ? 'location' : undefined}
              aria-describedby={hoveredId === item.messageId ? 'chat-turn-navigation-preview' : undefined}
              onMouseEnter={(event) => showItem(item, event)}
              onFocus={(event) => showItem(item, event)}
              onClick={() => selectItem(item.messageId)}
            >
              <span aria-hidden="true" className="chat-turn-navigation__mark" />
            </button>
          ))}
        </div>
        {hovered ? (
          <div
            key={hovered.messageId}
            id="chat-turn-navigation-preview"
            className="chat-turn-navigation__preview"
            style={{ top: hoverTop }}
            role="group"
            aria-label={t('chat.turnNavigation.summary')}
          >
            <strong className="chat-turn-navigation__user">{userPreview(hovered)}</strong>
            {hovered.status !== 'answered' ? (
              <span className="chat-turn-navigation__status">{statusLabel(hovered)}</span>
            ) : null}
            {hovered.assistantPreview ? (
              <span className="chat-turn-navigation__answer">{hovered.assistantPreview}</span>
            ) : null}
            {locatingMessageId === hovered.messageId ? (
              <span role="status">{t('chat.turnNavigation.locating')}</span>
            ) : null}
            {failedMessageId === hovered.messageId ? (
              <span className="chat-turn-navigation__error" role="alert">
                {t('chat.turnNavigation.locateFailed')}
                <button type="button" onClick={() => onNavigate(hovered.messageId)}>
                  {t('chat.historyTurn.retry')}
                </button>
              </span>
            ) : null}
          </div>
        ) : null}
        {partialIndex ? (
          <button
            type="button"
            className="chat-turn-navigation__coverage"
            title={t('chat.turnNavigation.partial')}
            aria-label={t('chat.turnNavigation.retryIndex')}
            onClick={onRetryIndex}
          >
            {loadingIndex ? '…' : '!'}
          </button>
        ) : null}
      </div>
      <div className="chat-turn-navigation__mobile">
        <button
          ref={mobileToggleRef}
          type="button"
          className="chat-turn-navigation__mobile-toggle"
          aria-expanded={mobileOpen}
          aria-controls={mobileOpen ? mobileListId : undefined}
          onClick={() => setMobileOpen((open) => !open)}
        >
          {t('chat.turnNavigation.mobileTitle', { count: items.length })}
          <span aria-hidden="true">{mobileOpen ? '⌃' : '⌄'}</span>
        </button>
        {mobileOpen ? (
          <div id={mobileListId} className="chat-turn-navigation__mobile-list">
            {partialIndex ? (
              <button type="button" className="chat-turn-navigation__mobile-retry" onClick={onRetryIndex}>
                {loadingIndex ? t('chat.turnNavigation.loadingIndex') : t('chat.turnNavigation.partial')}
              </button>
            ) : null}
            {items.map((item, index) => (
              <button
                key={item.messageId}
                type="button"
                className="chat-turn-navigation__mobile-item"
                aria-current={activeMessageId === item.messageId ? 'location' : undefined}
                onClick={() => selectItem(item.messageId)}
              >
                <span className="chat-turn-navigation__mobile-number">{index + 1}</span>
                <span className="chat-turn-navigation__mobile-copy">
                  <strong>{userPreview(item)}</strong>
                  <span>{item.assistantPreview || statusLabel(item)}</span>
                  {locatingMessageId === item.messageId ? <span role="status">{t('chat.turnNavigation.locating')}</span> : null}
                  {failedMessageId === item.messageId ? <span role="alert">{t('chat.turnNavigation.locateFailed')}</span> : null}
                </span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </nav>
  );
}
