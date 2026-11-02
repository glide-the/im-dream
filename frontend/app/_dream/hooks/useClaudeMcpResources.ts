// [Input] Original managed MCP index state and concrete platform HTTP/operation handoff.
// [Output] One list, create form, operation recovery and mutation state for Web/native.
// [Pos] State extracted from ClaudeMcpResourceSection; callers own navigation and controls.
// [Sync] 2026-10-29: extract original state for Web/native reuse; HTTP, business payloads and permissions keep their owners.
import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import * as browserApi from '../api/claudeMcpApi';
import {ClaudeMcpApiError,type ClaudeMcpCapability,type ClaudeMcpAuthState,type ClaudeMcpConfigScope,type ClaudeMcpOperation,type ClaudeMcpServer,type ClaudeMcpServerInventory,type ClaudeMcpState,type ClaudeMcpTool,type ClaudeMcpAppSettings,type ClaudeMcpApi} from '../api/claudeMcpApi';
import {rememberClaudeMcpOAuthOperation as browserRemember,forgetClaudeMcpOAuthOperation as browserForget} from '../components/claude-mcp/oauthHandoff';
import {canStartClaudeMcpAuth} from '../components/claude-mcp/authPolicy';
import {OPERATION_POLL_INTERVAL_MS,CAPABILITY_RETRY_INTERVAL_MS,CAPABILITY_UNAVAILABLE,ACTIVE_STATES,STATE_LABELS,SCOPE_LABELS,AUTH_STATE_LABELS,authStateOf,serverStatusLabel,canLogout,canDetectConnection,safeApiErrorMessage,safeOperationError,messageForCapability,operationFor} from '../components/claude-mcp/mcpResourcePresentation';
interface Options {api?:ClaudeMcpApi;active?:boolean;remember?:(id:string)=>boolean;forget?:(id?:string)=>void}
export default function useClaudeMcpResources(options:Options={}){
const active=options.active??true;const owner=useRef({api:options.api??browserApi,remember:options.remember??browserRemember,forget:options.forget??browserForget});
const {getClaudeMcpCapability,listClaudeMcpServers,getClaudeMcpServer,getClaudeMcpAppSettings,updateClaudeMcpAppSettings,getClaudeMcpAppEffectiveStatus,getClaudeMcpServerInventory,configureClaudeMcpServer,updateClaudeMcpServer,removeClaudeMcpServer,startClaudeMcpAuth,getClaudeMcpOperation,submitClaudeMcpRedirect,cancelClaudeMcpAuth,logoutClaudeMcpServer}=owner.current.api;const rememberClaudeMcpOAuthOperation=owner.current.remember,forgetClaudeMcpOAuthOperation=owner.current.forget;
  const [capability, setCapability] = useState<ClaudeMcpCapability | null>(null);
  const [servers, setServers] = useState<ClaudeMcpServer[]>([]);
  const [operations, setOperations] = useState<Record<string, ClaudeMcpOperation>>({});
  const [loading, setLoading] = useState(true);
  const [busyServer, setBusyServer] = useState<string | null>(null);
  const [serverName, setServerName] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [serverTransport, setServerTransport] = useState<'streamable_http' | 'sse' | 'stdio'>('streamable_http');
  const [stdioProfileKey, setStdioProfileKey] = useState('');
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [configurationError, setConfigurationError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [capabilityResult, serversResult] = await Promise.allSettled([
        getClaudeMcpCapability(),
        listClaudeMcpServers(),
      ]);
      if (capabilityResult.status === 'rejected') throw capabilityResult.reason;
      const nextCapability = capabilityResult.value;
      setCapability(nextCapability);
      if (!nextCapability.enabled) {
        setServers([]);
        return;
      }
      if (serversResult.status === 'rejected') throw serversResult.reason;
      const nextServers = serversResult.value;
      setServers(nextServers);
      const activeIds = nextServers
        .map((server) => server.active_operation_id)
        .filter((id): id is string => Boolean(id));
      const recovered = await Promise.all(activeIds.map(getClaudeMcpOperation));
      setOperations((current) => ({
        ...current,
        ...Object.fromEntries(recovered.map((operation) => [operation.id, operation])),
      }));
    } catch (cause) {
      setError(safeApiErrorMessage(cause, 'Claude MCP 状态读取失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!active || capability?.reason_code !== CAPABILITY_UNAVAILABLE) return undefined;
    const timer = setTimeout(() => {
      void load();
    }, CAPABILITY_RETRY_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [active, capability, load]);

  const activeOperationIds = useMemo(
    () => Object.values(operations)
      .filter((operation) => ACTIVE_STATES.includes(operation.state))
      .map((operation) => operation.id),
    [operations],
  );

  useEffect(() => {
    if (!active || activeOperationIds.length === 0) return undefined;
    const timer = setInterval(() => {
      void Promise.all(activeOperationIds.map(getClaudeMcpOperation))
        .then((items) => {
          setOperations((current) => ({
            ...current,
            ...Object.fromEntries(items.map((operation) => [operation.id, operation])),
          }));
          if (items.some((item) => !ACTIVE_STATES.includes(item.state))) {
            items
              .filter((item) => !ACTIVE_STATES.includes(item.state))
              .forEach((item) => forgetClaudeMcpOAuthOperation(item.id));
            void load();
          }
        })
        .catch((cause: unknown) => {
          setError(safeApiErrorMessage(cause, '认证状态刷新失败'));
        });
    }, OPERATION_POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [active, activeOperationIds, load]);

  const start = async (server: ClaudeMcpServer, state: ClaudeMcpState) => {
    if (!canStartClaudeMcpAuth(server, state)) return;
    setBusyServer(server.name);
    setError(null);
    try {
      const operation = await startClaudeMcpAuth(server.name);
      if (!rememberClaudeMcpOAuthOperation(operation.id)) {
        await cancelClaudeMcpAuth(operation.id);
        throw new Error('browser operation handoff unavailable');
      }
      setOperations((current) => ({ ...current, [operation.id]: operation }));
    } catch (cause) {
      setError(safeApiErrorMessage(cause, '认证启动失败'));
    } finally {
      setBusyServer(null);
    }
  };

  const configure = async () => {
    const name = serverName.trim();
    const url = serverUrl.trim();
    const profileKey = stdioProfileKey.trim();
    if (!name || (serverTransport === 'stdio' ? !profileKey : !url)) {
      setConfigurationError(serverTransport === 'stdio'
        ? '请填写 MCP 服务名称并选择服务端 stdio profile。'
        : '请填写 MCP 服务名称和完整 HTTP 或 HTTPS URL。');
      return;
    }
    setConfiguring(true);
    setConfigurationError(null);
    try {
      const next = await configureClaudeMcpServer(
        name,
        serverTransport === 'stdio' ? null : url,
        {
          transport: serverTransport,
          stdioProfileKey: serverTransport === 'stdio' ? profileKey : null,
        },
      );
      setServers((current) => [
        ...current.filter((server) => server.name !== next.name),
        next,
      ]);
      setServerName('');
      setServerUrl('');
      setStdioProfileKey('');
      setAddDialogOpen(false);
    } catch (cause) {
      setConfigurationError(safeApiErrorMessage(cause, 'MCP 服务配置失败'));
    } finally {
      setConfiguring(false);
    }
  };

  const cancel = async (operation: ClaudeMcpOperation) => {
    setBusyServer(operation.server_name);
    setError(null);
    try {
      const next = await cancelClaudeMcpAuth(operation.id);
      setOperations((current) => ({ ...current, [next.id]: next }));
      forgetClaudeMcpOAuthOperation(operation.id);
      await load();
    } catch (cause) {
      setError(safeApiErrorMessage(cause, '认证取消失败'));
    } finally {
      setBusyServer(null);
    }
  };

  const logout = async (serverName: string) => {
    setBusyServer(serverName);
    setError(null);
    try {
      const next = await logoutClaudeMcpServer(serverName);
      setServers((current) => current.map((server) => server.name === next.name ? next : server));
      setOperations((current) => Object.fromEntries(
        Object.entries(current).filter(([, operation]) => operation.server_name !== serverName),
      ));
    } catch (cause) {
      setError(safeApiErrorMessage(cause, '退出认证失败'));
    } finally {
      setBusyServer(null);
    }
  };

  const remove = async (name: string) => {
    setBusyServer(name);
    setError(null);
    try {
      await removeClaudeMcpServer(name);
      setServers((current) => current.filter((server) => server.name !== name));
      setOperations((current) => Object.fromEntries(
        Object.entries(current).filter(([, operation]) => operation.server_name !== name),
      ));
    } catch (cause) {
      setError(safeApiErrorMessage(cause, 'MCP 服务移除失败'));
    } finally {
      setBusyServer(null);
    }
  };


return {capability,servers,operations,loading,busyServer,serverName,setServerName,serverUrl,setServerUrl,serverTransport,setServerTransport,stdioProfileKey,setStdioProfileKey,addDialogOpen,setAddDialogOpen,configuring,configurationError,setConfigurationError,error,load,start,configure,cancel,logout,remove};
}
