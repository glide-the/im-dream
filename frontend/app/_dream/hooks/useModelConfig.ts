// [Input] Original Settings model/configuration state, Cookie/CSRF HTTP and model catalog.
// [Output] One shared read/save/recovery lifecycle for Web and native settings fields.
// [Pos] Existing model-settings state owner; platform renderers retain their own controls.
// [Sync] 2026-10-29: extract original handlers; optional native HTTP and saved-config notification retain original URLs/DTOs.
import {useCallback,useEffect,useRef,useState} from 'react';
import {browserRequestHeaders} from '../lib/browserSession';
import {emitImFullAccessChanged,emitWorkspaceModeChanged} from '../lib/system-config-events';
import {API_BASE} from '../lib/apiBase';
import {fetchGatewayModels,gatewayModelsErrorMessage,resolveGatewayModelSelection,type GatewayModel} from '../api/gatewayModelsApi';
export type SandboxNetworkMode = 'disabled' | 'allowlist' | 'open';

interface EnvVar {
  key: string;
  value: string;
}

interface SystemConfigData {
  model?: string;
  image_model?: string;
  system_prompt?: string;
  workspace_enabled?: boolean;
  sandbox_network_mode?: SandboxNetworkMode;
  sandbox_network_allowed_domains?: string[];
  sandbox_fs_allowed_write_paths?: string[];
  im_full_access_enabled?: boolean;
  env_vars?: Record<string, string>;
}

type SystemConfigResponse = { success?: boolean; data?: SystemConfigData } & SystemConfigData;

const DEFAULT_SYSTEM_PROMPT = 'You are a concise and practical AI assistant for note-taking and writing.';

function isSandboxNetworkMode(value: unknown): value is SandboxNetworkMode {
  return value === 'disabled' || value === 'allowlist' || value === 'open';
}

function formatSandboxNetworkDomains(domains: string[] | undefined): string {
  return Array.isArray(domains) ? domains.join('\n') : '';
}

export function parseSandboxNetworkDomains(value: string): string[] {
  const domains: string[] = [];
  for (const rawPart of value.split(/[\n,;]+/)) {
    const part = rawPart.trim().toLowerCase();
    if (!part || part === '*') continue;
    const withoutProtocol = part.replace(/^[a-z][a-z0-9+.-]*:\/\//, '');
    const host = withoutProtocol.split('/')[0].split('?')[0].split('#')[0].replace(/:\d+$/, '').replace(/\.$/, '');
    if (host && !domains.includes(host)) {
      domains.push(host);
    }
  }
  return domains;
}

function normalizeSandboxNetworkDomain(value: string): string | null {
  return parseSandboxNetworkDomains(value)[0] ?? null;
}

function formatSandboxFsWritePaths(paths: string[] | undefined): string {
  return Array.isArray(paths) ? paths.join('\n') : '';
}

export function parseSandboxFsWritePaths(value: string): string[] {
  const paths: string[] = [];
  for (const rawPart of value.split(/[\n,;]+/)) {
    const part = rawPart.trim();
    if (!part || !part.startsWith('/')) continue;
    const normalized = part.replace(/\/+$/, '') || '/';
    if (!paths.includes(normalized)) {
      paths.push(normalized);
    }
  }
  return paths;
}

function normalizeSandboxFsWritePath(value: string): string | null {
  return parseSandboxFsWritePaths(value)[0] ?? null;
}

function readSystemConfigResponse(payload: SystemConfigResponse): SystemConfigData {
  return payload.data ?? payload;
}

function hasSystemConfigFields(config: SystemConfigData): boolean {
  return Boolean(
    config.model !== undefined
    || config.image_model !== undefined
    || config.system_prompt !== undefined
    || config.workspace_enabled !== undefined
    || config.sandbox_network_mode !== undefined
    || config.sandbox_network_allowed_domains !== undefined
    || config.sandbox_fs_allowed_write_paths !== undefined
    || config.im_full_access_enabled !== undefined
    || config.env_vars !== undefined
  );
}

export interface ModelConfigOptions {
  transport?:typeof fetch;
  onConfigSaved?:()=>void;
  onSessionExpired?:()=>void;
  onWorkspaceModeChanged?:(enabled:boolean)=>void;
  onImFullAccessChanged?:(enabled:boolean)=>void;
}
export default function useModelConfig({transport=fetch,onConfigSaved,onSessionExpired,onWorkspaceModeChanged=emitWorkspaceModeChanged,onImFullAccessChanged=emitImFullAccessChanged}:ModelConfigOptions={}) {
  const callbacks=useRef({onConfigSaved,onSessionExpired});callbacks.current={onConfigSaved,onSessionExpired};
  const request=useCallback<typeof fetch>(async(input,init)=>{
    const response=await transport(input,init);
    if(response.status===401)callbacks.current.onSessionExpired?.();
    return response;
  },[transport]);
  const notifySaved=useCallback(()=>callbacks.current.onConfigSaved?.(),[]);
  const [configSaveError,setConfigSaveError]=useState<string|null>(null);

  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPT);
  const [workspaceMode, setWorkspaceMode] = useState(true);
  const [sandboxNetworkMode, setSandboxNetworkMode] = useState<SandboxNetworkMode>('allowlist');
  const [sandboxNetworkDomains, setSandboxNetworkDomains] = useState('');
  const [sandboxNetworkSaving, setSandboxNetworkSaving] = useState(false);
  const [sandboxNetworkStatus, setSandboxNetworkStatus] = useState<string | null>(null);
  const [sandboxNetworkAddingDomain, setSandboxNetworkAddingDomain] = useState(false);
  const [sandboxNetworkNewDomain, setSandboxNetworkNewDomain] = useState('');
  const [sandboxFsPaths, setSandboxFsPaths] = useState('');
  const [sandboxFsSaving, setSandboxFsSaving] = useState(false);
  const [sandboxFsStatus, setSandboxFsStatus] = useState<string | null>(null);
  const [sandboxFsAddingPath, setSandboxFsAddingPath] = useState(false);
  const [sandboxFsNewPath, setSandboxFsNewPath] = useState('');
  const [imFullAccessEnabled, setImFullAccessEnabled] = useState(false);
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedImageModel, setSelectedImageModel] = useState('');
  const [imageModelOptions, setImageModelOptions] = useState<GatewayModel[]>([]);
  const [imageModelStatus, setImageModelStatus] = useState<string | null>(null);
  const [configReadError, setConfigReadError] = useState<string | null>(null);
  const [modelSaveUnconfirmed, setModelSaveUnconfirmed] = useState(false);
  const [modelOptions, setModelOptions] = useState<GatewayModel[]>([]);
  const [defaultModelAlias, setDefaultModelAlias] = useState<string | null>(null);
  const [modelCatalogError, setModelCatalogError] = useState<string | null>(null);
  const [modelStatus, setModelStatus] = useState<string | null>(null);
  const [modelLoadNonce, setModelLoadNonce] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [configLoading, setConfigLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [envVars, setEnvVars] = useState<EnvVar[]>([]);
  const [envVarsDirty, setEnvVarsDirty] = useState(false);
  const [envVarsSaving, setEnvVarsSaving] = useState(false);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setConfigLoading(true);
    setConfigSaveError(null);
    void (async () => {
      const configRequest = request(`${API_BASE}/api/system-config`, {
        headers: { ...browserRequestHeaders() },
        signal: controller.signal,
      });
      const modelsRequest = fetchGatewayModels(controller.signal, request);
      try {
        const [configResult, modelsResult] = await Promise.allSettled([configRequest, modelsRequest]);
        if (!active) return;
        if (modelsResult.status === 'fulfilled') {
          setModelOptions(modelsResult.value.models);
          setImageModelOptions(modelsResult.value.imageModels);
          setDefaultModelAlias(modelsResult.value.defaultModelAlias);
          setModelCatalogError(null);
        } else if (modelsResult.reason?.name !== 'AbortError') {
          setModelCatalogError(gatewayModelsErrorMessage(modelsResult.reason));
        }
        if (configResult.status !== 'fulfilled' || !configResult.value.ok) {
          setConfigReadError('模型设置读取失败，请重新加载后再选择。');
          return;
        }
        const payload = (await configResult.value.json()) as SystemConfigResponse;
        const config = readSystemConfigResponse(payload);
        if (!active) return;
        setConfigReadError(null);
        setModelSaveUnconfirmed(false);
        setModelStatus(null);
        setImageModelStatus(null);
        setSelectedImageModel(config.image_model ?? '');
        setSystemPrompt(config.system_prompt ?? DEFAULT_SYSTEM_PROMPT);
        setWorkspaceMode(config.workspace_enabled ?? true);
        setSandboxNetworkMode(isSandboxNetworkMode(config.sandbox_network_mode) ? config.sandbox_network_mode : 'allowlist');
        setSandboxNetworkDomains(formatSandboxNetworkDomains(config.sandbox_network_allowed_domains));
        setSandboxFsPaths(formatSandboxFsWritePaths(config.sandbox_fs_allowed_write_paths));
        setSandboxFsStatus(null);
        setSandboxNetworkStatus(null);
        setImFullAccessEnabled(config.im_full_access_enabled ?? false);
        setSelectedModel(
          modelsResult.status === 'fulfilled'
            ? resolveGatewayModelSelection(config.model, modelsResult.value)
            : (config.model ?? ''),
        );
        const savedEnvVars = config.env_vars ?? {};
        setEnvVars(Object.entries(savedEnvVars).map(([key, value]) => ({ key, value })));
        setDirty(false);
        setEnvVarsDirty(false);
      } catch (error) {
        if ((error as { name?: string }).name !== 'AbortError') {
          setConfigReadError('模型设置读取失败，请重新加载后再选择。');
        }
      } finally {
        if (active) setConfigLoading(false);
      }
    })();
    return () => { active = false; controller.abort(); };
  }, [modelLoadNonce, request]);

  const updateConfig = useCallback(async (patch: Partial<SystemConfigData>): Promise<SystemConfigData | null> => {
    setSaving(true);
    setConfigSaveError(null);
    try {
      const response = await request(`${API_BASE}/api/system-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...browserRequestHeaders() },
        body: JSON.stringify(patch),
      });
      if (!response.ok) { setConfigSaveError(response.status>=500?'保存结果未确认，请重新读取设置核对。':'设置保存失败，请重试。'); return null; }
      const payload = (await response.json().catch(() => null)) as SystemConfigResponse | null;
      if (!payload) { notifySaved(); return patch; }
      const config = readSystemConfigResponse(payload);
      notifySaved();
      return hasSystemConfigFields(config) ? config : patch;
    } catch {
      setConfigSaveError('连接中断，保存结果未确认，请重新读取设置核对。');
      return null;
    } finally {
      setSaving(false);
    }
  }, [request, notifySaved]);

  const handleModelChange = useCallback((value: string) => {
    const target = modelOptions.find((option) => option.modelAlias === value);
    if (!target?.callable) {
      setModelStatus(target?.upgradeHint ?? '此模型当前不可调用，请查看所需套餐或稍后重试。');
      return;
    }
    if (configLoading || configReadError || modelCatalogError || modelSaveUnconfirmed || saving) return;
    const previous = selectedModel;
    setSelectedModel(value);
    setModelStatus('正在保存平台模型…');
    void (async () => {
      try {
        setSaving(true);
        const response = await request(`${API_BASE}/api/system-config`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', ...browserRequestHeaders() },
          body: JSON.stringify({ model: value }),
        });
        if (response.ok) {
          const payload = (await response.json().catch(() => null)) as SystemConfigResponse | null;
          const savedConfig = payload ? readSystemConfigResponse(payload) : null;
          if (savedConfig?.model === value) {
            setSelectedModel(savedConfig.model);
            setModelStatus('模型已保存，将用于新对话。');
            notifySaved();
            return;
          }
        }
        setSelectedModel(previous);
        if (response.status === 403) {
          setModelStatus('当前账号没有此模型的调用权限，请重新选择。');
        } else if (response.status === 409) {
          setModelStatus('模型状态已变化，请重新选择。');
          setModelLoadNonce((nonce) => nonce + 1);
        } else {
          setModelStatus('模型保存结果未确认，请重新加载设置核对。');
          setModelSaveUnconfirmed(true);
        }
      } catch {
        setSelectedModel(previous);
        setModelStatus('网络连接失败，模型保存结果未确认，请重新加载设置核对。');
        setModelSaveUnconfirmed(true);
      } finally {
        setSaving(false);
      }
    })();
  }, [modelOptions, selectedModel, configLoading, configReadError, modelCatalogError, modelSaveUnconfirmed, saving, request, notifySaved]);

  const handleImageModelChange = useCallback((value: string) => {
    const target = imageModelOptions.find(option => option.modelAlias === value);
    if (!target?.images?.callable || saving || configLoading || configReadError || modelCatalogError || modelSaveUnconfirmed) return;
    const previous = selectedImageModel;
    setSelectedImageModel(value);
    setImageModelStatus('正在保存 Image 模型…');
    setSaving(true);
    void (async () => {
      try {
        const response = await request(`${API_BASE}/api/system-config`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json', ...browserRequestHeaders() },
          body: JSON.stringify({ image_model: value }),
        });
        const payload = response.ok ? await response.json().catch(() => null) as SystemConfigResponse | null : null;
        const savedConfig = payload ? readSystemConfigResponse(payload) : null;
        if (response.ok && savedConfig?.image_model === value) {
          setSelectedImageModel(value);
          setImageModelStatus('Image 模型已保存，仅用于后续 image_gen 工具调用。');
          notifySaved();
          return;
        }
        setSelectedImageModel(previous);
        setImageModelStatus(response.status === 403 ? 'Image 模型当前不可调用，请重新加载后选择其他模型。'
          : response.status === 409 ? 'Image 模型状态已变化，请重新加载后选择。'
            : 'Image 模型保存结果未确认，请重新加载设置核对。');
        if (response.status === 403 || response.status === 409) setModelLoadNonce(nonce => nonce + 1);
        else setModelSaveUnconfirmed(true);
      } catch {
        setSelectedImageModel(previous);
        setImageModelStatus('网络连接失败，Image 模型保存结果未确认，请重新加载设置核对。');
        setModelSaveUnconfirmed(true);
      } finally {
        setSaving(false);
      }
    })();
  }, [imageModelOptions, selectedImageModel, saving, configLoading, configReadError, modelCatalogError, modelSaveUnconfirmed, request, notifySaved]);

  const handleWorkspaceToggle = useCallback(() => {
    const next = !workspaceMode;
    setWorkspaceMode(next);
    onWorkspaceModeChanged(next);
    void (async () => {
      const savedConfig = await updateConfig({ workspace_enabled: next });
      if (savedConfig) {
        const persisted = savedConfig.workspace_enabled ?? next;
        setWorkspaceMode(persisted);
        onWorkspaceModeChanged(persisted);
        return;
      }
      setWorkspaceMode(!next);
      onWorkspaceModeChanged(!next);
    })();
  }, [updateConfig, workspaceMode, onWorkspaceModeChanged]);

  const saveSandboxNetworkDomains = useCallback(async (domains: string[]) => {
    setSandboxNetworkSaving(true);
    const savedConfig = await updateConfig({ sandbox_network_allowed_domains: domains });
    if (savedConfig) {
      setSandboxNetworkDomains(formatSandboxNetworkDomains(savedConfig.sandbox_network_allowed_domains ?? domains));
      if (isSandboxNetworkMode(savedConfig.sandbox_network_mode)) {
        setSandboxNetworkMode(savedConfig.sandbox_network_mode);
      }
      setSandboxNetworkStatus('域名允许列表已保存。');
    } else {
      setSandboxNetworkStatus('域名允许列表保存失败，请稍后重试。');
    }
    setSandboxNetworkSaving(false);
    return Boolean(savedConfig);
  }, [updateConfig]);

  const handleSandboxNetworkModeChange = useCallback((mode: SandboxNetworkMode) => {
    const previousMode = sandboxNetworkMode;
    setSandboxNetworkMode(mode);
    setSandboxNetworkStatus(null);
    void (async () => {
      const savedConfig = await updateConfig({ sandbox_network_mode: mode });
      if (savedConfig) {
        setSandboxNetworkMode(isSandboxNetworkMode(savedConfig.sandbox_network_mode) ? savedConfig.sandbox_network_mode : mode);
        setSandboxNetworkDomains(formatSandboxNetworkDomains(savedConfig.sandbox_network_allowed_domains ?? parseSandboxNetworkDomains(sandboxNetworkDomains)));
        setSandboxNetworkStatus('网络策略已保存。');
        return;
      }
      setSandboxNetworkMode(previousMode);
      setSandboxNetworkStatus('网络策略保存失败，请稍后重试。');
    })();
  }, [sandboxNetworkDomains, sandboxNetworkMode, updateConfig]);

  const handleSandboxNetworkAccessToggle = useCallback((enabled: boolean) => {
    const nextMode: SandboxNetworkMode = enabled
      ? (sandboxNetworkMode === 'disabled' ? 'allowlist' : sandboxNetworkMode)
      : 'disabled';
    void handleSandboxNetworkModeChange(nextMode);
  }, [handleSandboxNetworkModeChange, sandboxNetworkMode]);

  const handleSandboxNetworkPolicySelect = useCallback((value: string) => {
    const mode: SandboxNetworkMode = value === 'open' ? 'open' : 'allowlist';
    void handleSandboxNetworkModeChange(mode);
  }, [handleSandboxNetworkModeChange]);

  const handleAddSandboxNetworkDomain = useCallback(() => {
    if (!sandboxNetworkAddingDomain) {
      setSandboxNetworkAddingDomain(true);
      setSandboxNetworkStatus(null);
      return;
    }
    const domain = normalizeSandboxNetworkDomain(sandboxNetworkNewDomain);
    if (!domain) {
      setSandboxNetworkStatus('请输入有效域名。');
      return;
    }
    const domains = parseSandboxNetworkDomains(sandboxNetworkDomains);
    if (!domains.includes(domain)) {
      domains.push(domain);
    }
    setSandboxNetworkNewDomain('');
    setSandboxNetworkAddingDomain(false);
    void saveSandboxNetworkDomains(domains);
  }, [
    sandboxNetworkAddingDomain,
    sandboxNetworkDomains,
    sandboxNetworkNewDomain,
    saveSandboxNetworkDomains,
  ]);

  const handleRemoveSandboxNetworkDomain = useCallback((domain: string) => {
    const domains = parseSandboxNetworkDomains(sandboxNetworkDomains)
      .filter((item) => item !== domain);
    void saveSandboxNetworkDomains(domains);
  }, [sandboxNetworkDomains, saveSandboxNetworkDomains]);

  const saveSandboxFsWritePaths = useCallback(async (paths: string[]) => {
    setSandboxFsSaving(true);
    const savedConfig = await updateConfig({ sandbox_fs_allowed_write_paths: paths });
    if (savedConfig) {
      setSandboxFsPaths(formatSandboxFsWritePaths(savedConfig.sandbox_fs_allowed_write_paths ?? paths));
      setSandboxFsStatus('可写路径已保存。');
    } else {
      setSandboxFsStatus('可写路径保存失败，请稍后重试。');
    }
    setSandboxFsSaving(false);
    return Boolean(savedConfig);
  }, [updateConfig]);

  const handleAddSandboxFsPath = useCallback(() => {
    if (!sandboxFsAddingPath) {
      setSandboxFsAddingPath(true);
      setSandboxFsStatus(null);
      return;
    }
    const path = normalizeSandboxFsWritePath(sandboxFsNewPath);
    if (!path) {
      setSandboxFsStatus('请输入以 / 开头的绝对路径。');
      return;
    }
    const paths = parseSandboxFsWritePaths(sandboxFsPaths);
    if (!paths.includes(path)) {
      paths.push(path);
    }
    setSandboxFsNewPath('');
    setSandboxFsAddingPath(false);
    void saveSandboxFsWritePaths(paths);
  }, [
    sandboxFsAddingPath,
    sandboxFsNewPath,
    sandboxFsPaths,
    saveSandboxFsWritePaths,
  ]);

  const handleRemoveSandboxFsPath = useCallback((path: string) => {
    const paths = parseSandboxFsWritePaths(sandboxFsPaths)
      .filter((item) => item !== path);
    void saveSandboxFsWritePaths(paths);
  }, [sandboxFsPaths, saveSandboxFsWritePaths]);

  const handleImFullAccessToggle = useCallback(() => {
    const next = !imFullAccessEnabled;
    setImFullAccessEnabled(next);
    onImFullAccessChanged(next);
    void (async () => {
      const savedConfig = await updateConfig({ im_full_access_enabled: next });
      if (savedConfig) {
        const persisted = savedConfig.im_full_access_enabled ?? next;
        setImFullAccessEnabled(persisted);
        onImFullAccessChanged(persisted);
        return;
      }
      setImFullAccessEnabled(!next);
      onImFullAccessChanged(!next);
    })();
  }, [imFullAccessEnabled, updateConfig, onImFullAccessChanged]);

  const handleSavePrompt = useCallback(() => {
    void (async () => {
      const savedConfig = await updateConfig({ system_prompt: systemPrompt });
      if (savedConfig) {
        setSystemPrompt(savedConfig.system_prompt ?? systemPrompt);
        setDirty(false);
      }
    })();
  }, [systemPrompt, updateConfig]);

  const handleResetPrompt = useCallback(() => {
    setSystemPrompt(DEFAULT_SYSTEM_PROMPT);
    setDirty(true);
  }, []);

  const handleAddEnvVar = useCallback(() => {
    setEnvVars((prev) => [...prev, { key: '', value: '' }]);
    setEnvVarsDirty(true);
  }, []);

  const handleRemoveEnvVar = useCallback((index: number) => {
    setEnvVars((prev) => prev.filter((_, i) => i !== index));
    setEnvVarsDirty(true);
  }, []);

  const handleUpdateEnvVar = useCallback((index: number, field: 'key' | 'value', val: string) => {
    setEnvVars((prev) => prev.map((item, i) => i === index ? { ...item, [field]: val } : item));
    setEnvVarsDirty(true);
  }, []);

  const handleSaveEnvVars = useCallback(async () => {
    const record: Record<string, string> = {};
    for (const { key, value } of envVars) {
      if (key.trim()) record[key.trim()] = value.trim();
    }
    setEnvVarsSaving(true);
    try {
      const savedConfig = await updateConfig({ env_vars: record });
      if (savedConfig) {
        const savedEnvVars = savedConfig.env_vars ?? record;
        setEnvVars(Object.entries(savedEnvVars).map(([key, value]) => ({ key, value })));
        setEnvVarsDirty(false);
      }
    } finally {
      setEnvVarsSaving(false);
    }
  }, [envVars, updateConfig]);


  return {
    configSaveError,
    systemPrompt,setSystemPrompt,workspaceMode,sandboxNetworkMode,sandboxNetworkDomains,sandboxNetworkSaving,
    sandboxNetworkStatus,sandboxNetworkAddingDomain,setSandboxNetworkAddingDomain,sandboxNetworkNewDomain,setSandboxNetworkNewDomain,sandboxFsPaths,
    sandboxFsSaving,sandboxFsStatus,sandboxFsAddingPath,setSandboxFsAddingPath,sandboxFsNewPath,setSandboxFsNewPath,
    imFullAccessEnabled,selectedModel,selectedImageModel,imageModelOptions,imageModelStatus,configReadError,
    modelSaveUnconfirmed,modelOptions,defaultModelAlias,modelCatalogError,modelStatus,setModelLoadNonce,
    dirty,setDirty,configLoading,setConfigLoading,saving,envVars,
    envVarsDirty,envVarsSaving,handleModelChange,handleImageModelChange,handleWorkspaceToggle,handleSandboxNetworkAccessToggle,
    handleSandboxNetworkPolicySelect,handleAddSandboxNetworkDomain,handleRemoveSandboxNetworkDomain,handleAddSandboxFsPath,handleRemoveSandboxFsPath,handleImFullAccessToggle,
    handleSavePrompt,handleResetPrompt,handleAddEnvVar,handleRemoveEnvVar,handleUpdateEnvVar,handleSaveEnvVars
  };
}
