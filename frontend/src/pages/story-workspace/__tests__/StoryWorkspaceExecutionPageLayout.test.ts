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
const DIALOG_SOURCE = readFileSync(new URL(
  '../../../components/story-workspace/dream/StoryWorkspaceDreamAgentDialog.tsx',
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

test('execution status preview opens the Dream Agent floating dialog without mounting ChatView', () => {
  expect(PAGE_SOURCE).toContain('useStoryWorkspaceDreamAgent');
  expect(PAGE_SOURCE).toContain('<StoryWorkspaceDreamAgentDialog');
  expect(PAGE_SOURCE).toContain('onClick={() => setAgentDialogOpen(true)}');
  expect(PAGE_SOURCE).toContain('Dream Agent 消息预览');
  expect(PAGE_SOURCE).toContain('aria-controls="story-workspace-dream-agent-dialog"');
  expect(DIALOG_SOURCE).toContain('id="story-workspace-dream-agent-dialog"');
  expect(PAGE_SOURCE).not.toContain('<ChatView');
});

test('Episode workbench uses a restrained three-column reading hierarchy', () => {
  expect(CSS_SOURCE).toContain('[aria-label="Episode 叙事工作台"]');
  expect(CSS_SOURCE).toMatch(
    /\[aria-label="Episode 叙事工作台"\]\s*\{[^}]*display:\s*grid;[^}]*grid-template-columns:\s*minmax\(190px,\s*\.72fr\)\s+minmax\(320px,\s*1\.45fr\)\s+minmax\(240px,\s*\.9fr\)/s,
  );
  expect(CSS_SOURCE).toContain('[aria-label="叙事内容工作面"]');
  expect(CSS_SOURCE).toContain('[aria-label="Episode 辅助视图"]');
  expect(CSS_SOURCE).not.toMatch(/\[aria-label="Episode 辅助视图"\][^{]*\{[^}]*grid-column:\s*1\s*\/\s*-1/s);
});

test('Episode layout has one-column narrow-screen degradation and touch-safe controls', () => {
  expect(CSS_SOURCE).toMatch(/@media\s*\(max-width:\s*760px\)/);
  const narrowStart = CSS_SOURCE.indexOf('@media (max-width: 760px)');
  expect(narrowStart).toBeGreaterThan(-1);
  const narrow = CSS_SOURCE.slice(narrowStart);
  expect(narrow).toMatch(
    /\[aria-label="Episode 叙事工作台"\][^{]*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/s,
  );
  expect(narrow).toContain('min-height: 44px');
  expect(narrow).toContain('overflow-x: hidden');
});

test('Episode layout exposes keyboard focus, wrapping, and reduced-motion safeguards', () => {
  expect(CSS_SOURCE).toContain('[role="treeitem"]:focus-visible');
  expect(CSS_SOURCE).toContain('summary:focus-visible');
  expect(CSS_SOURCE).toContain('overflow-wrap: anywhere');
  const reducedMotionStart = CSS_SOURCE.indexOf('@media (prefers-reduced-motion: reduce)');
  expect(reducedMotionStart).toBeGreaterThan(-1);
  const reducedMotion = CSS_SOURCE.slice(reducedMotionStart);
  expect(reducedMotion).toContain('animation-duration: .01ms !important');
  expect(reducedMotion).toContain('transition-duration: .01ms !important');
});

test('Episode continuation dialog owns a viewport-safe confirmation workplane', () => {
  expect(PAGE_SOURCE).toContain('story-workspace-episode-action-dialog');
  expect(PAGE_SOURCE).toContain('aria-modal="true"');
  expect(CSS_SOURCE).toMatch(
    /\.story-workspace-collaboration \.story-workspace-episode-action-dialog\s*\{[^}]*position:\s*fixed;[^}]*max-height:\s*calc\(100dvh - 48px\)/s,
  );
  expect(CSS_SOURCE).toContain('.story-workspace-episode-action-dialog > section');
  const narrowStart = CSS_SOURCE.indexOf('@media (max-width: 760px)');
  expect(CSS_SOURCE.slice(narrowStart)).toMatch(
    /\.story-workspace-collaboration \.story-workspace-episode-action-dialog\s*\{[^}]*inset:\s*10px;[^}]*max-height:\s*calc\(100dvh - 20px\)/s,
  );
});
