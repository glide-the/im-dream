// [Input] Validated per-reply compaction snapshot and current stream activity.
// [Output] Standalone progress/completion divider, including truthful terminal feedback.
// [Pos] Chat reply marker outside the historical process disclosure.
// [Sync] 2026-10-12: historical rows never animate; completed source comes from SDK boundary.
import { useTranslation } from 'react-i18next';
import { FiAlertCircle, FiCheckCircle, FiLoader, FiXCircle } from 'react-icons/fi';
import type { ContextCompactionSnapshot } from '../../lib/context-compaction';
import './ContextCompactionMarker.css';

export default function ContextCompactionMarker({ row, isActive }: {
  row: ContextCompactionSnapshot;
  isActive: boolean;
}) {
  const { t } = useTranslation();
  const state = row.state === 'running' && !isActive ? 'unconfirmed' : row.state;
  const key = state === 'completed'
    ? (row.trigger === 'auto' ? 'automaticCompleted' : 'completed')
    : state;
  const Icon = state === 'running' ? FiLoader : state === 'completed'
    ? FiCheckCircle : state === 'cancelled' ? FiXCircle : FiAlertCircle;
  return <div
    className="context-compaction-marker"
    data-context-compaction-id={row.id}
    data-context-compaction-state={state}
    data-context-compaction-trigger={row.trigger ?? undefined}
    role="status"
    aria-live={isActive ? 'polite' : 'off'}
  >
    <Icon className={state === 'running' ? 'context-compaction-marker__spinner' : undefined} aria-hidden="true" />
    <span>{t(`chat.contextCompaction.${key}`)}</span>
  </div>;
}
