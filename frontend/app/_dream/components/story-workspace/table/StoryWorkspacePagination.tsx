export interface StoryWorkspacePaginationProps {
  page: number;
  perPage: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function StoryWorkspacePagination({
  page,
  perPage,
  total,
  totalPages,
  onPageChange,
}: StoryWorkspacePaginationProps) {
  const safeTotalPages = Math.max(totalPages, total > 0 ? 1 : 0);
  const firstItem = total === 0 ? 0 : (page - 1) * perPage + 1;
  const lastItem = Math.min(page * perPage, total);

  return (
    <nav aria-label="Story Workspace 分页" className="story-workspace-pagination">
      <span className="story-workspace-pagination__summary">
        {total === 0 ? '共 0 条' : `显示 ${firstItem}–${lastItem}，共 ${total} 条`}
      </span>
      <button disabled={page <= 1} onClick={() => onPageChange(page - 1)} type="button">
        上一页
      </button>
      <span>{safeTotalPages === 0 ? '0 / 0' : `${page} / ${safeTotalPages}`}</span>
      <button
        disabled={safeTotalPages === 0 || page >= safeTotalPages}
        onClick={() => onPageChange(page + 1)}
        type="button"
      >
        下一页
      </button>
    </nav>
  );
}
