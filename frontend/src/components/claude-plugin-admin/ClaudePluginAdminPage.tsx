// [Input] claudePluginAdminApi typed client, Settings / Work container, and Deck create-menu interaction pattern.
// [Output] Settings-owned Claude Code plugin admin with one accessible create menu, global Marketplace
//          select/confirm/install/result flow, recent operations, shared installation list, and uninstall.
// [Pos] Settings / Work / Plugins section component (deck-integration-delta architecture).
// [Sync] 2026-08-19: connect the global catalog and make dialog autofocus race-free for immediate keyboard use.

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from 'react';
import {
  FaChevronDown,
  FaDownload,
  FaHistory,
  FaPlus,
  FaShoppingBag,
  FaSyncAlt,
  FaTimes,
} from 'react-icons/fa';
import {
  ClaudePluginApiError,
  getClaudePluginOperation,
  installClaudePlugin,
  listClaudePluginInstallations,
  listClaudePluginMarketplace,
  listClaudePluginOperations,
  shortDigest,
  uninstallClaudePlugin,
  type ClaudePluginInstallation,
  type ClaudePluginMarketplaceEntry,
  type ClaudePluginOperation,
} from '../../api/claudePluginAdminApi';
import './ClaudePluginAdminPage.css';

const SPEC_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9._-]*(@v?\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?)?$/;
const OPERATION_LIMIT = 8;
const OPERATION_POLL_INTERVAL_MS = 2_000;

type ActiveDialog = 'install' | 'marketplace' | 'operations' | null;
type MarketplaceStep = 'select' | 'confirm' | 'installing' | 'result';

function errorMessage(error: unknown): string {
  return error instanceof ClaudePluginApiError
    ? `${error.code}: ${error.message}`
    : error instanceof Error
      ? error.message
      : String(error);
}

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
    <div className="claude-plugin-admin__operation-card">
      <div className="claude-plugin-admin__operation-heading">
        <code>{operation.id}</code>
        <StatusPill status={operation.status} />
      </div>
      <div className="claude-plugin-admin__operation-spec">{operation.requested_package_spec}</div>
      <div className="claude-plugin-admin__operation-message">
        {operation.message ?? operation.phase}
        {typeof operation.exit_code === 'number' ? ` · exit ${operation.exit_code}` : ''}
        {operation.cli_version ? ` · ${operation.cli_version}` : ''}
      </div>
      <div className="claude-plugin-admin__progress" aria-label={`安装进度 ${operation.progress}%`}>
        <span
          className={operation.status === 'error' ? 'is-error' : undefined}
          style={{ width: `${operation.progress}%` }}
        />
      </div>
      {operation.error_summary ? (
        <div className="claude-plugin-admin__operation-error">
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
  canUninstall,
}: {
  installation: ClaudePluginInstallation;
  onUninstall: (id: string) => void;
  busy: boolean;
  canUninstall: boolean;
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
    <div className="claude-plugin-admin__installation-row">
      <div className="claude-plugin-admin__installation-main">
        <div className="claude-plugin-admin__installation-copy">
          <div className="claude-plugin-admin__installation-title">
            <strong>{installation.package_name}</strong>
            <span>v{installation.resolved_version}</span>
            <StatusPill status={installation.status} />
          </div>
          <code>
            {installation.requested_package_spec} · {shortDigest(installation.artifact_digest)} · {installation.file_count} files
          </code>
        </div>
        <div className="claude-plugin-admin__row-actions">
          <button type="button" onClick={() => setExpanded((value) => !value)} style={buttonStyle(false)}>
            {expanded ? '收起' : '详情'}
          </button>
          {canUninstall && installation.status === 'ready' ? (
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
        <div className="claude-plugin-admin__installation-details">
          <div><FieldLabel>source</FieldLabel> {installation.source_type} · CLI {installation.claude_cli_version}</div>
          {installation.cli_git_commit_sha ? (
            <div><FieldLabel>commit</FieldLabel> <code>{installation.cli_git_commit_sha}</code></div>
          ) : null}
          <div><FieldLabel>digest</FieldLabel> <code>{installation.artifact_digest}</code></div>
          <div><FieldLabel>artifact</FieldLabel> <code>{installation.artifact_path}</code></div>
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

function FieldLabel({ children }: { children: ReactNode }) {
  return <span className="claude-plugin-admin__field-label">{children}</span>;
}

const MARKETPLACE_STEPS: Array<{ id: MarketplaceStep; label: string }> = [
  { id: 'select', label: '选择插件' },
  { id: 'confirm', label: '确认安装' },
  { id: 'installing', label: '正在安装' },
  { id: 'result', label: '可以使用' },
];

function MarketplaceStageRail({ step }: { step: MarketplaceStep }) {
  const current = MARKETPLACE_STEPS.findIndex((item) => item.id === step);
  return (
    <ol aria-label="Marketplace 安装进度" className="claude-plugin-admin__marketplace-stages">
      {MARKETPLACE_STEPS.map((item, index) => (
        <li
          aria-current={index === current ? 'step' : undefined}
          className={index <= current ? 'is-reached' : undefined}
          key={item.id}
        >
          <span>{index + 1}</span>
          {item.label}
        </li>
      ))}
    </ol>
  );
}

function componentSummary(entry: ClaudePluginMarketplaceEntry): string {
  const inventory = entry.component_inventory ?? {};
  const values = [
    ['skills', inventory.skills],
    ['commands', inventory.commands],
    ['agents', inventory.agents],
    ['MCP', inventory.mcpServers],
  ].filter(([, count]) => typeof count === 'number' && count > 0);
  return values.length
    ? values.map(([label, count]) => `${count} ${label}`).join(' · ')
    : '已通过 manifest 与目录校验';
}

function MarketplaceEntryCard({
  entry,
  selected,
  onSelect,
}: {
  entry: ClaudePluginMarketplaceEntry;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      aria-pressed={selected}
      className={`claude-plugin-admin__marketplace-card${selected ? ' is-selected' : ''}`}
      onClick={onSelect}
      type="button"
    >
      <span className="claude-plugin-admin__marketplace-card-heading">
        <span>
          <strong>{entry.display_name}</strong>
          <code>{entry.package_spec}</code>
        </span>
        <span className="claude-plugin-admin__marketplace-card-version">
          {entry.installation ? '已安装' : entry.version ? `v${entry.version}` : '可安装'}
        </span>
      </span>
      <span className="claude-plugin-admin__marketplace-card-description">
        {entry.description ?? '该插件未提供说明。'}
      </span>
      <span className="claude-plugin-admin__marketplace-card-meta">
        {entry.marketplace.display_name} · {componentSummary(entry)}
      </span>
    </button>
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

function ActionDialog({
  kind,
  title,
  description,
  onClose,
  children,
}: {
  kind: Exclude<ActiveDialog, null>;
  title: string;
  description: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = `claude-plugin-${kind}-dialog-title`;
  const descriptionId = `claude-plugin-${kind}-dialog-description`;

  useLayoutEffect(() => {
    const dialog = dialogRef.current;
    const autofocus = dialog?.querySelector<HTMLElement>('[data-dialog-autofocus]');
    const firstControl = dialog?.querySelector<HTMLElement>('button:not(:disabled), input:not(:disabled)');
    (autofocus ?? firstControl)?.focus();
  }, []);

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== 'Tab') return;
    const controls = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not(:disabled), input:not(:disabled), [tabindex]:not([tabindex="-1"])',
    ) ?? []);
    if (!controls.length) return;
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div
      className="claude-plugin-admin__dialog-backdrop"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        aria-describedby={descriptionId}
        aria-labelledby={titleId}
        aria-modal="true"
        className={`claude-plugin-admin__dialog is-${kind}`}
        onKeyDown={handleKeyDown}
        ref={dialogRef}
        role="dialog"
      >
        <header className="claude-plugin-admin__dialog-header">
          <div>
            <h3 id={titleId}>{title}</h3>
            <p id={descriptionId}>{description}</p>
          </div>
          <button aria-label="关闭" className="claude-plugin-admin__dialog-close" onClick={onClose} type="button">
            <FaTimes aria-hidden="true" />
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}

export default function ClaudePluginAdminPage() {
  const [installations, setInstallations] = useState<ClaudePluginInstallation[]>([]);
  const [operations, setOperations] = useState<ClaudePluginOperation[]>([]);
  const [spec, setSpec] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [installError, setInstallError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [canManage, setCanManage] = useState(false);
  const [trackedOperationId, setTrackedOperationId] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeDialog, setActiveDialog] = useState<ActiveDialog>(null);
  const [marketplaceEntries, setMarketplaceEntries] = useState<ClaudePluginMarketplaceEntry[]>([]);
  const [marketplaceLoading, setMarketplaceLoading] = useState(false);
  const [marketplaceError, setMarketplaceError] = useState<string | null>(null);
  const [marketplaceStep, setMarketplaceStep] = useState<MarketplaceStep>('select');
  const [selectedMarketplaceEntryId, setSelectedMarketplaceEntryId] = useState<string | null>(null);
  const [marketplaceOperationId, setMarketplaceOperationId] = useState<string | null>(null);
  const [marketplaceResult, setMarketplaceResult] = useState<ClaudePluginOperation | null>(null);
  const pollRef = useRef<number | null>(null);
  const menuBoundaryRef = useRef<HTMLDivElement>(null);
  const menuTriggerRef = useRef<HTMLButtonElement>(null);
  const menuItemRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const menuFocusIndexRef = useRef(0);

  const refresh = useCallback(async (initial = false) => {
    if (initial) setLoading(true);
    else setRefreshing(true);
    try {
      const [installResult, recentOperations] = await Promise.all([
        listClaudePluginInstallations(),
        listClaudePluginOperations(OPERATION_LIMIT),
      ]);
      setInstallations(installResult.installations);
      setOperations(recentOperations);
      setCanManage(Boolean(installResult.permissions?.can_manage_shared_plugins));
      setError(null);
    } catch (reason) {
      setCanManage(false);
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refresh(true);
  }, [refresh]);

  const loadMarketplace = useCallback(async () => {
    setMarketplaceLoading(true);
    setMarketplaceError(null);
    try {
      const result = await listClaudePluginMarketplace();
      setMarketplaceEntries(result.entries);
      setSelectedMarketplaceEntryId((current) => (
        current && result.entries.some((entry) => entry.id === current)
          ? current
          : result.entries[0]?.id ?? null
      ));
    } catch (reason) {
      setMarketplaceEntries([]);
      setSelectedMarketplaceEntryId(null);
      setMarketplaceError(errorMessage(reason));
    } finally {
      setMarketplaceLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeDialog !== 'marketplace') return;
    void loadMarketplace();
  }, [activeDialog, loadMarketplace]);

  useEffect(() => {
    if (!trackedOperationId) return undefined;
    let stopped = false;
    const tick = async () => {
      try {
        const operation = await getClaudePluginOperation(trackedOperationId);
        if (stopped) return;
        setOperations((current) => {
          const rest = current.filter((item) => item.id !== operation.id);
          return [operation, ...rest].slice(0, OPERATION_LIMIT);
        });
        if (operation.status === 'ready' || operation.status === 'error') {
          setTrackedOperationId(null);
          if (operation.id === marketplaceOperationId) {
            setMarketplaceResult(operation);
            setMarketplaceStep('result');
            setMarketplaceOperationId(null);
            void loadMarketplace();
          }
          setSuccessMessage(
            operation.status === 'ready'
              ? `${operation.requested_package_spec} 安装完成。`
              : null,
          );
          void refresh();
        }
      } catch {
        // A transient poll failure must not replace the last visible operation state.
      }
    };
    void tick();
    pollRef.current = window.setInterval(tick, OPERATION_POLL_INTERVAL_MS);
    return () => {
      stopped = true;
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
    };
  }, [trackedOperationId, refresh, marketplaceOperationId, loadMarketplace]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    requestAnimationFrame(() => menuItemRefs.current[menuFocusIndexRef.current]?.focus());
    const closeOutside = (event: PointerEvent) => {
      if (!menuBoundaryRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('pointerdown', closeOutside);
    return () => document.removeEventListener('pointerdown', closeOutside);
  }, [menuOpen]);

  const openMenu = (focusIndex = 0) => {
    menuFocusIndexRef.current = focusIndex;
    setMenuOpen(true);
  };

  const closeMenu = (restoreFocus = false) => {
    setMenuOpen(false);
    if (restoreFocus) requestAnimationFrame(() => menuTriggerRef.current?.focus());
  };

  const closeDialog = () => {
    setActiveDialog(null);
    requestAnimationFrame(() => menuTriggerRef.current?.focus());
  };

  const openDialog = (dialog: Exclude<ActiveDialog, null>) => {
    setMenuOpen(false);
    setInstallError(null);
    if (dialog === 'marketplace') {
      setMarketplaceStep('select');
      setMarketplaceResult(null);
      setMarketplaceError(null);
    }
    setActiveDialog(dialog);
  };

  const handleMenuKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const enabledItems = menuItemRefs.current.filter((item): item is HTMLButtonElement => Boolean(item && !item.disabled));
    if (!enabledItems.length) return;
    const currentIndex = enabledItems.findIndex((item) => item === document.activeElement);
    if (event.key === 'Escape') {
      event.preventDefault();
      closeMenu(true);
    } else if (event.key === 'Tab') {
      setMenuOpen(false);
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      enabledItems[(currentIndex + 1 + enabledItems.length) % enabledItems.length].focus();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      enabledItems[(currentIndex - 1 + enabledItems.length) % enabledItems.length].focus();
    } else if (event.key === 'Home') {
      event.preventDefault();
      enabledItems[0].focus();
    } else if (event.key === 'End') {
      event.preventDefault();
      enabledItems[enabledItems.length - 1].focus();
    }
  };

  const handleInstall = useCallback(async () => {
    const trimmed = spec.trim();
    if (!SPEC_PATTERN.test(trimmed)) {
      setInstallError('包名格式应为 <plugin>@<marketplace>，例如 superpowers@claude-plugins-official');
      return;
    }
    if (!canManage) {
      setInstallError('当前账户没有共享插件管理权限。');
      return;
    }
    setBusy(true);
    setInstallError(null);
    setSuccessMessage(null);
    try {
      const accepted = await installClaudePlugin({ packageSpec: trimmed });
      setTrackedOperationId(accepted.operation_id);
      setSpec('');
      setActiveDialog('operations');
    } catch (reason) {
      setInstallError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }, [canManage, spec]);

  const handleMarketplaceInstall = useCallback(async () => {
    const entry = marketplaceEntries.find((item) => item.id === selectedMarketplaceEntryId);
    if (!entry) {
      setMarketplaceError('请选择一个 Marketplace 插件。');
      setMarketplaceStep('select');
      return;
    }
    if (!canManage) {
      setMarketplaceError('当前账户没有共享插件管理权限。');
      return;
    }
    setBusy(true);
    setMarketplaceError(null);
    setMarketplaceResult(null);
    try {
      const accepted = await installClaudePlugin({ marketplaceEntryId: entry.id });
      setMarketplaceOperationId(accepted.operation_id);
      setTrackedOperationId(accepted.operation_id);
      setMarketplaceStep('installing');
    } catch (reason) {
      setMarketplaceError(errorMessage(reason));
      setMarketplaceStep('confirm');
    } finally {
      setBusy(false);
    }
  }, [canManage, marketplaceEntries, selectedMarketplaceEntryId]);

  const handleUninstall = useCallback(async (installationId: string) => {
    if (!canManage) return;
    setBusy(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await uninstallClaudePlugin(installationId);
      await refresh();
      setSuccessMessage('插件已卸载。');
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }, [canManage, refresh]);

  const selectedMarketplaceEntry = marketplaceEntries.find(
    (entry) => entry.id === selectedMarketplaceEntryId,
  ) ?? null;
  const activeMarketplaceOperation = marketplaceOperationId
    ? operations.find((operation) => operation.id === marketplaceOperationId) ?? null
    : null;

  return (
    <section aria-labelledby="claude-plugin-admin-title" className="claude-plugin-admin">
      <div className="claude-plugin-admin__topbar">
        <span className="claude-plugin-admin__section-label">Claude Code Plugins</span>
        <div className="claude-plugin-admin__top-actions">
          <button
            aria-label="刷新 Claude 插件"
            className="claude-plugin-admin__icon-action"
            disabled={loading || refreshing}
            onClick={() => void refresh()}
            title="刷新 Claude 插件"
            type="button"
          >
            <FaSyncAlt aria-hidden="true" className={refreshing ? 'is-spinning' : undefined} />
          </button>
          <div className="claude-plugin-admin__menu-anchor" ref={menuBoundaryRef}>
            <button
              aria-controls="claude-plugin-create-menu"
              aria-expanded={menuOpen}
              aria-haspopup="menu"
              className="claude-plugin-admin__create-action"
              onClick={() => (menuOpen ? closeMenu() : openMenu(canManage && !loading ? 0 : 1))}
              onKeyDown={(event) => {
                if (event.key === 'ArrowDown') {
                  event.preventDefault();
                  openMenu(canManage && !loading ? 0 : 1);
                } else if (event.key === 'ArrowUp') {
                  event.preventDefault();
                  openMenu(2);
                }
              }}
              ref={menuTriggerRef}
              type="button"
            >
              创建
              <FaChevronDown aria-hidden="true" />
            </button>
            {menuOpen ? (
              <div
                aria-label="Claude 插件创建操作"
                className="claude-plugin-admin__menu"
                id="claude-plugin-create-menu"
                onKeyDown={handleMenuKeyDown}
                role="menu"
              >
                <button
                  disabled={!canManage || loading}
                  onClick={() => openDialog('install')}
                  ref={(node) => { menuItemRefs.current[0] = node; }}
                  role="menuitem"
                  type="button"
                >
                  <FaDownload aria-hidden="true" />
                  <span>安装</span>
                </button>
                <button
                  onClick={() => openDialog('marketplace')}
                  ref={(node) => { menuItemRefs.current[1] = node; }}
                  role="menuitem"
                  type="button"
                >
                  <FaShoppingBag aria-hidden="true" />
                  <span>从 Marketplace 添加</span>
                </button>
                <button
                  onClick={() => openDialog('operations')}
                  ref={(node) => { menuItemRefs.current[2] = node; }}
                  role="menuitem"
                  type="button"
                >
                  <FaHistory aria-hidden="true" />
                  <span>最近操作</span>
                  <small>{operations.length}</small>
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <header className="claude-plugin-admin__header">
        <h2 id="claude-plugin-admin-title">Claude 插件</h2>
        <p>
          通过真实 <code>claude plugin install</code> 在服务端受管工作空间安装插件，
          生成 digest 固定的不可变制品。Deck 只保存安装引用；发起 Deck 对话时，
          插件包会被复制到该对话的 Agent 工作空间并通过 <code>--plugin-dir</code> 加载。
        </p>
      </header>

      {error ? (
        <div className="claude-plugin-admin__notice is-error" role="alert">
          <span>{error}</span>
          <button onClick={() => void refresh()} type="button">重试</button>
        </div>
      ) : null}
      {successMessage ? (
        <div className="claude-plugin-admin__notice is-success" role="status">{successMessage}</div>
      ) : null}
      {!loading && !error && !canManage ? (
        <div className="claude-plugin-admin__notice" role="status">
          当前账户没有共享插件管理权限；已安装列表保持只读。
        </div>
      ) : null}

      <div className="claude-plugin-admin__installations" aria-busy={loading} aria-live="polite">
        <div className="claude-plugin-admin__list-heading">
          <FieldLabel>已安装（{installations.length}）</FieldLabel>
        </div>
        {loading ? (
          <div className="claude-plugin-admin__empty" role="status">正在加载 Claude 插件…</div>
        ) : installations.length === 0 ? (
          <div className="claude-plugin-admin__empty">
            <FaPlus aria-hidden="true" />
            <strong>尚未安装任何插件</strong>
            <span>使用“创建 → 安装”输入 package spec 开始。</span>
          </div>
        ) : (
          installations.map((installation) => (
            <InstallationRow
              key={installation.id}
              installation={installation}
              onUninstall={handleUninstall}
              busy={busy}
              canUninstall={canManage}
            />
          ))
        )}
      </div>

      {activeDialog === 'install' ? (
        <ActionDialog
          description="输入 Claude Code package spec。请求会提交到现有服务端受管安装入口。"
          kind="install"
          onClose={closeDialog}
          title="安装 Claude 插件"
        >
          <form
            className="claude-plugin-admin__dialog-body"
            onSubmit={(event) => {
              event.preventDefault();
              void handleInstall();
            }}
          >
            <label className="claude-plugin-admin__spec-field">
              <span>Package spec</span>
              <input
                autoComplete="off"
                data-dialog-autofocus
                disabled={busy}
                onChange={(event) => setSpec(event.target.value)}
                placeholder="superpowers@claude-plugins-official"
                spellCheck={false}
                value={spec}
              />
              <small>格式：&lt;plugin&gt;@&lt;marketplace&gt;[@&lt;version&gt;]</small>
            </label>
            {installError ? <div className="claude-plugin-admin__form-error" role="alert">{installError}</div> : null}
            <div className="claude-plugin-admin__dialog-actions">
              <button disabled={busy} onClick={closeDialog} type="button">取消</button>
              <button className="is-primary" disabled={busy || !spec.trim() || !canManage} type="submit">
                {busy ? '安装中…' : '开始安装'}
              </button>
            </div>
          </form>
        </ActionDialog>
      ) : null}

      {activeDialog === 'marketplace' ? (
        <ActionDialog
          description="所有 Dream 用户看到同一份由平台运营审核的远程目录。选择插件后仍走现有真实安装入口。"
          kind="marketplace"
          onClose={closeDialog}
          title="从 Marketplace 添加"
        >
          <div className="claude-plugin-admin__dialog-body claude-plugin-admin__marketplace-dialog">
            <MarketplaceStageRail step={marketplaceStep} />

            {marketplaceStep === 'select' ? (
              <div>
                <div className="claude-plugin-admin__marketplace-context">
                  <FaShoppingBag aria-hidden="true" />
                  <span>平台全局目录 · 仅展示有效且已批准的远程 revision</span>
                </div>
                {marketplaceLoading ? (
                  <div className="claude-plugin-admin__empty" role="status">正在读取 Marketplace…</div>
                ) : marketplaceError ? (
                  <div className="claude-plugin-admin__marketplace-unavailable" role="alert">
                    <FaShoppingBag aria-hidden="true" />
                    <strong>Marketplace 目录暂不可用</strong>
                    <p>{marketplaceError}</p>
                    <button data-dialog-autofocus onClick={() => void loadMarketplace()} type="button">重新加载</button>
                  </div>
                ) : marketplaceEntries.length === 0 ? (
                  <div className="claude-plugin-admin__marketplace-unavailable" role="status">
                    <FaShoppingBag aria-hidden="true" />
                    <strong>暂无可添加插件</strong>
                    <p>运营者尚未批准任何有效 revision，或已停用全部远程来源。</p>
                  </div>
                ) : (
                  <div aria-label="可添加的 Marketplace 插件" className="claude-plugin-admin__marketplace-list">
                    {marketplaceEntries.map((entry) => (
                      <MarketplaceEntryCard
                        entry={entry}
                        key={entry.id}
                        onSelect={() => setSelectedMarketplaceEntryId(entry.id)}
                        selected={selectedMarketplaceEntryId === entry.id}
                      />
                    ))}
                  </div>
                )}
                <div className="claude-plugin-admin__dialog-actions">
                  <button onClick={closeDialog} type="button">取消</button>
                  <button
                    className="is-primary"
                    data-dialog-autofocus={marketplaceEntries.length > 0 ? true : undefined}
                    disabled={!selectedMarketplaceEntry || marketplaceLoading || !canManage}
                    onClick={() => {
                      setMarketplaceError(null);
                      setMarketplaceStep('confirm');
                    }}
                    type="button"
                  >
                    继续
                  </button>
                </div>
              </div>
            ) : null}

            {marketplaceStep === 'confirm' && selectedMarketplaceEntry ? (
              <div className="claude-plugin-admin__marketplace-confirm">
                <div className="claude-plugin-admin__marketplace-summary">
                  <span className="claude-plugin-admin__section-label">确认全局目录版本</span>
                  <h4>{selectedMarketplaceEntry.display_name}</h4>
                  <code>{selectedMarketplaceEntry.package_spec}</code>
                  <p>{selectedMarketplaceEntry.description ?? '该插件未提供说明。'}</p>
                  <dl>
                    <div><dt>来源</dt><dd>{selectedMarketplaceEntry.marketplace.display_name}</dd></div>
                    <div><dt>版本</dt><dd>{selectedMarketplaceEntry.version ?? '未声明'}</dd></div>
                    <div><dt>组件</dt><dd>{componentSummary(selectedMarketplaceEntry)}</dd></div>
                    <div><dt>固定 ref</dt><dd>{selectedMarketplaceEntry.revision.requested_ref ?? '远程默认分支'}</dd></div>
                    <div><dt>批准 commit</dt><dd><code>{selectedMarketplaceEntry.revision.commit_sha}</code></dd></div>
                    <div><dt>内容摘要</dt><dd><code>{selectedMarketplaceEntry.revision.plugin_digest}</code></dd></div>
                    <div><dt>重复添加</dt><dd>{selectedMarketplaceEntry.installation ? '复用并重新验证现有安装' : '创建新的共享安装记录'}</dd></div>
                  </dl>
                </div>
                <p className="claude-plugin-admin__marketplace-caveat">
                  安装前服务端会再次确认条目仍为 active/approved，并校验 CLI checkout 的 commit 与 manifest 摘要；发生远端漂移时不会继续安装。
                </p>
                {marketplaceError ? <div className="claude-plugin-admin__form-error" role="alert">{marketplaceError}</div> : null}
                <div className="claude-plugin-admin__dialog-actions">
                  <button disabled={busy} onClick={() => setMarketplaceStep('select')} type="button">返回选择</button>
                  <button
                    className="is-primary"
                    data-dialog-autofocus
                    disabled={busy || !canManage}
                    onClick={() => void handleMarketplaceInstall()}
                    type="button"
                  >
                    {busy ? '提交中…' : selectedMarketplaceEntry.installation ? '验证并复用安装' : '确认安装'}
                  </button>
                </div>
              </div>
            ) : null}

            {marketplaceStep === 'installing' ? (
              <div className="claude-plugin-admin__marketplace-installing" role="status" aria-live="polite">
                <span className="claude-plugin-admin__marketplace-spinner" aria-hidden="true" />
                <h4>正在安装 {selectedMarketplaceEntry?.display_name}</h4>
                <p>服务端正在校验已批准 revision、调用真实 Claude CLI，并导入 digest 固定的共享制品。可以关闭窗口，进度会保留在“最近操作”。</p>
                {activeMarketplaceOperation ? <OperationCard operation={activeMarketplaceOperation} /> : <code>{marketplaceOperationId}</code>}
                <div className="claude-plugin-admin__dialog-actions">
                  <button data-dialog-autofocus onClick={closeDialog} type="button">后台继续</button>
                </div>
              </div>
            ) : null}

            {marketplaceStep === 'result' && marketplaceResult ? (
              <div className={`claude-plugin-admin__marketplace-result ${marketplaceResult.status === 'ready' ? 'is-success' : 'is-error'}`} role={marketplaceResult.status === 'ready' ? 'status' : 'alert'}>
                <span className="claude-plugin-admin__marketplace-result-mark" aria-hidden="true">
                  {marketplaceResult.status === 'ready' ? '✓' : '!'}
                </span>
                <h4>{marketplaceResult.status === 'ready' ? '插件可以使用' : '安装未完成'}</h4>
                <p>
                  {marketplaceResult.status === 'ready'
                    ? `${marketplaceResult.requested_package_spec} 已进入共享安装列表，可继续绑定到 Deck。`
                    : `${marketplaceResult.error_code ?? 'CLAUDE_PLUGIN_INSTALL_FAILED'}：保留当前选择，可直接重试。`}
                </p>
                <OperationCard operation={marketplaceResult} />
                <div className="claude-plugin-admin__dialog-actions">
                  {marketplaceResult.status === 'error' ? (
                    <button onClick={() => setMarketplaceStep('confirm')} type="button">返回并重试</button>
                  ) : null}
                  <button className="is-primary" data-dialog-autofocus onClick={closeDialog} type="button">
                    {marketplaceResult.status === 'ready' ? '完成' : '关闭'}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </ActionDialog>
      ) : null}

      {activeDialog === 'operations' ? (
        <ActionDialog
          description="显示真实 operation ID、阶段、进度、CLI 版本和退出结果。"
          kind="operations"
          onClose={closeDialog}
          title="最近操作"
        >
          <div className="claude-plugin-admin__dialog-body claude-plugin-admin__operations-dialog">
            {operations.length === 0 ? (
              <div className="claude-plugin-admin__empty" role="status">
                <FaHistory aria-hidden="true" />
                <strong>暂无最近操作</strong>
                <span>安装请求提交后会在这里显示进度和结果。</span>
              </div>
            ) : (
              <div className="claude-plugin-admin__operation-list">
                {operations.map((operation) => <OperationCard key={operation.id} operation={operation} />)}
              </div>
            )}
            <div className="claude-plugin-admin__dialog-actions">
              <button data-dialog-autofocus onClick={closeDialog} type="button">关闭</button>
            </div>
          </div>
        </ActionDialog>
      ) : null}
    </section>
  );
}
