// [Input] Connector API client and a callback that opens the full-page `ConnectorConfigPage`.
// [Output] Chat `ResourceConnectorTab` content — `ConnectorToolbar` (filter/sort placeholders),
//          a dashed `ConnectorEmptyState` (三枚资源类型图标 + 标题 + 描述 + CTA), skeleton loading,
//          and a `ConnectorList` of connector cards. Selecting the CTA or a card navigates (page-level,
//          not a Settings redirect) into `ConnectorConfigPage`.
// [Pos] chat connector landing panel (ResourceConnectorTabPanel) in frontend/src/components/chat
// [Sync] 2026-07-08: initial Chat-to-Settings connector landing panel for the resource-link migration.
// [Sync] 2026-07-08: replace text-only loading state with a skeleton-screen placeholder, aligning
//                    with 《链接器概念的交互设计稿》 Chat 入口页「无资源链接」骨架屏 default state.
// [Sync] 2026-07-08: rebuild into `ResourceConnectorTabPanel` per docs/prd/notion-session/resource-connector.md
//                    §3.2 — add `ConnectorToolbar` (filter/sort), dashed三图标 empty state with「选择连接器」
//                    CTA, and route connector selection into the in-Chat `ConnectorConfigPage` instead of Settings.
import { useCallback, useEffect, useState } from 'react';
import { listConnectors, type ResourceConnector } from '../../api/resourceConnectorApi';
import {
  IconChevronRight,
  IconClock,
  IconDatabase,
  IconFolder,
  IconGrid,
} from './Icons';
import { SkeletonBar, SkeletonList } from './Skeleton';

interface ConnectorLandingPanelProps {
  /** Opens the full `ConnectorConfigPage` for the given connector (or the default Notion connector when none supplied yet). */
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

function ConnectorCard({ connector, onOpen }: { connector: ResourceConnector; onOpen: () => void }) {
  const healthy = connector.status === 'authenticated'
    || connector.status === 'synced'
    || connector.auth.status === 'authenticated';
  const statusLabel = getConnectorStatusLabel(connector);
  const lastInteraction = formatLastInteraction(connector);

  return (
    <button
      type="button"
      onClick={onOpen}
      style={{
        display: 'grid',
        gridTemplateColumns: '2.4rem minmax(0, 1fr) auto',
        alignItems: 'center',
        gap: '0.85rem',
        border: '1px solid var(--color-border-paper)',
        borderRadius: '1rem',
        background: 'rgba(255,250,242,0.86)',
        padding: '0.85rem 0.9rem',
        boxShadow: '0 10px 24px rgba(91, 69, 44, 0.05)',
        cursor: 'pointer',
        textAlign: 'left',
        width: '100%',
        font: 'inherit',
        color: 'inherit',
      }}
    >
      <div
        style={{
          width: '2.4rem',
          height: '2.4rem',
          borderRadius: '0.85rem',
          border: '1px solid var(--color-border-paper)',
          background: 'rgba(95, 74, 54, 0.08)',
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
            {connector.name}
          </h3>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.32rem',
              padding: '0.28rem 0.55rem',
              borderRadius: '999px',
              border: `1px solid ${healthy ? 'rgba(126, 148, 104, 0.22)' : 'var(--color-border-paper)'}`,
              background: healthy ? 'rgba(126, 148, 104, 0.12)' : 'rgba(91, 69, 44, 0.06)',
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
          {connector.platform.toUpperCase()} · 点击管理认证与来源
        </p>
        <div style={{ marginTop: '0.4rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
          <IconClock style={{ width: '0.82rem', height: '0.82rem' }} />
          最近交互 {lastInteraction}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', justifySelf: 'end' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>管理</span>
        <IconChevronRight style={{ width: '0.88rem', height: '0.88rem', color: 'var(--color-text-muted)' }} />
      </div>
    </button>
  );
}

function ConnectorEmptyState({ onSelectConnector }: { onSelectConnector: () => void }) {
  return (
    <div
      style={{
        border: '1px dashed var(--color-border-paper)',
        borderRadius: '1rem',
        background: 'rgba(255,250,242,0.72)',
        padding: '1.6rem 1.2rem',
        textAlign: 'center',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.6rem' }}>
        <span style={{ width: '2.2rem', height: '2.2rem', borderRadius: '0.7rem', border: '1px solid var(--color-border-paper)', background: 'rgba(95, 74, 54, 0.06)', display: 'grid', placeItems: 'center', color: 'var(--color-text-secondary)' }}>
          <IconDatabase style={{ width: '1rem', height: '1rem' }} />
        </span>
        <span style={{ width: '2.2rem', height: '2.2rem', borderRadius: '0.7rem', border: '1px solid var(--color-border-paper)', background: 'rgba(95, 74, 54, 0.06)', display: 'grid', placeItems: 'center', color: 'var(--color-text-secondary)' }}>
          <IconFolder style={{ width: '1rem', height: '1rem' }} />
        </span>
        <span style={{ width: '2.2rem', height: '2.2rem', borderRadius: '0.7rem', border: '1px solid var(--color-border-paper)', background: 'rgba(95, 74, 54, 0.06)', display: 'grid', placeItems: 'center', color: 'var(--color-text-secondary)' }}>
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
        background: 'linear-gradient(180deg, rgba(255,250,242,0.96), rgba(247,239,227,0.9))',
        boxShadow: '0 16px 36px rgba(91, 69, 44, 0.08)',
        overflow: 'hidden',
        padding: '0.95rem 1rem',
      }}
    >
      {loading ? <ConnectorToolbarSkeleton /> : <ConnectorToolbar />}

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'grid', gap: '0.8rem' }}>
        {loading ? <SkeletonList rows={2} /> : null}

        {!loading && hasConnectors ? connectors.map((connector) => (
          <ConnectorCard key={connector.id} connector={connector} onOpen={() => handleSelectConnector(connector)} />
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
