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

test('no-run Dream mounts its own launch module instead of Chat children', () => {
  expect(PAGE_SOURCE).toContain('<StoryWorkspaceDreamLaunch onNavigate={onNavigate} />');
  expect(PAGE_SOURCE).not.toContain('children: ReactNode');
  expect(PAGE_SOURCE).not.toContain('story-workspace-dream-launch__chat');
  expect(LAUNCH_SOURCE).toContain('发起 Dream');
  expect(LAUNCH_SOURCE).toContain('listDecks');
  expect(LAUNCH_SOURCE).toContain('role="alert"');
});

test('router and Story Workspace App branch have no dreamContent Chat seam', () => {
  expect(ROUTER_SOURCE).not.toContain('dreamContent');
  expect(ROUTER_SOURCE).not.toContain('type ReactNode');

  const storyWorkspaceStart = APP_SOURCE.indexOf("{currentView === 'story-workspace' && (");
  const storyWorkspaceBranch = APP_SOURCE.slice(
    storyWorkspaceStart,
    APP_SOURCE.indexOf("{currentView === 'writing' && (", storyWorkspaceStart),
  );
  expect(storyWorkspaceBranch).toContain('<StoryWorkspaceRouter');
  expect(storyWorkspaceBranch).not.toContain('<ChatView');
  expect(storyWorkspaceBranch).not.toContain('dreamContent=');
});

test('launch page keeps one primary action and no business failure branches', () => {
  expect(LAUNCH_SOURCE.match(/>发起 Dream</g)).toHaveLength(1);
  expect(LAUNCH_SOURCE).not.toContain('驳回');
  expect(LAUNCH_SOURCE).not.toContain('归档');
  expect(LAUNCH_SOURCE).not.toContain('重试');
});
