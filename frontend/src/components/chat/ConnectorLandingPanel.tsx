// [Input] Connector API client and a callback that opens Settings' resource-link connector section.
// [Output] Chat `ResourceConnectorTab` content — `ConnectorToolbar` (filter/sort placeholders),
//          a dashed `ConnectorEmptyState` (三枚资源类型图标 + 标题 + 描述 + CTA), skeleton loading,
//          and non-button connector status panels with linked resource previews. Only explicit
//          management actions navigate to Settings' resource-link section; Chat never owns the
//          Notion configuration flow.
// [Pos] chat connector landing panel (ResourceConnectorTabPanel) in frontend/src/components/chat
// [Sync] 2026-07-08: initial Chat-to-Settings connector landing panel for the resource-link migration.
// [Sync] 2026-07-08: replace text-only loading state with a skeleton-screen placeholder, aligning
//                    with 《链接器概念的交互设计稿》 Chat 入口页「无资源链接」骨架屏 default state.
// [Sync] 2026-07-08: rebuild into `ResourceConnectorTabPanel` per docs/prd/notion-session/resource-connector.md
//                    §3.2 — add `ConnectorToolbar` (filter/sort), dashed三图标 empty state with「选择连接器」
//                    CTA.
// [Sync] 2026-07-08: route connector CTA/card selection back to Settings resource-link management,
//                    matching 《链接器概念的交互设计稿》 Chat 入口页.
// [Sync] 2026-07-08: replace light-only card/empty-state fills with semantic theme tokens so the Chat
//                    resource connector tab renders correctly under dark mode.
// [Sync] 2026-07-08: convert connector entries from full-card buttons to status panels with linked
//                    resource previews and an explicit 管理 action.
import { useCallback, useEffect, useState } from 'react';
import { listConnectors, type ConnectorSource, type ResourceConnector } from '../../api/resourceConnectorApi';
import {
  IconChevronRight,
  IconClock,
  IconDatabase,
  IconFile,
  IconFolder,
  IconGrid,
} from './Icons';
import { SkeletonBar, SkeletonList } from './Skeleton';

interface ConnectorLandingPanelProps {
  /** Opens Settings and focuses the resource-link connector section. */
  onOpenConnector?: (connector: ResourceConnector | null) => void;
}

function formatLastInteraction(connector: ResourceConnector | null): string {
  const value = connector?.lastSyncedAt ?? connector?.updatedAt ?? connector?.createdAt;
  if (!value) return '暂无交互';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function getConnectorStatusLabel(connector: ResourceConnector | null): string {
  if (!connector) return '未连接';
  if (connector.status === 'authenticated' || connector.status === 'synced' || connector.auth.status === 'authenticated') {
    return '健康';
  }
  if (connector.status === 'authenticating' || connector.auth.status === 'authenticating') {
    return '认证中';
  }
  if (connector.status === 'expired' || connector.auth.status === 'expired') {
    return '已过期';
  }
  if (connector.status === 'error' || connector.auth.status === 'error') {
    return '异常';
  }
  return '未连接';
}

function getPlatformLabel(connector: ResourceConnector): string {
  return connector.platform === 'notion' ? 'Notion' : connector.platform;
}

function getAuthorizationStatusLabel(connector: ResourceConnector): string {
  switch (connector.auth.status) {
    case 'authenticated':
      return '已授权';
    case 'authenticating':
      return '授权中';
    case 'expired':
      return '授权过期';
    case 'error':
      return '授权异常';
    default:
      return '未授权';
  }
}

function getSyncStatusLabel(connector: ResourceConnector): string {
  switch (connector.status) {
    case 'syncing':
      return '同步中';
    case 'synced':
    case 'authenticated':
      return '已同步';
    case 'authenticating':
      return '等待授权';
    case 'expired':
      return '待重新授权';
    case 'error':
      return '同步异常';
    default:
      return connector.sources.length > 0 ? '已挂载' : '未同步';
  }
}

function getSourceTypeLabel(type: ConnectorSource['type']): string {
  return type === 'notion_database' ? 'Database' : 'Page';
}

function getSourceStatusLabel(status: ConnectorSource['status']): string {
  switch (status) {
    case 'syncing':
      return '同步中';
    case 'synced':
      return '已同步';
    case 'error':
      return '异常';
    default:
      return '待同步';
  }
}

function ConnectorToolbar() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem', flexShrink: 0 }}>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.35rem',
          border: '1px solid var(--color-border-paper)',
          borderRadius: '999px',
          padding: '0.4rem 0.7rem',
          background: 'var(--color-bg-surface)',
          color: 'var(--color-text-secondary)',
          fontSize: '0.76rem',
          fontWeight: 600,
        }}
      >
        筛选：全部
      </span>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.35rem',
          border: '1px solid var(--color-border-paper)',
          borderRadius: '999px',
          padding: '0.4rem 0.7rem',
          background: 'var(--color-bg-surface)',
          color: 'var(--color-text-secondary)',
          fontSize: '0.76rem',
          fontWeight: 600,
        }}
      >
        排序：最近交互
      </span>
    </div>
  );
}

function ConnectorToolbarSkeleton() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem', flexShrink: 0 }}>
      <SkeletonBar width="5.4rem" height="1.7rem" style={{ borderRadius: '999px' }} />
      <SkeletonBar width="6.6rem" height="1.7rem" style={{ borderRadius: '999px' }} />
    </div>
  );
}

function ConnectorStatusPanel({ connector, onOpen }: { connector: ResourceConnector; onOpen: () => void }) {
  const healthy = connector.status === 'authenticated'
    || connector.status === 'synced'
    || connector.auth.status === 'authenticated';
  const statusLabel = getConnectorStatusLabel(connector);
  const lastInteraction = formatLastInteraction(connector);
  const previewSources = connector.sources.slice(0, 3);
  const remainingSourceCount = Math.max(0, connector.sources.length - previewSources.length);

  return (
    <article
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
        border: '1px solid var(--color-border-paper)',
        borderRadius: '1rem',
        background: 'var(--color-bg-surface-solid)',
        padding: '0.85rem 0.9rem',
        boxShadow: '0 10px 24px var(--color-shadow-soft)',
        textAlign: 'left',
        width: '100%',
        boxSizing: 'border-box',
      }}
    >
      <div style={{ display: 'grid', gridTemplateColumns: '2.4rem minmax(0, 1fr) auto', alignItems: 'start', gap: '0.85rem' }}>
        <div
          style={{
            width: '2.4rem',
            height: '2.4rem',
            borderRadius: '0.85rem',
            border: '1px solid var(--color-border-paper)',
            background: 'var(--color-bg-hover)',
            color: 'var(--color-text-primary)',
            display: 'grid',
            placeItems: 'center',
            flexShrink: 0,
          }}
        >
          <IconDatabase style={{ width: '1rem', height: '1rem' }} />
        </div>

        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {getPlatformLabel(connector)}
            </h3>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.32rem',
                padding: '0.28rem 0.55rem',
                borderRadius: '999px',
                border: `1px solid ${healthy ? 'color-mix(in srgb, var(--color-state-success) 30%, var(--color-border-paper))' : 'var(--color-border-paper)'}`,
                background: healthy ? 'color-mix(in srgb, var(--color-state-success) 16%, var(--color-bg-paper))' : 'var(--color-bg-hover)',
                color: healthy ? 'var(--color-state-success)' : 'var(--color-text-secondary)',
                fontSize: '0.72rem',
                fontWeight: 700,
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  width: '0.4rem',
                  height: '0.4rem',
                  borderRadius: '999px',
                  background: healthy ? 'var(--color-state-success)' : 'var(--color-text-muted)',
                }}
              />
              {statusLabel}
            </span>
          </div>
          <p style={{ margin: '0.32rem 0 0', fontSize: '0.78rem', lineHeight: 1.55, color: 'var(--color-text-secondary)' }}>
            {connector.name}
          </p>
          <div style={{ marginTop: '0.4rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
            <IconClock style={{ width: '0.82rem', height: '0.82rem' }} />
            最近交互 {lastInteraction}
          </div>
        </div>

        <button
          type="button"
          onClick={onOpen}
          style={{
            justifySelf: 'end',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            border: '1px solid var(--color-border-paper)',
            borderRadius: '999px',
            padding: '0.42rem 0.68rem',
            background: 'var(--color-bg-surface)',
            color: 'var(--color-text-primary)',
            cursor: 'pointer',
            fontSize: '0.76rem',
            fontWeight: 700,
            whiteSpace: 'nowrap',
          }}
        >
          管理
          <IconChevronRight style={{ width: '0.78rem', height: '0.78rem', color: 'var(--color-text-muted)' }} />
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.55rem' }}>
        {[
          ['授权状态', getAuthorizationStatusLabel(connector)],
          ['同步状态', getSyncStatusLabel(connector)],
          ['已链接资源', `${connector.sources.length} 个`],
        ].map(([label, value]) => (
          <div key={label} style={{ border: '1px solid var(--color-border-paper)', borderRadius: '0.75rem', background: 'var(--color-bg-surface)', padding: '0.55rem 0.65rem', minWidth: 0 }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>{label}</div>
            <div style={{ marginTop: '0.2rem', fontSize: '0.82rem', color: 'var(--color-text-primary)', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gap: '0.45rem' }}>
        <div style={{ fontSize: '0.74rem', color: 'var(--color-text-muted)', fontWeight: 700 }}>已链接资源</div>
        {previewSources.length > 0 ? previewSources.map((source) => {
          const SourceIcon = source.type === 'notion_page' ? IconFile : IconDatabase;
          return (
            <div key={source.id} style={{ display: 'grid', gridTemplateColumns: '1.55rem minmax(0, 1fr) auto', alignItems: 'center', gap: '0.55rem', border: '1px solid var(--color-border-paper)', borderRadius: '0.7rem', background: 'var(--color-bg-hover)', padding: '0.52rem 0.6rem' }}>
              <span style={{ width: '1.55rem', height: '1.55rem', borderRadius: '0.5rem', display: 'grid', placeItems: 'center', color: 'var(--color-text-secondary)', background: 'var(--color-bg-surface)' }}>
                <SourceIcon style={{ width: '0.82rem', height: '0.82rem' }} />
              </span>
              <span style={{ minWidth: 0 }}>
                <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.8rem', color: 'var(--color-text-primary)', fontWeight: 650 }}>{source.title}</span>
                <span style={{ display: 'block', marginTop: '0.12rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                  {getSourceTypeLabel(source.type)} · {getSourceStatusLabel(source.status)}
                  {typeof source.pageCount === 'number' ? ` · ${source.pageCount} pages` : ''}
                </span>
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                {formatLastInteraction({ ...connector, lastSyncedAt: source.syncedAt ?? source.updatedAt })}
              </span>
            </div>
          );
        }) : (
          <div style={{ border: '1px dashed var(--color-border-paper)', borderRadius: '0.75rem', padding: '0.62rem 0.7rem', color: 'var(--color-text-muted)', fontSize: '0.76rem' }}>
            暂无已链接资源
          </div>
        )}
        {remainingSourceCount > 0 ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem', paddingLeft: '0.1rem' }}>
            另有 {remainingSourceCount} 个资源，可进入管理查看
          </div>
        ) : null}
      </div>
    </article>
  );
}

function ConnectorEmptyState({ onSelectConnector }: { onSelectConnector: () => void }) {
  return (
    <div
      style={{
        border: '1px dashed var(--color-border-paper)',
        borderRadius: '1rem',
        background: 'var(--color-bg-surface)',
        padding: '1.6rem 1.2rem',
        textAlign: 'center',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.6rem' }}>
        <span style={{ width: '2.2rem', height: '2.2rem', borderRadius: '0.7rem', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-hover)', display: 'grid', placeItems: 'center', color: 'var(--color-text-secondary)' }}>
          <IconDatabase style={{ width: '1rem', height: '1rem' }} />
        </span>
        <span style={{ width: '2.2rem', height: '2.2rem', borderRadius: '0.7rem', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-hover)', display: 'grid', placeItems: 'center', color: 'var(--color-text-secondary)' }}>
          <IconFolder style={{ width: '1rem', height: '1rem' }} />
        </span>
        <span style={{ width: '2.2rem', height: '2.2rem', borderRadius: '0.7rem', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-hover)', display: 'grid', placeItems: 'center', color: 'var(--color-text-secondary)' }}>
          <IconGrid style={{ width: '1rem', height: '1rem' }} />
        </span>
      </div>
      <h3 style={{ margin: '0.9rem 0 0', fontSize: '0.96rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
        暂无资源连接器
      </h3>
      <p style={{ margin: '0.4rem auto 0', maxWidth: '28rem', fontSize: '0.82rem', lineHeight: 1.6, color: 'var(--color-text-secondary)' }}>
        连接 Notion / 飞书 / CLI 后可在对话中使用资源
      </p>
      <button
        type="button"
        onClick={onSelectConnector}
        style={{
          marginTop: '1.1rem',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.45rem',
          border: 'none',
          borderRadius: '999px',
          padding: '0.68rem 1rem',
          background: 'var(--color-action-link)',
          color: 'var(--color-text-on-action)',
          fontSize: '0.84rem',
          fontWeight: 700,
          cursor: 'pointer',
        }}
      >
        选择连接器
        <IconChevronRight style={{ width: '0.9rem', height: '0.9rem' }} />
      </button>
    </div>
  );
}

export default function ConnectorLandingPanel({ onOpenConnector }: ConnectorLandingPanelProps) {
  const [connectors, setConnectors] = useState<ResourceConnector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void (async () => {
      setLoading(true);
      setError(null);

      try {
        const items = await listConnectors();
        if (active) {
          setConnectors(items);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : '连接器状态读取失败');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  const handleSelectConnector = useCallback((connector: ResourceConnector | null) => {
    onOpenConnector?.(connector);
  }, [onOpenConnector]);

  const hasConnectors = connectors.length > 0;

  return (
    <section
      style={{
        flex: 1,
        minHeight: 0,
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        border: '1px solid var(--color-border-paper)',
        borderRadius: '1.15rem',
        background: 'var(--color-bg-surface)',
        boxShadow: '0 16px 36px var(--color-shadow-soft)',
        overflow: 'hidden',
        padding: '0.95rem 1rem',
      }}
    >
      {loading ? <ConnectorToolbarSkeleton /> : <ConnectorToolbar />}

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'grid', gap: '0.8rem' }}>
        {loading ? <SkeletonList rows={2} /> : null}

        {!loading && hasConnectors ? connectors.map((connector) => (
          <ConnectorStatusPanel key={connector.id} connector={connector} onOpen={() => handleSelectConnector(connector)} />
        )) : null}

        {!loading && !hasConnectors ? (
          <ConnectorEmptyState onSelectConnector={() => handleSelectConnector(null)} />
        ) : null}

        {error ? (
          <div style={{ fontSize: '0.78rem', color: 'var(--color-state-error)' }}>
            {error}
          </div>
        ) : null}
      </div>
    </section>
  );
}
