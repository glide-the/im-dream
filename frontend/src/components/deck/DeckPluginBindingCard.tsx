// [Input] Current Deck Plugin binding, matching option metadata, and current Workflow Run reference.
// [Output] Current/empty Deck workflow plugin card with exact release and capability summary.
// [Pos] Primary Deck Editor Plugin binding summary component.

import type { DeckPluginBindingState, DeckPluginOption } from '../../api/deckPluginApi';

interface Props {
  state: DeckPluginBindingState | null;
  currentOption: DeckPluginOption | null;
  loading: boolean;
  disabled?: boolean;
  currentWorkflowRunId?: string | null;
  onBrowse: () => void;
}

function SummaryPills({ values }: { values: string[] }) {
  const visible = values.slice(0, 3);
  const remaining = values.length - visible.length;
  if (values.length === 0) {
    return <span style={{ color: 'var(--color-text-muted)' }}>无 capability 摘要</span>;
  }
  return (
    <span style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap' }}>
      {visible.map(value => (
        <code
          key={value}
          style={{
            padding: '2px 6px',
            borderRadius: 5,
            background: 'var(--color-code-inline-bg)',
            color: 'var(--color-code-text)',
            fontSize: 11,
          }}
        >
          {value}
        </code>
      ))}
      {remaining > 0 && <span>+{remaining} 更多</span>}
    </span>
  );
}

export default function DeckPluginBindingCard({
  state,
  currentOption,
  loading,
  disabled = false,
  currentWorkflowRunId,
  onBrowse,
}: Props) {
  const binding = state?.binding ?? null;
  const summary = currentOption ?? binding?.selection_validation_summary ?? null;

  return (
    <div
      style={{
        border: '1px solid var(--color-border-neutral)',
        borderRadius: 10,
        background: 'var(--color-bg-paper)',
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 9,
      }}
    >
      {binding ? (
        <>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                {currentOption?.display_name ?? binding.deck_plugin_id}
                {' '}
                <span style={{ color: 'var(--color-action-link)' }}>v{binding.deck_plugin_version}</span>
              </div>
              <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginTop: 3 }}>
                {summary?.release_status ?? 'release unknown'} · revision {binding.binding_revision}
              </div>
            </div>
            <button
              type="button"
              onClick={onBrowse}
              disabled={disabled || loading}
              style={{
                border: '1px solid var(--color-action-link)',
                borderRadius: 7,
                background: 'transparent',
                color: 'var(--color-action-link)',
                padding: '7px 10px',
                fontSize: 12,
                cursor: disabled || loading ? 'not-allowed' : 'pointer',
                opacity: disabled || loading ? 0.55 : 1,
                flexShrink: 0,
              }}
            >
              更换版本
            </button>
          </div>
          <div style={{ color: 'var(--color-text-body)', fontSize: 12 }}>
            能力：<SummaryPills values={summary?.capability_summary ?? []} />
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', color: 'var(--color-text-secondary)', fontSize: 11 }}>
            <span>Installation：{summary?.installation_status ?? 'unknown'}</span>
            <span>Runtime：{summary?.runtime_readiness ?? 'unknown'}</span>
            <span>Compatibility：{summary?.compatibility ?? 'unknown'}</span>
          </div>
        </>
      ) : (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <div>
            <div style={{ color: 'var(--color-text-primary)', fontSize: 13, fontWeight: 600 }}>
              {loading ? '正在读取当前选择…' : '未选择工作流插件。'}
            </div>
            {!loading && (
              <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, marginTop: 4 }}>
                选择插件以启用剧本创作工作流。
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onBrowse}
            disabled={disabled || loading}
            style={{
              border: 'none',
              borderRadius: 7,
              background: 'var(--color-action-link)',
              color: 'var(--color-text-on-action)',
              padding: '8px 11px',
              fontSize: 12,
              cursor: disabled || loading ? 'not-allowed' : 'pointer',
              opacity: disabled || loading ? 0.55 : 1,
              flexShrink: 0,
            }}
          >
            浏览可用插件
          </button>
        </div>
      )}
      {currentWorkflowRunId && (
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 11 }}>
          当前运行使用中：<code>{currentWorkflowRunId}</code>
        </div>
      )}
    </div>
  );
}
