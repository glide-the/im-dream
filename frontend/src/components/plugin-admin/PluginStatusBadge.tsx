// [Input] Server-reported declaration/materialization/activation states.
// [Output] Human-readable three-dimensional readiness badge.
// [Pos] Deck/Claude runtime Plugin Admin status primitive.

import type {
  ActivationStatus,
  DeclarationStatus,
  MaterializationStatus,
} from '../../api/deckPluginAdminApi';

interface PluginStatusBadgeProps {
  declarationStatus: DeclarationStatus;
  materializationStatus: MaterializationStatus;
  activationStatus: ActivationStatus;
  compact?: boolean;
}

const STATE_LABELS = {
  undeclared: 'Not installed',
  disabled: 'Disabled',
  materializing: 'Materializing…',
  failed: 'Declared, not materialized',
  load_failed: 'Load failed',
  loaded: 'Loaded',
  loadable: 'Ready',
  inactive: 'Not loadable',
} as const;

export default function PluginStatusBadge({
  declarationStatus,
  materializationStatus,
  activationStatus,
  compact = false,
}: PluginStatusBadgeProps) {
  let label: string = STATE_LABELS.inactive;
  let tone = 'neutral';
  let icon = '⏸';

  if (declarationStatus === 'disabled') {
    label = STATE_LABELS.disabled;
    tone = 'disabled';
    icon = '🚫';
  } else if (declarationStatus === 'undeclared') {
    label = STATE_LABELS.undeclared;
  } else if (materializationStatus === 'materializing') {
    label = STATE_LABELS.materializing;
    tone = 'pending';
    icon = '⏳';
  } else if (materializationStatus === 'failed') {
    label = STATE_LABELS.failed;
    tone = 'warning';
    icon = '⚠';
  } else if (materializationStatus === 'materialized' && activationStatus === 'load_failed') {
    label = STATE_LABELS.load_failed;
    tone = 'warning';
    icon = '⚠';
  } else if (materializationStatus === 'materialized' && activationStatus === 'loaded') {
    label = STATE_LABELS.loaded;
    tone = 'success';
    icon = '✓';
  } else if (materializationStatus === 'materialized' && activationStatus === 'loadable') {
    label = STATE_LABELS.loadable;
    tone = 'success';
    icon = '✓';
  }

  const title = [
    `declaration: ${declarationStatus}`,
    `materialization: ${materializationStatus}`,
    `activation: ${activationStatus}`,
  ].join(' · ');

  return (
    <span className={`plugin-admin-status plugin-admin-status--${tone}`} title={title} aria-label={`${label}; ${title}`}>
      <span aria-hidden="true">{icon}</span>
      {!compact && <span>{label}</span>}
    </span>
  );
}
