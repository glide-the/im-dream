// [Input] Server options, current binding, save state, and explicit user confirmation callback.
// [Output] Exact-version modal with recommended/other groups, diff summary, and no silent conflict retry.
// [Pos] Deck Editor Plugin version selection modal.

import { useMemo, useState } from 'react';
import type {
  DeckPluginBindingState,
  DeckPluginOption,
} from '../../api/deckPluginApi';
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

function optionKey(option: Pick<DeckPluginOption, 'deck_plugin_id' | 'deck_plugin_version'>): string {
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
  const recommended = useMemo(() => options.filter(option => option.selectable), [options]);
  const other = useMemo(() => options.filter(option => !option.selectable), [options]);
  const initialSelection = recommended.find(option => optionKey(option) === currentKey) ?? recommended[0] ?? null;
  const [selectedKey, setSelectedKey] = useState<string | null>(initialSelection ? optionKey(initialSelection) : null);
  const [showOther, setShowOther] = useState(false);
  const selected = recommended.find(option => optionKey(option) === selectedKey) ?? recommended[0] ?? null;
  const currentOption = options.find(option => optionKey(option) === currentKey) ?? null;
  const isCurrentSelection = selected ? optionKey(selected) === currentKey : false;

  const capabilityDiff = useMemo(() => {
    if (!selected) return { added: [], removed: [] };
    const before = new Set(currentOption?.capability_summary ?? []);
    const after = new Set(selected.capability_summary);
    return {
      added: selected.capability_summary.filter(capability => !before.has(capability)),
      removed: [...before].filter(capability => !after.has(capability)),
    };
  }, [currentOption, selected]);

  return (
    <div
      role="presentation"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10001,
        background: 'var(--color-bg-overlay)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="deck-plugin-picker-title"
        onClick={event => event.stopPropagation()}
        style={{
          width: 'min(760px, 100%)',
          maxHeight: '84vh',
          overflowY: 'auto',
          border: '2px solid var(--color-border-paper)',
          borderRadius: 14,
          background: 'var(--color-bg-surface-solid)',
          boxShadow: '0 16px 36px var(--color-shadow-medium)',
          padding: 18,
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
          <div>
            <div id="deck-plugin-picker-title" style={{ fontSize: 17, fontWeight: 700, color: 'var(--color-text-primary)' }}>
              选择 Deck 工作流插件版本
            </div>
            <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 4 }}>
              选择精确 release；服务端负责权限、兼容性与 runtime readiness 裁决。
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ border: 'none', background: 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', fontSize: 18 }}
            aria-label="关闭版本选择"
          >
            ×
          </button>
        </div>

        {loading && <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>正在刷新版本列表…</div>}
        {error && (
          <div role="alert" style={{ color: 'var(--color-state-error)', fontSize: 12 }}>
            {error}{' '}
            <button type="button" onClick={onRefresh} style={{ color: 'var(--color-action-link)', border: 'none', background: 'transparent', cursor: 'pointer' }}>
              重试
            </button>
          </div>
        )}
        {conflict && (
          <div role="alert" style={{ color: 'var(--color-state-warning)', fontSize: 12, lineHeight: 1.45 }}>
            {conflict.message}{' '}
            {conflict.selectionStillAvailable ? '原选择仍可用，请再次确认。' : '原选择已不可用，请改选其他版本。'}
          </div>
        )}

        <section aria-label="推荐兼容版本" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ color: 'var(--color-text-primary)', fontSize: 12, fontWeight: 700 }}>推荐兼容版本</div>
          {recommended.length === 0 && !loading && (
            <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>
              当前没有服务端判定为可选择的版本。请查看其他版本的原因与恢复入口。
            </div>
          )}
          <div role="radiogroup" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recommended.map(option => (
              <DeckPluginVersionCard
                key={optionKey(option)}
                option={option}
                current={optionKey(option) === currentKey}
                selected={selected ? optionKey(option) === optionKey(selected) : false}
                onSelect={candidate => setSelectedKey(optionKey(candidate))}
              />
            ))}
          </div>
        </section>

        {other.length > 0 && (
          <section aria-label="其他版本" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button
              type="button"
              onClick={() => setShowOther(value => !value)}
              aria-expanded={showOther}
              style={{ alignSelf: 'flex-start', border: 'none', background: 'transparent', color: 'var(--color-action-link)', cursor: 'pointer', padding: 0, fontSize: 12 }}
            >
              {showOther ? '收起其他版本' : `查看其他版本（${other.length}）`}
            </button>
            {showOther && other.map(option => (
              <DeckPluginVersionCard
                key={optionKey(option)}
                option={option}
                current={optionKey(option) === currentKey}
                selected={false}
                onSelect={() => undefined}
              />
            ))}
          </section>
        )}

        {selected && (
          <div
            style={{
              borderRadius: 9,
              background: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-paper)',
              padding: 10,
              color: 'var(--color-text-body)',
              fontSize: 11,
              lineHeight: 1.5,
            }}
          >
            <strong>版本差异：</strong>{' '}
            {currentOption
              ? `${currentOption.deck_plugin_version} → ${selected.deck_plugin_version}`
              : `未绑定 → ${selected.deck_plugin_version}`}
            {' · '}
            新增能力 {capabilityDiff.added.length} 项，移除能力 {capabilityDiff.removed.length} 项。
            能力与权限是否可用仍以服务端保存校验为准。
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button
            type="button"
            onClick={onClose}
            style={{ border: '1px solid var(--color-border-neutral)', borderRadius: 7, background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '8px 12px', cursor: 'pointer' }}
          >
            取消
          </button>
          <button
            type="button"
            disabled={!selected || saving || isCurrentSelection}
            onClick={async () => {
              if (!selected) return;
              const saved = await onConfirm(selected);
              if (saved) onClose();
            }}
            style={{
              border: 'none',
              borderRadius: 7,
              background: 'var(--color-action-link)',
              color: 'var(--color-text-on-action)',
              padding: '8px 13px',
              cursor: !selected || saving || isCurrentSelection ? 'not-allowed' : 'pointer',
              opacity: !selected || saving || isCurrentSelection ? 0.55 : 1,
            }}
          >
            {saving ? '保存中…' : isCurrentSelection ? '已是当前版本' : '确认选择'}
          </button>
        </div>
      </div>
    </div>
  );
}
