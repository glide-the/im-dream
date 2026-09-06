// [Input] Deck id and persisted binding-history endpoint.
// [Output] Read-only monotonic runtime-configuration revisions.
// [Pos] Deck version-history data hook.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getDeckPluginBindingHistory,
  type DeckPluginBindingHistoryResponse,
} from '../api/deckPluginApi';

export function useDeckPluginBindingHistory(deckId: string) {
  const [data, setData] = useState<DeckPluginBindingHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const next = await getDeckPluginBindingHistory(deckId);
      if (id === requestId.current) setData(next);
      return next;
    } catch {
      if (id === requestId.current) setError('版本记录加载失败，请重试。');
      return null;
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [deckId]);

  useEffect(() => {
    void refresh();
    return () => { requestId.current += 1; };
  }, [refresh]);

  return {
    history: data?.deck_id === deckId ? data.entries : [],
    currentRevision: data?.deck_id === deckId ? data.current_binding_revision : 0,
    loading,
    error,
    refresh,
  };
}
