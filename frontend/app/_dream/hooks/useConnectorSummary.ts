// [Input] Original resource-summary state, public actor and concrete HTTP/visibility.
// [Output] One actor-scoped connector read/status state for Web and native Resources.
// [Pos] State extracted from ConnectorSettingsSection; DOM focus stays with Web.
// [Sync] 2026-10-29: preserve original reads, focus refresh and status labels.
import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import * as browserApi from '../api/resourceConnectorApi';
import type {ResourceConnector,ResourceConnectorApi} from '../api/resourceConnectorApi';
import {useConnectorStatusRefresh,type ConnectorStatusObservation} from './useConnectorStatusRefresh';
import {formatLastInteraction,getResourceHealthTone,getNotionStatusLabel} from '../components/dashboard/connectorSummaryPresentation';
interface Options {ownerId:string|null;authenticated:boolean;focusNonce?:number;active?:boolean;api?:ResourceConnectorApi;observation?:ConnectorStatusObservation}
export default function useConnectorSummary(options:Options){
 const {ownerId,authenticated:isAuthenticated,focusNonce=0,active=true,observation}=options;const user=ownerId?{id:ownerId}:null;const owner=useRef(options.api??browserApi),api=owner.current;
  const actorKey = JSON.stringify([isAuthenticated, user?.id ?? null]);
  const actorKeyRef = useRef(actorKey);
  actorKeyRef.current = actorKey;
  const [connectors, setConnectors] = useState<ResourceConnector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConnectors = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const items = await api.listConnectors(signal);
      if (!signal?.aborted && actorKeyRef.current === actorKey) setConnectors(items);
    } catch (err) {
      if (!signal?.aborted && actorKeyRef.current === actorKey) setError(err instanceof Error ? err.message : '资源链接读取失败');
    } finally {
      if (!signal?.aborted && actorKeyRef.current === actorKey) setLoading(false);
    }
  }, [actorKey]);



  useEffect(() => {
    const abort = new AbortController();
    setConnectors([]);
    if (isAuthenticated) void loadConnectors(abort.signal);
    else setLoading(false);
    return () => abort.abort();
  }, [loadConnectors, focusNonce, isAuthenticated]);

  const notionConnector = useMemo(
    () => connectors.find((connector) => connector.platform === 'notion') ?? null,
    [connectors],
  );
  const refreshConnectorStatus = useCallback(async (signal: AbortSignal) => {
    try {
      const items = await api.listConnectors(signal);
      if (!signal.aborted && actorKeyRef.current === actorKey) { setConnectors(items); setError(null); }
    } catch (err) {
      if (!signal.aborted && actorKeyRef.current === actorKey) setError(err instanceof Error ? err.message : '资源链接读取失败');
    }
  }, [actorKey]);
  useConnectorStatusRefresh(refreshConnectorStatus, notionConnector?.syncPolicy?.refreshAfterSeconds, active && isAuthenticated && !loading,observation);
  const notionStatusLabel=getNotionStatusLabel(notionConnector);
  const notionStatusTone = getResourceHealthTone(notionConnector);
  const notionLastInteraction = formatLastInteraction(notionConnector);

 return {loading,error,loadConnectors,notionConnector,notionStatusLabel,notionStatusTone,notionLastInteraction};
}
