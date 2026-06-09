// [Input] System config API, chat icons, AuthContext token, dashboard design tokens.
// [Output] Render Settings AI model/theme/system-prompt/workspace/full-access/env controls.
// [Pos] settings-model-config component node in frontend/src/components/dashboard
// [Sync] 2026-06-09: add IM full-access approval toggle backed by
//                    system_config.im_full_access_enabled.
// [Sync] 2026-06-09: emit same-tab IM full-access change events so Chat UI
//                    updates without a page refresh.
import { useCallback, useEffect, useState } from 'react';
import { IconMonitor, IconMoon, IconSun } from '../chat/Icons';
import { getAuthToken } from '../../contexts/AuthContext';
import { emitImFullAccessChanged } from '../../lib/system-config-events';

const API_BASE = '/ink-and-memory';

export type ThemeMode = 'light' | 'system' | 'dark';

interface EnvVar {
  key: string;
  value: string;
}

interface SystemConfigData {
  provider?: string;
  model?: string;
  system_prompt?: string;
  workspace_enabled?: boolean;
  im_full_access_enabled?: boolean;
  theme?: ThemeMode;
  env_vars?: Record<string, string>;
}

const THEME_OPTIONS: { mode: ThemeMode; label: string; Icon: typeof IconSun }[] = [
  { mode: 'light', label: 'Light', Icon: IconSun },
  { mode: 'system', label: 'System', Icon: IconMonitor },
  { mode: 'dark', label: 'Dark', Icon: IconMoon },
];

const MODEL_OPTIONS = [
  { label: 'Auto', value: 'auto', model: 'claude-sonnet-4-20250514', provider: 'anthropic' },
  { label: 'Claude Sonnet', value: 'claude-sonnet-4-20250514', model: 'claude-sonnet-4-20250514', provider: 'anthropic' },
  { label: 'GPT-4.1', value: 'gpt-4.1-2025-04-14', model: 'gpt-4.1-2025-04-14', provider: 'openai' },
] as const;

const DEFAULT_SYSTEM_PROMPT = 'You are a concise and practical AI assistant for note-taking and writing.';
const THEME_STORAGE_KEY = 'dashboard-theme';

function resolveTheme(mode: ThemeMode, prefersDark: boolean): 'light' | 'dark' {
  if (mode === 'system') {
    return prefersDark ? 'dark' : 'light';
  }
  return mode;
}

function isThemeMode(value: string | null): value is ThemeMode {
  return value === 'light' || value === 'dark' || value === 'system';
}

export default function ModelConfigSection() {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') return 'system';
    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    return isThemeMode(savedTheme) ? savedTheme : 'system';
  });
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPT);
  const [workspaceMode, setWorkspaceMode] = useState(true);
  const [imFullAccessEnabled, setImFullAccessEnabled] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto');
  const [dirty, setDirty] = useState(false);
  const [configLoading, setConfigLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [envVars, setEnvVars] = useState<EnvVar[]>([]);
  const [envVarsDirty, setEnvVarsDirty] = useState(false);
  const [envVarsSaving, setEnvVarsSaving] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch(`${API_BASE}/api/system-config`, {
          headers: { 'Authorization': `Bearer ${getAuthToken()}` },
        });
        if (!response.ok) return;
        const payload = (await response.json()) as { data?: SystemConfigData } & SystemConfigData;
        const config = payload.data ?? payload;
        if (!active) return;
        setTheme(config.theme ?? 'system');
        setSystemPrompt(config.system_prompt ?? DEFAULT_SYSTEM_PROMPT);
        setWorkspaceMode(config.workspace_enabled ?? true);
        setImFullAccessEnabled(config.im_full_access_enabled ?? false);
        const match = MODEL_OPTIONS.find((option) => option.model === config.model);
        setSelectedModel(match?.value ?? 'auto');
        const savedEnvVars = config.env_vars ?? {};
        setEnvVars(Object.entries(savedEnvVars).map(([key, value]) => ({ key, value })));
        setDirty(false);
        setEnvVarsDirty(false);
      } catch {
        // ignore fetch errors
      } finally {
        if (active) setConfigLoading(false);
      }
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const applyTheme = () => {
      const resolvedTheme = resolveTheme(theme, media.matches);
      root.dataset.themeMode = theme;
      root.dataset.theme = resolvedTheme;
      root.style.colorScheme = resolvedTheme;
    };
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    applyTheme();
    if (theme !== 'system') return undefined;
    const handleChange = () => applyTheme();
    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', handleChange);
      return () => media.removeEventListener('change', handleChange);
    }
    media.addListener(handleChange);
    return () => media.removeListener(handleChange);
  }, [theme]);

  const updateConfig = useCallback(async (patch: Partial<SystemConfigData>) => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/system-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getAuthToken()}` },
        body: JSON.stringify(patch),
      });
      return response.ok;
    } catch {
      return false;
    } finally {
      setSaving(false);
    }
  }, []);

  const handleThemeChange = useCallback((mode: ThemeMode) => {
    setTheme(mode);
    void updateConfig({ theme: mode });
  }, [updateConfig]);

  const handleModelChange = useCallback((value: string) => {
    setSelectedModel(value);
    const option = MODEL_OPTIONS.find((entry) => entry.value === value) ?? MODEL_OPTIONS[0];
    void updateConfig({ model: option.model, provider: option.provider });
  }, [updateConfig]);

  const handleWorkspaceToggle = useCallback(() => {
    const next = !workspaceMode;
    setWorkspaceMode(next);
    void updateConfig({ workspace_enabled: next });
  }, [updateConfig, workspaceMode]);

  const handleImFullAccessToggle = useCallback(() => {
    const next = !imFullAccessEnabled;
    setImFullAccessEnabled(next);
    emitImFullAccessChanged(next);
    void (async () => {
      const saved = await updateConfig({ im_full_access_enabled: next });
      if (saved) {
        return;
      }
      setImFullAccessEnabled(!next);
      emitImFullAccessChanged(!next);
    })();
  }, [imFullAccessEnabled, updateConfig]);

  const handleSavePrompt = useCallback(() => {
    void updateConfig({ system_prompt: systemPrompt });
    setDirty(false);
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
      await fetch(`${API_BASE}/api/system-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getAuthToken()}` },
        body: JSON.stringify({ env_vars: record }),
      });
      setEnvVarsDirty(false);
    } finally {
      setEnvVarsSaving(false);
    }
  }, [envVars]);

  const fieldStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.75rem 0.85rem',
    borderRadius: '12px',
    border: '1px solid var(--color-border-paper)',
    background: 'var(--color-bg-paper)',
    color: 'var(--color-text-primary)',
    fontFamily: 'inherit',
    fontSize: '0.9rem',
    boxSizing: 'border-box',
  };

  if (configLoading) {
    return <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Loading config…</p>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Theme */}
      <div>
        <p style={{ margin: '0 0 0.75rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          外观主题 / Theme
        </p>
        <div style={{ display: 'flex', gap: '0.65rem' }}>
          {THEME_OPTIONS.map(({ mode, label, Icon }) => {
            const active = theme === mode;
            return (
              <button
                key={mode}
                type="button"
                onClick={() => handleThemeChange(mode)}
                title={label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.5rem 0.9rem',
                  borderRadius: '999px',
                  border: `1px solid ${active ? 'var(--color-border-focus)' : 'var(--color-border-paper)'}`,
                  background: active ? 'var(--color-bg-paper)' : 'transparent',
                  color: active ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                  cursor: 'pointer',
                  fontSize: '0.82rem',
                  fontWeight: active ? 600 : 400,
                  transition: 'all 0.2s ease',
                }}
              >
                <Icon style={{ width: '0.9rem', height: '0.9rem' }} />
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Model */}
      <div>
        <p style={{ margin: '0 0 0.65rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          AI 模型 / Model
        </p>
        <select
          value={selectedModel}
          onChange={(event) => handleModelChange(event.target.value)}
          style={fieldStyle}
        >
          {MODEL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </div>

      {/* System Prompt */}
      <div>
        <p style={{ margin: '0 0 0.65rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          系统提示词 / System Prompt
        </p>
        <textarea
          value={systemPrompt}
          onChange={(event) => { setSystemPrompt(event.target.value); setDirty(true); }}
          rows={5}
          style={{ ...fieldStyle, resize: 'vertical' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.65rem' }}>
          <button
            type="button"
            onClick={handleResetPrompt}
            style={{ border: 'none', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '0.82rem' }}
          >
            恢复默认
          </button>
          <button
            type="button"
            onClick={handleSavePrompt}
            disabled={saving || !dirty}
            style={{
              border: 'none',
              borderRadius: '999px',
              padding: '0.55rem 1.1rem',
              background: 'var(--color-action-link)',
              color: 'var(--color-text-on-action)',
              fontWeight: 600,
              fontSize: '0.82rem',
              cursor: saving || !dirty ? 'not-allowed' : 'pointer',
              opacity: saving || !dirty ? 0.55 : 1,
              transition: 'opacity 0.2s ease',
            }}
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>

      {/* Workspace mode */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        <div>
          <p style={{ margin: 0, fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            工作区模式 / Workspace Mode
          </p>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
            对话时启用文件侧边栏上下文。
          </p>
        </div>
        <button
          type="button"
          onClick={handleWorkspaceToggle}
          aria-pressed={workspaceMode}
          style={{
            flexShrink: 0,
            position: 'relative',
            width: '2.9rem',
            height: '1.7rem',
            border: 'none',
            borderRadius: '999px',
            background: workspaceMode ? 'var(--color-action-link)' : 'var(--color-disabled-bg)',
            cursor: 'pointer',
            transition: 'background 0.2s ease',
          }}
        >
          <span
            style={{
              position: 'absolute',
              top: '0.15rem',
              left: workspaceMode ? '1.45rem' : '0.15rem',
              width: '1.4rem',
              height: '1.4rem',
              borderRadius: '999px',
              background: 'var(--color-text-on-action)',
              transition: 'left 0.2s ease',
            }}
          />
        </button>
      </div>

      {/* IM approval mode */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        <div>
          <p style={{ margin: 0, fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            应如何批准 IM
          </p>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
            开启后，Claude-agent 的工具调用将自动获得完全访问权限。
          </p>
        </div>
        <button
          type="button"
          onClick={handleImFullAccessToggle}
          aria-pressed={imFullAccessEnabled}
          title={imFullAccessEnabled ? '完全访问已开启' : '完全访问已关闭'}
          style={{
            flexShrink: 0,
            minWidth: '6.25rem',
            height: '1.9rem',
            border: 'none',
            borderRadius: '999px',
            padding: '0 0.85rem',
            background: imFullAccessEnabled ? 'var(--color-text-primary)' : 'var(--color-disabled-bg)',
            color: imFullAccessEnabled ? 'var(--color-bg-paper)' : 'var(--color-text-secondary)',
            cursor: 'pointer',
            fontSize: '0.78rem',
            fontWeight: 600,
            transition: 'background 0.2s ease, color 0.2s ease',
            whiteSpace: 'nowrap',
          }}
        >
          完全访问
        </button>
      </div>

      {/* Environment Variables */}
      <div>
        <p style={{ margin: '0 0 0.3rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          环境变量 / Environment Variables
        </p>
        <p style={{ margin: '0 0 0.75rem', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
          为 Skills / MCP 工具配置运行时环境变量。
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {envVars.map((ev, i) => (
            <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="KEY"
                value={ev.key}
                onChange={(e) => handleUpdateEnvVar(i, 'key', e.target.value)}
                style={{ ...fieldStyle, flex: 1, fontFamily: 'monospace', fontSize: '0.82rem' }}
              />
              <input
                type="password"
                placeholder="value"
                value={ev.value}
                onChange={(e) => handleUpdateEnvVar(i, 'value', e.target.value)}
                style={{ ...fieldStyle, flex: 2, fontFamily: 'monospace', fontSize: '0.82rem' }}
              />
              <button
                type="button"
                onClick={() => handleRemoveEnvVar(i)}
                style={{
                  flexShrink: 0,
                  border: 'none',
                  background: 'transparent',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  padding: '0.25rem 0.4rem',
                  borderRadius: '6px',
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
          <button
            type="button"
            onClick={handleAddEnvVar}
            style={{
              border: '1px dashed var(--color-border-paper)',
              borderRadius: '8px',
              padding: '0.4rem 0.85rem',
              background: 'transparent',
              color: 'var(--color-text-muted)',
              fontSize: '0.82rem',
              cursor: 'pointer',
            }}
          >
            + 添加变量
          </button>
          <button
            type="button"
            disabled={!envVarsDirty || envVarsSaving}
            onClick={handleSaveEnvVars}
            style={{
              border: 'none',
              borderRadius: '999px',
              padding: '0.4rem 1rem',
              background: 'var(--color-action-link)',
              color: 'var(--color-text-on-action)',
              fontWeight: 600,
              fontSize: '0.82rem',
              cursor: !envVarsDirty || envVarsSaving ? 'not-allowed' : 'pointer',
              opacity: !envVarsDirty || envVarsSaving ? 0.55 : 1,
              transition: 'opacity 0.2s ease',
            }}
          >
            {envVarsSaving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
