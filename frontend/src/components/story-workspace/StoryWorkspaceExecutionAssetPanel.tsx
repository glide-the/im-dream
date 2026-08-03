// [Input] Authoritative run snapshot + optional execution projection.
// [Output] Read-only asset panel (design_004 §5.2 资产): episode-projection
//          asset references with deep links back to the Dream detail view.
// [Pos] Story Workspace execution page data-layer leaf (Task 5); hook-free
//       pure render so node-side tests can direct-call it.
// [Sync] 2026-08-04: initial implementation. No asset projection endpoint
//                    exists yet — the panel degrades to an explicit empty
//                    state with a Dream deep link (§5.1 PDF 取舍: no video
//                    preview/upload/player, no editable gallery).

import type { WorkflowRun } from '../../api/storyWorkspaceApi';
import type { StoryWorkspaceExecutionProjection } from '../../hooks/story-workspace/contracts';

export interface StoryWorkspaceExecutionAssetPanelProps {
  run: WorkflowRun;
  projection?: StoryWorkspaceExecutionProjection | null;
  /** Router navigation for the Dream deep link; falls back to a plain href. */
  onNavigate?: (href: string) => void;
  /** Dream entry route for the fallback deep link (surface entry_route). */
  dreamEntryRoute?: string;
}

/** 资产 tab — read-only references + Dream deep link (§5.2, DEC-008). */
export function StoryWorkspaceExecutionAssetPanel({
  run,
  projection,
  onNavigate,
  dreamEntryRoute = '/story-workspace/dream',
}: StoryWorkspaceExecutionAssetPanelProps) {
  const dreamHref = `${dreamEntryRoute}?run=${encodeURIComponent(run.workflow_run_id)}`;

  return (
    <section aria-label="资产" className="story-workspace-execution-assets">
      {projection?.assets_ref ? (
        <p className="story-workspace-execution-assets__ref">
          产物引用：<code>{projection.assets_ref}</code>
        </p>
      ) : (
        <div className="story-workspace-table-message">
          <p>暂无资产数据：角色 / 场景 / 分集产物投影尚未透出，产物以 Dream 详情为准。</p>
        </div>
      )}
      <a
        className="story-workspace-execution-assets__dream-link"
        href={dreamHref}
        onClick={onNavigate
          ? (event) => {
            event.preventDefault();
            onNavigate(dreamHref);
          }
          : undefined}
      >
        回 Dream 查看产物详情
      </a>
    </section>
  );
}
