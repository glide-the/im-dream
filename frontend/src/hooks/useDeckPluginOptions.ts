// [Input] Deck id and the frozen Deck Plugin options endpoint.
// [Output] Current server-filtered options plus loading, error, and refresh state.
// [Pos] Deck Editor Plugin options data hook.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DeckPluginApiError,
  getDeckPluginOptions,
  type DeckPluginOptionsResponse,
} from '../api/deckPluginApi';

function optionLoadMessage(error: unknown): string {
  if (error instanceof DeckPluginApiError && error.status === 404) {
    return '无法读取此 Deck 的工作流插件选项。';
  }
  if (error instanceof Error && error.message === 'Not authenticated') {
    return '登录状态已失效，请重新登录后重试。';
  }
  return '工作流插件版本加载失败，请稍后重试。';
}

export function useDeckPluginOptions(deckId: string) {
  const [data, setData] = useState<DeckPluginOptionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(async (): Promise<DeckPluginOptionsResponse | null> => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const nextData = await getDeckPluginOptions(deckId);
      if (currentRequest === requestId.current) setData(nextData);
      return nextData;
    } catch (nextError) {
      if (currentRequest === requestId.current) setError(optionLoadMessage(nextError));
      return null;
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, [deckId]);

  useEffect(() => {
    void refresh();
    return () => {
      requestId.current += 1;
    };
  }, [refresh]);

  return {
    options: data?.deck_id === deckId ? data.options : [],
    appliedTo: data?.deck_id === deckId ? data.applied_to : 'next_run',
    loading,
    error,
    refresh,
  };
}
