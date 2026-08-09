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
const EPISODE_WORKBENCH_SOURCE = readFileSync(new URL(
  '../../../components/story-workspace/episode/StoryWorkspaceEpisodeNarrativeWorkbench.tsx',
  import.meta.url,
), 'utf8');
const EPISODE_E2E_SOURCE = readFileSync(new URL(
  '../../../../e2e/story-workspace-episode-execution.spec.ts',
  import.meta.url,
), 'utf8');
const ROUTER_SOURCE = readFileSync(new URL(
  '../../../router/story-workspace.tsx',
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
  expect(PAGE_SOURCE).toMatch(
    /onClick=\{\(\) => \{\s*setDreamAgentInitialWorkflowFocus\(null\);\s*setAgentDialogOpen\(true\);\s*\}\}/,
  );
  expect(PAGE_SOURCE).toContain('Dream Agent 消息预览');
  expect(PAGE_SOURCE).toContain('aria-controls="story-workspace-dream-agent-dialog"');
  expect(DIALOG_SOURCE).toContain('id="story-workspace-dream-agent-dialog"');
  expect(PAGE_SOURCE).not.toContain('<ChatView');
});

test('Episode artifacts unfold after the Dream projection on the same run execution route', () => {
  const projectionStart = PAGE_SOURCE.indexOf('<details ref={dreamProjectionDetailsRef}>');
  const projectionEnd = PAGE_SOURCE.indexOf('</details>', projectionStart);
  const artifactMarker = 'aria-label="第一集产物工作台"';
  const artifactStart = PAGE_SOURCE.indexOf(artifactMarker);
  const agentDialogStart = PAGE_SOURCE.indexOf('<StoryWorkspaceDreamAgentDialog');

  expect(projectionStart).toBeGreaterThan(-1);
  expect(projectionEnd).toBeGreaterThan(projectionStart);
  expect(PAGE_SOURCE.match(new RegExp(artifactMarker, 'g')) ?? []).toHaveLength(1);
  expect(artifactStart).toBeGreaterThan(projectionEnd);
  expect(agentDialogStart).toBeGreaterThan(artifactStart);
  expect(PAGE_SOURCE.slice(projectionStart, PAGE_SOURCE.indexOf('>', projectionStart) + 1))
    .toBe('<details ref={dreamProjectionDetailsRef}>');
  expect(CSS_SOURCE).toMatch(
    /\.story-workspace-collaboration\s*\{[^}]*overflow-y:\s*auto;/s,
  );
  expect(ROUTER_SOURCE).toContain("case 'run-execution':");
  expect(ROUTER_SOURCE).toContain('key={match.params.storyWorkspaceRunId}');
  expect(ROUTER_SOURCE).toContain('runId={match.params.storyWorkspaceRunId}');
});

test('Episode workbench uses a two-column master-detail hierarchy', () => {
  expect(CSS_SOURCE).toContain('[aria-label="Episode 主工作面"]');
  expect(CSS_SOURCE).toMatch(
    /\[aria-label="Episode 主工作面"\]\s*\{[^}]*display:\s*grid;[^}]*grid-template-columns:\s*minmax\(200px,\s*\.62fr\)\s+minmax\(0,\s*2fr\)/s,
  );
  expect(CSS_SOURCE).toContain('[aria-label="叙事内容工作面"]');
  expect(CSS_SOURCE).toContain('[aria-label="Episode 辅助视图"]');
  expect(EPISODE_WORKBENCH_SOURCE).toContain("{ 'aria-label': 'Episode 内容工作面' }");
  const contentWorkplane = EPISODE_WORKBENCH_SOURCE.indexOf("{ 'aria-label': 'Episode 内容工作面' }");
  const auxiliaryView = EPISODE_WORKBENCH_SOURCE.indexOf("{ 'aria-label': 'Episode 辅助视图' }");
  expect(contentWorkplane).toBeGreaterThan(-1);
  expect(auxiliaryView).toBeGreaterThan(contentWorkplane);
});

test('places the artifact progress directly below the Episode Overview title', () => {
  const overviewStart = EPISODE_WORKBENCH_SOURCE.indexOf('function EpisodeOverviewContent');
  const overviewEnd = EPISODE_WORKBENCH_SOURCE.indexOf('function BeatContent', overviewStart);
  const overview = EPISODE_WORKBENCH_SOURCE.slice(overviewStart, overviewEnd);
  const title = overview.indexOf("h('h2'");
  const progress = overview.indexOf("'aria-label': '第一集产物进度'");

  expect(title).toBeGreaterThan(-1);
  expect(progress).toBeGreaterThan(title);
  expect(PAGE_SOURCE.match(/aria-label="第一集产物进度"/g) ?? []).toHaveLength(0);
});

test('Episode layout has a mobile storyline sheet and 44px controls below 768px', () => {
  expect(CSS_SOURCE).toMatch(/@media\s*\(max-width:\s*767px\)/);
  const narrowStart = CSS_SOURCE.indexOf('@media (max-width: 767px)');
  expect(narrowStart).toBeGreaterThan(-1);
  const narrow = CSS_SOURCE.slice(narrowStart);
  expect(narrow).toMatch(
    /\[aria-label="Episode 主工作面"\][^{]*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/s,
  );
  expect(narrow).toContain('min-height: 44px');
  expect(narrow).toContain('min-width: 44px');
  expect(narrow).toContain('overflow-x: hidden');
  expect(narrow).toContain('.story-workspace-episode-storyline-sheet');
  expect(narrow).toContain('position: fixed');
  expect(narrow).toMatch(
    /\[aria-label="第一集文件导航"\][^{]*\{[^}]*display:\s*grid;[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/s,
  );
  expect(narrow).toMatch(
    /\.story-workspace-episode-artifact-reader__markdown table\s*\{[^}]*overflow-x:\s*auto/s,
  );
  expect(EPISODE_WORKBENCH_SOURCE).toContain("'aria-expanded': storylineOpen");
  expect(EPISODE_WORKBENCH_SOURCE).toContain("'aria-controls': STORYLINE_SHEET_ID");
  expect(EPISODE_WORKBENCH_SOURCE).toContain('hidden: isNarrowLayout && !storylineOpen');
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
  const narrowStart = CSS_SOURCE.indexOf('@media (max-width: 767px)');
  expect(CSS_SOURCE.slice(narrowStart)).toMatch(
    /\.story-workspace-collaboration \.story-workspace-episode-action-dialog\s*\{[^}]*inset:\s*10px;[^}]*max-height:\s*calc\(100dvh - 20px\)/s,
  );
});

test('Episode browser QA freezes the date and timezone before navigation', () => {
  const clockFreeze = EPISODE_E2E_SOURCE.indexOf('await page.clock.setFixedTime');
  const navigation = EPISODE_E2E_SOURCE.indexOf('await page.goto');

  expect(EPISODE_E2E_SOURCE).toContain("timezoneId: 'Asia/Shanghai'");
  expect(clockFreeze).toBeGreaterThan(-1);
  expect(navigation).toBeGreaterThan(clockFreeze);
  expect(EPISODE_E2E_SOURCE).toContain('Unallowlisted API request');
});
