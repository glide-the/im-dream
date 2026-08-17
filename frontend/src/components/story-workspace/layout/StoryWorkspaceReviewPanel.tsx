// [Input] Review content, visibility state, and close callback from the workspace layout.
// [Output] Render the fixed-width review container without review business behavior.
// [Pos] Story Workspace right-side layout region.
import type { ReactNode } from 'react';
import { ProvenanceBadge, type ProvenanceBadgeProps } from '../workflow/ProvenanceBadge';
import './StoryWorkspaceLayout.css';

export interface StoryWorkspaceReviewPanelProps {
  children?: ReactNode;
  open: boolean;
  onClose: () => void;
  provenance?: ProvenanceBadgeProps | null;
  title?: string;
}

export function StoryWorkspaceReviewPanel({
  children,
  open,
  onClose,
  provenance,
  title = '审阅详情',
}: StoryWorkspaceReviewPanelProps) {
  if (!open) {
    return null;
  }

  return (
    <aside
      aria-label={title}
      className="story-workspace-review-panel"
      data-story-workspace-region="review-panel"
    >
      <header className="story-workspace-review-panel__header">
        <h2 className="story-workspace-review-panel__title">{title}</h2>
        <button
          aria-label="关闭审阅面板"
          className="story-workspace-review-panel__close"
          onClick={onClose}
          type="button"
        >
          <span aria-hidden="true">×</span>
        </button>
      </header>
      <div className="story-workspace-review-panel__body">
        {provenance && (
          <div className="story-workspace-review-panel__provenance">
            <ProvenanceBadge {...provenance} />
          </div>
        )}
        {children}
      </div>
    </aside>
  );
}
