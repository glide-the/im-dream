// [Input] Authoritative server lifecycle operation and optional dismissal callback.
// [Output] Accessible operation phase/progress/error surface.
// [Pos] Plugin Admin mutation progress component.

import type { PluginOperation } from '../../api/deckPluginAdminApi';
import PluginErrorCard from './PluginErrorCard';

interface PluginOperationProgressProps {
  operation: PluginOperation;
  onDismiss?: () => void;
}

export default function PluginOperationProgress({ operation, onDismiss }: PluginOperationProgressProps) {
  const terminal = ['ready', 'completed', 'error', 'failed'].includes(operation.status);
  const failed = operation.status === 'error' || operation.status === 'failed';
  const progress = operation.progress == null
    ? operation.status === 'queued' ? 8 : terminal ? 100 : 45
    : Math.max(0, Math.min(100, operation.progress));

  return (
    <section className="plugin-admin-operation" aria-live="polite">
      <div className="plugin-admin-section-heading">
        <div>
          <h4>{failed ? '操作失败' : terminal ? '操作完成' : '操作进行中'}</h4>
          <p>{operation.phase ?? operation.message ?? `operation_id: ${operation.operationId}`}</p>
        </div>
        <span className={`plugin-admin-pill plugin-admin-pill--${failed ? 'danger' : terminal ? 'success' : 'pending'}`}>
          {operation.status}
        </span>
      </div>
      {!failed && (
        <div className="plugin-admin-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
          <span style={{ width: `${progress}%` }} />
        </div>
      )}
      {failed && (
        <PluginErrorCard
          code={operation.errorCode}
          summary={operation.errorSummary ?? operation.message}
          operationId={operation.operationId}
        />
      )}
      {terminal && onDismiss && (
        <button type="button" className="plugin-admin-link-button" onClick={onDismiss}>关闭</button>
      )}
    </section>
  );
}
