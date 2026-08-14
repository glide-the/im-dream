/* eslint-disable react-refresh/only-export-components -- Pure status mappers are exported for strict Node seams. */
// [Input] Current file availability and the independent PostgreSQL Story Index query state.
// [Output] Two explicit facts, one combined outcome, and a narrowly gated retry action.
// [Pos] Bound Episode header; informational only and never gates creative actions.

import type {
  StoryWorkspaceStoryIndexProjection,
  StoryWorkspaceStoryIndexStatus,
} from '../../../hooks/story-workspace/contracts';

export type StoryWorkspaceStoryIndexFileStatus =
  | 'generating'
  | 'available'
  | 'missing'
  | 'invalid'
  | 'unavailable';

export type StoryWorkspaceStoryIndexDisplayStatus =
  | 'syncing'
  | StoryWorkspaceStoryIndexStatus;

export interface StoryWorkspaceStoryIndexStatusProps {
  readonly fileStatus: StoryWorkspaceStoryIndexFileStatus;
  readonly projection: StoryWorkspaceStoryIndexProjection | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly isSyncing: boolean;
  readonly onRefresh: () => void;
  readonly onRetry: () => void;
}

const FILE_STATUS_LABELS: Readonly<Record<StoryWorkspaceStoryIndexFileStatus, string>> = {
  generating: '生成中',
  available: '可读',
  missing: '缺失',
  invalid: '无效',
  unavailable: '暂不可用',
};

const INDEX_STATUS_LABELS: Readonly<Record<StoryWorkspaceStoryIndexDisplayStatus, string>> = {
  syncing: '同步中',
  indexed: '已就绪',
  missing: '未建立',
  stale: '版本已过期',
  failed: '同步失败',
};

export function storyWorkspaceStoryIndexDisplayStatus({
  projection,
  error,
  isLoading,
  isSyncing,
}: Pick<
StoryWorkspaceStoryIndexStatusProps,
'projection' | 'error' | 'isLoading' | 'isSyncing'
>): StoryWorkspaceStoryIndexDisplayStatus {
  if (isSyncing || (isLoading && projection === null)) return 'syncing';
  if (error !== null) return 'failed';
  return projection?.status ?? 'missing';
}

export function storyWorkspaceStoryIndexCombinedCopy(
  fileStatus: StoryWorkspaceStoryIndexFileStatus,
  indexStatus: StoryWorkspaceStoryIndexDisplayStatus,
): string {
  if (fileStatus === 'available') {
    if (indexStatus === 'indexed') return '文件与故事索引均已就绪';
    if (indexStatus === 'syncing') return '文件已生成，索引同步中';
    if (indexStatus === 'missing') return '文件可读，故事索引尚未建立';
    if (indexStatus === 'failed') return '文件可读，但索引同步失败';
    return '文件已更新，索引待刷新';
  }
  const fileLabel = FILE_STATUS_LABELS[fileStatus];
  const indexLabel = INDEX_STATUS_LABELS[indexStatus];
  return `文件${fileLabel}；故事索引${indexLabel}`;
}

export function storyWorkspaceStoryIndexCanRetry(
  projection: StoryWorkspaceStoryIndexProjection | null,
  indexStatus: StoryWorkspaceStoryIndexDisplayStatus,
  isSyncing: boolean,
): boolean {
  return projection?.retryable === true
    && (indexStatus === 'missing' || indexStatus === 'stale' || indexStatus === 'failed')
    && !isSyncing;
}

export function StoryWorkspaceStoryIndexStatus({
  fileStatus,
  projection,
  error,
  isLoading,
  isSyncing,
  onRefresh,
  onRetry,
}: StoryWorkspaceStoryIndexStatusProps) {
  const indexStatus = storyWorkspaceStoryIndexDisplayStatus({
    projection,
    error,
    isLoading,
    isSyncing,
  });
  const retryable = storyWorkspaceStoryIndexCanRetry(projection, indexStatus, isSyncing);
  const offersRetry = projection?.retryable === true
    && (
      projection.status === 'missing'
      || projection.status === 'stale'
      || projection.status === 'failed'
    );
  const retryDisabled = !retryable || isLoading;
  const viewState = isLoading && projection === null
    ? 'loading'
    : error !== null
      ? 'error'
      : projection === null
        ? 'empty'
        : 'ready';

  return (
    <section
      aria-label="故事文件与索引状态"
      aria-live="polite"
      className="story-workspace-story-index-status"
      data-file-status={fileStatus}
      data-index-status={indexStatus}
      data-view-state={viewState}
    >
      <dl>
        <div>
          <dt>文件</dt>
          <dd>{FILE_STATUS_LABELS[fileStatus]}</dd>
        </div>
        <div>
          <dt>PostgreSQL 索引</dt>
          <dd>{INDEX_STATUS_LABELS[indexStatus]}</dd>
        </div>
      </dl>
      <p>{storyWorkspaceStoryIndexCombinedCopy(fileStatus, indexStatus)}</p>
      {error !== null && (
        <p role="alert">故事索引状态暂时无法读取；页面会继续尝试获取最新状态。</p>
      )}
      {projection?.errorCode !== null && projection?.errorCode !== undefined && (
        <code>错误码：{projection.errorCode}</code>
      )}
      {offersRetry && (
        <button disabled={retryDisabled} onClick={onRetry} type="button">
          {isSyncing ? '正在同步…' : '重试索引同步'}
        </button>
      )}
      {error !== null && projection === null && (
        <button disabled={isLoading} onClick={onRefresh} type="button">重新检查</button>
      )}
    </section>
  );
}
