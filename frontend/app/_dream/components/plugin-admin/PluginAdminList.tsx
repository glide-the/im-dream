// [Input] Filtered normalized plugin catalog, selection state, permission, and lifecycle callback.
// [Output] Loading/error/empty/list states for Plugin Admin.
// [Pos] Plugin Admin catalog list.

import type { PluginAdminItem, PluginMutationAction } from '../../api/deckPluginAdminApi';
import PluginAdminListItem from './PluginAdminListItem';

interface PluginAdminListProps {
  items: PluginAdminItem[];
  selectedKey?: string;
  loading: boolean;
  error?: Error | null;
  canManage: boolean;
  busy: boolean;
  onRetry: () => void;
  onSelect: (item: PluginAdminItem) => void;
  onAction: (action: PluginMutationAction, item: PluginAdminItem) => void;
}

function pluginAdminItemKey(item: PluginAdminItem): string {
  return item.category === 'deck-workflow'
    ? `deck:${item.deckPluginId}:${item.deckPluginVersion}`
    : `runtime:${item.parentDeckPluginId ?? 'global'}:${item.claudeCodePluginId}:${item.resolvedVersion}`;
}

export default function PluginAdminList({
  items,
  selectedKey,
  loading,
  error,
  canManage,
  busy,
  onRetry,
  onSelect,
  onAction,
}: PluginAdminListProps) {
  if (loading && !items.length) {
    return <div className="plugin-admin-empty" aria-live="polite">正在读取服务端插件目录…</div>;
  }
  if (error && !items.length) {
    return (
      <div className="plugin-admin-empty plugin-admin-empty--error" role="alert">
        <strong>插件目录暂不可用</strong>
        <p>{error.message}</p>
        <button type="button" className="plugin-admin-button" onClick={onRetry}>重试</button>
      </div>
    );
  }
  if (!items.length) {
    return <div className="plugin-admin-empty">当前分类没有服务端返回的插件记录。</div>;
  }
  return (
    <div className="plugin-admin-list" aria-label="Plugin catalog">
      {error && (
        <div className="plugin-admin-inline-warning" role="status">
          刷新失败，当前显示上次成功结果。<button type="button" onClick={onRetry}>重试</button>
        </div>
      )}
      {items.map((item) => (
        <PluginAdminListItem
          key={pluginAdminItemKey(item)}
          item={item}
          selected={pluginAdminItemKey(item) === selectedKey}
          canManage={canManage}
          busy={busy}
          onSelect={onSelect}
          onAction={onAction}
        />
      ))}
    </div>
  );
}
