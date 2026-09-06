// [Input] Authoritative Dream file projections after the single confirmation.
// [Output] Canonical-first Project title plus Assets / Outline indexes, compact summaries, complete focus documents, and navigation seams.
// [Pos] Story Workspace execution page pure view-model (Task 3 F5)
// [Sync] 2026-08-14: preserve Hook-published full asset content for the focus reader.
// [Sync] 2026-08-14: remove the revision-derived workspace update feed; the
//                    Execution surface presents current artifacts only.
// [Sync] 2026-08-31: resolve the canonical Episode reader host from the
//                    matching storyboard entry in the Dream draft.
// [Sync] 2026-09-02: use the Episode identity, not a storyboard label, as its container title.

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
  readonly content: string | null;
  readonly relations: readonly string[];
  readonly sourceFile: string;
  readonly revision: number;
}

export interface StoryWorkspaceExecutionWorkspace {
  readonly assets: readonly StoryWorkspaceExecutionEntry[];
  readonly outline: readonly StoryWorkspaceExecutionEntry[];
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
    title: stage === 'storyboards' && /^EP[0-9]{2}$/.test(item.entityId)
      ? item.entityId
      : item.displayName,
    summary: item.summary,
    content: item.content ?? null,
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

  for (const stage of ['characters', 'scenes', 'storyboards'] as const) {
    const projection = files.stages[stage];
    if (!projection) continue;
    const target = stage === 'storyboards' ? outline : assets;
    target.push(...projection.items.map((item) => toEntry(stage, projection.revision, item)));
  }

  return { assets, outline };
}

/** Match a published Episode projection to its Dream storyboard entry. */
export function storyWorkspaceExecutionEpisodeEntry(
  entries: readonly StoryWorkspaceExecutionEntry[],
  episodeCode: string | null | undefined,
): StoryWorkspaceExecutionEntry | null {
  const canonicalEpisodeCode = episodeCode?.trim();
  if (!canonicalEpisodeCode) return null;
  return entries.find((entry) => (
    entry.stage === 'storyboards'
    && (
      entry.entityId === canonicalEpisodeCode
      || entry.relations.includes(canonicalEpisodeCode)
    )
  )) ?? null;
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
