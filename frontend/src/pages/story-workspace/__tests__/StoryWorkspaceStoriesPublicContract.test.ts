// [Input] Stories page, public Story contract, and review-editor source.
// [Output] P0 guards against forbidden Story fields and misleading empty copy.
// [Pos] Story Workspace Stories public-browser safety seam.

// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const STORIES_PAGE = readFileSync(new URL('../StoryWorkspaceStoriesPage.tsx', import.meta.url), 'utf8');
const CONTRACTS = readFileSync(new URL(
  '../../../hooks/story-workspace/contracts.ts',
  import.meta.url,
), 'utf8');
const REVIEW_API = readFileSync(new URL(
  '../../../api/storyWorkspaceReviewApi.ts',
  import.meta.url,
), 'utf8');
const REVIEW_DETAIL = readFileSync(new URL(
  '../../../components/story-workspace/layout/StoryWorkspaceReviewDetail.tsx',
  import.meta.url,
), 'utf8');

test('uses the PostgreSQL Story Index empty state instead of claiming no generated files', () => {
  expect(STORIES_PAGE).toContain(
    'PostgreSQL 中暂无故事索引；已生成文件请在对应 Dream 执行页检查同步状态。',
  );
  expect(STORIES_PAGE).not.toContain('暂无故事，等待 Agent 生成。');
});

test('public Story frontend contracts omit internal locators, content, sessions and review revision', () => {
  const storyStart = CONTRACTS.indexOf('export interface StoryWorkspaceStory {');
  const storyEnd = CONTRACTS.indexOf('/** GET/POST', storyStart);
  const publicStory = CONTRACTS.slice(storyStart, storyEnd);
  for (const forbidden of [
    'source_thread_ref',
    'sourceThreadRef',
    'artifact_source_type',
    'content:',
    'agent_session_id',
    'reviewed_script_revision',
  ]) {
    expect(publicStory).not.toContain(forbidden);
    expect(REVIEW_API).not.toContain(forbidden);
  }
});

test('Story review edits cannot synthesize or PATCH an omitted content field', () => {
  expect(REVIEW_DETAIL).not.toContain('draft.content');
  expect(REVIEW_DETAIL).not.toContain("content: draft.content");
  expect(REVIEW_DETAIL).not.toContain("update('content'");
  expect(REVIEW_DETAIL).not.toContain('<label>正文');
});

test('Story review renders neither thread identity nor arbitrary server detail', () => {
  expect(REVIEW_DETAIL).not.toContain('<dt>Thread</dt>');
  expect(REVIEW_DETAIL).not.toContain('{sourceReceipt.chat_thread_id}</code>');
  expect(REVIEW_API).not.toContain('body.detail');
  expect(REVIEW_API).toContain('Story Workspace 请求失败（${response.status}）');
});
