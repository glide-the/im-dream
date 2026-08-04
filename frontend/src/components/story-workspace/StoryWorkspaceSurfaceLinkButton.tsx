// [Input] Server-aggregated surface link props (see surfaceLink.ts).
// [Output] Dream surface jump link(s) for the review-panel detail area and the
//          story list row action column (design_004 §4).
// [Pos] Story Workspace dream-surface jump link component (Task 4; Task 5
//       Step 0 added router-navigation interception)
// [Sync] 2026-08-04: Task 5 — when onNavigate is provided, clicks route
//                    in-app (no full-page load); without it the plain href
//                    keeps its Task 4 progressive-enhancement behavior.

import {
  storyWorkspaceResolveSurfaceLink,
  type StoryWorkspaceSurfaceLinkButtonProps,
  type StoryWorkspaceSurfaceLinkTarget,
} from './surfaceLink';

export type { StoryWorkspaceSurfaceLinkButtonProps } from './surfaceLink';

function linkClickHandler(
  target: StoryWorkspaceSurfaceLinkTarget,
  onNavigate: StoryWorkspaceSurfaceLinkButtonProps['onNavigate'],
) {
  if (!onNavigate) return undefined;
  return (event: React.MouseEvent<HTMLAnchorElement>) => {
    // Modified clicks (new tab/window) keep native href semantics.
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onNavigate(target.href);
  };
}

/**
 * Dream surface jump link. Mounted in the review panel detail area and the
 * story list row action column; renders nothing unless the server-aggregated
 * props satisfy every visibility condition (§4.1/§4.4).
 */
export function StoryWorkspaceSurfaceLinkButton(props: StoryWorkspaceSurfaceLinkButtonProps) {
  const model = storyWorkspaceResolveSurfaceLink(props);
  if (!model) return null;

  return (
    <nav aria-label="Dream 跳转" className="story-workspace-surface-link">
      <a
        className="story-workspace-surface-link__primary"
        href={model.primary.href}
        onClick={linkClickHandler(model.primary, props.onNavigate)}
      >
        {model.primary.label}
      </a>
      {model.secondary && (
        <a
          className="story-workspace-surface-link__secondary"
          href={model.secondary.href}
          onClick={linkClickHandler(model.secondary, props.onNavigate)}
        >
          {model.secondary.label}
        </a>
      )}
    </nav>
  );
}
