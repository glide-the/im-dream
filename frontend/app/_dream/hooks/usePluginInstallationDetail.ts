// [Input] Selected Deck Plugin id/version and detail API.
// [Output] Refreshable, abort-safe Plugin Admin detail state.
// [Pos] Plugin Admin detail query hook.

import { useCallback, useEffect, useState } from 'react';
import {
  getPluginInstallationDetail,
  type DeckPluginInstallation,
} from '../api/deckPluginAdminApi';

export function usePluginInstallationDetail(deckPluginId?: string, version?: string) {
  const [detail, setDetail] = useState<DeckPluginInstallation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const refresh = useCallback(() => setRefreshNonce((value) => value + 1), []);

  useEffect(() => {
    if (!deckPluginId || !version) return;
    const controller = new AbortController();
    let active = true;
    void getPluginInstallationDetail(deckPluginId, version, controller.signal)
      .then((nextDetail) => {
        if (!active) return;
        setDetail(nextDetail);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!active || controller.signal.aborted) return;
        setError(reason instanceof Error ? reason : new Error('无法加载插件详情。'));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [deckPluginId, refreshNonce, version]);

  return { detail, loading, error, refresh };
}
