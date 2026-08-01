// [Input] Story Workspace stories REST list and local search/filter/sort/page state.
// [Output] Render the stories route with pending-only selection and table controls.
// [Pos] /story-workspace/stories page.
import { useState } from 'react';
import {
  StoryWorkspaceBatchReviewToolbar,
  StoryWorkspacePagination,
  StoryWorkspaceStoryTable,
  StoryWorkspaceToolbar,
} from '../../components/story-workspace';
import { useDebounce } from '../../hooks/useDebounce';
import {
  useStories,
  type StoryWorkspaceReviewStatus,
  type StoryWorkspaceSortOrder,
  type StoryWorkspaceStoryType,
} from '../../hooks/story-workspace';

const STORY_SORT_OPTIONS = [
  { label: '最近生成', sort: 'created_at', order: 'desc' as const },
  { label: '最早生成', sort: 'created_at', order: 'asc' as const },
  { label: '最近更新', sort: 'updated_at', order: 'desc' as const },
  { label: '标题 A–Z', sort: 'title', order: 'asc' as const },
  { label: '标题 Z–A', sort: 'title', order: 'desc' as const },
];

export function StoryWorkspaceStoriesPage() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);
  const [reviewStatuses, setReviewStatuses] = useState<StoryWorkspaceReviewStatus[]>([]);
  const [storyTypes, setStoryTypes] = useState<StoryWorkspaceStoryType[]>([]);
  const [sort, setSort] = useState('created_at');
  const [order, setOrder] = useState<StoryWorkspaceSortOrder>('desc');
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [batchNotice, setBatchNotice] = useState('');
  const stories = useStories({
    q: debouncedQuery,
    reviewStatus: reviewStatuses,
    type: storyTypes,
    sort,
    order,
    page,
    perPage: 20,
  });

  const updateSort = (nextSort: string, nextOrder: StoryWorkspaceSortOrder) => {
    setSort(nextSort);
    setOrder(nextOrder);
    setPage(1);
  };

  return (
    <section aria-labelledby="story-workspace-stories-title" className="story-workspace-page">
      <header className="story-workspace-page__header">
        <p className="story-workspace-page__eyebrow">Story Workspace</p>
        <h1 className="story-workspace-page__title" id="story-workspace-stories-title">故事管理</h1>
        <p className="story-workspace-page__description">搜索、筛选并审阅 Agent 生成的故事与剧本。</p>
      </header>

      {selectedIds.length > 0 ? (
        <StoryWorkspaceBatchReviewToolbar
          onCancel={() => {
            setSelectedIds([]);
            setBatchNotice('');
          }}
          onConfirm={() => setBatchNotice('批量确认接口将在审阅流程任务中接入。')}
          onReject={() => setBatchNotice('批量驳回接口将在审阅流程任务中接入。')}
          selectedCount={selectedIds.length}
        />
      ) : (
        <StoryWorkspaceToolbar
          onOrderAndSortChange={updateSort}
          onQueryChange={(value) => {
            setQuery(value);
            setPage(1);
          }}
          onReviewStatusesChange={(statuses) => {
            setReviewStatuses(statuses);
            setPage(1);
          }}
          onStoryTypesChange={(types) => {
            setStoryTypes(types);
            setPage(1);
          }}
          order={order}
          query={query}
          reviewStatuses={reviewStatuses}
          sort={sort}
          sortOptions={STORY_SORT_OPTIONS}
          storyTypes={storyTypes}
        />
      )}

      {batchNotice && <p className="story-workspace-table__secondary">{batchNotice}</p>}
      {stories.isLoading ? (
        <div className="story-workspace-table-message">正在加载故事…</div>
      ) : stories.error ? (
        <div className="story-workspace-table-message story-workspace-table-message--error">
          {stories.error.message}
        </div>
      ) : stories.data.length === 0 ? (
        <div className="story-workspace-table-message">暂无故事，等待 Agent 生成。</div>
      ) : (
        <StoryWorkspaceStoryTable
          items={stories.data}
          onSelectionChange={setSelectedIds}
          onSortChange={updateSort}
          order={order}
          selectedIds={selectedIds}
          sort={sort}
        />
      )}

      <StoryWorkspacePagination
        onPageChange={setPage}
        page={stories.pagination.page}
        perPage={stories.pagination.per_page}
        total={stories.pagination.total}
        totalPages={stories.pagination.total_pages}
      />
    </section>
  );
}
