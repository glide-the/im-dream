// [Input] Server version options, current binding, and explicit save callback.
// [Output] Focused exact-version confirmation dialog with capability diff.
// [Pos] Deck runtime-version picker.
// [Sync] 2026-08-16: restore CozeLoop-inspired version choice without a detailed workbench.

import { useMemo, useState } from 'react';
import type { DeckPluginBindingState, DeckPluginOption } from '../../api/deckPluginApi';
import type { DeckPluginBindingConflict } from '../../hooks/useDeckPluginBinding';
import DeckPluginVersionCard from './DeckPluginVersionCard';

interface Props {
  options: DeckPluginOption[];
  bindingState: DeckPluginBindingState | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  conflict: DeckPluginBindingConflict | null;
  onRefresh: () => void;
  onConfirm: (option: DeckPluginOption) => Promise<boolean>;
  onClose: () => void;
}

function optionKey(option: Pick<DeckPluginOption, 'deck_plugin_id' | 'deck_plugin_version'>) {
  return `${option.deck_plugin_id}@${option.deck_plugin_version}`;
}

export default function DeckPluginVersionPicker({
  options,
  bindingState,
  loading,
  saving,
  error,
  conflict,
  onRefresh,
  onConfirm,
  onClose,
}: Props) {
  const currentKey = bindingState?.binding ? optionKey(bindingState.binding) : null;
  const selectable = useMemo(() => options.filter((option) => option.selectable), [options]);
  const unavailable = useMemo(() => options.filter((option) => !option.selectable), [options]);
  const initial = selectable.find((option) => optionKey(option) === currentKey) ?? selectable[0] ?? null;
  const [selectedKey, setSelectedKey] = useState(initial ? optionKey(initial) : null);
  const [showUnavailable, setShowUnavailable] = useState(false);
  const selected = selectable.find((option) => optionKey(option) === selectedKey) ?? null;
  const current = options.find((option) => optionKey(option) === currentKey) ?? null;
  const currentCapabilities = new Set(current?.capability_summary ?? []);
  const nextCapabilities = new Set(selected?.capability_summary ?? []);
  const added = selected?.capability_summary.filter((value) => !currentCapabilities.has(value)) ?? [];
  const removed = current?.capability_summary.filter((value) => !nextCapabilities.has(value)) ?? [];

  return (
    <div className="deck-version-picker-backdrop" onClick={onClose} role="presentation">
      <section
        aria-labelledby="deck-version-picker-title"
        aria-modal="true"
        className="deck-version-picker"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <header className="deck-version-picker__header">
          <div>
            <h2 id="deck-version-picker-title">选择运行版本</h2>
            <p>选择精确版本；服务端会重新校验权限、兼容性和并发 revision。</p>
          </div>
          <button aria-label="关闭版本选择" className="deck-icon-button" onClick={onClose} type="button">×</button>
        </header>

        {(loading || error || conflict) && (
          <div className="deck-version-picker__notice" aria-live="polite">
            {loading && <span>正在刷新版本…</span>}
            {error && <span role="alert">{error} <button onClick={onRefresh} type="button">重试</button></span>}
            {conflict && <span role="alert">{conflict.message}</span>}
          </div>
        )}

        <div className="deck-version-picker__list" role="radiogroup" aria-label="可用版本">
          {selectable.map((option) => (
            <DeckPluginVersionCard
              current={optionKey(option) === currentKey}
              key={optionKey(option)}
              onSelect={(candidate) => setSelectedKey(optionKey(candidate))}
              option={option}
              selected={optionKey(option) === selectedKey}
            />
          ))}
          {!loading && selectable.length === 0 && <p className="deck-empty-copy">当前没有可选择的版本。</p>}
        </div>

        {unavailable.length > 0 && (
          <section className="deck-version-picker__other">
            <button aria-expanded={showUnavailable} onClick={() => setShowUnavailable((value) => !value)} type="button">
              {showUnavailable ? '收起不可用版本' : `查看不可用版本（${unavailable.length}）`}
            </button>
            {showUnavailable && unavailable.map((option) => (
              <DeckPluginVersionCard
                current={optionKey(option) === currentKey}
                key={optionKey(option)}
                onSelect={() => undefined}
                option={option}
                selected={false}
              />
            ))}
          </section>
        )}

        {selected && (
          <div className="deck-version-picker__diff">
            <strong>{current ? `v${current.deck_plugin_version}` : '未绑定'} → v{selected.deck_plugin_version}</strong>
            <span>新增能力 {added.length} 项 · 移除能力 {removed.length} 项</span>
            <span>只影响下一次运行；历史和当前运行保持原版本。</span>
          </div>
        )}

        <footer className="deck-version-picker__footer">
          <button className="deck-secondary-button" onClick={onClose} type="button">取消</button>
          <button
            className="deck-primary-button"
            disabled={!selected || saving || optionKey(selected) === currentKey}
            onClick={async () => {
              if (selected && await onConfirm(selected)) onClose();
            }}
            type="button"
          >
            {saving ? '保存中…' : selected && optionKey(selected) === currentKey ? '已是当前版本' : '确认切换'}
          </button>
        </footer>
      </section>
    </div>
  );
}
