// [Input] One server-adjudicated Deck Plugin option and current/selected identity.
// [Output] Exact-version radio card with status, safe reason code, and recovery owner/action.
// [Pos] Reusable row in the Deck Plugin version picker.

import type { DeckPluginOption } from '../../api/deckPluginApi';

interface Props {
  option: DeckPluginOption;
  selected: boolean;
  current: boolean;
  onSelect: (option: DeckPluginOption) => void;
}

const REASON_LABELS: Record<string, string> = {
  DECK_PLUGIN_UNAVAILABLE: '版本当前不可用',
  DECK_PLUGIN_DISABLED: '插件已停用',
  DECK_PLUGIN_UPGRADE_PENDING: '能力升级等待审批',
  DECK_HOST_INCOMPATIBLE: 'Deck runtime contract 不兼容',
  CLAUDE_AGENT_INCOMPATIBLE: 'ClaudeAgent 版本不兼容',
  STORY_SCHEMA_INCOMPATIBLE: 'Story schema 不兼容',
  DECK_RUNTIME_CONFIG_INCOMPATIBLE: 'Deck runtime 配置不完整',
  RUNTIME_PLUGIN_UNRESOLVED: 'Runtime 插件来源未解析',
  WORKFLOW_PERMISSION_DENIED: '当前身份无选择权限',
  RUNTIME_PLUGIN_NOT_READY: 'Runtime 插件尚未就绪',
  RUNTIME_CONTEXT_UNAVAILABLE: 'Runtime 状态暂不可用',
};

function releaseTone(option: DeckPluginOption): string {
  if (option.selectable) return 'var(--color-state-success)';
  if (option.installation_status === 'materializing') return 'var(--color-state-warning)';
  return 'var(--color-text-muted)';
}

export default function DeckPluginVersionCard({ option, selected, current, onSelect }: Props) {
  const reason = option.reason_code
    ? `${REASON_LABELS[option.reason_code] ?? '当前不可选择'}（${option.reason_code}）`
    : null;

  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      disabled={!option.selectable}
      onClick={() => onSelect(option)}
      style={{
        width: '100%',
        textAlign: 'left',
        border: selected
          ? '2px solid var(--color-action-link)'
          : '1px solid var(--color-border-neutral)',
        borderRadius: 10,
        background: selected ? 'var(--color-bg-active)' : 'var(--color-bg-paper)',
        color: 'var(--color-text-primary)',
        padding: 12,
        cursor: option.selectable ? 'pointer' : 'not-allowed',
        opacity: option.selectable ? 1 : 0.68,
        display: 'flex',
        flexDirection: 'column',
        gap: 7,
      }}
    >
      <span style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
        <span style={{ fontWeight: 700, fontSize: 13 }}>
          {option.display_name} · v{option.deck_plugin_version}
        </span>
        <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
          {current && <span style={{ color: 'var(--color-action-link)', fontSize: 10 }}>当前</span>}
          <span style={{ color: releaseTone(option), fontSize: 10, textTransform: 'uppercase' }}>
            {option.release_status}
          </span>
        </span>
      </span>
      <span style={{ display: 'flex', gap: 10, flexWrap: 'wrap', color: 'var(--color-text-secondary)', fontSize: 11 }}>
        <span>Installation：{option.installation_status}</span>
        <span>Runtime：{option.runtime_readiness}</span>
        <span>Contract：{option.compatibility}</span>
        <span>Capabilities：{option.capability_summary.length}</span>
      </span>
      {reason && <span style={{ color: 'var(--color-state-warning)', fontSize: 11 }}>{reason}</span>}
      {option.recovery && (
        <span style={{ color: 'var(--color-text-body)', fontSize: 11 }}>
          恢复入口：{option.recovery.owner} · {option.recovery.action}
        </span>
      )}
    </button>
  );
}
