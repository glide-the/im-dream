// [Input] claudePluginAdminApi installations + Deck refs endpoints.
// [Output] Deck editor selector for Claude Code plugins: only ready, digest-verified,
//          CLI-compatible installations are selectable; saves references (never paths).
// [Pos] Mounted inside DeckEditorModal below the workflow plugin section.

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ClaudePluginApiError,
  listClaudePluginInstallations,
  listDeckClaudePluginRefs,
  putDeckClaudePluginRefs,
  shortDigest,
  type ClaudePluginInstallation,
} from '../api/claudePluginAdminApi';

interface DeckClaudePluginSelectorProps {
  deckId: string;
  disabled?: boolean;
}

export default function DeckClaudePluginSelector({ deckId, disabled }: DeckClaudePluginSelectorProps) {
  const [installations, setInstallations] = useState<ClaudePluginInstallation[]>([]);
  const [selected, setSelected] = useState<Map<string, boolean>>(new Map());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const readyInstallations = useMemo(
    () => installations.filter((item) => item.status === 'ready'),
    [installations],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [installs, refs] = await Promise.all([
        listClaudePluginInstallations(),
        listDeckClaudePluginRefs(deckId),
      ]);
      setInstallations(installs);
      const next = new Map<string, boolean>();
      refs.forEach((ref) => next.set(ref.plugin_installation_id, ref.enabled === 1));
      setSelected(next);
    } catch (err) {
      setError(err instanceof ClaudePluginApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setLoading(false);
    }
  }, [deckId]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = useCallback((installationId: string) => {
    setSaved(false);
    setSelected((current) => {
      const next = new Map(current);
      if (next.get(installationId)) {
        next.delete(installationId);
      } else {
        next.set(installationId, true);
      }
      return next;
    });
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const refs = [...selected.entries()]
        .filter(([, enabled]) => enabled)
        .map(([installationId], index) => ({
          plugin_installation_id: installationId,
          enabled: true,
          order_index: index,
        }));
      await putDeckClaudePluginRefs(deckId, refs);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ClaudePluginApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setSaving(false);
    }
  }, [deckId, selected]);

  return (
    <section
      aria-label="Deck Claude 插件"
      style={{
        background: 'var(--color-bg-surface-solid)',
        border: '2px solid var(--color-border-neutral)',
        borderRadius: 12,
        padding: 14,
        boxShadow: '0 2px 6px var(--color-shadow-soft)',
        display: 'flex',
        flexDirection: 'column',
        gap: 9,
        flexShrink: 0,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-text-secondary)', letterSpacing: 0.5, textTransform: 'uppercase' }}>
        🧩 Claude 插件（共享安装 · digest 固定）
      </div>
      <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
        只可选择已真实安装、状态 ready、digest 校验通过且与当前 Claude Code 兼容的插件。
        发起此 Deck 的对话时，插件包将复制到对话工作空间并通过 --plugin-dir 加载。
      </div>
      {loading ? (
        <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>加载中…</div>
      ) : readyInstallations.length === 0 ? (
        <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
          暂无 ready 状态的插件。请先在 Settings → Claude 插件中安装（例如 superpowers@claude-plugins-official）。
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 8 }}>
          {readyInstallations.map((installation) => {
            const checked = selected.get(installation.id) === true;
            return (
              <label
                key={installation.id}
                style={{
                  display: 'flex', gap: 10, alignItems: 'flex-start',
                  padding: '9px 11px', borderRadius: 8, cursor: disabled ? 'not-allowed' : 'pointer',
                  border: `1px solid ${checked ? 'var(--color-text-primary)' : 'var(--color-border-paper)'}`,
                  background: checked ? 'var(--color-bg-hover)' : 'var(--color-bg-surface)',
                  opacity: disabled ? 0.6 : 1,
                }}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={disabled}
                  onChange={() => toggle(installation.id)}
                  style={{ marginTop: 3 }}
                />
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: 13 }}>{installation.package_name}</strong>
                    <span style={{
                      borderRadius: 999, padding: '1px 7px', fontSize: 10, fontWeight: 700,
                      background: 'var(--color-bg-hover)', color: 'var(--color-text-secondary)',
                    }}>
                      v{installation.resolved_version}
                    </span>
                  </span>
                  <code style={{ display: 'block', marginTop: 3, fontSize: 10, color: 'var(--color-text-muted)', overflowWrap: 'anywhere' }}>
                    {installation.requested_package_spec} · {shortDigest(installation.artifact_digest)}
                  </code>
                </span>
              </label>
            );
          })}
        </div>
      )}
      {error ? (
        <div style={{
          padding: '8px 10px', borderRadius: 7, fontSize: 12,
          background: 'color-mix(in srgb, #c44848 10%, var(--color-bg-surface))', color: '#a03737',
        }}>
          {error}
        </div>
      ) : null}
      {!disabled && readyInstallations.length > 0 ? (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            type="button"
            disabled={saving}
            onClick={() => void handleSave()}
            style={{
              border: '1px solid var(--color-text-primary)', borderRadius: 7,
              background: 'var(--color-text-primary)', color: 'var(--color-text-on-action)',
              padding: '6px 12px', font: 'inherit', fontSize: 12, fontWeight: 600,
              cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? '保存中…' : '保存插件选择'}
          </button>
          {saved ? (
            <span style={{ fontSize: 12, color: '#24784c' }}>已保存 ✓</span>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
