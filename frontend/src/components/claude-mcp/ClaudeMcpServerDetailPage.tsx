// [Input] One actor-owned Claude MCP server name, typed claude-mcp APIs, and Settings navigation callbacks.
// [Output] Notion-aligned MCP detail workbench with Runtime-gated auth actions, anonymous feedback, and searchable read-only tool inventory.
// [Pos] Server detail surface in the frontend claude-mcp business domain.
// [Sync] 2026-08-20: add public-SDK tool discovery without `/mcp` TUI parsing or remote tool execution.
// [Sync] 2026-08-25: separate anonymous, required, authenticated, and rollback-compatible unknown auth actions.

import { useCallback, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react';
import {
  cancelClaudeMcpAuth,
  getClaudeMcpCapability,
  getClaudeMcpOperation,
  getClaudeMcpServer,
  getClaudeMcpServerInventory,
  logoutClaudeMcpServer,
  removeClaudeMcpServer,
  startClaudeMcpAuth,
  submitClaudeMcpRedirect,
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
  const authState = authStateOf(server);
  return (state === 'needs_auth' && authState === 'required')
    || (state === 'connected' && (authState === 'anonymous' || authState === 'authenticated'));
}

function canLogout(server: ClaudeMcpServer | null, state: ClaudeMcpState | undefined): boolean {
  const authState = authStateOf(server);
  return state === 'connected' && (authState === 'authenticated' || authState === 'unknown');
}

function canDetectConnection(server: ClaudeMcpServer | null, state: ClaudeMcpState | undefined): boolean {
  return state === 'configured'
    || state === 'failed'
    || state === 'logged_out'
    || (state === 'needs_auth' && authStateOf(server) === 'unknown');
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
    return '连接探测失败。请先重试状态探测；此状态不会自动启动 OAuth。';
  }
  return '先检测 MCP 连接；只有 Runtime 明确报告需要认证时才会启动 OAuth。';
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
  const [redirectUrl, setRedirectUrl] = useState('');
  const [activeTab, setActiveTab] = useState<CapabilityTab>('tools');
  const [searchQuery, setSearchQuery] = useState('');
  const [toolFilter, setToolFilter] = useState<ToolFilter>('all');
  const [loading, setLoading] = useState(true);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [inventoryError, setInventoryError] = useState<string | null>(null);

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
    setInventoryLoading(true);
    setInventoryError(null);
    try {
      const next = await getClaudeMcpServerInventory(serverName);
      setInventory(next);
    } catch (error) {
      setInventory(null);
      setInventoryError(errorMessage(error, 'MCP 工具清单读取失败'));
    } finally {
      setInventoryLoading(false);
    }
  }, [serverName]);

  const load = useCallback(async () => {
    setLoading(true);
    setPageError(null);
    try {
      const [nextCapability, nextServer] = await Promise.all([
        getClaudeMcpCapability(),
        getClaudeMcpServer(serverName),
      ]);
      setCapability(nextCapability);
      setServer(nextServer);
      if (nextServer.active_operation_id) {
        setOperation(await getClaudeMcpOperation(nextServer.active_operation_id));
      }
      if (nextServer.state === 'connected') {
        await loadInventory();
      } else {
        setInventory(null);
      }
    } catch (error) {
      setPageError(errorMessage(error, 'Claude MCP 服务详情读取失败'));
    } finally {
      setLoading(false);
    }
  }, [loadInventory, serverName]);

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
            setRedirectUrl('');
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
      setOperation(await startClaudeMcpAuth(serverName));
    } catch (error) {
      setPageError(errorMessage(error, '认证启动失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, effectiveState, server, serverName]);

  const submitRedirect = useCallback(async () => {
    if (!operation || !redirectUrl.trim() || busyAction) return;
    setBusyAction('redirect');
    setPageError(null);
    try {
      setOperation(await submitClaudeMcpRedirect(operation.id, redirectUrl.trim()));
      setRedirectUrl('');
    } catch (error) {
      setPageError(errorMessage(error, 'redirect URL 提交失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, operation, redirectUrl]);

  const cancelAuth = useCallback(async () => {
    if (!operation || busyAction) return;
    setBusyAction('cancel');
    setPageError(null);
    try {
      setOperation(await cancelClaudeMcpAuth(operation.id));
      setRedirectUrl('');
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
      const nextServer = await logoutClaudeMcpServer(serverName);
      setServer(nextServer);
      setOperation(null);
      if (nextServer.state === 'connected') {
        await loadInventory();
      } else {
        setInventory(null);
      }
    } catch (error) {
      setPageError(errorMessage(error, '退出认证失败'));
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, loadInventory, serverName]);

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
              {canDetectConnection(server, effectiveState) && (!effectiveState || !ACTIVE_STATES.includes(effectiveState)) ? (
                <button type="button" onClick={() => void load()} disabled={Boolean(busyAction) || loading} style={{ ...actionStyle(effectiveState === 'failed'), opacity: busyAction || loading ? 0.62 : 1 }}>
                  {loading ? <IconLoader style={{ width: '0.88rem', height: '0.88rem' }} /> : <IconShare style={{ width: '0.88rem', height: '0.88rem' }} />}
                  {effectiveState === 'failed' ? '重试状态探测' : '检测连接'}
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
            <InfoChip label="CLI" value={capability?.cli_version ?? '未验证'} />
            <InfoChip label="配置" value={`${inventory?.config_scope ?? 'user'} · ${inventory?.runtime_scope ?? '等待探测'}`} />
            <InfoChip label="传输" value={inventory?.transport ?? server?.transport ?? '未报告'} />
            <InfoChip label="URL" value={inventory?.url ?? '未报告'} />
            <InfoChip label="最近探测" value={formatDateTime(inventory?.refreshed_at)} />
          </div>
        ) : null}

        {operation && ACTIVE_STATES.includes(operation.state) ? (
          <div style={{ display: 'grid', gap: '0.58rem', borderLeft: '2px solid color-mix(in srgb, var(--color-border-paper) 70%, transparent)', padding: '0.12rem 0 0.16rem 0.72rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.8rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.78rem', lineHeight: 1.55 }}>
                {operation.state === 'waiting_for_user'
                  ? '在浏览器完成授权后，粘贴最终跳转的完整 redirect URL。该值只写入当前 CLI 进程。'
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
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <input
                    aria-label={`${serverName} redirect URL`}
                    type="url"
                    autoComplete="off"
                    spellCheck={false}
                    value={redirectUrl}
                    onChange={(event) => setRedirectUrl(event.target.value)}
                    placeholder="完整 redirect URL"
                    style={{ flex: '1 1 20rem', minWidth: 0, border: SOFT_CONTROL_BORDER, borderRadius: '999px', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.82rem' }}
                  />
                  <button type="button" onClick={() => void submitRedirect()} disabled={!redirectUrl.trim() || Boolean(busyAction)} style={{ ...actionStyle(true), opacity: !redirectUrl.trim() || busyAction ? 0.62 : 1 }}>
                    提交并连接
                  </button>
                </div>
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
        subtitle="工具清单来自公开 Agent SDK 状态接口；安全标签只展示 MCP server 明确声明的注解。"
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
            <button type="button" onClick={() => void loadInventory()} disabled={inventoryLoading || effectiveState !== 'connected'} style={{ ...actionStyle(), opacity: inventoryLoading || effectiveState !== 'connected' ? 0.62 : 1 }}>
              {inventoryLoading ? <IconLoader style={{ width: '0.82rem', height: '0.82rem' }} /> : <IconShare style={{ width: '0.82rem', height: '0.82rem' }} />}
              重新探测
            </button>
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
              <div role="alert" style={{ display: 'grid', gap: '0.55rem', padding: '0.9rem', color: 'var(--color-state-error)', fontSize: '0.8rem' }}>
                <span>{inventoryError}</span>
                <button type="button" onClick={() => void loadInventory()} style={{ ...actionStyle(), width: 'fit-content' }}>重试探测</button>
              </div>
            ) : null}
            {!inventoryLoading && !inventoryError && effectiveState !== 'connected' ? (
              <div style={{ padding: '0.9rem', color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>MCP 连接成功后即可读取工具清单；是否需要认证由 Runtime 探测结果决定。</div>
            ) : null}
            {!inventoryLoading && inventory && visibleTools.length === 0 ? (
              <div style={{ padding: '0.9rem', color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
                {inventory.tool_count === 0 ? '该服务没有报告工具。' : '没有匹配当前搜索和风险筛选的工具。'}
              </div>
            ) : null}
            {visibleTools.map((tool) => <ToolRow key={tool.name} tool={tool} />)}
            {inventory?.tools_truncated ? (
              <div style={{ padding: '0.72rem', color: 'var(--color-state-warning)', fontSize: '0.76rem' }}>工具数量超过安全展示上限，当前仅显示前 {inventory.tools.length} 项。</div>
            ) : null}
          </div>
        ) : (
          <div style={{ borderLeft: '2px solid color-mix(in srgb, var(--color-border-paper) 70%, transparent)', padding: '0.25rem 0 0.25rem 0.75rem', color: 'var(--color-text-secondary)', fontSize: '0.8rem', lineHeight: 1.6 }}>
            目前公开的 <code>get_mcp_status()</code> 契约不返回 {activeTab === 'resources' ? 'Resources' : 'Prompts'} 清单。这里不会解析 <code>/mcp</code> TUI 或伪造数量；待正式 SDK 提供后再接入。
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
