// [Input] Server-aggregated surface link state + workspace surfaces (Task 2).
// [Output] Pure resolution seams for the Dream surface jump link: label table,
//          deep-link builders, visibility/supersede resolution (design_004 §4).
// [Pos] Story Workspace dream-surface link seams (Task 4); the component in
//       StoryWorkspaceSurfaceLinkButton.tsx is a thin JSX wrapper over these.
// [Sync] 2026-08-04: initial implementation. Six-stage labels come from
//                    server-aggregated props only — the frontend never infers
//                    stage; missing aggregation keeps the link hidden.

import type {
  StoryWorkspaceSurface,
  StoryWorkspaceSurfaceLinkStage,
  StoryWorkspaceSurfaceLinkState,
} from '../../hooks/story-workspace/contracts';

export interface StoryWorkspaceSurfaceLinkTarget {
  label: string;
  href: string;
}

export interface StoryWorkspaceSurfaceLinkModel {
  primary: StoryWorkspaceSurfaceLinkTarget;
  secondary?: StoryWorkspaceSurfaceLinkTarget;
}

export interface StoryWorkspaceSurfaceLinkButtonProps {
  /** Session surfaces from useWorkspaceSurfaces; undefined = no surface (hidden). */
  surfaces: StoryWorkspaceSurface[] | undefined;
  /** storyWorkspaceRunId bound to the reviewed resource; missing = hidden (§4.1-2). */
  runId: string | null | undefined;
  /** Optional episode binding for the review deep link (§4.2). */
  episodeId?: string | null;
  /** Server-aggregated stage/supersede state; missing = hidden, never inferred. */
  state: StoryWorkspaceSurfaceLinkState | null | undefined;
}

/**
 * Stage → label/target mapping, verbatim from design_004 §4.2. `review`
 * targets the review deep link, `execution` the execution page deep link.
 */
export const SURFACE_LINK_LABELS: Record<
  StoryWorkspaceSurfaceLinkStage,
  { label: string; target: 'review' | 'execution' }
> = {
  pending_review: { label: '前往 Dream 审阅', target: 'review' },
  confirmed: { label: '进入后续执行', target: 'execution' },
  continuing: { label: '查看执行进度', target: 'execution' },
  completed: { label: '查看执行结果', target: 'execution' },
  failed: { label: '查看失败详情', target: 'execution' },
  rejected: { label: '查看审阅记录', target: 'review' },
};

/**
 * Review deep link (§4.2): episode-scoped when episodeId is bound, otherwise
 * degrades to the Dream home page carrying `?run=` (§4.4).
 */
export function storyWorkspaceReviewDeepLink(
  runId: string,
  episodeId?: string | null,
  entryRoute = '/story-workspace/dream',
): string {
  const encodedRunId = encodeURIComponent(runId);
  if (episodeId) {
    return `/story-workspace/episodes/${encodeURIComponent(episodeId)}/review?run=${encodedRunId}`;
  }
  return `${entryRoute}?run=${encodedRunId}`;
}

/** Execution page deep link (§4.2). */
export function storyWorkspaceExecutionDeepLink(runId: string): string {
  return `/story-workspace/runs/${encodeURIComponent(runId)}/execution`;
}

/**
 * Resolve the link model from server-aggregated props. Returns undefined
 * (hidden) unless every §4.1 visibility condition holds: dream surface
 * present, runId bound, aggregated state available. Superseded proposals
 * degrade to 查看最新版本 (latest run review deep link) with a 查看运行记录
 * companion link for the stale run (§4.1/§4.4).
 */
export function resolveStoryWorkspaceSurfaceLink(
  props: StoryWorkspaceSurfaceLinkButtonProps,
): StoryWorkspaceSurfaceLinkModel | undefined {
  const dreamSurface = props.surfaces?.find((surface) => surface.name === 'dream');
  const { runId, episodeId, state } = props;
  if (!dreamSurface || !runId || !state) return undefined;

  if (state.superseded) {
    const runRecords: StoryWorkspaceSurfaceLinkTarget = {
      label: '查看运行记录',
      href: storyWorkspaceExecutionDeepLink(runId),
    };
    if (state.latestRunId && state.latestRunId !== runId) {
      return {
        primary: {
          label: '查看最新版本',
          href: storyWorkspaceReviewDeepLink(
            state.latestRunId,
            episodeId,
            dreamSurface.entry_route,
          ),
        },
        secondary: runRecords,
      };
    }
    return { primary: runRecords };
  }

  const spec = SURFACE_LINK_LABELS[state.stage];
  const href = spec.target === 'execution'
    ? storyWorkspaceExecutionDeepLink(runId)
    : storyWorkspaceReviewDeepLink(runId, episodeId, dreamSurface.entry_route);
  return { primary: { label: spec.label, href } };
}
