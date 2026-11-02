// [Sync] 2026-10-29: share the original reference-selection lifecycle with Native; Web DOM and save behavior remain.
// [Input] claudePluginAdminApi installations + Deck refs endpoints.
// [Output] Deck editor selector for Claude Code plugins: only ready, digest-verified,
//          CLI-compatible installations are selectable; saves references (never paths).
// [Pos] Mounted inside DeckEditorModal between Deck metadata and Agent maintenance.
// [Sync] 2026-10-09: localize the 思维模式/Deck plugin section accessible name.
// [Sync] 2026-08-16: restore the pre-01a00576 maintenance selector without adding an orchestration editor.
// [Sync] 2026-08-16: notify the editor after a durable plugin-ref save so the aggregate draft state refreshes.

import {useTranslation} from 'react-i18next';
import {shortDigest} from '../api/claudePluginAdminApi';
import {useDeckClaudePluginRefs} from '../hooks/useDeckClaudePluginRefs';

interface DeckClaudePluginSelectorProps {
  deckId: string;
  disabled?: boolean;
  onSaved?: () => Promise<void>;
}

export default function DeckClaudePluginSelector({ deckId, disabled, onSaved }: DeckClaudePluginSelectorProps) {
  const { t } = useTranslation();
  const {readyInstallations,selected,loading,saving,error,saved,toggle,handleSave}=useDeckClaudePluginRefs(deckId,onSaved);

  return (
    <section aria-label={t('deck.details.pluginsLabel')} className="deck-plugin-selector">
      <div className="deck-plugin-selector__eyebrow">{t('deck.details.pluginsInstalledLabel')}</div>
      <div className="deck-plugin-selector__description">
        {t('deck.details.pluginsDescription')}
        {t('deck.details.pluginUsageHint')}
      </div>
      {loading ? (
        <div className="deck-plugin-selector__state">加载中…</div>
      ) : readyInstallations.length === 0 ? (
        <div className="deck-plugin-selector__state">
          {t('deck.details.pluginsEmpty')}
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
