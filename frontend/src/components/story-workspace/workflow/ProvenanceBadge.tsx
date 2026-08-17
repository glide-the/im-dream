// [Input] Immutable workflow provenance and independently authorized Voice source metadata.
// [Output] Read-only run/source tracing with a fixed no-permission redaction state.
// [Pos] Story Workspace tables/review/run detail provenance surface.
export interface WorkflowProvenance {
  workflowRunId: string;
  deckPluginId: string;
  deckPluginVersion: string;
  deckRuntimeProfileId?: string | null;
  deckRuntimeSnapshotId: string;
  runtimePluginLockId: string;
  generatedAt?: string | null;
  runStatus?: string | null;
  retryOfRunId?: string | null;
}

export interface VoiceSourceProvenance {
  access: 'granted' | 'denied';
  voiceDisplayName?: string | null;
  sourceMessageTime?: string | null;
  sourceUrl?: string | null;
}

export interface ProvenanceBadgeProps {
  provenance: WorkflowProvenance;
  voiceSource?: VoiceSourceProvenance | null;
  compact?: boolean;
  onOpenRun?: (workflowRunId: string) => void;
}

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function ProvenanceBadge({
  provenance,
  voiceSource,
  compact = false,
  onOpenRun,
}: ProvenanceBadgeProps) {
  const generatedAt = formatDate(provenance.generatedAt);
  const sourceTime = voiceSource?.access === 'granted'
    ? formatDate(voiceSource.sourceMessageTime)
    : null;

  if (compact) {
    return (
      <span className="workflow-provenance-badge">
        <button onClick={() => onOpenRun?.(provenance.workflowRunId)} type="button">
          {provenance.workflowRunId}
        </button>
        <span>{provenance.deckPluginId} · v{provenance.deckPluginVersion}</span>
      </span>
    );
  }

  return (
    <section aria-label="工作流运行来源" className="workflow-provenance-card">
      <header>
        <div>
          <p className="workflow-panel__eyebrow">不可变来源</p>
          <h3 className="workflow-panel__title">运行来源与版本</h3>
        </div>
        {provenance.runStatus && <span className="workflow-status-chip">{provenance.runStatus}</span>}
      </header>
      <dl className="workflow-provenance-list">
        <div>
          <dt>Workflow run</dt>
          <dd>
            <button onClick={() => onOpenRun?.(provenance.workflowRunId)} type="button">
              {provenance.workflowRunId}
            </button>
          </dd>
        </div>
        <div><dt>Deck Plugin</dt><dd>{provenance.deckPluginId} · v{provenance.deckPluginVersion}</dd></div>
        {provenance.deckRuntimeProfileId && (
          <div><dt>Runtime profile</dt><dd>{provenance.deckRuntimeProfileId}</dd></div>
        )}
        <div><dt>Runtime snapshot</dt><dd>{provenance.deckRuntimeSnapshotId}</dd></div>
        <div><dt>Runtime lock</dt><dd>{provenance.runtimePluginLockId}</dd></div>
        {generatedAt && <div><dt>生成时间</dt><dd>{generatedAt}</dd></div>}
        {provenance.retryOfRunId && <div><dt>重试来源</dt><dd>{provenance.retryOfRunId}</dd></div>}
      </dl>

      {voiceSource?.access === 'denied' && (
        <p className="workflow-voice-source workflow-voice-source--denied">来源：Voice 对话（无权查看）</p>
      )}
      {voiceSource?.access === 'granted' && (
        <div className="workflow-voice-source">
          <span>
            来源：Voice {voiceSource.voiceDisplayName ?? '对话'}{sourceTime ? ` · ${sourceTime}` : ''}
          </span>
          {voiceSource.sourceUrl && (
            <a href={voiceSource.sourceUrl}>返回来源对话</a>
          )}
        </div>
      )}
    </section>
  );
}
