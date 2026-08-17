// [Input] One server-adjudicated exact runtime version and current selection.
// [Output] Compact accessible version row with availability and recovery facts.
// [Pos] Deck version picker row.
// [Sync] 2026-08-16: restore version selection with IM semantics and no Workflow UI.

import type { DeckPluginOption } from '../../api/deckPluginApi';

interface Props {
  option: DeckPluginOption;
  selected: boolean;
  current: boolean;
  onSelect: (option: DeckPluginOption) => void;
}

export default function DeckPluginVersionCard({ option, selected, current, onSelect }: Props) {
  return (
    <button
      aria-checked={selected}
      className={`deck-version-option${selected ? ' is-selected' : ''}`}
      disabled={!option.selectable}
      onClick={() => onSelect(option)}
      role="radio"
      type="button"
    >
      <span className="deck-version-option__main">
        <span>
          <strong>{option.display_name}</strong>
          <span className="deck-version-option__number">v{option.deck_plugin_version}</span>
        </span>
        <span className="deck-version-option__badges">
          {current && <span className="is-current">当前</span>}
          <span>{option.release_status}</span>
        </span>
      </span>
      <span className="deck-version-option__meta">
        {option.installation_status} · {option.runtime_readiness} · {option.compatibility}
      </span>
      {!option.selectable && option.reason_code && (
        <span className="deck-version-option__reason">
          {option.reason_code}
          {option.recovery ? ` · ${option.recovery.owner}: ${option.recovery.action}` : ''}
        </span>
      )}
    </button>
  );
}
