import type { StoryWorkspaceReviewStatus } from '../../../hooks/story-workspace';

const REVIEW_STATUS_LABELS: Record<StoryWorkspaceReviewStatus, string> = {
  pending: '待审阅',
  confirmed: '已确认',
  rejected: '已驳回',
  archived: '已归档',
};

export interface StoryWorkspaceReviewStatusBadgeProps {
  status: StoryWorkspaceReviewStatus;
}

export function StoryWorkspaceReviewStatusBadge({
  status,
}: StoryWorkspaceReviewStatusBadgeProps) {
  return (
    <span className={`story-workspace-review-badge story-workspace-review-badge--${status}`}>
      {REVIEW_STATUS_LABELS[status]}
    </span>
  );
}
