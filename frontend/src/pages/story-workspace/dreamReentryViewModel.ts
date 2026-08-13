// [Input] Server-ordered durable Dream re-entry rows and a user-entered query/page.
// [Output] Pure lifecycle copy, filtering, and bounded pagination projections for the Dream launch page.
// [Pos] Story Workspace Dream re-entry presentation policy; it never recomputes server status or order.
// [Sync] 2026-08-13: extract searchable, per-group client pagination from the React surface.

import type { StoryWorkspaceDreamReentryItem } from '../../hooks/story-workspace';

const STORY_WORKSPACE_DREAM_REENTRY_PAGE_SIZE = 4;

const STORY_WORKSPACE_DREAM_REENTRY_COPY: Record<StoryWorkspaceDreamReentryItem['lifecycle'], string> = {
  generating: 'Dream Agent 正在创作',
  waiting_confirmation: '等待你修改并确认',
  running: 'Dream Agent 正在执行',
  recent: '最近完成本轮输出',
};

export function storyWorkspaceDreamReentryLifecycleCopy(
  lifecycle: StoryWorkspaceDreamReentryItem['lifecycle'],
): string {
  return STORY_WORKSPACE_DREAM_REENTRY_COPY[lifecycle];
}

export function storyWorkspaceFilterDreamReentryRuns(
  runs: readonly StoryWorkspaceDreamReentryItem[],
  query: string,
): readonly StoryWorkspaceDreamReentryItem[] {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery) return runs;
  return runs.filter((run) => [
    run.goalPrefix,
    run.deckDisplayName,
    run.deckPluginVersion,
    run.storyWorkspaceRunId,
    storyWorkspaceDreamReentryLifecycleCopy(run.lifecycle),
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
