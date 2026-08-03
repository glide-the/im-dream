// [Input] Server-aggregated surface link props (see surfaceLink.ts).
// [Output] Dream surface jump link(s) for the review-panel detail area and the
//          story list row action column (design_004 §4).
// [Pos] Story Workspace dream-surface jump link component (Task 4)
// [Sync] 2026-08-04: initial implementation; thin JSX wrapper over the pure
//                    seams in surfaceLink.ts — all state is server-aggregated
//                    props, the frontend never infers stage.

import {
  resolveStoryWorkspaceSurfaceLink,
  type StoryWorkspaceSurfaceLinkButtonProps,
} from './surfaceLink';

export type { StoryWorkspaceSurfaceLinkButtonProps } from './surfaceLink';

/**
 * Dream surface jump link. Mounted in the review panel detail area and the
 * story list row action column; renders nothing unless the server-aggregated
 * props satisfy every visibility condition (§4.1/§4.4).
 */
export function StoryWorkspaceSurfaceLinkButton(props: StoryWorkspaceSurfaceLinkButtonProps) {
  const model = resolveStoryWorkspaceSurfaceLink(props);
  if (!model) return null;

  return (
    <nav aria-label="Dream 跳转" className="story-workspace-surface-link">
      <a className="story-workspace-surface-link__primary" href={model.primary.href}>
        {model.primary.label}
      </a>
      {model.secondary && (
        <a className="story-workspace-surface-link__secondary" href={model.secondary.href}>
          {model.secondary.label}
        </a>
      )}
    </nav>
  );
}
