// [Input] Story Workspace region content and optional controlled review-panel state.
// [Output] Render the desktop-only 240px / fluid / 360px workspace skeleton.
// [Pos] Story Workspace root layout container.
import { useCallback, useState, type ReactNode } from 'react';
import { StoryWorkspaceReviewPanel } from './StoryWorkspaceReviewPanel';
import {
  WorkflowContextBar,
  type ProvenanceBadgeProps,
  type WorkflowContextBarProps,
} from '../workflow';
import './StoryWorkspaceLayout.css';

export interface StoryWorkspaceLayoutProps {
  children: ReactNode;
  sidebar: ReactNode;
  reviewPanel?: ReactNode;
  reviewPanelOpen?: boolean;
  defaultReviewPanelOpen?: boolean;
  onReviewPanelOpenChange?: (open: boolean) => void;
  reviewPanelTitle?: string;
  reviewProvenance?: ProvenanceBadgeProps | null;
  workflowContext?: WorkflowContextBarProps | null;
}

export function StoryWorkspaceLayout({
  children,
  sidebar,
  reviewPanel,
  reviewPanelOpen,
  defaultReviewPanelOpen = true,
  onReviewPanelOpenChange,
  reviewPanelTitle,
  reviewProvenance,
  workflowContext,
}: StoryWorkspaceLayoutProps) {
  const [uncontrolledReviewPanelOpen, setUncontrolledReviewPanelOpen] = useState(
    defaultReviewPanelOpen,
  );
  const isReviewPanelControlled = reviewPanelOpen !== undefined;
  const hasReviewPanel = reviewPanel !== undefined && reviewPanel !== null;
  const isReviewPanelOpen = hasReviewPanel
    && (isReviewPanelControlled ? reviewPanelOpen : uncontrolledReviewPanelOpen);

  const setReviewPanelOpen = useCallback((open: boolean) => {
    if (!isReviewPanelControlled) {
      setUncontrolledReviewPanelOpen(open);
    }
    onReviewPanelOpenChange?.(open);
  }, [isReviewPanelControlled, onReviewPanelOpenChange]);

  return (
    <div
      className="story-workspace-layout"
      data-review-panel-state={isReviewPanelOpen ? 'open' : 'closed'}
    >
      <aside
        aria-label="Story Workspace sidebar"
        className="story-workspace-layout__sidebar"
        data-story-workspace-region="sidebar"
      >
        {sidebar}
      </aside>

      <main
        className="story-workspace-layout__main"
        data-story-workspace-region="main"
      >
        {workflowContext && (
          <div className="story-workspace-layout__workflow-context">
            <WorkflowContextBar {...workflowContext} />
          </div>
        )}
        {children}
      </main>

      <StoryWorkspaceReviewPanel
        open={isReviewPanelOpen}
        onClose={() => setReviewPanelOpen(false)}
        provenance={reviewProvenance}
        title={reviewPanelTitle}
      >
        {reviewPanel}
      </StoryWorkspaceReviewPanel>
    </div>
  );
}
