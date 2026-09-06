// [Input] Selected normalized plugin, optional server detail/readiness, permission, and lifecycle callbacks.
// [Output] Configuration/Status drawer with manifest, runtime lock, capabilities, history, runs, and recovery.
// [Pos] Plugin Admin detail surface.

import { useState } from 'react';
import type {
  DeckPluginInstallation,
  PluginAdminItem,
  PluginMutationAction,
} from '../../api/deckPluginAdminApi';
import PluginCapabilityDiff from './PluginCapabilityDiff';
import PluginErrorCard from './PluginErrorCard';
import PluginStatusBadge from './PluginStatusBadge';

interface PluginAdminDetailProps {
  item: PluginAdminItem;
  detail?: DeckPluginInstallation | null;
  readiness?: Partial<DeckPluginInstallation> | null;
  loading?: boolean;
  error?: Error | null;
  canManage: boolean;
  busy: boolean;
  onClose: () => void;
  onRetry: () => void;
  onAction: (action: PluginMutationAction, item: PluginAdminItem) => void;
}

function formatDate(value?: string): string {
  if (!value) return '无记录';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium', timeStyle: 'short',
  }).format(date);
}

function EmptyLine({ children = '未返回' }: { children?: string }) {
  return <span className="plugin-admin-muted">{children}</span>;
}

export default function PluginAdminDetail({
  item,
  detail,
  readiness,
  loading = false,
  error,
  canManage,
  busy,
  onClose,
  onRetry,
  onAction,
}: PluginAdminDetailProps) {
  const [tab, setTab] = useState<'configuration' | 'status'>('configuration');
  const isDeck = item.category === 'deck-workflow';
  const installation = isDeck ? detail ?? item : null;
  const declarationStatus = readiness?.declarationStatus ?? item.declarationStatus;
  const materializationStatus = readiness?.materializationStatus ?? item.materializationStatus;
  const activationStatus = readiness?.activationStatus ?? item.activationStatus;
  const displayId = item.category === 'deck-workflow' ? item.deckPluginId : item.claudeCodePluginId;
  const version = item.category === 'deck-workflow' ? item.deckPluginVersion : item.resolvedVersion;
  const errorCode = readiness?.lastErrorCode ?? installation?.lastErrorCode ?? item.lastErrorCode;
  const errorSummary = readiness?.lastErrorSummary ?? installation?.lastErrorSummary ?? item.lastErrorSummary;

  return (
    <div className="plugin-admin-detail-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <aside className="plugin-admin-detail" role="dialog" aria-modal="true" aria-labelledby="plugin-admin-detail-title">
        <header className="plugin-admin-detail__header">
          <div>
            <span className="plugin-admin-eyebrow">{isDeck ? 'Deck 工作流插件' : 'ClaudeAgent 运行时插件'}</span>
            <h2 id="plugin-admin-detail-title">{item.displayName}</h2>
            <code>{displayId} · {version}</code>
          </div>
          <button type="button" className="plugin-admin-icon-button" aria-label="关闭插件详情" onClick={onClose}>×</button>
        </header>

        <div className="plugin-admin-detail__tabs" role="tablist" aria-label="Plugin detail tabs">
          {(['configuration', 'status'] as const).map((value) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={tab === value}
              className={tab === value ? 'is-active' : ''}
              onClick={() => setTab(value)}
            >
              {value === 'configuration' ? 'Configuration' : 'Status'}
            </button>
          ))}
        </div>

        <div className="plugin-admin-detail__body">
          {loading && <div className="plugin-admin-inline-warning">正在刷新服务端详情…</div>}
          {error && (
            <div className="plugin-admin-inline-warning plugin-admin-inline-warning--error">
              详情刷新失败：{error.message} <button type="button" onClick={onRetry}>重试</button>
            </div>
          )}

          {tab === 'configuration' ? (
            <>
              <section className="plugin-admin-detail-section">
                <h3>身份与来源</h3>
                <dl className="plugin-admin-detail-grid">
                  <div><dt>精确版本</dt><dd>{version}</dd></div>
                  <div><dt>来源</dt><dd>{installation?.sourceLabel ?? 'runtime lock'}</dd></div>
                  <div><dt>schema_version</dt><dd>{installation?.manifest?.schemaVersion ?? <EmptyLine />}</dd></div>
                  <div><dt>author</dt><dd>{installation?.manifest?.author ?? <EmptyLine />}</dd></div>
                  {!isDeck && <div><dt>artifact_digest</dt><dd><code>{item.artifactDigest ?? '未返回'}</code></dd></div>}
                </dl>
              </section>

              {installation && (
                <>
                  <section className="plugin-admin-detail-section">
                    <h3>工作流与 Schema</h3>
                    <dl className="plugin-admin-detail-grid">
                      <div><dt>输入 schema</dt><dd>{installation.manifest?.inputSchemaVersion ?? <EmptyLine />}</dd></div>
                      <div><dt>输出 schema</dt><dd>{installation.manifest?.outputSchemaVersion ?? <EmptyLine />}</dd></div>
                      <div className="plugin-admin-detail-grid__wide"><dt>Deck runtime contract</dt><dd>{installation.manifest?.deckRuntimeContract ?? <EmptyLine />}</dd></div>
                    </dl>
                    {installation.manifest?.workflowReferences.length ? (
                      <ul className="plugin-admin-code-list">
                        {installation.manifest.workflowReferences.map((reference) => <li key={reference}><code>{reference}</code></li>)}
                      </ul>
                    ) : <EmptyLine>未返回工作流定义引用</EmptyLine>}
                  </section>

                  <section className="plugin-admin-detail-section">
                    <h3>Manifest requested capabilities</h3>
                    {installation.manifestRequestedCapabilities.length ? (
                      <div className="plugin-admin-chip-list">
                        {installation.manifestRequestedCapabilities.map((capability) => <span key={capability}>{capability}</span>)}
                      </div>
                    ) : <EmptyLine />}
                  </section>

                  <section className="plugin-admin-detail-section">
                    <h3>ClaudeAgent 运行时依赖</h3>
                    {installation.runtimePlugins.length ? installation.runtimePlugins.map((runtime) => (
                      <div className="plugin-admin-runtime-row" key={`${runtime.claudeCodePluginId}:${runtime.resolvedVersion}`}>
                        <div><strong>{runtime.claudeCodePluginId}</strong><code>{runtime.resolvedVersion}</code></div>
                        <PluginStatusBadge
                          compact
                          declarationStatus={runtime.declarationStatus}
                          materializationStatus={runtime.materializationStatus}
                          activationStatus={runtime.activationStatus}
                        />
                        <code>{runtime.artifactDigest ?? runtime.versionConstraint ?? 'digest 未返回'}</code>
                      </div>
                    )) : <EmptyLine>当前详情未返回 Claude Code Plugin lock</EmptyLine>}
                  </section>
                </>
              )}
            </>
          ) : (
            <>
              <section className="plugin-admin-detail-section">
                <div className="plugin-admin-section-heading">
                  <div><h3>三维状态</h3><p>只展示服务端状态，不在浏览器中推导 run-ready。</p></div>
                  <PluginStatusBadge
                    declarationStatus={declarationStatus}
                    materializationStatus={materializationStatus}
                    activationStatus={activationStatus}
                  />
                </div>
                <dl className="plugin-admin-detail-grid">
                  <div><dt>Declaration</dt><dd>{declarationStatus}</dd></div>
                  <div><dt>Materialization</dt><dd>{materializationStatus}</dd></div>
                  <div><dt>Activation</dt><dd>{activationStatus}</dd></div>
                  <div><dt>Health</dt><dd>{readiness?.healthStatus ?? installation?.healthStatus ?? item.healthStatus}</dd></div>
                  {installation && <div><dt>Compatibility</dt><dd>{installation.compatibilityStatus}</dd></div>}
                  {installation && <div><dt>Last run</dt><dd>{formatDate(installation.lastRunAt)}</dd></div>}
                </dl>
              </section>

              {installation && (
                <section className="plugin-admin-detail-section">
                  <h3>Effective capabilities</h3>
                  <p className="plugin-admin-muted">权威交集由后端返回；前端不自行计算。</p>
                  {installation.effectiveCapabilities.length ? (
                    <div className="plugin-admin-chip-list">
                      {installation.effectiveCapabilities.map((capability) => <span key={capability}>{capability}</span>)}
                    </div>
                  ) : <EmptyLine />}
                </section>
              )}

              {installation?.capabilityDiff && (
                <PluginCapabilityDiff
                  diff={installation.capabilityDiff}
                  pendingApproval={installation.status === 'upgrade_pending'}
                  canManage={canManage}
                  busy={busy}
                  onApprove={() => onAction('approve-upgrade', item)}
                  onReject={() => onAction('reject-upgrade', item)}
                />
              )}

              <PluginErrorCard
                code={errorCode}
                summary={errorSummary}
                stage={installation?.lastErrorStage}
                operationId={installation?.operationId}
                canRecover={canManage && (materializationStatus === 'failed' || activationStatus === 'load_failed')}
                onRecover={() => onAction('reconcile', item)}
              />

              {installation && (
                <>
                  <section className="plugin-admin-detail-section">
                    <h3>安装状态历史</h3>
                    {installation.history.length ? (
                      <ol className="plugin-admin-timeline">
                        {installation.history.map((entry) => (
                          <li key={entry.id}>
                            <span />
                            <div><strong>{entry.action} · {entry.status}</strong><p>{entry.summary ?? entry.actor ?? '服务端状态记录'}</p><time>{formatDate(entry.occurredAt)}</time></div>
                          </li>
                        ))}
                      </ol>
                    ) : <EmptyLine>暂无历史记录</EmptyLine>}
                  </section>

                  <section className="plugin-admin-detail-section">
                    <h3>最近运行</h3>
                    {installation.recentRuns.length ? (
                      <div className="plugin-admin-table">
                        {installation.recentRuns.map((run) => (
                          <div key={run.runId}><code>{run.runId}</code><span>{run.status}</span><time>{formatDate(run.startedAt)}</time></div>
                        ))}
                      </div>
                    ) : <EmptyLine>暂无运行记录</EmptyLine>}
                  </section>

                  <section className="plugin-admin-detail-section">
                    <h3>操作日志</h3>
                    {installation.operationLogs.length ? (
                      <div className="plugin-admin-table">
                        {installation.operationLogs.map((entry) => (
                          <div key={entry.id}><strong>{entry.action}</strong><span>{entry.status}</span><time>{formatDate(entry.occurredAt)}</time></div>
                        ))}
                      </div>
                    ) : <EmptyLine>暂无操作日志</EmptyLine>}
                  </section>
                </>
              )}
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
