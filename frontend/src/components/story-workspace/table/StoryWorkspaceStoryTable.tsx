/* eslint-disable react-refresh/only-export-components -- Compact public metadata formatters are deterministic test seams. */
import type {
  StoryWorkspaceSortOrder,
  StoryWorkspaceStory,
  StoryWorkspaceStoryType,
} from '../../../hooks/story-workspace';
import {
  StoryWorkspaceSurfaceLinkButton,
  type StoryWorkspaceSurfaceLinkButtonProps,
} from '../StoryWorkspaceSurfaceLinkButton';
import { storyWorkspaceExecutionDeepLink } from '../surfaceLink';
import { StoryWorkspaceReviewStatusBadge } from './StoryWorkspaceReviewStatusBadge';
import { StoryWorkspaceSortButton } from './StoryWorkspaceSortButton';
import { StoryWorkspaceTableRow } from './StoryWorkspaceTableRow';
import {
  formatStoryWorkspaceDate,
  pendingSelectionHandler,
  togglePendingSelection,
} from './tableHelpers';

const STORY_TYPE_LABELS: Record<StoryWorkspaceStoryType, string> = {
  short: '短剧',
  long: '长篇',
  script: '剧本',
  outline: '大纲',
};

const ARTIFACT_SYNC_STATUS_LABELS = {
  syncing: '同步中',
  indexed: '已就绪',
  stale: '版本已过期',
  missing: '未建立',
  failed: '同步失败',
} as const;

const STORY_REVISION = /^sha256:([0-9a-f]{64})$/;
const STORY_RUN_ID = /^run_[0-9a-f]{32}$/;

export function storyWorkspaceShortRevision(value: string | null | undefined): string {
  const match = value?.match(STORY_REVISION);
  return match?.[1] ? `${match[1].slice(0, 10)}…` : '—';
}

export function storyWorkspaceArtifactIndexStatus(story: StoryWorkspaceStory): string {
  const file = story.artifact_available === true
    ? '文件可读'
    : story.artifact_available === false
      ? '文件缺失'
      : '文件状态未知';
  const syncStatus = story.artifact_sync_status;
  const index = syncStatus !== null
    && Object.prototype.hasOwnProperty.call(ARTIFACT_SYNC_STATUS_LABELS, syncStatus)
    ? `索引${ARTIFACT_SYNC_STATUS_LABELS[syncStatus]}`
    : '索引未建立';
  return `${file} · ${index}`;
}

export interface StoryWorkspaceStoryTableProps {
  items: StoryWorkspaceStory[];
  selectedIds: string[];
  sort: string;
  order: StoryWorkspaceSortOrder;
  onReview?: (story: StoryWorkspaceStory) => void;
  onSelectionChange: (ids: string[]) => void;
  onSortChange: (sort: string, order: StoryWorkspaceSortOrder) => void;
  /**
   * Row-level Dream surface link mount (design_004 §4.1, same component as the
   * review panel detail area). Optional: while no server aggregation binds
   * stories to runs, callers omit it and no link renders.
   */
  surfaceLinkForStory?: (story: StoryWorkspaceStory) => StoryWorkspaceSurfaceLinkButtonProps | null;
}

export function StoryWorkspaceStoryTable({
  items,
  selectedIds,
  sort,
  order,
  onReview,
  onSelectionChange,
  onSortChange,
  surfaceLinkForStory,
}: StoryWorkspaceStoryTableProps) {
  const pendingIds = items
    .filter((item) => item.review_status === 'pending' && item.status !== 'archived')
    .map((item) => item.id);
  const allPendingSelected = pendingIds.length > 0
    && pendingIds.every((id) => selectedIds.includes(id));

  return (
    <div className="story-workspace-table-shell">
      <table className="story-workspace-table">
        <thead>
          <tr>
            <th>
              <input
                aria-label="选择本页全部待审阅故事"
                checked={allPendingSelected}
                disabled={pendingIds.length === 0}
                onChange={pendingSelectionHandler(pendingIds, selectedIds, onSelectionChange)}
                type="checkbox"
              />
            </th>
            <th style={{ width: '24%' }}>
              <StoryWorkspaceSortButton
                activeSort={sort}
                field="title"
                label="标题"
                onSortChange={onSortChange}
                order={order}
              />
            </th>
            <th style={{ width: 104 }}>审阅状态</th>
            <th style={{ width: 80 }}>类型</th>
            <th style={{ width: 80 }}>角色数</th>
            <th style={{ width: 80 }}>场景数</th>
            <th style={{ width: 150 }}>生成时间</th>
            <th style={{ width: 220 }}>产物 / 索引</th>
            <th style={{ width: 132 }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {items.map((story) => {
            const displayReviewStatus = story.status === 'archived'
              ? 'archived'
              : story.review_status;
            const surfaceLinkProps = surfaceLinkForStory?.(story) ?? null;

            return (
              <StoryWorkspaceTableRow
              checked={selectedIds.includes(story.id)}
              key={story.id}
              onCheckedChange={(checked) => onSelectionChange(
                togglePendingSelection(selectedIds, story.id, checked),
              )}
              reviewStatus={displayReviewStatus}
            >
              <td>
                <div className="story-workspace-table__primary" title={story.title}>{story.title}</div>
                <div className="story-workspace-table__secondary">{story.identifier}</div>
              </td>
              <td><StoryWorkspaceReviewStatusBadge status={displayReviewStatus} /></td>
              <td>{STORY_TYPE_LABELS[story.type] ?? story.type}</td>
              <td>{story.character_count}</td>
              <td>{story.scene_count}</td>
              <td>{formatStoryWorkspaceDate(story.created_at)}</td>
              <td>
                <div
                  className="story-workspace-table__artifact-status"
                  data-artifact-sync-status={story.artifact_sync_status ?? 'missing'}
                >
                  {storyWorkspaceArtifactIndexStatus(story)}
                </div>
                <div className="story-workspace-table__artifact-facts">
                  <span>集数 {story.episode_count ?? '—'}</span>
                  <code title={story.script_revision ?? story.artifact_manifest_revision ?? undefined}>
                    {storyWorkspaceShortRevision(
                      story.script_revision ?? story.artifact_manifest_revision,
                    )}
                  </code>
                </div>
                <time className="story-workspace-table__artifact-time">
                  {formatStoryWorkspaceDate(story.artifact_indexed_at)}
                </time>
              </td>
              <td>
                <button
                  className="story-workspace-table__action"
                  onClick={() => onReview?.(story)}
                  type="button"
                >
                  审阅
                </button>
                {story.source_run_id !== null && STORY_RUN_ID.test(story.source_run_id) && (
                  <a
                    className="story-workspace-table__execution-link"
                    href={storyWorkspaceExecutionDeepLink(story.source_run_id)}
                  >
                    查看执行
                  </a>
                )}
                {surfaceLinkProps && <StoryWorkspaceSurfaceLinkButton {...surfaceLinkProps} />}
              </td>
              </StoryWorkspaceTableRow>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
