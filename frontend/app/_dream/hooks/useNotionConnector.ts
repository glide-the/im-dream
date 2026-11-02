// [Input] Original Notion detail state, authenticated owner and concrete resource HTTP/visibility.
// [Output] One auth, selection, sync-policy, source and Skill/file state shared by Web/native.
// [Pos] State extracted from ConnectorNotionDetailPage; DOM focus and native controls remain presentation-owned.
// [Sync] 2026-10-29: extract original state for Web/native reuse; HTTP, business payloads and permissions keep their owners.
import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import * as browserApi from '../api/resourceConnectorApi';
import {ResourceConnectorApiError,type ResourceConnector,type ConnectorSource,type ConnectorAuthStatus,type ConnectorStatus,type ConnectorResourceSelection,type NotionCapabilityAvailability,type NotionResourceOption,type NotionCapabilityCatalog,type NotionSkillDetail,type NotionSkillFileDescriptor,type NotionSkillFileContent,type ResourceConnectorApi} from '../api/resourceConnectorApi';
import {DEFAULT_NOTION_CONNECTOR_NAME,RESOURCE_PAGE_SIZE,MAX_TIMER_DELAY_MS,resourceFailureMessage,NOTION_WEBSITE,NOTION_PRIVACY,NOTION_TERMS,getErrorMessage,formatDateTime,formatConnectionDate,formatFileSize,formatSyncInterval,formatStatusLabel,availabilityLabel,availabilityTone,operationSourceLabel,getDetailStatus,buildSelectionFromSources,resolveSingleNotionConnector,shouldShowPageCount,sourceKindLabel,type DetailView,type DetailTone,type UnifiedResourceKind,type UnifiedResourceOption,type DetailStatus,type ResourceRequestOwner} from '../components/dashboard/notionConnectorPresentation';
import {useConnectorStatusRefresh,type ConnectorStatusObservation} from './useConnectorStatusRefresh';
interface Options {ownerId:string|null;authenticated:boolean;active?:boolean;api?:ResourceConnectorApi;observation?:ConnectorStatusObservation}
export default function useNotionConnector(options:Options){
const {ownerId,authenticated:isAuthenticated,observation}=options,active=options.active??true;const user=ownerId?{id:ownerId}:null;const owner=useRef(options.api??browserApi);const {fetchJson,listConnectors,createConnector,updateConnector,deleteConnector,startConnectorAuth,pollConnectorAuth,listConnectorDatabases,listConnectorPages,selectConnectorResources,refreshConnectorSources,getConnector,updateConnectorSyncPolicy,getNotionCapabilityCatalog,getNotionSkillDetail,getNotionSkillFile,notifyResourceConnectorsChanged}=owner.current;
  const actorKey = JSON.stringify([isAuthenticated, user?.id ?? null]);
  const actorKeyRef = useRef(actorKey);
  actorKeyRef.current = actorKey;
  const [view, setView] = useState<DetailView>('overview');
  const [connector, setConnector] = useState<ResourceConnector | null>(null);
  const connectorRef = useRef(connector);
  connectorRef.current = connector;
  const [catalog, setCatalog] = useState<NotionCapabilityCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [policySaving, setPolicySaving] = useState(false);
  const [policyEnabled, setPolicyEnabled] = useState(false);
  const [policyIntervalMinutes, setPolicyIntervalMinutes] = useState<number | null>(null);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [resourceSaving, setResourceSaving] = useState(false);
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [resourceCooldown, setResourceCooldown] = useState<{ owner: ResourceRequestOwner; deadline: number } | null>(null);
  const resourceRequestRef = useRef<ResourceRequestOwner | null>(null);
  const resourceGenerationRef = useRef(0);
  const resourceDiscoveryAbortRef = useRef<AbortController | null>(null);
  const connectorLoadGenerationRef = useRef(0);
  const [databaseOptions, setDatabaseOptions] = useState<NotionResourceOption[]>([]);
  const [pageOptions, setPageOptions] = useState<NotionResourceOption[]>([]);
  const [selectedDatabaseIds, setSelectedDatabaseIds] = useState<string[]>([]);
  const [selectedPageIds, setSelectedPageIds] = useState<string[]>([]);
  const [resourceSearchQuery, setResourceSearchQuery] = useState('');
  const [resourcePage, setResourcePage] = useState(1);
  const [skillDetail, setSkillDetail] = useState<NotionSkillDetail | null>(null);
  const [skillLoading, setSkillLoading] = useState(false);
  const [skillError, setSkillError] = useState<string | null>(null);
  const [selectedSkillFile, setSelectedSkillFile] = useState<NotionSkillFileDescriptor | null>(null);
  const [skillFileContent, setSkillFileContent] = useState<NotionSkillFileContent | null>(null);
  const [skillFileLoading, setSkillFileLoading] = useState(false);
  const [skillFileError, setSkillFileError] = useState<string | null>(null);

  const connectorId = connector?.id ?? null;
  const connectorAuthStatus = connector?.auth.status ?? 'idle';
  const cliInstallation = catalog?.cliInstallation ?? null;
  const cliMissing = cliInstallation?.status === 'missing';
  const canEditResources = isAuthenticated && connectorAuthStatus === 'authenticated';
  const resourceOwnerKey = JSON.stringify([actorKey, connectorId]);
  const resourceOwnerKeyRef = useRef(resourceOwnerKey);
  resourceOwnerKeyRef.current = resourceOwnerKey;
  const resourceCoolingDown = resourceCooldown !== null && resourceCooldown.owner.key === resourceOwnerKey;
  const syncPolicy = connector?.syncPolicy;
  const desiredPolicyEnabled = syncPolicy?.desired.enabled;
  const desiredPolicyInterval = syncPolicy?.desired.intervalMinutes;
  const desiredPolicyRevision = syncPolicy?.desired.revision;
  const detailStatus = getDetailStatus(connector, loading);
  const sourceStats = useMemo(() => {
    const sources = connector?.sources ?? [];
    const databases = sources.filter((source) => source.type === 'notion_database').length;
    return { total: sources.length, databases, pages: sources.length - databases };
  }, [connector?.sources]);
  const readOperations = useMemo(
    () => catalog?.operations.filter((operation) => operation.kind === 'read') ?? [],
    [catalog?.operations],
  );
  const writeOperations = useMemo(
    () => catalog?.operations.filter((operation) => operation.kind === 'write') ?? [],
    [catalog?.operations],
  );
  const unifiedResourceOptions = useMemo<UnifiedResourceOption[]>(
    () => [
      ...databaseOptions.map((option) => ({ ...option, kind: 'database' as const })),
      ...pageOptions.map((option) => ({ ...option, kind: 'page' as const })),
    ],
    [databaseOptions, pageOptions],
  );
  const filteredResourceOptions = useMemo(() => {
    const query = resourceSearchQuery.trim().toLocaleLowerCase();
    if (!query) return unifiedResourceOptions;
    return unifiedResourceOptions.filter((option) => `${option.title} ${option.subtitle ?? ''} ${option.kind}`.toLocaleLowerCase().includes(query));
  }, [resourceSearchQuery, unifiedResourceOptions]);
  const totalResourcePages = Math.max(1, Math.ceil(filteredResourceOptions.length / RESOURCE_PAGE_SIZE));
  const visibleResourceOptions = useMemo(() => {
    const start = (resourcePage - 1) * RESOURCE_PAGE_SIZE;
    return filteredResourceOptions.slice(start, start + RESOURCE_PAGE_SIZE);
  }, [filteredResourceOptions, resourcePage]);
  const selectedResourceCount = selectedDatabaseIds.length + selectedPageIds.length;

  const isResourceRequestCurrent = useCallback((owner: ResourceRequestOwner) => (
    resourceRequestRef.current === owner && resourceGenerationRef.current === owner.generation
    && resourceOwnerKeyRef.current === owner.key && !owner.abort.signal.aborted
  ), []);

  const beginResourceRequest = useCallback(() => {
    resourceRequestRef.current?.abort.abort();
    const owner = { key: resourceOwnerKey, generation: ++resourceGenerationRef.current, abort: new AbortController() };
    resourceRequestRef.current = owner;
    return owner;
  }, [resourceOwnerKey]);

  useEffect(() => {
    resourceRequestRef.current?.abort.abort();
    resourceRequestRef.current = null;
    resourceDiscoveryAbortRef.current?.abort();
    resourceGenerationRef.current += 1;
    setResourceCooldown(null);
    setResourceError(null);
    setResourceSaving(false);
    setSyncLoading(false);
    return () => {
      resourceRequestRef.current?.abort.abort();
      resourceRequestRef.current = null;
      resourceDiscoveryAbortRef.current?.abort();
      resourceGenerationRef.current += 1;
    };
  }, [resourceOwnerKey]);

  useEffect(() => {
    if (!resourceCooldown) return;
    const { owner, deadline } = resourceCooldown;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const release = () => {
      if (!isResourceRequestCurrent(owner)) return;
      const remaining = deadline - Date.now();
      if (remaining > 0) timer = setTimeout(release, Math.min(remaining, MAX_TIMER_DELAY_MS));
      else setResourceCooldown(null); // Expiry only unlocks existing actions; no request or retry.
    };
    release();
    return () => { if (timer !== undefined) clearTimeout(timer); };
  }, [isResourceRequestCurrent, resourceCooldown]);

  const applyResourceRetryAfter = useCallback((error: unknown, owner: ResourceRequestOwner) => {
    if (!isResourceRequestCurrent(owner) || !(error instanceof ResourceConnectorApiError)) return;
    const seconds = error.retryAfter;
    if (seconds === null || !Number.isSafeInteger(seconds) || seconds <= 0) return;
    const deadline = Date.now() + seconds * 1000;
    if (Number.isSafeInteger(deadline)) setResourceCooldown({ owner, deadline });
  }, [isResourceRequestCurrent]);

  const reloadCatalog = useCallback(async (shouldCommit: () => boolean = () => true) => {
    if (!shouldCommit()) return;
    setCatalogLoading(true);
    setCatalogError(null);
    try {
      const next = await getNotionCapabilityCatalog();
      if (shouldCommit()) setCatalog(next);
    } catch (error) {
      if (shouldCommit()) setCatalogError(getErrorMessage(error, 'Notion 能力信息暂时无法读取'));
    } finally {
      if (shouldCommit()) setCatalogLoading(false);
    }
  }, []);

  useEffect(() => {
    const abort = new AbortController();
    const generation = ++connectorLoadGenerationRef.current;
    setConnector(null);
    setSelectedDatabaseIds([]);
    setSelectedPageIds([]);
    setDatabaseOptions([]);
    setPageOptions([]);
    setResourceLoading(false);
    setLoading(isAuthenticated);
    setPageError(null);
    const current = () => !abort.signal.aborted && generation === connectorLoadGenerationRef.current
      && actorKeyRef.current === actorKey;
    if (isAuthenticated) void listConnectors(abort.signal).then((next) => {
      if (current()) setConnector(resolveSingleNotionConnector(next));
    }).catch((error: unknown) => {
      if (current()) setPageError(getErrorMessage(error, 'Notion 连接状态读取失败'));
    }).finally(() => { if (current()) setLoading(false); });
    void reloadCatalog(current);
    return () => abort.abort();
  }, [actorKey, isAuthenticated, reloadCatalog]);

  useEffect(() => {
    if (desiredPolicyEnabled === undefined || desiredPolicyInterval === undefined || desiredPolicyRevision === undefined) return;
    setPolicyEnabled(desiredPolicyEnabled);
    setPolicyIntervalMinutes(desiredPolicyInterval);
  }, [desiredPolicyEnabled, desiredPolicyInterval, desiredPolicyRevision]);

  const refreshConnectorStatus = useCallback(async (signal: AbortSignal) => {
    const original = connectorRef.current;
    const generation = connectorLoadGenerationRef.current;
    try {
      const next = await listConnectors(signal);
      if (!signal.aborted && actorKeyRef.current === actorKey
        && generation === connectorLoadGenerationRef.current && connectorRef.current === original) {
        setConnector(resolveSingleNotionConnector(next));
        setPageError(null);
      }
    } catch (error) {
      if (!signal.aborted && actorKeyRef.current === actorKey && generation === connectorLoadGenerationRef.current) {
        setPageError(getErrorMessage(error, 'Notion 连接状态读取失败'));
      }
    }
  }, [actorKey]);
  useConnectorStatusRefresh(refreshConnectorStatus, syncPolicy?.refreshAfterSeconds,
    active && isAuthenticated && !loading && connectorAuthStatus !== 'authenticating'
      && !connecting && !disconnecting && !policySaving && !resourceSaving && !syncLoading && !resourceCoolingDown,observation);

  useEffect(() => {
    setResourcePage(1);
  }, [resourceSearchQuery]);

  useEffect(() => {
    setResourcePage((current) => Math.min(current, totalResourcePages));
  }, [totalResourcePages]);


  useEffect(() => {
    if (!active || !connectorId || connectorAuthStatus !== 'authenticating') return undefined;
    let observing = true;
    const poll = async () => {
      try {
        const next = await pollConnectorAuth(connectorId);
        if (!observing || !next) return;
        setConnector(next);
        if (next.auth.status !== 'authenticating') void reloadCatalog();
      } catch (error) {
        if (observing) setPageError(getErrorMessage(error, '认证状态读取失败；你的输入和已有索引未被修改'));
      }
    };
    void poll();
    const intervalId = setInterval(() => { void poll(); }, 3500);
    return () => { observing = false; clearInterval(intervalId); };
  }, [active, connectorAuthStatus, connectorId, reloadCatalog]);

  const ensureSingleConnector = useCallback(async () => {
    if (connector) return connector;
    const existing = resolveSingleNotionConnector(await listConnectors());
    if (existing) { setConnector(existing); return existing; }
    const created = await createConnector({ name: DEFAULT_NOTION_CONNECTOR_NAME, platform: 'notion' });
    setConnector(created);
    return created;
  }, [connector]);

  const handleStartAuth = useCallback(async () => {
    if (connecting || cliMissing) return;
    setConnecting(true);
    setPageError(null);
    try {
      const target = await ensureSingleConnector();
      const next = await startConnectorAuth(target.id);
      if (next) setConnector(next);
      notifyResourceConnectorsChanged({ connectorId: target.id, reason: 'auth-updated' });
      await reloadCatalog();
    } catch (error) {
      setPageError(getErrorMessage(error, '无法启动 Notion 连接；已有内容未被修改，请重试'));
    } finally {
      setConnecting(false);
    }
  }, [cliMissing, connecting, ensureSingleConnector, reloadCatalog]);

  const handleDisconnect = useCallback(async () => {
    if (!connectorId || disconnecting) return;
    setDisconnecting(true);
    setPageError(null);
    try {
      if (await deleteConnector(connectorId)) {
        setConnector(null);
        setDatabaseOptions([]);
        setPageOptions([]);
        setSelectedDatabaseIds([]);
        setSelectedPageIds([]);
        notifyResourceConnectorsChanged({ connectorId, reason: 'connector-updated' });
        await reloadCatalog();
      }
    } catch (error) {
      setPageError(getErrorMessage(error, '无法关闭 Notion 连接；当前连接保持不变，请重试'));
    } finally {
      setDisconnecting(false);
    }
  }, [connectorId, disconnecting, reloadCatalog]);

  const handleSaveSyncPolicy = useCallback(async () => {
    if (!connectorId || !syncPolicy || policyIntervalMinutes === null || policySaving) return;
    setPolicySaving(true);
    setPolicyError(null);
    try {
      const next = await updateConnectorSyncPolicy(connectorId, { enabled: policyEnabled, intervalMinutes: policyIntervalMinutes });
      setConnector(next);
      notifyResourceConnectorsChanged({ connectorId, reason: 'connector-updated' });
    } catch (error) {
      setPolicyError(getErrorMessage(error, '策略未保存；服务器原策略仍然生效，请重试'));
    } finally {
      setPolicySaving(false);
    }
  }, [connectorId, policyEnabled, policyIntervalMinutes, policySaving, syncPolicy]);

  const handleOpenSkill = useCallback(async (skillId: string) => {
    setView('skill');
    setSkillLoading(true);
    setSkillError(null);
    setSkillDetail(null);
    try {
      setSkillDetail(await getNotionSkillDetail(skillId));
    } catch (error) {
      setSkillError(getErrorMessage(error, 'Skill 说明暂时无法读取；Notion 连接和索引不受影响'));
    } finally {
      setSkillLoading(false);
    }
  }, []);

  const handleOpenSkillFile = useCallback(async (file: NotionSkillFileDescriptor) => {
    if (!skillDetail) return;
    setSelectedSkillFile(file);
    setSkillFileContent(null);
    setSkillFileError(null);
    setSkillFileLoading(true);
    setView('file');
    try {
      setSkillFileContent(await getNotionSkillFile(skillDetail.skill.id, file.id, skillDetail.packageRevision));
    } catch (error) {
      if (error instanceof ResourceConnectorApiError && error.status === 409) {
        try {
          setSkillDetail(await getNotionSkillDetail(skillDetail.skill.id));
        } catch {
          // Keep the safe file error as the visible boundary; connector state remains usable.
        }
        setSkillFileError('Skill 包已更新，旧文件内容没有继续显示。请返回文件清单后重新打开。');
      } else {
        setSkillFileError(getErrorMessage(error, '文件暂时无法读取；请返回 Skill 刷新后重试'));
      }
    } finally {
      setSkillFileLoading(false);
    }
  }, [skillDetail]);

  const loadResourceOptions = useCallback(async () => {
    const selection = buildSelectionFromSources(connector?.sources ?? []);
    setSelectedDatabaseIds(selection.databaseIds);
    setSelectedPageIds(selection.pageIds);
    setResourceSearchQuery('');
    setResourcePage(1);
    setResourceError(null);
    if (!connectorId || !canEditResources) {
      setDatabaseOptions([]);
      setPageOptions([]);
      return;
    }
    resourceDiscoveryAbortRef.current?.abort();
    const abort = new AbortController();
    resourceDiscoveryAbortRef.current = abort;
    const generation = resourceGenerationRef.current;
    const current = () => !abort.signal.aborted && resourceDiscoveryAbortRef.current === abort
      && resourceOwnerKeyRef.current === resourceOwnerKey && resourceGenerationRef.current === generation;
    setResourceLoading(true);
    try {
      const [databases, pages] = await Promise.all([
        listConnectorDatabases(connectorId),
        listConnectorPages(connectorId),
      ]);
      if (!current()) return;
      setDatabaseOptions(databases);
      setPageOptions(pages);
      setSelectedDatabaseIds(selection.databaseIds.length > 0 ? selection.databaseIds : databases.filter((option) => option.selected).map((option) => option.id));
      setSelectedPageIds(selection.pageIds.length > 0 ? selection.pageIds : pages.filter((option) => option.selected).map((option) => option.id));
    } catch (error) {
      if (!current()) return;
      setResourceError(getErrorMessage(error, '资源列表加载失败；服务器当前范围没有改变，请重试'));
      setDatabaseOptions([]);
      setPageOptions([]);
    } finally {
      if (current()) setResourceLoading(false);
    }
  }, [canEditResources, connector?.sources, connectorId, resourceOwnerKey]);

  const handleOpenResources = useCallback(() => {
    setView('resources');
    void loadResourceOptions();
  }, [loadResourceOptions]);

  const handleSaveResources = useCallback(async () => {
    if (!connectorId || !canEditResources || resourceSaving || syncLoading || resourceCoolingDown) return;
    const owner = beginResourceRequest();
    const current = () => isResourceRequestCurrent(owner);
    setResourceSaving(true);
    setResourceError(null);
    try {
      const next = await selectConnectorResources(connectorId, {
        databaseIds: selectedDatabaseIds, pageIds: selectedPageIds, databaseOptions, pageOptions,
      });
      if (!current()) return;
      if (next) setConnector(next);
      notifyResourceConnectorsChanged({ connectorId, reason: 'resources-selected' });
      await reloadCatalog(current);
    } catch (error) {
      if (!current()) return;
      applyResourceRetryAfter(error, owner);
      if (error instanceof ResourceConnectorApiError && error.context.selection_saved === true) {
        const feedback = `资源范围已保存，索引更新未完成。${resourceFailureMessage(error, '请稍后重试索引更新。')}`;
        setResourceError(feedback);
        notifyResourceConnectorsChanged({ connectorId, reason: 'resources-selected' });
        try {
          const saved = resolveSingleNotionConnector(await listConnectors(owner.abort.signal));
          if (!current()) return;
          if (saved?.id === connectorId) setConnector(saved);
          else setResourceError(`${feedback}暂时无法重新读取当前范围；本页选择仍保留。`);
        } catch {
          if (current()) setResourceError(`${feedback}暂时无法重新读取当前范围；本页选择仍保留。`);
        }
      } else {
        setResourceError(`保存状态未确认；你的本页选择仍保留，请返回查看当前范围后重试。${error instanceof ResourceConnectorApiError && error.code === 'NOTION_SYNC_BUSY' ? resourceFailureMessage(error, '') : ''}`);
      }
    } finally {
      if (current()) setResourceSaving(false);
    }
  }, [applyResourceRetryAfter, beginResourceRequest, canEditResources, connectorId, databaseOptions, isResourceRequestCurrent, pageOptions, reloadCatalog, resourceCoolingDown, resourceSaving, selectedDatabaseIds, selectedPageIds, syncLoading]);

  const handleSyncSources = useCallback(async () => {
    if (!connectorId || !canEditResources || syncLoading || resourceSaving || resourceCoolingDown) return;
    const owner = beginResourceRequest();
    const current = () => isResourceRequestCurrent(owner);
    setSyncLoading(true);
    setResourceError(null);
    try {
      const next = await refreshConnectorSources(connectorId);
      if (!current()) return;
      if (next) setConnector(next);
      notifyResourceConnectorsChanged({ connectorId, reason: 'sources-refreshed' });
      await reloadCatalog(current);
    } catch (error) {
      if (!current()) return;
      applyResourceRetryAfter(error, owner);
      setResourceError(resourceFailureMessage(error, '索引更新失败；最近一次成功索引仍保留，请稍后重试'));
    } finally {
      if (current()) setSyncLoading(false);
    }
  }, [applyResourceRetryAfter, beginResourceRequest, canEditResources, connectorId, isResourceRequestCurrent, reloadCatalog, resourceCoolingDown, resourceSaving, syncLoading]);

  const authActionLabel = connectorAuthStatus === 'authenticated' ? '重新连接 Notion' : connectorAuthStatus === 'authenticating' ? '认证进行中' : '连接 Notion';


return {view,setView,connector,catalog,catalogLoading,pageError,catalogError,policyError,connecting,disconnecting,syncLoading,policySaving,policyEnabled,setPolicyEnabled,policyIntervalMinutes,setPolicyIntervalMinutes,resourceLoading,resourceSaving,resourceError,selectedDatabaseIds,setSelectedDatabaseIds,selectedPageIds,setSelectedPageIds,resourceSearchQuery,setResourceSearchQuery,resourcePage,setResourcePage,skillDetail,skillLoading,skillError,selectedSkillFile,skillFileContent,skillFileLoading,skillFileError,connectorId,connectorAuthStatus,cliInstallation,cliMissing,canEditResources,resourceCoolingDown,syncPolicy,detailStatus,sourceStats,readOperations,writeOperations,unifiedResourceOptions,filteredResourceOptions,totalResourcePages,visibleResourceOptions,selectedResourceCount,handleStartAuth,handleDisconnect,handleSaveSyncPolicy,handleOpenSkill,handleOpenSkillFile,handleOpenResources,handleSaveResources,handleSyncSources,authActionLabel,reloadCatalog};
}
