// [Input] Authoritative Dream file projections after the single confirmation.
// [Output] Canonical-first Project title plus Assets / Outline collaboration indexes and focus navigation seams.
// [Pos] Story Workspace execution page pure view-model (Task 3 F5)

import type {
  StoryWorkspaceDreamFilesResponse,
  StoryWorkspaceDreamStage,
  StoryWorkspaceDreamStageItem,
} from '../../hooks/story-workspace/contracts';

const STAGE_COPY: Record<StoryWorkspaceDreamStage, {
  label: string;
  module: 'Assets' | 'Outline';
}> = {
  characters: { label: '人物', module: 'Assets' },
  scenes: { label: '场景', module: 'Assets' },
  storyboards: { label: '分镜', module: 'Outline' },
};

const STORY_WORKSPACE_CREATION_GOAL_PREFIX_MAX = 80;

/** Keep Project display naming consistent with the server-owned re-entry list. */
export function storyWorkspaceResolveDreamDisplayTitle(
  projectTitle: string | null | undefined,
  creationGoal: string | null | undefined,
): string {
  const canonical = projectTitle?.trim();
  if (canonical) return canonical;
  const fallback = creationGoal?.trim();
  return fallback
    ? fallback.slice(0, STORY_WORKSPACE_CREATION_GOAL_PREFIX_MAX)
    : '故事协作工作台';
}

export interface StoryWorkspaceExecutionEntry {
  readonly key: string;
  readonly stage: StoryWorkspaceDreamStage;
  readonly stageLabel: string;
  readonly module: 'Assets' | 'Outline';
  readonly entityId: string;
  readonly title: string;
  readonly summary: string | null;
  readonly relations: readonly string[];
  readonly sourceFile: string;
  readonly revision: number;
}

export interface StoryWorkspaceExecutionActivity {
  readonly key: string;
  readonly label: string;
  readonly sourceCount: number;
  readonly revision: number;
}

export interface StoryWorkspaceExecutionWorkspace {
  readonly assets: readonly StoryWorkspaceExecutionEntry[];
  readonly outline: readonly StoryWorkspaceExecutionEntry[];
  readonly activity: readonly StoryWorkspaceExecutionActivity[];
  readonly runRevision: number;
}

/** Access guard uses the persisted Dream command, never legacy run statuses. */
export function storyWorkspaceCanAccessExecution(
  files: StoryWorkspaceDreamFilesResponse,
): boolean {
  return files.confirmationAccepted;
}

function toEntry(
  stage: StoryWorkspaceDreamStage,
  revision: number,
  item: StoryWorkspaceDreamStageItem,
): StoryWorkspaceExecutionEntry {
  return {
    key: `${stage}:${item.entityId}`,
    stage,
    stageLabel: STAGE_COPY[stage].label,
    module: STAGE_COPY[stage].module,
    entityId: item.entityId,
    title: item.displayName,
    summary: item.summary,
    relations: [...item.relations],
    sourceFile: item.sourceFile,
    revision,
  };
}

/**
 * Build the collaboration surface from workspace files only. Run-state
 * branches and approval actions are intentionally absent from this model.
 */
export function storyWorkspaceBuildExecutionWorkspace(
  files: StoryWorkspaceDreamFilesResponse,
): StoryWorkspaceExecutionWorkspace {
  const assets: StoryWorkspaceExecutionEntry[] = [];
  const outline: StoryWorkspaceExecutionEntry[] = [];
  const activity: StoryWorkspaceExecutionActivity[] = [];

  for (const stage of ['characters', 'scenes', 'storyboards'] as const) {
    const projection = files.stages[stage];
    if (!projection) continue;
    const target = stage === 'storyboards' ? outline : assets;
    target.push(...projection.items.map((item) => toEntry(stage, projection.revision, item)));
    activity.push({
      key: `${stage}:r${projection.revision}`,
      label: `${STAGE_COPY[stage].label}文件已写入 r${projection.revision}`,
      sourceCount: projection.sourceFiles.length,
      revision: projection.revision,
    });
  }

  activity.sort((left, right) => right.revision - left.revision);
  return { assets, outline, activity, runRevision: files.runRevision };
}

export function storyWorkspaceExecutionFocusNeighbors(
  entries: readonly StoryWorkspaceExecutionEntry[],
  activeKey: string,
): { previousKey: string | null; nextKey: string | null } {
  const index = entries.findIndex((entry) => entry.key === activeKey);
  if (index < 0) return { previousKey: null, nextKey: null };
  return {
    previousKey: entries[index - 1]?.key ?? null,
    nextKey: entries[index + 1]?.key ?? null,
  };
}
