// [Input] Canonical camelCase Dream file projections.
// [Output] Local-draft hydration and text-editor conversion helpers.
// [Pos] Story Workspace Dream page pure view-model seam (Task 3 F4)

import type {
  StoryWorkspaceDreamFieldValue,
  StoryWorkspaceDreamFilesResponse,
  StoryWorkspaceDreamLifecycleState,
} from '../../hooks/story-workspace/contracts';
import type { WorkflowRunStatus } from '../../api/storyWorkspaceApi';
import type { StoryWorkspaceDreamStageSnapshot } from '../../components/story-workspace/dreamState';
import { STORY_WORKSPACE_DREAM_STAGES } from '../../components/story-workspace/dreamState';

/** Map REST projections to the exact three-field local edit whitelist. */
export function dreamStageSnapshotsFromFiles(
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

export function parseStoryWorkspaceDreamEditorValue(
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
  if (!persistence?.confirmationAccepted) return fallback;
  return persistence.confirmationDispatched && runStatus === 'completed'
    ? 'story-workspace-dream-completed'
    : 'story-workspace-dream-continuing';
}

/** Copy has no rejected/failed/retry branch: acceptance is monotonic. */
export function storyWorkspaceDreamPersistenceNotice(
  persistence: StoryWorkspaceDreamConfirmationPersistence | null,
  lifecycle: 'continuing' | 'completed',
): string {
  if (persistence?.confirmationAccepted && !persistence.confirmationDispatched) {
    return '命令已保存，等待同一 Agent 接续';
  }
  if (lifecycle === 'completed') return '同一 Chat Agent 已完成后续执行';
  return '同一 Chat Agent 正在继续';
}
