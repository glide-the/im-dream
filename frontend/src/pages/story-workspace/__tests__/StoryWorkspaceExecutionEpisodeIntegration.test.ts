// [Input] Story Workspace execution and Dream dialog sources.
// [Output] Static integration guards for draft-hosted read-only artifacts and shared Chat interaction.
// [Pos] Prevents the deleted Episode action state machine from returning.
// [Sync] 2026-08-31: keep the file reader in its matching draft Episode focus.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses a built-in omitted from browser app types.
import { readFileSync } from 'node:fs';
const PAGE_SOURCE = readFileSync(
  new URL('../StoryWorkspaceExecutionPage.tsx', import.meta.url),
  'utf8',
);
const DIALOG_SOURCE = readFileSync(
  new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamAgentDialog.tsx', import.meta.url),
  'utf8',
);
const THREAD_CHAT_SOURCE = readFileSync(
  new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx', import.meta.url),
  'utf8',
);
const QUERY_SOURCE = readFileSync(
  new URL('../../../hooks/story-workspace/useStoryWorkspaceEpisodeArtifacts.ts', import.meta.url),
  'utf8',
);

test('Execution renders the canonical Episode artifact reader as a read-only projection', () => {
  const draftFocusStart = PAGE_SOURCE.indexOf('data-execution-depth="focus"');
  const draftOverviewStart = PAGE_SOURCE.indexOf('data-execution-depth="overview"');
  const syncStart = PAGE_SOURCE.indexOf('aria-label="Episode 产物工作台"');
  const dialogStart = PAGE_SOURCE.indexOf('<StoryWorkspaceDreamAgentDialog');
  const readerStart = PAGE_SOURCE.indexOf('<StoryWorkspaceEpisodeArtifactReader');

  expect(PAGE_SOURCE).toContain('useStoryWorkspaceEpisodeArtifacts');
  expect(readerStart).toBeGreaterThan(draftFocusStart);
  expect(readerStart).toBeLessThan(draftOverviewStart);
  expect(PAGE_SOURCE.slice(syncStart, dialogStart))
    .not.toContain('<StoryWorkspaceEpisodeArtifactReader');
  expect(PAGE_SOURCE).toContain('focusedEntry.key === episodeDraftEntry?.key');
  expect(PAGE_SOURCE).toContain('尚未构建');
  expect(PAGE_SOURCE).toContain('产物关联');
  expect(PAGE_SOURCE).not.toContain('尚未建立可信');
});

test('Dream dialog composes the shared Chat panel without workflow recommendation controls', () => {
  expect(DIALOG_SOURCE).toContain('<StoryWorkspaceDreamThreadChat');
  expect(THREAD_CHAT_SOURCE).toContain('<ChatPanel');
  expect(DIALOG_SOURCE).not.toContain('recommendedAction');
  expect(DIALOG_SOURCE).not.toContain('workflowActions');
  expect(DIALOG_SOURCE).not.toContain('Episode 下一步');
  expect(DIALOG_SOURCE).toContain('aria-label="工作台视图"');
  expect(DIALOG_SOURCE).toContain('初稿');
  expect(DIALOG_SOURCE).toContain('同步');
});

test('Episode artifact query exposes GET, ETag, polling and invalidation only', () => {
  expect(QUERY_SOURCE).toContain('storyWorkspaceFetchEpisodeArtifacts');
  expect(QUERY_SOURCE).toContain("credentials: 'include'");
  expect(QUERY_SOURCE).toContain('If-None-Match');
  expect(QUERY_SOURCE).not.toContain('episode-actions/continue');
  expect(QUERY_SOURCE).not.toContain('episode-binding/recover');
  expect(QUERY_SOURCE).not.toMatch(/method:\s*['"]POST['"]/);
});

test('Execution has no code-level stage transition or completion-fact state machine', () => {
  for (const forbidden of [
    'actionProjection',
    'nextAction',
    'completionFact',
    'storyWorkspaceContinueEpisodeAction',
    'storyWorkspaceRecoverEpisodeBinding',
    '确认 Episode 下一步',
  ]) {
    expect(PAGE_SOURCE).not.toContain(forbidden);
  }
});
