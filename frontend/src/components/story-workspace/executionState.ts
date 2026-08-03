// [Input] Authoritative run snapshots + the optional execution projection.
// [Output] Pure resolution seams for the standalone execution page (Task 5,
//          design_004 §5): the five-state UI resolution (§5.4), the Gate
//          redirect target (§5.5), guidable-status gating (Task 3 contract),
//          and the plan-required state copy.
// [Pos] Story Workspace execution page seams (Task 5); the routed page and
//       sidebar components consume these — presentation decisions never live
//       in JSX.
// [Sync] 2026-08-04: initial implementation. awaiting-guidance is a
//                    projection state inferred from continuing + projection
//                    markers (audit note D13), never a RunStatus. Without a
//                    projection endpoint the page degrades to plain
//                    continuing (see the Task 5 implementation record).

import type { WorkflowRun, WorkflowRunStatus } from '../../api/storyWorkspaceApi';
import type {
  StoryWorkspaceExecutionPageState,
  StoryWorkspaceExecutionProjection,
} from '../../hooks/story-workspace/contracts';
import { storyWorkspaceReviewDeepLink } from './surfaceLink';

/** Run statuses the execution page serves (Gate step 4 passed, §5.5). */
const EXECUTION_PAGE_STATUSES: ReadonlySet<WorkflowRunStatus> = new Set([
  'confirmed',
  'continuing',
  'completed',
  'failed',
  'cancelled',
]);

/**
 * Resolve the execution page UI state (§5.4). Runs before Gate step 4 (plus
 * rejected) resolve to `not-confirmed`, whose only action is the review deep
 * link redirect (§5.5). `confirmed` renders the progress view (execution has
 * not started continuing yet). `awaiting-guidance` is inferred from
 * `continuing` + projection markers (phase flag or a blocked step) — D13.
 */
export function resolveStoryWorkspaceExecutionState(
  run: Pick<WorkflowRun, 'status'>,
  projection: StoryWorkspaceExecutionProjection | null | undefined,
): StoryWorkspaceExecutionPageState {
  if (!EXECUTION_PAGE_STATUSES.has(run.status)) return 'not-confirmed';
  if (run.status === 'completed') return 'completed';
  if (run.status === 'failed') return 'failed';
  if (run.status === 'cancelled') return 'cancelled';

  const awaiting = projection !== null
    && projection !== undefined
    && (
      projection.phase === 'awaiting-guidance'
      || projection.steps.some((step) => step.blocked === true || step.status === 'blocked')
    );
  return awaiting ? 'awaiting-guidance' : 'continuing';
}

/**
 * Gate redirect target (§5.5): the review deep link carrying the run. Episode
 * binding is not available from the run read, so it degrades to the Dream
 * entry route with `?run=` (§4.4 degradation, same builder as Task 4).
 */
export function resolveStoryWorkspaceExecutionRedirect(
  runId: string,
  episodeId?: string | null,
): string {
  return storyWorkspaceReviewDeepLink(runId, episodeId);
}

/** Guidable statuses mirror the Task 3 endpoint contract {continuing, failed}. */
export function isStoryWorkspaceGuidableStatus(status: WorkflowRunStatus): boolean {
  return status === 'continuing' || status === 'failed';
}

export type StoryWorkspaceExecutionPageView = 'loading' | 'error' | 'ready';

/**
 * Page-level branch resolution (F-1 fix, 2026-08-04): the loading branch is
 * first-paint only. A background refresh (e.g. the guidance sidebar's
 * onSubmitted → loadRun) keeps the already-loaded run mounted, so the
 * sidebar's just-set submit feedback actually paints instead of being
 * discarded by an unmount/remount cycle.
 */
export function resolveStoryWorkspaceExecutionPageView({
  isLoading,
  loadError,
  run,
}: {
  isLoading: boolean;
  loadError: string | null;
  run: WorkflowRun | null;
}): StoryWorkspaceExecutionPageView {
  if (run === null) {
    if (isLoading) return 'loading';
    return 'error';
  }
  if (loadError !== null) return 'error';
  return 'ready';
}

export interface StoryWorkspaceExecutionStateCopy {
  /** Short status badge next to the breadcrumb. */
  badge: string;
  /** Primary banner / empty-state line for the state. */
  banner: string;
}

/** Five-state copy (§5.4) with the plan-required texts. */
export const STORY_WORKSPACE_EXECUTION_STATE_COPY: Record<
  StoryWorkspaceExecutionPageState,
  StoryWorkspaceExecutionStateCopy
> = {
  continuing: {
    badge: '执行中',
    banner: '任务进度随执行实时更新，可随时在右侧提交指导。',
  },
  'awaiting-guidance': {
    badge: '等待指导',
    banner: '等待你的指导：Agent 已在阻塞步骤暂停，请在右侧提交指导后继续。',
  },
  completed: {
    badge: '已完成',
    banner: '执行完成，产物可回 Dream 查看。',
  },
  failed: {
    badge: '执行失败',
    banner: '执行失败，可在右侧重试失败步骤或回 Dream 再次生成。',
  },
  cancelled: {
    badge: '已取消',
    banner: '该运行已取消，确认事实保留，可回 Dream 重新发起。',
  },
  'not-confirmed': {
    badge: '未确认',
    banner: '该运行尚未通过审阅确认，请先完成审阅确认。正在跳转审阅…',
  },
};
