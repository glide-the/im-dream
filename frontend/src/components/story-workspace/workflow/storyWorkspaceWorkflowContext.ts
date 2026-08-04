// [Input] A WorkflowContextBar state selected by Dream or legacy resource pages.
// [Output] Stable user-facing context label without coupling tests to JSX rendering.
// [Pos] Pure Story Workspace workflow-context label seam (Task 3 F9).

import type { WorkflowContextState } from './WorkflowContextBar';

const STORY_WORKSPACE_WORKFLOW_CONTEXT_LABELS: Record<WorkflowContextState, string> = {
  workflow_unselected: '未选择工作流',
  workflow_unavailable: '工作流不可用',
  deck_runtime_config_not_ready: '配置未就绪',
  story_workspace_dream: 'Dream 协作中',
  ready: '可运行',
  preflight_checking: '预检中…',
  preflight: '预检中…',
  queued: '等待运行',
  running: '运行中…',
  output_validating: '校验结果中…',
  pending_review: '待审阅',
  confirmed: '已确认',
  rejected: '已驳回',
  continuing: '继续运行中…',
  completed: '已完成',
  failed: '运行失败',
  cancelled: '已取消',
};

export function storyWorkspaceWorkflowContextLabel(state: WorkflowContextState): string {
  return STORY_WORKSPACE_WORKFLOW_CONTEXT_LABELS[state];
}
