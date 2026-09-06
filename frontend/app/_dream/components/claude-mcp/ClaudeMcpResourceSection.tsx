// [Input] Database-managed Claude MCP capability/CRUD/server/operation DTOs and shared design tokens/icons.
// [Output] Fast DB-backed server list, transport-safe create form, detail navigation, OAuth handoff, logout, and removal UI.
// [Pos] `claude-mcp` feature surface embedded by the Settings Resources page.
// [Sync] 2026-08-19: add the reviewed minimal MCP resource connector interaction.
// [Sync] 2026-08-19: enable user-owned HTTPS add/remove and correct the cross-platform capability message.
// [Sync] 2026-08-20: add the Notion-style server detail handoff for tool inventory and metadata.
// [Sync] 2026-08-21: accept absolute HTTP(S) URLs and remove only backend-confirmed user-scope servers.
// [Sync] 2026-08-25: gate authentication actions on authoritative connection/auth state, expose anonymous connectivity, and let backend removability govern every non-active server.
// [Sync] 2026-08-25: decouple list from discovery and expose managed HTTP/SSE/stdio-profile creation.
// [Sync] 2026-08-25: remove user-selected authentication; backend discovery alone classifies anonymous versus OAuth-required Servers.
// [Sync] 2026-08-25: replace redirect URL copy/paste with same-origin automatic SPA callback submission.
// [Sync] 2026-08-25: describe detail inventory as automatic; the list remains database-only and never discovers remotely.
// [Sync] 2026-08-27: automatically retry transient capability verification without misreporting a missing migration.

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  cancelClaudeMcpAuth,
  configureClaudeMcpServer,
  getClaudeMcpCapability,
  getClaudeMcpOperation,
  listClaudeMcpServers,
  logoutClaudeMcpServer,
  removeClaudeMcpServer,
  startClaudeMcpAuth,
  ClaudeMcpApiError,
  type ClaudeMcpCapability,
  type ClaudeMcpAuthState,
  type ClaudeMcpConfigScope,
  type ClaudeMcpOperation,
  type ClaudeMcpServer,
  type ClaudeMcpState,
} from '../../api/claudeMcpApi';
import {
  forgetClaudeMcpOAuthOperation,
  rememberClaudeMcpOAuthOperation,
} from './oauthHandoff';
import { IconCheck, IconChevronRight, IconDatabase, IconLoader, IconX } from '../chat/Icons';

const OPERATION_POLL_INTERVAL_MS = 1200;
const CAPABILITY_RETRY_INTERVAL_MS = 2000;
const CAPABILITY_UNAVAILABLE = 'CLAUDE_MCP_SCHEMA_CAPABILITY_UNAVAILABLE';
const ACTIVE_STATES: ClaudeMcpState[] = [
  'auth_starting',
  'waiting_for_user',
  'exchanging_code',
  'cancelling',
];

const STATE_LABELS: Record<ClaudeMcpState, string> = {
  not_configured: '未配置',
  configured: '已配置',
  needs_auth: '需要认证',
  auth_starting: '正在启动',
  waiting_for_user: '等待授权',
  exchanging_code: '正在连接',
  connected: '已连接',
  failed: '连接失败',
  cancelling: '正在取消',
  logged_out: '已退出',
  disabled: '不可用',
};

const SCOPE_LABELS: Record<ClaudeMcpConfigScope, string> = {
  user: '用户配置',
  workspace: '工作空间配置',
  local: '本地项目配置',
  project: '共享项目配置',
  plugin: '插件配置',
  unknown: '来源未知',
};

const AUTH_STATE_LABELS: Record<ClaudeMcpAuthState, string> = {
  anonymous: '匿名连接，无需 OAuth',
  required: '需要认证',
  authenticated: '已认证',
  unknown: '认证状态未知',
};

function authStateOf(server: ClaudeMcpServer): ClaudeMcpAuthState {
  return server.auth_state ?? 'unknown';
}

function serverStatusLabel(server: ClaudeMcpServer, state: ClaudeMcpState): string {
  if (state === 'connected') return AUTH_STATE_LABELS[authStateOf(server)];
  if (state === 'configured' && authStateOf(server) === 'unknown') return '已配置，等待检测连接';
  return STATE_LABELS[state];
}

function canStartAuth(server: ClaudeMcpServer, state: ClaudeMcpState): boolean {
  return state === 'needs_auth' && authStateOf(server) === 'required';
}

function canLogout(server: ClaudeMcpServer, state: ClaudeMcpState): boolean {
  const authState = authStateOf(server);
  if (server.credential_configured) return true;
  return state === 'connected' && (authState === 'authenticated' || authState === 'unknown');
}

function canDetectConnection(server: ClaudeMcpServer, state: ClaudeMcpState): boolean {
  return state === 'configured'
    || state === 'failed'
    || state === 'logged_out'
    || (state === 'needs_auth' && authStateOf(server) === 'unknown');
}

function safeApiErrorMessage(cause: unknown, fallback: string): string {
  return cause instanceof ClaudeMcpApiError
    ? `${cause.message}（${cause.code}）`
    : fallback;
}

function safeOperationError(operation: ClaudeMcpOperation): string | null {
  return operation.error
    ? `${operation.error.message}（${operation.error.code}）`
    : null;
}

function actionButton(primary = false): React.CSSProperties {
  return {
    border: `1px solid ${primary ? 'var(--color-text-primary)' : 'var(--color-border-paper)'}`,
    borderRadius: '999px',
    background: primary ? 'var(--color-text-primary)' : 'var(--color-bg-surface)',
    color: primary ? 'var(--color-bg-paper)' : 'var(--color-text-primary)',
    padding: '0.52rem 0.82rem',
    fontSize: '0.76rem',
    fontWeight: 700,
    cursor: 'pointer',
  };
}

function messageForCapability(capability: ClaudeMcpCapability): string {
  if (capability.reason_code === 'CLAUDE_MCP_SCHEMA_CAPABILITY_MISSING') {
    return '当前 PostgreSQL 未发布或不匹配 Dream MCP 管理 capability；请核对 Admin Drizzle 0038 迁移状态。';
  }
  if (capability.reason_code === CAPABILITY_UNAVAILABLE) {
    return 'Dream 暂时无法核验 PostgreSQL capability，数据库恢复后页面会自动重试。';
  }
  return 'Dream MCP 管理能力暂不可用，请检查数据库 capability 与服务策略。';
}

function operationFor(
  operations: Record<string, ClaudeMcpOperation>,
  server: ClaudeMcpServer,
): ClaudeMcpOperation | null {
  if (server.active_operation_id && operations[server.active_operation_id]) {
    return operations[server.active_operation_id];
  }
  const matching = Object.values(operations)
    .filter((item) => item.server_name === server.name)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
  return matching.find((item) => ACTIVE_STATES.includes(item.state))
    ?? matching.find((item) => item.state === 'failed')
    ?? null;
}

export default function ClaudeMcpResourceSection({
  onOpenServerDetail,
}: {
  onOpenServerDetail?: (serverName: string) => void;
}) {
  const [capability, setCapability] = useState<ClaudeMcpCapability | null>(null);
  const [servers, setServers] = useState<ClaudeMcpServer[]>([]);
  const [operations, setOperations] = useState<Record<string, ClaudeMcpOperation>>({});
  const [loading, setLoading] = useState(true);
  const [busyServer, setBusyServer] = useState<string | null>(null);
  const [serverName, setServerName] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [serverTransport, setServerTransport] = useState<'streamable_http' | 'sse' | 'stdio'>('streamable_http');
  const [stdioProfileKey, setStdioProfileKey] = useState('');
  const [configuring, setConfiguring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [capabilityResult, serversResult] = await Promise.allSettled([
        getClaudeMcpCapability(),
        listClaudeMcpServers(),
      ]);
      if (capabilityResult.status === 'rejected') throw capabilityResult.reason;
      const nextCapability = capabilityResult.value;
      setCapability(nextCapability);
      if (!nextCapability.enabled) {
        setServers([]);
        return;
      }
      if (serversResult.status === 'rejected') throw serversResult.reason;
      const nextServers = serversResult.value;
      setServers(nextServers);
      const activeIds = nextServers
        .map((server) => server.active_operation_id)
        .filter((id): id is string => Boolean(id));
      const recovered = await Promise.all(activeIds.map(getClaudeMcpOperation));
      setOperations((current) => ({
        ...current,
        ...Object.fromEntries(recovered.map((operation) => [operation.id, operation])),
      }));
    } catch (cause) {
      setError(safeApiErrorMessage(cause, 'Claude MCP 状态读取失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (capability?.reason_code !== CAPABILITY_UNAVAILABLE) return undefined;
    const timer = window.setTimeout(() => {
      void load();
    }, CAPABILITY_RETRY_INTERVAL_MS);
    return () => window.clearTimeout(timer);
  }, [capability, load]);

  const activeOperationIds = useMemo(
    () => Object.values(operations)
      .filter((operation) => ACTIVE_STATES.includes(operation.state))
      .map((operation) => operation.id),
    [operations],
  );

  useEffect(() => {
    if (activeOperationIds.length === 0) return undefined;
    const timer = window.setInterval(() => {
      void Promise.all(activeOperationIds.map(getClaudeMcpOperation))
        .then((items) => {
          setOperations((current) => ({
            ...current,
            ...Object.fromEntries(items.map((operation) => [operation.id, operation])),
          }));
          if (items.some((item) => !ACTIVE_STATES.includes(item.state))) {
            items
              .filter((item) => !ACTIVE_STATES.includes(item.state))
              .forEach((item) => forgetClaudeMcpOAuthOperation(item.id));
            void load();
          }
        })
        .catch((cause: unknown) => {
          setError(safeApiErrorMessage(cause, '认证状态刷新失败'));
        });
    }, OPERATION_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [activeOperationIds, load]);

  const start = async (server: ClaudeMcpServer, state: ClaudeMcpState) => {
    if (!canStartAuth(server, state)) return;
    setBusyServer(server.name);
    setError(null);
    try {
      const operation = await startClaudeMcpAuth(server.name);
      if (!rememberClaudeMcpOAuthOperation(operation.id)) {
        await cancelClaudeMcpAuth(operation.id);
        throw new Error('browser operation handoff unavailable');
      }
      setOperations((current) => ({ ...current, [operation.id]: operation }));
    } catch (cause) {
      setError(safeApiErrorMessage(cause, '认证启动失败'));
    } finally {
      setBusyServer(null);
    }
  };

  const configure = async () => {
    const name = serverName.trim();
    const url = serverUrl.trim();
    const profileKey = stdioProfileKey.trim();
    if (!name || (serverTransport === 'stdio' ? !profileKey : !url)) {
      setError(serverTransport === 'stdio'
        ? '请填写 MCP 服务名称并选择服务端 stdio profile。'
        : '请填写 MCP 服务名称和完整 HTTP 或 HTTPS URL。');
      return;
    }
    setConfiguring(true);
    setError(null);
    try {
      const next = await configureClaudeMcpServer(
        name,
        serverTransport === 'stdio' ? null : url,
        {
          transport: serverTransport,
          stdioProfileKey: serverTransport === 'stdio' ? profileKey : null,
        },
      );
      setServers((current) => [
        ...current.filter((server) => server.name !== next.name),
        next,
      ]);
      setServerName('');
      setServerUrl('');
      setStdioProfileKey('');
    } catch (cause) {
      setError(safeApiErrorMessage(cause, 'MCP 服务配置失败'));
    } finally {
      setConfiguring(false);
    }
  };

  const cancel = async (operation: ClaudeMcpOperation) => {
    setBusyServer(operation.server_name);
    setError(null);
    try {
      const next = await cancelClaudeMcpAuth(operation.id);
      setOperations((current) => ({ ...current, [next.id]: next }));
      forgetClaudeMcpOAuthOperation(operation.id);
      await load();
    } catch (cause) {
      setError(safeApiErrorMessage(cause, '认证取消失败'));
    } finally {
      setBusyServer(null);
    }
  };

  const logout = async (serverName: string) => {
    setBusyServer(serverName);
    setError(null);
    try {
      const next = await logoutClaudeMcpServer(serverName);
      setServers((current) => current.map((server) => server.name === next.name ? next : server));
      setOperations((current) => Object.fromEntries(
        Object.entries(current).filter(([, operation]) => operation.server_name !== serverName),
      ));
    } catch (cause) {
      setError(safeApiErrorMessage(cause, '退出认证失败'));
    } finally {
      setBusyServer(null);
    }
  };

  const remove = async (name: string) => {
    setBusyServer(name);
    setError(null);
    try {
      await removeClaudeMcpServer(name);
      setServers((current) => current.filter((server) => server.name !== name));
      setOperations((current) => Object.fromEntries(
        Object.entries(current).filter(([, operation]) => operation.server_name !== name),
      ));
    } catch (cause) {
      setError(safeApiErrorMessage(cause, 'MCP 服务移除失败'));
    } finally {
      setBusyServer(null);
    }
  };

  return (
    <section aria-labelledby="claude-mcp-heading" style={{ display: 'grid', gap: '0.72rem' }}>
      <div>
        <h3 id="claude-mcp-heading" style={{ margin: 0, fontSize: '0.92rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
          Claude MCP 资源
        </h3>
        <p style={{ margin: '0.28rem 0 0', fontSize: '0.78rem', lineHeight: 1.55, color: 'var(--color-text-secondary)' }}>
          Server 列表直接读取 Dream 数据库，不等待远端连接；进入详情后会自动加载 Tools、Resources 与 Prompts。
        </p>
      </div>

      {loading ? (
        <div role="status" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
          <IconLoader style={{ width: '0.9rem', height: '0.9rem' }} />
          读取 Claude MCP 状态…
        </div>
      ) : null}

      {capability && !capability.enabled ? (
        <div role="status" style={{ border: '1px dashed var(--color-border-paper)', borderRadius: '1rem', padding: '0.9rem', background: 'var(--color-bg-surface)', color: 'var(--color-text-secondary)', fontSize: '0.78rem', lineHeight: 1.6 }}>
          <strong style={{ color: 'var(--color-text-primary)' }}>安全门禁已关闭此能力</strong>
          <div>{messageForCapability(capability)}</div>
        </div>
      ) : null}

      {capability?.enabled ? (
        <form
          aria-label="添加 Claude MCP 服务"
          onSubmit={(event) => {
            event.preventDefault();
            void configure();
          }}
          style={{ border: '1px solid var(--color-border-paper)', borderRadius: '1rem', padding: '0.9rem', background: 'var(--color-bg-surface)', display: 'grid', gap: '0.68rem' }}
        >
          <div>
            <strong style={{ fontSize: '0.8rem', color: 'var(--color-text-primary)' }}>添加 MCP 服务</strong>
            <p style={{ margin: '0.22rem 0 0', fontSize: '0.73rem', lineHeight: 1.5, color: 'var(--color-text-secondary)' }}>
              HTTP/SSE 只保存安全 URL；stdio 只能引用服务端批准的 profile，不接受浏览器命令、参数或环境变量。
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(8rem, 0.8fr) minmax(8rem, 0.65fr) minmax(12rem, 1.3fr)', gap: '0.55rem' }}>
            <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.73rem', color: 'var(--color-text-secondary)' }}>
              MCP 服务名称
              <input
                aria-label="MCP 服务名称"
                value={serverName}
                onChange={(event) => setServerName(event.target.value)}
                autoComplete="off"
                maxLength={128}
                required
                placeholder="例如 comfy-cloud"
                style={{ border: '1px solid var(--color-border-paper)', borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem', minWidth: 0 }}
              />
            </label>
            <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.73rem', color: 'var(--color-text-secondary)' }}>
              传输方式
              <select
                aria-label="MCP 传输方式"
                value={serverTransport}
                onChange={(event) => setServerTransport(event.target.value as typeof serverTransport)}
                style={{ border: '1px solid var(--color-border-paper)', borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem', minWidth: 0 }}
              >
                <option value="streamable_http">Streamable HTTP</option>
                <option value="sse">Legacy SSE</option>
                <option value="stdio">stdio profile</option>
              </select>
            </label>
            <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.73rem', color: 'var(--color-text-secondary)' }}>
              {serverTransport === 'stdio' ? '服务端 profile key' : 'MCP 服务 URL'}
              <input
                aria-label={serverTransport === 'stdio' ? 'MCP stdio profile key' : 'MCP 服务 URL'}
                type={serverTransport === 'stdio' ? 'text' : 'url'}
                value={serverTransport === 'stdio' ? stdioProfileKey : serverUrl}
                onChange={(event) => serverTransport === 'stdio'
                  ? setStdioProfileKey(event.target.value)
                  : setServerUrl(event.target.value)}
                autoComplete="off"
                spellCheck={false}
                maxLength={serverTransport === 'stdio' ? 128 : 2048}
                required
                placeholder={serverTransport === 'stdio' ? '例如 local-files-readonly' : 'https://mcp.example.com/mcp'}
                style={{ border: '1px solid var(--color-border-paper)', borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem', minWidth: 0 }}
              />
            </label>
          </div>
          <p style={{ margin: 0, fontSize: '0.72rem', lineHeight: 1.5, color: 'var(--color-text-muted)' }}>
            认证要求由 Dream 连接 Server 后自动判断；无需选择无认证或 OAuth。
          </p>
          <div>
            <button type="submit" disabled={configuring} style={actionButton(true)}>
              {configuring ? '正在添加…' : '添加 MCP 服务'}
            </button>
          </div>
        </form>
      ) : null}

      {capability?.enabled && !loading && servers.length === 0 ? (
        <div style={{ border: '1px dashed var(--color-border-paper)', borderRadius: '1rem', padding: '0.9rem', fontSize: '0.78rem', color: 'var(--color-text-secondary)' }}>
          尚未配置 MCP 服务。添加后列表会立即从数据库返回；进入详情页后自动加载远端能力清单。
        </div>
      ) : null}

      <div style={{ display: 'grid', gap: '0.72rem' }}>
        {servers.map((server) => {
          const operation = operationFor(operations, server);
          const state = operation && ACTIVE_STATES.includes(operation.state)
            ? operation.state
            : server.state;
          return (
            <article key={server.name} aria-label={`MCP 服务 ${server.name}`} style={{ border: '1px solid var(--color-border-paper)', borderRadius: '1rem', padding: '0.9rem', background: 'var(--color-bg-surface-solid)', display: 'grid', gap: '0.72rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.8rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                {onOpenServerDetail ? (
                  <button
                    type="button"
                    aria-label={`管理与工具 ${server.name}`}
                    onClick={() => onOpenServerDetail(server.name)}
                    style={{ flex: '1 1 18rem', display: 'flex', alignItems: 'center', gap: '0.68rem', minWidth: 0, border: 'none', background: 'transparent', color: 'inherit', padding: 0, textAlign: 'left', cursor: 'pointer' }}
                  >
                    <span style={{ width: '2.2rem', height: '2.2rem', borderRadius: '0.75rem', display: 'grid', placeItems: 'center', background: 'var(--color-bg-hover)', color: 'var(--color-text-primary)', flexShrink: 0 }}>
                      <IconDatabase style={{ width: '1rem', height: '1rem' }} />
                    </span>
                    <span style={{ minWidth: 0, flex: 1 }}>
                      <strong style={{ color: 'var(--color-text-primary)', overflowWrap: 'anywhere' }}>{server.name}</strong>
                      <span style={{ marginTop: '0.25rem', display: 'flex', gap: '0.3rem', alignItems: 'center', fontSize: '0.73rem', color: state === 'connected' ? 'var(--color-state-success)' : state === 'failed' ? 'var(--color-state-error)' : 'var(--color-text-muted)' }}>
                        {state === 'connected' ? <IconCheck style={{ width: '0.78rem', height: '0.78rem' }} /> : state === 'failed' ? <IconX style={{ width: '0.78rem', height: '0.78rem' }} /> : null}
                        {serverStatusLabel(server, state)} · {SCOPE_LABELS[server.config_scope || 'unknown']}
                      </span>
                    </span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.28rem', color: 'var(--color-action-link)', fontSize: '0.74rem', fontWeight: 700, flexShrink: 0 }}>
                      管理与工具
                      <IconChevronRight style={{ width: '0.82rem', height: '0.82rem' }} />
                    </span>
                  </button>
                ) : (
                  <div style={{ display: 'flex', gap: '0.68rem', minWidth: 0 }}>
                    <span style={{ width: '2.2rem', height: '2.2rem', borderRadius: '0.75rem', display: 'grid', placeItems: 'center', background: 'var(--color-bg-hover)', color: 'var(--color-text-primary)' }}>
                      <IconDatabase style={{ width: '1rem', height: '1rem' }} />
                    </span>
                    <div style={{ minWidth: 0 }}>
                      <strong style={{ color: 'var(--color-text-primary)', overflowWrap: 'anywhere' }}>{server.name}</strong>
                      <div style={{ marginTop: '0.25rem', fontSize: '0.73rem', color: state === 'connected' ? 'var(--color-state-success)' : 'var(--color-text-muted)' }}>{serverStatusLabel(server, state)} · {SCOPE_LABELS[server.config_scope || 'unknown']}</div>
                    </div>
                  </div>
                )}
                <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
                  {canLogout(server, state) ? (
                    <button type="button" onClick={() => void logout(server.name)} disabled={busyServer === server.name} style={actionButton()}>
                      退出认证
                    </button>
                  ) : null}
                  {canStartAuth(server, state) && !ACTIVE_STATES.includes(state) ? (
                    <button type="button" onClick={() => void start(server, state)} disabled={busyServer === server.name} style={actionButton(true)}>
                      {state === 'connected' && authStateOf(server) === 'anonymous'
                        ? '尝试认证'
                        : state === 'connected' ? '重新认证' : '开始认证'}
                    </button>
                  ) : null}
                  {canDetectConnection(server, state) && !ACTIVE_STATES.includes(state) ? (
                    <button type="button" onClick={() => void load()} disabled={loading || busyServer === server.name} style={actionButton(state === 'failed')}>
                      刷新数据库状态
                    </button>
                  ) : null}
                  {operation && ACTIVE_STATES.includes(operation.state) ? (
                    <button type="button" onClick={() => void cancel(operation)} disabled={busyServer === server.name} style={actionButton()}>
                      取消
                    </button>
                  ) : null}
                  {server.removable && !ACTIVE_STATES.includes(state) ? (
                    <button type="button" onClick={() => void remove(server.name)} disabled={busyServer === server.name} style={actionButton()}>
                      移除
                    </button>
                  ) : null}
                  {!server.removable && server.config_scope && server.config_scope !== 'unknown' ? (
                    <span style={{ alignSelf: 'center', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                      请从{SCOPE_LABELS[server.config_scope]}来源管理
                    </span>
                  ) : null}
                </div>
              </div>

              {operation?.state === 'waiting_for_user' ? (
                <div style={{ display: 'grid', gap: '0.55rem', paddingTop: '0.68rem', borderTop: '1px solid var(--color-border-paper)' }}>
                  <p style={{ margin: 0, fontSize: '0.76rem', lineHeight: 1.55, color: 'var(--color-text-secondary)' }}>
                    在浏览器完成授权后会自动回到 Dream；无需复制或粘贴 redirect URL。Token 仅加密存入专用凭据表。
                  </p>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <a href={operation.authorization_url ?? undefined} target="_blank" rel="noreferrer" style={{ ...actionButton(true), textDecoration: 'none' }}>
                      打开授权页面
                    </a>
                  </div>
                </div>
              ) : null}

              {operation && safeOperationError(operation) ? (
                <div role="alert" style={{ fontSize: '0.75rem', color: 'var(--color-state-error)' }}>
                  {safeOperationError(operation)}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      {error ? <div role="alert" style={{ fontSize: '0.78rem', color: 'var(--color-state-error)' }}>{error}</div> : null}
    </section>
  );
}
