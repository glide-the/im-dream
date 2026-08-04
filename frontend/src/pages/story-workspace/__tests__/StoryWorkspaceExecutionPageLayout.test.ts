// [Input] Execution page JSX/CSS source after Dream confirmation.
// [Output] Two-depth layout guard: one overview workplane, then full-width focus replacement.
// [Pos] Story Workspace execution page structural seam (Task 3 F10).

// @ts-expect-error Playwright has Node built-ins; the browser app tsconfig intentionally omits Node types.
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const PAGE_SOURCE = readFileSync(new URL(
  '../StoryWorkspaceExecutionPage.tsx',
  import.meta.url,
), 'utf8');
const CSS_SOURCE = readFileSync(new URL(
  '../StoryWorkspaceExecutionPage.css',
  import.meta.url,
), 'utf8');

test('overview is one workplane with tabs and index content, never a fixed rail grid', () => {
  expect(PAGE_SOURCE).toContain('data-execution-depth="overview"');
  expect(PAGE_SOURCE).toContain('role="tablist"');
  expect(PAGE_SOURCE).not.toContain('story-workspace-collaboration__rail');
  expect(CSS_SOURCE).not.toMatch(/grid-template-columns:\s*(?:270|238)px/);
  expect(CSS_SOURCE).not.toContain('story-workspace-collaboration__rail');
});

test('focus replaces the overview layer and keeps only full-width context navigation', () => {
  const focusStart = PAGE_SOURCE.indexOf('data-execution-depth="focus"');
  const overviewStart = PAGE_SOURCE.indexOf('data-execution-depth="overview"');

  expect(focusStart).toBeGreaterThan(-1);
  expect(overviewStart).toBeGreaterThan(focusStart);
  const focusBranch = PAGE_SOURCE.slice(focusStart, overviewStart);
  expect(focusBranch).toContain('返回故事线');
  expect(focusBranch).toContain('上一条');
  expect(focusBranch).toContain('下一条');
  expect(focusBranch).not.toContain('role="tablist"');
  expect(focusBranch).not.toContain('WorkspaceIndexList');
});

test('execution page uses exactly one dashed rule', () => {
  expect(CSS_SOURCE.match(/dashed/g) ?? []).toHaveLength(1);
});
