// [Input] Persisted Deck/Agent DTOs, task-mode selection, and DeckManager action callbacks.
// [Output] Accessible use/create Deck panels without owning persistence or version facts.
// [Pos] Presentational Deck management panels in frontend/src/components/deck.
// [Sync] 2026-08-15: split Deck use and Deck creation tasks; version labels stay absent until
//                    the Admin-owned aggregate revision capability is available.
import type { CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import type { Deck, Voice } from '../../api/voiceApi';
import type { ActiveChatVoice } from '../../lib/chat-schema';
import { COLORS, iconMap } from '../deckVisuals';
import './DeckManagerPanels.css';

export type DeckManagerMode = 'use' | 'create';

interface DeckManagerModeTabsProps {
  mode: DeckManagerMode;
  onChange: (mode: DeckManagerMode) => void;
}

export function DeckManagerModeTabs({ mode, onChange }: DeckManagerModeTabsProps) {
  const { t } = useTranslation();

  return (
    <div className="deck-manager-mode">
      <div className="deck-manager-mode__tabs" role="tablist" aria-label={t('deck.mode.ariaLabel')}>
        {(['use', 'create'] as const).map((candidate) => (
          <button
            aria-controls={`deck-manager-panel-${candidate}`}
            aria-selected={mode === candidate}
            className="deck-manager-mode__tab"
            id={`deck-manager-tab-${candidate}`}
            key={candidate}
            onClick={() => onChange(candidate)}
            role="tab"
            tabIndex={mode === candidate ? 0 : -1}
            type="button"
          >
            {t(`deck.mode.${candidate}.label`)}
          </button>
        ))}
      </div>
      <p className="deck-manager-mode__description">
        {t(`deck.mode.${mode}.description`)}
      </p>
    </div>
  );
}

interface DeckUsePanelProps {
  decks: Deck[];
  selectedVoiceByDeck: Record<string, string | null>;
  onSelectVoice: (deckId: string, voiceId: string | null) => void;
  onUseDeck?: (deckId: string, voice: ActiveChatVoice) => void;
}

function voiceToChatVoice(voice: Voice): ActiveChatVoice {
  return {
    id: voice.id,
    name: voice.name,
    systemPrompt: voice.system_prompt,
    icon: voice.icon,
    color: voice.color,
  };
}

export function DeckUsePanel({
  decks,
  selectedVoiceByDeck,
  onSelectVoice,
  onUseDeck,
}: DeckUsePanelProps) {
  const { t } = useTranslation();
  const enabledDecks = decks.filter((deck) => deck.enabled);

  return (
    <section
      aria-labelledby="deck-manager-tab-use"
      className="deck-manager-panel"
      id="deck-manager-panel-use"
      role="tabpanel"
    >
      <div className="deck-manager-panel__heading">
        <h2>{t('deck.sections.availableDecks')}</h2>
        <span>{t('deck.sections.availableDecksCount', { count: enabledDecks.length })}</span>
      </div>

      {enabledDecks.length === 0 ? (
        <p className="deck-manager-empty">{t('deck.use.empty')}</p>
      ) : (
        <div className="deck-manager-grid">
          {enabledDecks.map((deck) => {
            const Icon = iconMap[deck.icon as keyof typeof iconMap] || iconMap.brain;
            const accent = COLORS[deck.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
            const enabledVoices = (deck.voices || []).filter((voice) => voice.enabled);
            const selectedVoiceId = selectedVoiceByDeck[deck.id];
            const selectedVoice = enabledVoices.find((voice) => voice.id === selectedVoiceId)
              ?? enabledVoices[0]
              ?? null;

            return (
              <article
                className="deck-manager-card deck-manager-card--use"
                data-deck-card-id={deck.id}
                data-deck-card-kind="use"
                key={deck.id}
                style={{ '--deck-accent': accent } as CSSProperties}
              >
                <div className="deck-manager-card__identity">
                  <span className="deck-manager-card__icon" aria-hidden="true"><Icon size={22} /></span>
                  <div className="deck-manager-card__copy">
                    <div className="deck-manager-card__title-row">
                      <h3>{deck.name}</h3>
                      <span className="deck-manager-card__type">
                        {t(`deck.labels.agentType.${deck.agent_type === 'dream' ? 'dream' : 'chat'}`)}
                      </span>
                    </div>
                    <p>{deck.description || t('deck.labels.noDescription')}</p>
                  </div>
                </div>

                {enabledVoices.length > 0 ? (
                  <label className="deck-manager-agent-field">
                    <span>{t('deck.use.agentLabel')}</span>
                    <select
                      aria-label={t('deck.use.agentSelectAria', { deck: deck.name })}
                      onChange={(event) => onSelectVoice(deck.id, event.target.value)}
                      value={selectedVoice?.id ?? ''}
                    >
                      {enabledVoices.map((voice) => (
                        <option key={voice.id} value={voice.id}>{voice.name}</option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <p className="deck-manager-card__notice">{t('deck.use.noAgent')}</p>
                )}

                <button
                  className="deck-manager-primary-action"
                  disabled={!selectedVoice || !onUseDeck}
                  onClick={() => selectedVoice && onUseDeck?.(deck.id, voiceToChatVoice(selectedVoice))}
                  type="button"
                >
                  {t('deck.actions.useInChat')}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

interface DeckCreatorPanelProps {
  decks: Deck[];
  publishedDecks: Deck[];
  creatingDeck: boolean;
  onCreateDeck: () => void;
  onOpenDeck: (deckId: string) => void;
  onToggleDeck: (deckId: string, enabled: boolean) => void;
  onForkDeck: (deckId: string) => void;
  onSyncDeck: (deckId: string) => void;
  onPublishDeck: (deck: Deck) => void;
  onUnpublishDeck: (deckId: string) => void;
  onDeleteDeck: (deckId: string) => void;
}

export function DeckCreatorPanel({
  decks,
  publishedDecks,
  creatingDeck,
  onCreateDeck,
  onOpenDeck,
  onToggleDeck,
  onForkDeck,
  onSyncDeck,
  onPublishDeck,
  onUnpublishDeck,
  onDeleteDeck,
}: DeckCreatorPanelProps) {
  const { t } = useTranslation();

  return (
    <section
      aria-labelledby="deck-manager-tab-create"
      className="deck-manager-panel"
      id="deck-manager-panel-create"
      role="tabpanel"
    >
      <div className="deck-manager-panel__heading deck-manager-panel__heading--action">
        <div>
          <h2>{t('deck.sections.myDecks')}</h2>
          <span>{t('deck.creator.scopeHint')}</span>
        </div>
        <button
          className="deck-manager-primary-action deck-manager-primary-action--compact"
          disabled={creatingDeck}
          onClick={onCreateDeck}
          type="button"
        >
          {creatingDeck ? t('deck.actions.creating') : t('deck.actions.create')}
        </button>
      </div>

      <div className="deck-manager-grid">
        {decks.map((deck) => {
          const isSystem = Boolean(deck.is_system);
          const publishDisabled = !deck.published && deck.can_publish === false;
          const Icon = iconMap[deck.icon as keyof typeof iconMap] || iconMap.brain;
          const accent = COLORS[deck.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
          const voiceCount = deck.voice_count || deck.voices?.length || 0;

          return (
            <article
              className="deck-manager-card deck-manager-card--creator"
              data-deck-card-id={deck.id}
              data-deck-card-kind="owned"
              key={deck.id}
              style={{ '--deck-accent': isSystem ? 'var(--color-border-paper)' : accent } as CSSProperties}
            >
              <div className="deck-manager-card__identity">
                <span className="deck-manager-card__icon" aria-hidden="true"><Icon size={22} /></span>
                <div className="deck-manager-card__copy">
                  <div className="deck-manager-card__title-row">
                    <h3>{deck.name}</h3>
                    {isSystem && <span className="deck-manager-card__type">{t('deck.labels.system')}</span>}
                  </div>
                  <p>{deck.description || t('deck.labels.noDescription')}</p>
                  <span className="deck-manager-card__meta">{t('deck.labels.voiceCount', { count: voiceCount })}</span>
                </div>
              </div>

              <div className="deck-manager-card__actions">
                <button
                  className="deck-manager-secondary-action"
                  onClick={() => onOpenDeck(deck.id)}
                  type="button"
                >
                  {isSystem ? t('deck.actions.inspect') : t('deck.actions.edit')}
                </button>
                {isSystem ? (
                  <button className="deck-manager-secondary-action" onClick={() => onForkDeck(deck.id)} type="button">
                    {t('deck.actions.fork')}
                  </button>
                ) : (
                  <>
                    <button
                      aria-checked={deck.enabled}
                      className="deck-manager-switch"
                      onClick={() => onToggleDeck(deck.id, deck.enabled)}
                      role="switch"
                      type="button"
                    >
                      <span aria-hidden="true" />
                      {deck.enabled ? t('deck.actions.disable') : t('deck.actions.enable')}
                    </button>
                    {deck.parent_id && (
                      <button className="deck-manager-secondary-action" onClick={() => onSyncDeck(deck.id)} type="button">
                        {t('deck.actions.sync')}
                      </button>
                    )}
                    <button
                      className="deck-manager-secondary-action"
                      disabled={publishDisabled}
                      onClick={() => onPublishDeck(deck)}
                      title={publishDisabled ? t('deck.messages.defaultDeckPublishForbidden') : undefined}
                      type="button"
                    >
                      {deck.published
                        ? t('deck.actions.unpublish')
                        : publishDisabled
                          ? t('deck.actions.publishUnavailable')
                          : t('deck.actions.publish')}
                    </button>
                    <button className="deck-manager-danger-action" onClick={() => onDeleteDeck(deck.id)} type="button">
                      {t('deck.actions.delete')}
                    </button>
                  </>
                )}
              </div>
            </article>
          );
        })}
      </div>

      <div className="deck-manager-publications">
        <div className="deck-manager-panel__heading">
          <h2>{t('deck.sections.publishedByMe', { count: publishedDecks.length })}</h2>
        </div>
        {publishedDecks.length === 0 ? (
          <p className="deck-manager-empty">{t('deck.publishedByMeEmpty')}</p>
        ) : (
          <div className="deck-manager-grid">
            {publishedDecks.map((deck) => {
              const Icon = iconMap[deck.icon as keyof typeof iconMap] || iconMap.brain;
              const accent = COLORS[deck.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
              return (
                <article
                  className="deck-manager-card"
                  data-deck-card-id={deck.id}
                  data-deck-card-kind="published-by-me"
                  key={deck.id}
                  style={{ '--deck-accent': accent } as CSSProperties}
                >
                  <div className="deck-manager-card__identity">
                    <span className="deck-manager-card__icon" aria-hidden="true"><Icon size={22} /></span>
                    <div className="deck-manager-card__copy">
                      <h3>{deck.name}</h3>
                      <p>{deck.description || t('deck.labels.noDescription')}</p>
                      <span className="deck-manager-card__meta">
                        {t('deck.publishedByMeMeta', {
                          voices: deck.voice_count || 0,
                          installs: deck.install_count || 0,
                        })}
                      </span>
                    </div>
                  </div>
                  <button className="deck-manager-secondary-action" onClick={() => onUnpublishDeck(deck.id)} type="button">
                    {t('deck.actions.unpublish')}
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
