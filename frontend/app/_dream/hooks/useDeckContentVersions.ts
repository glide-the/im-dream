// [Input] Deck aggregate version transport and a stable Deck id.
// [Output] Recoverable draft state/history plus preview/commit CAS actions.
// [Pos] Deck editor content-version lifecycle hook.
// [Sync] 2026-08-16: introduce explicit content-version iteration state.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  commitDeckContentVersion,
  DeckVersionApiError,
  getDeckContentVersionState,
  listDeckContentVersions,
  previewDeckContentVersion,
  type DeckContentVersionHistory,
  type DeckContentVersionPreview,
  type DeckContentVersionState,
} from '../api/deckVersionApi';

export function useDeckContentVersions(deckId: string) {
  const [state, setState] = useState<DeckContentVersionState | null>(null);
  const [history, setHistory] = useState<DeckContentVersionHistory | null>(null);
  const [preview, setPreview] = useState<DeckContentVersionPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [capabilityUnavailable, setCapabilityUnavailable] = useState(false);
  const requestId = useRef(0);

  const refresh = useCallback(async (includeHistory = false) => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const [nextState, nextHistory] = await Promise.all([
        getDeckContentVersionState(deckId),
        includeHistory ? listDeckContentVersions(deckId) : Promise.resolve(null),
      ]);
      if (id === requestId.current) {
        setState(nextState);
        setCapabilityUnavailable(false);
        if (nextHistory) setHistory(nextHistory);
      }
      return nextState;
    } catch (cause) {
      if (id === requestId.current) {
        const unavailable = cause instanceof DeckVersionApiError && cause.code === 'DECK_VERSION_CAPABILITY_MISSING';
        setCapabilityUnavailable(unavailable);
        setError(unavailable ? '版本能力尚未部署，当前编辑仍会保留。' : (cause instanceof Error ? cause.message : '版本状态加载失败。'));
      }
      return null;
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [deckId]);

  useEffect(() => {
    setState(null);
    setHistory(null);
    setPreview(null);
    void refresh();
    return () => { requestId.current += 1; };
  }, [deckId, refresh]);

  const prepare = useCallback(async () => {
    if (!state) return null;
    setSubmitting(true);
    setError(null);
    try {
      const result = await previewDeckContentVersion(deckId, state);
      setPreview(result);
      return result;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '版本差异预览失败。');
      if (cause instanceof DeckVersionApiError && cause.status === 409) await refresh();
      return null;
    } finally {
      setSubmitting(false);
    }
  }, [deckId, refresh, state]);

  const commit = useCallback(async (description: string) => {
    if (!state) return null;
    setSubmitting(true);
    setError(null);
    try {
      const result = await commitDeckContentVersion(deckId, state, description);
      setState(result.state);
      setPreview(null);
      await refresh(true);
      return result;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '版本提交失败，草稿未丢失。');
      if (cause instanceof DeckVersionApiError && cause.status === 409) await refresh();
      return null;
    } finally {
      setSubmitting(false);
    }
  }, [deckId, refresh, state]);

  return {
    state,
    history,
    preview,
    loading,
    submitting,
    error,
    capabilityUnavailable,
    refresh,
    prepare,
    commit,
    clearPreview: () => setPreview(null),
  };
}
