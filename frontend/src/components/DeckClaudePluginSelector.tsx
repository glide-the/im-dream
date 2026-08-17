// [Input] claudePluginAdminApi installations + Deck refs endpoints.
// [Output] Deck editor selector for Claude Code plugins: only ready, digest-verified,
//          CLI-compatible installations are selectable; saves references (never paths).
// [Pos] Mounted inside DeckEditorModal between Deck metadata and Agent maintenance.
// [Sync] 2026-08-16: restore the pre-01a00576 maintenance selector without adding an orchestration editor.
// [Sync] 2026-08-16: notify the editor after a durable plugin-ref save so the aggregate draft state refreshes.

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
  onSaved?: () => Promise<void>;
}

export default function DeckClaudePluginSelector({ deckId, disabled, onSaved }: DeckClaudePluginSelectorProps) {
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
      const [installResult, refs] = await Promise.all([
        listClaudePluginInstallations(),
        listDeckClaudePluginRefs(deckId),
      ]);
      setInstallations(installResult.installations);
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
      await onSaved?.();
      setSaved(true);
    } catch (err) {
      setError(err instanceof ClaudePluginApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setSaving(false);
    }
  }, [deckId, onSaved, selected]);

  return (
    <section aria-label="Deck Claude 插件" className="deck-plugin-selector">
      <div className="deck-plugin-selector__eyebrow">共享安装 · digest 固定</div>
      <div className="deck-plugin-selector__description">
        只可选择已真实安装、状态 ready、digest 校验通过且与当前 Claude Code 兼容的插件。
        发起此 Deck 的对话时，插件包将复制到对话工作空间并通过 --plugin-dir 加载。
      </div>
      {loading ? (
        <div className="deck-plugin-selector__state">加载中…</div>
      ) : readyInstallations.length === 0 ? (
        <div className="deck-plugin-selector__state">
          暂无 ready 状态的插件。请先在 Settings → Claude 插件中安装（例如 superpowers@claude-plugins-official）。
        </div>
      ) : (
        <div className="deck-plugin-selector__list">
          {readyInstallations.map((installation) => {
            const checked = selected.get(installation.id) === true;
            return (
              <label
                className={`deck-plugin-selector__item${checked ? ' is-selected' : ''}`}
                key={installation.id}
              >
                <input
                  checked={checked}
                  disabled={disabled}
                  onChange={() => toggle(installation.id)}
                  type="checkbox"
                />
                <span className="deck-plugin-selector__copy">
                  <span className="deck-plugin-selector__title">
                    <strong>{installation.package_name}</strong>
                    <span className="deck-plugin-selector__version">
                      v{installation.resolved_version}
                    </span>
                  </span>
                  <code>
                    {installation.requested_package_spec} · {shortDigest(installation.artifact_digest)}
                  </code>
                </span>
              </label>
            );
          })}
        </div>
      )}
      {error ? (
        <div className="deck-plugin-selector__error" role="alert">
          {error}
        </div>
      ) : null}
      {!disabled && readyInstallations.length > 0 ? (
        <div className="deck-plugin-selector__actions">
          <button
            className="deck-primary-button"
            disabled={saving}
            onClick={() => void handleSave()}
            type="button"
          >
            {saving ? '保存中…' : '保存插件选择'}
          </button>
          {saved ? (
            <span className="deck-plugin-selector__saved" role="status">已保存 ✓</span>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
