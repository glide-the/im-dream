// [Input] Server-aggregated surface link state + workspace surfaces (Task 2).
// [Output] Pure Dream lifecycle jump links and deep-link builders.
// [Pos] Story Workspace dream-surface link seams (Task 4); the component in
//       StoryWorkspaceSurfaceLinkButton.tsx is a thin JSX wrapper over these.
// [Sync] 2026-08-04: design_007 revision exposes only edit/continue/content
//                    lifecycle links; legacy aggregate branches stay hidden.

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
  /**
   * In-app router navigation (Task 5 Step 0): when provided, link clicks are
   * intercepted and routed without a full-page load; when absent the plain
   * href keeps its progressive-enhancement navigation (Task 4 review
   * leftover).
   */
  onNavigate?: (href: string) => void;
}

/**
 * Displayable stage → target mapping. The wider aggregate contract remains
 * accepted at the boundary, but only design_007 lifecycle bridge stages have
 * labels and therefore enter Dream UI.
 */
export const STORY_WORKSPACE_SURFACE_LINK_LABELS: Partial<Record<
  StoryWorkspaceSurfaceLinkStage,
  { label: string; target: 'review' | 'execution' }
>> = {
  pending_review: { label: '打开 Dream 修改', target: 'review' },
  confirmed: { label: '进入后续执行', target: 'execution' },
  running: { label: '查看执行内容', target: 'execution' },
  completed: { label: '查看最新内容', target: 'execution' },
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
 * present, runId bound, aggregated state available and its stage belongs to
 * the four displayable design_007 lifecycle bridges. Replaced attempts and
 * legacy aggregate branches remain hidden instead of creating a parallel UI.
 */
export function storyWorkspaceResolveSurfaceLink(
  props: StoryWorkspaceSurfaceLinkButtonProps,
): StoryWorkspaceSurfaceLinkModel | undefined {
  const dreamSurface = props.surfaces?.find((surface) => surface.name === 'dream');
  const { runId, episodeId, state } = props;
  if (!dreamSurface || !runId || !state) return undefined;

  if (state.superseded) return undefined;

  const spec = STORY_WORKSPACE_SURFACE_LINK_LABELS[state.stage];
  if (!spec) return undefined;
  const href = spec.target === 'execution'
    ? storyWorkspaceExecutionDeepLink(runId)
    : storyWorkspaceReviewDeepLink(runId, episodeId, dreamSurface.entry_route);
  return { primary: { label: spec.label, href } };
}
