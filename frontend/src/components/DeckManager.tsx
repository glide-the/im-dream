// [Input] Voice Deck and capability-backed Agent type APIs, task-mode panels, and editor modal.
// [Output] Deck workspace split into use and creator tasks; creator writes remain server-owned.
// [Pos] deck-manager-view node in frontend/src/components.
// [Sync] 2026-08-15: separate "use Deck" from "create Deck" without inventing revision facts;
//                    move presentation into deck/DeckManagerPanels and keep data/actions here.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  createDeck,
  createVoice,
  deleteDeck,
  deleteVoice,
  forkDeck,
  getDeck,
  listDecks,
  publishDeck,
  reconcileDefaultDeckPlugin,
  syncDeck,
  updateDeck,
  updateVoice,
  type Deck,
  type Voice,
} from '../api/voiceApi';
import { updateDeckAgentType, type DeckAgentType } from '../api/deckPluginApi';
import type { ActiveChatVoice } from '../lib/chat-schema';
import DeckEditorModal from './DeckEditorModal';
import {
  DeckCreatorPanel,
  DeckManagerModeTabs,
  DeckUsePanel,
  type DeckManagerMode,
} from './deck/DeckManagerPanels';

interface Props {
  onUpdate?: () => void;
  onChatWithDeck?: (deckId: string, voiceInfo: ActiveChatVoice) => void;
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export default function DeckManager({ onUpdate, onChatWithDeck }: Props) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<DeckManagerMode>('use');
  const [decks, setDecks] = useState<Deck[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingDeck, setCreatingDeck] = useState(false);
  const [creatingVoice, setCreatingVoice] = useState<string | null>(null);
  const [publishWarning, setPublishWarning] = useState<string | null>(null);
  const [selectedVoiceByDeck, setSelectedVoiceByDeck] = useState<Record<string, string | null>>({});
  const [activeDeckId, setActiveDeckId] = useState<string | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void loadDecks();
  }, []);

  const publishedDecks = useMemo(
    () => decks.filter((deck) => deck.published),
    [decks],
  );

  useEffect(() => {
    setSelectedVoiceByDeck((previous) => {
      let changed = false;
      const next = { ...previous };

      decks.forEach((deck) => {
        const voiceIds = (deck.voices || []).filter((voice) => voice.enabled).map((voice) => voice.id);
        const currentSelection = next[deck.id];
        if (voiceIds.length === 0) {
          if (currentSelection !== null) {
            next[deck.id] = null;
            changed = true;
          }
        } else if (!currentSelection || !voiceIds.includes(currentSelection)) {
          next[deck.id] = voiceIds[0];
          changed = true;
        }
      });

      return changed ? next : previous;
    });
  }, [decks]);

  async function loadDecks(preserveScroll = false) {
    const savedScrollTop = preserveScroll && scrollContainerRef.current
      ? scrollContainerRef.current.scrollTop
      : 0;

    try {
      if (!preserveScroll) {
        setLoading(true);
        try {
          await reconcileDefaultDeckPlugin();
        } catch (reconcileError) {
          console.warn(
            'Default Deck plugin reconciliation is temporarily unavailable; loading persisted Decks.',
            reconcileError,
          );
        }
      }
      const fetchedDecks = await listDecks();
      const decksWithVoices = await Promise.all(
        fetchedDecks.map(async (deck) => {
          try {
            return await getDeck(deck.id);
          } catch (deckError) {
            console.error(`Failed to load voices for deck ${deck.id}:`, deckError);
            return deck;
          }
        }),
      );
      setDecks(decksWithVoices);
      setError(null);

      if (preserveScroll && scrollContainerRef.current) {
        setTimeout(() => {
          scrollContainerRef.current?.scrollTo({ top: savedScrollTop });
        }, 0);
      }
    } catch (loadError) {
      console.error('Failed to load decks:', loadError);
      setError(getErrorMessage(loadError, 'Failed to load decks'));
    } finally {
      if (!preserveScroll) setLoading(false);
    }
  }

  function handleModeChange(nextMode: DeckManagerMode) {
    setMode(nextMode);
    setActiveDeckId(null);
    setPublishWarning(null);
  }

  async function handleForkDeck(deckId: string) {
    try {
      await forkDeck(deckId);
      await loadDecks(true);
      onUpdate?.();
    } catch (forkError) {
      alert(`Failed to fork deck: ${getErrorMessage(forkError, 'Unknown error')}`);
    }
  }

  async function handleToggleDeck(deckId: string, currentEnabled: boolean) {
    try {
      await updateDeck(deckId, { enabled: !currentEnabled });
      await loadDecks(true);
      onUpdate?.();
    } catch (toggleError) {
      alert(`Failed to toggle deck: ${getErrorMessage(toggleError, 'Unknown error')}`);
    }
  }

  async function handleUpdateDeck(deckId: string, data: Partial<Deck>) {
    try {
      await updateDeck(deckId, data);
      await loadDecks(true);
      onUpdate?.();
    } catch (updateError) {
      alert(`Failed to update deck: ${getErrorMessage(updateError, 'Unknown error')}`);
    }
  }

  async function handleUpdateAgentType(
    deckId: string,
    agentType: DeckAgentType,
    expectedBindingRevision: number,
  ): Promise<number> {
    const saved = await updateDeckAgentType(deckId, agentType, expectedBindingRevision);
    setDecks((current) => current.map((deck) => deck.id === deckId ? {
      ...deck,
      agent_type: saved.agent_type,
      agent_type_revision: saved.binding_revision,
    } : deck));
    onUpdate?.();
    return saved.binding_revision;
  }

  async function handleDeleteDeck(deckId: string) {
    if (!confirm(t('deck.confirm.delete'))) return;
    try {
      await deleteDeck(deckId);
      await loadDecks(true);
      onUpdate?.();
    } catch (deleteError) {
      alert(`Failed to delete deck: ${getErrorMessage(deleteError, 'Unknown error')}`);
    }
  }

  async function handleSyncDeck(deckId: string) {
    if (!confirm(t('deck.confirm.sync'))) return;
    try {
      const result = await syncDeck(deckId);
      alert(`✅ Synced ${result.synced_voices} voices with original template`);
      await loadDecks(true);
      onUpdate?.();
    } catch (syncError) {
      alert(`Failed to sync deck: ${getErrorMessage(syncError, 'Unknown error')}`);
    }
  }

  async function handleToggleVoice(voiceId: string, currentEnabled: boolean) {
    try {
      await updateVoice(voiceId, { enabled: !currentEnabled });
      await loadDecks(true);
      onUpdate?.();
    } catch (toggleError) {
      alert(`Failed to toggle voice: ${getErrorMessage(toggleError, 'Unknown error')}`);
    }
  }

  async function handleUpdateVoice(voiceId: string, data: Partial<Voice>) {
    try {
      await updateVoice(voiceId, data);
      await loadDecks(true);
      onUpdate?.();
    } catch (updateError) {
      alert(`Failed to update voice: ${getErrorMessage(updateError, 'Unknown error')}`);
    }
  }

  async function handleDeleteVoice(voiceId: string) {
    if (!confirm(t('deck.confirm.deleteAgent'))) return;
    try {
      await deleteVoice(voiceId);
      await loadDecks(true);
      onUpdate?.();
    } catch (deleteError) {
      alert(`Failed to delete voice: ${getErrorMessage(deleteError, 'Unknown error')}`);
    }
  }

  async function handleCreateDeck() {
    setCreatingDeck(true);
    try {
      const newDeck = await createDeck({
        name: 'New Deck',
        description: 'Describe your deck here',
        icon: 'brain',
        color: 'blue',
      });
      await loadDecks(true);
      setActiveDeckId(newDeck.deck_id);
      onUpdate?.();
    } catch (createError) {
      alert(`Failed to create deck: ${getErrorMessage(createError, 'Unknown error')}`);
    } finally {
      setCreatingDeck(false);
    }
  }

  async function handleAddVoice(deckId: string) {
    setCreatingVoice(deckId);
    try {
      const { voice_id: newVoiceId } = await createVoice({
        deck_id: deckId,
        name: 'New Voice',
        system_prompt: 'You are a helpful assistant.',
        icon: 'brain',
        color: 'blue',
      });
      setSelectedVoiceByDeck((previous) => ({ ...previous, [deckId]: newVoiceId }));
      await loadDecks(true);
      onUpdate?.();
    } catch (createError) {
      alert(`Failed to create voice: ${getErrorMessage(createError, 'Unknown error')}`);
    } finally {
      setCreatingVoice(null);
    }
  }

  function handlePublishClick(deck: Deck) {
    if (deck.published) {
      void handlePublishToggle(deck.id);
      return;
    }
    if (deck.can_publish === false) {
      alert(t('deck.messages.defaultDeckPublishForbidden'));
      return;
    }
    setPublishWarning(deck.id);
  }

  async function handlePublishToggle(deckId: string) {
    try {
      const result = await publishDeck(deckId);
      alert(result.published ? t('deck.messages.publishSuccess') : t('deck.messages.unpublishSuccess'));
      await loadDecks(true);
      onUpdate?.();
    } catch (publishError) {
      alert(`Failed: ${getErrorMessage(publishError, 'Unknown error')}`);
    } finally {
      setPublishWarning(null);
    }
  }

  if (loading) {
    return (
      <div className="deck-manager-status" aria-live="polite">
        <span className="deck-manager-status__spinner" aria-hidden="true" />
        {t('deck.loading')}
      </div>
    );
  }

  if (error) {
    return (
      <div className="deck-manager-status" role="alert">
        <span>{error}</span>
        <button className="deck-manager-primary-action deck-manager-primary-action--compact" onClick={() => void loadDecks()} type="button">
          {t('deck.actions.retry')}
        </button>
      </div>
    );
  }

  const activeDeck = decks.find((deck) => deck.id === activeDeckId) || null;

  return (
    <div className="deck-manager-shell" data-deck-manager-mode={mode}>
      <div className="deck-manager-shell__scroll" ref={scrollContainerRef}>
        <div className="deck-manager-shell__content">
          <header className="deck-manager-shell__header">
            <h1>{t('deck.heading')}</h1>
            <p>{t('deck.subheading')}</p>
          </header>

          <DeckManagerModeTabs mode={mode} onChange={handleModeChange} />

          {mode === 'use' ? (
            <DeckUsePanel
              decks={decks}
              onSelectVoice={(deckId, voiceId) => setSelectedVoiceByDeck((previous) => ({
                ...previous,
                [deckId]: voiceId,
              }))}
              onUseDeck={onChatWithDeck}
              selectedVoiceByDeck={selectedVoiceByDeck}
            />
          ) : (
            <DeckCreatorPanel
              creatingDeck={creatingDeck}
              decks={decks}
              onCreateDeck={() => void handleCreateDeck()}
              onDeleteDeck={(deckId) => void handleDeleteDeck(deckId)}
              onForkDeck={(deckId) => void handleForkDeck(deckId)}
              onOpenDeck={setActiveDeckId}
              onPublishDeck={handlePublishClick}
              onSyncDeck={(deckId) => void handleSyncDeck(deckId)}
              onToggleDeck={(deckId, enabled) => void handleToggleDeck(deckId, enabled)}
              onUnpublishDeck={(deckId) => void handlePublishToggle(deckId)}
              publishedDecks={publishedDecks}
            />
          )}
        </div>
      </div>

      {mode === 'create' && activeDeck && (
        <DeckEditorModal
          creatingVoiceId={creatingVoice}
          deck={activeDeck}
          isSystem={Boolean(activeDeck.is_system)}
          onAddVoice={handleAddVoice}
          onChatWithDeck={onChatWithDeck}
          onClose={() => setActiveDeckId(null)}
          onDeleteVoice={handleDeleteVoice}
          onSelectVoice={(voiceId) => setSelectedVoiceByDeck((previous) => ({
            ...previous,
            [activeDeck.id]: voiceId,
          }))}
          onToggleVoice={handleToggleVoice}
          onUpdateAgentType={handleUpdateAgentType}
          onUpdateDeck={handleUpdateDeck}
          onUpdateVoice={handleUpdateVoice}
          selectedVoiceId={selectedVoiceByDeck[activeDeck.id] || activeDeck.voices?.[0]?.id || null}
        />
      )}

      {publishWarning && (
        <div className="deck-manager-dialog-backdrop" onClick={() => setPublishWarning(null)}>
          <div
            aria-labelledby="deck-publish-warning-title"
            aria-modal="true"
            className="deck-manager-dialog"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <h2 id="deck-publish-warning-title">{t('deck.publishWarning.heading')}</h2>
            <p dangerouslySetInnerHTML={{ __html: t('deck.publishWarning.body') }} />
            <p className="deck-manager-dialog__warning">{t('deck.publishWarning.note')}</p>
            <div className="deck-manager-dialog__actions">
              <button className="deck-manager-secondary-action" onClick={() => setPublishWarning(null)} type="button">
                {t('deck.publishWarning.cancel')}
              </button>
              <button className="deck-manager-primary-action deck-manager-primary-action--compact" onClick={() => void handlePublishToggle(publishWarning)} type="button">
                {t('deck.publishWarning.confirm')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
