// [Input] Deck id and server-adjudicated exact runtime versions.
// [Output] Selectable/unavailable version options with refresh state.
// [Pos] Deck version-management options hook.
// [Sync] 2026-08-16: restore exact-version options without a separate workbench.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DeckPluginApiError,
  getDeckPluginOptions,
  type DeckPluginOptionsResponse,
} from '../api/deckPluginApi';

function loadMessage(error: unknown): string {
  if (error instanceof DeckPluginApiError && error.status === 404) return '此 Deck 的可用版本不可读取。';
  if (error instanceof Error && error.message === 'Not authenticated') return '登录状态已失效，请重新登录。';
  return '可用版本加载失败，请稍后重试。';
}

export function useDeckPluginOptions(deckId: string) {
  const [data, setData] = useState<DeckPluginOptionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(async (): Promise<DeckPluginOptionsResponse | null> => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const next = await getDeckPluginOptions(deckId);
      if (id === requestId.current) setData(next);
      return next;
    } catch (nextError) {
      if (id === requestId.current) setError(loadMessage(nextError));
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
    options: data?.deck_id === deckId ? data.options : [],
    appliedTo: data?.deck_id === deckId ? data.applied_to : 'next_run',
    loading,
    error,
    refresh,
  };
}
