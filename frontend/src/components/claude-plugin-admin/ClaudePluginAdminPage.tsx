// [Input] claudePluginAdminApi typed client.
// [Output] Settings-owned Claude Code plugin admin: package-spec install with real
//          operation progress, shared installation list with digest/status, uninstall.
// [Pos] Settings section component (deck-integration-delta architecture).

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ClaudePluginApiError,
  getClaudePluginOperation,
  installClaudePlugin,
  listClaudePluginInstallations,
  listClaudePluginOperations,
  shortDigest,
  uninstallClaudePlugin,
  type ClaudePluginInstallation,
  type ClaudePluginOperation,
} from '../../api/claudePluginAdminApi';

interface ClaudePluginAdminPageProps {
  isMobile?: boolean;
}

const SPEC_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9._-]*(@v?\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?)?$/;

function StatusPill({ status }: { status: string }) {
  const tone =
    status === 'ready'
      ? { bg: 'color-mix(in srgb, #2e9d62 14%, var(--color-bg-surface))', fg: '#24784c' }
      : status === 'error' || status === 'failed'
        ? { bg: 'color-mix(in srgb, #c44848 14%, var(--color-bg-surface))', fg: '#a03737' }
        : { bg: 'var(--color-bg-hover)', fg: 'var(--color-text-secondary)' };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', borderRadius: 999,
      padding: '4px 9px', fontSize: 11, fontWeight: 700,
      background: tone.bg, color: tone.fg, whiteSpace: 'nowrap',
    }}>
      {status}
    </span>
  );
}

function OperationCard({ operation }: { operation: ClaudePluginOperation }) {
  return (
    <div style={{
      border: '1px solid var(--color-border-paper)', borderRadius: 10,
      background: 'var(--color-bg-surface)', padding: '12px 14px', marginTop: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
        <code style={{ fontSize: 11, color: 'var(--color-text-muted)', overflowWrap: 'anywhere' }}>
          {operation.id}
        </code>
        <StatusPill status={operation.status} />
      </div>
      <div style={{ marginTop: 8, fontSize: 13, color: 'var(--color-text-primary)' }}>
        {operation.requested_package_spec}
      </div>
      <div style={{ marginTop: 4, fontSize: 12, color: 'var(--color-text-secondary)' }}>
        {operation.message ?? operation.phase}
        {typeof operation.exit_code === 'number' ? ` · exit ${operation.exit_code}` : ''}
        {operation.cli_version ? ` · ${operation.cli_version}` : ''}
      </div>
      <div style={{
        marginTop: 8, height: 6, borderRadius: 999, background: 'var(--color-bg-hover)', overflow: 'hidden',
      }}>
        <div style={{
          width: `${operation.progress}%`, height: '100%',
          background: operation.status === 'error' ? '#c44848' : 'var(--color-text-primary)',
          transition: 'width .3s ease',
        }} />
      </div>
      {operation.error_summary ? (
        <div style={{ marginTop: 8, fontSize: 12, color: '#a03737', overflowWrap: 'anywhere' }}>
          {operation.error_code}: {operation.error_summary}
        </div>
      ) : null}
    </div>
  );
}

function InstallationRow({
  installation,
  onUninstall,
  busy,
}: {
  installation: ClaudePluginInstallation;
  onUninstall: (id: string) => void;
  busy: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  let inventory: Record<string, unknown> = {};
  try {
    inventory = JSON.parse(installation.component_inventory_json || '{}');
  } catch {
    inventory = {};
  }
  const skills = Array.isArray(inventory.skills) ? (inventory.skills as string[]) : [];
  return (
    <div style={{
      border: '1px solid var(--color-border-paper)', borderRadius: 10,
      background: 'var(--color-bg-surface)', padding: '14px 16px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <strong style={{ fontSize: 15 }}>{installation.package_name}</strong>
            <span style={{
              borderRadius: 999, padding: '2px 8px', fontSize: 11, fontWeight: 700,
              background: 'var(--color-bg-hover)', color: 'var(--color-text-secondary)',
            }}>
              v{installation.resolved_version}
            </span>
            <StatusPill status={installation.status} />
          </div>
          <code style={{ display: 'block', marginTop: 6, fontSize: 11, color: 'var(--color-text-muted)', overflowWrap: 'anywhere' }}>
            {installation.requested_package_spec} · {shortDigest(installation.artifact_digest)} · {installation.file_count} files
          </code>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            style={buttonStyle(false)}
          >
            {expanded ? '收起' : '详情'}
          </button>
          {installation.status === 'ready' ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => onUninstall(installation.id)}
              style={buttonStyle(false)}
            >
              卸载
            </button>
          ) : null}
        </div>
      </div>
      {expanded ? (
        <div style={{ marginTop: 12, fontSize: 12, color: 'var(--color-text-secondary)', display: 'grid', gap: 6 }}>
          <div><FieldLabel>source</FieldLabel> {installation.source_type} · CLI {installation.claude_cli_version}</div>
          {installation.cli_git_commit_sha ? (
            <div><FieldLabel>commit</FieldLabel> <code>{installation.cli_git_commit_sha}</code></div>
          ) : null}
          <div><FieldLabel>digest</FieldLabel> <code style={{ overflowWrap: 'anywhere' }}>{installation.artifact_digest}</code></div>
          <div><FieldLabel>artifact</FieldLabel> <code style={{ overflowWrap: 'anywhere' }}>{installation.artifact_path}</code></div>
          {skills.length ? (
            <div><FieldLabel>skills ({skills.length})</FieldLabel> {skills.join(', ')}</div>
          ) : null}
          <div><FieldLabel>decks</FieldLabel> {installation.deck_ref_count ?? 0} 个引用</div>
          <div><FieldLabel>installed</FieldLabel> {installation.installed_at ?? '—'}</div>
        </div>
      ) : null}
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <span style={{
      display: 'inline-block', marginRight: 8, color: 'var(--color-text-muted)',
      fontSize: 10, fontWeight: 700, letterSpacing: '.04em', textTransform: 'uppercase',
    }}>
      {children}
    </span>
  );
}

function buttonStyle(primary: boolean): React.CSSProperties {
  return {
    border: '1px solid var(--color-border-paper)', borderRadius: 7,
    background: primary ? 'var(--color-text-primary)' : 'var(--color-bg-surface)',
    color: primary ? 'var(--color-text-on-action)' : 'var(--color-text-primary)',
    padding: '7px 12px', font: 'inherit', fontSize: 12, fontWeight: 600, cursor: 'pointer',
  };
}

export default function ClaudePluginAdminPage({ isMobile: _isMobile }: ClaudePluginAdminPageProps) {
  const [installations, setInstallations] = useState<ClaudePluginInstallation[]>([]);
  const [operations, setOperations] = useState<ClaudePluginOperation[]>([]);
  const [spec, setSpec] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [trackedOperationId, setTrackedOperationId] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [installs, ops] = await Promise.all([
        listClaudePluginInstallations(),
        listClaudePluginOperations(8),
      ]);
      setInstallations(installs);
      setOperations(ops);
      setError(null);
    } catch (err) {
      setError(err instanceof ClaudePluginApiError ? `${err.code}: ${err.message}` : String(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Poll the tracked operation until it reaches a terminal state.
  useEffect(() => {
    if (!trackedOperationId) return undefined;
    let stopped = false;
    const tick = async () => {
      try {
        const operation = await getClaudePluginOperation(trackedOperationId);
        if (stopped) return;
        setOperations((current) => {
          const rest = current.filter((item) => item.id !== operation.id);
          return [operation, ...rest].slice(0, 8);
        });
        if (operation.status === 'ready' || operation.status === 'error') {
          setTrackedOperationId(null);
          void refresh();
        }
      } catch {
        /* keep polling; transient errors are fine */
      }
    };
    void tick();
    pollRef.current = window.setInterval(tick, 2000);
    return () => {
      stopped = true;
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
    };
  }, [trackedOperationId, refresh]);

  const handleInstall = useCallback(async () => {
    const trimmed = spec.trim();
    if (!SPEC_PATTERN.test(trimmed)) {
      setError('包名格式应为 <plugin>@<marketplace>，例如 superpowers@claude-plugins-official');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const accepted = await installClaudePlugin({ packageSpec: trimmed });
      setTrackedOperationId(accepted.operation_id);
      setSpec('');
    } catch (err) {
      setError(err instanceof ClaudePluginApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setBusy(false);
    }
  }, [spec]);

  const handleUninstall = useCallback(async (installationId: string) => {
    setBusy(true);
    try {
      await uninstallClaudePlugin(installationId);
      await refresh();
    } catch (err) {
      setError(err instanceof ClaudePluginApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  return (
    <div style={{ color: 'var(--color-text-primary)' }}>
      <div style={{ marginBottom: 18 }}>
        <span style={{
          display: 'block', marginBottom: 6, color: 'var(--color-text-muted)',
          fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase',
        }}>
          Claude Code Plugins
        </span>
        <h2 style={{ margin: 0, fontFamily: 'Georgia, "Times New Roman", serif' }}>
          Claude 插件
        </h2>
        <p style={{ margin: '6px 0 0', color: 'var(--color-text-secondary)', fontSize: 13, lineHeight: 1.55 }}>
          通过真实 <code>claude plugin install</code> 在服务端受管工作空间安装插件，
          生成 digest 固定的不可变制品。Deck 只保存安装引用；发起 Deck 对话时，
          插件包会被复制到该对话的 Agent 工作空间并通过 <code>--plugin-dir</code> 加载。
        </p>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          value={spec}
          onChange={(event) => setSpec(event.target.value)}
          placeholder="superpowers@claude-plugins-official"
          spellCheck={false}
          style={{
            flex: '1 1 320px', minWidth: 240, padding: '9px 12px', font: 'inherit', fontSize: 13,
            borderRadius: 8, border: '1px solid var(--color-border-paper)',
            background: 'var(--color-bg-surface)', color: 'var(--color-text-primary)',
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !busy) void handleInstall();
          }}
        />
        <button
          type="button"
          disabled={busy || !spec.trim()}
          onClick={() => void handleInstall()}
          style={{ ...buttonStyle(true), opacity: busy || !spec.trim() ? 0.5 : 1 }}
        >
          {busy ? '安装中…' : 'Install Plugin'}
        </button>
      </div>

      {error ? (
        <div style={{
          marginTop: 12, padding: '10px 12px', borderRadius: 8, fontSize: 12,
          background: 'color-mix(in srgb, #c44848 10%, var(--color-bg-surface))',
          color: '#a03737', overflowWrap: 'anywhere',
        }}>
          {error}
        </div>
      ) : null}

      {operations.length ? (
        <div style={{ marginTop: 18 }}>
          <FieldLabel>最近操作（真实 operation ID / argv / exit code）</FieldLabel>
          {operations.map((operation) => (
            <OperationCard key={operation.id} operation={operation} />
          ))}
        </div>
      ) : null}

      <div style={{ marginTop: 22, display: 'grid', gap: 10 }}>
        <FieldLabel>已安装（{installations.length}）</FieldLabel>
        {installations.length === 0 ? (
          <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
            尚未安装任何插件。输入包名并点击 Install Plugin 开始。
          </div>
        ) : (
          installations.map((installation) => (
            <InstallationRow
              key={installation.id}
              installation={installation}
              onUninstall={handleUninstall}
              busy={busy}
            />
          ))
        )}
      </div>
    </div>
  );
}
