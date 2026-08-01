import type { MouseEvent, ReactNode } from 'react';
import type { StoryWorkspaceReviewStatus } from '../../../hooks/story-workspace';

export interface StoryWorkspaceTableRowProps {
  children: ReactNode;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  onSelect?: () => void;
  reviewStatus: StoryWorkspaceReviewStatus;
  selected?: boolean;
}

export function StoryWorkspaceTableRow({
  children,
  checked,
  onCheckedChange,
  onSelect,
  reviewStatus,
  selected = checked,
}: StoryWorkspaceTableRowProps) {
  const isPending = reviewStatus === 'pending';

  const handleCheckboxClick = (event: MouseEvent<HTMLInputElement>) => {
    event.stopPropagation();
  };

  return (
    <tr
      className={[
        'story-workspace-table-row',
        `story-workspace-table-row--${reviewStatus}`,
        selected ? 'story-workspace-table-row--selected' : '',
      ].filter(Boolean).join(' ')}
      aria-selected={selected}
      onClick={onSelect}
    >
      <td>
        <input
          aria-label={isPending ? '选择待审阅项目' : '仅待审阅项目可批量选择'}
          checked={checked}
          disabled={!isPending}
          onChange={(event) => onCheckedChange(event.target.checked)}
          onClick={handleCheckboxClick}
          type="checkbox"
        />
      </td>
      {children}
    </tr>
  );
}
