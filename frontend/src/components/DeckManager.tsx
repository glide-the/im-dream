// [Input] Existing Deck/Agent CRUD APIs, PDF-led home, original create defaults, and pre-refactor maintenance editor.
// [Output] Resilient Deck home/Work manager with create-first editing and related Chat cleanup through production APIs.
// [Pos] Deck manager orchestration node in frontend/src/components.
// [Sync] 2026-08-16: restore the pre-01a00576 Deck maintenance scope without restoring its superseded page modes.
// [Sync] 2026-08-16: propagate form mutation failures so content-version state refreshes only after durable writes.
// [Sync] 2026-08-17: keep published-clean home visibility separate from Settings / Work full inventory without duplicating APIs.
// [Sync] 2026-08-17: orchestrate Deck-scoped Chat history reads/deletes for the Work More menu.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  createDeck,
  createVoice,
  deleteDeck,
  deleteVoice,
  getDeck,
  listDecks,
  reconcileDefaultDeckPlugin,
  syncDeck,
  updateDeck,
  updateVoice,
  type Deck,
  type Voice,
} from '../api/voiceApi';
import { updateDeckAgentType, type DeckAgentType } from '../api/deckPluginApi';
import { deleteChatThread, listChatThreads } from '../api/chatHistoryApi';
import { DEFAULT_DECK_CREATE_VISUAL } from '../constants/deck';
import type { ActiveChatVoice } from '../lib/chat-schema';
import DeckEditorModal from './DeckEditorModal';
import { DeckLaunchPanel, DeckSettingsPanel } from './deck/DeckManagerPanels';

interface Props {
  onUpdate?: () => void;
  onChatWithDeck?: (deckId: string, voiceInfo: ActiveChatVoice) => void;
  onOpenSettings?: () => void;
  surface?: 'launcher' | 'settings';
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export default function DeckManager({
  onUpdate,
  onChatWithDeck,
  onOpenSettings = () => undefined,
  surface = 'launcher',
}: Props) {
  const { t } = useTranslation();
  const [decks, setDecks] = useState<Deck[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshingDecks, setRefreshingDecks] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [busyDeckId, setBusyDeckId] = useState<string | null>(null);
  const [activeDeckId, setActiveDeckId] = useState<string | null>(null);
  const [creatingDeck, setCreatingDeck] = useState(false);
  const [creatingVoice, setCreatingVoice] = useState<string | null>(null);
  const [selectedVoiceByDeck, setSelectedVoiceByDeck] = useState<Record<string, string | null>>({});
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const loadDecks = useCallback(async (
    options: { initial?: boolean; preserveScroll?: boolean } = {},
  ) => {
    const savedScrollTop = options.preserveScroll && scrollContainerRef.current
      ? scrollContainerRef.current.scrollTop
      : 0;

    try {
      if (options.initial) {
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
      const decksWithVoices = await Promise.all(fetchedDecks.map(async (deck) => {
        try {
          return await getDeck(deck.id);
        } catch (deckError) {
          console.error(`Failed to load agents for Deck ${deck.id}:`, deckError);
          return deck;
        }
      }));
      setDecks(decksWithVoices);
      setError(null);
      setRefreshError(null);

      if (options.preserveScroll && scrollContainerRef.current) {
        requestAnimationFrame(() => {
          scrollContainerRef.current?.scrollTo({ top: savedScrollTop });
        });
      }
    } catch (loadError) {
      const message = getErrorMessage(loadError, t('deck.messages.loadFailed'));
      if (options.initial) setError(message);
      else setRefreshError(message);
      throw loadError;
    } finally {
      if (options.initial) setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadDecks({ initial: true }).catch(() => undefined);
  }, [loadDecks]);

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

  async function refreshAfterMutation() {
    await loadDecks({ preserveScroll: true });
    onUpdate?.();
  }

  async function handleCreateDeck() {
    if (creatingDeck) return;
    setCreatingDeck(true);
    setOperationError(null);
    try {
      const created = await createDeck({
        name: t('deck.defaults.newName'),
        description: t('deck.defaults.newDescription'),
        ...DEFAULT_DECK_CREATE_VISUAL,
      });
      await refreshAfterMutation();
      setActiveDeckId(created.deck_id);
    } catch (createError) {
      setOperationError(getErrorMessage(createError, t('deck.messages.createFailed')));
    } finally {
      setCreatingDeck(false);
    }
  }

  async function handleUpdateDeck(deckId: string, data: Partial<Deck>) {
    setBusyDeckId(deckId);
    setOperationError(null);
    try {
      await updateDeck(deckId, data);
      await refreshAfterMutation();
    } catch (updateError) {
      const message = getErrorMessage(updateError, t('deck.messages.updateFailed'));
      setOperationError(message);
      throw new Error(message);
    } finally {
      setBusyDeckId(null);
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

  async function handleAddVoice(deckId: string) {
    setCreatingVoice(deckId);
    setOperationError(null);
    try {
      const { voice_id: voiceId } = await createVoice({
        deck_id: deckId,
        name: 'New Voice',
        system_prompt: 'You are a helpful assistant.',
        icon: 'brain',
        color: 'blue',
      });
      setSelectedVoiceByDeck((previous) => ({ ...previous, [deckId]: voiceId }));
      await refreshAfterMutation();
    } catch (createError) {
      const message = getErrorMessage(createError, t('deck.messages.createAgentFailed'));
      setOperationError(message);
      throw new Error(message);
    } finally {
      setCreatingVoice(null);
    }
  }

  async function handleUpdateVoice(voiceId: string, data: Partial<Voice>) {
    setOperationError(null);
    try {
      await updateVoice(voiceId, data);
      await refreshAfterMutation();
    } catch (updateError) {
      const message = getErrorMessage(updateError, t('deck.messages.updateAgentFailed'));
      setOperationError(message);
      throw new Error(message);
    }
  }

  async function handleToggleVoice(voiceId: string, currentEnabled: boolean) {
    await handleUpdateVoice(voiceId, { enabled: !currentEnabled });
  }

  async function handleDeleteVoice(voiceId: string) {
    if (!confirm(t('deck.confirm.deleteAgent'))) return;
    setOperationError(null);
    try {
      await deleteVoice(voiceId);
      await refreshAfterMutation();
    } catch (deleteError) {
      const message = getErrorMessage(deleteError, t('deck.messages.deleteAgentFailed'));
      setOperationError(message);
      throw new Error(message);
    }
  }

  async function handleToggleDeck(deckId: string, currentEnabled: boolean) {
    setBusyDeckId(deckId);
    setOperationError(null);
    try {
      await updateDeck(deckId, { enabled: !currentEnabled });
      await refreshAfterMutation();
    } catch (toggleError) {
      setOperationError(getErrorMessage(toggleError, t('deck.messages.toggleFailed')));
    } finally {
      setBusyDeckId(null);
    }
  }

  async function handleDeleteDeck(deckId: string) {
    if (!confirm(t('deck.confirm.delete'))) return;
    setBusyDeckId(deckId);
    setOperationError(null);
    try {
      await deleteDeck(deckId);
      if (activeDeckId === deckId) setActiveDeckId(null);
      await refreshAfterMutation();
    } catch (deleteError) {
      setOperationError(getErrorMessage(deleteError, t('deck.messages.deleteFailed')));
    } finally {
      setBusyDeckId(null);
    }
  }

  const handleLoadRelatedThreads = useCallback((deckId: string, offset: number) => (
    listChatThreads({ deckId, limit: 20, offset })
  ), []);

  const handleDeleteRelatedThread = useCallback(async (threadId: string) => {
    await deleteChatThread(threadId);
  }, []);

  async function handleSyncDeck(deckId: string) {
    if (!confirm(t('deck.confirm.sync'))) return;
    setBusyDeckId(deckId);
    setOperationError(null);
    try {
      await syncDeck(deckId);
      await refreshAfterMutation();
    } catch (syncError) {
      setOperationError(getErrorMessage(syncError, t('deck.messages.syncFailed')));
    } finally {
      setBusyDeckId(null);
    }
  }

  async function handleRefreshDecks() {
    setRefreshingDecks(true);
    setRefreshError(null);
    try {
      await loadDecks({ preserveScroll: true });
    } catch {
      // `loadDecks` keeps the last successful list visible and owns the recoverable error copy.
    } finally {
      setRefreshingDecks(false);
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
        <button
          className="deck-manager-primary-action deck-manager-primary-action--compact"
          onClick={() => void loadDecks({ initial: true }).catch(() => undefined)}
          type="button"
        >
          {t('deck.actions.retry')}
        </button>
      </div>
    );
  }

  const activeDeck = decks.find((deck) => deck.id === activeDeckId) ?? null;

  return (
    <div className={`deck-manager-shell deck-manager-shell--${surface}`}>
      <div className="deck-manager-shell__scroll" ref={scrollContainerRef}>
        <div className="deck-manager-shell__content">
          {surface === 'launcher' ? (
            <DeckLaunchPanel
              creatingDeck={creatingDeck}
              decks={decks}
              onCreateDeck={() => void handleCreateDeck()}
              onOpenDeck={setActiveDeckId}
              onOpenSettings={onOpenSettings}
              onRefreshDecks={() => void handleRefreshDecks()}
              operationError={operationError}
              refreshError={refreshError}
              refreshingDecks={refreshingDecks}
            />
          ) : (
            <DeckSettingsPanel
              busyDeckId={busyDeckId}
              creatingDeck={creatingDeck}
              decks={decks}
              onCreateDeck={() => void handleCreateDeck()}
              onDeleteDeck={(deckId) => void handleDeleteDeck(deckId)}
              onOpenDeck={setActiveDeckId}
              onLoadRelatedThreads={handleLoadRelatedThreads}
              onDeleteRelatedThread={handleDeleteRelatedThread}
              onRefreshDecks={() => void handleRefreshDecks()}
              onSyncDeck={(deckId) => void handleSyncDeck(deckId)}
              onToggleDeck={(deckId, enabled) => void handleToggleDeck(deckId, enabled)}
              operationError={operationError}
              refreshError={refreshError}
              refreshingDecks={refreshingDecks}
            />
          )}
        </div>
      </div>

      {activeDeck && (
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
          onVersionChanged={refreshAfterMutation}
          selectedVoiceId={selectedVoiceByDeck[activeDeck.id] || activeDeck.voices?.[0]?.id || null}
        />
      )}
    </div>
  );
}
