import { useEffect, useState } from 'react';
import { IconMonitor, IconMoon, IconSun } from '../chat/Icons';

export type ThemeMode = 'light' | 'system' | 'dark';

const THEME_OPTIONS: { mode: ThemeMode; label: string; Icon: typeof IconSun }[] = [
  { mode: 'light', label: 'Light', Icon: IconSun },
  { mode: 'system', label: 'System', Icon: IconMonitor },
  { mode: 'dark', label: 'Dark', Icon: IconMoon },
];

interface SidebarProps {
  open: boolean;
  desktopCollapsed?: boolean;
  onClose: () => void;
  theme?: ThemeMode;
  onThemeChange?: (mode: ThemeMode) => void;
  systemPrompt?: string;
  onSystemPromptChange?: (value: string) => void;
  onSavePrompt?: (value: string) => void;
  onResetPrompt?: () => void;
  workspaceMode?: boolean;
  onWorkspaceToggle?: () => void;
  selectedModel?: string;
  onModelChange?: (value: string) => void;
  title?: string;
}

const MODELS = [
  { label: 'Auto', value: 'auto' },
  { label: 'Claude Sonnet', value: 'claude-sonnet' },
  { label: 'GPT-4.1', value: 'gpt-4.1' },
];

export default function Sidebar({ open, desktopCollapsed = false, onClose, theme = 'system', onThemeChange, systemPrompt = 'You are a concise and reflective writing assistant.', onSystemPromptChange, onSavePrompt, onResetPrompt, workspaceMode = true, onWorkspaceToggle, selectedModel = 'auto', onModelChange, title = 'Chat settings' }: SidebarProps) {
  const [draftPrompt, setDraftPrompt] = useState(systemPrompt);

  useEffect(() => {
    setDraftPrompt(systemPrompt);
  }, [systemPrompt]);

  return (
    <>
      {open ? <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 20, background: 'var(--color-bg-overlay)' }} /> : null}
      <aside style={{ position: 'relative', zIndex: 21, width: desktopCollapsed ? 0 : '18rem', minWidth: desktopCollapsed ? 0 : '18rem', overflow: 'hidden', borderRight: desktopCollapsed ? 'none' : '1px solid var(--color-border-paper)', background: 'var(--color-bg-app)', transition: 'width 0.25s ease, min-width 0.25s ease', display: open || !desktopCollapsed ? 'block' : 'none' }}>
        <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.25rem', height: '100%', boxSizing: 'border-box' }}>
          <div>
            <p style={{ margin: 0, fontSize: '0.72rem', letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>Workspace</p>
            <h2 style={{ margin: '0.35rem 0 0', fontSize: '1.15rem', color: 'var(--color-text-primary)' }}>{title}</h2>
          </div>

          <section>
            <p style={{ margin: 0, fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>Theme</p>
            <div style={{ display: 'flex', gap: '0.65rem', marginTop: '0.75rem' }}>
              {THEME_OPTIONS.map(({ mode, label, Icon }) => {
                const active = theme === mode;
                return <button key={mode} type="button" onClick={() => onThemeChange?.(mode)} title={label} style={{ width: '2.2rem', height: '2.2rem', borderRadius: '999px', border: `1px solid ${active ? 'var(--color-border-focus)' : 'var(--color-border-paper)'}`, background: active ? 'var(--color-bg-paper)' : 'transparent', color: active ? 'var(--color-text-primary)' : 'var(--color-text-muted)', cursor: 'pointer' }}><Icon style={{ width: '1rem', height: '1rem' }} /></button>;
              })}
            </div>
          </section>

          <section>
            <p style={{ margin: 0, fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>Model</p>
            <select value={selectedModel} onChange={(event) => onModelChange?.(event.target.value)} style={{ width: '100%', marginTop: '0.65rem', padding: '0.75rem 0.85rem', borderRadius: '12px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)' }}>
              {MODELS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </section>

          <section>
            <p style={{ margin: 0, fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>System prompt</p>
            <textarea value={draftPrompt} onChange={(event) => { setDraftPrompt(event.target.value); onSystemPromptChange?.(event.target.value); }} rows={5} style={{ width: '100%', marginTop: '0.65rem', padding: '0.75rem 0.85rem', borderRadius: '12px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', resize: 'vertical', boxSizing: 'border-box' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.65rem' }}>
              <button type="button" onClick={() => { setDraftPrompt('You are a concise and reflective writing assistant.'); onResetPrompt?.(); }} style={{ border: 'none', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer' }}>Reset</button>
              <button type="button" onClick={() => onSavePrompt?.(draftPrompt)} style={{ border: 'none', borderRadius: '999px', padding: '0.55rem 0.9rem', background: 'var(--color-action-link)', color: '#fff', fontWeight: 600, cursor: 'pointer' }}>Save</button>
            </div>
          </section>

          <section style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ margin: 0, fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>Workspace mode</p>
              <p style={{ margin: '0.2rem 0 0', fontSize: '0.74rem', color: 'var(--color-text-muted)' }}>Enable file-side context while chatting.</p>
            </div>
            <button type="button" onClick={onWorkspaceToggle} aria-pressed={workspaceMode} style={{ position: 'relative', width: '2.9rem', height: '1.7rem', border: 'none', borderRadius: '999px', background: workspaceMode ? 'var(--color-action-link)' : 'var(--color-disabled-bg)', cursor: 'pointer' }}>
              <span style={{ position: 'absolute', top: '0.15rem', left: workspaceMode ? '1.45rem' : '0.15rem', width: '1.4rem', height: '1.4rem', borderRadius: '999px', background: '#fff', transition: 'left 0.2s ease' }} />
            </button>
          </section>
        </div>
      </aside>
    </>
  );
}
