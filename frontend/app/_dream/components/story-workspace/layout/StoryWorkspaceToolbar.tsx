import type {
  StoryWorkspaceReviewStatus,
  StoryWorkspaceSortOrder,
  StoryWorkspaceStoryType,
} from '../../../hooks/story-workspace';
import '../table/StoryWorkspaceTable.css';

const REVIEW_STATUS_OPTIONS: Array<{ label: string; value: StoryWorkspaceReviewStatus }> = [
  { label: '待审阅', value: 'pending' },
  { label: '已确认', value: 'confirmed' },
  { label: '已驳回', value: 'rejected' },
  { label: '已归档', value: 'archived' },
];

const STORY_TYPE_OPTIONS: Array<{ label: string; value: StoryWorkspaceStoryType }> = [
  { label: '短剧', value: 'short' },
  { label: '长篇', value: 'long' },
  { label: '剧本', value: 'script' },
  { label: '大纲', value: 'outline' },
];

export interface StoryWorkspaceSortOption {
  label: string;
  order: StoryWorkspaceSortOrder;
  sort: string;
}

export interface StoryWorkspaceToolbarProps {
  order: StoryWorkspaceSortOrder;
  query: string;
  reviewStatuses: StoryWorkspaceReviewStatus[];
  sort: string;
  sortOptions: StoryWorkspaceSortOption[];
  storyTypes?: StoryWorkspaceStoryType[];
  onOrderAndSortChange: (sort: string, order: StoryWorkspaceSortOrder) => void;
  onQueryChange: (query: string) => void;
  onReviewStatusesChange: (statuses: StoryWorkspaceReviewStatus[]) => void;
  onStoryTypesChange?: (types: StoryWorkspaceStoryType[]) => void;
}

function toggleValue<T extends string>(values: T[], value: T, checked: boolean): T[] {
  if (checked) return values.includes(value) ? values : [...values, value];
  return values.filter((candidate) => candidate !== value);
}

export function StoryWorkspaceToolbar({
  order,
  query,
  reviewStatuses,
  sort,
  sortOptions,
  storyTypes = [],
  onOrderAndSortChange,
  onQueryChange,
  onReviewStatusesChange,
  onStoryTypesChange,
}: StoryWorkspaceToolbarProps) {
  const filterCount = reviewStatuses.length + storyTypes.length;

  return (
    <div className="story-workspace-toolbar" role="search">
      <input
        aria-label="搜索 Story Workspace 内容"
        className="story-workspace-toolbar__search"
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="搜索 Agent 产出…"
        type="search"
        value={query}
      />

      <details className="story-workspace-toolbar__filters">
        <summary>筛选{filterCount > 0 ? `（${filterCount}）` : ''}</summary>
        <div className="story-workspace-toolbar__filter-panel">
          <span className="story-workspace-toolbar__filter-label">审阅状态</span>
          {REVIEW_STATUS_OPTIONS.map((option) => (
            <label className="story-workspace-toolbar__filter-option" key={option.value}>
              <input
                checked={reviewStatuses.includes(option.value)}
                onChange={(event) => onReviewStatusesChange(
                  toggleValue(reviewStatuses, option.value, event.target.checked),
                )}
                type="checkbox"
              />
              {option.label}
            </label>
          ))}
          {onStoryTypesChange && (
            <>
              <span className="story-workspace-toolbar__filter-label">故事类型</span>
              {STORY_TYPE_OPTIONS.map((option) => (
                <label className="story-workspace-toolbar__filter-option" key={option.value}>
                  <input
                    checked={storyTypes.includes(option.value)}
                    onChange={(event) => onStoryTypesChange(
                      toggleValue(storyTypes, option.value, event.target.checked),
                    )}
                    type="checkbox"
                  />
                  {option.label}
                </label>
              ))}
            </>
          )}
        </div>
      </details>

      <select
        aria-label="排序方式"
        className="story-workspace-toolbar__select"
        onChange={(event) => {
          const [nextSort, nextOrder] = event.target.value.split(':');
          onOrderAndSortChange(nextSort, nextOrder as StoryWorkspaceSortOrder);
        }}
        value={`${sort}:${order}`}
      >
        {sortOptions.map((option) => (
          <option key={`${option.sort}:${option.order}`} value={`${option.sort}:${option.order}`}>
            {option.label}
          </option>
        ))}
      </select>

      <span className="story-workspace-toolbar__hint">默认每页 20 条</span>
    </div>
  );
}
