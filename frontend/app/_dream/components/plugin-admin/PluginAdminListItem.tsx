// [Input] Normalized Deck workflow installation and server permission result.
// [Output] Plugin catalog card with exact identity, readiness, health, compatibility, and legal actions.
// [Pos] Plugin Admin list row.
// [Sync] 2026-10-10: remove runtime-only fields and lifecycle branches; show workflow facts.

import type {
  DeckPluginInstallation,
  PluginMutationAction,
} from '../../api/deckPluginAdminApi';
import PluginStatusBadge from './PluginStatusBadge';

interface PluginAdminListItemProps {
  item: DeckPluginInstallation;
  selected: boolean;
  canManage: boolean;
  busy: boolean;
  onSelect: (item: DeckPluginInstallation) => void;
  onAction: (action: PluginMutationAction, item: DeckPluginInstallation) => void;
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
  const capabilities = item.effectiveCapabilities;
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
            <span className="plugin-admin-version">v{item.deckPluginVersion}</span>
          </div>
          <code>{item.deckPluginId}</code>
        </div>
        <PluginStatusBadge
          declarationStatus={item.declarationStatus}
          materializationStatus={item.materializationStatus}
          activationStatus={item.activationStatus}
        />
      </div>

      <div className="plugin-admin-facts">
        <span><strong>来源</strong>{item.sourceLabel}</span>
        <span><strong>兼容</strong>{item.compatibilityStatus}</span>
        <span><strong>默认版本</strong>{item.defaultVersion ?? '未设置'}</span>
        <span><strong>健康</strong>{item.healthStatus}</span>
        <span><strong>能力</strong>{capabilities.length ? `${capabilities.length} 项 · ${capabilities.slice(0, 2).join(', ')}` : '未返回'}</span>
        <span><strong>最近运行</strong>{formatDate(item.lastRunAt)}</span>
      </div>

      {item.lastErrorCode && (
        <div className="plugin-admin-list-item__error">
          <code>{item.lastErrorCode}</code>
          <span>{item.lastErrorSummary ?? '查看详情了解恢复方式'}</span>
        </div>
      )}

      <div className="plugin-admin-list-item__footer">
        <button type="button" className="plugin-admin-link-button" onClick={(event) => { event.stopPropagation(); onSelect(item); }}>
          工作流详情
        </button>
        {canManage ? (
          <div className="plugin-admin-actions">
            {item.status === 'disabled' && <ActionButton disabled={busy} onClick={() => onAction('enable', item)}>启用</ActionButton>}
            {item.status === 'ready' && <ActionButton disabled={busy} onClick={() => onAction('disable', item)}>停用</ActionButton>}
            {item.availableVersion && item.availableVersion !== item.deckPluginVersion && (
              <ActionButton disabled={busy} onClick={() => onAction('upgrade', item)}>升级</ActionButton>
            )}
            {item.rollbackVersions.length > 0 && (
              <ActionButton disabled={busy} onClick={() => onAction('rollback', item)}>回退版本</ActionButton>
            )}
            {hasReadinessError && <ActionButton disabled={busy} onClick={() => onAction('reconcile', item)}>重试准备</ActionButton>}
            {!item.isSystem && item.status !== 'uninstalled' && (
              <ActionButton danger disabled={busy} onClick={() => onAction('uninstall', item)}>卸载</ActionButton>
            )}
          </div>
        ) : <span className="plugin-admin-readonly">只读 · 管理动作需要插件管理员权限</span>}
      </div>
    </article>
  );
}
