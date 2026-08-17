// [Input] Actor-scoped WorkflowRun selected by a Dream route deep link.
// [Output] WorkflowContextBar props with raw run status replaced by one safe Dream state.
// [Pos] Pure boundary between WorkflowRun persistence states and Dream UI context (Task 3 F9).

import type { WorkflowRun } from '../api/storyWorkspaceApi';
import type { WorkflowContextBarProps } from '../components/story-workspace/workflow/WorkflowContextBar';

export type StoryWorkspaceDreamWorkflowContextRun = Pick<
  WorkflowRun,
  | 'workflow_run_id'
  | 'deck_plugin_display_name'
  | 'deck_plugin_version'
  | 'workflow_summary'
  | 'status'
>;

export function storyWorkspaceDreamWorkflowContext(
  run: StoryWorkspaceDreamWorkflowContextRun | null,
): WorkflowContextBarProps | null {
  if (!run) return null;
  return {
    state: 'story_workspace_dream',
    deckPluginDisplayName: run.deck_plugin_display_name,
    deckPluginVersion: run.deck_plugin_version,
    workflowRunId: run.workflow_run_id,
    workflowSummary: run.workflow_summary,
  };
}
