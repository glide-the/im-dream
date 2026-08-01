// [Input] Story Workspace scenes REST list and local search/filter/sort/page state.
// [Output] Render the scenes route with associations and pending-only selection.
// [Pos] /story-workspace/scenes page.
import { useState } from 'react';
import {
  StoryWorkspaceBatchReviewToolbar,
  StoryWorkspacePagination,
  StoryWorkspaceSceneTable,
  StoryWorkspaceToolbar,
} from '../../components/story-workspace';
import { useDebounce } from '../../hooks/useDebounce';
import {
  useScenes,
  type StoryWorkspaceReviewStatus,
  type StoryWorkspaceSortOrder,
} from '../../hooks/story-workspace';

const SCENE_SORT_OPTIONS = [
  { label: '最近更新', sort: 'updated_at', order: 'desc' as const },
  { label: '最早生成', sort: 'created_at', order: 'asc' as const },
  { label: '名称 A–Z', sort: 'name', order: 'asc' as const },
  { label: '场景顺序', sort: 'order_index', order: 'asc' as const },
];

export function StoryWorkspaceScenesPage() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);
  const [reviewStatuses, setReviewStatuses] = useState<StoryWorkspaceReviewStatus[]>([]);
  const [sort, setSort] = useState('updated_at');
  const [order, setOrder] = useState<StoryWorkspaceSortOrder>('desc');
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [batchNotice, setBatchNotice] = useState('');
  const scenes = useScenes({
    q: debouncedQuery,
    reviewStatus: reviewStatuses,
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
    <section aria-labelledby="story-workspace-scenes-title" className="story-workspace-page">
      <header className="story-workspace-page__header">
        <p className="story-workspace-page__eyebrow">Story Workspace</p>
        <h1 className="story-workspace-page__title" id="story-workspace-scenes-title">场景管理</h1>
        <p className="story-workspace-page__description">浏览场景描述、关联故事与 Agent 生成的角色数量。</p>
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
          order={order}
          query={query}
          reviewStatuses={reviewStatuses}
          sort={sort}
          sortOptions={SCENE_SORT_OPTIONS}
        />
      )}

      {batchNotice && <p className="story-workspace-table__secondary">{batchNotice}</p>}
      {scenes.isLoading ? (
        <div className="story-workspace-table-message">正在加载场景…</div>
      ) : scenes.error ? (
        <div className="story-workspace-table-message story-workspace-table-message--error">
          {scenes.error.message}
        </div>
      ) : scenes.data.length === 0 ? (
        <div className="story-workspace-table-message">还没有场景，等待 Agent 生成。</div>
      ) : (
        <StoryWorkspaceSceneTable
          items={scenes.data}
          onSelectionChange={setSelectedIds}
          onSortChange={updateSort}
          order={order}
          selectedIds={selectedIds}
          sort={sort}
        />
      )}

      <StoryWorkspacePagination
        onPageChange={setPage}
        page={scenes.pagination.page}
        perPage={scenes.pagination.per_page}
        total={scenes.pagination.total}
        totalPages={scenes.pagination.total_pages}
      />
    </section>
  );
}
