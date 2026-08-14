// [Input] Canonical camelCase Dream file projections.
// [Output] Local-draft hydration and text-editor conversion helpers.
// [Pos] Story Workspace Dream page pure view-model seam (Task 3 F4)

import type {
  StoryWorkspaceDreamAgentActivityProjection,
  StoryWorkspaceDreamFieldValue,
  StoryWorkspaceDreamFilesResponse,
  StoryWorkspaceDreamLifecycleState,
} from '../../hooks/story-workspace/contracts';
import type { WorkflowRun, WorkflowRunStatus } from '../../api/storyWorkspaceApi';
import type { StoryWorkspaceDreamStageSnapshot } from '../../components/story-workspace/dreamState';
import { STORY_WORKSPACE_DREAM_STAGES } from '../../components/story-workspace/dreamState';

/** Map REST projections to the exact three-field local edit whitelist. */
export function storyWorkspaceDreamStageSnapshotsFromFiles(
  files: StoryWorkspaceDreamFilesResponse,
): StoryWorkspaceDreamStageSnapshot[] {
  return STORY_WORKSPACE_DREAM_STAGES.flatMap((stage) => {
    const projection = files.stages[stage];
    if (!projection) return [];
    return [{
      stage,
      revision: projection.revision,
      items: projection.items.map((item) => ({
        entityId: item.entityId,
        fields: {
          displayName: item.displayName,
          summary: item.summary,
          relations: [...item.relations],
        },
        editableFields: ['displayName', 'summary', 'relations'],
      })),
    }];
  });
}

export function storyWorkspaceDreamEditorValue(
  value: StoryWorkspaceDreamFieldValue,
): string {
  if (value === null) return '';
  if (Array.isArray(value)) return value.map(String).join('，');
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

export function storyWorkspaceParseDreamEditorValue(
  field: 'displayName' | 'summary' | 'relations',
  value: string,
): StoryWorkspaceDreamFieldValue {
  if (field === 'relations') {
    const seen = new Set<string>();
    return value.split(/[，,]/).map((part) => part.trim()).filter((part) => {
      if (!part || seen.has(part)) return false;
      seen.add(part);
      return true;
    });
  }
  const trimmed = value.trim();
  if (field === 'displayName') {
    if (!trimmed) throw new Error('名称不能为空');
    return trimmed;
  }
  return trimmed || null;
}

export type StoryWorkspaceDreamConfirmationPersistence = Pick<
  StoryWorkspaceDreamFilesResponse,
  'confirmationAccepted' | 'confirmationDispatched'
>;

/** Recover the visible one-confirm lifecycle from durable server facts. */
export function storyWorkspaceDreamLifecycleFromPersistence(
  persistence: StoryWorkspaceDreamConfirmationPersistence | null,
  runStatus: WorkflowRunStatus | null | undefined,
  fallback: StoryWorkspaceDreamLifecycleState,
): StoryWorkspaceDreamLifecycleState {
  if (runStatus === 'failed' || runStatus === 'rejected' || runStatus === 'cancelled') {
    return fallback;
  }
  if (!persistence?.confirmationAccepted) return fallback;
  return persistence.confirmationDispatched && runStatus === 'completed'
    ? 'story-workspace-dream-completed'
    : 'story-workspace-dream-running';
}

export function storyWorkspaceDreamRunFailureNotice(
  run: Pick<WorkflowRun, 'status' | 'error_code' | 'failed_step'> | null,
): string | null {
  if (run?.status !== 'failed') return null;
  if (run.error_code === 'GATEWAY_TOKEN_ALLOWANCE_EXHAUSTED') {
    return '当前周期 Token 额度已用完。运行已安全停止，请查看订阅与用量后重试。';
  }
  if (
    run.error_code === 'GATEWAY_MODEL_SELECTION_STALE'
    || run.error_code === 'GATEWAY_MODEL_NOT_AVAILABLE'
    || run.error_code === 'GATEWAY_FORBIDDEN'
  ) {
    return '当前平台模型已不可调用。运行已安全停止，请在设置中重新选择模型或查看订阅资格。';
  }
  if (
    run.error_code === 'GATEWAY_UNAVAILABLE'
    || run.error_code === 'GATEWAY_PROVIDER_FAILED'
    || run.error_code === 'DREAM_AGENT_DISPATCH_FAILED'
  ) {
    return 'Dream Agent 暂时无法连接平台模型服务。运行已安全停止，未完成的步骤不会显示为成功。';
  }
  return 'Dream Agent 执行失败。运行已安全停止，未完成的步骤不会显示为成功。';
}

/** Copy has no rejected/failed/retry branch: acceptance is monotonic. */
export function storyWorkspaceDreamPersistenceNotice(
  persistence: StoryWorkspaceDreamConfirmationPersistence | null,
  lifecycle: 'running' | 'completed',
): string {
  if (persistence?.confirmationAccepted && !persistence.confirmationDispatched) {
    return '命令已保存，等待同一 Dream Agent 接续';
  }
  if (lifecycle === 'completed') return '同一 Dream Agent 已完成后续执行';
  return '同一 Dream Agent 正在执行';
}

const DREAM_AGENT_OPERATION_LABELS: Partial<Record<
  NonNullable<StoryWorkspaceDreamAgentActivityProjection['operationScope']>,
  string
>> = {
  content_generation: 'Dream 内容生成',
  workflow_operation: 'Dream 工作流操作',
};

const DREAM_AGENT_OPERATION_STATE_COPY: Record<
  NonNullable<StoryWorkspaceDreamAgentActivityProjection['operationState']>,
  string
> = {
  started: '正在运行',
  waiting_confirmation: '等待确认',
  succeeded: '已完成',
  failed: '执行失败',
};

/**
 * Render a content-free Observer hint. This copy is informational only: callers
 * must never use it to drive Chat controls, confirmation, or Workflow state.
 */
export function storyWorkspaceDreamAgentActivityNotice(
  activity: StoryWorkspaceDreamAgentActivityProjection | null | undefined,
): string | null {
  if (!activity) return null;
  if (activity.activity === 'reconcile_requested') {
    return '正在校验 Dream 业务投影';
  }
  if (
    activity.activity !== 'activity_started_hint'
    && activity.activity !== 'activity_settled_hint'
  ) return null;
  if (
    !activity.operationScope
    || !activity.operationState
    || activity.operationState === 'waiting_confirmation'
  ) return null;
  const operationLabel = DREAM_AGENT_OPERATION_LABELS[activity.operationScope];
  if (!operationLabel) return null;
  return `${operationLabel}${DREAM_AGENT_OPERATION_STATE_COPY[activity.operationState]}`;
}
