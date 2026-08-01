import type {
  StoryWorkspaceCharacter,
  StoryWorkspaceSortOrder,
} from '../../../hooks/story-workspace';
import { StoryWorkspaceReviewStatusBadge } from './StoryWorkspaceReviewStatusBadge';
import { StoryWorkspaceSortButton } from './StoryWorkspaceSortButton';
import { StoryWorkspaceTableRow } from './StoryWorkspaceTableRow';
import {
  pendingSelectionHandler,
  togglePendingSelection,
} from './tableHelpers';

export interface StoryWorkspaceCharacterTableProps {
  items: StoryWorkspaceCharacter[];
  selectedIds: string[];
  sort: string;
  order: StoryWorkspaceSortOrder;
  onReview?: (character: StoryWorkspaceCharacter) => void;
  onSelectionChange: (ids: string[]) => void;
  onSortChange: (sort: string, order: StoryWorkspaceSortOrder) => void;
}

export function StoryWorkspaceCharacterTable({
  items,
  selectedIds,
  sort,
  order,
  onReview,
  onSelectionChange,
  onSortChange,
}: StoryWorkspaceCharacterTableProps) {
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
                aria-label="选择本页全部待审阅角色"
                checked={allPendingSelected}
                disabled={pendingIds.length === 0}
                onChange={pendingSelectionHandler(pendingIds, selectedIds, onSelectionChange)}
                type="checkbox"
              />
            </th>
            <th style={{ width: 58 }}>头像</th>
            <th style={{ width: '18%' }}>
              <StoryWorkspaceSortButton
                activeSort={sort}
                field="name"
                label="名称"
                onSortChange={onSortChange}
                order={order}
              />
            </th>
            <th style={{ width: '18%' }}>身份</th>
            <th style={{ width: '23%' }}>性格标签</th>
            <th style={{ width: 90 }}>关联故事</th>
            <th style={{ width: 104 }}>审阅状态</th>
            <th style={{ width: 76 }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {items.map((character) => (
            <StoryWorkspaceTableRow
              checked={selectedIds.includes(character.id)}
              key={character.id}
              onCheckedChange={(checked) => onSelectionChange(
                togglePendingSelection(selectedIds, character.id, checked),
              )}
              reviewStatus={character.review_status}
            >
              <td>
                <span className="story-workspace-character-avatar">
                  {character.avatar_url ? (
                    <img alt="" src={character.avatar_url} />
                  ) : character.name.slice(0, 1)}
                </span>
              </td>
              <td>
                <div className="story-workspace-table__primary" title={character.name}>{character.name}</div>
              </td>
              <td>
                <div className="story-workspace-table__description" title={character.identity ?? ''}>
                  {character.identity || '—'}
                </div>
              </td>
              <td>
                <div className="story-workspace-tags">
                  {character.tags.length > 0
                    ? character.tags.slice(0, 3).map((tag) => (
                      <span className="story-workspace-tag" key={tag} title={tag}>{tag}</span>
                    ))
                    : <span className="story-workspace-table__secondary">—</span>}
                </div>
              </td>
              <td>{character.story_count}</td>
              <td><StoryWorkspaceReviewStatusBadge status={character.review_status} /></td>
              <td>
                <button
                  className="story-workspace-table__action"
                  onClick={() => onReview?.(character)}
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
