// [Input] Deck Plugin Admin list API and React lifecycle.
// [Output] Refreshable installation/runtime catalog with server-owned permissions and safe errors.
// [Pos] Plugin Admin list query hook.

import { useCallback, useEffect, useState } from 'react';
import {
  listPluginInstallations,
  type PluginInstallationListResult,
} from '../api/deckPluginAdminApi';

const EMPTY_RESULT: PluginInstallationListResult = {
  installations: [],
  runtimePlugins: [],
  permissions: { canManage: false, canInstallLocal: false, canForcePurge: false },
};

export function usePluginInstallations() {
  const [result, setResult] = useState<PluginInstallationListResult>(EMPTY_RESULT);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);

  const refresh = useCallback(() => setRefreshNonce((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void listPluginInstallations(controller.signal)
      .then((nextResult) => {
        if (!active) return;
        setResult(nextResult);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!active || controller.signal.aborted) return;
        setError(reason instanceof Error ? reason : new Error('无法加载插件目录。'));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [refreshNonce]);

  return { ...result, loading, error, refresh };
}
