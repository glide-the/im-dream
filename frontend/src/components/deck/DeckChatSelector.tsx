// [Input] Enabled Deck summaries (hydrated with voices) and the current Dream chat selection.
// [Output] Render the compact, single-select Deck control used by AIInputDock.
// [Pos] deck-domain adapter between Dream chat composition and Deck configuration.
// [Sync] 2026-08-03: popup lists each deck together with its bundled agents (prefix
//                    matching covers deck and agent names), and the popup position is
//                    computed against the browser viewport (up/down + horizontal clamp).
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Deck, Voice } from '../../api/voiceApi';
import { COLORS, iconMap } from '../deckVisuals';

interface DeckChatSelectorProps {
  decks: Deck[];
  selectedDeckId?: string;
  onChange?: (deckId: string | undefined) => void;
  loading?: boolean;
  error?: string | null;
  locked?: boolean;
}

interface DeckOption {
  id: string | undefined;
  label: string;
  deck?: Deck;
}

interface PopupLayout {
  top?: number;
  bottom?: number;
  left: number;
  width: number;
  listMaxHeight: number;
}

const VIEWPORT_MARGIN = 8;
const POPUP_WIDTH = 280;
// @@@ Approximate fixed chrome of the popup (search input + paddings + gaps).
const POPUP_CHROME = 52;

function enabledVoicesOf(deck: Deck): Voice[] {
  return (deck.voices || []).filter((voice) => voice.enabled);
}

export default function DeckChatSelector({
  decks,
  selectedDeckId,
  onChange,
  loading = false,
  error,
  locked = false,
}: DeckChatSelectorProps) {
  const { t, i18n } = useTranslation();
  const language = (i18n.language || 'en').split('-')[0];
  const deckLabel = (deck: Deck) =>
    ((language === 'zh' ? deck.name_zh : deck.name_en) || deck.name);
  const voiceLabel = (voice: Voice) =>
    ((language === 'zh' ? voice.name_zh : voice.name_en) || voice.name);
  const selectedDeck = decks.find((deck) => deck.id === selectedDeckId);
  const selectedLabel = selectedDeck
    ? deckLabel(selectedDeck)
    : t('chat.deck.none');

  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [popupLayout, setPopupLayout] = useState<PopupLayout | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // @@@ Prefix match against deck names and their bundled agent names.
  const options: DeckOption[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matched = q
      ? decks.filter((deck) => {
          const label = ((language === 'zh' ? deck.name_zh : deck.name_en) || deck.name).toLowerCase();
          if (label.startsWith(q) || deck.name.toLowerCase().startsWith(q)) return true;
          return (deck.voices || []).some((voice) => {
            const vLabel = ((language === 'zh' ? voice.name_zh : voice.name_en) || voice.name).toLowerCase();
            return vLabel.startsWith(q) || voice.name.toLowerCase().startsWith(q);
          });
        })
      : decks;
    return [
      { id: undefined, label: t('chat.deck.none') },
      ...matched.map((deck) => ({
        id: deck.id as string | undefined,
        label: (language === 'zh' ? deck.name_zh : deck.name_en) || deck.name,
        deck,
      })),
    ];
  }, [decks, query, language, t]);

  // @@@ Viewport-adaptive layout: open toward whichever side has more room and
  // clamp horizontally so the popup never leaves the browser window.
  const computeLayout = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom - VIEWPORT_MARGIN;
    const spaceAbove = rect.top - VIEWPORT_MARGIN;
    const openUp = spaceAbove > spaceBelow;
    const available = Math.max(120, (openUp ? spaceAbove : spaceBelow) - VIEWPORT_MARGIN);
    const width = Math.min(POPUP_WIDTH, window.innerWidth - VIEWPORT_MARGIN * 2);
    const left = Math.min(
      Math.max(VIEWPORT_MARGIN, rect.left),
      window.innerWidth - width - VIEWPORT_MARGIN,
    );
    setPopupLayout({
      ...(openUp
        ? { bottom: window.innerHeight - rect.top + 6 }
        : { top: rect.bottom + 6 }),
      left,
      width,
      listMaxHeight: Math.max(96, Math.min(300, available - POPUP_CHROME)),
    });
  }, []);

  // @@@ Click-outside closes the popup; scroll/resize keeps it attached to the window.
  // Scroll events from descendants (captured at the window) must not close the
  // popup — the listbox itself is scrollable.
  useEffect(() => {
    if (!isOpen) return undefined;
    const handleMouseDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleResize = () => computeLayout();
    const handleScroll = (event: Event) => {
      if (
        rootRef.current
        && event.target instanceof Node
        && rootRef.current.contains(event.target)
      ) {
        return;
      }
      setIsOpen(false);
    };
    document.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('resize', handleResize);
    window.addEventListener('scroll', handleScroll, true);
    return () => {
      document.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [isOpen, computeLayout]);

  // @@@ Keep the keyboard-active option visible while navigating.
  useEffect(() => {
    if (!isOpen) return;
    itemRefs.current.get(activeIndex)?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex, isOpen]);

  const openPopup = () => {
    setQuery('');
    setActiveIndex(0);
    computeLayout();
    setIsOpen(true);
  };

  const selectOption = (deckId: string | undefined) => {
    onChange?.(deckId);
    setIsOpen(false);
    setQuery('');
  };

  const handleSearchKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      setIsOpen(false);
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, options.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const option = options[activeIndex];
      if (option) selectOption(option.id);
    }
  };

  if (locked) {
    return (
      <div
        aria-label={t('chat.deck.lockedAria', { name: selectedLabel })}
        title={t('chat.deck.lockedTitle')}
        style={{
          display: 'inline-flex',
          minHeight: '1.8rem',
          maxWidth: '15rem',
          alignItems: 'center',
          gap: '0.42rem',
          border: '1px solid var(--color-border-paper)',
          borderRadius: '999px',
          background: 'var(--color-bg-app)',
          color: 'var(--color-text-secondary)',
          padding: '0 0.7rem',
          fontSize: '0.76rem',
          whiteSpace: 'nowrap',
        }}
      >
        <span aria-hidden="true" style={{ color: 'var(--color-text-muted)' }}>Deck</span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{selectedLabel}</span>
        <span aria-hidden="true" style={{ fontSize: '0.64rem', color: 'var(--color-text-muted)' }}>●</span>
      </div>
    );
  }

  return (
    <div ref={rootRef} style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        ref={triggerRef}
        type="button"
        aria-label={t('chat.deck.selectAria')}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        title={error || t('chat.deck.selectTitle')}
        disabled={loading}
        onClick={() => (isOpen ? setIsOpen(false) : openPopup())}
        style={{
          display: 'inline-flex',
          minHeight: '1.8rem',
          maxWidth: '15rem',
          alignItems: 'center',
          gap: '0.35rem',
          border: `1px solid ${error ? 'var(--color-state-error)' : 'var(--color-border-paper)'}`,
          borderRadius: '999px',
          background: 'var(--color-bg-app)',
          color: error ? 'var(--color-state-error)' : 'var(--color-text-secondary)',
          padding: '0 0.7rem',
          fontSize: '0.76rem',
          cursor: loading ? 'wait' : 'pointer',
          whiteSpace: 'nowrap',
        }}
      >
        <span aria-hidden="true" style={{ color: 'var(--color-text-muted)' }}>Deck</span>
        <span style={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          maxWidth: '10rem',
          color: 'var(--color-text-primary)',
        }}>
          {loading ? t('chat.deck.loading') : selectedLabel}
        </span>
        <span aria-hidden="true" style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)' }}>▾</span>
      </button>

      {isOpen && popupLayout && (
        <div
          role="listbox"
          style={{
            position: 'fixed',
            top: popupLayout.top,
            bottom: popupLayout.bottom,
            left: popupLayout.left,
            width: popupLayout.width,
            background: 'var(--color-bg-surface-solid)',
            border: '1px solid var(--color-border-neutral)',
            borderRadius: '8px',
            boxShadow: '0 4px 12px var(--color-shadow-medium)',
            padding: '6px',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            boxSizing: 'border-box',
          }}
        >
          <input
            // eslint-disable-next-line jsx-a11y/no-autofocus -- popup search should be typed into immediately
            autoFocus
            value={query}
            placeholder={t('chat.deck.searchPlaceholder')}
            aria-label={t('chat.deck.searchPlaceholder')}
            onChange={(event) => {
              setQuery(event.target.value);
              setActiveIndex(0);
            }}
            onKeyDown={handleSearchKeyDown}
            style={{
              width: '100%',
              boxSizing: 'border-box',
              border: '1px solid var(--color-border-neutral)',
              borderRadius: '6px',
              background: 'var(--color-bg-paper)',
              color: 'var(--color-text-primary)',
              padding: '6px 8px',
              fontSize: '12px',
              outline: 'none',
            }}
          />
          <div style={{
            maxHeight: popupLayout.listMaxHeight,
            overflowY: 'auto',
            overscrollBehavior: 'contain',
          }}>
            {options.map((option, idx) => {
              const isActive = idx === activeIndex;
              const isSelected = option.id === selectedDeckId;
              const agents = option.deck ? enabledVoicesOf(option.deck) : [];
              const agentCount = option.deck
                ? (option.deck.voices ? agents.length : (option.deck.voice_count ?? 0))
                : 0;
              return (
                <div
                  key={option.id ?? '__none__'}
                  role="option"
                  aria-selected={isSelected}
                  ref={(el) => {
                    if (el) {
                      itemRefs.current.set(idx, el);
                    } else {
                      itemRefs.current.delete(idx);
                    }
                  }}
                  onClick={() => selectOption(option.id)}
                  onMouseEnter={() => setActiveIndex(idx)}
                  style={{
                    padding: '7px 10px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    color: 'var(--color-text-body)',
                    background: isActive ? 'var(--color-bg-hover)' : 'transparent',
                    transition: 'background 0.15s',
                  }}
                >
                  <span
                    aria-hidden="true"
                    style={{
                      width: '14px',
                      flexShrink: 0,
                      color: 'var(--color-action-link)',
                      visibility: isSelected ? 'visible' : 'hidden',
                    }}
                  >
                    ✓
                  </span>
                  <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <span style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontStyle: option.id === undefined ? 'italic' : 'normal',
                      color: option.id === undefined ? 'var(--color-text-muted)' : undefined,
                    }}>
                      {option.label}
                    </span>
                    {option.deck && (
                      <span
                        aria-hidden="true"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px',
                          overflow: 'hidden',
                          whiteSpace: 'nowrap',
                          fontSize: '11px',
                          color: 'var(--color-text-muted)',
                        }}
                      >
                        {agents.length > 0 ? (
                          <>
                            <span style={{ display: 'inline-flex', gap: '2px', flexShrink: 0 }}>
                              {agents.slice(0, 5).map((voice) => {
                                const AgentIcon = iconMap[voice.icon as keyof typeof iconMap] || iconMap.brain;
                                const agentColor = COLORS[voice.color as keyof typeof COLORS]?.hex
                                  || 'var(--color-action-link)';
                                return <AgentIcon key={voice.id} size={11} color={agentColor} />;
                              })}
                            </span>
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {agents.slice(0, 3).map((voice) => voiceLabel(voice)).join(' · ')}
                              {agents.length > 3 ? ` · +${agents.length - 3}` : ''}
                            </span>
                          </>
                        ) : (
                          <span>{t('chat.deck.agentCount', { count: agentCount })}</span>
                        )}
                      </span>
                    )}
                  </span>
                </div>
              );
            })}
            {options.length <= 1 && query.trim() !== '' && (
              <div style={{
                padding: '8px 10px',
                fontSize: '12px',
                color: 'var(--color-text-muted)',
                fontStyle: 'italic',
              }}>
                {t('chat.deck.noMatch')}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
