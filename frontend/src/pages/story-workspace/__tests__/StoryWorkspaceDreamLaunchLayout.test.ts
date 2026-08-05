// [Input] Dream page/router/App source after the dedicated Dream start integration.
// [Output] Static regression checks that Dream no longer embeds the ordinary Chat UI.
// [Pos] Story Workspace Dream launch layout seam test (Task 3 U4)

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

test('no-run Dream mounts its own launch module instead of Chat children', () => {
  expect(PAGE_SOURCE).toContain('<StoryWorkspaceDreamLaunch onNavigate={onNavigate} />');
  expect(PAGE_SOURCE).not.toContain('children: ReactNode');
  expect(PAGE_SOURCE).not.toContain('story-workspace-dream-launch__chat');
  expect(LAUNCH_SOURCE).toContain('发起 Dream');
  expect(LAUNCH_SOURCE).toContain('listDecks');
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
  expect(storyWorkspaceBranch).not.toContain('<ChatView');
  expect(storyWorkspaceBranch).not.toContain('<ChatWidgetUI');
  expect(storyWorkspaceBranch).not.toContain('dreamContent=');
});

test('launch page keeps one primary action and no business failure branches', () => {
  expect(LAUNCH_SOURCE.match(/>发起 Dream</g)).toHaveLength(1);
  expect(LAUNCH_SOURCE).not.toContain('驳回');
  expect(LAUNCH_SOURCE).not.toContain('归档');
  expect(LAUNCH_SOURCE).not.toContain('重试');
});

test('launch surface uses one concise lifecycle note instead of a four-step lifecycle guide', () => {
  expect(LAUNCH_SOURCE).toContain('Dream 会逐步写入人物、场景与分镜');
  expect(LAUNCH_SOURCE).not.toContain('Creation flow');
  expect(LAUNCH_SOURCE).not.toContain('从目标到可编辑稿件');
  expect(LAUNCH_SOURCE).not.toContain('<ol>');
});

test('launch form keeps its action visible while its fields scroll inside the workbench', () => {
  expect(LAUNCH_SOURCE).toContain('story-workspace-dream-launch__form-body');
  expect(LAUNCH_SOURCE).toContain('story-workspace-dream-launch__form-actions');
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-launch__form\s*\{[^}]*grid-template-rows: minmax\(0, 1fr\) auto;[^}]*overflow: hidden;/s);
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-launch__form-body\s*\{[^}]*overflow-y: auto;/s);
});
