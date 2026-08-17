// [Input] Deck content commits plus current runtime binding/options/history.
// [Output] Default-collapsed content-version timeline with secondary runtime configuration.
// [Pos] Right-side version panel inside DeckEditorModal.
// [Sync] 2026-08-16: make immutable Deck content vN the primary history.

import { useEffect, useMemo, useState } from 'react';
import { useDeckPluginBinding } from '../../hooks/useDeckPluginBinding';
import { useDeckPluginBindingHistory } from '../../hooks/useDeckPluginBindingHistory';
import { useDeckPluginOptions } from '../../hooks/useDeckPluginOptions';
import { useDeckContentVersions } from '../../hooks/useDeckContentVersions';
import DeckPluginVersionPicker from './DeckPluginVersionPicker';

interface Props {
  deckId: string;
  isSystem: boolean;
  onClose: () => void;
  onVersionChanged: () => Promise<void>;
}

export default function DeckVersionPanel({ deckId, isSystem, onClose, onVersionChanged }: Props) {
  const binding = useDeckPluginBinding(deckId);
  const options = useDeckPluginOptions(deckId);
  const history = useDeckPluginBindingHistory(deckId);
  const content = useDeckContentVersions(deckId);
  const [pickerOpen, setPickerOpen] = useState(false);
  useEffect(() => {
    void content.refresh(true);
    // The content hook already owns Deck-id invalidation; this effect requests
    // the heavier immutable history only while the folded panel is mounted.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deckId]);
  const currentOption = useMemo(() => {
    const current = binding.state?.binding;
    return current
      ? options.options.find((option) => (
        option.deck_plugin_id === current.deck_plugin_id
        && option.deck_plugin_version === current.deck_plugin_version
      )) ?? null
      : null;
  }, [binding.state?.binding, options.options]);

  const refreshAll = async () => {
    await Promise.all([content.refresh(true), binding.refresh(), options.refresh(), history.refresh(), onVersionChanged()]);
  };

  return (
    <aside aria-label="版本记录" className="deck-version-panel">
      <header className="deck-version-panel__header">
        <div>
          <h2>版本记录</h2>
          <p>Deck 内容版本 · 默认折叠</p>
        </div>
        <button aria-label="收起版本记录" className="deck-icon-button" onClick={onClose} type="button">›</button>
      </header>

      {(content.loading || binding.loading || history.loading) && <div className="deck-version-panel__status" role="status">正在读取版本记录…</div>}
      {(content.error || binding.error || history.error) && (
        <div className="deck-version-panel__status is-error" role="alert">
          {content.error || binding.error || history.error}
          <button onClick={() => void refreshAll()} type="button">重试</button>
        </div>
      )}

      {!content.loading && !binding.loading && !history.loading && (
        <>
          <section className="deck-version-current">
            <span className="deck-version-current__eyebrow">当前 Deck 内容</span>
            {content.state?.latest_version ? (
              <>
                <strong>v{content.state.latest_version}</strong>
                <span>{content.state.dirty ? `存在未提交草稿 · r${content.state.draft_revision}` : '已与当前草稿一致'}</span>
              </>
            ) : (
              <>
                <strong>尚未提交</strong>
                <span>完成表单编辑后，在顶部提交第一个 v1。</span>
              </>
            )}
          </section>

          <section className="deck-version-timeline" aria-label="Deck 内容版本历史">
            <h3>内容版本</h3>
            {!content.history || content.history.versions.length === 0 ? (
              <p className="deck-empty-copy">暂无已提交内容版本。</p>
            ) : content.history.versions.map((entry, index) => (
              <article className={`deck-version-entry${index === 0 ? ' is-active' : ''}`} key={entry.version}>
                <span className="deck-version-entry__dot" aria-hidden="true" />
                <div>
                  <strong>v{entry.version}{index === 0 ? ' · 当前' : ''}</strong>
                  <span>{entry.description || '未填写版本说明'} · {new Date(entry.created_at).toLocaleString()}</span>
                </div>
              </article>
            ))}
          </section>

          <section className="deck-version-runtime">
            <div>
              <span className="deck-version-current__eyebrow">运行插件版本（随内容快照记录）</span>
              <strong>{binding.state?.binding ? `v${binding.state.binding.deck_plugin_version}` : 'Chat 配置'}</strong>
              <span>{binding.state?.binding ? (currentOption?.display_name ?? binding.state.binding.deck_plugin_id) : '没有活动的 Dream 运行插件'}</span>
            </div>
            {!isSystem && <button className="deck-secondary-button" onClick={() => setPickerOpen(true)} type="button">选择运行版本</button>}
          </section>

          <details className="deck-version-runtime-history">
            <summary>运行配置记录 {history.currentRevision > 0 ? `· r${history.currentRevision}` : ''}</summary>
            <div className="deck-version-timeline">
              {history.history.length === 0 ? <p className="deck-empty-copy">暂无运行配置记录。</p> : history.history.map((entry) => (
                <article className={`deck-version-entry${entry.status === 'active' ? ' is-active' : ''}`} key={entry.deck_plugin_binding_id}>
                  <span className="deck-version-entry__dot" aria-hidden="true" />
                  <div><strong>r{entry.binding_revision} · v{entry.deck_plugin_version}</strong><span>{entry.status === 'active' ? '当前' : '历史'}</span></div>
                </article>
              ))}
            </div>
          </details>
        </>
      )}

      {binding.successMessage && <div className="deck-version-panel__status is-success">{binding.successMessage}</div>}
      {binding.conflict && (
        <div className="deck-version-panel__status is-warning" role="alert">
          {binding.conflict.message}
          {binding.conflict.currentRevision !== null && ` 当前为 r${binding.conflict.currentRevision}。`}
        </div>
      )}

      {pickerOpen && (
        <DeckPluginVersionPicker
          bindingState={binding.state}
          conflict={binding.conflict}
          error={options.error || binding.error}
          loading={options.loading || binding.loading}
          onClose={() => setPickerOpen(false)}
          onConfirm={async (option) => {
            const saved = await binding.save(option, options.refresh);
            if (saved) await Promise.all([content.refresh(true), history.refresh(), onVersionChanged()]);
            return saved;
          }}
          onRefresh={() => void refreshAll()}
          options={options.options}
          saving={binding.saving}
        />
      )}
    </aside>
  );
}
