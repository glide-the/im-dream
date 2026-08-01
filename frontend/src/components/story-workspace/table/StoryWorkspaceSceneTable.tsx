import type {
  StoryWorkspaceScene,
  StoryWorkspaceSortOrder,
} from '../../../hooks/story-workspace';
import { StoryWorkspaceReviewStatusBadge } from './StoryWorkspaceReviewStatusBadge';
import { StoryWorkspaceSortButton } from './StoryWorkspaceSortButton';
import { StoryWorkspaceTableRow } from './StoryWorkspaceTableRow';
import {
  pendingSelectionHandler,
  togglePendingSelection,
} from './tableHelpers';

export interface StoryWorkspaceSceneTableProps {
  items: StoryWorkspaceScene[];
  selectedIds: string[];
  sort: string;
  order: StoryWorkspaceSortOrder;
  onReview?: (scene: StoryWorkspaceScene) => void;
  onSelectionChange: (ids: string[]) => void;
  onSortChange: (sort: string, order: StoryWorkspaceSortOrder) => void;
}

export function StoryWorkspaceSceneTable({
  items,
  selectedIds,
  sort,
  order,
  onReview,
  onSelectionChange,
  onSortChange,
}: StoryWorkspaceSceneTableProps) {
  const pendingIds = items.filter((item) => item.review_status === 'pending').map((item) => item.id);
  const allPendingSelected = pendingIds.length > 0
    && pendingIds.every((id) => selectedIds.includes(id));

  return (
    <div className="story-workspace-table-shell">
      <table className="story-workspace-table">
        <thead>
          <tr>
            <th>
              <input
                aria-label="选择本页全部待审阅场景"
                checked={allPendingSelected}
                disabled={pendingIds.length === 0}
                onChange={pendingSelectionHandler(pendingIds, selectedIds, onSelectionChange)}
                type="checkbox"
              />
            </th>
            <th style={{ width: '20%' }}>
              <StoryWorkspaceSortButton
                activeSort={sort}
                field="name"
                label="名称"
                onSortChange={onSortChange}
                order={order}
              />
            </th>
            <th style={{ width: '30%' }}>描述</th>
            <th style={{ width: '18%' }}>关联故事</th>
            <th style={{ width: 90 }}>关联角色</th>
            <th style={{ width: 104 }}>审阅状态</th>
            <th style={{ width: 76 }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {items.map((scene) => (
            <StoryWorkspaceTableRow
              checked={selectedIds.includes(scene.id)}
              key={scene.id}
              onCheckedChange={(checked) => onSelectionChange(
                togglePendingSelection(selectedIds, scene.id, checked),
              )}
              reviewStatus={scene.review_status}
            >
              <td>
                <div className="story-workspace-table__primary" title={scene.name}>{scene.name}</div>
              </td>
              <td>
                <div className="story-workspace-table__description" title={scene.description ?? ''}>
                  {scene.description || '—'}
                </div>
              </td>
              <td>
                <div className="story-workspace-table__description" title={scene.story_id ?? ''}>
                  {scene.story_id || '—'}
                </div>
              </td>
              <td>{scene.character_count}</td>
              <td><StoryWorkspaceReviewStatusBadge status={scene.review_status} /></td>
              <td>
                <button
                  className="story-workspace-table__action"
                  onClick={() => onReview?.(scene)}
                  type="button"
                >
                  审阅
                </button>
              </td>
            </StoryWorkspaceTableRow>
          ))}
        </tbody>
      </table>
    </div>
  );
}
