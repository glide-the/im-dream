// [Input] Selected Deck Plugin identifier and server runtime-readiness API.
// [Output] Refreshable declaration/materialization/activation snapshot without client-side readiness inference.
// [Pos] Plugin Admin runtime readiness hook.

import { useCallback, useEffect, useState } from 'react';
import {
  getPluginRuntimeReadiness,
  type DeckPluginInstallation,
} from '../api/deckPluginAdminApi';

export function usePluginRuntimeReadiness(deckPluginId?: string) {
  const [readiness, setReadiness] = useState<Partial<DeckPluginInstallation> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const refresh = useCallback(() => setRefreshNonce((value) => value + 1), []);

  useEffect(() => {
    if (!deckPluginId) return;
    const controller = new AbortController();
    let active = true;
    void getPluginRuntimeReadiness(deckPluginId, controller.signal)
      .then((nextReadiness) => {
        if (!active) return;
        setReadiness(nextReadiness);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!active || controller.signal.aborted) return;
        setError(reason instanceof Error ? reason : new Error('无法读取运行时就绪状态。'));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [deckPluginId, refreshNonce]);

  return { readiness, loading, error, refresh };
}
