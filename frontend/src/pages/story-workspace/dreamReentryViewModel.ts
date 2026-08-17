// [Input] Server-ordered durable Dream re-entry rows and a user-entered query/page.
// [Output] Pure lifecycle/outcome copy, canonical-title search, and bounded pagination for Dream re-entry.
// [Pos] Story Workspace Dream re-entry presentation policy; it never recomputes server status or order.
// [Sync] 2026-08-14: align visible outcome copy with Dream's initial/in-progress phases.

import type { StoryWorkspaceDreamReentryItem } from '../../hooks/story-workspace';

const STORY_WORKSPACE_DREAM_REENTRY_PAGE_SIZE = 4;

const STORY_WORKSPACE_DREAM_REENTRY_COPY: Record<StoryWorkspaceDreamReentryItem['lifecycle'], string> = {
  generating: 'Dream Agent 正在创作',
  waiting_confirmation: '等待你修改并确认',
  running: 'Dream Agent 正在执行',
  recent: '最近完成本轮输出',
};

const STORY_WORKSPACE_DREAM_OUTCOME_COPY: Record<StoryWorkspaceDreamReentryItem['outcome'], string> = {
  initial: '初始状态',
  in_progress: '进行中',
};

export function storyWorkspaceDreamReentryLifecycleCopy(
  lifecycle: StoryWorkspaceDreamReentryItem['lifecycle'],
): string {
  return STORY_WORKSPACE_DREAM_REENTRY_COPY[lifecycle];
}

export function storyWorkspaceDreamReentryOutcomeCopy(
  outcome: StoryWorkspaceDreamReentryItem['outcome'],
): string {
  return STORY_WORKSPACE_DREAM_OUTCOME_COPY[outcome];
}

export function storyWorkspaceFilterDreamReentryRuns(
  runs: readonly StoryWorkspaceDreamReentryItem[],
  query: string,
): readonly StoryWorkspaceDreamReentryItem[] {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery) return runs;
  return runs.filter((run) => [
    run.displayTitle,
    run.goalPrefix,
    run.deckDisplayName,
    run.deckPluginVersion,
    run.storyWorkspaceRunId,
    storyWorkspaceDreamReentryLifecycleCopy(run.lifecycle),
    storyWorkspaceDreamReentryOutcomeCopy(run.outcome),
  ].some((value) => value.toLocaleLowerCase().includes(normalizedQuery)));
}

export function storyWorkspacePaginateDreamReentryRuns(
  runs: readonly StoryWorkspaceDreamReentryItem[],
  requestedPage: number,
): {
  items: readonly StoryWorkspaceDreamReentryItem[];
  page: number;
  totalPages: number;
} {
  const totalPages = Math.max(1, Math.ceil(runs.length / STORY_WORKSPACE_DREAM_REENTRY_PAGE_SIZE));
  const page = Math.min(Math.max(1, requestedPage), totalPages);
  const start = (page - 1) * STORY_WORKSPACE_DREAM_REENTRY_PAGE_SIZE;
  return {
    items: runs.slice(start, start + STORY_WORKSPACE_DREAM_REENTRY_PAGE_SIZE),
    page,
    totalPages,
  };
}
