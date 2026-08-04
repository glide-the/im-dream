// [Input] Current Deck binding/runtime/readiness projection and permitted navigation callbacks.
// [Output] A compact workflow context and action bar with a sanitized config summary.
// [Pos] Story Workspace main-region workflow context header.
// [Sync] 2026-08-04: add a status-agnostic Dream collaboration context while
//                    preserving legacy labels for non-Dream resource pages.
import type { WorkflowRunStatus } from '../../../api/storyWorkspaceApi';
import { storyWorkspaceWorkflowContextLabel } from './storyWorkspaceWorkflowContext';

export type WorkflowContextState =
  | 'workflow_unselected'
  | 'workflow_unavailable'
  | 'deck_runtime_config_not_ready'
  | 'story_workspace_dream'
  | 'ready'
  | 'preflight_checking'
  | WorkflowRunStatus;

export interface WorkflowContextBarProps {
  state: WorkflowContextState;
  deckPluginDisplayName?: string | null;
  deckPluginVersion?: string | null;
  workflowSummary?: string | null;
  runtimeReady?: boolean | null;
  deckRuntimeProfileId?: string | null;
  deckRuntimeSnapshotId?: string | null;
  runtimePluginLockId?: string | null;
  workflowRunId?: string | null;
  progressLabel?: string | null;
  selectorLocked?: boolean;
  onChooseWorkflow?: () => void;
  onStartPreflight?: () => void;
  onCancel?: () => void;
  onRetry?: () => void;
  onOpenReview?: () => void;
}

export function WorkflowContextBar({
  state,
  deckPluginDisplayName,
  deckPluginVersion,
  workflowSummary,
  runtimeReady,
  deckRuntimeProfileId,
  deckRuntimeSnapshotId,
  runtimePluginLockId,
  workflowRunId,
  progressLabel,
  selectorLocked = false,
  onChooseWorkflow,
  onStartPreflight,
  onCancel,
  onRetry,
  onOpenReview,
}: WorkflowContextBarProps) {
  const hasWorkflow = Boolean(deckPluginDisplayName && deckPluginVersion);
  const canCancel = state === 'queued' || state === 'running' || state === 'continuing';
  const canStart = hasWorkflow && runtimeReady === true
    && (state === 'ready' || state === 'completed' || state === 'cancelled');

  return (
    <section aria-label="当前工作流上下文" className="workflow-context-bar">
      <div className="workflow-context-bar__identity">
        <span aria-hidden="true" className="workflow-context-bar__icon">◆</span>
        <div>
          <p className="workflow-context-bar__name">
            {hasWorkflow ? `${deckPluginDisplayName} v${deckPluginVersion}` : '未选择工作流'}
          </p>
          {workflowSummary && <p className="workflow-context-bar__summary">{workflowSummary}</p>}
        </div>
      </div>

      <div className="workflow-context-bar__facts">
        <span className={`workflow-context-bar__fact workflow-context-bar__fact--${runtimeReady === true ? 'ready' : runtimeReady === false ? 'blocked' : 'unknown'}`}>
          Deck 配置：{runtimeReady === true ? 'Ready' : runtimeReady === false ? '未就绪' : '待确认'}
        </span>
        <span className={`workflow-context-bar__fact workflow-context-bar__fact--state-${state}`}>
          运行：{storyWorkspaceWorkflowContextLabel(state)}{progressLabel ? ` · ${progressLabel}` : ''}
        </span>
        {workflowRunId && <code className="workflow-context-bar__run-id">{workflowRunId}</code>}
      </div>

      <div className="workflow-context-bar__actions">
        {onChooseWorkflow && (
          <button className="workflow-button" disabled={selectorLocked} onClick={onChooseWorkflow} type="button">
            更换工作流
          </button>
        )}
        {(deckRuntimeProfileId || deckRuntimeSnapshotId || runtimePluginLockId) && (
          <details className="workflow-context-config">
            <summary className="workflow-button">查看配置</summary>
            <dl>
              {deckRuntimeProfileId && <div><dt>Profile</dt><dd>{deckRuntimeProfileId}</dd></div>}
              {deckRuntimeSnapshotId && <div><dt>Snapshot</dt><dd>{deckRuntimeSnapshotId}</dd></div>}
              {runtimePluginLockId && <div><dt>Runtime lock</dt><dd>{runtimePluginLockId}</dd></div>}
            </dl>
          </details>
        )}
        {onStartPreflight && canStart && (
          <button className="workflow-button workflow-button--primary" onClick={onStartPreflight} type="button">开始运行</button>
        )}
        {onCancel && canCancel && (
          <button className="workflow-button" onClick={onCancel} type="button">取消</button>
        )}
        {onRetry && state === 'failed' && (
          <button className="workflow-button workflow-button--primary" onClick={onRetry} type="button">重试</button>
        )}
        {onOpenReview && state === 'pending_review' && (
          <button className="workflow-button workflow-button--primary" onClick={onOpenReview} type="button">审阅结果</button>
        )}
      </div>
    </section>
  );
}
