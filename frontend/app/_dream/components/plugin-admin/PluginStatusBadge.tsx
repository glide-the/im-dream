// [Input] Server-reported declaration/materialization/activation states.
// [Output] Workflow availability badge from the server-reported installation, file, and loading states.
// [Pos] Deck workflow status primitive.
// [Sync] 2026-10-10: remove runtime-only compact mode and replace file-preparation jargon with specific feedback.

import type {
  ActivationStatus,
  DeclarationStatus,
  MaterializationStatus,
} from '../../api/deckPluginAdminApi';

interface PluginStatusBadgeProps {
  declarationStatus: DeclarationStatus;
  materializationStatus: MaterializationStatus;
  activationStatus: ActivationStatus;
}

const STATE_LABELS = {
  undeclared: '未安装',
  disabled: '已停用',
  materializing: '文件准备中…',
  failed: '文件准备失败',
  load_failed: '加载失败',
  loaded: '已加载',
  loadable: '可使用',
  inactive: '暂不可使用',
} as const;

export default function PluginStatusBadge({
  declarationStatus,
  materializationStatus,
  activationStatus,
}: PluginStatusBadgeProps) {
  let label: string = STATE_LABELS.inactive;
  let tone = 'neutral';
  let icon = '·';

  if (declarationStatus === 'disabled') {
    label = STATE_LABELS.disabled;
    tone = 'disabled';
    icon = '·';
  } else if (declarationStatus === 'undeclared') {
    label = STATE_LABELS.undeclared;
  } else if (materializationStatus === 'materializing') {
    label = STATE_LABELS.materializing;
    tone = 'pending';
    icon = '…';
  } else if (materializationStatus === 'failed') {
    label = STATE_LABELS.failed;
    tone = 'warning';
    icon = '!';
  } else if (materializationStatus === 'materialized' && activationStatus === 'load_failed') {
    label = STATE_LABELS.load_failed;
    tone = 'warning';
    icon = '!';
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
      <span>{label}</span>
    </span>
  );
}
