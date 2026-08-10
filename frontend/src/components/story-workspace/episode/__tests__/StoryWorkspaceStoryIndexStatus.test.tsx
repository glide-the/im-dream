// [Input] File availability plus Story Index query/mutation facts.
// [Output] Exact two-fact status copy and retry-gating coverage.
// [Pos] Story Workspace bound Episode Story Index status component seam.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
import type { StoryWorkspaceStoryIndexProjection } from '../../../../hooks/story-workspace/contracts';
import {
  storyWorkspaceStoryIndexCanRetry,
  storyWorkspaceStoryIndexCombinedCopy,
  storyWorkspaceStoryIndexDisplayStatus,
} from '../StoryWorkspaceStoryIndexStatus';

const REVISION = `sha256:${'a'.repeat(64)}`;
const STORY_ID = '123e4567-e89b-52d3-a456-426614174000';

function projection(
  status: StoryWorkspaceStoryIndexProjection['status'],
): StoryWorkspaceStoryIndexProjection {
  return {
    runId: `run_${'1'.repeat(32)}`,
    projectId: 'rainy-night',
    storyId: status === 'missing' ? null : STORY_ID,
    status,
    observedManifestRevision: REVISION,
    observedScriptRevision: REVISION,
    indexedManifestRevision: status === 'missing' ? null : REVISION,
    indexedScriptRevision: status === 'missing' ? null : REVISION,
    episodeCount: 1,
    lastIndexedAt: status === 'missing' ? null : '2026-08-10T01:02:03Z',
    errorCode: status === 'missing' ? 'story_index_row_missing' : null,
    retryable: status !== 'indexed',
    etag: REVISION,
  };
}

const SOURCE = readFileSync(new URL('../StoryWorkspaceStoryIndexStatus.tsx', import.meta.url), 'utf8');

test('renders the two independent facts and exact available/indexed copy', () => {
  expect(SOURCE).toContain('aria-label="故事文件与索引状态"');
  expect(SOURCE).toContain('<dt>文件</dt>');
  expect(SOURCE).toContain('<dt>PostgreSQL 索引</dt>');
  expect(storyWorkspaceStoryIndexCombinedCopy('available', 'indexed')).toBe(
    '文件与故事索引均已就绪',
  );
});

test('covers all five index display states with the specified available-file copy', () => {
  const cases = [
    ['syncing', '文件已生成，索引同步中'],
    ['missing', '文件可读，故事索引尚未建立'],
    ['failed', '文件可读，但索引同步失败'],
    ['stale', '文件已更新，索引待刷新'],
  ] as const;
  for (const [status, copy] of cases) {
    expect(storyWorkspaceStoryIndexCombinedCopy('available', status), status).toBe(copy);
  }
  expect(storyWorkspaceStoryIndexDisplayStatus({
    projection: projection('indexed'), error: null, isLoading: false, isSyncing: true,
  })).toBe('syncing');
  expect(storyWorkspaceStoryIndexDisplayStatus({
    projection: projection('missing'), error: new Error('safe'), isLoading: false, isSyncing: false,
  })).toBe('failed');
});

test('shows retry only for retryable missing, stale, or failed states', () => {
  expect(storyWorkspaceStoryIndexCanRetry(projection('missing'), 'missing', false)).toBe(true);
  expect(storyWorkspaceStoryIndexCanRetry(projection('stale'), 'stale', false)).toBe(true);
  expect(storyWorkspaceStoryIndexCanRetry(projection('missing'), 'failed', false)).toBe(true);
  expect(storyWorkspaceStoryIndexCanRetry(projection('indexed'), 'indexed', false)).toBe(false);
  expect(storyWorkspaceStoryIndexCanRetry(projection('missing'), 'syncing', true)).toBe(false);
  expect(SOURCE).toContain("{isSyncing ? '正在同步…' : '重试索引同步'}");
  expect(SOURCE).toContain('disabled={retryDisabled}');
});

test('has explicit loading, empty, safe error, disabled, refresh and retry UI states', () => {
  expect(SOURCE).toContain("? 'loading'");
  expect(SOURCE).toContain("? 'error'");
  expect(SOURCE).toContain("? 'empty'");
  expect(SOURCE).toContain('data-view-state={viewState}');
  expect(SOURCE).toContain('故事索引状态暂时无法读取；页面会继续尝试获取最新状态。');
  expect(SOURCE).toContain('onClick={onRefresh}');
  expect(SOURCE).toContain('>重新检查</button>');
});

test('keeps file missing, invalid, unavailable and generating distinct', () => {
  const cases = [
    ['generating', '文件生成中'],
    ['missing', '文件缺失'],
    ['invalid', '文件无效'],
    ['unavailable', '文件暂不可用'],
  ] as const;
  for (const [fileStatus, expected] of cases) {
    expect(storyWorkspaceStoryIndexCombinedCopy(fileStatus, 'missing')).toContain(expected);
  }
});

test('renders only the fixed safe error code and no internal locator or review fields', () => {
  expect(SOURCE).toContain('{projection.errorCode}');
  for (const forbidden of [
    'source_thread_ref',
    'sourceThreadRef',
    'reviewed_script_revision',
    '/Users/',
    'ARTIFACT_WORKSPACE_ROOT',
  ]) {
    expect(SOURCE).not.toContain(forbidden);
  }
});
