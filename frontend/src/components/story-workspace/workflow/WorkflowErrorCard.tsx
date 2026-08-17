// [Input] A structured workflow error code and authorized recovery callbacks.
// [Output] Safe user copy, diagnostic ids, and bounded recovery actions without raw server detail.
// [Pos] Story Workspace workflow error recovery card.
export type WorkflowRecoveryAction =
  | 'choose_workflow'
  | 'choose_version'
  | 'view_config'
  | 'choose_compatible_config'
  | 'retry'
  | 'request_access'
  | 'report'
  | 'refresh'
  | 'view_run'
  | 'wait_for_runtime';

interface WorkflowErrorPresentation {
  title: string;
  message: string;
  actions: WorkflowRecoveryAction[];
}

const WORKFLOW_ERROR_PRESENTATIONS: Record<string, WorkflowErrorPresentation> = {
  WORKFLOW_SELECTION_REQUIRED: {
    title: '尚未选择工作流',
    message: '请先选择工作流插件，再开始预检。',
    actions: ['choose_workflow'],
  },
  DECK_PLUGIN_UNAVAILABLE: {
    title: '工作流版本不可用',
    message: '当前锁定的工作流版本不可使用，请选择其他可用版本。',
    actions: ['choose_version'],
  },
  DECK_RUNTIME_CONFIG_INVALID: {
    title: 'Deck 运行配置未就绪',
    message: '运行配置缺失、未激活或已经过期。',
    actions: ['view_config'],
  },
  DECK_RUNTIME_CONFIG_INCOMPATIBLE: {
    title: 'Deck 运行配置不兼容',
    message: '当前运行快照与工作流合同不兼容。',
    actions: ['choose_compatible_config'],
  },
  DECK_RUNTIME_CONFIG_UNAVAILABLE: {
    title: 'Deck 运行配置暂不可用',
    message: '服务暂时无法读取运行配置，你的输入已保留。',
    actions: ['retry'],
  },
  WORKFLOW_PERMISSION_DENIED: {
    title: '权限不足',
    message: '你没有使用当前工作流或查看其来源的权限。',
    actions: ['request_access', 'choose_workflow'],
  },
  AGENT_EXECUTION_FAILED: {
    title: '运行失败',
    message: 'Agent 未能完成本次运行，可按原版本创建新的运行。',
    actions: ['retry', 'report'],
  },
  OUTPUT_CONTRACT_INVALID: {
    title: '结果格式不符合预期',
    message: '输出没有通过工作流结果合同校验。',
    actions: ['retry', 'choose_workflow'],
  },
  CONFIG_VERSION_DRIFT: {
    title: '配置版本已变化',
    message: '本次运行仍保留已锁定来源；升级后需创建新的运行。',
    actions: ['view_config', 'retry'],
  },
  RUNTIME_PLUGIN_NOT_READY: {
    title: '运行时插件未就绪',
    message: '运行时能力包仍在物化或加载中。',
    actions: ['wait_for_runtime', 'report'],
  },
  BINDING_REVISION_CONFLICT: {
    title: '工作流选择已被修改',
    message: '当前页面的工作流选择不是最新版本，请刷新后重试。',
    actions: ['refresh'],
  },
  IDEMPOTENCY_CONFLICT: {
    title: '检测到重复请求',
    message: '该操作键已用于不同请求，请查看现有运行状态。',
    actions: ['view_run'],
  },
  SECURITY_REVOCATION: {
    title: '运行已因安全策略停止',
    message: '当前版本或权限已被撤销，原运行不会恢复。',
    actions: ['choose_version', 'report'],
  },
};

const ACTION_LABELS: Record<WorkflowRecoveryAction, string> = {
  choose_workflow: '选择工作流',
  choose_version: '更换版本',
  view_config: '查看配置',
  choose_compatible_config: '选择兼容配置或版本',
  retry: '重试',
  request_access: '申请授权',
  report: '报告问题',
  refresh: '刷新',
  view_run: '查看运行状态',
  wait_for_runtime: '等待物化',
};

export interface WorkflowErrorCardProps {
  errorCode: string;
  failedStep?: string | null;
  workflowRunId?: string | null;
  operationId?: string | null;
  deckOwner?: string | null;
  onAction?: (action: WorkflowRecoveryAction) => void;
}

export function WorkflowErrorCard({
  errorCode,
  failedStep,
  workflowRunId,
  operationId,
  deckOwner,
  onAction,
}: WorkflowErrorCardProps) {
  const presentation = WORKFLOW_ERROR_PRESENTATIONS[errorCode] ?? {
    title: '工作流操作未完成',
    message: '发生了可恢复的问题，请刷新状态或报告问题。',
    actions: ['refresh', 'report'] as WorkflowRecoveryAction[],
  };

  return (
    <section aria-live="polite" className="workflow-error-card" role="alert">
      <div aria-hidden="true" className="workflow-error-card__icon">!</div>
      <div className="workflow-error-card__content">
        <p className="workflow-panel__eyebrow">需要处理</p>
        <h3 className="workflow-panel__title">{presentation.title}</h3>
        <p className="workflow-panel__message">{presentation.message}</p>
        {deckOwner && (
          <p className="workflow-panel__meta">Deck owner：{deckOwner}</p>
        )}
        <div className="workflow-panel__actions">
          {presentation.actions.map((action, index) => (
            <button
              className={index === 0 ? 'workflow-button workflow-button--primary' : 'workflow-button'}
              key={action}
              onClick={() => onAction?.(action)}
              type="button"
            >
              {ACTION_LABELS[action]}
            </button>
          ))}
        </div>
        <details className="workflow-technical-details">
          <summary>详细信息</summary>
          <dl>
            <div><dt>error_code</dt><dd>{errorCode}</dd></div>
            {failedStep && <div><dt>失败步骤</dt><dd>{failedStep}</dd></div>}
            {workflowRunId && <div><dt>workflow_run_id</dt><dd>{workflowRunId}</dd></div>}
            {operationId && <div><dt>operation_id</dt><dd>{operationId}</dd></div>}
          </dl>
        </details>
      </div>
    </section>
  );
}
