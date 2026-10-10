// [Input] Deck workflow query/mutation hooks and server-owned installation contracts.
// [Output] Workflow purpose, Dream Story Workflow scope, catalog, lifecycle controls, and detail drawer.
// [Pos] Plugin Admin root page mounted incrementally inside the existing Settings view.
// [Sync] 2026-10-10: delete the runtime-plugin category and explain the built-in story workflow in the actual page.

import { useCallback, useState } from 'react';
import {
  getPluginInstallationDetail,
  type DeckPluginApiError,
  type DeckPluginInstallation,
  type InstallPluginInput,
  type PluginMutationAction,
} from '../../api/deckPluginAdminApi';
import { usePluginInstallationDetail } from '../../hooks/usePluginInstallationDetail';
import { usePluginInstallations } from '../../hooks/usePluginInstallations';
import { usePluginOperation } from '../../hooks/usePluginOperation';
import { usePluginRuntimeReadiness } from '../../hooks/usePluginRuntimeReadiness';
import PluginAdminDetail from './PluginAdminDetail';
import PluginAdminList from './PluginAdminList';
import PluginErrorCard from './PluginErrorCard';
import PluginOperationProgress from './PluginOperationProgress';

interface PluginAdminPageProps {
  isMobile?: boolean;
}

const EMPTY_INSTALL_INPUT: InstallPluginInput = {
  deckPluginId: '',
  deckPluginVersion: '',
  sourceType: 'controlled',
  source: '',
};

const EXACT_VERSION_PATTERN = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;

function pluginAdminItemKey(item: DeckPluginInstallation): string {
  return `${item.deckPluginId}:${item.deckPluginVersion}`;
}

function styles(): string {
  return `
    .plugin-admin { color: var(--color-text-primary); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .plugin-admin * { box-sizing: border-box; }
    .plugin-admin__header, .plugin-admin-section-heading, .plugin-admin-list-item__top, .plugin-admin-list-item__footer { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
    .plugin-admin__header h2, .plugin-admin-detail h2 { margin: 0; font-family: Georgia, "Times New Roman", serif; }
    .plugin-admin__header p, .plugin-admin-section-heading p { margin: 6px 0 0; color: var(--color-text-secondary); font-size: 13px; line-height: 1.55; }
    .plugin-admin-eyebrow { display: block; margin-bottom: 6px; color: var(--color-text-muted); font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .plugin-admin-workflow-summary { margin: 20px 0; padding: 18px; border: 1px solid var(--color-border-paper); border-radius: 10px; background: var(--color-bg-surface); }
    .plugin-admin-workflow-summary h3 { margin: 0 0 8px; font-size: 16px; }
    .plugin-admin-workflow-summary p { margin: 8px 0; font-size: 13px; line-height: 1.65; color: var(--color-text-secondary); }
    .plugin-admin-workflow-summary dl { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; }
    .plugin-admin-workflow-summary dt { font-size: 12px; font-weight: 700; }
    .plugin-admin-workflow-summary dd { margin: 6px 0 0; font-size: 13px; line-height: 1.65; color: var(--color-text-secondary); }
    .plugin-admin-detail__tabs button { border: 0; background: transparent; color: var(--color-text-secondary); padding: 8px 12px; border-radius: 7px; font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; }
    .plugin-admin-detail__tabs button.is-active { background: var(--color-bg-hover); color: var(--color-text-primary); box-shadow: inset 0 0 0 1px var(--color-border-paper); }
    .plugin-admin-list { display: grid; gap: 12px; }
    .plugin-admin-list-item { padding: 18px; border: 1px solid var(--color-border-paper); border-radius: 10px; background: var(--color-bg-surface); cursor: pointer; transition: border-color .16s ease, transform .16s ease, box-shadow .16s ease; }
    .plugin-admin-list-item:hover, .plugin-admin-list-item:focus-visible, .plugin-admin-list-item--selected { outline: none; border-color: var(--color-text-muted); box-shadow: 0 8px 24px var(--color-shadow-light); transform: translateY(-1px); }
    .plugin-admin-list-item__identity { min-width: 0; }
    .plugin-admin-list-item__title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .plugin-admin-list-item h3 { margin: 0; font-size: 16px; }
    .plugin-admin-list-item code, .plugin-admin-detail code { color: var(--color-text-muted); font-size: 11px; overflow-wrap: anywhere; }
    .plugin-admin-version, .plugin-admin-pill { display: inline-flex; align-items: center; border-radius: 999px; padding: 3px 8px; background: var(--color-bg-hover); color: var(--color-text-secondary); font-size: 11px; font-weight: 700; }
    .plugin-admin-status { display: inline-flex; align-items: center; gap: 5px; border-radius: 999px; padding: 5px 9px; font-size: 11px; font-weight: 700; white-space: nowrap; background: var(--color-bg-hover); color: var(--color-text-secondary); }
    .plugin-admin-status--success, .plugin-admin-pill--success { background: color-mix(in srgb, #2e9d62 14%, var(--color-bg-surface)); color: #24784c; }
    .plugin-admin-status--pending, .plugin-admin-pill--pending { background: color-mix(in srgb, #c28b24 16%, var(--color-bg-surface)); color: #8b641b; }
    .plugin-admin-status--warning, .plugin-admin-pill--danger { background: color-mix(in srgb, #c44848 14%, var(--color-bg-surface)); color: #a03737; }
    .plugin-admin-status--disabled { opacity: .72; }
    .plugin-admin-facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px 18px; margin-top: 16px; font-size: 12px; color: var(--color-text-secondary); }
    .plugin-admin-facts span { min-width: 0; overflow-wrap: anywhere; }
    .plugin-admin-facts strong { display: block; margin-bottom: 3px; color: var(--color-text-muted); font-size: 10px; letter-spacing: .04em; text-transform: uppercase; }
    .plugin-admin-list-item__error { display: flex; gap: 8px; margin-top: 14px; padding: 9px 11px; border-radius: 7px; background: color-mix(in srgb, #c44848 10%, var(--color-bg-surface)); color: var(--color-text-secondary); font-size: 12px; }
    .plugin-admin-list-item__footer { align-items: center; margin-top: 16px; padding-top: 13px; border-top: 1px dashed var(--color-border-paper); }
    .plugin-admin-actions { display: flex; gap: 7px; flex-wrap: wrap; justify-content: flex-end; }
    .plugin-admin-button { border: 1px solid var(--color-border-paper); border-radius: 7px; background: var(--color-bg-surface); color: var(--color-text-primary); padding: 7px 10px; font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; }
    .plugin-admin-button:hover:not(:disabled) { background: var(--color-bg-hover); }
    .plugin-admin-button:disabled { cursor: not-allowed; opacity: .48; }
    .plugin-admin-button--primary { background: var(--color-text-primary); color: var(--color-text-on-action); border-color: var(--color-text-primary); }
    .plugin-admin-button--primary:hover:not(:disabled) { background: var(--color-text-secondary); }
    .plugin-admin-button--danger { color: #a03737; }
    .plugin-admin-link-button { border: 0; background: transparent; color: var(--color-text-secondary); padding: 2px 0; font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
    .plugin-admin-readonly, .plugin-admin-muted { color: var(--color-text-muted); font-size: 12px; }
    .plugin-admin-empty { padding: 32px 18px; border: 1px dashed var(--color-border-paper); border-radius: 10px; text-align: center; color: var(--color-text-secondary); }
    .plugin-admin-empty p { margin: 8px auto 14px; max-width: 520px; font-size: 13px; }
    .plugin-admin-inline-warning { margin-bottom: 12px; padding: 9px 11px; border-radius: 7px; background: color-mix(in srgb, #c28b24 12%, var(--color-bg-surface)); color: var(--color-text-secondary); font-size: 12px; }
    .plugin-admin-inline-warning button { border: 0; background: transparent; color: inherit; text-decoration: underline; cursor: pointer; }
    .plugin-admin-inline-warning--error { background: color-mix(in srgb, #c44848 12%, var(--color-bg-surface)); }
    .plugin-admin-operation { margin: 0 0 16px; padding: 14px; border: 1px solid var(--color-border-paper); border-radius: 9px; background: var(--color-bg-surface); }
    .plugin-admin-operation h4, .plugin-admin-section-heading h4, .plugin-admin-section-heading h3 { margin: 0; }
    .plugin-admin-progress { height: 6px; margin: 12px 0 6px; border-radius: 999px; overflow: hidden; background: var(--color-bg-hover); }
    .plugin-admin-progress span { display: block; height: 100%; border-radius: inherit; background: var(--color-text-primary); transition: width .25s ease; }
    .plugin-admin-error { display: flex; gap: 10px; margin: 12px 0; padding: 12px; border: 1px solid color-mix(in srgb, #c44848 32%, var(--color-border-paper)); border-radius: 8px; background: color-mix(in srgb, #c44848 8%, var(--color-bg-surface)); font-size: 12px; }
    .plugin-admin-error__icon { display: grid; place-items: center; flex: 0 0 22px; height: 22px; border-radius: 50%; background: #a03737; color: white; font-weight: 800; }
    .plugin-admin-error strong, .plugin-admin-error code { display: block; margin-bottom: 5px; }
    .plugin-admin-inline-facts { display: grid; grid-template-columns: auto 1fr; gap: 3px 8px; margin: 8px 0; }
    .plugin-admin-inline-facts dt { color: var(--color-text-muted); }
    .plugin-admin-inline-facts dd { margin: 0; overflow-wrap: anywhere; }
    .plugin-admin-detail-backdrop { position: fixed; inset: 0; z-index: 1000; display: flex; justify-content: flex-end; background: rgba(17, 20, 24, .34); }
    .plugin-admin-detail { width: min(620px, 94vw); height: 100%; display: flex; flex-direction: column; background: var(--color-bg-app); box-shadow: -18px 0 50px rgba(0,0,0,.18); }
    .plugin-admin-detail__header { display: flex; justify-content: space-between; gap: 16px; padding: 22px 24px 16px; border-bottom: 1px solid var(--color-border-paper); }
    .plugin-admin-detail__header h2 { margin-bottom: 4px; font-size: 22px; }
    .plugin-admin-icon-button { width: 34px; height: 34px; border: 1px solid var(--color-border-paper); border-radius: 50%; background: transparent; color: var(--color-text-primary); font-size: 24px; line-height: 1; cursor: pointer; }
    .plugin-admin-detail__tabs { display: flex; gap: 8px; padding: 12px 24px; border-bottom: 1px solid var(--color-border-paper); }
    .plugin-admin-detail__body { flex: 1; overflow: auto; padding: 20px 24px 40px; }
    .plugin-admin-detail-section, .plugin-admin-capability-diff { padding: 16px 0; border-bottom: 1px solid var(--color-border-paper); }
    .plugin-admin-detail-section:first-child { padding-top: 0; }
    .plugin-admin-detail-section h3, .plugin-admin-capability-diff h4 { margin: 0 0 12px; font-size: 14px; }
    .plugin-admin-detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 0; }
    .plugin-admin-detail-grid div { padding: 10px; border-radius: 7px; background: var(--color-bg-surface); }
    .plugin-admin-detail-grid__wide { grid-column: 1 / -1; }
    .plugin-admin-detail-grid dt { color: var(--color-text-muted); font-size: 10px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
    .plugin-admin-detail-grid dd { margin: 5px 0 0; font-size: 12px; overflow-wrap: anywhere; }
    .plugin-admin-chip-list { display: flex; flex-wrap: wrap; gap: 6px; }
    .plugin-admin-chip-list span { border: 1px solid var(--color-border-paper); border-radius: 999px; padding: 4px 8px; background: var(--color-bg-surface); font-size: 11px; }
    .plugin-admin-code-list { margin: 10px 0 0; padding-left: 20px; }
    .plugin-admin-diff-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 12px 0; }
    .plugin-admin-diff-grid > div { padding: 11px; border-radius: 7px; background: var(--color-bg-surface); font-size: 12px; }
    .plugin-admin-diff-grid ul { margin: 8px 0 0; padding-left: 17px; }
    .plugin-admin-timeline { list-style: none; margin: 0; padding: 0; }
    .plugin-admin-timeline li { display: flex; gap: 10px; padding: 0 0 14px; }
    .plugin-admin-timeline li > span { flex: 0 0 8px; height: 8px; margin-top: 5px; border-radius: 50%; background: var(--color-text-muted); }
    .plugin-admin-timeline strong, .plugin-admin-timeline p, .plugin-admin-timeline time { display: block; margin: 0 0 3px; font-size: 12px; }
    .plugin-admin-timeline p, .plugin-admin-timeline time { color: var(--color-text-muted); }
    .plugin-admin-table > div { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 10px; padding: 9px 0; border-bottom: 1px dashed var(--color-border-paper); font-size: 11px; }
    .plugin-admin-install-backdrop { position: fixed; inset: 0; z-index: 1001; display: grid; place-items: center; padding: 20px; background: rgba(17, 20, 24, .42); }
    .plugin-admin-install { width: min(560px, 100%); max-height: 90vh; overflow: auto; padding: 22px; border-radius: 12px; background: var(--color-bg-app); box-shadow: 0 24px 70px rgba(0,0,0,.24); }
    .plugin-admin-install h3 { margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: 21px; }
    .plugin-admin-field { display: grid; gap: 6px; margin-top: 14px; font-size: 12px; font-weight: 600; }
    .plugin-admin-field input, .plugin-admin-field select { width: 100%; border: 1px solid var(--color-border-paper); border-radius: 7px; background: var(--color-bg-surface); color: var(--color-text-primary); padding: 9px 10px; font: inherit; font-weight: 400; }
    .plugin-admin-review { margin-top: 14px; padding: 12px; border-radius: 8px; background: var(--color-bg-surface); }
    .plugin-admin-review h4 { margin: 0 0 8px; }
    .plugin-admin-check { display: flex; gap: 8px; align-items: flex-start; margin: 14px 0; color: var(--color-text-secondary); font-size: 12px; line-height: 1.45; }
    @media (max-width: 680px) {
      .plugin-admin__header, .plugin-admin-list-item__top, .plugin-admin-list-item__footer { flex-direction: column; }
      .plugin-admin-facts, .plugin-admin-detail-grid, .plugin-admin-diff-grid, .plugin-admin-workflow-summary dl { grid-template-columns: 1fr; }
      .plugin-admin-detail-grid__wide { grid-column: auto; }
      .plugin-admin-actions { justify-content: flex-start; }
      .plugin-admin-detail__header, .plugin-admin-detail__tabs, .plugin-admin-detail__body { padding-left: 16px; padding-right: 16px; }
      .plugin-admin-table > div { grid-template-columns: 1fr auto; }
      .plugin-admin-table time { grid-column: 1 / -1; }
    }
  `;
}

export default function PluginAdminPage({ isMobile = false }: PluginAdminPageProps) {
  const [selectedItem, setSelectedItem] = useState<DeckPluginInstallation | null>(null);
  const [installOpen, setInstallOpen] = useState(false);
  const [installInput, setInstallInput] = useState<InstallPluginInput>(EMPTY_INSTALL_INPUT);
  const [installPreview, setInstallPreview] = useState<DeckPluginInstallation | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<Error | null>(null);
  const [capabilitiesConfirmed, setCapabilitiesConfirmed] = useState(false);

  const catalog = usePluginInstallations();
  const detail = usePluginInstallationDetail(selectedItem?.deckPluginId, selectedItem?.deckPluginVersion);
  const readiness = usePluginRuntimeReadiness(selectedItem?.deckPluginId);
  const refreshCatalog = catalog.refresh;
  const refreshDetail = detail.refresh;
  const refreshReadiness = readiness.refresh;
  const refreshAll = useCallback(() => {
    refreshCatalog();
    refreshDetail();
    refreshReadiness();
  }, [refreshCatalog, refreshDetail, refreshReadiness]);
  const operation = usePluginOperation(refreshAll);

  const openInstall = useCallback(() => {
    setInstallInput(EMPTY_INSTALL_INPUT);
    setInstallPreview(null);
    setPreviewError(null);
    setCapabilitiesConfirmed(false);
    setInstallOpen(true);
  }, []);

  const loadInstallPreview = useCallback(async () => {
    if (!installInput.deckPluginId.trim() || !EXACT_VERSION_PATTERN.test(installInput.deckPluginVersion.trim())) {
      setPreviewError(new Error('请输入 Deck Plugin ID 和精确 SemVer 版本。'));
      return;
    }
    setPreviewLoading(true);
    setPreviewError(null);
    setInstallPreview(null);
    setCapabilitiesConfirmed(false);
    try {
      const preview = await getPluginInstallationDetail(
        installInput.deckPluginId.trim(),
        installInput.deckPluginVersion.trim(),
      );
      setInstallPreview(preview);
    } catch (reason) {
      setPreviewError(reason instanceof Error ? reason : new Error('无法加载 manifest 预览。'));
    } finally {
      setPreviewLoading(false);
    }
  }, [installInput.deckPluginId, installInput.deckPluginVersion]);

  const submitInstall = useCallback(async () => {
    if (!installPreview || !capabilitiesConfirmed) return;
    try {
      await operation.install({
        ...installInput,
        deckPluginId: installInput.deckPluginId.trim(),
        deckPluginVersion: installInput.deckPluginVersion.trim(),
        source: installInput.source.trim(),
      });
      setInstallOpen(false);
    } catch {
      // The operation hook owns the safe visible error state.
    }
  }, [capabilitiesConfirmed, installInput, installPreview, operation]);

  const handleAction = useCallback(async (action: PluginMutationAction, item: DeckPluginInstallation) => {
    const deckPluginId = item.deckPluginId;
    if (!catalog.permissions.canManage) return;
    if (action === 'uninstall' && !window.confirm('确认软卸载该 Deck 工作流插件？历史 run 引用与来源元数据将由服务端保留。')) return;
    if (action === 'rollback' && !window.confirm('确认回滚默认版本？当前和历史运行不会被改绑。')) return;
    if (action === 'reject-upgrade' && !window.confirm('确认拒绝本次能力扩张升级？旧 ready 版本将保持可用。')) return;
    const targetVersion = action === 'upgrade'
      ? item.availableVersion
      : action === 'rollback' ? item.rollbackVersions[0] : undefined;
    try {
      await operation.mutate({ action, deckPluginId, targetVersion, purge: false });
    } catch {
      // The operation hook owns the safe visible error state.
    }
  }, [catalog.permissions.canManage, operation]);

  const selectedKey = selectedItem ? pluginAdminItemKey(selectedItem) : undefined;
  const operationApiError = operation.error as DeckPluginApiError | null;

  return (
    <section className="plugin-admin" aria-labelledby="plugin-admin-title" data-mobile={isMobile || undefined}>
      <style>{styles()}</style>
      <header className="plugin-admin__header">
        <div>
          <span className="plugin-admin-eyebrow">Settings · Plugins</span>
          <h2 id="plugin-admin-title">Deck 工作流插件</h2>
          <p>为 Dream 类型 Deck 提供创作 Skill、阶段指引和工作台内容结构。在 Deck 维护中选择工作流版本，后续新 Run 使用所选版本。</p>
        </div>
        {catalog.permissions.canManage && (
          <button type="button" className="plugin-admin-button plugin-admin-button--primary" onClick={openInstall}>
            安装工作流
          </button>
        )}
      </header>

      <section className="plugin-admin-workflow-summary" aria-labelledby="dream-story-workflow-title">
        <span className="plugin-admin-eyebrow">内置短剧工作流</span>
        <h3 id="dream-story-workflow-title">Dream Story Workflow</h3>
        <p>把短剧创作组织成项目准备与分集创作。用户在同一 Chat 中与 Dream Agent 协作，生成内容在 Dream 工作台按项目和 Episode 展示。</p>
        <dl>
          <div><dt>项目准备</dt><dd>建立项目和分集计划，整理各集共用的角色卡与场景卡。</dd></div>
          <div><dt>分集创作</dt><dd>为每个 Episode 生成剧本、分镜、Prompt 和审阅结果，支持继续修订与重新生成。</dd></div>
        </dl>
        <p>首次创作从 /drama-init 开始，之后可按需要调用或重复创作 Skill。渲染、配音、后期和宣发尚未开放。</p>
      </section>

      {operation.operation && <PluginOperationProgress operation={operation.operation} onDismiss={operation.clear} />}
      {operation.error && !operation.operation && (
        <PluginErrorCard
          code={operationApiError?.code}
          summary={operation.error.message}
          operationId={operationApiError?.operationId}
        />
      )}

      <PluginAdminList
        items={catalog.installations}
        selectedKey={selectedKey}
        loading={catalog.loading}
        error={catalog.error}
        canManage={catalog.permissions.canManage}
        busy={operation.submitting}
        onRetry={catalog.refresh}
        onSelect={setSelectedItem}
        onAction={(action, item) => { void handleAction(action, item); }}
      />

      {selectedItem && (
        <PluginAdminDetail
          item={selectedItem}
          detail={detail.detail?.deckPluginId === selectedItem.deckPluginId && detail.detail.deckPluginVersion === selectedItem.deckPluginVersion ? detail.detail : null}
          readiness={readiness.readiness}
          loading={detail.loading || readiness.loading}
          error={detail.error ?? readiness.error}
          canManage={catalog.permissions.canManage}
          busy={operation.submitting}
          onClose={() => setSelectedItem(null)}
          onRetry={() => { detail.refresh(); readiness.refresh(); }}
          onAction={(action, item) => { void handleAction(action, item); }}
        />
      )}

      {installOpen && (
        <div className="plugin-admin-install-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget && !operation.submitting) setInstallOpen(false);
        }}>
          <form className="plugin-admin-install" onSubmit={(event) => { event.preventDefault(); void submitInstall(); }}>
            <div className="plugin-admin-section-heading">
              <div><h3>安装 Deck 工作流插件</h3><p>读取工作流信息并审阅所需权限后，提交安装。</p></div>
              <button type="button" className="plugin-admin-icon-button" aria-label="关闭安装对话框" onClick={() => setInstallOpen(false)}>×</button>
            </div>
            <label className="plugin-admin-field">Deck Plugin ID
              <input required value={installInput.deckPluginId} placeholder="工作流 ID" onChange={(event) => { setInstallInput((value) => ({ ...value, deckPluginId: event.target.value })); setInstallPreview(null); }} />
            </label>
            <label className="plugin-admin-field">精确版本
              <input required value={installInput.deckPluginVersion} placeholder="精确 SemVer 版本" pattern="\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?" onChange={(event) => { setInstallInput((value) => ({ ...value, deckPluginVersion: event.target.value })); setInstallPreview(null); }} />
            </label>
            <label className="plugin-admin-field">来源类型
              <select value={installInput.sourceType} onChange={(event) => setInstallInput((value) => ({ ...value, sourceType: event.target.value as InstallPluginInput['sourceType'] }))}>
                <option value="marketplace">受控 marketplace</option>
                <option value="controlled">受控路径</option>
                {catalog.permissions.canInstallLocal && <option value="local">本地路径（管理员）</option>}
              </select>
            </label>
            <label className="plugin-admin-field">来源
              <input required value={installInput.source} placeholder="来源地址" onChange={(event) => setInstallInput((value) => ({ ...value, source: event.target.value }))} />
            </label>
            <div className="plugin-admin-actions" style={{ marginTop: 14 }}>
              <button type="button" className="plugin-admin-button" disabled={previewLoading} onClick={() => { void loadInstallPreview(); }}>
                {previewLoading ? '读取中…' : '读取工作流与权限'}
              </button>
            </div>
            {previewError && <PluginErrorCard code={(previewError as DeckPluginApiError).code} summary={previewError.message} />}
            {installPreview && (
              <div className="plugin-admin-review">
                <h4>能力确认</h4>
                <p className="plugin-admin-muted">{installPreview.displayName} · {installPreview.deckPluginVersion}</p>
                {installPreview.manifestRequestedCapabilities.length ? (
                  <div className="plugin-admin-chip-list">
                    {installPreview.manifestRequestedCapabilities.map((capability) => <span key={capability}>{capability}</span>)}
                  </div>
                ) : <p className="plugin-admin-muted">服务端 manifest 未声明能力。</p>}
                <label className="plugin-admin-check">
                  <input type="checkbox" checked={capabilitiesConfirmed} onChange={(event) => setCapabilitiesConfirmed(event.target.checked)} />
                  <span>我已审阅此工作流所需的权限。</span>
                </label>
              </div>
            )}
            <div className="plugin-admin-actions" style={{ marginTop: 18 }}>
              <button type="button" className="plugin-admin-button" disabled={operation.submitting} onClick={() => setInstallOpen(false)}>取消</button>
              <button type="submit" className="plugin-admin-button plugin-admin-button--primary" disabled={!installPreview || !capabilitiesConfirmed || operation.submitting}>
                {operation.submitting ? '提交中…' : '确认安装'}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}
