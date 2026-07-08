// [Input] Resource connector API summary, ResourceConnectorPage page mode, and shared chat icons.
// [Output] Settings-owned Notion connector detail page matching the connector config sketch:
//          TopNavigation, ConnectorHeader, ConnectorOverviewSection, StrategySection,
//          ResourceSourceSection, and ConnectionStateCard while preserving the existing
//          ResourceConnectorPage auth/resource-selection/sync flow.
// [Pos] connector-notion-detail-page node in frontend/src/components/dashboard
// [Sync] 2026-07-08: initial dedicated navigation page for the Notion "具体配置页面", fixing the
//                    Settings 管理 action so it navigates to a new page instead of an inline toggle.
// [Sync] 2026-07-08: rebuild the page shell around the latest connector config sketch and keep
//                    ResourceConnectorPage as the single owner of Notion auth/resource business flow.
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  deleteConnector,
  listConnectors,
  type ResourceConnector,
} from '../../api/resourceConnectorApi';
import {
  IconChevronLeft,
  IconChevronRight,
  IconDatabase,
  IconFile,
  IconLoader,
  IconTrash,
} from '../chat/Icons';
import { SkeletonBar, SkeletonCircle } from '../chat/Skeleton';
import ResourceConnectorPage from './ResourceConnectorPage';

interface ConnectorNotionDetailPageProps {
  onBack: () => void;
  isMobile?: boolean;
}

type DetailTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

interface DetailStatus {
  label: string;
  tone: DetailTone;
  title: string;
  description: string;
  enabled: boolean;
}

function getDetailStatus(connector: ResourceConnector | null, loading: boolean): DetailStatus {
  if (loading) {
    return {
      label: '读取中',
      tone: 'info',
      title: '正在读取连接器状态',
      description: '页面结构已就绪，正在同步 Notion connector 的最新认证与来源摘要。',
      enabled: false,
    };
  }

  if (!connector) {
    return {
      label: '未认证',
      tone: 'warning',
      title: '当前 connector 尚未认证',
      description: '完成 Notion 授权后，系统会列出当前账号可访问的数据库和页面。',
      enabled: false,
    };
  }

  const status = connector.status;
  const authStatus = connector.auth.status;

  if (status === 'error' || authStatus === 'error') {
    return {
      label: '同步失败',
      tone: 'danger',
      title: '连接器状态异常',
      description: connector.auth.message || '认证或同步失败，请在资源选择工作台中重新认证或刷新来源。',
      enabled: false,
    };
  }

  if (authStatus === 'expired') {
    return {
      label: '未认证',
      tone: 'warning',
      title: 'Notion 授权已过期',
      description: '资源选择暂不可用，请重新完成 Notion 授权。',
      enabled: false,
    };
  }

  if (status === 'authenticating' || authStatus === 'authenticating') {
    return {
      label: '认证中',
      tone: 'info',
      title: '正在等待 Notion 授权确认',
      description: connector.auth.message || '打开 Notion 验证页完成确认后，页面会继续轮询认证结果。',
      enabled: false,
    };
  }

  if (status === 'syncing') {
    return {
      label: '同步中',
      tone: 'info',
      title: '正在同步 Notion 来源',
      description: '资源列表会在同步完成后更新，当前已选来源暂时保持可读。',
      enabled: true,
    };
  }

  if (status === 'authenticated' || status === 'synced' || authStatus === 'authenticated') {
    return {
      label: '已连接',
      tone: 'success',
      title: 'Notion 连接器已连接',
      description: `${connector.sources.length} 个来源已挂载，可在对话中作为资源上下文使用。`,
      enabled: true,
    };
  }

  return {
    label: '未认证',
    tone: 'warning',
    title: '当前 connector 尚未认证',
    description: '完成 Notion 授权后，资源选择和来源同步才会启用。',
    enabled: false,
  };
}

function toneStyles(tone: DetailTone) {
  switch (tone) {
    case 'success':
      return {
        border: 'color-mix(in srgb, var(--color-state-success) 32%, var(--color-border-paper))',
        background: 'color-mix(in srgb, var(--color-state-success) 14%, var(--color-bg-surface))',
        color: 'var(--color-state-success)',
      };
    case 'warning':
      return {
        border: 'color-mix(in srgb, var(--color-state-warning) 32%, var(--color-border-paper))',
        background: 'color-mix(in srgb, var(--color-state-warning) 14%, var(--color-bg-surface))',
        color: 'var(--color-state-warning)',
      };
    case 'danger':
      return {
        border: 'color-mix(in srgb, var(--color-state-error) 32%, var(--color-border-paper))',
        background: 'color-mix(in srgb, var(--color-state-error) 12%, var(--color-bg-surface))',
        color: 'var(--color-state-error)',
      };
    case 'info':
      return {
        border: 'color-mix(in srgb, var(--color-action-link) 28%, var(--color-border-paper))',
        background: 'color-mix(in srgb, var(--color-action-link) 10%, var(--color-bg-surface))',
        color: 'var(--color-action-link)',
      };
    default:
      return {
        border: 'var(--color-border-paper)',
        background: 'var(--color-bg-surface)',
        color: 'var(--color-text-secondary)',
      };
  }
}

function StatusPill({ status }: { status: DetailStatus }) {
  const palette = toneStyles(status.tone);
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        border: `1px solid ${palette.border}`,
        borderRadius: '999px',
        background: palette.background,
        color: palette.color,
        padding: '0.32rem 0.68rem',
        fontSize: '0.74rem',
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: '0.4rem',
          height: '0.4rem',
          borderRadius: '999px',
          background: palette.color,
        }}
      />
      {status.label}
    </span>
  );
}

function DetailSection({
  title,
  subtitle,
  badge,
  action,
  children,
}: {
  title: string;
  subtitle?: string;
  badge?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      style={{
        border: '1px solid var(--color-border-paper)',
        borderRadius: '1rem',
        background: 'var(--color-bg-surface)',
        boxShadow: '0 14px 34px var(--color-shadow-soft)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '1rem',
          padding: '1rem 1.1rem 0.85rem',
          borderBottom: '1px solid var(--color-border-paper)',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
            <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {title}
            </h2>
            {badge ? (
              <span
                style={{
                  border: '1px solid var(--color-border-paper)',
                  borderRadius: '999px',
                  padding: '0.22rem 0.5rem',
                  color: 'var(--color-text-muted)',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                }}
              >
                {badge}
              </span>
            ) : null}
          </div>
          {subtitle ? (
            <p style={{ margin: '0.32rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.82rem', lineHeight: 1.6 }}>
              {subtitle}
            </p>
          ) : null}
        </div>
        {action}
      </div>
      <div style={{ padding: '1rem 1.1rem 1.1rem' }}>{children}</div>
    </section>
  );
}

function OverviewRow({
  label,
  value,
  action,
}: {
  label: string;
  value: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '8rem minmax(0, 1fr) auto',
        alignItems: 'center',
        gap: '0.8rem',
        minHeight: '2.7rem',
        borderBottom: '1px solid color-mix(in srgb, var(--color-border-paper) 72%, transparent)',
      }}
    >
      <div style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem', fontWeight: 700 }}>{label}</div>
      <div style={{ minWidth: 0, color: 'var(--color-text-primary)', fontSize: '0.86rem', lineHeight: 1.5 }}>{value}</div>
      <div>{action}</div>
    </div>
  );
}

export default function ConnectorNotionDetailPage({ onBack, isMobile = false }: ConnectorNotionDetailPageProps) {
  const [connectors, setConnectors] = useState<ResourceConnector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const [workbenchKey, setWorkbenchKey] = useState(0);
  const workbenchRef = useRef<HTMLDivElement>(null);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await listConnectors();
      setConnectors(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : '连接器状态读取失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary, workbenchKey]);

  const notionConnector = useMemo(
    () => connectors.find((connector) => connector.platform === 'notion') ?? null,
    [connectors],
  );
  const detailStatus = getDetailStatus(notionConnector, loading);
  const statusPalette = toneStyles(detailStatus.tone);

  const scrollToWorkbench = useCallback(() => {
    workbenchRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const handleDisconnect = useCallback(async () => {
    if (!notionConnector || disconnecting) return;
    const ok = window.confirm('关闭 Notion 连接后，对话中将无法继续使用该连接器。是否继续？');
    if (!ok) return;

    setDisconnecting(true);
    setError(null);
    try {
      const deleted = await deleteConnector(notionConnector.id);
      if (deleted) {
        setWorkbenchKey((value) => value + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '关闭连接失败');
    } finally {
      setDisconnecting(false);
    }
  }, [disconnecting, notionConnector]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
      <nav
        aria-label="链接器具体配置页面导航"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.42rem',
          flexWrap: 'wrap',
          color: 'var(--color-text-secondary)',
          fontSize: '0.84rem',
        }}
      >
        <button
          type="button"
          onClick={onBack}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            border: '1px solid var(--color-border-paper)',
            borderRadius: '999px',
            padding: '0.48rem 0.82rem',
            background: 'var(--color-bg-paper)',
            color: 'var(--color-text-primary)',
            cursor: 'pointer',
            fontSize: '0.82rem',
            fontWeight: 700,
          }}
        >
          <IconChevronLeft style={{ width: '0.88rem', height: '0.88rem' }} />
          资源连接器
        </button>
        <IconChevronRight style={{ width: '0.78rem', height: '0.78rem', color: 'var(--color-text-muted)' }} />
        <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>Notion Connector</span>
      </nav>

      <section
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
          border: '1px solid var(--color-border-paper)',
          borderRadius: '1.15rem',
          background: 'var(--color-bg-paper)',
          boxShadow: '0 16px 36px var(--color-shadow-soft)',
          padding: isMobile ? '1rem' : '1.15rem 1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.85rem', minWidth: 0 }}>
          {loading ? (
            <SkeletonCircle size="2.7rem" />
          ) : (
            <span
              style={{
                width: '2.7rem',
                height: '2.7rem',
                flexShrink: 0,
                borderRadius: '0.9rem',
                border: '1px solid var(--color-border-paper)',
                background: 'color-mix(in srgb, var(--color-text-primary) 8%, var(--color-bg-surface))',
                display: 'grid',
                placeItems: 'center',
                color: 'var(--color-text-primary)',
              }}
            >
              <IconDatabase style={{ width: '1.15rem', height: '1.15rem' }} />
            </span>
          )}
          <div style={{ minWidth: 0 }}>
            {loading ? (
              <div style={{ display: 'grid', gap: '0.45rem', minWidth: '16rem' }}>
                <SkeletonBar width="15rem" height="1rem" />
                <SkeletonBar width="22rem" height="0.78rem" />
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                  <h1 style={{ margin: 0, fontSize: isMobile ? '1.25rem' : '1.45rem', lineHeight: 1.2, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                    Notion Resource Connector
                  </h1>
                  <StatusPill status={detailStatus} />
                </div>
                <p style={{ margin: '0.42rem 0 0', maxWidth: '42rem', color: 'var(--color-text-secondary)', fontSize: '0.86rem', lineHeight: 1.6 }}>
                  Notion 远程资源连接器说明：连接 Notion 数据库与页面，用于对话检索、上下文读取和来源同步。
                </p>
              </>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            disabled
            title="设计稿作为仓库文档维护，当前前端不发布该 PDF 静态资源。"
            style={{
              border: '1px solid var(--color-border-paper)',
              borderRadius: '999px',
              padding: '0.62rem 0.9rem',
              background: 'var(--color-bg-surface)',
              color: 'var(--color-text-muted)',
              cursor: 'not-allowed',
              fontSize: '0.82rem',
              fontWeight: 700,
            }}
          >
            查看设计稿
          </button>
          <button
            type="button"
            onClick={() => void handleDisconnect()}
            disabled={!notionConnector || disconnecting}
            style={{
              border: `1px solid ${statusPalette.border}`,
              borderRadius: '999px',
              padding: '0.62rem 0.9rem',
              background: statusPalette.background,
              color: statusPalette.color,
              cursor: !notionConnector || disconnecting ? 'not-allowed' : 'pointer',
              opacity: !notionConnector ? 0.62 : 1,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              fontSize: '0.82rem',
              fontWeight: 700,
            }}
          >
            {disconnecting ? <IconLoader style={{ width: '0.9rem', height: '0.9rem' }} /> : <IconTrash style={{ width: '0.9rem', height: '0.9rem' }} />}
            {disconnecting ? '关闭中' : '关闭连接'}
          </button>
        </div>
      </section>

      {error ? (
        <div
          style={{
            border: '1px solid color-mix(in srgb, var(--color-state-error) 30%, var(--color-border-paper))',
            borderRadius: '0.9rem',
            background: 'color-mix(in srgb, var(--color-state-error) 10%, var(--color-bg-paper))',
            color: 'var(--color-state-error)',
            padding: '0.75rem 0.9rem',
            fontSize: '0.84rem',
          }}
        >
          {error}
        </div>
      ) : null}

      <DetailSection title="连接器概览" subtitle="确认当前连接器身份、用途、认证状态和连接控制。">
        {loading ? (
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            <SkeletonBar width="100%" height="2.2rem" />
            <SkeletonBar width="92%" height="2.2rem" />
            <SkeletonBar width="88%" height="2.2rem" />
          </div>
        ) : (
          <div>
            <OverviewRow
              label="图标"
              value={
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                  <IconDatabase style={{ width: '0.95rem', height: '0.95rem' }} />
                  Notion Connector
                </span>
              }
            />
            <OverviewRow
              label="描述"
              value="连接 Notion 数据库、页面，用于对话与资源检索。"
            />
            <OverviewRow
              label="状态"
              value={<StatusPill status={detailStatus} />}
            />
            <OverviewRow
              label="设计稿"
              value="链接器概念的交互设计稿"
              action={<span style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem' }}>仓库文档</span>}
            />
            <OverviewRow
              label="连接控制"
              value={notionConnector ? '可关闭当前连接器；关闭后资源选择与同步不可用。' : '尚未创建连接器，请先在下方工作台创建并认证。'}
              action={
                <button
                  type="button"
                  onClick={notionConnector ? () => void handleDisconnect() : scrollToWorkbench}
                  disabled={disconnecting}
                  style={{
                    border: '1px solid var(--color-border-paper)',
                    borderRadius: '999px',
                    background: 'var(--color-bg-paper)',
                    color: 'var(--color-text-primary)',
                    padding: '0.45rem 0.7rem',
                    cursor: disconnecting ? 'not-allowed' : 'pointer',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {notionConnector ? '关闭连接' : '添加连接器'}
                </button>
              }
            />
          </div>
        )}
      </DetailSection>

      <DetailSection
        title="策略设计"
        badge="暂不实现"
        subtitle="当前版本暂不开放策略配置，避免在可用能力之外制造复杂表单。"
      >
        <div
          style={{
            border: '1px dashed var(--color-border-paper)',
            borderRadius: '0.9rem',
            background: 'var(--color-bg-paper)',
            color: 'var(--color-text-secondary)',
            padding: '0.95rem 1rem',
            fontSize: '0.84rem',
            lineHeight: 1.65,
          }}
        >
          后续可支持默认同步范围、权限规则、索引策略和更新频率。本期只保留说明型占位，不提供不可用配置控件。
        </div>
      </DetailSection>

      <DetailSection
        title="资源选择 / 来源列表"
        subtitle="完成 Notion 授权后，在这里选择数据库和页面，并查看已挂载来源。"
        action={
          <button
            type="button"
            onClick={scrollToWorkbench}
            style={{
              border: '1px solid var(--color-border-paper)',
              borderRadius: '999px',
              background: 'var(--color-bg-paper)',
              color: 'var(--color-text-primary)',
              padding: '0.55rem 0.8rem',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.42rem',
              fontSize: '0.8rem',
              fontWeight: 700,
              whiteSpace: 'nowrap',
            }}
          >
            <IconFile style={{ width: '0.88rem', height: '0.88rem' }} />
            添加
          </button>
        }
      >
        {!detailStatus.enabled ? (
          <div
            style={{
              border: '1px dashed var(--color-border-paper)',
              borderRadius: '0.9rem',
              background: 'var(--color-bg-paper)',
              color: 'var(--color-text-secondary)',
              padding: '0.95rem 1rem',
              marginBottom: '1rem',
              fontSize: '0.84rem',
              lineHeight: 1.65,
              textAlign: 'center',
            }}
          >
            当前未认证，资源选择不可用。请先在下方工作台完成 Notion 授权。
          </div>
        ) : null}

        <div ref={workbenchRef}>
          <ResourceConnectorPage key={workbenchKey} isMobile={isMobile} />
        </div>
      </DetailSection>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'minmax(0, 1fr) auto',
          alignItems: 'center',
          gap: '1rem',
          border: `1px solid ${statusPalette.border}`,
          borderRadius: '1rem',
          background: statusPalette.background,
          padding: '1rem 1.1rem',
          color: 'var(--color-text-primary)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.8rem', minWidth: 0 }}>
          <span
            aria-hidden="true"
            style={{
              width: '2rem',
              height: '2rem',
              flexShrink: 0,
              borderRadius: '0.7rem',
              border: `1px solid ${statusPalette.border}`,
              display: 'grid',
              placeItems: 'center',
              color: statusPalette.color,
              fontWeight: 800,
            }}
          >
            !
          </span>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
              <h2 style={{ margin: 0, color: 'var(--color-text-primary)', fontSize: '0.98rem', fontWeight: 700 }}>
                授权 / 同步状态
              </h2>
              <StatusPill status={detailStatus} />
            </div>
            <p style={{ margin: '0.35rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.84rem', lineHeight: 1.65 }}>
              {detailStatus.title}。{detailStatus.description}
            </p>
          </div>
        </div>

        <button
          type="button"
          aria-pressed={detailStatus.enabled}
          disabled
          title="该开关展示连接器可用状态，实际开启需完成 Notion 认证。"
          style={{
            width: '3.2rem',
            height: '1.8rem',
            borderRadius: '999px',
            border: `1px solid ${statusPalette.border}`,
            background: detailStatus.enabled ? statusPalette.color : 'var(--color-disabled-bg)',
            padding: '0.18rem',
            opacity: 0.88,
            cursor: 'not-allowed',
          }}
        >
          <span
            style={{
              display: 'block',
              width: '1.35rem',
              height: '1.35rem',
              borderRadius: '999px',
              background: 'var(--color-bg-paper)',
              transform: detailStatus.enabled ? 'translateX(1.35rem)' : 'translateX(0)',
              transition: 'transform 0.18s ease',
            }}
          />
        </button>
      </section>
    </div>
  );
}
