// [Sync] 2026-10-13: allow analysis-specific labels and restore trigger focus after keyboard selection.
// [Input] Enabled Decks hydrated with their Agents and the current Agent selection.
// [Output] Render a Deck-grouped, Agent-selecting cascade for Chat and Dream.
// [Pos] Shared Deck -> Agent selection boundary.
// [Sync] 2026-08-05: Decks are grouping labels only; selectable values are Agents.
// [Sync] 2026-08-15: remove the unused locked presentation; historical Chat
//                    shows immutable context only in its top bar.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Deck, Voice } from '../../api/voiceApi';
import { COLORS, iconMap } from '../deckVisuals';
// [Sync] 2026-10-28: share enabled-Agent grouping and localized prefix search; preserve the Web popup and selection callbacks.
import {agentLabel as originalAgentLabel,deckLabel as originalDeckLabel,enabledAgentsOf,groupDeckAgents,type AgentGroup,type DeckAgentSelection,type DeckChatSelectorProps} from './deckAgentSelection';
export type {DeckAgentSelection} from './deckAgentSelection';

interface AgentOption extends DeckAgentSelection {
  deck: Deck;
  agent: Voice;
}

interface PopupLayout {
  top?: number;
  bottom?: number;
  left: number;
  width: number;
  listMaxHeight: number;
}

const VIEWPORT_MARGIN = 8;
const POPUP_WIDTH = 300;
const POPUP_CHROME = 52;

export default function DeckChatSelector({
  decks,
  selectedAgentId,
  onChange,
  loading = false,
  error,
  allowNone = true,
  variant = 'compact',
  noneLabel, triggerLabel, unavailableSelectionLabel,
}: DeckChatSelectorProps) {
  const { t, i18n } = useTranslation();
  const language = (i18n.language || 'en').split('-')[0];
  const deckLabel = useCallback((deck: Deck) => originalDeckLabel(deck,language), [language]);
  const agentLabel = useCallback((agent: Voice) => originalAgentLabel(agent,language), [language]);

  const selected = useMemo(() => decks
    .flatMap((deck) => enabledAgentsOf(deck).map((agent) => ({ deck, agent })))
    .find(({ agent }) => agent.id === selectedAgentId), [decks, selectedAgentId]);
  const selectedLabel = selected ? agentLabel(selected.agent)
    : selectedAgentId && unavailableSelectionLabel ? unavailableSelectionLabel : (noneLabel ?? t('chat.deck.noneAgent'));

  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [popupLayout, setPopupLayout] = useState<PopupLayout | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const groups = useMemo<AgentGroup[]>(() => groupDeckAgents(decks,query,language), [decks,query,language]);

  const options = useMemo<(AgentOption | undefined)[]>(() => [
    ...(allowNone ? [undefined] : []),
    ...groups.flatMap(({ deck, agents }) => agents.map((agent) => ({
      deck,
      agent,
      deckId: deck.id,
      agentId: agent.id,
    }))),
  ], [allowNone, groups]);

  const computeLayout = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom - VIEWPORT_MARGIN;
    const spaceAbove = rect.top - VIEWPORT_MARGIN;
    const openUp = spaceAbove > spaceBelow;
    const available = Math.max(120, (openUp ? spaceAbove : spaceBelow) - VIEWPORT_MARGIN);
    const preferredWidth = variant === 'dream' ? Math.max(POPUP_WIDTH, rect.width) : POPUP_WIDTH;
    const width = Math.min(preferredWidth, window.innerWidth - VIEWPORT_MARGIN * 2);
    const left = Math.min(
      Math.max(VIEWPORT_MARGIN, rect.left),
      window.innerWidth - width - VIEWPORT_MARGIN,
    );
    setPopupLayout({
      ...(openUp ? { bottom: window.innerHeight - rect.top + 6 } : { top: rect.bottom + 6 }),
      left,
      width,
      listMaxHeight: Math.max(96, Math.min(320, available - POPUP_CHROME)),
    });
  }, [variant]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handleMouseDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setIsOpen(false);
    };
    const handleResize = () => computeLayout();
    const handleScroll = (event: Event) => {
      if (rootRef.current && event.target instanceof Node && rootRef.current.contains(event.target)) return;
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

  useEffect(() => {
    if (isOpen) itemRefs.current.get(activeIndex)?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex, isOpen]);

  const openPopup = () => {
    setQuery('');
    const selectedIndex = options.findIndex((option) => option?.agentId === selectedAgentId);
    setActiveIndex(Math.max(0, selectedIndex));
    computeLayout();
    setIsOpen(true);
  };

  const selectOption = (option: AgentOption | undefined) => {
    onChange?.(option ? { deckId: option.deckId, agentId: option.agentId } : undefined);
    setIsOpen(false);
    setQuery('');
    triggerRef.current?.focus();
  };

  const handleSearchKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, options.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (options.length) selectOption(options[activeIndex]);
    }
  };

  const trigger = (
    <button
      ref={triggerRef}
      type="button"
      aria-label={triggerLabel ?? t('chat.deck.selectAgentAria')}
      aria-haspopup="listbox"
      aria-expanded={isOpen}
      title={error || t('chat.deck.selectAgentTitle')}
      disabled={loading}
      className={variant === 'dream' ? 'deck-agent-selector deck-agent-selector--dream' : undefined}
      onClick={() => (isOpen ? setIsOpen(false) : openPopup())}
      style={variant === 'compact' ? {
        display: 'inline-flex', minHeight: '1.8rem', maxWidth: '15rem', alignItems: 'center', gap: '0.35rem',
        border: `1px solid ${error ? 'var(--color-state-error)' : 'var(--color-border-paper)'}`,
        borderRadius: '999px', background: 'var(--color-bg-app)',
        color: error ? 'var(--color-state-error)' : 'var(--color-text-secondary)', padding: '0 0.7rem',
        fontSize: '0.76rem', cursor: loading ? 'wait' : 'pointer', whiteSpace: 'nowrap',
      } : undefined}
    >
      <span aria-hidden="true" style={{ color: 'var(--color-text-muted)' }}>{triggerLabel ?? 'Agent'}</span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '10rem', color: 'var(--color-text-primary)' }}>
        {loading ? t('chat.deck.loadingAgents') : selectedLabel}
      </span>
      <span aria-hidden="true" style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)' }}>▾</span>
    </button>
  );

  return (
    <div ref={rootRef} style={{ position: 'relative', display: variant === 'dream' ? 'block' : 'inline-flex', width: variant === 'dream' ? '100%' : undefined }}>
      {trigger}
      {isOpen && popupLayout && (
        <div role="listbox" aria-label={t('chat.deck.agentListAria')} style={{
          position: 'fixed', top: popupLayout.top, bottom: popupLayout.bottom, left: popupLayout.left,
          width: popupLayout.width, background: 'var(--color-bg-surface-solid)', border: '1px solid var(--color-border-neutral)',
          borderRadius: '8px', boxShadow: '0 4px 12px var(--color-shadow-medium)', padding: '6px', zIndex: 1000,
          display: 'flex', flexDirection: 'column', gap: '4px', boxSizing: 'border-box',
        }}>
          <input
            autoFocus value={query} placeholder={t('chat.deck.searchAgentPlaceholder')}
            aria-label={t('chat.deck.searchAgentPlaceholder')}
            onChange={(event) => { setQuery(event.target.value); setActiveIndex(0); }}
            onKeyDown={handleSearchKeyDown}
            style={{ width: '100%', boxSizing: 'border-box', border: '1px solid var(--color-border-neutral)', borderRadius: '6px', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '6px 8px', fontSize: '12px', outlineOffset: 2 }}
          />
          <div style={{ maxHeight: popupLayout.listMaxHeight, overflowY: 'auto', overscrollBehavior: 'contain' }}>
            {allowNone && (() => {
              const isActive = activeIndex === 0;
              return (
                <div role="option" aria-selected={!selectedAgentId} ref={(el) => { if (el) itemRefs.current.set(0, el); else itemRefs.current.delete(0); }}
                  onClick={() => selectOption(undefined)} onMouseEnter={() => setActiveIndex(0)}
                  style={{ padding: '7px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', borderRadius: '6px', fontSize: '13px', color: 'var(--color-text-muted)', background: isActive ? 'var(--color-bg-hover)' : 'transparent', fontStyle: 'italic' }}>
                  <span aria-hidden="true" style={{ width: '14px', visibility: selectedAgentId ? 'hidden' : 'visible' }}>✓</span>
                  {(noneLabel ?? t('chat.deck.noneAgent'))}
                </div>
              );
            })()}
            {groups.map(({ deck, agents }) => (
              <div key={deck.id} role="group" aria-label={deckLabel(deck)}>
                <div style={{ padding: '8px 10px 4px', color: 'var(--color-text-muted)', fontSize: '10px', fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase' }}>
                  {deckLabel(deck)}
                </div>
                {agents.map((agent) => {
                  const flatIndex = options.findIndex((option) => option?.agentId === agent.id);
                  const isActive = flatIndex === activeIndex;
                  const isSelected = agent.id === selectedAgentId;
                  const AgentIcon = iconMap[agent.icon as keyof typeof iconMap] || iconMap.brain;
                  const agentColor = COLORS[agent.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
                  const option = { deck, agent, deckId: deck.id, agentId: agent.id };
                  return (
                    <div key={agent.id} role="option" aria-selected={isSelected}
                      ref={(el) => { if (el) itemRefs.current.set(flatIndex, el); else itemRefs.current.delete(flatIndex); }}
                      onClick={() => selectOption(option)} onMouseEnter={() => setActiveIndex(flatIndex)}
                      style={{ marginLeft: '8px', padding: '7px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', borderRadius: '6px', fontSize: '13px', color: 'var(--color-text-body)', background: isActive ? 'var(--color-bg-hover)' : 'transparent' }}>
                      <span aria-hidden="true" style={{ width: '14px', color: 'var(--color-action-link)', visibility: isSelected ? 'visible' : 'hidden' }}>✓</span>
                      <AgentIcon size={14} color={agentColor} />
                      <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{agentLabel(agent)}</span>
                    </div>
                  );
                })}
              </div>
            ))}
            {groups.length === 0 && query.trim() && (
              <div style={{ padding: '8px 10px', fontSize: '12px', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                {t('chat.deck.noAgentMatch')}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
