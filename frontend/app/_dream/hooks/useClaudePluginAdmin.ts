// [Input] Original Claude Code plugin API, installation permissions, Marketplace and operation DTOs.
// [Output] Shared Work plugin reads, install/operation/result, manual spec, uninstall and original failure feedback.
// [Pos] Extracted ClaudePluginAdminPage state; DOM focus and native controls remain platform-owned.
// [Sync] 2026-10-29: reuse the original Web state with stable optional HTTP transport and timer cleanup; business endpoints and permissions remain.
import {useCallback,useEffect,useRef,useState} from 'react';
import {
  ClaudePluginApiError,
  getClaudePluginOperation,
  installClaudePlugin,
  listClaudePluginInstallations,
  listClaudePluginMarketplace,
  listClaudePluginOperations,
  uninstallClaudePlugin,
  type ClaudePluginInstallation,
  type ClaudePluginMarketplaceEntry,
  type ClaudePluginOperation,
} from '../api/claudePluginAdminApi';

const SPEC_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9._-]*(@v?\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?)?$/;
const OPERATION_LIMIT = 8;
const OPERATION_POLL_INTERVAL_MS = 2_000;

export type ClaudePluginDialog = 'install' | 'marketplace' | 'operations' | null;
export type MarketplaceStep = 'select' | 'confirm' | 'installing' | 'result';

export function claudePluginErrorMessage(error: unknown): string {
  return error instanceof ClaudePluginApiError
    ? `${error.code}: ${error.message}`
    : error instanceof Error
      ? error.message
      : String(error);
}

export default function useClaudePluginAdmin(options:{transport?:typeof fetch;onSessionExpired?:()=>void}={}) {
  const defaults=useRef({transport:fetch});
  const transport=options.transport??defaults.current.transport;
  const expired=useRef(options.onSessionExpired);expired.current=options.onSessionExpired;
  const reportError=useCallback((reason:unknown)=>{
    if(reason instanceof ClaudePluginApiError&&reason.status===401)expired.current?.();
    return claudePluginErrorMessage(reason);
  },[]);
  const [installations, setInstallations] = useState<ClaudePluginInstallation[]>([]);
  const [operations, setOperations] = useState<ClaudePluginOperation[]>([]);
  const [spec, setSpec] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [installError, setInstallError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [canManage, setCanManage] = useState(false);
  const [trackedOperationId, setTrackedOperationId] = useState<string | null>(null);
  const [activeDialog, setActiveDialog] = useState<ClaudePluginDialog>(null);
  const [marketplaceEntries, setMarketplaceEntries] = useState<ClaudePluginMarketplaceEntry[]>([]);
  const [marketplaceLoading, setMarketplaceLoading] = useState(false);
  const [marketplaceError, setMarketplaceError] = useState<string | null>(null);
  const [marketplaceStep, setMarketplaceStep] = useState<MarketplaceStep>('select');
  const [selectedMarketplaceEntryId, setSelectedMarketplaceEntryId] = useState<string | null>(null);
  const [marketplaceOperationId, setMarketplaceOperationId] = useState<string | null>(null);
  const [marketplaceResult, setMarketplaceResult] = useState<ClaudePluginOperation | null>(null);
  const refresh = useCallback(async (initial = false) => {
    if (initial) setLoading(true);
    else setRefreshing(true);
    try {
      const [installResult, recentOperations] = await Promise.all([
        listClaudePluginInstallations(transport),
        listClaudePluginOperations(OPERATION_LIMIT,transport),
      ]);
      setInstallations(installResult.installations);
      setOperations(recentOperations);
      setCanManage(Boolean(installResult.permissions?.can_manage_shared_plugins));
      setError(null);
    } catch (reason) {
      setCanManage(false);
      setError(reportError(reason));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [transport,reportError]);

  useEffect(() => {
    void refresh(true);
  }, [refresh]);

  const loadMarketplace = useCallback(async () => {
    setMarketplaceLoading(true);
    setMarketplaceError(null);
    try {
      const result = await listClaudePluginMarketplace(transport);
      setMarketplaceEntries(result.entries);
      setSelectedMarketplaceEntryId((current) => (
        current && result.entries.some((entry) => entry.id === current)
          ? current
          : result.entries[0]?.id ?? null
      ));
    } catch (reason) {
      setMarketplaceEntries([]);
      setSelectedMarketplaceEntryId(null);
      setMarketplaceError(reportError(reason));
    } finally {
      setMarketplaceLoading(false);
    }
  }, [transport,reportError]);

  useEffect(() => {
    if (activeDialog !== 'marketplace') return;
    void loadMarketplace();
  }, [activeDialog, loadMarketplace]);

  useEffect(() => {
    if (!trackedOperationId) return undefined;
    let stopped = false;
    const tick = async () => {
      try {
        const operation = await getClaudePluginOperation(trackedOperationId,transport);
        if (stopped) return;
        setOperations((current) => {
          const rest = current.filter((item) => item.id !== operation.id);
          return [operation, ...rest].slice(0, OPERATION_LIMIT);
        });
        if (operation.status === 'ready' || operation.status === 'error') {
          setTrackedOperationId(null);
          if (operation.id === marketplaceOperationId) {
            setMarketplaceResult(operation);
            setMarketplaceStep('result');
            setMarketplaceOperationId(null);
            void loadMarketplace();
          }
          setSuccessMessage(
            operation.status === 'ready'
              ? `${operation.requested_package_spec} 安装完成。`
              : null,
          );
          void refresh();
        }
      } catch (reason) {
        if(reason instanceof ClaudePluginApiError&&reason.status===401)expired.current?.();
        // A transient poll failure must not replace the last visible operation state.
      }
    };
    void tick();
    const timer = setInterval(tick, OPERATION_POLL_INTERVAL_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [trackedOperationId, refresh, marketplaceOperationId, loadMarketplace,transport]);

  const handleInstall = useCallback(async () => {
    const trimmed = spec.trim();
    if (!SPEC_PATTERN.test(trimmed)) {
      setInstallError('包名格式应为 <plugin>@<marketplace>，例如 superpowers@claude-plugins-official');
      return;
    }
    if (!canManage) {
      setInstallError('当前账户没有共享插件管理权限。');
      return;
    }
    setBusy(true);
    setInstallError(null);
    setSuccessMessage(null);
    try {
      const accepted = await installClaudePlugin({ packageSpec: trimmed },transport);
      setTrackedOperationId(accepted.operation_id);
      setSpec('');
      setActiveDialog('operations');
    } catch (reason) {
      setInstallError(reportError(reason));
    } finally {
      setBusy(false);
    }
  }, [canManage, spec,transport,reportError]);

  const handleMarketplaceInstall = useCallback(async () => {
    const entry = marketplaceEntries.find((item) => item.id === selectedMarketplaceEntryId);
    if (!entry) {
      setMarketplaceError('请选择一个 Marketplace 插件。');
      setMarketplaceStep('select');
      return;
    }
    if (!canManage) {
      setMarketplaceError('当前账户没有共享插件管理权限。');
      return;
    }
    setBusy(true);
    setMarketplaceError(null);
    setMarketplaceResult(null);
    try {
      const accepted = await installClaudePlugin({ marketplaceEntryId: entry.id },transport);
      setMarketplaceOperationId(accepted.operation_id);
      setTrackedOperationId(accepted.operation_id);
      setMarketplaceStep('installing');
    } catch (reason) {
      setMarketplaceError(reportError(reason));
      setMarketplaceStep('confirm');
    } finally {
      setBusy(false);
    }
  }, [canManage, marketplaceEntries, selectedMarketplaceEntryId,transport,reportError]);

  const handleUninstall = useCallback(async (installationId: string) => {
    if (!canManage) return;
    setBusy(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await uninstallClaudePlugin(installationId,transport);
      await refresh();
      setSuccessMessage('插件已卸载。');
    } catch (reason) {
      setError(reportError(reason));
    } finally {
      setBusy(false);
    }
  }, [canManage, refresh,transport,reportError]);

  const selectedMarketplaceEntry = marketplaceEntries.find(
    (entry) => entry.id === selectedMarketplaceEntryId,
  ) ?? null;
  const activeMarketplaceOperation = marketplaceOperationId
    ? operations.find((operation) => operation.id === marketplaceOperationId) ?? null
    : null;

  const openDialog=(dialog:Exclude<ClaudePluginDialog,null>)=>{
    setInstallError(null);
    if (dialog === 'marketplace') {
      setMarketplaceStep('select');
      setMarketplaceResult(null);
      setMarketplaceError(null);
    }
    setActiveDialog(dialog);
  };

  return {installations,operations,spec,setSpec,error,installError,successMessage,loading,refreshing,busy,canManage,activeDialog,setActiveDialog,marketplaceEntries,marketplaceLoading,marketplaceError,setMarketplaceError,marketplaceStep,setMarketplaceStep,selectedMarketplaceEntryId,setSelectedMarketplaceEntryId,marketplaceOperationId,marketplaceResult,refresh,loadMarketplace,handleInstall,handleMarketplaceInstall,handleUninstall,selectedMarketplaceEntry,activeMarketplaceOperation,openDialog};
}
