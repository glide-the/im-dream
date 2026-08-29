// [Input] Server-owned Notion connector/capability/Skill DTOs, Settings back callback, and existing resource/auth/sync mutations.
// [Output] One seven-section Notion overview plus Skill/file/resource/source child views on the Settings-owned scroll surface.
// [Pos] Canonical Settings Notion connector detail and child-view composition node in frontend/src/components/dashboard.
// [Sync] 2026-08-29: implement the approved seven-section warm-paper overview, safe Skill Markdown/files, and focused resource/source child views; Hosted MCP remains visibly unavailable and non-executable.
// [Sync] 2026-08-29: move provider discovery and long source lists off the overview, remove nested vertical scrolling, preserve resource drafts on save failure, and render createdAt without a current-time fallback.
// [Sync] 2026-08-29: remove decorative section indices, redundant normal-state notices, and the four-item status summary while retaining the compact status badge and actionable errors.
// [Sync] 2026-08-29: compact the overview into a desktop settings ledger with aligned section labels/content, denser controls, and a single-column mobile fallback.
// [Sync] 2026-08-29: render operations from the real Read-hook/workspace-materializer catalog instead of synthetic Skill/MCP operation rows.
// [Sync] 2026-08-29: restore skeleton-proportioned section rhythm and remove overview-only helper copy and resource statistics.
// [Sync] 2026-08-30: identify the connector as Notion CLI in the overview heading while retaining Notion as the provider name elsewhere.
// [Sync] 2026-08-30: block auth on a missing server ntn installation and show the backend-owned pinned install command.
// [Sync] 2026-08-30: remove the overview title subtitle and replace ambiguous CLI availability with installation/connection-aware states.
import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from 'react';
import { FaExternalLinkAlt, FaPuzzlePiece } from 'react-icons/fa';
import ReactMarkdown, { defaultUrlTransform, type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  createConnector,
  deleteConnector,
  getNotionCapabilityCatalog,
  getNotionSkillDetail,
  getNotionSkillFile,
  listConnectorDatabases,
  listConnectorPages,
  listConnectors,
  notifyResourceConnectorsChanged,
  pollConnectorAuth,
  refreshConnectorSources,
  ResourceConnectorApiError,
  selectConnectorResources,
  startConnectorAuth,
  updateConnectorSyncPolicy,
  type ConnectorAuthStatus,
  type ConnectorResourceSelection,
  type ConnectorSource,
  type ConnectorStatus,
  type NotionCapabilityAvailability,
  type NotionCapabilityCatalog,
  type NotionResourceOption,
  type NotionSkillDetail,
  type NotionSkillFileContent,
  type NotionSkillFileDescriptor,
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
  IconMoreHorizontal,
  IconShare,
  IconTrash,
} from '../chat/Icons';
import { SkeletonList } from '../chat/Skeleton';
import './ConnectorNotionDetailPage.css';

interface ConnectorNotionDetailPageProps {
  onBack: () => void;
  isMobile?: boolean;
}

type DetailView = 'overview' | 'skill' | 'file' | 'resources' | 'sources';
type DetailTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';
type UnifiedResourceKind = 'database' | 'page';

interface UnifiedResourceOption extends NotionResourceOption {
  kind: UnifiedResourceKind;
}

interface DetailStatus {
  label: string;
  tone: DetailTone;
}

const DEFAULT_NOTION_CONNECTOR_NAME = 'Notion Resource Connector';
const RESOURCE_PAGE_SIZE = 10;
const NOTION_WEBSITE = 'https://developers.notion.com/cli/get-started/overview';
const NOTION_PRIVACY = 'https://privacycenter.notion.so/policies';
const NOTION_TERMS = 'https://notion.notion.site/Terms-and-Privacy-28ffdd083dc3473e9c2da6ec011b58ac';

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function formatDateTime(value?: string): string {
  if (!value) return '未更新';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '暂时无法读取';
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function formatConnectionDate(connector: ResourceConnector | null): string {
  if (!connector) return '尚未连接';
  if (!connector.createdAt) return '暂时无法读取';
  const date = new Date(connector.createdAt);
  if (Number.isNaN(date.getTime())) return '暂时无法读取';
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date);
}

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  return `${(sizeBytes / 1024).toFixed(sizeBytes < 10 * 1024 ? 1 : 0)} KB`;
}

function formatSyncInterval(minutes: number): string {
  if (minutes < 60) return `每 ${minutes} 分钟`;
  if (minutes % 1440 === 0) return `每 ${minutes / 1440} 天`;
  return `每 ${minutes / 60} 小时`;
}

function formatStatusLabel(
  status?: ConnectorStatus | ConnectorSource['status'] | ConnectorAuthStatus | 'idle',
): string {
  switch (status) {
    case 'authenticating': return '认证中';
    case 'authenticated': return '已认证';
    case 'syncing': return '同步中';
    case 'synced': return '已同步';
    case 'expired': return '已过期';
    case 'error': return '错误';
    case 'draft': return '待连接';
    default: return '待处理';
  }
}

function availabilityLabel(availability: NotionCapabilityAvailability): string {
  switch (availability) {
    case 'available': return '可用';
    case 'requires_installation': return '需安装 ntn';
    case 'requires_connection': return '连接后可用';
    case 'requires_scope': return '选择资源后可用';
    default: return '不可用';
  }
}

function availabilityTone(availability: NotionCapabilityAvailability): DetailTone {
  switch (availability) {
    case 'available': return 'success';
    case 'requires_installation': return 'warning';
    case 'requires_connection': return 'warning';
    case 'requires_scope': return 'info';
    default: return 'neutral';
  }
}

function operationSourceLabel(source: 'runtime_hook' | 'workspace_materializer'): string {
  return source === 'runtime_hook' ? '内置 Hook' : '工作区';
}

function getDetailStatus(connector: ResourceConnector | null, loading: boolean): DetailStatus {
  if (loading) {
    return { label: '读取中', tone: 'info' };
  }
  if (!connector) {
    return { label: '未连接', tone: 'warning' };
  }
  if (connector.syncPolicy?.status === 'error') {
    return { label: '部分可用', tone: 'warning' };
  }
  if (connector.auth.warning) {
    return { label: '部分可用', tone: 'warning' };
  }
  if (connector.status === 'error' || connector.auth.status === 'error') {
    return { label: '异常', tone: 'danger' };
  }
  if (connector.auth.status === 'expired') {
    return { label: '已过期', tone: 'warning' };
  }
  if (connector.auth.status === 'authenticating' || connector.status === 'authenticating') {
    return { label: '认证中', tone: 'info' };
  }
  if (connector.status === 'syncing') {
    return { label: '同步中', tone: 'info' };
  }
  if (connector.auth.status === 'authenticated') {
    return connector.lastSyncedAt
      ? { label: '已连接', tone: 'success' }
      : { label: '已连接', tone: 'info' };
  }
  return { label: '待连接', tone: 'warning' };
}

function buildSelectionFromSources(sources: ConnectorSource[]): ConnectorResourceSelection {
  return {
    databaseIds: sources.filter((source) => source.type === 'notion_database').map((source) => source.id),
    pageIds: sources.filter((source) => source.type === 'notion_page').map((source) => source.id),
  };
}

function resolveSingleNotionConnector(connectors: ResourceConnector[]): ResourceConnector | null {
  const notionConnectors = connectors.filter((connector) => connector.platform === 'notion');
  if (notionConnectors.length === 0) return null;
  return notionConnectors.slice().sort((a, b) => {
    const aTime = new Date(a.updatedAt || a.createdAt || 0).getTime();
    const bTime = new Date(b.updatedAt || b.createdAt || 0).getTime();
    return bTime - aTime;
  })[0] ?? null;
}

function shouldShowPageCount(pageCount?: number): pageCount is number {
  return typeof pageCount === 'number' && pageCount > 0;
}

function sourceKindLabel(type: ConnectorSource['type']): string {
  return type === 'notion_database' ? '数据库' : '页面';
}

function Badge({ label, tone = 'neutral' }: { label: string; tone?: DetailTone }) {
  return <span className={`notion-detail__badge notion-detail__badge--${tone}`}>{label}</span>;
}

function Notice({ tone = 'neutral', title, children }: { tone?: DetailTone; title?: string; children: ReactNode }) {
  return (
    <div className={`notion-detail__notice notion-detail__notice--${tone}`} role={tone === 'danger' ? 'alert' : undefined}>
      {title ? <strong>{title}</strong> : null}
      <div>{children}</div>
    </div>
  );
}

function IndexSection({ sectionId, title, children }: { sectionId: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={`notion-section-${sectionId}`} className="notion-detail__section">
      <div className="notion-detail__section-body">
        <header className="notion-detail__section-header">
          <h2 id={`notion-section-${sectionId}`}>{title}</h2>
        </header>
        <div className="notion-detail__section-content">{children}</div>
      </div>
    </section>
  );
}

function NotionMark() {
  return <span aria-hidden="true" className="notion-detail__mark"><span>N</span></span>;
}

const MARKDOWN_COMPONENTS: Components = {
  a({ children, href }) {
    if (!href || (!href.startsWith('https://') && !href.startsWith('http://') && !href.startsWith('mailto:'))) {
      return <span className="notion-detail__markdown-inert-link">{children}</span>;
    }
    return <a href={href} rel="noopener noreferrer" target="_blank">{children}</a>;
  },
  img({ alt }) {
    return <span className="notion-detail__markdown-image-placeholder">{alt || '图片未在设置页加载'}</span>;
  },
};

function safeMarkdownUrlTransform(value: string): string {
  if (value.startsWith('https://') || value.startsWith('http://') || value.startsWith('mailto:')) {
    return defaultUrlTransform(value);
  }
  return '';
}

function MarkdownView({ content }: { content: string }) {
  return (
    <div className="notion-detail__markdown">
      <ReactMarkdown components={MARKDOWN_COMPONENTS} remarkPlugins={[remarkGfm]} urlTransform={safeMarkdownUrlTransform}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

function ChildHeader({ backLabel, title, description, onBack, headingRef }: {
  backLabel: string;
  title: string;
  description: string;
  onBack: () => void;
  headingRef: React.RefObject<HTMLHeadingElement | null>;
}) {
  return (
    <header className="notion-detail__child-header">
      <button className="notion-detail__back" onClick={onBack} type="button">
        <IconChevronLeft />
        {backLabel}
      </button>
      <h1 ref={headingRef} tabIndex={-1}>{title}</h1>
      <p>{description}</p>
    </header>
  );
}

function ResourceOptionRow({ option, checked, onToggle, disabled }: {
  option: UnifiedResourceOption;
  checked: boolean;
  onToggle: () => void;
  disabled?: boolean;
}) {
  const Icon = option.kind === 'database' ? IconDatabase : IconFile;
  return (
    <button
      aria-pressed={checked}
      className="notion-detail__resource-row"
      disabled={disabled}
      onClick={onToggle}
      type="button"
    >
      <span className="notion-detail__row-icon"><Icon /></span>
      <span className="notion-detail__row-copy">
        <strong>{option.title}</strong>
        <small>{option.subtitle || (option.kind === 'database' ? 'Notion 数据库' : '独立页面')}</small>
      </span>
      <span className="notion-detail__row-meta">
        <Badge label={option.kind === 'database' ? '数据库' : '页面'} />
        {shouldShowPageCount(option.pageCount) ? <small>{option.pageCount} 页</small> : null}
        <span aria-hidden="true" className={`notion-detail__check${checked ? ' is-checked' : ''}`}><IconCheck /></span>
      </span>
    </button>
  );
}

function SourceRow({ source }: { source: ConnectorSource }) {
  const Icon = source.type === 'notion_database' ? IconDatabase : IconFile;
  const tone: DetailTone = source.status === 'synced' ? 'success' : source.status === 'syncing' ? 'info' : source.status === 'error' ? 'danger' : 'neutral';
  return (
    <article className="notion-detail__source-row">
      <span className="notion-detail__row-icon"><Icon /></span>
      <div className="notion-detail__row-copy">
        <div className="notion-detail__source-title"><strong>{source.title}</strong><Badge label={formatStatusLabel(source.status)} tone={tone} /></div>
        <small>{sourceKindLabel(source.type)}{source.description ? ` · ${source.description}` : ''}</small>
      </div>
      <div className="notion-detail__source-meta">
        {shouldShowPageCount(source.pageCount) ? <strong>{source.pageCount} 页</strong> : null}
        <small>{formatDateTime(source.syncedAt || source.updatedAt)}</small>
      </div>
    </article>
  );
}

export default function ConnectorNotionDetailPage({ onBack, isMobile = false }: ConnectorNotionDetailPageProps) {
  const [view, setView] = useState<DetailView>('overview');
  const [connector, setConnector] = useState<ResourceConnector | null>(null);
  const [catalog, setCatalog] = useState<NotionCapabilityCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [policySaving, setPolicySaving] = useState(false);
  const [policyEnabled, setPolicyEnabled] = useState(false);
  const [policyIntervalMinutes, setPolicyIntervalMinutes] = useState<number | null>(null);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [resourceSaving, setResourceSaving] = useState(false);
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [databaseOptions, setDatabaseOptions] = useState<NotionResourceOption[]>([]);
  const [pageOptions, setPageOptions] = useState<NotionResourceOption[]>([]);
  const [selectedDatabaseIds, setSelectedDatabaseIds] = useState<string[]>([]);
  const [selectedPageIds, setSelectedPageIds] = useState<string[]>([]);
  const [resourceSearchQuery, setResourceSearchQuery] = useState('');
  const [resourcePage, setResourcePage] = useState(1);
  const [skillDetail, setSkillDetail] = useState<NotionSkillDetail | null>(null);
  const [skillLoading, setSkillLoading] = useState(false);
  const [skillError, setSkillError] = useState<string | null>(null);
  const [selectedSkillFile, setSelectedSkillFile] = useState<NotionSkillFileDescriptor | null>(null);
  const [skillFileContent, setSkillFileContent] = useState<NotionSkillFileContent | null>(null);
  const [skillFileLoading, setSkillFileLoading] = useState(false);
  const [skillFileError, setSkillFileError] = useState<string | null>(null);

  const rootRef = useRef<HTMLDivElement>(null);
  const childHeadingRef = useRef<HTMLHeadingElement>(null);
  const overviewReturnFocusKeyRef = useRef<string | null>(null);
  const fileReturnFocusIdRef = useRef<string | null>(null);
  const pendingFocusRestoreRef = useRef<'overview' | 'skill' | null>(null);

  const connectorId = connector?.id ?? null;
  const connectorAuthStatus = connector?.auth.status ?? 'idle';
  const cliInstallation = catalog?.cliInstallation ?? null;
  const cliMissing = cliInstallation?.status === 'missing';
  const canEditResources = connectorAuthStatus === 'authenticated';
  const syncPolicy = connector?.syncPolicy;
  const detailStatus = getDetailStatus(connector, loading);
  const sourceStats = useMemo(() => {
    const sources = connector?.sources ?? [];
    const databases = sources.filter((source) => source.type === 'notion_database').length;
    return { total: sources.length, databases, pages: sources.length - databases };
  }, [connector?.sources]);
  const readOperations = useMemo(
    () => catalog?.operations.filter((operation) => operation.kind === 'read') ?? [],
    [catalog?.operations],
  );
  const writeOperations = useMemo(
    () => catalog?.operations.filter((operation) => operation.kind === 'write') ?? [],
    [catalog?.operations],
  );
  const unifiedResourceOptions = useMemo<UnifiedResourceOption[]>(
    () => [
      ...databaseOptions.map((option) => ({ ...option, kind: 'database' as const })),
      ...pageOptions.map((option) => ({ ...option, kind: 'page' as const })),
    ],
    [databaseOptions, pageOptions],
  );
  const filteredResourceOptions = useMemo(() => {
    const query = resourceSearchQuery.trim().toLocaleLowerCase();
    if (!query) return unifiedResourceOptions;
    return unifiedResourceOptions.filter((option) => `${option.title} ${option.subtitle ?? ''} ${option.kind}`.toLocaleLowerCase().includes(query));
  }, [resourceSearchQuery, unifiedResourceOptions]);
  const totalResourcePages = Math.max(1, Math.ceil(filteredResourceOptions.length / RESOURCE_PAGE_SIZE));
  const visibleResourceOptions = useMemo(() => {
    const start = (resourcePage - 1) * RESOURCE_PAGE_SIZE;
    return filteredResourceOptions.slice(start, start + RESOURCE_PAGE_SIZE);
  }, [filteredResourceOptions, resourcePage]);
  const selectedResourceCount = selectedDatabaseIds.length + selectedPageIds.length;

  const reloadCatalog = useCallback(async () => {
    setCatalogLoading(true);
    setCatalogError(null);
    try {
      setCatalog(await getNotionCapabilityCatalog());
    } catch (error) {
      setCatalogError(getErrorMessage(error, 'Notion 能力信息暂时无法读取'));
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  const loadConnector = useCallback(async () => {
    setLoading(true);
    setPageError(null);
    try {
      setConnector(resolveSingleNotionConnector(await listConnectors()));
    } catch (error) {
      setPageError(getErrorMessage(error, 'Notion 连接状态读取失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadConnector();
    void reloadCatalog();
  }, [loadConnector, reloadCatalog]);

  useEffect(() => {
    if (!syncPolicy) return;
    setPolicyEnabled(syncPolicy.desired.enabled);
    setPolicyIntervalMinutes(syncPolicy.desired.intervalMinutes);
  }, [syncPolicy]);

  useEffect(() => {
    setResourcePage(1);
  }, [resourceSearchQuery]);

  useEffect(() => {
    setResourcePage((current) => Math.min(current, totalResourcePages));
  }, [totalResourcePages]);

  useEffect(() => {
    if (view === 'overview' && pendingFocusRestoreRef.current === 'overview') {
      pendingFocusRestoreRef.current = null;
      const focusTarget = [...(rootRef.current?.querySelectorAll<HTMLButtonElement>('button[data-focus-key]') ?? [])]
        .find((button) => button.dataset.focusKey === overviewReturnFocusKeyRef.current);
      focusTarget?.scrollIntoView({ block: 'center' });
      focusTarget?.focus();
      return;
    }
    if (view === 'skill' && pendingFocusRestoreRef.current === 'skill') {
      pendingFocusRestoreRef.current = null;
      const focusTarget = [...(rootRef.current?.querySelectorAll<HTMLButtonElement>('button[data-file-focus-id]') ?? [])]
        .find((button) => button.dataset.fileFocusId === fileReturnFocusIdRef.current);
      focusTarget?.scrollIntoView({ block: 'center' });
      focusTarget?.focus();
      return;
    }
    if (view !== 'overview') {
      childHeadingRef.current?.focus();
      rootRef.current?.scrollIntoView({ block: 'start' });
    }
  }, [view]);

  useEffect(() => {
    if (!connectorId || connectorAuthStatus !== 'authenticating') return undefined;
    let active = true;
    const poll = async () => {
      try {
        const next = await pollConnectorAuth(connectorId);
        if (!active || !next) return;
        setConnector(next);
        if (next.auth.status !== 'authenticating') void reloadCatalog();
      } catch (error) {
        if (active) setPageError(getErrorMessage(error, '认证状态读取失败；你的输入和已有索引未被修改'));
      }
    };
    void poll();
    const intervalId = window.setInterval(() => { void poll(); }, 3500);
    return () => { active = false; window.clearInterval(intervalId); };
  }, [connectorAuthStatus, connectorId, reloadCatalog]);

  const enterView = useCallback((nextView: DetailView, event: MouseEvent<HTMLButtonElement>) => {
    overviewReturnFocusKeyRef.current = event.currentTarget.dataset.focusKey ?? null;
    setView(nextView);
  }, []);

  const returnToOverview = useCallback(() => {
    pendingFocusRestoreRef.current = 'overview';
    setView('overview');
  }, []);

  const returnToSkill = useCallback(() => {
    pendingFocusRestoreRef.current = 'skill';
    setView('skill');
  }, []);

  const ensureSingleConnector = useCallback(async () => {
    if (connector) return connector;
    const existing = resolveSingleNotionConnector(await listConnectors());
    if (existing) { setConnector(existing); return existing; }
    const created = await createConnector({ name: DEFAULT_NOTION_CONNECTOR_NAME, platform: 'notion' });
    setConnector(created);
    return created;
  }, [connector]);

  const handleStartAuth = useCallback(async () => {
    if (connecting || cliMissing) return;
    setConnecting(true);
    setPageError(null);
    try {
      const target = await ensureSingleConnector();
      const next = await startConnectorAuth(target.id);
      if (next) setConnector(next);
      notifyResourceConnectorsChanged({ connectorId: target.id, reason: 'auth-updated' });
      await reloadCatalog();
    } catch (error) {
      setPageError(getErrorMessage(error, '无法启动 Notion 连接；已有内容未被修改，请重试'));
    } finally {
      setConnecting(false);
    }
  }, [cliMissing, connecting, ensureSingleConnector, reloadCatalog]);

  const handleDisconnect = useCallback(async () => {
    if (!connectorId || disconnecting) return;
    setDisconnecting(true);
    setPageError(null);
    try {
      if (await deleteConnector(connectorId)) {
        setConnector(null);
        setDatabaseOptions([]);
        setPageOptions([]);
        setSelectedDatabaseIds([]);
        setSelectedPageIds([]);
        notifyResourceConnectorsChanged({ connectorId, reason: 'connector-updated' });
        await reloadCatalog();
      }
    } catch (error) {
      setPageError(getErrorMessage(error, '无法关闭 Notion 连接；当前连接保持不变，请重试'));
    } finally {
      setDisconnecting(false);
    }
  }, [connectorId, disconnecting, reloadCatalog]);

  const handleSaveSyncPolicy = useCallback(async () => {
    if (!connectorId || !syncPolicy || policyIntervalMinutes === null || policySaving) return;
    setPolicySaving(true);
    setPolicyError(null);
    try {
      const next = await updateConnectorSyncPolicy(connectorId, { enabled: policyEnabled, intervalMinutes: policyIntervalMinutes });
      setConnector(next);
      notifyResourceConnectorsChanged({ connectorId, reason: 'connector-updated' });
    } catch (error) {
      setPolicyError(getErrorMessage(error, '策略未保存；服务器原策略仍然生效，请重试'));
    } finally {
      setPolicySaving(false);
    }
  }, [connectorId, policyEnabled, policyIntervalMinutes, policySaving, syncPolicy]);

  const handleOpenSkill = useCallback(async (event: MouseEvent<HTMLButtonElement>, skillId: string) => {
    enterView('skill', event);
    setSkillLoading(true);
    setSkillError(null);
    setSkillDetail(null);
    try {
      setSkillDetail(await getNotionSkillDetail(skillId));
    } catch (error) {
      setSkillError(getErrorMessage(error, 'Skill 说明暂时无法读取；Notion 连接和索引不受影响'));
    } finally {
      setSkillLoading(false);
    }
  }, [enterView]);

  const handleOpenSkillFile = useCallback(async (file: NotionSkillFileDescriptor) => {
    if (!skillDetail) return;
    fileReturnFocusIdRef.current = file.id;
    setSelectedSkillFile(file);
    setSkillFileContent(null);
    setSkillFileError(null);
    setSkillFileLoading(true);
    setView('file');
    try {
      setSkillFileContent(await getNotionSkillFile(skillDetail.skill.id, file.id, skillDetail.packageRevision));
    } catch (error) {
      if (error instanceof ResourceConnectorApiError && error.status === 409) {
        try {
          setSkillDetail(await getNotionSkillDetail(skillDetail.skill.id));
        } catch {
          // Keep the safe file error as the visible boundary; connector state remains usable.
        }
        setSkillFileError('Skill 包已更新，旧文件内容没有继续显示。请返回文件清单后重新打开。');
      } else {
        setSkillFileError(getErrorMessage(error, '文件暂时无法读取；请返回 Skill 刷新后重试'));
      }
    } finally {
      setSkillFileLoading(false);
    }
  }, [skillDetail]);

  const loadResourceOptions = useCallback(async () => {
    const selection = buildSelectionFromSources(connector?.sources ?? []);
    setSelectedDatabaseIds(selection.databaseIds);
    setSelectedPageIds(selection.pageIds);
    setResourceSearchQuery('');
    setResourcePage(1);
    setResourceError(null);
    if (!connectorId || !canEditResources) {
      setDatabaseOptions([]);
      setPageOptions([]);
      return;
    }
    setResourceLoading(true);
    try {
      const [databases, pages] = await Promise.all([
        listConnectorDatabases(connectorId),
        listConnectorPages(connectorId),
      ]);
      setDatabaseOptions(databases);
      setPageOptions(pages);
      setSelectedDatabaseIds(selection.databaseIds.length > 0 ? selection.databaseIds : databases.filter((option) => option.selected).map((option) => option.id));
      setSelectedPageIds(selection.pageIds.length > 0 ? selection.pageIds : pages.filter((option) => option.selected).map((option) => option.id));
    } catch (error) {
      setResourceError(getErrorMessage(error, '资源列表加载失败；服务器当前范围没有改变，请重试'));
      setDatabaseOptions([]);
      setPageOptions([]);
    } finally {
      setResourceLoading(false);
    }
  }, [canEditResources, connector?.sources, connectorId]);

  const handleOpenResources = useCallback((event: MouseEvent<HTMLButtonElement>) => {
    enterView('resources', event);
    void loadResourceOptions();
  }, [enterView, loadResourceOptions]);

  const handleSaveResources = useCallback(async () => {
    if (!connectorId || !canEditResources || resourceSaving) return;
    setResourceSaving(true);
    setResourceError(null);
    try {
      const next = await selectConnectorResources(connectorId, {
        databaseIds: selectedDatabaseIds,
        pageIds: selectedPageIds,
        databaseOptions,
        pageOptions,
      });
      if (next) setConnector(next);
      notifyResourceConnectorsChanged({ connectorId, reason: 'resources-selected' });
      await reloadCatalog();
    } catch (error) {
      setResourceError(getErrorMessage(error, '资源范围未保存；你的本页选择仍保留，服务器范围没有改变'));
    } finally {
      setResourceSaving(false);
    }
  }, [canEditResources, connectorId, databaseOptions, pageOptions, reloadCatalog, resourceSaving, selectedDatabaseIds, selectedPageIds]);

  const handleSyncSources = useCallback(async () => {
    if (!connectorId || !canEditResources || syncLoading) return;
    setSyncLoading(true);
    setResourceError(null);
    try {
      const next = await refreshConnectorSources(connectorId);
      if (next) setConnector(next);
      notifyResourceConnectorsChanged({ connectorId, reason: 'sources-refreshed' });
      await reloadCatalog();
    } catch (error) {
      setResourceError(getErrorMessage(error, '索引更新失败；最近一次成功索引仍保留，请稍后重试'));
    } finally {
      setSyncLoading(false);
    }
  }, [canEditResources, connectorId, reloadCatalog, syncLoading]);

  const authActionLabel = connectorAuthStatus === 'authenticated' ? '重新连接 Notion' : connectorAuthStatus === 'authenticating' ? '认证进行中' : '连接 Notion';

  if (view === 'skill') {
    return (
      <div className={`notion-detail${isMobile ? ' notion-detail--mobile' : ''}`} ref={rootRef}>
        <ChildHeader backLabel="Notion" description="查看服务器安装的只读 Skill 说明与公开文件。" headingRef={childHeadingRef} onBack={returnToOverview} title={skillDetail?.skill.title || 'Notion Skill'} />
        {skillLoading ? <SkeletonList rows={5} /> : skillError ? <Notice tone="danger" title="Skill 信息暂不可用">{skillError}</Notice> : skillDetail ? (
          <>
            <div className="notion-detail__skill-meta">
              <div><FaPuzzlePiece aria-hidden="true" /><span>{skillDetail.skill.description}</span></div>
              <div><Badge label="内置" /><Badge label={availabilityLabel(skillDetail.skill.availability)} tone={availabilityTone(skillDetail.skill.availability)} /></div>
            </div>
            <section aria-labelledby="notion-skill-body-title" className="notion-detail__child-section">
              <h2 id="notion-skill-body-title">Skill 说明</h2>
              <MarkdownView content={skillDetail.skill.body} />
            </section>
            <section aria-labelledby="notion-skill-files-title" className="notion-detail__child-section">
              <h2 id="notion-skill-files-title">包含的文件</h2>
              {skillDetail.files.length === 0 ? <Notice>当前 Skill 没有可公开查看的相关文件。</Notice> : (
                <div className="notion-detail__file-list">
                  {skillDetail.files.map((file) => (
                    <button data-file-focus-id={file.id} key={file.id} onClick={() => void handleOpenSkillFile(file)} type="button">
                      <span><IconFile /><span><strong>{file.relativePath}</strong><small>{file.mediaType}</small></span></span>
                      <span><small>{formatFileSize(file.sizeBytes)}</small><IconChevronRight /></span>
                    </button>
                  ))}
                </div>
              )}
            </section>
          </>
        ) : null}
      </div>
    );
  }

  if (view === 'file') {
    return (
      <div className={`notion-detail${isMobile ? ' notion-detail--mobile' : ''}`} ref={rootRef}>
        <ChildHeader backLabel="包含的文件" description={`${selectedSkillFile?.mediaType || 'text/markdown'} · ${selectedSkillFile ? formatFileSize(selectedSkillFile.sizeBytes) : '只读'}`} headingRef={childHeadingRef} onBack={returnToSkill} title={selectedSkillFile?.relativePath || 'Skill 文件'} />
        {skillFileLoading ? <SkeletonList rows={6} /> : skillFileError ? <Notice tone="danger" title="文件暂不可用">{skillFileError}</Notice> : skillFileContent ? (
          <section aria-label="Skill 文件内容" className="notion-detail__child-section notion-detail__file-reader">
            <MarkdownView content={skillFileContent.file.content} />
          </section>
        ) : null}
      </div>
    );
  }

  if (view === 'resources') {
    return (
      <div className={`notion-detail${isMobile ? ' notion-detail--mobile' : ''}`} ref={rootRef}>
        <ChildHeader backLabel="Notion" description="选择允许进入轻量索引的数据库和独立页面；正文不会在此批量下载。" headingRef={childHeadingRef} onBack={returnToOverview} title="资源范围" />
        {!canEditResources ? (
          <Notice tone="warning" title="连接后才能管理资源">当前服务器范围保持不变。返回 Notion 详情完成连接后再试。</Notice>
        ) : (
          <>
            <div className="notion-detail__resource-toolbar">
              <label><span className="notion-detail__sr-only">搜索 Notion 资源</span><input disabled={resourceLoading} onChange={(event) => setResourceSearchQuery(event.target.value)} placeholder="搜索资源" type="search" value={resourceSearchQuery} /></label>
              <span>已选择 {selectedResourceCount} 个{selectedResourceCount !== sourceStats.total ? ' · 有未保存更改' : ''}</span>
            </div>
            {resourceError ? <Notice tone="danger" title="资源操作未完成">{resourceError}</Notice> : null}
            {resourceLoading ? <SkeletonList rows={6} /> : unifiedResourceOptions.length === 0 ? (
              <Notice title="没有可访问的资源">当前 Notion 授权没有返回可选择的数据库或页面。</Notice>
            ) : visibleResourceOptions.length === 0 ? (
              <Notice title="没有匹配的资源">调整搜索关键词后再试。</Notice>
            ) : (
              <div className="notion-detail__resource-list">
                {visibleResourceOptions.map((option) => {
                  const isDatabase = option.kind === 'database';
                  const checked = isDatabase ? selectedDatabaseIds.includes(option.id) : selectedPageIds.includes(option.id);
                  return (
                    <ResourceOptionRow
                      checked={checked}
                      key={`${option.kind}-${option.id}`}
                      onToggle={() => {
                        if (isDatabase) {
                          setSelectedDatabaseIds((current) => current.includes(option.id) ? current.filter((id) => id !== option.id) : [...current, option.id]);
                        } else {
                          setSelectedPageIds((current) => current.includes(option.id) ? current.filter((id) => id !== option.id) : [...current, option.id]);
                        }
                      }}
                      option={option}
                    />
                  );
                })}
              </div>
            )}
            <div className="notion-detail__pagination">
              <span>共 {filteredResourceOptions.length} 个 · 第 {resourcePage} / {totalResourcePages} 页</span>
              <div>
                <button disabled={resourcePage <= 1} onClick={() => setResourcePage((current) => Math.max(1, current - 1))} type="button">上一页</button>
                <button disabled={resourcePage >= totalResourcePages} onClick={() => setResourcePage((current) => Math.min(totalResourcePages, current + 1))} type="button">下一页</button>
              </div>
            </div>
            <div className="notion-detail__sticky-action">
              <span>服务器当前范围 {sourceStats.total} 个</span>
              <button className="notion-detail__button notion-detail__button--primary" disabled={resourceSaving || resourceLoading} onClick={() => void handleSaveResources()} type="button">
                {resourceSaving ? <IconLoader className="notion-detail__spinner" /> : <IconCheck />}{resourceSaving ? '保存并同步中' : '保存并首次同步'}
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  if (view === 'sources') {
    return (
      <div className={`notion-detail${isMobile ? ' notion-detail--mobile' : ''}`} ref={rootRef}>
        <ChildHeader backLabel="Notion" description="查看当前已挂载来源的轻量索引状态；立即同步不会批量下载正文。" headingRef={childHeadingRef} onBack={returnToOverview} title="已挂载来源" />
        <div className="notion-detail__source-summary">
          <div><strong>{sourceStats.total} 个来源</strong><span>最近成功 {formatDateTime(connector?.lastSyncedAt)}</span></div>
          <button className="notion-detail__button" disabled={!canEditResources || syncLoading || sourceStats.total === 0} onClick={() => void handleSyncSources()} type="button">
            {syncLoading ? <IconLoader className="notion-detail__spinner" /> : <IconArrowUp />}{syncLoading ? '同步中' : syncPolicy?.status === 'error' ? '立即重试' : '立即同步'}
          </button>
        </div>
        {resourceError ? <Notice tone="danger" title="索引没有更新">{resourceError}</Notice> : null}
        {sourceStats.total === 0 ? <Notice title="还没有挂载来源">前往“资源范围”选择数据库或页面并保存。</Notice> : (
          <div className="notion-detail__source-list">{connector?.sources.map((source) => <SourceRow key={`${source.type}-${source.id}`} source={source} />)}</div>
        )}
      </div>
    );
  }

  return (
    <div className={`notion-detail${isMobile ? ' notion-detail--mobile' : ''}`} ref={rootRef}>
      <nav aria-label="Notion 详情导航">
        <button className="notion-detail__back" onClick={onBack} type="button"><IconChevronLeft />资源链接</button>
      </nav>

      <header className="notion-detail__hero">
        <div className="notion-detail__identity">
          <NotionMark />
          <div>
            <div className="notion-detail__title-row"><h1>Notion CLI</h1><Badge label={detailStatus.label} tone={detailStatus.tone} /></div>
          </div>
        </div>
        <div className="notion-detail__hero-actions">
          <button className="notion-detail__button notion-detail__button--primary" disabled={catalogLoading || cliMissing || connecting || connectorAuthStatus === 'authenticating'} onClick={() => void handleStartAuth()} type="button">
            {connecting ? <IconLoader className="notion-detail__spinner" /> : <IconShare />}{connecting ? '连接中' : cliMissing ? '先安装 ntn' : authActionLabel}
          </button>
          <details className="notion-detail__more">
            <summary aria-label="更多 Notion 操作"><IconMoreHorizontal /></summary>
            <div><button disabled={!connectorId || disconnecting} onClick={() => void handleDisconnect()} type="button">{disconnecting ? <IconLoader className="notion-detail__spinner" /> : <IconTrash />}{disconnecting ? '关闭中' : '关闭连接'}</button></div>
          </details>
        </div>
        {connector?.auth.status === 'authenticating' ? (
          <div className="notion-detail__verification">
            <div><span>验证码</span><strong>{connector.auth.verificationCode || '等待生成'}</strong></div>
            <div><span>{connector.auth.message || '在 Notion 中完成确认后，本页会自动刷新。'}</span>{connector.auth.verificationUrl ? <a href={connector.auth.verificationUrl} rel="noopener noreferrer" target="_blank">打开验证页 <FaExternalLinkAlt /></a> : null}</div>
          </div>
        ) : null}
      </header>

      {cliMissing && cliInstallation ? (
        <Notice tone="warning" title="连接前需要安装 Notion CLI">
          在 Dream 服务所在机器运行 <code>{cliInstallation.installCommand}</code>，安装完成后刷新本页继续认证。
        </Notice>
      ) : null}

      {pageError ? <Notice tone="danger" title="Notion 状态未更新">{pageError}</Notice> : null}

      <div className="notion-detail__sections">
        <IndexSection sectionId="permissions" title="权限">
          <div className="notion-detail__policy">
            <div>
              <label><input checked={policyEnabled} disabled={!syncPolicy || policySaving} onChange={(event) => setPolicyEnabled(event.target.checked)} type="checkbox" /><span><strong>自动同步</strong><small>{syncPolicy ? `当前生效：${syncPolicy.effective.enabled ? formatSyncInterval(syncPolicy.effective.intervalMinutes) : '已关闭'}` : '连接后可设置'}</small></span></label>
              <select aria-label="Notion 自动同步频率" disabled={!syncPolicy || !policyEnabled || policySaving} onChange={(event) => setPolicyIntervalMinutes(Number(event.target.value))} value={policyIntervalMinutes ?? ''}>
                {syncPolicy?.allowedIntervalMinutes.map((minutes) => <option key={minutes} value={minutes}>{formatSyncInterval(minutes)}</option>)}
              </select>
              <button className="notion-detail__button" disabled={!syncPolicy || policyIntervalMinutes === null || policySaving} onClick={() => void handleSaveSyncPolicy()} type="button">{policySaving ? '保存中' : '保存策略'}</button>
            </div>
            <p>{syncPolicy?.status === 'error' ? '上次同步失败；最近成功索引仍保留。' : syncPolicy?.status === 'syncing' ? '正在后台同步。' : policyEnabled && syncPolicy ? `下次计划 ${formatDateTime(syncPolicy.nextSyncAt)}` : '自动同步已关闭。'}</p>
          </div>
          {policyError ? <Notice tone="danger">{policyError}</Notice> : null}
        </IndexSection>

        <IndexSection sectionId="skills" title="Skills">
          {catalogLoading ? <SkeletonList rows={1} /> : catalogError ? <Notice tone="danger" title="Skill 信息暂不可用">{catalogError}；连接和索引不受影响。</Notice> : catalog?.skills.length ? (
            <div className="notion-detail__action-list">
              {catalog.skills.map((skill) => (
                <button data-focus-key={`skill-${skill.id}`} key={skill.id} onClick={(event) => void handleOpenSkill(event, skill.id)} type="button">
                  <span className="notion-detail__skill-icon"><FaPuzzlePiece aria-hidden="true" /></span>
                  <span><strong>{skill.title}</strong></span>
                  <span><Badge label="内置" /><Badge label={availabilityLabel(skill.availability)} tone={availabilityTone(skill.availability)} /><IconChevronRight /></span>
                </button>
              ))}
            </div>
          ) : <Notice>当前服务器没有可查看的 Notion Skill。</Notice>}
        </IndexSection>

        <IndexSection sectionId="read-operations" title="读取操作">
          {catalogLoading ? <SkeletonList rows={3} /> : catalogError ? <Notice tone="danger">读取能力说明暂时无法读取；资源管理仍可继续。</Notice> : (
            <div className="notion-detail__capabilities">
              {readOperations.map((operation) => (
                <div className="notion-detail__capability-row" key={operation.id}>
                  <span><strong>{operation.title}</strong><small>{operation.description}</small></span>
                  <span className="notion-detail__operation-badges"><Badge label={operationSourceLabel(operation.source)} /><Badge label={availabilityLabel(operation.availability)} tone={availabilityTone(operation.availability)} /></span>
                </div>
              ))}
            </div>
          )}
        </IndexSection>

        <IndexSection sectionId="write-operations" title="写入操作">
          {writeOperations.length > 0 ? writeOperations.map((operation) => <div className="notion-detail__capability-row" key={operation.id}><span><strong>{operation.title}</strong><small>{operation.description}</small></span><span className="notion-detail__operation-badges"><Badge label={operationSourceLabel(operation.source)} /><Badge label={availabilityLabel(operation.availability)} tone={availabilityTone(operation.availability)} /></span></div>) : <div className="notion-detail__compact-state"><span>暂无可用操作</span><Badge label="只读" /></div>}
        </IndexSection>

        <IndexSection sectionId="resource-scope" title="资源范围">
          <button className="notion-detail__management-row" data-focus-key="resources" onClick={handleOpenResources} type="button">
            <span><strong>管理资源范围</strong></span>
            <span><IconChevronRight /></span>
          </button>
        </IndexSection>

        <IndexSection sectionId="mounted-sources" title="已挂载来源">
          <button className="notion-detail__management-row" data-focus-key="sources" onClick={(event) => enterView('sources', event)} type="button">
            <span><strong>管理已挂载来源</strong></span>
            <span><IconChevronRight /></span>
          </button>
        </IndexSection>

        <IndexSection sectionId="information" title="信息">
          <dl className="notion-detail__information">
            <div><dt>连接时间</dt><dd>{formatConnectionDate(connector)}</dd></div>
            {[
              ['网站', NOTION_WEBSITE],
              ['隐私政策', NOTION_PRIVACY],
              ['服务条款', NOTION_TERMS],
            ].map(([label, href]) => <div key={label}><dt>{label}</dt><dd><a aria-label={`${label}（在新窗口打开）`} href={href} rel="noopener noreferrer" target="_blank"><FaExternalLinkAlt aria-hidden="true" /></a></dd></div>)}
          </dl>
        </IndexSection>
      </div>
    </div>
  );
}
