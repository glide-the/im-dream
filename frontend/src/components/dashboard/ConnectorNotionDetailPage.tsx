// [Input] Notion resource connector API helpers, Settings navigation callback, and shared chat icons.
// [Output] Settings-owned single-account Notion resource configuration page.
// [Pos] connector-notion-detail-page node in frontend/src/components/dashboard
// [Sync] 2026-07-08: initial dedicated navigation page for the Notion "具体配置页面", fixing the
//                    Settings 管理 action so it navigates to a new page instead of an inline toggle.
// [Sync] 2026-07-08: rebuild the page shell around the latest connector config sketch.
// [Sync] 2026-07-08: refactor Settings detail into a single-platform/single-account page with
//                    local auth/resource/sync UI and no collection workbench chrome.
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  createConnector,
  deleteConnector,
  listConnectorDatabases,
  listConnectorPages,
  listConnectors,
  pollConnectorAuth,
  refreshConnectorSources,
  selectConnectorResources,
  startConnectorAuth,
  type ConnectorAuthStatus,
  type ConnectorResourceSelection,
  type ConnectorSource,
  type ConnectorStatus,
  type NotionResourceOption,
  type ResourceConnector,
} from '../../api/resourceConnectorApi';
import {
  IconArrowUp,
  IconCheck,
  IconChevronLeft,
  IconChevronRight,
  IconDatabase,
  IconFile,
  IconLoader,
  IconShare,
  IconTrash,
} from '../chat/Icons';
import { SkeletonBar, SkeletonCircle, SkeletonList } from '../chat/Skeleton';

interface ConnectorNotionDetailPageProps {
  onBack: () => void;
  isMobile?: boolean;
}

const RESOURCE_PAGE_SIZE = 10;

type DetailTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

interface DetailStatus {
  label: string;
  tone: DetailTone;
  title: string;
  description: string;
  enabled: boolean;
}

const DEFAULT_NOTION_CONNECTOR_NAME = 'Notion Resource Connector';

type UnifiedResourceKind = 'database' | 'page';

interface UnifiedResourceOption extends NotionResourceOption {
  kind: UnifiedResourceKind;
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function formatDateTime(value?: string): string {
  if (!value) return '未更新';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function formatStatusLabel(
  status?: ConnectorStatus | ConnectorSource['status'] | ConnectorAuthStatus | 'idle',
): string {
  switch (status) {
    case 'authenticating':
      return '认证中';
    case 'authenticated':
      return '已认证';
    case 'syncing':
      return '同步中';
    case 'synced':
      return '已同步';
    case 'expired':
      return '已过期';
    case 'error':
      return '错误';
    case 'draft':
      return '待连接';
    default:
      return '待处理';
  }
}

function getDetailStatus(connector: ResourceConnector | null, loading: boolean): DetailStatus {
  if (loading) {
    return {
      label: '读取中',
      tone: 'info',
      title: '正在读取 Notion 账号状态',
      description: '页面结构已就绪，正在同步 Notion connector 的认证、资源和同步摘要。',
      enabled: false,
    };
  }

  if (!connector) {
    return {
      label: '未认证',
      tone: 'warning',
      title: '尚未连接 Notion 账号',
      description: '同一平台只允许认证一个账号。连接后可选择这个账号下允许 Chat 使用的数据库和页面。',
      enabled: false,
    };
  }

  if (connector.status === 'error' || connector.auth.status === 'error') {
    return {
      label: '同步失败',
      tone: 'danger',
      title: 'Notion 连接器状态异常',
      description: connector.auth.message || '认证或同步失败，请重新连接 Notion 或刷新同步。',
      enabled: false,
    };
  }

  if (connector.auth.status === 'expired') {
    return {
      label: '已过期',
      tone: 'warning',
      title: 'Notion 授权已过期',
      description: '当前账号授权不可继续使用，请重新连接 Notion。',
      enabled: false,
    };
  }

  if (connector.status === 'authenticating' || connector.auth.status === 'authenticating') {
    return {
      label: '认证中',
      tone: 'info',
      title: '正在等待 Notion 授权确认',
      description: connector.auth.message || '打开 Notion 验证页完成确认后，页面会自动轮询认证结果。',
      enabled: false,
    };
  }

  if (connector.status === 'syncing') {
    return {
      label: '同步中',
      tone: 'info',
      title: '正在同步 Notion 来源',
      description: '资源列表会在同步完成后更新，当前已选来源暂时保持可读。',
      enabled: true,
    };
  }

  if (connector.auth.status === 'authenticated' || connector.status === 'authenticated' || connector.status === 'synced') {
    return {
      label: '已连接',
      tone: 'success',
      title: 'Notion 账号已连接',
      description: `${connector.sources.length} 个来源已挂载，可在对话中作为资源上下文使用。`,
      enabled: true,
    };
  }

  return {
    label: '未认证',
    tone: 'warning',
    title: '尚未完成 Notion 授权',
    description: '完成授权后，资源选择和来源同步才会启用。',
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

function buildSelectionFromSources(sources: ConnectorSource[]): ConnectorResourceSelection {
  return {
    databaseIds: sources.filter((source) => source.type === 'notion_database').map((source) => source.id),
    pageIds: sources.filter((source) => source.type === 'notion_page').map((source) => source.id),
  };
}

function buildSelectedSources(
  databaseOptions: NotionResourceOption[],
  pageOptions: NotionResourceOption[],
  databaseIds: string[],
  pageIds: string[],
  existingSources: ConnectorSource[] = [],
): ConnectorSource[] {
  const now = new Date().toISOString();
  const existingById = new Map(existingSources.map((source) => [source.id, source]));
  const databaseById = new Map(databaseOptions.map((option) => [option.id, option]));
  const pageById = new Map(pageOptions.map((option) => [option.id, option]));

  const databases = databaseIds.map((id): ConnectorSource => {
    const option = databaseById.get(id);
    const existing = existingById.get(id);
    return {
      id,
      title: option?.title || existing?.title || 'Untitled database',
      type: 'notion_database',
      status: existing?.status === 'error' ? 'error' : 'synced',
      updatedAt: existing?.updatedAt || now,
      syncedAt: existing?.syncedAt || now,
      pageCount: option?.pageCount ?? existing?.pageCount,
      description: option?.subtitle || existing?.description || 'Notion data source',
      url: existing?.url,
    };
  });

  const pages = pageIds.map((id): ConnectorSource => {
    const option = pageById.get(id);
    const existing = existingById.get(id);
    return {
      id,
      title: option?.title || existing?.title || 'Untitled page',
      type: 'notion_page',
      status: existing?.status === 'error' ? 'error' : 'synced',
      updatedAt: existing?.updatedAt || now,
      syncedAt: existing?.syncedAt || now,
      description: option?.subtitle || existing?.description || 'Standalone page',
      url: existing?.url,
    };
  });

  return [...databases, ...pages];
}

function resolveSingleNotionConnector(connectors: ResourceConnector[]): ResourceConnector | null {
  const notionConnectors = connectors.filter((connector) => connector.platform === 'notion');
  if (notionConnectors.length === 0) return null;
  return notionConnectors.slice().sort((a, b) => {
    const aTime = new Date(a.updatedAt || a.createdAt).getTime();
    const bTime = new Date(b.updatedAt || b.createdAt).getTime();
    return bTime - aTime;
  })[0];
}

function sourceKindLabel(type: ConnectorSource['type']): string {
  return type === 'notion_database' ? 'Database' : 'Page';
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

function InlineStatusPill({
  label,
  tone,
}: {
  label: string;
  tone: DetailTone;
}) {
  const palette = toneStyles(tone);
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        border: `1px solid ${palette.border}`,
        borderRadius: '999px',
        background: palette.background,
        color: palette.color,
        padding: '0.24rem 0.58rem',
        fontSize: '0.72rem',
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}

function DetailSection({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle?: string;
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
          flexWrap: 'wrap',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            {title}
          </h2>
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

function MetricCard({
  label,
  value,
  helper,
}: {
  label: string;
  value: ReactNode;
  helper?: string;
}) {
  return (
    <div
      style={{
        border: '1px solid var(--color-border-paper)',
        borderRadius: '0.85rem',
        background: 'var(--color-bg-paper)',
        padding: '0.9rem',
        minWidth: 0,
      }}
    >
      <div style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {label}
      </div>
      <div style={{ marginTop: '0.42rem', color: 'var(--color-text-primary)', fontSize: '1rem', lineHeight: 1.35, fontWeight: 700 }}>
        {value}
      </div>
      {helper ? (
        <p style={{ margin: '0.32rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.76rem', lineHeight: 1.5 }}>
          {helper}
        </p>
      ) : null}
    </div>
  );
}

function ResourceOptionRow({
  option,
  checked,
  onToggle,
  disabled,
  type,
}: {
  option: NotionResourceOption;
  checked: boolean;
  onToggle: () => void;
  disabled?: boolean;
  type: 'database' | 'page';
}) {
  const Icon = type === 'database' ? IconDatabase : IconFile;
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.8rem',
        border: '1px solid var(--color-border-paper)',
        borderRadius: '0.9rem',
        background: checked ? 'var(--color-bg-surface-solid)' : 'var(--color-bg-paper)',
        color: 'var(--color-text-primary)',
        padding: '0.82rem 0.9rem',
        textAlign: 'left',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.62 : 1,
        boxShadow: checked ? '0 10px 24px var(--color-shadow-soft)' : 'none',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: '1.25rem',
          height: '1.25rem',
          marginTop: '0.12rem',
          borderRadius: '0.38rem',
          border: '1px solid var(--color-border-paper)',
          background: checked ? 'var(--color-text-primary)' : 'var(--color-bg-surface)',
          color: checked ? 'var(--color-text-on-action)' : 'var(--color-text-muted)',
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
        }}
      >
        {checked ? <IconCheck style={{ width: '0.75rem', height: '0.75rem' }} /> : <Icon style={{ width: '0.75rem', height: '0.75rem' }} />}
      </span>
      <span style={{ minWidth: 0, flex: 1 }}>
          <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.8rem' }}>
            <span style={{ fontSize: '0.88rem', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {option.title}
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', flexShrink: 0 }}>
              <InlineStatusPill label={type === 'database' ? 'Data source' : 'Page'} tone="neutral" />
              {typeof option.pageCount === 'number' ? (
                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>
                  {option.pageCount} pages
                </span>
              ) : null}
            </span>
          </span>
        <span style={{ display: 'block', marginTop: '0.28rem', color: 'var(--color-text-secondary)', fontSize: '0.76rem', lineHeight: 1.45 }}>
          {option.subtitle || (type === 'database' ? 'Notion database' : 'Standalone page')}
        </span>
      </span>
    </button>
  );
}

function SourceCard({ source }: { source: ConnectorSource }) {
  const Icon = source.type === 'notion_database' ? IconDatabase : IconFile;
  const tone: DetailTone = source.status === 'synced'
    ? 'success'
    : source.status === 'syncing'
      ? 'info'
      : source.status === 'error'
        ? 'danger'
        : 'neutral';

  return (
    <article
      style={{
        border: '1px solid var(--color-border-paper)',
        borderRadius: '0.9rem',
        background: 'var(--color-bg-paper)',
        padding: '0.9rem',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: '0.9rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', minWidth: 0 }}>
        <span
          aria-hidden="true"
          style={{
            width: '2.2rem',
            height: '2.2rem',
            borderRadius: '0.75rem',
            border: '1px solid var(--color-border-paper)',
            background: 'var(--color-bg-surface)',
            color: 'var(--color-text-primary)',
            display: 'grid',
            placeItems: 'center',
            flexShrink: 0,
          }}
        >
          <Icon style={{ width: '0.95rem', height: '0.95rem' }} />
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0, color: 'var(--color-text-primary)', fontSize: '0.9rem', lineHeight: 1.35, fontWeight: 700 }}>
              {source.title}
            </h3>
            <InlineStatusPill label={formatStatusLabel(source.status)} tone={tone} />
          </div>
          <p style={{ margin: '0.32rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.76rem', lineHeight: 1.5 }}>
            {sourceKindLabel(source.type)}
            {source.description ? ` · ${source.description}` : ''}
          </p>
        </div>
      </div>
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        {typeof source.pageCount === 'number' ? (
          <div style={{ color: 'var(--color-text-primary)', fontSize: '0.78rem', fontWeight: 700 }}>{source.pageCount} pages</div>
        ) : null}
        <div style={{ marginTop: '0.3rem', color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>
          {formatDateTime(source.syncedAt || source.updatedAt)}
        </div>
      </div>
    </article>
  );
}

function EmptyPanel({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div
      style={{
        border: '1px dashed var(--color-border-paper)',
        borderRadius: '0.95rem',
        background: 'var(--color-bg-paper)',
        color: 'var(--color-text-secondary)',
        padding: '1rem',
        textAlign: 'center',
        lineHeight: 1.65,
      }}
    >
      <div style={{ color: 'var(--color-text-primary)', fontWeight: 700, fontSize: '0.92rem' }}>{title}</div>
      <div style={{ margin: '0.38rem auto 0', maxWidth: '38rem', fontSize: '0.84rem' }}>{children}</div>
      {action ? <div style={{ marginTop: '0.9rem' }}>{action}</div> : null}
    </div>
  );
}

export default function ConnectorNotionDetailPage({ onBack, isMobile = false }: ConnectorNotionDetailPageProps) {
  const [connector, setConnector] = useState<ResourceConnector | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [resourceSaving, setResourceSaving] = useState(false);
  const [databaseOptions, setDatabaseOptions] = useState<NotionResourceOption[]>([]);
  const [pageOptions, setPageOptions] = useState<NotionResourceOption[]>([]);
  const [selectedDatabaseIds, setSelectedDatabaseIds] = useState<string[]>([]);
  const [selectedPageIds, setSelectedPageIds] = useState<string[]>([]);
  const [resourceSearchQuery, setResourceSearchQuery] = useState('');
  const [resourcePage, setResourcePage] = useState(1);

  const detailStatus = getDetailStatus(connector, loading);
  const statusPalette = toneStyles(detailStatus.tone);
  const connectorId = connector?.id ?? null;
  const connectorAuthStatus = connector?.auth.status ?? 'idle';
  const canEditResources = connectorAuthStatus === 'authenticated';
  const sourceSelection = useMemo(
    () => buildSelectionFromSources(connector?.sources ?? []),
    [connector?.sources],
  );
  const sourceStats = useMemo(() => {
    const sources = connector?.sources ?? [];
    const databases = sources.filter((source) => source.type === 'notion_database').length;
    return {
      total: sources.length,
      databases,
      pages: sources.length - databases,
    };
  }, [connector?.sources]);
  const unifiedResourceOptions = useMemo<UnifiedResourceOption[]>(
    () => [
      ...databaseOptions.map((option) => ({ ...option, kind: 'database' as const })),
      ...pageOptions.map((option) => ({ ...option, kind: 'page' as const })),
    ],
    [databaseOptions, pageOptions],
  );
  const filteredResourceOptions = useMemo(() => {
    const query = resourceSearchQuery.trim().toLowerCase();
    if (!query) return unifiedResourceOptions;
    return unifiedResourceOptions.filter((option) => {
      const haystack = `${option.title} ${option.subtitle ?? ''} ${option.kind}`.toLowerCase();
      return haystack.includes(query);
    });
  }, [resourceSearchQuery, unifiedResourceOptions]);
  const totalResourcePages = Math.max(1, Math.ceil(filteredResourceOptions.length / RESOURCE_PAGE_SIZE));
  const visibleResourceOptions = useMemo(() => {
    const start = (resourcePage - 1) * RESOURCE_PAGE_SIZE;
    return filteredResourceOptions.slice(start, start + RESOURCE_PAGE_SIZE);
  }, [filteredResourceOptions, resourcePage]);
  const selectedResourceCount = selectedDatabaseIds.length + selectedPageIds.length;

  const upsertConnector = useCallback((nextConnector: ResourceConnector) => {
    setConnector(nextConnector);
    setPageError(null);
  }, []);

  const resetResourceState = useCallback(() => {
    setDatabaseOptions([]);
    setPageOptions([]);
    setSelectedDatabaseIds([]);
    setSelectedPageIds([]);
    setResourceSearchQuery('');
    setResourcePage(1);
    setResourceError(null);
    setResourceLoading(false);
  }, []);

  const loadConnector = useCallback(async () => {
    setLoading(true);
    setPageError(null);
    try {
      const items = await listConnectors();
      const nextConnector = resolveSingleNotionConnector(items);
      setConnector(nextConnector);
    } catch (error) {
      setPageError(getErrorMessage(error, 'Notion 连接器状态读取失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadConnector();
  }, [loadConnector]);

  useEffect(() => {
    if (!connectorId || connectorAuthStatus !== 'authenticated') {
      resetResourceState();
      return undefined;
    }

    let active = true;
    setResourceLoading(true);
    setResourceError(null);

    void (async () => {
      try {
        const [databases, pages] = await Promise.all([
          listConnectorDatabases(connectorId),
          listConnectorPages(connectorId),
        ]);
        if (!active) return;

        setDatabaseOptions(databases);
        setPageOptions(pages);
        setSelectedDatabaseIds(sourceSelection.databaseIds);
        setSelectedPageIds(sourceSelection.pageIds);
      } catch (error) {
        if (!active) return;
        setResourceError(getErrorMessage(error, '资源列表加载失败'));
        setDatabaseOptions([]);
        setPageOptions([]);
      } finally {
        if (active) {
          setResourceLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [connectorAuthStatus, connectorId, resetResourceState, sourceSelection]);

  useEffect(() => {
    setResourcePage(1);
  }, [resourceSearchQuery]);

  useEffect(() => {
    setResourcePage((current) => Math.min(current, totalResourcePages));
  }, [totalResourcePages]);

  useEffect(() => {
    if (!connectorId || connectorAuthStatus !== 'authenticating') {
      return undefined;
    }

    let active = true;
    const poll = async () => {
      if (!active) return;
      try {
        const next = await pollConnectorAuth(connectorId);
        if (active && next) {
          upsertConnector(next);
        }
      } catch (error) {
        if (active) {
          setResourceError(getErrorMessage(error, '认证轮询失败'));
        }
      }
    };

    void poll();
    const intervalId = window.setInterval(() => {
      void poll();
    }, 3500);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, [connectorAuthStatus, connectorId, upsertConnector]);

  const ensureSingleConnector = useCallback(async () => {
    if (connector) return connector;

    const items = await listConnectors();
    const existingConnector = resolveSingleNotionConnector(items);
    if (existingConnector) {
      upsertConnector(existingConnector);
      return existingConnector;
    }

    const nextConnector = await createConnector({
      name: DEFAULT_NOTION_CONNECTOR_NAME,
      platform: 'notion',
    });
    upsertConnector(nextConnector);
    return nextConnector;
  }, [connector, upsertConnector]);

  const handleStartAuth = useCallback(async () => {
    if (connecting) return;
    setConnecting(true);
    setPageError(null);
    setResourceError(null);
    try {
      const targetConnector = await ensureSingleConnector();
      const nextConnector = await startConnectorAuth(targetConnector.id);
      if (nextConnector) {
        upsertConnector(nextConnector);
      }
    } catch (error) {
      setPageError(getErrorMessage(error, '启动 Notion 认证失败'));
    } finally {
      setConnecting(false);
    }
  }, [connecting, ensureSingleConnector, upsertConnector]);

  const handleSaveResources = useCallback(async () => {
    if (!connectorId || !canEditResources || resourceSaving) return;
    setResourceSaving(true);
    setResourceError(null);
    try {
      const nextConnector = await selectConnectorResources(connectorId, {
        databaseIds: selectedDatabaseIds,
        pageIds: selectedPageIds,
      });
      const selectedSources = buildSelectedSources(
        databaseOptions,
        pageOptions,
        selectedDatabaseIds,
        selectedPageIds,
        connector?.sources ?? [],
      );
      const now = new Date().toISOString();
      if (nextConnector) {
        upsertConnector({
          ...nextConnector,
          status: selectedSources.length > 0 ? 'synced' : nextConnector.status,
          updatedAt: now,
          lastSyncedAt: selectedSources.length > 0 ? now : nextConnector.lastSyncedAt,
          sources: nextConnector.sources.length > 0 || selectedSources.length === 0
            ? nextConnector.sources
            : selectedSources,
        });
      } else if (connector) {
        upsertConnector({
          ...connector,
          status: selectedSources.length > 0 ? 'synced' : connector.status,
          updatedAt: now,
          lastSyncedAt: selectedSources.length > 0 ? now : connector.lastSyncedAt,
          sources: selectedSources,
        });
      }
    } catch (error) {
      setResourceError(getErrorMessage(error, '保存资源选择失败'));
    } finally {
      setResourceSaving(false);
    }
  }, [canEditResources, connector, connectorId, databaseOptions, pageOptions, resourceSaving, selectedDatabaseIds, selectedPageIds, upsertConnector]);

  const handleSyncSources = useCallback(async () => {
    if (!connectorId || !canEditResources || syncLoading) return;
    setSyncLoading(true);
    setResourceError(null);
    try {
      const nextConnector = await refreshConnectorSources(connectorId);
      if (nextConnector) {
        upsertConnector(nextConnector);
      }
    } catch (error) {
      setResourceError(getErrorMessage(error, '刷新同步失败'));
    } finally {
      setSyncLoading(false);
    }
  }, [canEditResources, connectorId, syncLoading, upsertConnector]);

  const handleDisconnect = useCallback(async () => {
    if (!connectorId || disconnecting) return;
    const ok = window.confirm('关闭 Notion 账号连接后，Chat 将无法继续使用该平台资源。是否继续？');
    if (!ok) return;

    setDisconnecting(true);
    setPageError(null);
    setResourceError(null);
    try {
      const deleted = await deleteConnector(connectorId);
      if (deleted) {
        setConnector(null);
        resetResourceState();
      }
    } catch (error) {
      setPageError(getErrorMessage(error, '关闭 Notion 连接失败'));
    } finally {
      setDisconnecting(false);
    }
  }, [connectorId, disconnecting, resetResourceState]);

  const authActionLabel = connectorAuthStatus === 'authenticated'
    ? '重新连接 Notion'
    : connectorAuthStatus === 'authenticating'
      ? '认证进行中'
      : '连接 Notion';

  const actionButtonStyle = {
    border: 'none',
    borderRadius: '999px',
    padding: '0.68rem 0.95rem',
    background: 'var(--color-text-primary)',
    color: 'var(--color-text-on-action)',
    cursor: connecting || connectorAuthStatus === 'authenticating' ? 'not-allowed' : 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.48rem',
    fontSize: '0.84rem',
    fontWeight: 700,
    boxShadow: '0 12px 26px var(--color-shadow-medium)',
    opacity: connecting || connectorAuthStatus === 'authenticating' ? 0.66 : 1,
  } as const;

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
                <p style={{ margin: '0.42rem 0 0', maxWidth: '46rem', color: 'var(--color-text-secondary)', fontSize: '0.86rem', lineHeight: 1.6 }}>
                  单平台单账号配置页：这里管理当前用户唯一的 Notion 账号授权、资源范围和同步状态。
                </p>
              </>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => void handleStartAuth()}
            disabled={connecting || connectorAuthStatus === 'authenticating'}
            style={actionButtonStyle}
          >
            {connecting ? <IconLoader style={{ width: '0.9rem', height: '0.9rem' }} /> : <IconShare style={{ width: '0.9rem', height: '0.9rem' }} />}
            {connecting ? '连接中' : authActionLabel}
          </button>
          <button
            type="button"
            onClick={() => void handleDisconnect()}
            disabled={!connectorId || disconnecting}
            style={{
              border: `1px solid ${statusPalette.border}`,
              borderRadius: '999px',
              padding: '0.66rem 0.92rem',
              background: statusPalette.background,
              color: statusPalette.color,
              cursor: !connectorId || disconnecting ? 'not-allowed' : 'pointer',
              opacity: !connectorId ? 0.62 : 1,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              fontSize: '0.84rem',
              fontWeight: 700,
            }}
          >
            {disconnecting ? <IconLoader style={{ width: '0.9rem', height: '0.9rem' }} /> : <IconTrash style={{ width: '0.9rem', height: '0.9rem' }} />}
            {disconnecting ? '关闭中' : '关闭连接'}
          </button>
        </div>
      </section>

      {pageError ? (
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
          {pageError}
        </div>
      ) : null}

      <DetailSection
        title="Notion Resource Connector"
        subtitle="账号状态、授权状态、资源数量和最近同步集中在这里；不再展示连接器集合列表。"
      >
        {loading ? (
          <SkeletonList rows={3} />
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : 'repeat(4, minmax(0, 1fr))',
                gap: '0.75rem',
              }}
            >
              <MetricCard label="账号模型" value="Notion 单账号" helper="同一平台只保留一个认证账号。" />
              <MetricCard label="授权状态" value={formatStatusLabel(connectorAuthStatus)} helper={connector?.auth.message || detailStatus.title} />
              <MetricCard label="挂载来源" value={`${sourceStats.total}`} helper={`${sourceStats.databases} databases · ${sourceStats.pages} pages`} />
              <MetricCard label="最近同步" value={formatDateTime(connector?.lastSyncedAt || connector?.updatedAt)} helper="用于 Chat 上下文读取。" />
            </div>

            {!connector || connectorAuthStatus === 'idle' || connectorAuthStatus === 'expired' || connectorAuthStatus === 'error' ? (
              <EmptyPanel
                title="连接 Notion 账号后才能选择资源"
                action={
                  <button
                    type="button"
                    onClick={() => void handleStartAuth()}
                    disabled={connecting}
                    style={actionButtonStyle}
                  >
                    {connecting ? <IconLoader style={{ width: '0.9rem', height: '0.9rem' }} /> : <IconShare style={{ width: '0.9rem', height: '0.9rem' }} />}
                    {connecting ? '连接中' : '连接 Notion'}
                  </button>
                }
              >
                页面会自动创建或复用当前用户唯一的 Notion connector，然后进入认证流程。
              </EmptyPanel>
            ) : null}

            {connector && connectorAuthStatus === 'authenticating' ? (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: isMobile ? '1fr' : '1.1fr 0.9fr',
                  gap: '0.85rem',
                }}
              >
                <div
                  style={{
                    border: '1px solid var(--color-border-paper)',
                    borderRadius: '0.9rem',
                    background: 'var(--color-bg-paper)',
                    padding: '0.95rem 1rem',
                  }}
                >
                  <div style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                    Verification code
                  </div>
                  <div
                    style={{
                      marginTop: '0.55rem',
                      color: 'var(--color-text-primary)',
                      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                      fontSize: '1.22rem',
                      fontWeight: 800,
                      letterSpacing: '0.08em',
                    }}
                  >
                    {connector.auth.verificationCode || '等待生成'}
                  </div>
                  <p style={{ margin: '0.55rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.82rem', lineHeight: 1.6 }}>
                    {connector.auth.message || '在 Notion 中确认访问权限，页面会自动轮询结果。'}
                  </p>
                </div>
                <div
                  style={{
                    border: '1px solid var(--color-border-paper)',
                    borderRadius: '0.9rem',
                    background: 'var(--color-bg-paper)',
                    padding: '0.95rem 1rem',
                  }}
                >
                  <div style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                    Browser step
                  </div>
                  <p style={{ margin: '0.55rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.82rem', lineHeight: 1.6 }}>
                    打开 Notion 验证页确认授权。认证完成后，本页会显示可选择的数据库和页面。
                  </p>
                  {connector.auth.verificationUrl ? (
                    <a
                      href={connector.auth.verificationUrl}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.45rem',
                        marginTop: '0.8rem',
                        color: 'var(--color-text-primary)',
                        fontSize: '0.84rem',
                        fontWeight: 700,
                        textDecoration: 'none',
                      }}
                    >
                      <IconShare style={{ width: '0.9rem', height: '0.9rem' }} />
                      打开 Notion 验证页
                    </a>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        )}
      </DetailSection>

      <DetailSection
        title="资源范围"
        subtitle="选择这个 Notion 账号授权给 Chat 使用的数据库和页面。"
        action={
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <input
              type="search"
              value={resourceSearchQuery}
              onChange={(event) => setResourceSearchQuery(event.target.value)}
              placeholder="搜索资源"
              aria-label="搜索 Notion 资源"
              disabled={!canEditResources}
              style={{
                width: isMobile ? '100%' : '13.5rem',
                border: '1px solid var(--color-border-paper)',
                borderRadius: '999px',
                background: 'var(--color-bg-paper)',
                color: 'var(--color-text-primary)',
                padding: '0.58rem 0.82rem',
                outline: 'none',
                fontSize: '0.8rem',
                opacity: canEditResources ? 1 : 0.62,
              }}
            />
            <button
              type="button"
              onClick={() => void handleSaveResources()}
              disabled={!canEditResources || resourceSaving}
              style={{
                border: 'none',
                borderRadius: '999px',
                padding: '0.58rem 0.82rem',
                background: 'var(--color-text-primary)',
                color: 'var(--color-text-on-action)',
                cursor: !canEditResources || resourceSaving ? 'not-allowed' : 'pointer',
                opacity: !canEditResources || resourceSaving ? 0.62 : 1,
                fontSize: '0.8rem',
                fontWeight: 700,
              }}
            >
              {resourceSaving ? '保存中' : '保存资源'}
            </button>
            <button
              type="button"
              onClick={() => void handleSyncSources()}
              disabled={!canEditResources || syncLoading}
              style={{
                border: '1px solid var(--color-border-paper)',
                borderRadius: '999px',
                padding: '0.56rem 0.78rem',
                background: 'var(--color-bg-paper)',
                color: 'var(--color-text-primary)',
                cursor: !canEditResources || syncLoading ? 'not-allowed' : 'pointer',
                opacity: !canEditResources || syncLoading ? 0.62 : 1,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.42rem',
                fontSize: '0.8rem',
                fontWeight: 700,
              }}
            >
              {syncLoading ? <IconLoader style={{ width: '0.86rem', height: '0.86rem' }} /> : <IconArrowUp style={{ width: '0.86rem', height: '0.86rem' }} />}
              {syncLoading ? '同步中' : '刷新同步'}
            </button>
          </div>
        }
      >
        {!canEditResources ? (
          <EmptyPanel
            title="资源选择暂不可用"
            action={
              <button
                type="button"
                onClick={() => void handleStartAuth()}
                disabled={connecting || connectorAuthStatus === 'authenticating'}
                style={actionButtonStyle}
              >
                {connecting ? <IconLoader style={{ width: '0.9rem', height: '0.9rem' }} /> : <IconShare style={{ width: '0.9rem', height: '0.9rem' }} />}
                {connecting ? '连接中' : authActionLabel}
              </button>
            }
          >
            完成 Notion 授权后，这里会列出可访问的 databases 和 standalone pages；当前只管理 Notion 这一个平台账号。
          </EmptyPanel>
        ) : resourceLoading ? (
          <SkeletonList rows={4} />
        ) : resourceError ? (
          <div
            style={{
              border: '1px solid color-mix(in srgb, var(--color-state-error) 34%, var(--color-border-paper))',
              borderRadius: '0.9rem',
              background: 'color-mix(in srgb, var(--color-state-error) 12%, var(--color-bg-paper))',
              padding: '0.9rem 1rem',
              color: 'var(--color-state-error)',
              fontSize: '0.84rem',
              lineHeight: 1.6,
            }}
          >
            {resourceError}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '0.85rem' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.75rem',
                flexWrap: 'wrap',
                color: 'var(--color-text-secondary)',
                fontSize: '0.78rem',
              }}
            >
              <span>
                共 {filteredResourceOptions.length} 个资源，已选择 {selectedResourceCount} 个
              </span>
              <span>
                第 {resourcePage} / {totalResourcePages} 页，每页 {RESOURCE_PAGE_SIZE} 个
              </span>
            </div>

            {unifiedResourceOptions.length === 0 ? (
              <EmptyPanel title="没有可访问的资源">
                当前 Notion 授权没有返回可选择的 data_source 或 page。
              </EmptyPanel>
            ) : visibleResourceOptions.length === 0 ? (
              <EmptyPanel title="没有匹配的资源">
                调整搜索关键词后再选择资源。
              </EmptyPanel>
            ) : (
              <div style={{ display: 'grid', gap: '0.65rem' }}>
                {visibleResourceOptions.map((option) => {
                  const isDatabase = option.kind === 'database';
                  const checked = isDatabase
                    ? selectedDatabaseIds.includes(option.id)
                    : selectedPageIds.includes(option.id);
                  return (
                    <ResourceOptionRow
                      key={`${option.kind}-${option.id}`}
                      option={option}
                      type={option.kind}
                      checked={checked}
                      onToggle={() => {
                        if (isDatabase) {
                          setSelectedDatabaseIds((current) =>
                            current.includes(option.id)
                              ? current.filter((id) => id !== option.id)
                              : [...current, option.id],
                          );
                          return;
                        }
                        setSelectedPageIds((current) =>
                          current.includes(option.id)
                            ? current.filter((id) => id !== option.id)
                            : [...current, option.id],
                        );
                      }}
                    />
                  );
                })}
              </div>
            )}

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                gap: '0.5rem',
                flexWrap: 'wrap',
              }}
            >
              <button
                type="button"
                onClick={() => setResourcePage((current) => Math.max(1, current - 1))}
                disabled={resourcePage <= 1}
                style={{
                  border: '1px solid var(--color-border-paper)',
                  borderRadius: '999px',
                  background: 'var(--color-bg-paper)',
                  color: 'var(--color-text-primary)',
                  padding: '0.5rem 0.78rem',
                  cursor: resourcePage <= 1 ? 'not-allowed' : 'pointer',
                  opacity: resourcePage <= 1 ? 0.55 : 1,
                  fontSize: '0.78rem',
                  fontWeight: 700,
                }}
              >
                上一页
              </button>
              <button
                type="button"
                onClick={() => setResourcePage((current) => Math.min(totalResourcePages, current + 1))}
                disabled={resourcePage >= totalResourcePages}
                style={{
                  border: '1px solid var(--color-border-paper)',
                  borderRadius: '999px',
                  background: 'var(--color-bg-paper)',
                  color: 'var(--color-text-primary)',
                  padding: '0.5rem 0.78rem',
                  cursor: resourcePage >= totalResourcePages ? 'not-allowed' : 'pointer',
                  opacity: resourcePage >= totalResourcePages ? 0.55 : 1,
                  fontSize: '0.78rem',
                  fontWeight: 700,
                }}
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </DetailSection>

      <DetailSection
        title="已挂载来源"
        subtitle="这里显示当前 Notion 账号已经授权给 Chat 使用的资源和同步状态。"
      >
        {loading ? (
          <SkeletonList rows={2} />
        ) : !connector || connector.sources.length === 0 ? (
          <EmptyPanel title="还没有挂载来源">
            认证并保存资源选择后，数据库和页面会出现在这里。这里集中展示当前 Notion 账号的来源。
          </EmptyPanel>
        ) : (
          <div style={{ display: 'grid', gap: '0.7rem' }}>
            {connector.sources.map((source) => (
              <SourceCard key={source.id} source={source} />
            ))}
          </div>
        )}
      </DetailSection>
    </div>
  );
}
