// [Input] One public Story row with Artifact index metadata.
// [Output] Combined-column, short-revision, and execution-link render coverage.
// [Pos] Story Workspace Stories table frontend seam.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
import type { StoryWorkspaceStory } from '../../../../hooks/story-workspace/contracts';
import {
  storyWorkspaceArtifactIndexStatus,
  storyWorkspaceShortRevision,
} from '../StoryWorkspaceStoryTable';

const REVISION = `sha256:${'a'.repeat(64)}`;
const RUN_ID = `run_${'1'.repeat(32)}`;
const SOURCE = readFileSync(new URL('../StoryWorkspaceStoryTable.tsx', import.meta.url), 'utf8');

const STORY: StoryWorkspaceStory = {
  id: '123e4567-e89b-52d3-a456-426614174000',
  identifier: 'rainy-night',
  title: '雨夜重逢',
  description: null,
  status: 'draft',
  review_status: 'pending',
  type: 'script',
  character_count: 0,
  scene_count: 0,
  created_at: '2026-08-10T01:00:00Z',
  updated_at: '2026-08-10T01:02:03Z',
  confirmed_at: null,
  source_run_id: RUN_ID,
  source_project_id: 'rainy-night',
  episode_count: 2,
  artifact_manifest_revision: REVISION,
  script_revision: REVISION,
  artifact_sync_status: 'indexed',
  artifact_indexed_at: '2026-08-10T01:02:03Z',
  artifact_sync_error_code: null,
  script_size_bytes: 2048,
  artifact_available: true,
  reconcile_version: 1,
};

test('renders one 产物 / 索引 column with its four compact facts', () => {
  expect(SOURCE.match(/产物 \/ 索引/g) ?? []).toHaveLength(1);
  expect(storyWorkspaceArtifactIndexStatus(STORY)).toBe('文件可读 · 索引已就绪');
  expect(SOURCE).toContain("<span>集数 {story.episode_count ?? '—'}</span>");
  expect(storyWorkspaceShortRevision(REVISION)).toBe('aaaaaaaaaa…');
  expect(SOURCE).toContain('storyWorkspaceExecutionDeepLink(story.source_run_id)');
  expect(SOURCE).toContain('查看执行');
});

test('revision and status helpers fail closed for malformed public values', () => {
  expect(storyWorkspaceShortRevision(REVISION)).toBe('aaaaaaaaaa…');
  expect(storyWorkspaceShortRevision('/Users/private/script.md')).toBe('—');
  expect(storyWorkspaceArtifactIndexStatus(STORY)).toBe('文件可读 · 索引已就绪');
  expect(storyWorkspaceArtifactIndexStatus({
    ...STORY,
    artifact_available: false,
    artifact_sync_status: 'missing',
  })).toBe('文件缺失 · 索引未建立');
});

test('table source never renders private locators, script content, or reviewed revision', () => {
  for (const forbidden of [
    'source_thread_ref',
    'sourceThreadRef',
    'artifact_source_type',
    'reviewed_script_revision',
    'story.content',
  ]) expect(SOURCE).not.toContain(forbidden);
});
