// [Input] Story Workspace scenes REST list and local search/filter/sort/page state.
// [Output] Render the scenes route with associations and pending-only selection.
// [Pos] /story-workspace/scenes page.
import { useEffect, useState } from 'react';
import { batchReviewResources } from '../../api/storyWorkspaceReviewApi';
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
  type StoryWorkspaceScene,
} from '../../hooks/story-workspace';

const SCENE_SORT_OPTIONS = [
  { label: '最近更新', sort: 'updated_at', order: 'desc' as const },
  { label: '最早生成', sort: 'created_at', order: 'asc' as const },
  { label: '名称 A–Z', sort: 'name', order: 'asc' as const },
  { label: '场景顺序', sort: 'order_index', order: 'asc' as const },
];

export interface StoryWorkspaceScenesPageProps {
  onReview?: (scene: StoryWorkspaceScene) => void;
  refreshNonce?: number;
}

export function StoryWorkspaceScenesPage({ onReview, refreshNonce = 0 }: StoryWorkspaceScenesPageProps = {}) {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);
  const [reviewStatuses, setReviewStatuses] = useState<StoryWorkspaceReviewStatus[]>([]);
  const [sort, setSort] = useState('updated_at');
  const [order, setOrder] = useState<StoryWorkspaceSortOrder>('desc');
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [batchNotice, setBatchNotice] = useState('');
  const [batchNotes, setBatchNotes] = useState('');
  const [batchSubmitting, setBatchSubmitting] = useState(false);
  const scenes = useScenes({
    q: debouncedQuery,
    reviewStatus: reviewStatuses,
    sort,
    order,
    page,
    perPage: 20,
  });
  const { refetch: refetchScenes } = scenes;

  useEffect(() => {
    if (refreshNonce > 0) refetchScenes();
  }, [refreshNonce, refetchScenes]);

  const runBatch = async (action: 'confirm' | 'reject') => {
    if (batchSubmitting) return;
    if (action === 'reject' && !batchNotes.trim()) {
      setBatchNotice('批量驳回前请填写修改意见。');
      return;
    }
    setBatchSubmitting(true);
    try {
      const result = await batchReviewResources('scene', selectedIds, action, batchNotes.trim());
      setBatchNotice(`已${action === 'confirm' ? '确认' : '驳回'} ${result.total_updated} 个场景提案。`);
      setSelectedIds([]);
      setBatchNotes('');
      refetchScenes();
    } catch (reason) {
      setBatchNotice(reason instanceof Error ? reason.message : '批量审阅失败。');
    } finally {
      setBatchSubmitting(false);
    }
  };

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
        <div>
          <StoryWorkspaceBatchReviewToolbar
            onCancel={() => {
              setSelectedIds([]);
              setBatchNotes('');
              setBatchNotice('');
            }}
            onConfirm={() => { void runBatch('confirm'); }}
            onReject={() => { void runBatch('reject'); }}
            selectedCount={selectedIds.length}
          />
          <textarea aria-label="批量驳回场景的修改意见" disabled={batchSubmitting} onChange={(event) => setBatchNotes(event.target.value)} placeholder="批量驳回时填写 Agent 修改意见" rows={2} value={batchNotes} style={{ width: '100%', marginTop: 8 }} />
        </div>
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
          onReview={onReview}
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
