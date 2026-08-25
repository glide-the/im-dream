// [Input] One actor-owned database MCP server identifier, typed claude-mcp APIs, and Settings navigation callbacks.
// [Output] MCP detail workbench with automatic cache-first standard-SDK discovery, OAuth actions, and searchable tools/resources/prompts inventory.
// [Pos] Server detail surface in the frontend claude-mcp business domain.
// [Sync] 2026-08-20: add public-SDK tool discovery without `/mcp` TUI parsing or remote tool execution.
// [Sync] 2026-08-25: separate anonymous, required, authenticated, and rollback-compatible unknown auth actions.
// [Sync] 2026-08-25: automatically load all three MCP inventory families without a user-facing refresh control.
// [Sync] 2026-08-25: add revision-aware managed configuration editing followed by automatic cache-first discovery.
// [Sync] 2026-08-25: remove editable authentication policy; backend discovery owns anonymous/OAuth classification.
// [Sync] 2026-08-25: replace redirect URL copy/paste with same-origin automatic SPA callback submission.
// [Sync] 2026-08-25: ignore stale inventory responses when config or credential revisions change mid-discovery.

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import {
  cancelClaudeMcpAuth,
  getClaudeMcpCapability,
  getClaudeMcpOperation,
  getClaudeMcpServer,
  getClaudeMcpServerInventory,
  logoutClaudeMcpServer,
  removeClaudeMcpServer,
  startClaudeMcpAuth,
  updateClaudeMcpServer,
  ClaudeMcpApiError,
  type ClaudeMcpCapability,
  type ClaudeMcpAuthState,
  type ClaudeMcpOperation,
  type ClaudeMcpServer,
  type ClaudeMcpServerInventory,
  type ClaudeMcpState,
  type ClaudeMcpTool,
} from '../../api/claudeMcpApi';
import {
  forgetClaudeMcpOAuthOperation,
  rememberClaudeMcpOAuthOperation,
} from './oauthHandoff';
import {
  IconCheck,
  IconChevronLeft,
  IconChevronRight,
  IconDatabase,
  IconList,
  IconLoader,
  IconSearch,
  IconShare,
  IconTrash,
  IconX,
} from '../chat/Icons';
import { SkeletonBar, SkeletonCircle, SkeletonList } from '../chat/Skeleton';

interface ClaudeMcpServerDetailPageProps {
  serverName: string;
  onBack: () => void;
  isMobile?: boolean;
}

type CapabilityTab = 'tools' | 'resources' | 'prompts';
type ToolFilter = 'all' | 'read_only' | 'destructive' | 'open_world' | 'unspecified';
type EditTransport = 'streamable_http' | 'sse' | 'stdio';
type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

const OPERATION_POLL_INTERVAL_MS = 1200;
const ACTIVE_STATES: ClaudeMcpState[] = [
  'auth_starting',
  'waiting_for_user',
  'exchanging_code',
  'cancelling',
];
const DASHED_PAGE_BORDER = '1px dashed color-mix(in srgb, var(--color-border-paper) 62%, transparent)';
const SOFT_CONTROL_BORDER = '1px solid color-mix(in srgb, var(--color-border-paper) 58%, transparent)';
const SOFT_ROW_DIVIDER = '1px solid color-mix(in srgb, var(--color-border-paper) 34%, transparent)';
const SOFT_ROW_SURFACE = 'color-mix(in srgb, var(--color-bg-paper) 28%, transparent)';

const STATE_LABELS: Record<ClaudeMcpState, string> = {
  not_configured: '未配置',
  configured: '已配置',
  needs_auth: '需要认证',
  auth_starting: '正在启动',
  waiting_for_user: '等待授权',
  exchanging_code: '正在交换凭证',
  connected: '已连接',
  failed: '连接失败',
  cancelling: '正在取消',
  logged_out: '已退出',
  disabled: '已禁用',
};

const AUTH_STATE_LABELS: Record<ClaudeMcpAuthState, string> = {
  anonymous: '匿名连接，无需 OAuth',
  required: '需要认证',
  authenticated: '已认证',
  unknown: '认证状态未知',
};

function authStateOf(server: ClaudeMcpServer | null): ClaudeMcpAuthState {
  return server?.auth_state ?? 'unknown';
}

function canStartAuth(server: ClaudeMcpServer | null, state: ClaudeMcpState | undefined): boolean {
  return state === 'needs_auth' && authStateOf(server) === 'required';
}

function canLogout(server: ClaudeMcpServer | null, state: ClaudeMcpState | undefined): boolean {
  const authState = authStateOf(server);
  if (server?.credential_configured) return true;
  return state === 'connected' && (authState === 'authenticated' || authState === 'unknown');
}

function connectionStateLabel(server: ClaudeMcpServer | null, state: ClaudeMcpState | undefined): string {
  if (state === 'connected' && authStateOf(server) === 'anonymous') return '已匿名连接';
  if (state === 'connected' && authStateOf(server) === 'authenticated') return '已认证连接';
  return state ? STATE_LABELS[state] : '状态未知';
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ClaudeMcpApiError
    ? `${error.message}（${error.code}）`
    : fallback;
}

function operationErrorMessage(operation: ClaudeMcpOperation): string | null {
  return operation.error
    ? `${operation.error.message}（${operation.error.code}）`
    : null;
}

function connectionSummary(
  server: ClaudeMcpServer | null,
  state: ClaudeMcpState | undefined,
  toolCount: number | undefined,
): string {
  const count = toolCount ?? '—';
  if (state === 'connected' && authStateOf(server) === 'anonymous') {
    return `已匿名连接，无需 OAuth；已发现 ${count} 个工具，可供 Chat 会话使用。`;
  }
  if (state === 'connected' && authStateOf(server) === 'authenticated') {
    return `已通过认证连接；已发现 ${count} 个工具，可供 Chat 会话使用。`;
  }
  if (state === 'connected') {
    return `连接可用；已发现 ${count} 个工具。认证状态由 Runtime 回报为未知。`;
  }
  if (state === 'needs_auth' && authStateOf(server) === 'required') {
    return '服务已明确要求认证，完成 OAuth 后可继续检测工具能力。';
  }
  if (state === 'failed') {
    return '最近一次 inventory discovery 失败；单 Server 失败不会阻塞其他 Server。';
  }
  return 'Server 配置已从 Dream 数据库加载；正在自动读取远端能力清单。';
}

function formatDateTime(value?: string): string {
  if (!value) return '尚未探测';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

function stateTone(state: ClaudeMcpState | undefined): Tone {
  if (state === 'connected') return 'success';
  if (state === 'failed') return 'danger';
  if (state === 'needs_auth' || state === 'logged_out') return 'warning';
  if (state && ACTIVE_STATES.includes(state)) return 'info';
  return 'neutral';
}

function tonePalette(tone: Tone) {
  if (tone === 'success') {
    return {
      background: 'color-mix(in srgb, var(--color-state-success) 14%, var(--color-bg-surface))',
      color: 'var(--color-state-success)',
    };
  }
  if (tone === 'warning') {
    return {
      background: 'color-mix(in srgb, var(--color-state-warning) 14%, var(--color-bg-surface))',
      color: 'var(--color-state-warning)',
    };
  }
  if (tone === 'danger') {
    return {
      background: 'color-mix(in srgb, var(--color-state-error) 12%, var(--color-bg-surface))',
      color: 'var(--color-state-error)',
    };
  }
  if (tone === 'info') {
    return {
      background: 'color-mix(in srgb, var(--color-action-link) 10%, var(--color-bg-surface))',
      color: 'var(--color-action-link)',
    };
  }
  return { background: 'var(--color-bg-surface)', color: 'var(--color-text-secondary)' };
}

function Pill({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  const palette = tonePalette(tone);
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.3rem',
        borderRadius: '999px',
        background: palette.background,
        color: palette.color,
        padding: '0.28rem 0.58rem',
        fontSize: '0.72rem',
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </span>
  );
}

function InfoChip({ label, value }: { label: string; value: ReactNode }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.38rem',
        borderRadius: '999px',
        background: 'color-mix(in srgb, var(--color-bg-surface) 74%, transparent)',
        color: 'var(--color-text-secondary)',
        padding: '0.34rem 0.62rem',
        fontSize: '0.72rem',
        lineHeight: 1.2,
        maxWidth: '100%',
      }}
    >
      <span style={{ color: 'var(--color-text-muted)', fontWeight: 700 }}>{label}</span>
      <span style={{ color: 'var(--color-text-primary)', fontWeight: 800, overflowWrap: 'anywhere' }}>{value}</span>
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
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap', paddingBottom: '0.58rem' }}>
        <div style={{ minWidth: 0 }}>
          <h2 style={{ margin: 0, color: 'var(--color-text-primary)', fontSize: '1rem', fontWeight: 700 }}>{title}</h2>
          {subtitle ? <p style={{ margin: '0.3rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.8rem', lineHeight: 1.55 }}>{subtitle}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function actionStyle(primary = false, danger = false): CSSProperties {
  return {
    border: 'none',
    borderRadius: '999px',
    padding: '0.62rem 0.88rem',
    background: danger
      ? 'color-mix(in srgb, var(--color-state-error) 12%, var(--color-bg-surface))'
      : primary
        ? 'var(--color-text-primary)'
        : 'var(--color-bg-surface)',
    color: danger
      ? 'var(--color-state-error)'
      : primary
        ? 'var(--color-bg-app)'
        : 'var(--color-text-primary)',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.42rem',
    fontSize: '0.8rem',
    fontWeight: 700,
  };
}

function toolMatchesFilter(tool: ClaudeMcpTool, filter: ToolFilter): boolean {
  if (filter === 'read_only') return tool.annotations.read_only === true;
  if (filter === 'destructive') return tool.annotations.destructive === true;
  if (filter === 'open_world') return tool.annotations.open_world === true;
  if (filter === 'unspecified') {
    return tool.annotations.read_only !== true
      && tool.annotations.destructive !== true
      && tool.annotations.open_world !== true;
  }
  return true;
}

function ToolRow({ tool }: { tool: ClaudeMcpTool }) {
  const hasAnnotation = tool.annotations.read_only === true
    || tool.annotations.destructive === true
    || tool.annotations.open_world === true;
  return (
    <article
      aria-label={`MCP 工具 ${tool.name}`}
      style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.8rem', padding: '0.72rem 0.6rem', borderBottom: SOFT_ROW_DIVIDER }}
    >
      <div style={{ minWidth: 0, display: 'flex', alignItems: 'flex-start', gap: '0.68rem' }}>
        <span aria-hidden="true" style={{ width: '1.8rem', height: '1.8rem', borderRadius: '0.58rem', background: SOFT_ROW_SURFACE, color: 'var(--color-text-muted)', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
          <IconList style={{ width: '0.82rem', height: '0.82rem' }} />
        </span>
        <div style={{ minWidth: 0 }}>
          <h3 style={{ margin: 0, color: 'var(--color-text-primary)', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.84rem', lineHeight: 1.4, overflowWrap: 'anywhere' }}>
            {tool.name}
          </h3>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.75rem', lineHeight: 1.5 }}>
            {tool.description || '服务未提供工具说明。'}
          </p>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.34rem', flexWrap: 'wrap', justifyContent: 'flex-end', flexShrink: 0 }}>
        {tool.annotations.read_only === true ? <Pill tone="success">只读</Pill> : null}
        {tool.annotations.destructive === true ? <Pill tone="danger">破坏性</Pill> : null}
        {tool.annotations.open_world === true ? <Pill tone="warning">开放世界</Pill> : null}
        {!hasAnnotation ? <Pill>未声明</Pill> : null}
      </div>
    </article>
  );
}

export default function ClaudeMcpServerDetailPage({
  serverName,
  onBack,
  isMobile = false,
}: ClaudeMcpServerDetailPageProps) {
  const [capability, setCapability] = useState<ClaudeMcpCapability | null>(null);
  const [server, setServer] = useState<ClaudeMcpServer | null>(null);
  const [inventory, setInventory] = useState<ClaudeMcpServerInventory | null>(null);
  const [operation, setOperation] = useState<ClaudeMcpOperation | null>(null);
  const [activeTab, setActiveTab] = useState<CapabilityTab>('tools');
  const [searchQuery, setSearchQuery] = useState('');
  const [toolFilter, setToolFilter] = useState<ToolFilter>('all');
  const [loading, setLoading] = useState(true);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [inventoryError, setInventoryError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editDisplayName, setEditDisplayName] = useState('');
  const [editTransport, setEditTransport] = useState<EditTransport>('streamable_http');
  const [editUrl, setEditUrl] = useState('');
  const [editStdioProfile, setEditStdioProfile] = useState('');
  const [editEnabled, setEditEnabled] = useState(true);
  const automaticInventoryKeyRef = useRef<string | null>(null);
  const inventoryRequestSequenceRef = useRef(0);

  const effectiveState = operation && ACTIVE_STATES.includes(operation.state)
    ? operation.state
    : server?.state;
  const visibleTools = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase();
    return (inventory?.tools ?? []).filter((tool) => {
      if (!toolMatchesFilter(tool, toolFilter)) return false;
      if (!query) return true;
      return `${tool.name} ${tool.description ?? ''}`.toLocaleLowerCase().includes(query);
    });
  }, [inventory?.tools, searchQuery, toolFilter]);

  const loadInventory = useCallback(async () => {
    const requestSequence = inventoryRequestSequenceRef.current + 1;
    inventoryRequestSequenceRef.current = requestSequence;
    setInventoryLoading(true);
    setInventoryError(null);
    try {
      const next = await getClaudeMcpServerInventory(serverName);
      if (requestSequence !== inventoryRequestSequenceRef.current) return;
      automaticInventoryKeyRef.current = `${serverName}:${next.config_revision}:${next.credential_revision}:enabled`;
      setInventory(next);
      setServer((current) => current ? {
        ...current,
        revision: next.config_revision,
        credential_revision: next.credential_revision,
        state: next.status === 'connected'
          ? 'connected'
          : next.status === 'needs_auth' ? 'needs_auth' : 'failed',
        auth_state: next.status === 'needs_auth'
          ? 'required'
          : next.status === 'connected'
            ? (current.credential_configured ? 'authenticated' : 'anonymous')
            : current.auth_state,
      } : current);
    } catch (error) {
      if (requestSequence !== inventoryRequestSequenceRef.current) return;
      setInventory(null);
      setInventoryError(errorMessage(error, 'MCP 工具清单读取失败'));
    } finally {
      if (requestSequence === inventoryRequestSequenceRef.current) setInventoryLoading(false);
    }
  }, [serverName]);

  const loadInventoryForServer = useCallback((nextServer: ClaudeMcpServer) => {
    const key = `${serverName}:${nextServer.revision ?? 'unknown'}:${nextServer.credential_revision}:`;
    const inventoryKey = `${key}${nextServer.enabled ? 'enabled' : 'disabled'}`;
    if (automaticInventoryKeyRef.current === inventoryKey) return;
    automaticInventoryKeyRef.current = inventoryKey;
    setInventory(null);
    setInventoryError(null);
    if (nextServer.enabled) {
      void loadInventory();
    } else {
      inventoryRequestSequenceRef.current += 1;
      setInventoryLoading(false);
    }
  }, [loadInventory, serverName]);

  const load = useCallback(async () => {
    setLoading(true);
    setPageError(null);
    try {
      const [capabilityResult, serverResult] = await Promise.allSettled([
        getClaudeMcpCapability(),
        getClaudeMcpServer(serverName),
      ]);
      if (capabilityResult.status === 'rejected') throw capabilityResult.reason;
      const nextCapability = capabilityResult.value;
      setCapability(nextCapability);
      if (!nextCapability.enabled) {
        inventoryRequestSequenceRef.current += 1;
        setServer(null);
        setInventory(null);
        setInventoryLoading(false);
        return;
      }
      if (serverResult.status === 'rejected') throw serverResult.reason;
      const nextServer = serverResult.value;
      setServer(nextServer);
      setEditDisplayName(nextServer.display_name);
      setEditTransport((nextServer.transport ?? 'streamable_http') as EditTransport);
      setEditUrl(nextServer.url ?? '');
      setEditStdioProfile(nextServer.stdio_profile_key ?? '');
      setEditEnabled(nextServer.enabled);
      if (nextServer.active_operation_id) {
        setOperation(await getClaudeMcpOperation(nextServer.active_operation_id));
      }
      loadInventoryForServer(nextServer);
    } catch (error) {
      setPageError(errorMessage(error, 'Claude MCP 服务详情读取失败'));
    } finally {
      setLoading(false);
    }
  }, [loadInventoryForServer, serverName]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!operation || !ACTIVE_STATES.includes(operation.state)) return undefined;
    const timer = window.setInterval(() => {
      void getClaudeMcpOperation(operation.id)
        .then((next) => {
          setOperation(next);
          if (next.state === 'connected') {
            forgetClaudeMcpOAuthOperation(next.id);
            void load();
          }
        })
        .catch((error: unknown) => setPageError(errorMessage(error, '认证状态刷新失败')));
    }, OPERATION_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [load, operation]);

  const startAuth = useCallback(async () => {
    if (busyAction || !canStartAuth(server, effectiveState)) return;
    setBusyAction('auth');
    setPageError(null);
    try {
      const next = await startClaudeMcpAuth(serverName);
      if (!rememberClaudeMcpOAuthOperation(next.id)) {
        await cancelClaudeMcpAuth(next.id);
        throw new Error('browser operation handoff unavailable');
      }
      setOperation(next);
    } catch (error) {
      setPageError(errorMessage(error, '认证启动失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, effectiveState, server, serverName]);

  const cancelAuth = useCallback(async () => {
    if (!operation || busyAction) return;
    setBusyAction('cancel');
    setPageError(null);
    try {
      setOperation(await cancelClaudeMcpAuth(operation.id));
      forgetClaudeMcpOAuthOperation(operation.id);
      await load();
    } catch (error) {
      setPageError(errorMessage(error, '认证取消失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, load, operation]);

  const logout = useCallback(async () => {
    if (busyAction) return;
    setBusyAction('logout');
    setPageError(null);
    try {
      await logoutClaudeMcpServer(serverName);
      setOperation(null);
      automaticInventoryKeyRef.current = null;
      await load();
    } catch (error) {
      setPageError(errorMessage(error, '退出认证失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, load, serverName]);

  const saveConfiguration = useCallback(async () => {
    if (!server || busyAction) return;
    const displayName = editDisplayName.trim();
    const url = editUrl.trim();
    const stdioProfile = editStdioProfile.trim();
    if (!displayName) {
      setPageError('显示名称不能为空。');
      return;
    }
    if (editTransport === 'stdio' ? !stdioProfile : !url) {
      setPageError(editTransport === 'stdio' ? 'stdio 需要服务端 profile key。' : 'HTTP/SSE 需要绝对 URL。');
      return;
    }
    setBusyAction('update');
    setPageError(null);
    try {
      const nextServer = await updateClaudeMcpServer(server, {
        displayName,
        transport: editTransport,
        url: editTransport === 'stdio' ? null : url,
        stdioProfileKey: editTransport === 'stdio' ? stdioProfile : null,
        enabled: editEnabled,
      });
      setServer(nextServer);
      loadInventoryForServer(nextServer);
      setOperation(null);
      setEditing(false);
      setEditDisplayName(nextServer.display_name);
      setEditTransport((nextServer.transport ?? 'streamable_http') as EditTransport);
      setEditUrl(nextServer.url ?? '');
      setEditStdioProfile(nextServer.stdio_profile_key ?? '');
      setEditEnabled(nextServer.enabled);
    } catch (error) {
      setPageError(errorMessage(error, 'MCP Server 配置更新失败'));
    } finally {
      setBusyAction(null);
    }
  }, [
    busyAction,
    editDisplayName,
    editEnabled,
    editStdioProfile,
    editTransport,
    editUrl,
    loadInventoryForServer,
    server,
  ]);

  const remove = useCallback(async () => {
    if (busyAction || !server?.removable) return;
    if (!window.confirm(`移除 MCP 服务“${serverName}”？此操作会移除服务配置和已保存的认证信息（如有）。`)) return;
    setBusyAction('remove');
    setPageError(null);
    try {
      await removeClaudeMcpServer(serverName);
      onBack();
    } catch (error) {
      setPageError(errorMessage(error, 'MCP 服务移除失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, onBack, server, serverName]);

  const tabCounts = {
    tools: inventory?.capabilities.tools.count,
    resources: inventory?.capabilities.resources.count,
    prompts: inventory?.capabilities.prompts.count,
  };
  const statusPalette = tonePalette(stateTone(effectiveState));

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: isMobile ? '1rem' : '1.2rem',
        width: '100%',
        border: DASHED_PAGE_BORDER,
        borderRadius: '1.05rem',
        background: 'transparent',
        padding: isMobile ? '0.85rem' : '1rem 1.08rem 1.12rem',
      }}
    >
      <nav aria-label="MCP 链接器具体配置页面导航" style={{ display: 'flex', alignItems: 'center', gap: '0.42rem', flexWrap: 'wrap', color: 'var(--color-text-secondary)', fontSize: '0.84rem' }}>
        <button type="button" onClick={onBack} style={{ ...actionStyle(), background: SOFT_ROW_SURFACE, padding: '0.48rem 0.82rem' }}>
          <IconChevronLeft style={{ width: '0.88rem', height: '0.88rem' }} />
          资源连接器
        </button>
        <IconChevronRight style={{ width: '0.78rem', height: '0.78rem', color: 'var(--color-text-muted)' }} />
        <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>Claude MCP</span>
        <IconChevronRight style={{ width: '0.78rem', height: '0.78rem', color: 'var(--color-text-muted)' }} />
        <span style={{ fontWeight: 700, color: 'var(--color-text-primary)', overflowWrap: 'anywhere' }}>{serverName}</span>
      </nav>

      <section style={{ display: 'grid', gap: '0.72rem', padding: isMobile ? '0.15rem 0 0.25rem' : '0.2rem 0 0.35rem' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.9rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.72rem', minWidth: 0, flex: '1 1 26rem' }}>
            {loading ? <SkeletonCircle size="2.2rem" /> : (
              <span aria-hidden="true" style={{ width: '2.2rem', height: '2.2rem', flexShrink: 0, borderRadius: '0.72rem', background: 'color-mix(in srgb, var(--color-text-primary) 8%, var(--color-bg-surface))', display: 'grid', placeItems: 'center', color: 'var(--color-text-primary)' }}>
                <IconDatabase style={{ width: '1rem', height: '1rem' }} />
              </span>
            )}
            <div style={{ minWidth: 0 }}>
              {loading ? (
                <div style={{ display: 'grid', gap: '0.4rem', minWidth: '16rem' }}>
                  <SkeletonBar width="15rem" height="0.95rem" />
                  <SkeletonBar width="22rem" height="0.72rem" />
                </div>
              ) : (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
                    <h1 style={{ margin: 0, fontSize: isMobile ? '1.08rem' : '1.22rem', lineHeight: 1.18, fontWeight: 700, color: 'var(--color-text-primary)', overflowWrap: 'anywhere' }}>
                      {serverName} MCP Server
                    </h1>
                    <Pill tone={stateTone(effectiveState)}>
                      <span aria-hidden="true" style={{ width: '0.4rem', height: '0.4rem', borderRadius: '999px', background: statusPalette.color }} />
                      {connectionStateLabel(server, effectiveState)}
                    </Pill>
                  </div>
                  <p style={{ margin: '0.28rem 0 0', maxWidth: '48rem', color: 'var(--color-text-secondary)', fontSize: '0.78rem', lineHeight: 1.5 }}>
                    {connectionSummary(server, effectiveState, inventory?.tool_count)}
                  </p>
                </>
              )}
            </div>
          </div>

          {!loading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', justifyContent: isMobile ? 'flex-start' : 'flex-end' }}>
              {server && (!effectiveState || !ACTIVE_STATES.includes(effectiveState)) ? (
                <button type="button" onClick={() => setEditing((value) => !value)} disabled={Boolean(busyAction)} style={{ ...actionStyle(), opacity: busyAction ? 0.62 : 1 }}>
                  {editing ? '取消编辑' : '编辑配置'}
                </button>
              ) : null}
              {canStartAuth(server, effectiveState) && (!effectiveState || !ACTIVE_STATES.includes(effectiveState)) ? (
                <button type="button" onClick={() => void startAuth()} disabled={Boolean(busyAction)} style={{ ...actionStyle(true), opacity: busyAction ? 0.62 : 1 }}>
                  {busyAction === 'auth' ? <IconLoader style={{ width: '0.88rem', height: '0.88rem' }} /> : <IconShare style={{ width: '0.88rem', height: '0.88rem' }} />}
                  {effectiveState === 'connected' && authStateOf(server) === 'anonymous'
                    ? '尝试认证'
                    : effectiveState === 'connected' ? '重新认证' : '开始认证'}
                </button>
              ) : null}
              {canLogout(server, effectiveState) ? (
                <button type="button" onClick={() => void logout()} disabled={Boolean(busyAction)} style={{ ...actionStyle(false, true), opacity: busyAction ? 0.62 : 1 }}>
                  {busyAction === 'logout' ? <IconLoader style={{ width: '0.88rem', height: '0.88rem' }} /> : <IconX style={{ width: '0.88rem', height: '0.88rem' }} />}
                  退出认证
                </button>
              ) : null}
              {server?.removable && (!effectiveState || !ACTIVE_STATES.includes(effectiveState)) ? (
                <button type="button" onClick={() => void remove()} disabled={Boolean(busyAction)} style={{ ...actionStyle(false, true), opacity: busyAction ? 0.62 : 1 }}>
                  <IconTrash style={{ width: '0.88rem', height: '0.88rem' }} />
                  移除
                </button>
              ) : null}
            </div>
          ) : null}
        </div>

        {!loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
            <InfoChip label="认证" value={AUTH_STATE_LABELS[authStateOf(server)]} />
            <InfoChip label="连接" value={effectiveState ? STATE_LABELS[effectiveState] : '未知'} />
            <InfoChip label="管理" value={capability?.management_mode === 'managed_db' ? 'Dream 数据库' : '不可用'} />
            <InfoChip label="配置" value={`${server?.config_scope ?? 'user'} · revision ${server?.revision ?? '—'}`} />
            <InfoChip label="传输" value={inventory?.transport ?? server?.transport ?? '未报告'} />
            <InfoChip label="URL" value={inventory?.url ?? server?.url ?? '未报告'} />
            <InfoChip label="最近探测" value={formatDateTime(inventory?.refreshed_at)} />
          </div>
        ) : null}

        {editing && server ? (
          <form
            aria-label="编辑 MCP Server 配置"
            onSubmit={(event) => {
              event.preventDefault();
              void saveConfiguration();
            }}
            style={{ display: 'grid', gap: '0.7rem', padding: '0.8rem', border: SOFT_CONTROL_BORDER, borderRadius: '0.9rem', background: SOFT_ROW_SURFACE }}
          >
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, minmax(0, 1fr))', gap: '0.65rem' }}>
              <label style={{ display: 'grid', gap: '0.3rem', color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>
                显示名称
                <input value={editDisplayName} onChange={(event) => setEditDisplayName(event.target.value)} maxLength={200} style={{ border: SOFT_CONTROL_BORDER, borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem' }} />
              </label>
              <label style={{ display: 'grid', gap: '0.3rem', color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>
                传输
                <select value={editTransport} onChange={(event) => {
                  const next = event.target.value as EditTransport;
                  setEditTransport(next);
                }} style={{ border: SOFT_CONTROL_BORDER, borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem' }}>
                  <option value="streamable_http">Streamable HTTP</option>
                  <option value="sse">SSE</option>
                  <option value="stdio">stdio profile</option>
                </select>
              </label>
              {editTransport === 'stdio' ? (
                <label style={{ display: 'grid', gap: '0.3rem', color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>
                  服务端 profile key
                  <input value={editStdioProfile} onChange={(event) => setEditStdioProfile(event.target.value)} maxLength={128} autoComplete="off" spellCheck={false} style={{ border: SOFT_CONTROL_BORDER, borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem' }} />
                </label>
              ) : (
                <label style={{ display: 'grid', gap: '0.3rem', color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>
                  MCP URL
                  <input type="url" value={editUrl} onChange={(event) => setEditUrl(event.target.value)} autoComplete="off" spellCheck={false} style={{ border: SOFT_CONTROL_BORDER, borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem' }} />
                </label>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.7rem', flexWrap: 'wrap' }}>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', color: 'var(--color-text-secondary)', fontSize: '0.76rem' }}>
                <input type="checkbox" checked={editEnabled} onChange={(event) => setEditEnabled(event.target.checked)} />
                启用此 Server
              </label>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>修改 endpoint 或 transport 会清除旧凭据与 inventory，并由后端重新判断认证要求。</span>
                <button type="submit" disabled={Boolean(busyAction)} style={{ ...actionStyle(true), opacity: busyAction ? 0.62 : 1 }}>
                  {busyAction === 'update' ? <IconLoader style={{ width: '0.82rem', height: '0.82rem' }} /> : <IconCheck style={{ width: '0.82rem', height: '0.82rem' }} />}
                  保存配置
                </button>
              </div>
            </div>
          </form>
        ) : null}

        {operation && ACTIVE_STATES.includes(operation.state) ? (
          <div style={{ display: 'grid', gap: '0.58rem', borderLeft: '2px solid color-mix(in srgb, var(--color-border-paper) 70%, transparent)', padding: '0.12rem 0 0.16rem 0.72rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.8rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.78rem', lineHeight: 1.55 }}>
                {operation.state === 'waiting_for_user'
                  ? '在浏览器完成授权后会自动回到 Dream；无需复制或粘贴 redirect URL。'
                  : `认证状态：${STATE_LABELS[operation.state]}`}
              </div>
              <button type="button" onClick={() => void cancelAuth()} disabled={Boolean(busyAction)} style={actionStyle()}>
                取消
              </button>
            </div>
            {operation.state === 'waiting_for_user' ? (
              <>
                <a href={operation.authorization_url ?? undefined} target="_blank" rel="noreferrer" style={{ ...actionStyle(true), width: 'fit-content', textDecoration: 'none' }}>
                  <IconShare style={{ width: '0.82rem', height: '0.82rem' }} />
                  打开授权页面
                </a>
              </>
            ) : null}
          </div>
        ) : null}
      </section>

      {pageError ? <div role="alert" style={{ borderRadius: '0.9rem', background: 'color-mix(in srgb, var(--color-state-error) 10%, var(--color-bg-paper))', color: 'var(--color-state-error)', padding: '0.75rem 0.9rem', fontSize: '0.82rem' }}>{pageError}</div> : null}

      <section aria-label="MCP 使用策略" style={{ display: 'grid', gap: '0.28rem', padding: '0.1rem 0 0.25rem' }}>
        <h2 style={{ margin: 0, color: 'var(--color-text-primary)', fontSize: '0.9rem', fontWeight: 700 }}>使用策略</h2>
        <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: '0.78rem', lineHeight: 1.5 }}>
          此页面只发现能力，不执行工具。Chat 中的工具调用继续遵循现有权限确认与沙箱策略。
        </p>
      </section>

      <DetailSection
        title="能力与工具"
        subtitle="进入详情页后，Dream 会通过标准 MCP SDK 自动发现 Tools、Resources 与 Prompts；列表页不会触发远端连接。"
        action={activeTab === 'tools' ? (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <label style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
              <IconSearch aria-hidden="true" style={{ position: 'absolute', left: '0.75rem', width: '0.78rem', height: '0.78rem', color: 'var(--color-text-muted)' }} />
              <input
                aria-label="搜索 MCP 工具"
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="搜索工具"
                style={{ width: isMobile ? '100%' : '13.5rem', border: SOFT_CONTROL_BORDER, borderRadius: '999px', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.58rem 0.82rem 0.58rem 2rem', fontSize: '0.8rem' }}
              />
            </label>
            <select aria-label="筛选 MCP 工具风险" value={toolFilter} onChange={(event) => setToolFilter(event.target.value as ToolFilter)} style={{ border: SOFT_CONTROL_BORDER, borderRadius: '999px', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.58rem 0.82rem', fontSize: '0.8rem' }}>
              <option value="all">全部标签</option>
              <option value="read_only">只读</option>
              <option value="destructive">破坏性</option>
              <option value="open_world">开放世界</option>
              <option value="unspecified">未声明</option>
            </select>
          </div>
        ) : null}
      >
        <div role="tablist" aria-label="MCP 能力" style={{ display: 'flex', alignItems: 'center', gap: '0.38rem', flexWrap: 'wrap', padding: '0.18rem 0 0.7rem' }}>
          {(['tools', 'resources', 'prompts'] as const).map((tab) => {
            const label = tab === 'tools' ? 'Tools' : tab === 'resources' ? 'Resources' : 'Prompts';
            const count = tabCounts[tab];
            return (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={activeTab === tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  border: 'none',
                  borderRadius: '999px',
                  background: activeTab === tab ? 'var(--color-text-primary)' : SOFT_ROW_SURFACE,
                  color: activeTab === tab ? 'var(--color-bg-app)' : 'var(--color-text-secondary)',
                  padding: '0.5rem 0.74rem',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {label} {typeof count === 'number' ? count : '—'}
              </button>
            );
          })}
        </div>

        {activeTab === 'tools' ? (
          <div aria-label="MCP 工具列表" style={{ background: 'color-mix(in srgb, var(--color-bg-paper) 34%, transparent)', borderRadius: '0.8rem', padding: '0 0.15rem' }}>
            {inventoryLoading && !inventory ? <SkeletonList rows={5} /> : null}
            {inventoryError ? (
              <div role="alert" style={{ padding: '0.9rem', color: 'var(--color-state-error)', fontSize: '0.8rem' }}>{inventoryError}</div>
            ) : null}
            {!inventoryLoading && !inventoryError && !inventory ? (
              <div style={{ padding: '0.9rem', color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>{server?.enabled ? '正在自动读取工具清单。' : '该 Server 已禁用。'}</div>
            ) : null}
            {!inventoryLoading && inventory && visibleTools.length === 0 ? (
              <div style={{ padding: '0.9rem', color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
                {inventory.status === 'needs_auth'
                  ? '完成 OAuth 后将自动加载工具。'
                  : inventory.status === 'failed'
                    ? '连接失败，未能读取工具清单。'
                    : inventory.tool_count === 0
                      ? '该服务没有报告工具。'
                      : '没有匹配当前搜索和风险筛选的工具。'}
              </div>
            ) : null}
            {visibleTools.map((tool) => <ToolRow key={tool.name} tool={tool} />)}
            {inventory?.tools_truncated ? (
              <div style={{ padding: '0.72rem', color: 'var(--color-state-warning)', fontSize: '0.76rem' }}>工具数量超过安全展示上限，当前仅显示前 {inventory.tools.length} 项。</div>
            ) : null}
          </div>
        ) : activeTab === 'resources' ? (
          <div style={{ display: 'grid', gap: '0.35rem' }}>
            {(inventory?.resources ?? []).map((resource) => (
              <article key={resource.uri} style={{ padding: '0.72rem', borderBottom: SOFT_ROW_DIVIDER }}>
                <strong style={{ color: 'var(--color-text-primary)', overflowWrap: 'anywhere' }}>{resource.name}</strong>
                <div style={{ marginTop: '0.2rem', color: 'var(--color-text-muted)', fontSize: '0.74rem', overflowWrap: 'anywhere' }}>{resource.uri}</div>
                {resource.description ? <p style={{ margin: '0.28rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.76rem' }}>{resource.description}</p> : null}
              </article>
            ))}
            {!inventory ? <div style={{ padding: '0.9rem', color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>正在自动读取 Resources。</div> : null}
            {inventory && inventory.resources.length === 0 ? <div style={{ padding: '0.9rem', color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>该 Server 没有报告 Resources。</div> : null}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '0.35rem' }}>
            {(inventory?.prompts ?? []).map((prompt) => (
              <article key={prompt.name} style={{ padding: '0.72rem', borderBottom: SOFT_ROW_DIVIDER }}>
                <strong style={{ color: 'var(--color-text-primary)', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }}>{prompt.name}</strong>
                {prompt.description ? <p style={{ margin: '0.28rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.76rem' }}>{prompt.description}</p> : null}
              </article>
            ))}
            {!inventory ? <div style={{ padding: '0.9rem', color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>正在自动读取 Prompts。</div> : null}
            {inventory && inventory.prompts.length === 0 ? <div style={{ padding: '0.9rem', color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>该 Server 没有报告 Prompts。</div> : null}
          </div>
        )}
      </DetailSection>

      {operation && operationErrorMessage(operation) ? <div role="alert" style={{ color: 'var(--color-state-error)', fontSize: '0.78rem' }}>{operationErrorMessage(operation)}</div> : null}
      {inventory?.server_info ? (
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>
          <span>Server info</span>
          <strong style={{ color: 'var(--color-text-secondary)' }}>{inventory.server_info.name}</strong>
          <span>{inventory.server_info.version}</span>
          <span aria-hidden="true">·</span>
          <span><IconCheck style={{ width: '0.7rem', height: '0.7rem', verticalAlign: 'middle' }} /> 只读探测完成</span>
        </div>
      ) : null}
    </div>
  );
}
