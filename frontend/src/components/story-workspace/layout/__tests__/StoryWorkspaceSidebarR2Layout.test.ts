// [Input] Story Workspace sidebar, router, App Decks handoff and subscription page sources.
// [Output] Node seam for R2 navigation labels, concrete Decks reuse and static subscription boundary.
// [Pos] Story Workspace sidebar R2 Red/Green regression test.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source only; browser app omits Node types.
import { readFileSync } from 'node:fs';

const SIDEBAR = readFileSync(new URL('../StoryWorkspaceSidebar.tsx', import.meta.url), 'utf8');
const ROUTER = readFileSync(new URL('../../../../router/story-workspace.tsx', import.meta.url), 'utf8');
const APP = readFileSync(new URL('../../../../App.tsx', import.meta.url), 'utf8');
const PATHS = readFileSync(new URL('../../../../router/storyWorkspacePath.ts', import.meta.url), 'utf8');
const SUBSCRIPTION = readFileSync(new URL('../../../../pages/story-workspace/StoryWorkspaceSubscriptionPage.tsx', import.meta.url), 'utf8');
const SETTINGS = readFileSync(new URL('../../../../pages/story-workspace/StoryWorkspaceSettingsPage.tsx', import.meta.url), 'utf8');
const DREAM_LAUNCH = readFileSync(new URL('../../../../pages/story-workspace/StoryWorkspaceDreamLaunch.tsx', import.meta.url), 'utf8');

test('sidebar replaces legacy resource management with Dream, Decks and subscription', () => {
  expect(SIDEBAR).toContain("label: 'Dream'");
  expect(SIDEBAR).toContain("label: 'Decks'");
  expect(SIDEBAR).toContain("label: '订阅'");
  expect(SIDEBAR).not.toContain('故事管理');
  expect(SIDEBAR).not.toContain('角色管理');
  expect(SIDEBAR).not.toContain('场景管理');
});

test('Decks stays inside the workspace and projects the existing DeckManager into its main region', () => {
  expect(PATHS).toContain("decks: '/story-workspace/decks'");
  expect(ROUTER).toContain("case 'decks':");
  expect(ROUTER).toContain('decksContent: ReactNode;');
  expect(ROUTER).toContain('{decksContent}</div>');
  expect(ROUTER).toContain('story-workspace-decks-surface');
  expect(APP).toContain('<StoryWorkspaceRouter\n            decksContent={storyWorkspaceDeckManager}');
  expect(APP).toContain('onOpenDreamWithDeck={handleOpenDreamWithDeck}');
  expect(APP).not.toContain('handleStoryWorkspaceOpenDecks');
  expect(SIDEBAR).toContain("label: 'Decks', path: '/story-workspace/decks'");
  expect(SIDEBAR).not.toContain("action: 'open-decks'");
  expect(SIDEBAR).not.toContain('onOpenDecks');
  expect(SIDEBAR).toContain('aria-current={isCurrent ?');
  expect(SIDEBAR).not.toContain('DeckManager');
});

test('sidebar theme switch is a footer utility that follows the shared theme owner', () => {
  expect(SIDEBAR).toContain("import { getTheme, onThemeChange, toggleTheme } from '../../../utils/theme'");
  expect(SIDEBAR).toContain("useState(() => getTheme() === 'dark')");
  expect(SIDEBAR).toContain('return onThemeChange((resolved) =>');
  expect(SIDEBAR).toContain('toggleTheme();');
  expect(SIDEBAR).toContain("aria-label={isDark ? '切换到浅色' : '切换到深色'}");
  expect(SIDEBAR).toContain("title={isDark ? '切换到浅色' : '切换到深色'}");
  const footerMarkup = SIDEBAR.slice(
    SIDEBAR.indexOf('<footer className="story-workspace-sidebar__footer">'),
    SIDEBAR.indexOf('</footer>'),
  );
  expect(footerMarkup.indexOf('story-workspace-sidebar__theme-button')).toBeLessThan(
    footerMarkup.indexOf('story-workspace-sidebar__settings-button'),
  );
  expect(SIDEBAR).not.toContain('localStorage');
});

test('Dream keeps its durable recent list while subscription stays a static, accessible three-plan page', () => {
  expect(PATHS).toContain("subscription: '/story-workspace/subscription'");
  expect(ROUTER).toContain("case 'subscription'");
  expect(DREAM_LAUNCH).toContain('最近的 Dream');
  expect(SUBSCRIPTION).toContain('Free');
  expect(SUBSCRIPTION).toContain('Dream');
  expect(SUBSCRIPTION).toContain('is Dreaming');
  expect(SUBSCRIPTION).toContain('aria-labelledby');
  expect(SUBSCRIPTION).not.toContain('fetch(');
  expect(SUBSCRIPTION).not.toContain('apiUrl');
});

test('subscription and Settings stay in the workspace sidebar while their pages render in the right main region', () => {
  const footerMarkup = SIDEBAR.slice(
    SIDEBAR.indexOf('<footer className="story-workspace-sidebar__footer">'),
    SIDEBAR.indexOf('</footer>'),
  );
  expect(footerMarkup.indexOf('subscriptionItem.path')).toBeLessThan(
    footerMarkup.indexOf('story-workspace-sidebar__settings-button'),
  );
  expect(SIDEBAR).toContain("onNavigate('/story-workspace/settings')");
  expect(ROUTER).toContain("case 'settings':");
  expect(ROUTER).toContain('renderSettings(storyWorkspaceSettingsSectionForRoute(match.route), onNavigate)');
  expect(APP).not.toContain("setCurrentView('settings')");
  expect(SETTINGS).toContain('<section aria-labelledby=');
  expect(SETTINGS).toContain('className="story-workspace-settings__section"');
  expect(SETTINGS).toContain('role="region"');
});
