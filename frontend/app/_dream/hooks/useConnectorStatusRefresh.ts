// [Sync] 2026-10-29: inject concrete native visibility/change observation; keep original serial reads and timer cadence.
// [Input] Server refresh cadence and an actor-scoped, abortable connector read.
// [Output] Serial visible-page status refreshes; no synchronization or configuration writes.
// [Pos] Shared resource-link status observation hook for Settings summary and Notion detail.
// [Sync] 2026-10-13: refresh scheduled outcomes without overlapping reads or surviving an owner change.
import { useEffect } from 'react';
import { RESOURCE_CONNECTORS_CHANGED_EVENT } from '../api/resourceConnectorApi';

export interface ConnectorStatusObservation {
  hidden:()=>boolean;
  subscribe:(onRefresh:()=>void,onVisible:()=>void)=>()=>void;
}
const browserObservation:ConnectorStatusObservation={
  hidden:()=>document.hidden,
  subscribe(onRefresh,onVisible){
    window.addEventListener('focus',onRefresh);window.addEventListener(RESOURCE_CONNECTORS_CHANGED_EVENT,onRefresh);document.addEventListener('visibilitychange',onVisible);
    return()=>{window.removeEventListener('focus',onRefresh);window.removeEventListener(RESOURCE_CONNECTORS_CHANGED_EVENT,onRefresh);document.removeEventListener('visibilitychange',onVisible);};
  },
};

export function useConnectorStatusRefresh(
  refresh: (signal: AbortSignal) => Promise<void>,
  refreshAfterSeconds: number | undefined,
  enabled: boolean,
  observation:ConnectorStatusObservation=browserObservation,
): void {
  useEffect(() => {
    if (!enabled) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let request: AbortController | undefined;
    const clearTimer = () => { if (timer !== undefined) clearTimeout(timer); };
    const schedule = () => {
      clearTimer();
      if (!disposed && !observation.hidden() && refreshAfterSeconds !== undefined) {
        // This is the browser timer representation bound, not a business interval.
        timer = setTimeout(() => { void read(); }, Math.min(refreshAfterSeconds * 1000, 2_147_483_647));
      }
    };
    const read = async () => {
      clearTimer();
      if (disposed || observation.hidden() || request) return;
      request = new AbortController();
      try { await refresh(request.signal); }
      finally { request = undefined; schedule(); }
    };
    const onVisible = () => {
      if (observation.hidden()) { clearTimer(); request?.abort(); }
      else void read();
    };
    const onRefresh = () => { void read(); };
    schedule();
    const unsubscribe=observation.subscribe(onRefresh,onVisible);
    return () => {
      disposed = true;
      clearTimer();
      request?.abort();
      unsubscribe();
    };
  }, [enabled, refresh, refreshAfterSeconds, observation]);
}
