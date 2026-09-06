// [Input] Server-computed capability diff and optional administrator verdict callbacks.
// [Output] Added/removed capability review with explicit approve/reject controls.
// [Pos] Plugin Admin capability-expansion approval component.

import type { PluginCapabilityDiffValue } from '../../api/deckPluginAdminApi';

interface PluginCapabilityDiffProps {
  diff: PluginCapabilityDiffValue;
  pendingApproval?: boolean;
  canManage?: boolean;
  busy?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
}

export default function PluginCapabilityDiff({
  diff,
  pendingApproval = false,
  canManage = false,
  busy = false,
  onApprove,
  onReject,
}: PluginCapabilityDiffProps) {
  return (
    <section className="plugin-admin-capability-diff" aria-label="Capability changes">
      <div className="plugin-admin-section-heading">
        <div>
          <h4>能力变更</h4>
          <p>{diff.added.length ? '新增能力必须由管理员显式批准。' : '该版本没有新增能力。'}</p>
        </div>
        {pendingApproval && <span className="plugin-admin-pill plugin-admin-pill--pending">等待审批</span>}
      </div>
      <div className="plugin-admin-diff-grid">
        <div>
          <strong>Added</strong>
          {diff.added.length ? (
            <ul>{diff.added.map((item) => <li key={item}>+ {item}</li>)}</ul>
          ) : <p className="plugin-admin-muted">无</p>}
        </div>
        <div>
          <strong>Removed</strong>
          {diff.removed.length ? (
            <ul>{diff.removed.map((item) => <li key={item}>− {item}</li>)}</ul>
          ) : <p className="plugin-admin-muted">无</p>}
        </div>
      </div>
      {pendingApproval && canManage && (
        <div className="plugin-admin-actions">
          <button type="button" className="plugin-admin-button plugin-admin-button--primary" disabled={busy} onClick={onApprove}>
            批准升级
          </button>
          <button type="button" className="plugin-admin-button" disabled={busy} onClick={onReject}>
            拒绝
          </button>
        </div>
      )}
    </section>
  );
}
