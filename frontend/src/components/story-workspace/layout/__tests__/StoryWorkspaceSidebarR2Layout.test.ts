// [Input] Story Workspace sidebar, router, App Decks handoff and subscription page sources.
// [Output] Node seam for the current Chat/Dream/Decks navigation, retained legacy
//          routes, concrete Decks reuse, and the Product BFF subscription boundary.
// [Pos] Story Workspace sidebar R2 Red/Green regression test.
// [Sync] 2026-08-14: assert Writing, Timeline, and Analysis are hidden from the
//                    sidebar while their route implementations remain intact.
// [Sync] 2026-08-14: assert the visible primary order is Chat, Dream, Decks.

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

test('sidebar exposes only Chat, Dream, and Decks in that order', () => {
  expect(SIDEBAR).toContain("dream: '/story-workspace/dream'");
  expect(SIDEBAR).toContain("decks: '/story-workspace/decks'");
  expect(SIDEBAR).toContain("chat: '/story-workspace/chat'");
  expect(SIDEBAR).not.toContain("writing: '/story-workspace/writing'");
  expect(SIDEBAR).not.toContain("timeline: '/story-workspace/timeline'");
  expect(SIDEBAR).not.toContain("analysis: '/story-workspace/analysis'");
  expect(SIDEBAR).not.toContain("view: 'writing'");
  expect(SIDEBAR).not.toContain("view: 'timeline'");
  expect(SIDEBAR).not.toContain("view: 'analysis'");
  const primaryNavigation = SIDEBAR.slice(
    SIDEBAR.indexOf('<nav aria-label="Story Workspace 导航"'),
    SIDEBAR.indexOf('</nav>'),
  );
  expect(primaryNavigation.indexOf("view: 'chat'")).toBeLessThan(
    primaryNavigation.indexOf("view: 'dream'"),
  );
  expect(primaryNavigation.indexOf("view: 'dream'")).toBeLessThan(
    primaryNavigation.indexOf("view: 'decks'"),
  );
  expect(SIDEBAR).toContain('const Icon = item.icon as IconType;');
  expect(SIDEBAR).toContain('story-workspace-sidebar__icon');
  expect(SIDEBAR).toContain('aria-label={collapsed ? item.label : undefined}');
  expect(SIDEBAR).not.toContain("label: '订阅'");
  expect(SIDEBAR).not.toContain('故事管理');
  expect(SIDEBAR).not.toContain('角色管理');
  expect(SIDEBAR).not.toContain('场景管理');
  expect(SIDEBAR).not.toContain('创作者工作台');
  expect(DREAM_LAUNCH).toContain('id="dream-home-title">Dream');
});

test('Decks stays inside the workspace and projects the existing DeckManager into its main region', () => {
  expect(PATHS).toContain("decks: '/story-workspace/decks'");
  expect(ROUTER).toContain("case 'decks':");
  expect(ROUTER).toContain('decksContent: ReactNode;');
  expect(ROUTER).toContain('{decksContent}</div>');
  expect(ROUTER).toContain('story-workspace-decks-surface');
  expect(APP).toContain('<StoryWorkspaceRouter\n            decksContent={storyWorkspaceDeckManager}');
  expect(APP).toContain('onChatWithDeck={handleChatWithDeck}');
  expect(APP).not.toContain('onOpenDreamWithDeck');
  expect(APP).not.toContain('handleStoryWorkspaceOpenDecks');
  expect(SIDEBAR).toContain("decks: '/story-workspace/decks'");
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

test('Dream keeps its durable My Dream list while subscription uses the real monthly Token boundary', () => {
  expect(PATHS).toContain("subscription: '/story-workspace/subscription'");
  expect(ROUTER).toContain("case 'subscription'");
  expect(DREAM_LAUNCH).toContain('我的 Dream');
  expect(SUBSCRIPTION).toContain('useStoryWorkspaceSubscription');
  expect(SUBSCRIPTION).toContain('Dream · Subscription');
  expect(SUBSCRIPTION).toContain("{ id: 'info', label: '订阅信息' }");
  expect(SUBSCRIPTION).toContain("{ id: 'allowance', label: '我的额度' }");
  expect(SUBSCRIPTION).toContain("{ id: 'plans', label: '可选套餐' }");
  expect(SUBSCRIPTION).toContain('aria-labelledby');
  expect(SUBSCRIPTION).not.toContain('STORY_WORKSPACE_DREAM_PLANS');
  expect(SUBSCRIPTION).not.toContain('订阅功能即将开放');
  expect(SUBSCRIPTION).not.toContain('fetch(');
  expect(SUBSCRIPTION).not.toContain('apiUrl');
  expect(SUBSCRIPTION).not.toContain('localStorage');
});

test('subscription moves into the focused Settings layout', () => {
  const footerMarkup = SIDEBAR.slice(
    SIDEBAR.indexOf('<footer className="story-workspace-sidebar__footer">'),
    SIDEBAR.indexOf('</footer>'),
  );
  expect(footerMarkup).not.toContain('subscriptionItem');
  expect(footerMarkup).not.toContain("onNavigate('/story-workspace/subscription')");
  expect(SIDEBAR).toContain("onNavigate('/story-workspace/settings')");
  expect(SETTINGS).toContain("id: 'settings-subscription'");
  expect(SETTINGS).toContain("path: '/story-workspace/subscription'");
  expect(SETTINGS).toContain('StoryWorkspaceSubscriptionPage');
  expect(ROUTER).toContain("case 'settings':");
  expect(ROUTER).toContain("case 'subscription':");
  expect(ROUTER).toContain('renderSettings(storyWorkspaceSettingsSectionForRoute(match.route), onNavigate)');
  expect(APP).not.toContain("setCurrentView('settings')");
  expect(SETTINGS).toContain('<section aria-labelledby=');
  expect(SETTINGS).toContain('className="story-workspace-settings__section"');
  expect(SETTINGS).toContain('role="region"');
  expect(SETTINGS).toContain('aria-label="返回应用"');
  expect(SETTINGS).toContain("onNavigate('/story-workspace/dream')");
  expect(ROUTER).toContain('showSidebar={!isSettingsRoute}');
  expect(ROUTER).toContain("|| activeRoute === 'subscription'");
  expect(ROUTER).toContain('workflowContext={isDreamRoute || isSettingsRoute');
});

test('legacy page links render through the workspace router main region', () => {
  expect(PATHS).toContain("writing: '/story-workspace/writing'");
  expect(PATHS).toContain("timeline: '/story-workspace/timeline'");
  expect(PATHS).toContain("analysis: '/story-workspace/analysis'");
  expect(PATHS).toContain("chat: '/story-workspace/chat'");
  expect(ROUTER).toContain('legacyContent');
  expect(ROUTER).toContain("case 'writing':");
  expect(ROUTER).toContain("case 'chat':");
  expect(APP).toContain('legacyContent={{');
  expect(APP).toContain('storyWorkspaceLegacyView');
  expect(APP).toContain('onRouteChange={handleStoryWorkspaceRouteChange}');
  expect(APP).toContain('Start writing...');
  expect(APP).not.toContain('onGlobalNavigate={handleAppViewChange}');
});

test('workspace user area owns the floating logout menu', () => {
  expect(SIDEBAR).toContain('const { user, logout } = useAuth();');
  expect(SIDEBAR).toContain('story-workspace-sidebar__user-menu');
  expect(SIDEBAR).toContain('story-workspace-sidebar__logout');
  expect(SIDEBAR).toContain('logout();');
});
