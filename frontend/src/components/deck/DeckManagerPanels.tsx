// [Input] Persisted Deck DTOs, PDF page-layout contract, pagination policy, and DeckManager callbacks.
// [Output] User published-clean Deck home, default-visible system Decks, preview page, Work inventory, and related Chat cleanup.
// [Pos] Presentational Deck launch and Settings / Work management surfaces in frontend/src/components/deck.
// [Sync] 2026-08-16: align the page with Deck设计需求.pdf pages 1-2; remove the table/dashboard layout,
//                    keep marketplace options absent, and show only exact active runtime-version facts.
// [Sync] 2026-08-17: keep user Decks behind enabled/published-clean facts while system Decks default to visible.
// [Sync] 2026-08-17: add More → related conversations using the Chat history preview pattern.
// [Sync] 2026-08-17: split Available/System Deck launcher groups and keep system-default Decks static.
// [Sync] 2026-08-17: add a read-only Deck preview page before maintenance editing.
// [Sync] 2026-08-17: keep Deck preview visuals neutral instead of applying persisted accent colors.
// [Sync] 2026-08-17: let orchestration dispatch typed preview examples to Chat or the dedicated Dream workbench.
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from 'react';
import { FaCog, FaCommentAlt, FaPlay, FaShieldAlt, FaTrashAlt } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import type { ChatHistoryThread } from '../../api/chatHistoryApi';
import type { Deck } from '../../api/voiceApi';
import { DECK_ENABLED_LAUNCH_LIMIT, DECK_MANAGEMENT_PAGE_SIZE } from '../../constants/deck';
import { COLORS, iconMap } from '../deckVisuals';
import './DeckManagerPanels.css';

interface DeckManagerPanelProps {
  decks: Deck[];
  busyDeckId: string | null;
  creatingDeck: boolean;
  refreshingDecks: boolean;
  refreshError: string | null;
  operationError: string | null;
  onCreateDeck: () => void;
  onRefreshDecks: () => void;
  onOpenDeck: (deckId: string) => void;
  onToggleDeck: (deckId: string, enabled: boolean) => void;
  onSyncDeck: (deckId: string) => void;
  onDeleteDeck: (deckId: string) => void;
  onLoadRelatedThreads: (deckId: string, offset: number) => Promise<ChatHistoryThread[]>;
  onDeleteRelatedThread: (threadId: string) => Promise<void>;
}

interface DeckLaunchPanelProps {
  decks: Deck[];
  creatingDeck: boolean;
  refreshingDecks: boolean;
  refreshError: string | null;
  operationError: string | null;
  onCreateDeck: () => void;
  onRefreshDecks: () => void;
  onOpenDeck: (deckId: string) => void;
  onOpenSettings: () => void;
}

type DeckPreviewVoice = NonNullable<Deck['voices']>[number];

interface DeckPreviewPanelProps {
  deck: Deck;
  launchError: string | null;
  launchingDream: boolean;
  onBack: () => void;
  onEditDeck: (deckId: string) => void;
  onTryDeck: (deckId: string, voice: DeckPreviewVoice, input?: string) => void | Promise<void>;
}

type AgentTypeFilter = 'all' | 'chat' | 'dream';
type StatusFilter = 'all' | 'enabled' | 'disabled';

const RELATED_THREADS_PAGE_SIZE = 20;
const DEFAULT_INITIALIZED_DECK_REASON = 'default_initialized';

const isSystemDeckDisplay = (deck: Deck): boolean => (
  deck.is_system || deck.publish_block_reason === DEFAULT_INITIALIZED_DECK_REASON
);

const isUserDeckHomeVisible = (deck: Deck): boolean => (
  deck.enabled
  && deck.deck_version_capability === true
  && typeof deck.deck_version === 'number'
  && deck.deck_version > 0
  && deck.deck_version_dirty === false
  && deck.deck_version_status === 'published'
);

const isDeckHomeVisible = (deck: Deck): boolean => (
  isSystemDeckDisplay(deck) || isUserDeckHomeVisible(deck)
);

export function DeckLaunchPanel({
  decks,
  creatingDeck,
  refreshingDecks,
  refreshError,
  operationError,
  onCreateDeck,
  onRefreshDecks,
  onOpenDeck,
  onOpenSettings,
}: DeckLaunchPanelProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [agentType, setAgentType] = useState<AgentTypeFilter>('all');
  const [createMenuOpen, setCreateMenuOpen] = useState(false);
  const menuBoundaryRef = useRef<HTMLDivElement>(null);
  const visibleHomeDecks = useMemo(
    () => decks.filter(isDeckHomeVisible),
    [decks],
  );
  const shortcutDecks = useMemo(
    () => visibleHomeDecks.slice(0, DECK_ENABLED_LAUNCH_LIMIT),
    [visibleHomeDecks],
  );
  const enabledAgentTypeCounts = useMemo(() => ({
    all: visibleHomeDecks.length,
    chat: visibleHomeDecks.filter((deck) => deck.agent_type === 'chat').length,
    dream: visibleHomeDecks.filter((deck) => deck.agent_type === 'dream').length,
  }), [visibleHomeDecks]);
  const visibleDecks = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return visibleHomeDecks.filter((deck) => {
      const matchesQuery = normalizedQuery.length === 0 || [
        deck.name,
        deck.name_zh,
        deck.name_en,
        deck.description,
        deck.description_zh,
        deck.description_en,
      ].some((value) => value?.toLocaleLowerCase().includes(normalizedQuery));
      const matchesAgentType = agentType === 'all' || deck.agent_type === agentType;
      return matchesQuery && matchesAgentType;
    });
  }, [agentType, query, visibleHomeDecks]);
  const userVisibleDecks = useMemo(
    () => visibleDecks.filter((deck) => !isSystemDeckDisplay(deck)),
    [visibleDecks],
  );
  const systemVisibleDecks = useMemo(
    () => visibleDecks.filter(isSystemDeckDisplay),
    [visibleDecks],
  );

  useEffect(() => {
    const closeMenu = (event: PointerEvent) => {
      if (!menuBoundaryRef.current?.contains(event.target as Node)) setCreateMenuOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setCreateMenuOpen(false);
    };
    document.addEventListener('pointerdown', closeMenu);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeMenu);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, []);

  return (
    <div className="deck-manager-home deck-manager-home--launcher" data-deck-manager-launcher ref={menuBoundaryRef}>
      <div className="deck-manager-home__topbar">
        <span className="deck-manager-home__section-label">{t('deck.home.sectionLabel')}</span>
        <div className="deck-manager-home__top-actions">
          <button
            aria-label={t('deck.actions.refresh')}
            className="deck-manager-icon-action"
            disabled={refreshingDecks}
            onClick={onRefreshDecks}
            title={t('deck.actions.refresh')}
            type="button"
          >
            <span aria-hidden="true" className={refreshingDecks ? 'is-spinning' : undefined}>↻</span>
          </button>
          <div className="deck-manager-menu-anchor">
            <button
              aria-expanded={createMenuOpen}
              aria-haspopup="menu"
              className="deck-manager-create-action"
              onClick={() => setCreateMenuOpen((current) => !current)}
              type="button"
            >
              {t('deck.actions.createMenu')}
              <span aria-hidden="true">⌄</span>
            </button>
            {createMenuOpen && (
              <div className="deck-manager-menu deck-manager-menu--create" role="menu">
                <button
                  disabled={creatingDeck}
                  onClick={() => {
                    setCreateMenuOpen(false);
                    onCreateDeck();
                  }}
                  role="menuitem"
                  type="button"
                >
                  <span aria-hidden="true">＋</span>
                  {creatingDeck ? t('deck.actions.creating') : t('deck.actions.create')}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <header className="deck-manager-home__header">
        <h1>{t('deck.home.title')}</h1>
        <p>{t('deck.home.launchDescription')}</p>
      </header>

      <label className="deck-manager-search deck-manager-search--launcher">
        <span className="deck-manager-sr-only">{t('deck.home.launchSearchLabel')}</span>
        <span aria-hidden="true">⌕</span>
        <input
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t('deck.creator.searchPlaceholder')}
          type="search"
          value={query}
        />
      </label>

      {refreshError && <p className="deck-manager-inline-error" role="alert">{refreshError}</p>}
      {operationError && <p className="deck-manager-inline-error" role="alert">{operationError}</p>}

      <section aria-labelledby="deck-manager-enabled-title" className="deck-manager-enabled">
        <div className="deck-manager-section-heading">
          <h2 id="deck-manager-enabled-title">{t('deck.home.enabledTitle')}</h2>
          <button
            aria-label={t('deck.home.openSettings')}
            className="deck-manager-enabled__settings"
            onClick={onOpenSettings}
            title={t('deck.home.openSettings')}
            type="button"
          >
            <FaCog aria-hidden="true" size={18} />
          </button>
        </div>
        <div className="deck-manager-enabled__strip" role="list">
          {shortcutDecks.map((deck) => {
            const Icon = iconMap[deck.icon as keyof typeof iconMap] || iconMap.brain;
            const accent = COLORS[deck.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
            return (
              <span key={deck.id} role="listitem">
                <button
                  aria-label={isSystemDeckDisplay(deck)
                    ? t('deck.home.systemDeckLabel', { deck: deck.name })
                    : t('deck.home.openDeck', { deck: deck.name })}
                  className={`deck-manager-enabled__item${isSystemDeckDisplay(deck) ? ' deck-manager-enabled__item--system' : ''}`}
                  data-deck-home-id={deck.id}
                  data-deck-home-kind={isSystemDeckDisplay(deck) ? 'system' : 'user'}
                  onClick={() => onOpenDeck(deck.id)}
                  style={{ '--deck-accent': accent } as CSSProperties}
                  title={`${deck.name}${isSystemDeckDisplay(deck) ? ` · ${t('deck.labels.system')}` : ''}`}
                  type="button"
                >
                  <Icon aria-hidden="true" size={24} />
                  {isSystemDeckDisplay(deck) ? (
                    <span aria-hidden="true" className="deck-manager-enabled__system-marker">
                      <FaShieldAlt size={7} />
                    </span>
                  ) : null}
                </button>
              </span>
            );
          })}
        </div>
        {visibleHomeDecks.length === 0 ? (
          <p className="deck-manager-enabled__empty">{t('deck.home.availableEmpty')}</p>
        ) : null}
      </section>

      {visibleHomeDecks.length > 0 ? (
        <section aria-labelledby="deck-manager-launch-catalog-title" className="deck-manager-launch-catalog">
          <div className="deck-manager-launch-catalog__controls">
            <div aria-label={t('deck.creator.agentTypeFilter')} className="deck-manager-filter-tabs" role="tablist">
              {(['all', 'chat', 'dream'] as const).map((candidate) => (
                <button
                  aria-selected={agentType === candidate}
                  key={candidate}
                  onClick={() => setAgentType(candidate)}
                  role="tab"
                  type="button"
                >
                  {t(`deck.creator.agentTypeTabs.${candidate}`)}
                  <span>{enabledAgentTypeCounts[candidate]}</span>
                </button>
              ))}
            </div>
          </div>
          <h2 className="deck-manager-sr-only" id="deck-manager-launch-catalog-title">
            {t('deck.home.launchCatalogTitle')}
          </h2>

          {visibleDecks.length === 0 ? (
            <div className="deck-manager-empty deck-manager-empty--launcher">
              <p>{t('deck.creator.noResults')}</p>
              <button
                className="deck-manager-secondary-action"
                onClick={() => {
                  setQuery('');
                  setAgentType('all');
                }}
                type="button"
              >
                {t('deck.actions.clearFilters')}
              </button>
            </div>
          ) : (
            <div className="deck-manager-launch-catalog__groups">
              <DeckLaunchGroup
                decks={userVisibleDecks}
                emptyLabel={t('deck.home.availableListEmpty')}
                label={t('deck.home.availableListTitle')}
                listLabel={t('deck.home.availableListLabel')}
                onOpenDeck={onOpenDeck}
                t={t}
              />
              <DeckLaunchGroup
                decks={systemVisibleDecks}
                emptyLabel={t('deck.home.systemListEmpty')}
                label={t('deck.home.systemListTitle')}
                listLabel={t('deck.home.systemListLabel')}
                onOpenDeck={onOpenDeck}
                t={t}
              />
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}

function DeckLaunchGroup({
  decks,
  emptyLabel,
  label,
  listLabel,
  onOpenDeck,
  t,
}: {
  decks: Deck[];
  emptyLabel: string;
  label: string;
  listLabel: string;
  onOpenDeck: (deckId: string) => void;
  t: ReturnType<typeof useTranslation>['t'];
}) {
  return (
    <section className="deck-manager-launch-group" aria-label={label}>
      <h3>{label}</h3>
      <ul aria-label={listLabel} className="deck-manager-launch-catalog__grid">
        {decks.map((deck) => {
          const Icon = iconMap[deck.icon as keyof typeof iconMap] || iconMap.brain;
          const accent = COLORS[deck.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
          return (
            <li key={deck.id}>
              <button
                aria-label={isSystemDeckDisplay(deck)
                  ? t('deck.home.systemDeckLabel', { deck: deck.name })
                  : `${t('deck.actions.edit')} ${deck.name}`}
                className={`deck-manager-launch-card${isSystemDeckDisplay(deck) ? ' deck-manager-launch-card--system' : ''}`}
                data-deck-home-id={deck.id}
                data-deck-home-kind={isSystemDeckDisplay(deck) ? 'system' : 'user'}
                onClick={() => onOpenDeck(deck.id)}
                style={{ '--deck-accent': accent } as CSSProperties}
                type="button"
              >
                <span aria-hidden="true" className="deck-manager-launch-card__icon">
                  <Icon size={24} />
                </span>
                <span className="deck-manager-launch-card__copy">
                  <span className="deck-manager-launch-card__title">
                    {deck.name}
                    {isSystemDeckDisplay(deck) ? <span className="deck-manager-chip">{t('deck.labels.system')}</span> : null}
                  </span>
                  <span className="deck-manager-launch-card__description">
                    {deck.description || t('deck.labels.noDescription')}
                  </span>
                  <span className="deck-manager-launch-card__meta">
                    {t(`deck.labels.agentType.${deck.agent_type === 'dream' ? 'dream' : 'chat'}`)}
                    <span aria-hidden="true">·</span>
                    {isSystemDeckDisplay(deck) ? t('deck.labels.systemBuiltIn') : t('deck.labels.contentVersion', { version: deck.deck_version })}
                  </span>
                </span>
                <span aria-hidden="true" className="deck-manager-launch-card__arrow">›</span>
              </button>
            </li>
          );
        })}
      </ul>
      {decks.length === 0 ? (
        <p className="deck-manager-launch-group__empty">{emptyLabel}</p>
      ) : null}
    </section>
  );
}

export function DeckPreviewPanel({
  deck,
  launchError,
  launchingDream,
  onBack,
  onEditDeck,
  onTryDeck,
}: DeckPreviewPanelProps) {
  const { i18n, t } = useTranslation();
  const isSystem = isSystemDeckDisplay(deck);
  const Icon = iconMap[deck.icon as keyof typeof iconMap] || iconMap.brain;
  const voices = deck.voices || [];
  const enabledVoices = voices.filter((voice) => voice.enabled);
  const trialVoice = enabledVoices[0] || voices[0] || null;
  const examples = voices.slice(0, 3);
  const fallbackPrompt = deck.description || t('deck.preview.defaultDescription', { deck: deck.name });
  const locale = i18n.resolvedLanguage === 'zh' ? 'zh-CN' : 'en-US';
  const updatedAt = deck.updated_at ? new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(deck.updated_at)) : t('deck.labels.updateUnknown');
  const versionLabel = isSystem
    ? t('deck.labels.systemBuiltIn')
    : (deck.deck_version ? t('deck.labels.contentVersion', { version: deck.deck_version }) : t('deck.version.unpublished'));

  return (
    <article
      className="deck-manager-preview"
      data-deck-preview-id={deck.id}
    >
      <div className="deck-manager-preview__topbar">
        <button className="deck-manager-preview__back" onClick={onBack} type="button">
          <span aria-hidden="true">‹</span>
          {t('deck.preview.back')}
        </button>
      </div>

      <header className="deck-manager-preview__header">
        <span className="deck-manager-preview__icon">
          <Icon aria-hidden="true" size={40} />
        </span>
        <div className="deck-manager-preview__title-row">
          <div>
            <h1>{deck.name}</h1>
            <p>{deck.description || t('deck.labels.noDescription')}</p>
          </div>
          <div className="deck-manager-preview__actions">
            {!isSystem ? (
              <button
                aria-label={t('deck.preview.editDeck', { deck: deck.name })}
                className="deck-manager-icon-action"
                onClick={() => onEditDeck(deck.id)}
                title={t('deck.actions.edit')}
                type="button"
              >
                <span aria-hidden="true">•••</span>
              </button>
            ) : null}
            <button
              aria-busy={launchingDream}
              className="deck-manager-preview__try"
              disabled={!trialVoice || launchingDream}
              onClick={() => {
                if (trialVoice) onTryDeck(deck.id, trialVoice);
              }}
              type="button"
            >
              <FaPlay aria-hidden="true" size={13} />
              {launchingDream ? t('deck.preview.launchingDream') : t('deck.preview.tryNow')}
            </button>
          </div>
        </div>
      </header>

      {launchError ? (
        <p className="deck-manager-inline-error" role="alert">{launchError}</p>
      ) : null}

      <section aria-label={t('deck.preview.examples')} className="deck-manager-preview__hero">
        {examples.length > 0 ? examples.map((voice, index) => {
          const VoiceIcon = iconMap[voice.icon as keyof typeof iconMap] || Icon;
          const prompt = voice.system_prompt?.split('\n').find((line) => line.trim().length > 0)?.trim()
            || deck.description
            || t('deck.labels.noDescription');
          return (
            <button
              aria-busy={launchingDream}
              className={`deck-manager-preview__example deck-manager-preview__example--${index + 1}`}
              disabled={!voice.enabled || launchingDream}
              key={voice.id}
              onClick={() => onTryDeck(deck.id, voice, prompt)}
              type="button"
            >
              <VoiceIcon aria-hidden="true" size={17} />
              <strong>{voice.name}</strong>
              <span>{prompt}</span>
              <span aria-hidden="true" className="deck-manager-preview__example-arrow">›</span>
            </button>
          );
        }) : (
          <div className="deck-manager-preview__example deck-manager-preview__example--empty">
            <Icon aria-hidden="true" size={17} />
            <strong>{deck.name}</strong>
            <span>{fallbackPrompt}</span>
          </div>
        )}
      </section>

      <p className="deck-manager-preview__description">
        {deck.description || t('deck.preview.defaultDescription', { deck: deck.name })}
      </p>

      <section className="deck-manager-preview__section" aria-labelledby="deck-preview-agents-title">
        <h2 id="deck-preview-agents-title">{t('deck.preview.agentsTitle', { count: voices.length })}</h2>
        <ul className="deck-manager-preview__rows">
          {voices.length > 0 ? voices.map((voice) => {
            const VoiceIcon = iconMap[voice.icon as keyof typeof iconMap] || iconMap.brain;
            return (
              <li key={voice.id}>
                <span className="deck-manager-preview__row-icon"><VoiceIcon aria-hidden="true" size={18} /></span>
                <span>
                  <strong>{voice.name}</strong>
                  <small>{voice.enabled ? t('deck.labels.enabled') : t('deck.labels.disabled')}</small>
                </span>
              </li>
            );
          }) : (
            <li className="deck-manager-preview__empty-row">{t('deck.preview.noAgents')}</li>
          )}
        </ul>
      </section>

      <section className="deck-manager-preview__section" aria-labelledby="deck-preview-info-title">
        <h2 id="deck-preview-info-title">{t('deck.preview.infoTitle')}</h2>
        <dl className="deck-manager-preview__info">
          <div>
            <dt>{t('deck.preview.infoDeveloper')}</dt>
            <dd>{isSystem ? t('deck.preview.systemDeveloper') : t('deck.preview.userDeveloper')}</dd>
          </div>
          <div>
            <dt>{t('deck.preview.infoType')}</dt>
            <dd>{t(`deck.labels.agentType.${deck.agent_type === 'dream' ? 'dream' : 'chat'}`)}</dd>
          </div>
          <div>
            <dt>{t('deck.preview.infoVersion')}</dt>
            <dd>{versionLabel}</dd>
          </div>
          <div>
            <dt>{t('deck.preview.infoRuntime')}</dt>
            <dd>{deck.deck_plugin_version || t('deck.labels.updateUnknown')}</dd>
          </div>
          <div>
            <dt>{t('deck.preview.infoUpdated')}</dt>
            <dd>{updatedAt}</dd>
          </div>
        </dl>
      </section>
    </article>
  );
}

export function DeckSettingsPanel({
  decks,
  busyDeckId,
  creatingDeck,
  refreshingDecks,
  refreshError,
  operationError,
  onCreateDeck,
  onRefreshDecks,
  onOpenDeck,
  onToggleDeck,
  onSyncDeck,
  onDeleteDeck,
  onLoadRelatedThreads,
  onDeleteRelatedThread,
}: DeckManagerPanelProps) {
  const { i18n, t } = useTranslation();
  const [query, setQuery] = useState('');
  const [agentType, setAgentType] = useState<AgentTypeFilter>('all');
  const [status, setStatus] = useState<StatusFilter>('all');
  const [page, setPage] = useState(1);
  const [createMenuOpen, setCreateMenuOpen] = useState(false);
  const [actionMenuDeckId, setActionMenuDeckId] = useState<string | null>(null);
  const [relatedDeck, setRelatedDeck] = useState<Deck | null>(null);
  const [relatedThreads, setRelatedThreads] = useState<ChatHistoryThread[]>([]);
  const [relatedThreadsLoading, setRelatedThreadsLoading] = useState(false);
  const [relatedThreadsLoadingMore, setRelatedThreadsLoadingMore] = useState(false);
  const [relatedThreadsHasMore, setRelatedThreadsHasMore] = useState(false);
  const [relatedThreadsError, setRelatedThreadsError] = useState<string | null>(null);
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null);
  const menuBoundaryRef = useRef<HTMLDivElement>(null);

  const agentTypeCounts = useMemo(() => ({
    all: decks.length,
    chat: decks.filter((deck) => deck.agent_type === 'chat').length,
    dream: decks.filter((deck) => deck.agent_type === 'dream').length,
  }), [decks]);
  const filteredDecks = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return decks.filter((deck) => {
      const matchesQuery = normalizedQuery.length === 0 || [
        deck.name,
        deck.name_zh,
        deck.name_en,
        deck.description,
        deck.description_zh,
        deck.description_en,
      ].some((value) => value?.toLocaleLowerCase().includes(normalizedQuery));
      const matchesAgentType = agentType === 'all' || deck.agent_type === agentType;
      const matchesStatus = status === 'all'
        || (status === 'enabled' ? deck.enabled : !deck.enabled);
      return matchesQuery && matchesAgentType && matchesStatus;
    });
  }, [agentType, decks, query, status]);

  const pageCount = Math.max(1, Math.ceil(filteredDecks.length / DECK_MANAGEMENT_PAGE_SIZE));
  const visibleDecks = filteredDecks.slice(
    (page - 1) * DECK_MANAGEMENT_PAGE_SIZE,
    page * DECK_MANAGEMENT_PAGE_SIZE,
  );
  const hasFilters = query.trim().length > 0 || agentType !== 'all' || status !== 'all';
  const locale = i18n.resolvedLanguage === 'zh' ? 'zh-CN' : 'en-US';

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);

  useEffect(() => {
    const closeMenus = (event: PointerEvent) => {
      if (!menuBoundaryRef.current?.contains(event.target as Node)) {
        setCreateMenuOpen(false);
        setActionMenuDeckId(null);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setCreateMenuOpen(false);
        setActionMenuDeckId(null);
        setRelatedDeck(null);
      }
    };
    document.addEventListener('pointerdown', closeMenus);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeMenus);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, []);

  const formatUpdatedAt = (value?: string): string => {
    if (!value) return t('deck.labels.updateUnknown');
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return t('deck.labels.updateUnknown');
    return new Intl.DateTimeFormat(locale, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(date);
  };

  const clearFilters = () => {
    setQuery('');
    setAgentType('all');
    setStatus('all');
    setPage(1);
  };

  const selectAgentType = (next: AgentTypeFilter) => {
    setAgentType(next);
    setPage(1);
  };

  const openCreateDialog = () => {
    setCreateMenuOpen(false);
    onCreateDeck();
  };

  const closeRelatedThreads = () => {
    setRelatedDeck(null);
    setRelatedThreads([]);
    setRelatedThreadsError(null);
    setDeletingThreadId(null);
  };

  const loadRelatedThreads = async (deck: Deck, offset = 0) => {
    const append = offset > 0;
    if (append) setRelatedThreadsLoadingMore(true);
    else setRelatedThreadsLoading(true);
    setRelatedThreadsError(null);
    try {
      const rows = await onLoadRelatedThreads(deck.id, offset);
      setRelatedThreads((current) => append ? [...current, ...rows] : rows);
      setRelatedThreadsHasMore(rows.length === RELATED_THREADS_PAGE_SIZE);
    } catch (loadError) {
      setRelatedThreadsError(
        loadError instanceof Error && loadError.message
          ? loadError.message
          : t('deck.related.loadFailed'),
      );
    } finally {
      setRelatedThreadsLoading(false);
      setRelatedThreadsLoadingMore(false);
    }
  };

  const openRelatedThreads = (deck: Deck) => {
    setActionMenuDeckId(null);
    setRelatedDeck(deck);
    setRelatedThreads([]);
    setRelatedThreadsHasMore(false);
    void loadRelatedThreads(deck);
  };

  const deleteRelatedThread = async (thread: ChatHistoryThread) => {
    if (deletingThreadId) return;
    const title = thread.title || t('chat.history.fallbackTitle');
    if (!confirm(t('deck.related.confirmDelete', { title }))) return;
    setDeletingThreadId(thread.id);
    setRelatedThreadsError(null);
    try {
      await onDeleteRelatedThread(thread.id);
      setRelatedThreads((current) => current.filter((candidate) => candidate.id !== thread.id));
    } catch (deleteError) {
      setRelatedThreadsError(
        deleteError instanceof Error && deleteError.message
          ? deleteError.message
          : t('deck.related.deleteFailed'),
      );
    } finally {
      setDeletingThreadId(null);
    }
  };

  const deleteDeckAfterThreads = () => {
    if (!relatedDeck) return;
    const deckId = relatedDeck.id;
    closeRelatedThreads();
    onDeleteDeck(deckId);
  };

  return (
    <div className="deck-manager-home deck-manager-home--settings" data-deck-manager-list ref={menuBoundaryRef}>
      <div className="deck-manager-home__topbar">
        <span className="deck-manager-home__section-label">{t('deck.home.sectionLabel')}</span>
        <div className="deck-manager-home__top-actions">
          <button
            aria-label={t('deck.actions.refresh')}
            className="deck-manager-icon-action"
            disabled={refreshingDecks}
            onClick={onRefreshDecks}
            title={t('deck.actions.refresh')}
            type="button"
          >
            <span aria-hidden="true" className={refreshingDecks ? 'is-spinning' : undefined}>↻</span>
          </button>
          <div className="deck-manager-menu-anchor">
            <button
              aria-expanded={createMenuOpen}
              aria-haspopup="menu"
              className="deck-manager-create-action"
              onClick={() => {
                setActionMenuDeckId(null);
                setCreateMenuOpen((current) => !current);
              }}
              type="button"
            >
              {t('deck.actions.createMenu')}
              <span aria-hidden="true">⌄</span>
            </button>
            {createMenuOpen && (
              <div className="deck-manager-menu deck-manager-menu--create" role="menu">
                <button disabled={creatingDeck} onClick={openCreateDialog} role="menuitem" type="button">
                  <span aria-hidden="true">＋</span>
                  {creatingDeck ? t('deck.actions.creating') : t('deck.actions.create')}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <label className="deck-manager-search">
        <span className="deck-manager-sr-only">{t('deck.creator.searchLabel')}</span>
        <span aria-hidden="true">⌕</span>
        <input
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(1);
          }}
          placeholder={t('deck.creator.searchPlaceholder')}
          type="search"
          value={query}
        />
      </label>

      {refreshError && <p className="deck-manager-inline-error" role="alert">{refreshError}</p>}
      {operationError && <p className="deck-manager-inline-error" role="alert">{operationError}</p>}

      <section aria-labelledby="deck-manager-all-title" className="deck-manager-catalog">
        <div className="deck-manager-catalog__controls">
          <div aria-label={t('deck.creator.agentTypeFilter')} className="deck-manager-filter-tabs" role="tablist">
            {(['all', 'chat', 'dream'] as const).map((candidate) => (
              <button
                aria-selected={agentType === candidate}
                key={candidate}
                onClick={() => selectAgentType(candidate)}
                role="tab"
                type="button"
              >
                {t(`deck.creator.agentTypeTabs.${candidate}`)}
                <span>{agentTypeCounts[candidate]}</span>
              </button>
            ))}
          </div>
          <label className="deck-manager-status-filter">
            <span className="deck-manager-sr-only">{t('deck.creator.statusFilter')}</span>
            <select
              aria-label={t('deck.creator.statusFilter')}
              onChange={(event) => {
                setStatus(event.target.value as StatusFilter);
                setPage(1);
              }}
              value={status}
            >
              <option value="all">{t('deck.creator.statusAll')}</option>
              <option value="enabled">{t('deck.labels.enabled')}</option>
              <option value="disabled">{t('deck.labels.disabled')}</option>
            </select>
          </label>
        </div>
        <h2 className="deck-manager-sr-only" id="deck-manager-all-title">{t('deck.home.allTitle')}</h2>

        {filteredDecks.length === 0 ? (
          <div className="deck-manager-empty">
            <p>{decks.length === 0 ? t('deck.creator.empty') : t('deck.creator.noResults')}</p>
            {hasFilters && (
              <button className="deck-manager-secondary-action" onClick={clearFilters} type="button">
                {t('deck.actions.clearFilters')}
              </button>
            )}
          </div>
        ) : (
          <ul aria-label={t('deck.creator.listLabel')} className="deck-manager-list">
            {visibleDecks.map((deck) => {
              const isSystem = isSystemDeckDisplay(deck);
              const disabled = busyDeckId === deck.id;
              const Icon = iconMap[deck.icon as keyof typeof iconMap] || iconMap.brain;
              const accent = COLORS[deck.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
              const voiceCount = deck.voice_count || deck.voices?.length || 0;
              const menuOpen = actionMenuDeckId === deck.id;
              return (
                <li
                  className={`deck-manager-list__row${isSystem ? ' deck-manager-list__row--system' : ''}`}
                  data-deck-card-id={deck.id}
                  data-deck-card-kind="owned"
                  key={deck.id}
                  style={{ '--deck-accent': isSystem ? 'var(--color-border-paper)' : accent } as CSSProperties}
                >
                  <button
                    className="deck-manager-list__identity"
                    disabled={disabled || isSystem}
                    onClick={() => {
                      if (!isSystem) onOpenDeck(deck.id);
                    }}
                    type="button"
                  >
                    <span className="deck-manager-list__icon" aria-hidden="true"><Icon size={19} /></span>
                    <span className="deck-manager-list__copy">
                      <span className="deck-manager-list__title">
                        {deck.name}
                        {isSystem && <span className="deck-manager-chip">{t('deck.labels.system')}</span>}
                      </span>
                      <span className="deck-manager-list__description">
                        {deck.description || t('deck.labels.noDescription')}
                      </span>
                      <span className="deck-manager-list__meta">
                        {t(`deck.labels.agentType.${deck.agent_type === 'dream' ? 'dream' : 'chat'}`)}
                        <span aria-hidden="true">·</span>
                        {t('deck.labels.agentCount', { count: voiceCount })}
                        {deck.deck_version_capability && (
                          <>
                            <span aria-hidden="true">·</span>
                            <span className="deck-manager-version-fact">
                              {deck.deck_version ? `内容 v${deck.deck_version}` : '未提交版本'}
                              {deck.deck_version_dirty ? ` · 草稿 r${deck.draft_revision}` : ''}
                            </span>
                          </>
                        )}
                        {deck.deck_plugin_version && (
                          <>
                            <span aria-hidden="true">·</span>
                            <span className="deck-manager-version-fact">运行插件 v{deck.deck_plugin_version}</span>
                          </>
                        )}
                        <span aria-hidden="true">·</span>
                        {formatUpdatedAt(deck.updated_at)}
                      </span>
                    </span>
                  </button>

                  <div className="deck-manager-list__actions">
                    {!isSystem && (
                      <div className="deck-manager-menu-anchor">
                        <button
                          aria-expanded={menuOpen}
                          aria-haspopup="menu"
                          aria-label={t('deck.actions.more', { deck: deck.name })}
                          className="deck-manager-icon-action"
                          disabled={disabled}
                          onClick={() => {
                            setCreateMenuOpen(false);
                            setActionMenuDeckId((current) => current === deck.id ? null : deck.id);
                          }}
                          type="button"
                        >
                          <span aria-hidden="true">•••</span>
                        </button>
                        {menuOpen && (
                          <div className="deck-manager-menu deck-manager-menu--row" role="menu">
                            <button onClick={() => { setActionMenuDeckId(null); onOpenDeck(deck.id); }} role="menuitem" type="button">
                              {t('deck.actions.edit')}
                            </button>
                            {deck.parent_id && (
                              <button onClick={() => { setActionMenuDeckId(null); onSyncDeck(deck.id); }} role="menuitem" type="button">
                                {t('deck.actions.sync')}
                              </button>
                            )}
                            <button onClick={() => openRelatedThreads(deck)} role="menuitem" type="button">
                              {t('deck.actions.relatedConversations')}
                            </button>
                            <button className="is-danger" onClick={() => { setActionMenuDeckId(null); onDeleteDeck(deck.id); }} role="menuitem" type="button">
                              {t('deck.actions.delete')}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                    {!isSystem && (
                      <button
                        aria-checked={deck.enabled}
                        aria-label={deck.enabled
                          ? t('deck.actions.disableDeck', { deck: deck.name })
                          : t('deck.actions.enableDeck', { deck: deck.name })}
                        className="deck-manager-switch"
                        disabled={disabled}
                        onClick={() => onToggleDeck(deck.id, deck.enabled)}
                        role="switch"
                        type="button"
                      >
                        <span aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {pageCount > 1 && (
          <nav aria-label={t('deck.pagination.ariaLabel')} className="deck-manager-pagination">
            <button
              className="deck-manager-secondary-action"
              disabled={page === 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              type="button"
            >
              {t('deck.pagination.previous')}
            </button>
            <span aria-live="polite">{t('deck.pagination.summary', { page, pages: pageCount })}</span>
            <button
              className="deck-manager-secondary-action"
              disabled={page === pageCount}
              onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
              type="button"
            >
              {t('deck.pagination.next')}
            </button>
          </nav>
        )}
      </section>

      {relatedDeck && (
        <div
          className="deck-manager-dialog-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeRelatedThreads();
          }}
        >
          <section
            aria-labelledby="deck-related-conversations-title"
            aria-modal="true"
            className="deck-manager-dialog deck-manager-related-dialog"
            role="dialog"
          >
            <header className="deck-manager-related-dialog__header">
              <div>
                <span className="deck-manager-related-dialog__eyebrow">{relatedDeck.name}</span>
                <h2 id="deck-related-conversations-title">{t('deck.related.title')}</h2>
              </div>
              <button
                aria-label={t('deck.related.close')}
                className="deck-manager-details-dialog__close"
                onClick={closeRelatedThreads}
                type="button"
              >
                ×
              </button>
            </header>

            <p className="deck-manager-related-dialog__description">
              {t('deck.related.description')}
            </p>

            <div aria-live="polite" className="deck-manager-related-dialog__body">
              {relatedThreadsLoading ? (
                <div className="deck-manager-related-dialog__loading">
                  <span className="deck-manager-status__spinner" aria-hidden="true" />
                  {t('deck.related.loading')}
                </div>
              ) : null}

              {relatedThreadsError ? (
                <div className="deck-manager-related-dialog__error" role="alert">
                  <span>{relatedThreadsError}</span>
                  <button onClick={() => void loadRelatedThreads(relatedDeck)} type="button">
                    {t('deck.actions.retry')}
                  </button>
                </div>
              ) : null}

              {!relatedThreadsLoading
                && !relatedThreadsError
                && relatedThreads.length === 0
                && !relatedThreadsHasMore ? (
                <div className="deck-manager-related-dialog__empty">
                  <FaCommentAlt aria-hidden="true" />
                  <strong>{t('deck.related.emptyTitle')}</strong>
                  <span>{t('deck.related.emptyDescription')}</span>
                </div>
              ) : null}

              {relatedThreads.length > 0 ? (
                <ul aria-label={t('deck.related.listLabel')} className="deck-manager-related-list">
                  {relatedThreads.map((thread) => {
                    const title = thread.title || t('chat.history.fallbackTitle');
                    const deleting = deletingThreadId === thread.id;
                    return (
                      <li className="deck-manager-related-list__item" key={thread.id}>
                        <span className="deck-manager-related-list__icon" aria-hidden="true">
                          <FaCommentAlt />
                        </span>
                        <span className="deck-manager-related-list__copy">
                          <strong title={title}>{title}</strong>
                          <span>{formatUpdatedAt(thread.updated_at)}</span>
                        </span>
                        <button
                          aria-label={t('deck.related.deleteConversation', { title })}
                          className="deck-manager-related-list__delete"
                          disabled={Boolean(deletingThreadId)}
                          onClick={() => void deleteRelatedThread(thread)}
                          title={t('chat.history.deleteThread')}
                          type="button"
                        >
                          <FaTrashAlt aria-hidden="true" />
                          <span>{deleting ? t('deck.related.deleting') : t('deck.related.delete')}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              ) : null}

              {relatedThreadsHasMore ? (
                <button
                  className="deck-manager-secondary-action deck-manager-related-dialog__more"
                  disabled={relatedThreadsLoadingMore}
                  onClick={() => void loadRelatedThreads(relatedDeck, relatedThreads.length)}
                  type="button"
                >
                  {relatedThreadsLoadingMore ? t('deck.related.loadingMore') : t('deck.related.loadMore')}
                </button>
              ) : null}
            </div>

            <footer className="deck-manager-related-dialog__footer">
              <p>{relatedThreadsError
                ? t('deck.related.unknownHint')
                : relatedThreads.length > 0 || relatedThreadsHasMore
                  ? t('deck.related.deleteHint')
                  : t('deck.related.readyHint')}</p>
              <div>
                <button className="deck-manager-secondary-action" onClick={closeRelatedThreads} type="button">
                  {t('deck.related.close')}
                </button>
                <button
                  className="deck-manager-related-dialog__delete-deck"
                  disabled={relatedThreadsLoading
                    || Boolean(relatedThreadsError)
                    || relatedThreads.length > 0
                    || relatedThreadsHasMore}
                  onClick={deleteDeckAfterThreads}
                  type="button"
                >
                  {t('deck.related.deleteDeck')}
                </button>
              </div>
            </footer>
          </section>
        </div>
      )}
    </div>
  );
}
