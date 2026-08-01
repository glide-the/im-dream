// [Input] An authoritative WorkflowPreflight snapshot and optional run callback.
// [Output] The fixed eight-step progress list, stop-on-failure focus, and passed token action.
// [Pos] Story Workspace workflow preflight progress panel.
import {
  PREFLIGHT_CHECK_ORDER,
  type WorkflowPreflight,
  type WorkflowPreflightCheck,
  type WorkflowPreflightStep,
} from '../../../api/storyWorkspaceApi';
import { WorkflowErrorCard, type WorkflowRecoveryAction } from './WorkflowErrorCard';

const CHECK_LABELS: Record<WorkflowPreflightCheck, string> = {
  identity_workspace_permission: '身份、workspace 与 Deck 使用权限',
  binding_release: 'Binding revision 与精确 release 可用性',
  manifest_workflow_schema: 'Manifest、workflow definition 与输入输出 schema',
  host_agent_runtime_compatibility: 'Host、ClaudeAgent、Claude Code 与 Deck runtime 兼容性',
  capability_source_policy: '能力交集与来源策略',
  deck_runtime_snapshot: '创建或复用不可变 Deck runtime snapshot',
  runtime_materialization: 'Runtime lock 声明、物化、摘要与 load smoke',
  token_issuance: '输入 hash、过期时间与 preflight token',
};

const STEP_STATUS_LABELS: Record<WorkflowPreflightStep['status'], string> = {
  waiting: '等待',
  checking: '检查中',
  passed: '通过',
  failed: '失败',
};

function deriveSteps(preflight: WorkflowPreflight): WorkflowPreflightStep[] {
  if (preflight.checks?.length) {
    const byCheck = new Map(preflight.checks.map((step) => [step.check, step]));
    return PREFLIGHT_CHECK_ORDER.map((check) => byCheck.get(check) ?? { check, status: 'waiting' });
  }
  if (preflight.status === 'passed') {
    return PREFLIGHT_CHECK_ORDER.map((check) => ({ check, status: 'passed' }));
  }
  if (preflight.status === 'failed' && preflight.failed_check) {
    const failedIndex = PREFLIGHT_CHECK_ORDER.indexOf(preflight.failed_check);
    return PREFLIGHT_CHECK_ORDER.map((check, index) => ({
      check,
      status: index < failedIndex ? 'passed' : index === failedIndex ? 'failed' : 'waiting',
      error_code: index === failedIndex ? preflight.error_code : null,
    }));
  }
  return PREFLIGHT_CHECK_ORDER.map((check) => ({
    check,
    status: check === preflight.current_check ? 'checking' : 'waiting',
  }));
}

export interface PreflightProgressPanelProps {
  preflight: WorkflowPreflight;
  isStartingRun?: boolean;
  onStartRun?: (preflightToken: string) => void;
  onRecoveryAction?: (action: WorkflowRecoveryAction) => void;
}

export function PreflightProgressPanel({
  preflight,
  isStartingRun = false,
  onStartRun,
  onRecoveryAction,
}: PreflightProgressPanelProps) {
  const steps = deriveSteps(preflight);
  const completedCount = steps.filter((step) => step.status === 'passed').length;

  return (
    <section aria-labelledby="workflow-preflight-title" className="workflow-panel workflow-preflight-panel">
      <header className="workflow-panel__header">
        <div>
          <p className="workflow-panel__eyebrow">Workflow Preflight</p>
          <h3 className="workflow-panel__title" id="workflow-preflight-title">运行前检查</h3>
        </div>
        <span className="workflow-panel__count">{completedCount} / {PREFLIGHT_CHECK_ORDER.length}</span>
      </header>

      <ol className="workflow-preflight-list">
        {steps.map((step, index) => (
          <li
            aria-current={step.status === 'checking' ? 'step' : undefined}
            className={`workflow-preflight-step workflow-preflight-step--${step.status}`}
            key={step.check}
          >
            <span aria-hidden="true" className="workflow-preflight-step__marker">{index + 1}</span>
            <span className="workflow-preflight-step__name">{CHECK_LABELS[step.check]}</span>
            <span className="workflow-preflight-step__status">{STEP_STATUS_LABELS[step.status]}</span>
          </li>
        ))}
      </ol>

      {preflight.status === 'failed' && preflight.error_code && (
        <WorkflowErrorCard
          errorCode={preflight.error_code}
          failedStep={preflight.failed_check ? CHECK_LABELS[preflight.failed_check] : null}
          operationId={preflight.workflow_preflight_id}
          onAction={onRecoveryAction}
        />
      )}

      {preflight.status === 'passed' && preflight.preflight_token && (
        <div className="workflow-panel__footer">
          <p>8 项检查已通过。令牌仅用于本次锁定来源，不会显示在页面中。</p>
          <button
            className="workflow-button workflow-button--primary"
            disabled={isStartingRun}
            onClick={() => onStartRun?.(preflight.preflight_token as string)}
            type="button"
          >
            {isStartingRun ? '正在创建运行…' : '开始运行'}
          </button>
        </div>
      )}
    </section>
  );
}
