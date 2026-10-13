// [Input] Server refresh cadence and an actor-scoped, abortable connector read.
// [Output] Serial visible-page status refreshes; no synchronization or configuration writes.
// [Pos] Shared resource-link status observation hook for Settings summary and Notion detail.
// [Sync] 2026-10-13: refresh scheduled outcomes without overlapping reads or surviving an owner change.
import { useEffect } from 'react';
import { RESOURCE_CONNECTORS_CHANGED_EVENT } from '../api/resourceConnectorApi';

export function useConnectorStatusRefresh(
  refresh: (signal: AbortSignal) => Promise<void>,
  refreshAfterSeconds: number | undefined,
  enabled: boolean,
): void {
  useEffect(() => {
    if (!enabled) return;
    let disposed = false;
    let timer: number | undefined;
    let request: AbortController | undefined;
    const clearTimer = () => { if (timer !== undefined) window.clearTimeout(timer); };
    const schedule = () => {
      clearTimer();
      if (!disposed && !document.hidden && refreshAfterSeconds !== undefined) {
        // This is the browser timer representation bound, not a business interval.
        timer = window.setTimeout(() => { void read(); }, Math.min(refreshAfterSeconds * 1000, 2_147_483_647));
      }
    };
    const read = async () => {
      clearTimer();
      if (disposed || document.hidden || request) return;
      request = new AbortController();
      try { await refresh(request.signal); }
      finally { request = undefined; schedule(); }
    };
    const onVisible = () => {
      if (document.hidden) { clearTimer(); request?.abort(); }
      else void read();
    };
    const onRefresh = () => { void read(); };
    schedule();
    window.addEventListener('focus', onRefresh);
    window.addEventListener(RESOURCE_CONNECTORS_CHANGED_EVENT, onRefresh);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      disposed = true;
      clearTimer();
      request?.abort();
      window.removeEventListener('focus', onRefresh);
      window.removeEventListener(RESOURCE_CONNECTORS_CHANGED_EVENT, onRefresh);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [enabled, refresh, refreshAfterSeconds]);
}
