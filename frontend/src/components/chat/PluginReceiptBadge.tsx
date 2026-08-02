// [Input] getThreadPluginLoadReceipt API.
// [Output] Compact badge showing the packed plugin package/version/digest for the
//          active chat thread (workspace load receipt from the backend).
// [Pos] Mounted next to the Deck voice badge in ChatView's top-right action row.

import { useEffect, useState } from 'react';
import {
  getThreadPluginLoadReceipt,
  shortDigest,
  type PluginLoadReceipt,
} from '../../api/claudePluginAdminApi';

interface PluginReceiptBadgeProps {
  threadId: string | null;
}

export default function PluginReceiptBadge({ threadId }: PluginReceiptBadgeProps) {
  const [receipt, setReceipt] = useState<PluginLoadReceipt | null>(null);

  useEffect(() => {
    let cancelled = false;
    setReceipt(null);
    if (!threadId) return undefined;
    getThreadPluginLoadReceipt(threadId)
      .then((payload) => {
        if (!cancelled) setReceipt(payload);
      })
      .catch(() => {
        if (!cancelled) setReceipt(null);
      });
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  const plugins = receipt?.receipt?.plugins ?? receipt?.launch_manifest?.plugins ?? [];
  if (!threadId || plugins.length === 0) return null;

  const frozen = receipt?.receipt?.frozen === true;
  return (
    <div
      title={
        plugins
          .map(
            (plugin) =>
              `${plugin.package_spec} v${plugin.resolved_version ?? '?'}\n${plugin.artifact_digest}`,
          )
          .join('\n\n') + (frozen ? '\n\nworkspace frozen（本次对话锁定）' : '')
      }
      style={{
        height: '2rem',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: '0 0.6rem',
        borderRadius: '0.55rem',
        border: '1px solid #9b7ff555',
        background: '#9b7ff518',
        color: '#7a63d8',
        fontSize: '0.78rem',
        fontWeight: 600,
        maxWidth: '16rem',
        overflow: 'hidden',
      }}
    >
      <span aria-hidden>🧩</span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {plugins.map((plugin) => (
          <span key={`${plugin.package_spec}-${plugin.artifact_digest}`} style={{ marginRight: '0.5rem' }}>
            {plugin.package_spec.split('@')[0]} v{plugin.resolved_version ?? '?'} ·{' '}
            {shortDigest(plugin.artifact_digest)}
          </span>
        ))}
      </span>
      {frozen ? <span style={{ opacity: 0.75 }}>🔒</span> : null}
    </div>
  );
}
