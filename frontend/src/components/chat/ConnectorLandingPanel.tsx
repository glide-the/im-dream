// [Input] Connector API client and Settings navigation callback.
// [Output] Lightweight Chat connector landing panel with status summary, empty state, and a Settings CTA.
// [Pos] chat connector landing panel in frontend/src/components/chat
// [Sync] 2026-07-08: initial Chat-to-Settings connector landing panel for the resource-link migration.
// [Sync] 2026-07-08: replace text-only loading state with a skeleton-screen placeholder, aligning
//                    with 《链接器概念的交互设计稿》 Chat 入口页「无资源链接」骨架屏 default state.
import { useCallback, useEffect, useState } from 'react';
import { listConnectors, type ResourceConnector } from '../../api/resourceConnectorApi';
import {
  IconChevronRight,
  IconClock,
  IconDatabase,
  IconSettings,
} from './Icons';
import { SkeletonList } from './Skeleton';

interface ConnectorLandingPanelProps {
  onOpenSettings?: () => void;
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

function ConnectorSummaryRow({ connector }: { connector: ResourceConnector }) {
  const healthy = connector.status === 'authenticated'
    || connector.status === 'synced'
    || connector.auth.status === 'authenticated';
  const statusLabel = getConnectorStatusLabel(connector);
  const lastInteraction = formatLastInteraction(connector);

  return (
    <div
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
          {connector.platform.toUpperCase()} · 已连接平台资源会在这里显示最近交互时间
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
    </div>
  );
}

export default function ConnectorLandingPanel({ onOpenSettings }: ConnectorLandingPanelProps) {
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

  const handleOpenSettings = useCallback(() => {
    onOpenSettings?.();
  }, [onOpenSettings]);

  const hasConnectors = connectors.length > 0;

  return (
    <section
      style={{
        flex: 1,
        minHeight: 0,
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid var(--color-border-paper)',
        borderRadius: '1.15rem',
        background: 'linear-gradient(180deg, rgba(255,250,242,0.96), rgba(247,239,227,0.9))',
        boxShadow: '0 16px 36px rgba(91, 69, 44, 0.08)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '0.95rem 1rem',
          borderBottom: '1px solid var(--color-border-paper)',
          background: 'linear-gradient(180deg, rgba(255,255,255,0.5), rgba(255,255,255,0))',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              <IconSettings style={{ width: '0.86rem', height: '0.86rem' }} />
              资源链接器
            </div>
            <h2 style={{ margin: '0.4rem 0 0', fontSize: '0.98rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Chat 只保留入口，完整管理放到 Settings
            </h2>
            <p style={{ margin: '0.32rem 0 0', fontSize: '0.8rem', lineHeight: 1.55, color: 'var(--color-text-secondary)' }}>
              连接完成后，Agent 能读取外部资料；认证、资源选择和来源维护都在 Settings 里继续处理。
            </p>
          </div>
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '0.95rem 1rem', display: 'grid', gap: '0.8rem' }}>
        {loading ? <SkeletonList rows={2} /> : null}

        {!loading && hasConnectors ? connectors.map((connector) => (
          <ConnectorSummaryRow key={connector.id} connector={connector} />
        )) : null}

        {!loading && !hasConnectors ? (
          <div
            style={{
              border: '1px dashed var(--color-border-paper)',
              borderRadius: '1rem',
              background: 'rgba(255,250,242,0.72)',
              padding: '1.4rem 1rem',
              textAlign: 'center',
            }}
          >
            <IconDatabase style={{ width: '2rem', height: '2rem', color: 'var(--color-text-muted)' }} />
            <h3 style={{ margin: '0.8rem 0 0', fontSize: '0.96rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              还没有资源链接
            </h3>
            <p style={{ margin: '0.4rem auto 0', maxWidth: '28rem', fontSize: '0.82rem', lineHeight: 1.6, color: 'var(--color-text-secondary)' }}>
              在 Settings 里创建和配置 Notion 连接器后，这里会显示一个轻量状态摘要。聊天区不再承担认证或来源维护。
            </p>
          </div>
        ) : null}

        {error ? (
          <div style={{ fontSize: '0.78rem', color: 'var(--color-state-error)' }}>
            {error}
          </div>
        ) : null}
      </div>

      <div style={{ padding: '0.9rem 1rem', borderTop: '1px solid var(--color-border-paper)', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          type="button"
          onClick={handleOpenSettings}
          disabled={!onOpenSettings}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.45rem',
            border: 'none',
            borderRadius: '999px',
            padding: '0.68rem 0.95rem',
            background: onOpenSettings ? 'var(--color-action-link)' : 'var(--color-disabled-bg)',
            color: 'var(--color-text-on-action)',
            fontSize: '0.82rem',
            fontWeight: 700,
            cursor: onOpenSettings ? 'pointer' : 'not-allowed',
            opacity: onOpenSettings ? 1 : 0.75,
          }}
        >
          去设置添加来源
          <IconChevronRight style={{ width: '0.9rem', height: '0.9rem' }} />
        </button>
      </div>
    </section>
  );
}
