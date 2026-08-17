// [Input] Dream page/router/App source after Chat-unified Dream start integration.
// [Output] Static regression checks for the quiet active preview, marketplace exclusion, and canonical navigation.
// [Pos] Story Workspace Dream launch layout seam test (Task 3 U4)
// [Sync] 2026-08-14: lock the borderless three-item active preview and explicit reveal control.
// [Sync] 2026-08-14: lock system-default inclusion and visible provenance in Community Decks.
// [Sync] 2026-08-14: lock the actor-default fallback when no shared system row exists.
// [Sync] 2026-08-16: require the deferred Deck marketplace to stay out of Dream.

// @ts-expect-error Playwright has Node built-ins; the browser app tsconfig intentionally omits Node types.
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const PAGE_SOURCE = readFileSync(new URL(
  '../StoryWorkspaceDreamPage.tsx',
  import.meta.url,
), 'utf8');
const LAUNCH_SOURCE = readFileSync(new URL(
  '../StoryWorkspaceDreamLaunch.tsx',
  import.meta.url,
), 'utf8');
const ROUTER_SOURCE = readFileSync(new URL(
  '../../../router/story-workspace.tsx',
  import.meta.url,
), 'utf8');
const APP_SOURCE = readFileSync(new URL('../../../App.tsx', import.meta.url), 'utf8');
const DREAM_CSS = readFileSync(new URL('../StoryWorkspaceDreamPage.css', import.meta.url), 'utf8');
const LAYOUT_CSS = readFileSync(new URL(
  '../../../components/story-workspace/layout/StoryWorkspaceLayout.css',
  import.meta.url,
), 'utf8');

test('no-run Dream mounts its re-entry module instead of Chat children', () => {
  expect(PAGE_SOURCE).toContain('<StoryWorkspaceDreamLaunch onNavigate={onNavigate} />');
  expect(PAGE_SOURCE).not.toContain('children: ReactNode');
  expect(PAGE_SOURCE).not.toContain('story-workspace-dream-launch__chat');
  expect(LAUNCH_SOURCE).toContain('进行中的 Dream');
  expect(LAUNCH_SOURCE).toContain('我的 Dream');
  expect(LAUNCH_SOURCE).not.toMatch(/社区卡组|listDecks|reconcileDefaultDeckPlugin|forkDeck/);
  expect(LAUNCH_SOURCE).toContain("run.outcome === 'in_progress'");
  expect(LAUNCH_SOURCE).toContain('role="alert"');
});

test('router keeps Decks content route-scoped and Dream free of Chat seams', () => {
  expect(ROUTER_SOURCE).not.toContain('dreamContent');
  expect(ROUTER_SOURCE).toContain('type ReactNode');
  expect(ROUTER_SOURCE).toContain('decksContent: ReactNode;');
  expect(ROUTER_SOURCE).toContain("case 'decks':");

  const decksRouteBranch = ROUTER_SOURCE.slice(
    ROUTER_SOURCE.indexOf("case 'decks':"),
    ROUTER_SOURCE.indexOf("case 'run-execution':"),
  );
  expect(decksRouteBranch).toContain('{decksContent}');
  expect(ROUTER_SOURCE.match(/\{decksContent\}/g)).toHaveLength(1);

  const dreamPageProps = ROUTER_SOURCE.split('<StoryWorkspaceDreamPage').slice(1);
  expect(dreamPageProps).not.toHaveLength(0);
  dreamPageProps.forEach((props: string) => {
    expect(props.slice(0, props.indexOf('/>'))).not.toContain('decksContent');
  });
  expect(ROUTER_SOURCE).not.toContain('ChatView');
  expect(ROUTER_SOURCE).not.toContain('ChatWidgetUI');

  const storyWorkspaceStart = APP_SOURCE.indexOf("{currentView === 'story-workspace' && (");
  const storyWorkspaceBranch = APP_SOURCE.slice(
    storyWorkspaceStart,
    APP_SOURCE.indexOf("{currentView === 'writing' && (", storyWorkspaceStart),
  );
  expect(storyWorkspaceBranch).toContain('<StoryWorkspaceRouter');
  expect(storyWorkspaceBranch).toContain('legacyContent={{');
  expect(storyWorkspaceBranch).not.toContain('dreamContent=');
});

test('discovery page removes the duplicate launch form and invented workflow actions', () => {
  expect(LAUNCH_SOURCE).not.toContain('>发起 Dream<');
  expect(LAUNCH_SOURCE).not.toContain('创作设置');
  expect(LAUNCH_SOURCE).not.toContain('useStoryWorkspaceDreamLaunch');
  expect(LAUNCH_SOURCE).not.toContain('驳回');
  expect(LAUNCH_SOURCE).not.toContain('归档');
});

test('active runs keep canonical hrefs without a marketplace handoff', () => {
  expect(LAUNCH_SOURCE).not.toContain('/story-workspace/chat?deck=');
  expect(LAUNCH_SOURCE).toContain('href={run.href}');
  expect(LAUNCH_SOURCE).toContain('onNavigate(run.href)');
  expect(LAUNCH_SOURCE).not.toContain('Creation flow');
  expect(LAUNCH_SOURCE).not.toContain('从目标到可编辑稿件');
  expect(LAUNCH_SOURCE).not.toContain('<ol>');
});

test('Dream home uses the layout scroller and a natural-flow responsive card hierarchy', () => {
  expect(LAUNCH_SOURCE).toContain('story-workspace-dream-home__active-grid');
  expect(LAUNCH_SOURCE).toContain('<div className="story-workspace-dream-home"');
  expect(LAUNCH_SOURCE).not.toContain('story-workspace-dream-launch story-workspace-dream-home');
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-home__active-grid\s*\{[^}]*grid-template-columns:/s);
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-home\s*\{[^}]*height: auto;[^}]*overflow: visible;/s);
  expect(LAYOUT_CSS).toMatch(/\.story-workspace-layout__main\s*\{[^}]*overflow-y: auto;/s);
  expect(DREAM_CSS).toContain('@media (max-width: 640px)');
});

test('active Dreams default to a quiet three-item preview with an accessible reveal', () => {
  expect(LAUNCH_SOURCE).toContain('STORY_WORKSPACE_ACTIVE_DREAM_PREVIEW_COUNT = 3');
  expect(LAUNCH_SOURCE).toContain('activeDreamRuns.slice(0, STORY_WORKSPACE_ACTIVE_DREAM_PREVIEW_COUNT)');
  expect(LAUNCH_SOURCE).toContain('aria-controls="dream-active-list"');
  expect(LAUNCH_SOURCE).toContain('aria-expanded={showAllActiveDreams}');
  expect(LAUNCH_SOURCE).toContain("showAllActiveDreams ? '收起' : `查看更多（${hiddenActiveDreamCount}）`");
  expect(LAUNCH_SOURCE).not.toContain('story-workspace-dream-home__active-mark');
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-home__section\s*\{[^}]*border: 0;[^}]*background: transparent;[^}]*box-shadow: none;/s);
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-home__section--active\s*\{[^}]*max-width: 780px;/s);
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-home__active-card\s*\{[^}]*border: 0;[^}]*background: transparent;/s);
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-home__more\s*\{[^}]*border: 0;/s);
});

test('Dream launch surface follows the shared dark theme canvas and action contrast tokens', () => {
  expect(DREAM_CSS).toContain('--dream-canvas: var(--color-bg-app, #f6efe5);');
  expect(DREAM_CSS).toContain('color: var(--dream-canvas);');
  expect(DREAM_CSS).not.toContain('--color-bg-warm');
  expect(DREAM_CSS).toContain('color: var(--color-state-error, #9b3d2e);');
});

test('Dream omits deferred Deck marketplace and installation behavior', () => {
  expect(LAUNCH_SOURCE).not.toMatch(/communityDecks|社区卡组|公开 Deck|安装并使用/);
  expect(LAUNCH_SOURCE).not.toMatch(/listDecks|forkDeck|updateDeckAgentType/);
});
