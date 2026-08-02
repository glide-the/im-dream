// [Input] Enabled Deck summaries and the current Dream chat selection.
// [Output] Render the compact, single-select Deck control used by AIInputDock.
// [Pos] deck-domain adapter between Dream chat composition and Deck configuration.
import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import type { Deck } from '../../api/voiceApi';

interface DeckChatSelectorProps {
  decks: Deck[];
  selectedDeckId?: string;
  onChange?: (deckId: string | undefined) => void;
  loading?: boolean;
  error?: string | null;
  locked?: boolean;
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
  const selectId = useId();
  const language = (i18n.language || 'en').split('-')[0];
  const selectedDeck = decks.find((deck) => deck.id === selectedDeckId);
  const selectedLabel = selectedDeck
    ? (language === 'zh' ? selectedDeck.name_zh : selectedDeck.name_en) || selectedDeck.name
    : t('chat.deck.none');

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
    <label
      htmlFor={selectId}
      title={error || t('chat.deck.selectTitle')}
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
        padding: '0 0.45rem 0 0.7rem',
        fontSize: '0.76rem',
      }}
    >
      <span aria-hidden="true" style={{ color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>Deck</span>
      <select
        id={selectId}
        aria-label={t('chat.deck.selectAria')}
        value={selectedDeckId ?? ''}
        disabled={loading}
        onChange={(event) => onChange?.(event.target.value || undefined)}
        style={{
          minWidth: 0,
          maxWidth: '10rem',
          border: 'none',
          outline: 'none',
          background: 'transparent',
          color: 'var(--color-text-primary)',
          font: 'inherit',
          cursor: loading ? 'wait' : 'pointer',
        }}
      >
        <option value="">{loading ? t('chat.deck.loading') : t('chat.deck.none')}</option>
        {decks.map((deck) => {
          const label = (language === 'zh' ? deck.name_zh : deck.name_en) || deck.name;
          return <option key={deck.id} value={deck.id}>{label}</option>;
        })}
      </select>
    </label>
  );
}
