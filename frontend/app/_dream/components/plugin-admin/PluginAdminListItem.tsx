// [Input] Normalized Deck workflow or ClaudeAgent runtime plugin record and server permission result.
// [Output] Plugin catalog card with exact identity, readiness, health, compatibility, and legal actions.
// [Pos] Plugin Admin list row.

import type {
  DeckPluginInstallation,
  PluginAdminItem,
  PluginMutationAction,
} from '../../api/deckPluginAdminApi';
import PluginStatusBadge from './PluginStatusBadge';

interface PluginAdminListItemProps {
  item: PluginAdminItem;
  selected: boolean;
  canManage: boolean;
  busy: boolean;
  onSelect: (item: PluginAdminItem) => void;
  onAction: (action: PluginMutationAction, item: PluginAdminItem) => void;
}

function formatDate(value?: string): string {
  if (!value) return '无记录';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('zh-CN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(date);
}

function ActionButton({ children, onClick, disabled = false, danger = false }: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      className={`plugin-admin-button${danger ? ' plugin-admin-button--danger' : ''}`}
      disabled={disabled}
      onClick={(event) => { event.stopPropagation(); onClick(); }}
    >
      {children}
    </button>
  );
}

export default function PluginAdminListItem({
  item,
  selected,
  canManage,
  busy,
  onSelect,
  onAction,
}: PluginAdminListItemProps) {
  const isDeck = item.category === 'deck-workflow';
  const deck = isDeck ? item as DeckPluginInstallation : null;
  const displayId = item.category === 'deck-workflow' ? item.deckPluginId : item.claudeCodePluginId;
  const version = item.category === 'deck-workflow' ? item.deckPluginVersion : item.resolvedVersion;
  const capabilities = deck?.effectiveCapabilities ?? [];
  const hasReadinessError = item.materializationStatus === 'failed' || item.activationStatus === 'load_failed';

  return (
    <article
      className={`plugin-admin-list-item${selected ? ' plugin-admin-list-item--selected' : ''}`}
      tabIndex={0}
      role="button"
      aria-pressed={selected}
      onClick={() => onSelect(item)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelect(item);
        }
      }}
    >
      <div className="plugin-admin-list-item__top">
        <div className="plugin-admin-list-item__identity">
          <div className="plugin-admin-list-item__title-row">
            <h3>{item.displayName}</h3>
            <span className="plugin-admin-version">v{version}</span>
          </div>
          <code>{displayId}</code>
        </div>
        <PluginStatusBadge
          declarationStatus={item.declarationStatus}
          materializationStatus={item.materializationStatus}
          activationStatus={item.activationStatus}
        />
      </div>

      <div className="plugin-admin-facts">
        <span><strong>类型</strong>{isDeck ? 'Deck 工作流插件' : 'ClaudeAgent 运行时插件'}</span>
        <span><strong>来源</strong>{deck?.sourceLabel ?? 'runtime lock'}</span>
        <span><strong>兼容</strong>{deck?.compatibilityStatus ?? '由父 Deck release 决定'}</span>
        <span><strong>健康</strong>{item.healthStatus}</span>
        <span><strong>能力</strong>{capabilities.length ? `${capabilities.length} 项 · ${capabilities.slice(0, 2).join(', ')}` : '未返回'}</span>
        <span><strong>最近运行</strong>{formatDate(deck?.lastRunAt)}</span>
      </div>

      {(deck?.lastErrorCode || item.lastErrorCode) && (
        <div className="plugin-admin-list-item__error">
          <code>{deck?.lastErrorCode ?? item.lastErrorCode}</code>
          <span>{deck?.lastErrorSummary ?? item.lastErrorSummary ?? '查看详情了解恢复方式'}</span>
        </div>
      )}

      <div className="plugin-admin-list-item__footer">
        <button type="button" className="plugin-admin-link-button" onClick={(event) => { event.stopPropagation(); onSelect(item); }}>
          Configuration / Status
        </button>
        {canManage ? (
          <div className="plugin-admin-actions">
            {deck?.status === 'disabled' && <ActionButton disabled={busy} onClick={() => onAction('enable', item)}>Enable</ActionButton>}
            {deck?.status === 'ready' && <ActionButton disabled={busy} onClick={() => onAction('disable', item)}>Disable</ActionButton>}
            {deck?.availableVersion && deck.availableVersion !== deck.deckPluginVersion && (
              <ActionButton disabled={busy} onClick={() => onAction('upgrade', item)}>Upgrade</ActionButton>
            )}
            {deck && deck.rollbackVersions.length > 0 && (
              <ActionButton disabled={busy} onClick={() => onAction('rollback', item)}>Rollback</ActionButton>
            )}
            {hasReadinessError && <ActionButton disabled={busy} onClick={() => onAction('reconcile', item)}>Reconcile</ActionButton>}
            {deck && !deck.isSystem && deck.status !== 'uninstalled' && (
              <ActionButton danger disabled={busy} onClick={() => onAction('uninstall', item)}>Uninstall</ActionButton>
            )}
          </div>
        ) : <span className="plugin-admin-readonly">只读 · 管理动作需要插件管理员权限</span>}
      </div>
    </article>
  );
}
