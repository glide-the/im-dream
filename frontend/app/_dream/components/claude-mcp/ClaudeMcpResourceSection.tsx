// [Sync] 2026-10-29: share original MCP list state with native and retain Web markup/focus.
// [Input] Database-managed Claude MCP capability/CRUD/server/operation DTOs plus the shared accessible Modal with an explicit initial-focus target and design tokens/icons.
// [Output] Fast DB-backed server list, modal transport-safe creation, detail navigation, OAuth handoff, logout, and removal UI.
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
// [Sync] 2026-09-06: move MCP Server creation from the long settings flow into the shared accessible responsive dialog and focus its first field on open.
// [Sync] 2026-09-06: group connection identity and endpoint inputs inside a caller-scoped wide dialog with a scrollable body and persistent action footer.
// [Sync] 2026-09-16: expose OAuth replacement from terminal failed/configured states while preserving the current credential until exchange succeeds.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
import { canStartClaudeMcpAuth, claudeMcpAuthActionLabel } from './authPolicy';
import { IconCheck, IconChevronRight, IconDatabase, IconLoader, IconPlus, IconX } from '../chat/Icons';
import Modal from '../chat/Modal';
import './ClaudeMcpResourceSection.css';

import {OPERATION_POLL_INTERVAL_MS,CAPABILITY_RETRY_INTERVAL_MS,CAPABILITY_UNAVAILABLE,ACTIVE_STATES,STATE_LABELS,SCOPE_LABELS,AUTH_STATE_LABELS,authStateOf,serverStatusLabel,canLogout,canDetectConnection,safeApiErrorMessage,safeOperationError,messageForCapability,operationFor} from './mcpResourcePresentation';
import useClaudeMcpResources from '../../hooks/useClaudeMcpResources';

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

export default function ClaudeMcpResourceSection({
  onOpenServerDetail,
}: {
  onOpenServerDetail?: (serverName: string) => void;
}) {
  const {capability,servers,operations,loading,busyServer,serverName,setServerName,serverUrl,setServerUrl,serverTransport,setServerTransport,stdioProfileKey,setStdioProfileKey,addDialogOpen,setAddDialogOpen,configuring,configurationError,setConfigurationError,error,load,start,configure,cancel,logout,remove}=useClaudeMcpResources();
  const serverNameInputRef=useRef<HTMLInputElement>(null);

  return (
    <section aria-labelledby="claude-mcp-heading" style={{ display: 'grid', gap: '0.72rem' }}>
      <div className="claude-mcp-resource__header">
        <div>
          <h3 id="claude-mcp-heading" style={{ margin: 0, fontSize: '0.92rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            Claude MCP 资源
          </h3>
          <p style={{ margin: '0.28rem 0 0', fontSize: '0.78rem', lineHeight: 1.55, color: 'var(--color-text-secondary)' }}>
            Server 列表直接读取 Dream 数据库，不等待远端连接；进入详情后会自动加载 Tools、Resources 与 Prompts。
          </p>
        </div>
        {capability?.enabled ? (
          <button
            aria-haspopup="dialog"
            className="claude-mcp-resource__add-button"
            onClick={() => {
              setConfigurationError(null);
              setAddDialogOpen(true);
            }}
            style={actionButton(true)}
            type="button"
          >
            <IconPlus />
            添加 MCP 服务
          </button>
        ) : null}
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

      <Modal
        closeLabel="关闭添加 MCP 服务弹窗"
        initialFocusRef={serverNameInputRef}
        onClose={() => setAddDialogOpen(false)}
        open={addDialogOpen && capability?.enabled === true}
        surfaceClassName="claude-mcp-add-dialog"
        title="添加 MCP 服务"
      >
        <form
          aria-label="添加 Claude MCP 服务"
          aria-busy={configuring}
          className="claude-mcp-add-form"
          onSubmit={(event) => {
            event.preventDefault();
            void configure();
          }}
        >
          <div className="claude-mcp-add-form__body">
            <p className="claude-mcp-add-form__description">
              配置连接信息后，Dream 会自动判断服务是否需要认证并读取可用能力。
            </p>
            <fieldset className="claude-mcp-add-form__group">
              <legend>连接信息</legend>
              <p className="claude-mcp-add-form__group-hint">名称用于在 Resources 中识别此连接，传输方式应与服务端保持一致。</p>
              <div className="claude-mcp-add-form__fields">
                <label>
                  MCP 服务名称
                  <input
                    ref={serverNameInputRef}
                    aria-label="MCP 服务名称"
                    value={serverName}
                    onChange={(event) => setServerName(event.target.value)}
                    autoComplete="off"
                    maxLength={128}
                    required
                    placeholder="例如 comfy-cloud"
                  />
                </label>
                <label>
                  传输方式
                  <select
                    aria-label="MCP 传输方式"
                    value={serverTransport}
                    onChange={(event) => {
                      setServerTransport(event.target.value as typeof serverTransport);
                      setConfigurationError(null);
                    }}
                  >
                    <option value="streamable_http">Streamable HTTP</option>
                    <option value="sse">Legacy SSE</option>
                    <option value="stdio">stdio profile</option>
                  </select>
                </label>
              </div>
            </fieldset>
            <fieldset className="claude-mcp-add-form__group">
              <legend>{serverTransport === 'stdio' ? '运行配置' : '连接地址'}</legend>
              <p className="claude-mcp-add-form__group-hint">
                {serverTransport === 'stdio'
                  ? 'stdio 只能引用服务端批准的 profile，不接受浏览器命令、参数或环境变量。'
                  : 'HTTP/SSE 只保存安全 URL，不保存浏览器中的认证信息。'}
              </p>
              <label className="claude-mcp-add-form__endpoint">
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
                />
              </label>
              <p className="claude-mcp-add-form__hint">
                认证要求由 Dream 连接 Server 后自动判断，无需预先选择认证方式。
              </p>
            </fieldset>
          </div>
          <div className="claude-mcp-add-form__footer">
            {configurationError ? (
              <div className="claude-mcp-add-form__error" role="alert">{configurationError}</div>
            ) : null}
            <div className="claude-mcp-add-form__actions">
              <button
                disabled={configuring}
                onClick={() => setAddDialogOpen(false)}
                style={actionButton()}
                type="button"
              >
                取消
              </button>
              <button type="submit" disabled={configuring} style={actionButton(true)}>
                {configuring ? '正在添加…' : '添加 MCP 服务'}
              </button>
            </div>
          </div>
        </form>
      </Modal>

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
                  {canStartClaudeMcpAuth(server, state) && !ACTIVE_STATES.includes(state) ? (
                    <button type="button" onClick={() => void start(server, state)} disabled={busyServer === server.name} style={actionButton(true)}>
                      {claudeMcpAuthActionLabel(server)}
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
