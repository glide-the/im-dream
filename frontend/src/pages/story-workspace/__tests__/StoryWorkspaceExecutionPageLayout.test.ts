// [Input] Execution page JSX/CSS source after Dream confirmation.
// [Output] Two-depth layout guard: one overview workplane, then full-width focus replacement.
// [Pos] Story Workspace execution page structural seam (Task 3 F10).
// [Sync] 2026-08-14: guard the Execution canvas against a light-only fallback in dark mode.
// [Sync] 2026-08-14: guard against restoring the removed workspace update feed.
// [Sync] 2026-08-14: guard structured frontmatter and real storyboard note identifiers.
// [Sync] 2026-08-14: guard default draft and exclusive dialog-selected sync surfaces.
// [Sync] 2026-08-31: guard the canonical reader inside the matching draft Episode focus.
// [Sync] 2026-08-31: guard the concise storyboard overview in the EP list description.
// [Sync] 2026-08-31: guard the read-only three-stage guide and its in-place focus entry.
// [Sync] 2026-09-02: guard Outline-aligned Episode index and accessible return navigation.

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
const CREATION_GUIDE_SOURCE = readFileSync(new URL(
  '../../../components/story-workspace/StoryWorkspaceCreationGuide.tsx',
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

test('screenplay workbench presents current artifacts without a workspace update feed', () => {
  expect(PAGE_SOURCE).not.toContain('工作空间更新流');
  expect(PAGE_SOURCE).not.toContain('stage revisions');
  expect(PAGE_SOURCE).not.toContain('story-workspace-collaboration__activity');
  expect(PAGE_SOURCE).not.toContain('Agent 工作空间历史');
  expect(PAGE_SOURCE).not.toContain('story-workspace-collaboration__history');
  expect(CSS_SOURCE).not.toContain('story-workspace-collaboration__activity');
  expect(CSS_SOURCE).not.toContain('story-workspace-collaboration__history');
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

test('asset focus renders the Hook-published complete document while indexes keep summaries', () => {
  expect(PAGE_SOURCE).toContain("focusedEntry.content ? '完整资产资料' : '主要信息'");
  expect(PAGE_SOURCE).toContain('<StoryWorkspaceAssetContent');
  expect(PAGE_SOURCE).toContain('<ReactMarkdown');
  expect(PAGE_SOURCE).toContain('storyWorkspaceBuildAssetDocumentViewModel(content)');
  expect(PAGE_SOURCE).toContain('aria-label="资产元数据"');
  expect(PAGE_SOURCE).toContain('{document.body}');
  expect(PAGE_SOURCE).toContain('skipHtml');
  expect(PAGE_SOURCE).toContain("entry.summary || '等待 Agent 补充主要信息。'");
  expect(CSS_SOURCE).toContain('.story-workspace-collaboration__asset-document');
  expect(CSS_SOURCE).toContain('.story-workspace-collaboration__asset-metadata');
  expect(CSS_SOURCE).toMatch(/asset-document h1\s*\{[^}]*font-size:\s*clamp\(25px,\s*3vw,\s*34px\)/s);
});

test('storyboard list description and note follow projected shots instead of the flattened summary', () => {
  expect(PAGE_SOURCE).toContain('focusedStoryboardShot?.shotId ?? focusedEntry.entityId');
  expect(PAGE_SOURCE).toContain("focusedStoryboardShot?.visual ?? '等待镜头说明写入工作空间。'");
  expect(PAGE_SOURCE).toContain('`${storyboardShots.length} 镜、${storyboardDurationSeconds} 秒。`');
  expect(PAGE_SOURCE).toContain("entry.key === episodeDraftEntry?.key && storyboardShots.length > 0");
  expect(PAGE_SOURCE).not.toContain("? '分镜概览'");
  expect(PAGE_SOURCE).not.toContain('<b>01</b>');
  expect(CSS_SOURCE).toContain('.story-workspace-collaboration__shot-note code');
});

test('Outline header opens a read-only three-stage guide in the shared focus layer', () => {
  const guideTrigger = PAGE_SOURCE.indexOf('className="story-workspace-collaboration__guide-trigger"');
  const episodeIndex = PAGE_SOURCE.indexOf('id="story-workspace-execution-index"');

  expect(guideTrigger).toBeGreaterThan(-1);
  expect(episodeIndex).toBeGreaterThan(guideTrigger);
  expect(PAGE_SOURCE).toContain('查看短剧创作阶段指引');
  expect(PAGE_SOURCE).not.toContain('STORY_WORKSPACE_CREATION_GUIDE_INDEX_COPY');
  expect(PAGE_SOURCE).not.toContain('story-workspace-collaboration__guide-entry');
  expect(PAGE_SOURCE).toContain('creationGuideFocused ? (');
  expect(PAGE_SOURCE).toContain('<StoryWorkspaceCreationGuide onBack={() => setFocusKey(null)} />');
  expect(PAGE_SOURCE).toContain("focusKey === STORY_WORKSPACE_CREATION_GUIDE_FOCUS_KEY");
  expect(PAGE_SOURCE).toContain('useState<string | null>(null)');
  expect(PAGE_SOURCE).not.toContain('initialFocus');
  expect(CREATION_GUIDE_SOURCE).toContain('角色卡和场景卡首次定稿后');
  expect(CREATION_GUIDE_SOURCE).toContain('每个 EP 重复');
  expect(CREATION_GUIDE_SOURCE).toContain('尚未实现');
  for (const command of [
    '/drama-init',
    '/drama-plan',
    '/drama-asset',
    '/drama-script (EP01)',
    '/drama-storyboard (EP01)',
    '/drama-prompt (EP01)',
    '/script-reviewer',
    '/drama-render + /drama-voice',
    '/drama-edit',
    '/drama-promote',
  ]) expect(CREATION_GUIDE_SOURCE).toContain(command);
  expect(CREATION_GUIDE_SOURCE.match(/<button/g) ?? []).toHaveLength(1);
  expect(CREATION_GUIDE_SOURCE).toContain(
    '/assets/story-workspace-guide-illustrations/01-mimo-xiaohei-workflow-triptych.png',
  );
  expect(CREATION_GUIDE_SOURCE.match(/<img/g) ?? []).toHaveLength(1);
  expect(CREATION_GUIDE_SOURCE).toContain('Mimo 把角色卡和场景卡');
  expect(CREATION_GUIDE_SOURCE).not.toContain('C4D');
  expect(CSS_SOURCE).toContain('.story-workspace-creation-guide__stage--shared > section');
  expect(CSS_SOURCE).toContain('.story-workspace-creation-guide__stage--future');
  expect(CSS_SOURCE).toContain('aspect-ratio: 3 / 2');
  expect(CSS_SOURCE).toContain('grid-template-columns: repeat(3, minmax(0, 1fr))');
  expect(CSS_SOURCE).toContain("font-family: 'Excalifont', 'Xiaolai', Georgia, serif");
  expect(CSS_SOURCE).not.toContain('story-workspace-creation-guide::before');
  expect(CSS_SOURCE).toContain('.story-workspace-collaboration__guide-trigger');
});

test('execution page uses exactly one dashed rule', () => {
  expect(CSS_SOURCE.match(/dashed/g) ?? []).toHaveLength(1);
});

test('execution canvas follows the shared app background token in every theme', () => {
  expect(CSS_SOURCE).toContain(
    '--collaboration-canvas: var(--color-bg-app, #f6efe5);',
  );
  expect(CSS_SOURCE).not.toContain('--color-bg-warm');
});

test('execution status preview opens the Dream Agent floating dialog without mounting ChatView', () => {
  expect(PAGE_SOURCE).toContain('threadId={files.data.threadId}');
  expect(PAGE_SOURCE).toContain('<StoryWorkspaceDreamAgentDialog');
  expect(PAGE_SOURCE).toContain('onClick={() => setAgentDialogOpen(true)}');
  expect(PAGE_SOURCE).toContain('Dream Agent 消息预览');
  expect(PAGE_SOURCE).toContain('aria-controls="story-workspace-dream-agent-dialog"');
  expect(DIALOG_SOURCE).toContain('id="story-workspace-dream-agent-dialog"');
  expect(DIALOG_SOURCE).toContain('<StoryWorkspaceDreamThreadChat');
  expect(PAGE_SOURCE).not.toContain('useStoryWorkspaceDreamAgent');
  expect(PAGE_SOURCE).not.toContain('<ChatView');
});

test('draft is the default full surface and sync remains an exclusive coordination view', () => {
  const projectionStart = PAGE_SOURCE.indexOf('aria-label="Dream 初稿工作台"');
  const artifactMarker = 'aria-label="Episode 产物工作台"';
  const artifactStart = PAGE_SOURCE.indexOf(artifactMarker);
  const agentDialogStart = PAGE_SOURCE.indexOf('<StoryWorkspaceDreamAgentDialog');
  const focusStart = PAGE_SOURCE.indexOf('data-execution-depth="focus"');
  const overviewStart = PAGE_SOURCE.indexOf('data-execution-depth="overview"');
  const readerStart = PAGE_SOURCE.indexOf('<StoryWorkspaceEpisodeArtifactReader');

  expect(projectionStart).toBeGreaterThan(-1);
  expect(PAGE_SOURCE.match(new RegExp(artifactMarker, 'g')) ?? []).toHaveLength(1);
  expect(artifactStart).toBeGreaterThan(projectionStart);
  expect(agentDialogStart).toBeGreaterThan(artifactStart);
  expect(PAGE_SOURCE).toContain("useState<StoryWorkspaceExecutionView>('draft')");
  expect(PAGE_SOURCE).toContain("workspaceView === 'draft'");
  expect(PAGE_SOURCE).toContain("workspaceView === 'sync'");
  expect(PAGE_SOURCE).toContain('onWorkspaceViewChange={setWorkspaceView}');
  expect(readerStart).toBeGreaterThan(focusStart);
  expect(readerStart).toBeLessThan(overviewStart);
  expect(PAGE_SOURCE.slice(artifactStart, agentDialogStart))
    .not.toContain('<StoryWorkspaceEpisodeArtifactReader');
  expect(PAGE_SOURCE).toContain("setWorkspaceView('draft')");
  expect(PAGE_SOURCE).toContain('setFocusKey(episodeDraftEntry.key)');
  expect(PAGE_SOURCE).not.toContain('<summary>Dream 初稿阶段投影</summary>');
  expect(PAGE_SOURCE).not.toContain('dreamProjectionDetailsRef');
  expect(DIALOG_SOURCE).toContain('aria-label="工作台视图"');
  expect(DIALOG_SOURCE).toContain('aria-pressed={workspaceView === \'draft\'}');
  expect(DIALOG_SOURCE).toContain('aria-pressed={workspaceView === \'sync\'}');
  expect(CSS_SOURCE).toMatch(
    /\.story-workspace-collaboration\s*\{[^}]*overflow-y:\s*auto;/s,
  );
  expect(CSS_SOURCE).toMatch(
    /\.story-workspace-collaboration__draft-surface\s*\{[^}]*flex:\s*1 1 auto;/s,
  );
  expect(ROUTER_SOURCE).toContain("case 'run-execution':");
  expect(ROUTER_SOURCE).toContain('key={match.params.storyWorkspaceRunId}');
  expect(ROUTER_SOURCE).toContain('runId={match.params.storyWorkspaceRunId}');
  expect(ROUTER_SOURCE).toContain('episodeId={readStoryWorkspaceEpisodeParam(match.query)}');
});

test('Sync defaults to the Outline-aligned Episode index before an explicit selection', () => {
  const sync = PAGE_SOURCE.slice(
    PAGE_SOURCE.indexOf('aria-label="Episode 产物工作台"'),
    PAGE_SOURCE.indexOf('<StoryWorkspaceDreamAgentDialog'),
  );
  expect(sync).toContain('episodeId === null || episodeId === undefined');
  expect(sync).toContain('id="story-workspace-episode-index-title"');
  expect(sync).toContain('<StoryWorkspaceManuscriptIndex');
  expect(sync).toContain('items={episodeIndexItems}');
  expect(PAGE_SOURCE).toContain('← 返回 Episode 索引');
  expect(sync).toContain('Episode 不存在或已失效');
  expect(sync).not.toContain('Episode execution');
  expect(PAGE_SOURCE).toContain('artifactEpisodeId');
  expect(PAGE_SOURCE).toContain('selectedEpisode?.opaqueEpisodeId ?? null');
  expect(CSS_SOURCE).toContain('.story-workspace-collaboration__episode-back');
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
  const progress = overview.indexOf("'aria-label': `${episodeCode} 产物进度`");

  expect(title).toBeGreaterThan(-1);
  expect(progress).toBeGreaterThan(title);
  expect(PAGE_SOURCE.match(/aria-label="EP01 产物进度"/g) ?? []).toHaveLength(0);
});

test('places the independent Story Index facts below the Episode title without a next-action control', () => {
  const episodeHeader = PAGE_SOURCE.slice(
    PAGE_SOURCE.indexOf('<main aria-labelledby="story-workspace-episode-title">'),
    PAGE_SOURCE.indexOf('</header>', PAGE_SOURCE.indexOf('<main aria-labelledby="story-workspace-episode-title">')),
  );
  const title = episodeHeader.indexOf('id="story-workspace-episode-title"');
  const indexStatus = episodeHeader.indexOf('<StoryWorkspaceStoryIndexStatus');
  expect(title).toBeGreaterThan(-1);
  expect(indexStatus).toBeGreaterThan(title);
  expect(episodeHeader).not.toContain('Episode 下一步');
  expect(CSS_SOURCE).toMatch(
    /\.story-workspace-story-index-status\s*\{[^}]*min-width:\s*0;[^}]*grid-column:\s*1\s*\/\s*-1;/s,
  );
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
    /\[aria-label\$="文件导航"\][^{]*\{[^}]*display:\s*grid;[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/s,
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

test('Episode layout contains no dedicated workflow action confirmation workplane', () => {
  expect(PAGE_SOURCE).not.toContain('story-workspace-episode-action-dialog');
  expect(CSS_SOURCE).not.toContain('story-workspace-episode-action-dialog');
});

test('Episode browser QA freezes the date and timezone before navigation', () => {
  const clockFreeze = EPISODE_E2E_SOURCE.indexOf('await page.clock.setFixedTime');
  const navigation = EPISODE_E2E_SOURCE.indexOf('await page.goto');

  expect(EPISODE_E2E_SOURCE).toContain("timezoneId: 'Asia/Shanghai'");
  expect(clockFreeze).toBeGreaterThan(-1);
  expect(navigation).toBeGreaterThan(clockFreeze);
  expect(EPISODE_E2E_SOURCE).toContain('Unallowlisted API request');
});
