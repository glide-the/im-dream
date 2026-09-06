// [Input] A workflow selection/readiness state or an authoritative WorkflowRun snapshot.
// [Output] Explicit empty, warning, progress, review, failure, cancelled, and completion states.
// [Pos] Story Workspace main workflow status surface.
import type { WorkflowRun, WorkflowRunStep } from '../../../api/storyWorkspaceApi';
import { ProvenanceBadge } from './ProvenanceBadge';
import { WorkflowErrorCard, type WorkflowRecoveryAction } from './WorkflowErrorCard';

export type WorkflowDisplayState =
  | 'workflow_unselected'
  | 'workflow_unavailable'
  | 'deck_runtime_config_not_ready'
  | WorkflowRun['status'];

const STEP_LABELS: Record<WorkflowRunStep['status'], string> = {
  waiting: '等待',
  running: '运行中',
  completed: '完成',
  failed: '失败',
};

export interface WorkflowRunStatusPanelProps {
  state: WorkflowDisplayState;
  run?: WorkflowRun | null;
  unavailableReason?: string | null;
  deckOwner?: string | null;
  elapsedSeconds?: number | null;
  isMutating?: boolean;
  onChooseWorkflow?: () => void;
  onViewConfig?: () => void;
  onCancel?: () => void;
  onOpenReview?: () => void;
  onOpenRun?: (workflowRunId: string) => void;
  onRecoveryAction?: (action: WorkflowRecoveryAction) => void;
}

function formatElapsed(seconds: number | null | undefined): string | null {
  if (seconds === null || seconds === undefined || seconds < 0) return null;
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60);
  return `${minutes}:${String(remainder).padStart(2, '0')}`;
}

export function WorkflowRunStatusPanel({
  state,
  run,
  unavailableReason,
  deckOwner,
  elapsedSeconds,
  isMutating = false,
  onChooseWorkflow,
  onViewConfig,
  onCancel,
  onOpenReview,
  onOpenRun,
  onRecoveryAction,
}: WorkflowRunStatusPanelProps) {
  if (state === 'workflow_unselected') {
    return (
      <section className="workflow-panel workflow-panel--empty">
        <p className="workflow-panel__eyebrow">Workflow</p>
        <h3 className="workflow-panel__title">选择工作流以开始创作</h3>
        <p className="workflow-panel__message">工作流会在运行前锁定 Deck 插件版本与运行快照。</p>
        {onChooseWorkflow && <button className="workflow-button workflow-button--primary" onClick={onChooseWorkflow} type="button">选择工作流</button>}
      </section>
    );
  }

  if (state === 'workflow_unavailable') {
    return (
      <section className="workflow-panel workflow-panel--warning">
        <p className="workflow-panel__eyebrow">Workflow unavailable</p>
        <h3 className="workflow-panel__title">当前工作流不可用</h3>
        {unavailableReason && <p className="workflow-panel__message">{unavailableReason}</p>}
        {onChooseWorkflow && <button className="workflow-button workflow-button--primary" onClick={onChooseWorkflow} type="button">更换工作流</button>}
      </section>
    );
  }

  if (state === 'deck_runtime_config_not_ready') {
    return (
      <section className="workflow-panel workflow-panel--warning">
        <p className="workflow-panel__eyebrow">Deck runtime</p>
        <h3 className="workflow-panel__title">Deck 运行配置未就绪</h3>
        {deckOwner && <p className="workflow-panel__message">Deck owner：{deckOwner}</p>}
        {onViewConfig && <button className="workflow-button workflow-button--primary" onClick={onViewConfig} type="button">查看配置</button>}
      </section>
    );
  }

  if (!run) return null;

  if (state === 'failed' && run.error_code) {
    return (
      <WorkflowErrorCard
        deckOwner={deckOwner}
        errorCode={run.error_code}
        failedStep={run.failed_step}
        onAction={onRecoveryAction}
        workflowRunId={run.workflow_run_id}
      />
    );
  }

  const elapsed = formatElapsed(elapsedSeconds);
  const completedSteps = run.steps?.filter((step) => step.status === 'completed').length ?? 0;
  const totalSteps = run.steps?.length ?? 0;
  const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

  return (
    <section className={`workflow-panel workflow-run-panel workflow-run-panel--${state}`}>
      <header className="workflow-panel__header">
        <div>
          <p className="workflow-panel__eyebrow">Workflow run</p>
          <h3 className="workflow-panel__title">
            {state === 'pending_review' ? '结果待审阅' : state === 'completed' ? '运行已完成' : state === 'cancelled' ? '运行已取消' : '工作流运行中'}
          </h3>
        </div>
        <code className="workflow-run-panel__id">{run.workflow_run_id}</code>
      </header>

      {['preflight', 'queued', 'running', 'output_validating', 'confirmed'].includes(state) && (
        <>
          <div
            aria-label={`运行进度 ${progress}%`}
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={progress}
            className="workflow-progress"
            role="progressbar"
          >
            <span style={{ width: `${progress}%` }} />
          </div>
          <div className="workflow-run-panel__summary">
            <span>当前步骤：{run.current_step ?? (state === 'queued' ? '等待执行资源' : '等待状态更新')}</span>
            {elapsed && <span>已运行 {elapsed}</span>}
          </div>
          {run.steps && run.steps.length > 0 && (
            <ol className="workflow-run-steps">
              {run.steps.map((step) => (
                <li className={`workflow-run-step workflow-run-step--${step.status}`} key={step.id}>
                  <span>{step.name}</span><small>{STEP_LABELS[step.status]}</small>
                </li>
              ))}
            </ol>
          )}
          {onCancel && ['queued', 'running', 'confirmed'].includes(state) && (
            <button className="workflow-button" disabled={isMutating} onClick={onCancel} type="button">取消运行</button>
          )}
        </>
      )}

      {state === 'pending_review' && (
        <div className="workflow-panel__footer">
          <p>{run.result_summary ?? '工作流已生成可审阅结果。'}</p>
          {onOpenReview && <button className="workflow-button workflow-button--primary" onClick={onOpenReview} type="button">开始审阅</button>}
        </div>
      )}

      {state === 'cancelled' && <p className="workflow-panel__message">本次运行已停止，不会自动恢复。</p>}

      {state === 'completed' && (
        <>
          {run.result_summary && <p className="workflow-panel__message">{run.result_summary}</p>}
          <ProvenanceBadge
            onOpenRun={onOpenRun}
            provenance={{
              workflowRunId: run.workflow_run_id,
              deckPluginId: run.deck_plugin_id,
              deckPluginVersion: run.deck_plugin_version,
              deckRuntimeProfileId: run.deck_runtime_profile_id,
              deckRuntimeSnapshotId: run.deck_runtime_snapshot_id,
              runtimePluginLockId: run.runtime_plugin_lock_id,
              generatedAt: run.completed_at,
              runStatus: run.status,
              retryOfRunId: run.retry_of_run_id,
            }}
            voiceSource={run.source_context ? {
              access: run.source_context.source_access,
              voiceDisplayName: run.source_context.voice_display_name,
              sourceMessageTime: run.source_context.source_message_time,
              sourceUrl: run.source_context.source_url,
            } : null}
          />
        </>
      )}
    </section>
  );
}
