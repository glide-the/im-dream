// [Input] Claude MCP API capability/configuration/server/operation DTOs and shared design tokens/icons.
// [Output] Runtime-gated HTTP(S) discovery, anonymous/authenticated feedback, detail navigation, browser OAuth handoff, recovery, logout, and removal UI.
// [Pos] `claude-mcp` feature surface embedded by the Settings Resources page.
// [Sync] 2026-08-19: add the reviewed minimal MCP resource connector interaction.
// [Sync] 2026-08-19: enable user-owned HTTPS add/remove and correct the cross-platform capability message.
// [Sync] 2026-08-20: add the Notion-style server detail handoff for tool inventory and metadata.
// [Sync] 2026-08-21: accept absolute HTTP(S) URLs and remove only backend-confirmed user-scope servers.
// [Sync] 2026-08-25: gate authentication actions on authoritative connection/auth state, expose anonymous connectivity, and let backend removability govern every non-active server.

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
  submitClaudeMcpRedirect,
  ClaudeMcpApiError,
  type ClaudeMcpCapability,
  type ClaudeMcpAuthState,
  type ClaudeMcpConfigScope,
  type ClaudeMcpOperation,
  type ClaudeMcpServer,
  type ClaudeMcpState,
} from '../../api/claudeMcpApi';
import { IconCheck, IconChevronRight, IconDatabase, IconLoader, IconX } from '../chat/Icons';

const OPERATION_POLL_INTERVAL_MS = 1200;
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
  const authState = authStateOf(server);
  return (state === 'needs_auth' && authState === 'required')
    || (state === 'connected' && (authState === 'anonymous' || authState === 'authenticated'));
}

function canLogout(server: ClaudeMcpServer, state: ClaudeMcpState): boolean {
  const authState = authStateOf(server);
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
  if (capability.reason_code === 'CLAUDE_MCP_CLI_VERSION_UNSUPPORTED') {
    return `Claude Code 版本不满足 headless OAuth 要求（最低 ${capability.headless_minimum_cli_version}）。`;
  }
  if (capability.reason_code === 'CLAUDE_MCP_IDENTITY_UNAVAILABLE') {
    return '当前后端进程无法访问与 Claude Agent 相同的用户级凭证存储；请检查 CLI 路径、系统用户与 macOS Keychain / Linux 文件权限。';
  }
  return 'Claude MCP 能力暂不可用，请检查 CLI 与运行身份配置。';
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
  const [redirects, setRedirects] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busyServer, setBusyServer] = useState<string | null>(null);
  const [serverName, setServerName] = useState('');
  const [serverUrl, setServerUrl] = useState('');
  const [configuring, setConfiguring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextCapability = await getClaudeMcpCapability();
      setCapability(nextCapability);
      if (!nextCapability.enabled) {
        setServers([]);
        return;
      }
      const nextServers = await listClaudeMcpServers();
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
    if (!name || !url) {
      setError('请填写 MCP 服务名称和完整 HTTP 或 HTTPS URL。');
      return;
    }
    setConfiguring(true);
    setError(null);
    try {
      const next = await configureClaudeMcpServer(name, url);
      setServers((current) => [
        ...current.filter((server) => server.name !== next.name),
        next,
      ]);
      setServerName('');
      setServerUrl('');
    } catch (cause) {
      setError(safeApiErrorMessage(cause, 'MCP 服务配置失败'));
    } finally {
      setConfiguring(false);
    }
  };

  const submit = async (operation: ClaudeMcpOperation) => {
    const redirectUrl = redirects[operation.id]?.trim();
    if (!redirectUrl) {
      setError('请粘贴浏览器授权完成后的完整 redirect URL。');
      return;
    }
    setBusyServer(operation.server_name);
    setError(null);
    try {
      const next = await submitClaudeMcpRedirect(operation.id, redirectUrl);
      setOperations((current) => ({ ...current, [next.id]: next }));
      setRedirects((current) => ({ ...current, [operation.id]: '' }));
    } catch (cause) {
      setError(safeApiErrorMessage(cause, 'redirect URL 提交失败'));
    } finally {
      setBusyServer(null);
    }
  };

  const cancel = async (operation: ClaudeMcpOperation) => {
    setBusyServer(operation.server_name);
    setError(null);
    try {
      const next = await cancelClaudeMcpAuth(operation.id);
      setOperations((current) => ({ ...current, [next.id]: next }));
      setRedirects((current) => ({ ...current, [operation.id]: '' }));
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
          发现 Claude Code 已配置的 MCP 服务；Runtime 会先检测连接，仅在服务明确要求或你主动尝试时进入浏览器授权。
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
            <strong style={{ fontSize: '0.8rem', color: 'var(--color-text-primary)' }}>添加远程 MCP 服务</strong>
            <p style={{ margin: '0.22rem 0 0', fontSize: '0.73rem', lineHeight: 1.5, color: 'var(--color-text-secondary)' }}>
              接受完整 HTTP 或 HTTPS 服务地址；添加后会检测匿名连接，需要 OAuth 时再由 Claude Code 的用户级安全存储管理凭证。
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(8rem, 0.7fr) minmax(12rem, 1.3fr)', gap: '0.55rem' }}>
            <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.73rem', color: 'var(--color-text-secondary)' }}>
              MCP 服务名称
              <input
                aria-label="MCP 服务名称"
                value={serverName}
                onChange={(event) => setServerName(event.target.value)}
                autoComplete="off"
                maxLength={512}
                required
                placeholder="例如 comfy-cloud"
                style={{ border: '1px solid var(--color-border-paper)', borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem', minWidth: 0 }}
              />
            </label>
            <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.73rem', color: 'var(--color-text-secondary)' }}>
              MCP 服务 URL
              <input
                aria-label="MCP 服务 URL"
                type="url"
                value={serverUrl}
                onChange={(event) => setServerUrl(event.target.value)}
                autoComplete="off"
                spellCheck={false}
                maxLength={2048}
                required
                placeholder="https://mcp.example.com/api 或 http://host/mcp"
                style={{ border: '1px solid var(--color-border-paper)', borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem', minWidth: 0 }}
              />
            </label>
          </div>
          <div>
            <button type="submit" disabled={configuring} style={actionButton(true)}>
              {configuring ? '正在添加…' : '添加 MCP 服务'}
            </button>
          </div>
        </form>
      ) : null}

      {capability?.enabled && !loading && servers.length === 0 ? (
        <div style={{ border: '1px dashed var(--color-border-paper)', borderRadius: '1rem', padding: '0.9rem', fontSize: '0.78rem', color: 'var(--color-text-secondary)' }}>
          尚未配置 MCP 服务。添加 HTTP(S) 服务后将先检测连接；只有服务明确要求时才会提供 OAuth 认证。
        </div>
      ) : null}

      <div style={{ display: 'grid', gap: '0.72rem' }}>
        {servers.map((server) => {
          const operation = operationFor(operations, server);
          const state = operation && ACTIVE_STATES.includes(operation.state)
            ? operation.state
            : server.state;
          const isBusy = busyServer === server.name || ACTIVE_STATES.includes(state);
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
                      {state === 'failed' ? '重试状态探测' : '检测连接'}
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
                    先在浏览器完成授权，再粘贴最终跳转后的完整 URL。URL 只写入当前 CLI 进程，不会保存到浏览器或数据库。
                  </p>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <a href={operation.authorization_url ?? undefined} target="_blank" rel="noreferrer" style={{ ...actionButton(true), textDecoration: 'none' }}>
                      打开授权页面
                    </a>
                  </div>
                  <label style={{ display: 'grid', gap: '0.32rem', fontSize: '0.74rem', color: 'var(--color-text-secondary)' }}>
                    完整 redirect URL
                    <input
                      aria-label={`${server.name} redirect URL`}
                      type="url"
                      autoComplete="off"
                      spellCheck={false}
                      value={redirects[operation.id] ?? ''}
                      onChange={(event) => setRedirects((current) => ({ ...current, [operation.id]: event.target.value }))}
                      placeholder="https://callback.example/path?code=…&state=…"
                      style={{ border: '1px solid var(--color-border-paper)', borderRadius: '0.72rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.62rem 0.72rem', minWidth: 0 }}
                    />
                  </label>
                  <div>
                    <button type="button" onClick={() => void submit(operation)} disabled={isBusy && busyServer === server.name} style={actionButton(true)}>
                      提交并连接
                    </button>
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
