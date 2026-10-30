// [Input] Original MCP detail and CAS autosave state with concrete HTTP, confirmation and operation handoff.
// [Output] One configuration, inventory, auth and queued usage-policy state for Web/native.
// [Pos] State extracted from ClaudeMcpServerDetailPage; callers own controls and navigation.
// [Sync] 2026-10-29: extract original state for Web/native reuse; HTTP, business payloads and permissions keep their owners.
import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import * as browserApi from '../api/claudeMcpApi';
import {ClaudeMcpApiError,type ClaudeMcpCapability,type ClaudeMcpAuthState,type ClaudeMcpConfigScope,type ClaudeMcpOperation,type ClaudeMcpServer,type ClaudeMcpServerInventory,type ClaudeMcpState,type ClaudeMcpTool,type ClaudeMcpAppSettings,type ClaudeMcpApi} from '../api/claudeMcpApi';
import {OPERATION_POLL_INTERVAL_MS,APP_USAGE_POLICY_AUTO_SAVE_DELAY_MS,APP_USAGE_POLICY_RETRY_DELAY_MS,APP_USAGE_POLICY_MAX_CONFLICT_REBASES,APP_SETTINGS_REVISION_CONFLICT,ACTIVE_STATES,DASHED_PAGE_BORDER,SOFT_CONTROL_BORDER,SOFT_ROW_DIVIDER,SOFT_ROW_SURFACE,STATE_LABELS,AUTH_STATE_LABELS,authStateOf,canLogout,connectionStateLabel,errorMessage,operationErrorMessage,appUsagePolicyDraft,connectionSummary,formatDateTime,stateTone,toolMatchesFilter,type CapabilityTab,type ToolFilter,type EditTransport,type Tone,type AppUsagePolicyField,type AppUsagePolicyDraft} from '../components/claude-mcp/mcpServerPresentation';
import {rememberClaudeMcpOAuthOperation as browserRemember,forgetClaudeMcpOAuthOperation as browserForget} from '../components/claude-mcp/oauthHandoff';
import {canStartClaudeMcpAuth} from '../components/claude-mcp/authPolicy';
const browserConfirm=(message:string)=>window.confirm(message);
interface Options {serverName:string;onBack:()=>void;api?:ClaudeMcpApi;active?:boolean;confirmRemove?:(message:string)=>boolean|Promise<boolean>;remember?:(id:string)=>boolean;forget?:(id?:string)=>void}
export default function useClaudeMcpServer(options:Options){
const {serverName,onBack}=options,active=options.active??true;const owner=useRef({api:options.api??browserApi,confirm:options.confirmRemove??browserConfirm,remember:options.remember??browserRemember,forget:options.forget??browserForget});
const {getClaudeMcpCapability,listClaudeMcpServers,getClaudeMcpServer,getClaudeMcpAppSettings,updateClaudeMcpAppSettings,getClaudeMcpAppEffectiveStatus,getClaudeMcpServerInventory,configureClaudeMcpServer,updateClaudeMcpServer,removeClaudeMcpServer,startClaudeMcpAuth,getClaudeMcpOperation,submitClaudeMcpRedirect,cancelClaudeMcpAuth,logoutClaudeMcpServer}=owner.current.api;const confirmRemove=owner.current.confirm,rememberClaudeMcpOAuthOperation=owner.current.remember,forgetClaudeMcpOAuthOperation=owner.current.forget;
  const [capability, setCapability] = useState<ClaudeMcpCapability | null>(null);
  const [server, setServer] = useState<ClaudeMcpServer | null>(null);
  const [inventory, setInventory] = useState<ClaudeMcpServerInventory | null>(null);
  const [operation, setOperation] = useState<ClaudeMcpOperation | null>(null);
  const [activeTab, setActiveTab] = useState<CapabilityTab>('tools');
  const [searchQuery, setSearchQuery] = useState('');
  const [toolFilter, setToolFilter] = useState<ToolFilter>('all');
  const [loading, setLoading] = useState(true);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [inventoryError, setInventoryError] = useState<string | null>(null);
  const [appSettings, setAppSettings] = useState<ClaudeMcpAppSettings | null>(null);
  const [appSettingsError, setAppSettingsError] = useState<string | null>(null);
  const [appUsagePolicySaving, setAppUsagePolicySaving] = useState(false);
  const [editAppEnabled, setEditAppEnabled] = useState(false);
  const [editAppLowRiskToolCalls, setEditAppLowRiskToolCalls] = useState(false);
  const [editAppUiMessages, setEditAppUiMessages] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editDisplayName, setEditDisplayName] = useState('');
  const [editTransport, setEditTransport] = useState<EditTransport>('streamable_http');
  const [editUrl, setEditUrl] = useState('');
  const [editStdioProfile, setEditStdioProfile] = useState('');
  const [editEnabled, setEditEnabled] = useState(true);
  const automaticInventoryKeyRef = useRef<string | null>(null);
  const inventoryRequestSequenceRef = useRef(0);
  const serverRef = useRef<ClaudeMcpServer | null>(null);
  const appSettingsRef = useRef<ClaudeMcpAppSettings | null>(null);
  const appUsagePolicyDraftRef = useRef<AppUsagePolicyDraft>({
    enabled: false,
    lowRiskToolCalls: false,
    uiMessages: false,
  });
  const appUsagePolicyDirtyFieldsRef = useRef<Partial<Record<AppUsagePolicyField, number>>>({});
  const appUsagePolicyChangeSequenceRef = useRef(0);
  const appUsagePolicySaveInFlightRef = useRef(false);
  const appUsagePolicySaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const appUsagePolicyScopeRef = useRef(0);

  serverRef.current = server;

  const effectiveState = operation && ACTIVE_STATES.includes(operation.state)
    ? operation.state
    : server?.state;
  const visibleTools = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase();
    return (inventory?.tools ?? []).filter((tool) => {
      if (!toolMatchesFilter(tool, toolFilter)) return false;
      if (!query) return true;
      return `${tool.name} ${tool.description ?? ''}`.toLocaleLowerCase().includes(query);
    });
  }, [inventory?.tools, searchQuery, toolFilter]);

  const adoptAppUsagePolicySettings = useCallback((
    next: ClaudeMcpAppSettings,
    preserveDirtyDraft: boolean,
  ) => {
    const current = appSettingsRef.current;
    if (current && next.revision < current.revision) return;

    appSettingsRef.current = next;
    setAppSettings(next);
    const visibleDraft = appUsagePolicyDraft(next);
    if (preserveDirtyDraft) {
      const localDraft = appUsagePolicyDraftRef.current;
      const dirtyFields = appUsagePolicyDirtyFieldsRef.current;
      if (dirtyFields.enabled) visibleDraft.enabled = localDraft.enabled;
      if (dirtyFields.lowRiskToolCalls) {
        visibleDraft.lowRiskToolCalls = localDraft.lowRiskToolCalls;
      }
      if (dirtyFields.uiMessages) visibleDraft.uiMessages = localDraft.uiMessages;
    }
    appUsagePolicyDraftRef.current = visibleDraft;
    setEditAppEnabled(visibleDraft.enabled);
    setEditAppLowRiskToolCalls(visibleDraft.lowRiskToolCalls);
    setEditAppUiMessages(visibleDraft.uiMessages);
  }, []);

  const loadInventory = useCallback(async () => {
    const requestSequence = inventoryRequestSequenceRef.current + 1;
    inventoryRequestSequenceRef.current = requestSequence;
    setInventoryLoading(true);
    setInventoryError(null);
    try {
      const next = await getClaudeMcpServerInventory(serverName);
      if (requestSequence !== inventoryRequestSequenceRef.current) return;
      automaticInventoryKeyRef.current = `${serverName}:${next.config_revision}:${next.credential_revision}:enabled`;
      setInventory(next);
      setServer((current) => current ? {
        ...current,
        revision: next.config_revision,
        credential_revision: next.credential_revision,
        state: next.status === 'connected'
          ? 'connected'
          : next.status === 'needs_auth' ? 'needs_auth' : 'failed',
        auth_state: next.status === 'needs_auth'
          ? 'required'
          : next.status === 'connected'
            ? (current.credential_configured ? 'authenticated' : 'anonymous')
            : current.auth_state,
      } : current);
    } catch (error) {
      if (requestSequence !== inventoryRequestSequenceRef.current) return;
      setInventory(null);
      setInventoryError(errorMessage(error, 'MCP 工具清单读取失败'));
    } finally {
      if (requestSequence === inventoryRequestSequenceRef.current) setInventoryLoading(false);
    }
  }, [serverName]);

  const loadInventoryForServer = useCallback((nextServer: ClaudeMcpServer) => {
    const key = `${serverName}:${nextServer.revision ?? 'unknown'}:${nextServer.credential_revision}:`;
    const inventoryKey = `${key}${nextServer.enabled ? 'enabled' : 'disabled'}`;
    if (automaticInventoryKeyRef.current === inventoryKey) return;
    automaticInventoryKeyRef.current = inventoryKey;
    setInventory(null);
    setInventoryError(null);
    if (nextServer.enabled) {
      void loadInventory();
    } else {
      inventoryRequestSequenceRef.current += 1;
      setInventoryLoading(false);
    }
  }, [loadInventory, serverName]);

  const load = useCallback(async () => {
    setLoading(true);
    setPageError(null);
    try {
      const [capabilityResult, serverResult] = await Promise.allSettled([
        getClaudeMcpCapability(),
        getClaudeMcpServer(serverName),
      ]);
      if (capabilityResult.status === 'rejected') throw capabilityResult.reason;
      const nextCapability = capabilityResult.value;
      setCapability(nextCapability);
      if (!nextCapability.enabled) {
        appUsagePolicyScopeRef.current += 1;
        inventoryRequestSequenceRef.current += 1;
        setServer(null);
        setInventory(null);
        setInventoryLoading(false);
        setAppSettings(null);
        appSettingsRef.current = null;
        appUsagePolicyDirtyFieldsRef.current = {};
        setAppUsagePolicySaving(false);
        return;
      }
      if (serverResult.status === 'rejected') throw serverResult.reason;
      const nextServer = serverResult.value;
      setServer(nextServer);
      setEditDisplayName(nextServer.display_name);
      setEditTransport((nextServer.transport ?? 'streamable_http') as EditTransport);
      setEditUrl(nextServer.url ?? '');
      setEditStdioProfile(nextServer.stdio_profile_key ?? '');
      setEditEnabled(nextServer.enabled);
      try {
        const nextAppSettings = await getClaudeMcpAppSettings(
          nextServer.id ?? serverName,
          nextServer.workspace_id,
        );
        adoptAppUsagePolicySettings(nextAppSettings, true);
        setAppSettingsError(null);
      } catch (error) {
        if (!appSettingsRef.current) setAppSettings(null);
        setAppSettingsError(errorMessage(error, 'MCP App 设置读取失败'));
      }
      if (nextServer.active_operation_id) {
        setOperation(await getClaudeMcpOperation(nextServer.active_operation_id));
      }
      loadInventoryForServer(nextServer);
    } catch (error) {
      setPageError(errorMessage(error, 'Claude MCP 服务详情读取失败'));
    } finally {
      setLoading(false);
    }
  }, [adoptAppUsagePolicySettings, loadInventoryForServer, serverName]);

  useEffect(() => {
    appUsagePolicyScopeRef.current += 1;
    appUsagePolicyDirtyFieldsRef.current = {};
    appSettingsRef.current = null;
    appUsagePolicyDraftRef.current = {
      enabled: false,
      lowRiskToolCalls: false,
      uiMessages: false,
    };
    setAppUsagePolicySaving(false);
    if (appUsagePolicySaveTimerRef.current !== null) {
      clearTimeout(appUsagePolicySaveTimerRef.current);
      appUsagePolicySaveTimerRef.current = null;
    }
    return () => {
      appUsagePolicyScopeRef.current += 1;
      if (appUsagePolicySaveTimerRef.current !== null) {
        clearTimeout(appUsagePolicySaveTimerRef.current);
        appUsagePolicySaveTimerRef.current = null;
      }
    };
  }, [serverName]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!active || !operation || !ACTIVE_STATES.includes(operation.state)) return undefined;
    const timer = setInterval(() => {
      void getClaudeMcpOperation(operation.id)
        .then((next) => {
          setOperation(next);
          if (next.state === 'connected') {
            forgetClaudeMcpOAuthOperation(next.id);
            void load();
          }
        })
        .catch((error: unknown) => setPageError(errorMessage(error, '认证状态刷新失败')));
    }, OPERATION_POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [active, load, operation]);

  const startAuth = useCallback(async () => {
    if (busyAction || !canStartClaudeMcpAuth(server, effectiveState)) return;
    setBusyAction('auth');
    setPageError(null);
    try {
      const next = await startClaudeMcpAuth(serverName);
      if (!rememberClaudeMcpOAuthOperation(next.id)) {
        await cancelClaudeMcpAuth(next.id);
        throw new Error('browser operation handoff unavailable');
      }
      setOperation(next);
    } catch (error) {
      setPageError(errorMessage(error, '认证启动失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, effectiveState, server, serverName]);

  const cancelAuth = useCallback(async () => {
    if (!operation || busyAction) return;
    setBusyAction('cancel');
    setPageError(null);
    try {
      setOperation(await cancelClaudeMcpAuth(operation.id));
      forgetClaudeMcpOAuthOperation(operation.id);
      await load();
    } catch (error) {
      setPageError(errorMessage(error, '认证取消失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, load, operation]);

  const logout = useCallback(async () => {
    if (busyAction) return;
    setBusyAction('logout');
    setPageError(null);
    try {
      await logoutClaudeMcpServer(serverName);
      setOperation(null);
      automaticInventoryKeyRef.current = null;
      await load();
    } catch (error) {
      setPageError(errorMessage(error, '退出认证失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, load, serverName]);

  const saveConfiguration = useCallback(async () => {
    if (!server || busyAction) return;
    const displayName = editDisplayName.trim();
    const url = editUrl.trim();
    const stdioProfile = editStdioProfile.trim();
    if (!displayName) {
      setPageError('显示名称不能为空。');
      return;
    }
    if (editTransport === 'stdio' ? !stdioProfile : !url) {
      setPageError(editTransport === 'stdio' ? 'stdio 需要服务端 profile key。' : 'HTTP/SSE 需要绝对 URL。');
      return;
    }
    setBusyAction('update');
    setPageError(null);
    try {
      const nextServer = await updateClaudeMcpServer(server, {
        displayName,
        transport: editTransport,
        url: editTransport === 'stdio' ? null : url,
        stdioProfileKey: editTransport === 'stdio' ? stdioProfile : null,
        enabled: editEnabled,
      });
      setServer(nextServer);
      loadInventoryForServer(nextServer);
      setOperation(null);
      setEditing(false);
      setEditDisplayName(nextServer.display_name);
      setEditTransport((nextServer.transport ?? 'streamable_http') as EditTransport);
      setEditUrl(nextServer.url ?? '');
      setEditStdioProfile(nextServer.stdio_profile_key ?? '');
      setEditEnabled(nextServer.enabled);
    } catch (error) {
      setPageError(errorMessage(error, 'MCP Server 配置更新失败'));
    } finally {
      setBusyAction(null);
    }
  }, [
    busyAction,
    editDisplayName,
    editEnabled,
    editStdioProfile,
    editTransport,
    editUrl,
    loadInventoryForServer,
    server,
  ]);

  const remove = useCallback(async () => {
    if (busyAction || !server?.removable) return;
    if (!await confirmRemove(`移除 MCP 服务“${serverName}”？此操作会移除服务配置和已保存的认证信息（如有）。`)) return;
    setBusyAction('remove');
    setPageError(null);
    try {
      await removeClaudeMcpServer(serverName);
      onBack();
    } catch (error) {
      setPageError(errorMessage(error, 'MCP 服务移除失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, onBack, server, serverName]);

  const flushAppUsagePolicy = useCallback(async () => {
    if (appUsagePolicySaveInFlightRef.current) return;
    const activeServer = serverRef.current;
    if (!activeServer || !appSettingsRef.current) return;

    const scope = appUsagePolicyScopeRef.current;
    let retryDelay: number | null = null;
    let conflictRebases = 0;
    appUsagePolicySaveInFlightRef.current = true;
    setAppUsagePolicySaving(true);
    setAppSettingsError(null);

    try {
      while (Object.keys(appUsagePolicyDirtyFieldsRef.current).length > 0) {
        if (scope !== appUsagePolicyScopeRef.current) return;
        const baseSettings = appSettingsRef.current;
        if (!baseSettings) return;

        const dirtySnapshot = { ...appUsagePolicyDirtyFieldsRef.current };
        const localDraft = appUsagePolicyDraftRef.current;
        const desired = appUsagePolicyDraft(baseSettings);
        if (dirtySnapshot.enabled) desired.enabled = localDraft.enabled;
        if (dirtySnapshot.lowRiskToolCalls) {
          desired.lowRiskToolCalls = localDraft.lowRiskToolCalls;
        }
        if (dirtySnapshot.uiMessages) desired.uiMessages = localDraft.uiMessages;

        let next: ClaudeMcpAppSettings;
        try {
          next = await updateClaudeMcpAppSettings(activeServer, baseSettings, desired);
        } catch (error) {
          const isRevisionConflict = error instanceof ClaudeMcpApiError
            && error.code === APP_SETTINGS_REVISION_CONFLICT;
          if (!isRevisionConflict || conflictRebases >= APP_USAGE_POLICY_MAX_CONFLICT_REBASES) {
            throw error;
          }
          conflictRebases += 1;
          const latest = await getClaudeMcpAppSettings(
            activeServer.id ?? serverName,
            activeServer.workspace_id,
          );
          if (scope !== appUsagePolicyScopeRef.current) return;
          adoptAppUsagePolicySettings(latest, true);
          continue;
        }

        if (scope !== appUsagePolicyScopeRef.current) return;
        appSettingsRef.current = next;
        const currentDirtyFields = appUsagePolicyDirtyFieldsRef.current;
        (Object.keys(dirtySnapshot) as AppUsagePolicyField[]).forEach((field) => {
          if (currentDirtyFields[field] === dirtySnapshot[field]) {
            delete currentDirtyFields[field];
          }
        });
        adoptAppUsagePolicySettings(next, true);
        conflictRebases = 0;
      }

      setAppSettingsError(null);
    } catch (error) {
      const detail = errorMessage(error, 'MCP 使用策略自动保存失败。');
      setAppSettingsError(`${detail} 当前选择已保留，将自动重试。`);
      retryDelay = APP_USAGE_POLICY_RETRY_DELAY_MS;
    } finally {
      appUsagePolicySaveInFlightRef.current = false;
      if (scope === appUsagePolicyScopeRef.current) setAppUsagePolicySaving(false);
      if (
        scope === appUsagePolicyScopeRef.current
        && Object.keys(appUsagePolicyDirtyFieldsRef.current).length > 0
        && appUsagePolicySaveTimerRef.current === null
      ) {
        appUsagePolicySaveTimerRef.current = setTimeout(() => {
          appUsagePolicySaveTimerRef.current = null;
          void flushAppUsagePolicy();
        }, retryDelay ?? 0);
      }
    }
  }, [adoptAppUsagePolicySettings, serverName]);

  const updateAppUsagePolicyDraft = useCallback((
    field: AppUsagePolicyField,
    value: boolean,
  ) => {
    const nextDraft = { ...appUsagePolicyDraftRef.current, [field]: value };
    appUsagePolicyDraftRef.current = nextDraft;
    if (field === 'enabled') setEditAppEnabled(value);
    if (field === 'lowRiskToolCalls') setEditAppLowRiskToolCalls(value);
    if (field === 'uiMessages') setEditAppUiMessages(value);

    appUsagePolicyChangeSequenceRef.current += 1;
    appUsagePolicyDirtyFieldsRef.current[field] = appUsagePolicyChangeSequenceRef.current;
    setAppSettingsError(null);
    if (appUsagePolicySaveTimerRef.current !== null) {
      clearTimeout(appUsagePolicySaveTimerRef.current);
    }
    appUsagePolicySaveTimerRef.current = setTimeout(() => {
      appUsagePolicySaveTimerRef.current = null;
      void flushAppUsagePolicy();
    }, APP_USAGE_POLICY_AUTO_SAVE_DELAY_MS);
  }, [flushAppUsagePolicy]);

  const tabCounts = {
    tools: inventory?.capabilities.tools.count,
    resources: inventory?.capabilities.resources.count,
    prompts: inventory?.capabilities.prompts.count,
  };


return {capability,server,inventory,operation,activeTab,setActiveTab,searchQuery,setSearchQuery,toolFilter,setToolFilter,loading,inventoryLoading,busyAction,pageError,inventoryError,appSettings,appSettingsError,appUsagePolicySaving,editAppEnabled,editAppLowRiskToolCalls,editAppUiMessages,editing,setEditing,editDisplayName,setEditDisplayName,editTransport,setEditTransport,editUrl,setEditUrl,editStdioProfile,setEditStdioProfile,editEnabled,setEditEnabled,effectiveState,visibleTools,startAuth,cancelAuth,logout,saveConfiguration,remove,updateAppUsagePolicyDraft,tabCounts,load};
}
