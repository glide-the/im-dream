import type { StoryWorkspaceSortOrder } from '../../../hooks/story-workspace';

export interface StoryWorkspaceSortButtonProps {
  activeSort: string;
  field: string;
  label: string;
  order: StoryWorkspaceSortOrder;
  onSortChange: (sort: string, order: StoryWorkspaceSortOrder) => void;
}

export function StoryWorkspaceSortButton({
  activeSort,
  field,
  label,
  order,
  onSortChange,
}: StoryWorkspaceSortButtonProps) {
  const active = activeSort === field;
  const indicator = active ? (order === 'asc' ? '↑' : '↓') : '↕';

  return (
    <button
      aria-label={`${label}排序${active ? `，当前${order === 'asc' ? '升序' : '降序'}` : ''}`}
      className="story-workspace-table__sort"
      onClick={() => onSortChange(field, active && order === 'asc' ? 'desc' : 'asc')}
      type="button"
    >
      {label}<span aria-hidden="true">{indicator}</span>
    </button>
  );
}
