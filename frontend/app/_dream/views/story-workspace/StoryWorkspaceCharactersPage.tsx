// [Input] Story Workspace characters REST list and local search/filter/sort/page state.
// [Output] Render the characters route with tags, avatars, and pending-only selection.
// [Pos] /story-workspace/characters page.
import { useEffect, useState } from 'react';
import { batchReviewResources } from '../../api/storyWorkspaceReviewApi';
import {
  StoryWorkspaceBatchReviewToolbar,
  StoryWorkspaceCharacterTable,
  StoryWorkspacePagination,
  StoryWorkspaceToolbar,
} from '../../components/story-workspace';
import { useDebounce } from '../../hooks/useDebounce';
import {
  useCharacters,
  type StoryWorkspaceReviewStatus,
  type StoryWorkspaceSortOrder,
  type StoryWorkspaceCharacter,
} from '../../hooks/story-workspace';

const CHARACTER_SORT_OPTIONS = [
  { label: '最近更新', sort: 'updated_at', order: 'desc' as const },
  { label: '最早生成', sort: 'created_at', order: 'asc' as const },
  { label: '名称 A–Z', sort: 'name', order: 'asc' as const },
  { label: '名称 Z–A', sort: 'name', order: 'desc' as const },
];

export interface StoryWorkspaceCharactersPageProps {
  onReview?: (character: StoryWorkspaceCharacter) => void;
  refreshNonce?: number;
}

export function StoryWorkspaceCharactersPage({ onReview, refreshNonce = 0 }: StoryWorkspaceCharactersPageProps = {}) {
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
  const characters = useCharacters({
    q: debouncedQuery,
    reviewStatus: reviewStatuses,
    sort,
    order,
    page,
    perPage: 20,
  });
  const { refetch: refetchCharacters } = characters;

  useEffect(() => {
    if (refreshNonce > 0) refetchCharacters();
  }, [refreshNonce, refetchCharacters]);

  const runBatch = async (action: 'confirm' | 'reject') => {
    if (batchSubmitting) return;
    if (action === 'reject' && !batchNotes.trim()) {
      setBatchNotice('批量驳回前请填写修改意见。');
      return;
    }
    setBatchSubmitting(true);
    try {
      const result = await batchReviewResources('character', selectedIds, action, batchNotes.trim());
      setBatchNotice(`已${action === 'confirm' ? '确认' : '驳回'} ${result.total_updated} 个角色提案。`);
      setSelectedIds([]);
      setBatchNotes('');
      refetchCharacters();
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
    <section aria-labelledby="story-workspace-characters-title" className="story-workspace-page">
      <header className="story-workspace-page__header">
        <p className="story-workspace-page__eyebrow">Story Workspace</p>
        <h1 className="story-workspace-page__title" id="story-workspace-characters-title">角色管理</h1>
        <p className="story-workspace-page__description">查看 Agent 生成的角色身份、性格标签与审阅状态。</p>
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
          <textarea aria-label="批量驳回角色的修改意见" disabled={batchSubmitting} onChange={(event) => setBatchNotes(event.target.value)} placeholder="批量驳回时填写 Agent 修改意见" rows={2} value={batchNotes} style={{ width: '100%', marginTop: 8 }} />
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
          sortOptions={CHARACTER_SORT_OPTIONS}
        />
      )}

      {batchNotice && <p className="story-workspace-table__secondary">{batchNotice}</p>}
      {characters.isLoading ? (
        <div className="story-workspace-table-message">正在加载角色…</div>
      ) : characters.error ? (
        <div className="story-workspace-table-message story-workspace-table-message--error">
          {characters.error.message}
        </div>
      ) : characters.data.length === 0 ? (
        <div className="story-workspace-table-message">还没有角色，等待 Agent 生成。</div>
      ) : (
        <StoryWorkspaceCharacterTable
          items={characters.data}
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
        page={characters.pagination.page}
        perPage={characters.pagination.per_page}
        total={characters.pagination.total}
        totalPages={characters.pagination.total_pages}
      />
    </section>
  );
}
