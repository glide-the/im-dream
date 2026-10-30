// [Sync] 2026-10-29: retain existing ownership contracts at the extracted shared state/presentation paths; Web DOM assertions remain.
// [Input] ClaudePlugin admin source/styles/API, Story Workspace Work/Layout wiring, and Marketplace interaction design.
// [Output] Lock both plugin managers plus the Claude global Marketplace install, fail-closed capability, focus, and responsive presentation.
// [Pos] Source-contract regression for ClaudePlugin Marketplace add scope.
// [Sync] 2026-09-05: read the Settings view from the relocated non-framework app/_dream/views tree.
// [Sync] 2026-08-19: assert the Admin-approved catalog DTO, entry-ID install, four-stage UX, and remote lineage copy.

// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { readFileSync } from 'node:fs';
// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

declare const process: { cwd(): string };

const read = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8');
const PAGE = read('app/_dream/components/claude-plugin-admin/ClaudePluginAdminPage.tsx');
const STATE = read('app/_dream/hooks/useClaudePluginAdmin.ts');
const PRESENTATION = read('app/_dream/components/claude-plugin-admin/claudePluginPresentation.ts');
const STYLES = read('app/_dream/components/claude-plugin-admin/ClaudePluginAdminPage.css');
const API = read('app/_dream/api/claudePluginAdminApi.ts');
const SETTINGS = read('app/_dream/views/story-workspace/StoryWorkspaceSettingsPage.tsx');
const LAYOUT = read('app/_dream/components/story-workspace/layout/StoryWorkspaceLayout.tsx');
const DESIGN = read('../docs/design/deck-plugin/claude-plugin-marketplace-add.md');

test('Work / Plugins keeps the shared Settings layout and mounts both plugin domains', () => {
  expect(SETTINGS).toContain("workTab === 'plugins'");
  expect(SETTINGS).toContain('<PluginAdminPage isMobile={isMobile} />');
  expect(SETTINGS).toContain('<ClaudePluginAdminPage />');
  expect(SETTINGS).toContain('className="story-workspace-work__plugin-stack"');
  expect(SETTINGS).toContain('className="story-workspace-work__toolbar"');
  expect(LAYOUT).toContain('data-story-workspace-region="main"');
  expect(PAGE).toContain('className="claude-plugin-admin__topbar"');
  expect(PAGE).toContain('aria-labelledby="claude-plugin-admin-title"');
});

test('one create menu owns install, Marketplace, and recent-operation entry points in order', () => {
  const installIndex = PAGE.indexOf('<span>安装</span>');
  const marketplaceIndex = PAGE.indexOf('<span>从 Marketplace 添加</span>');
  const operationsIndex = PAGE.indexOf('<span>最近操作</span>');
  expect(installIndex).toBeGreaterThan(-1);
  expect(marketplaceIndex).toBeGreaterThan(installIndex);
  expect(operationsIndex).toBeGreaterThan(marketplaceIndex);
  expect(PAGE).toContain('aria-haspopup="menu"');
  expect(PAGE).toContain('aria-expanded={menuOpen}');
  expect(PAGE).toContain('role="menu"');
  expect(PAGE).toContain("openDialog('install')");
  expect(PAGE).toContain("openDialog('marketplace')");
  expect(PAGE).toContain("openDialog('operations')");
  expect(PAGE).not.toContain('Install Plugin');
  expect(PAGE).not.toContain('最近操作（真实 operation ID / argv / exit code）');
});

test('manual install preserves the existing production call and server-owned permission', () => {
  expect(API).toContain("'/api/claude-plugins/install'");
  expect(API).toContain('can_manage_shared_plugins?: boolean');
  expect(STATE).toContain('installClaudePlugin({ packageSpec: trimmed },transport)');
  expect(STATE).toContain('getClaudePluginOperation(trackedOperationId,transport)');
  expect(STATE).toContain('Boolean(installResult.permissions?.can_manage_shared_plugins)');
  expect(STATE).toContain("setActiveDialog('operations')");
  expect(STATE).toContain('setInstallError(reportError(reason))');
  expect(PAGE).not.toContain('forkDeck');
});

test('Marketplace uses the global catalog and the existing production install operation', () => {
  expect(API).toContain("'/api/claude-plugins/marketplace'");
  expect(API).toContain('marketplace_entry_id');
  expect(API).toContain("scope: 'platform-global'");
  expect(PRESENTATION).toContain("{ id: 'select', label: '选择插件' }");
  expect(PRESENTATION).toContain("{ id: 'confirm', label: '确认安装' }");
  expect(PRESENTATION).toContain("{ id: 'installing', label: '正在安装' }");
  expect(PRESENTATION).toContain("{ id: 'result', label: '可以使用' }");
  expect(STATE).toContain('installClaudePlugin({ marketplaceEntryId: entry.id },transport)');
  expect(PAGE).toContain('批准 commit');
  expect(PAGE).toContain('固定 ref');
  expect(PAGE).toContain('revision.requested_ref');
  expect(PAGE).toContain('内容摘要');
  expect(PAGE).toContain('revision.plugin_digest');
  expect(PAGE).toContain('发生远端漂移时不会继续安装');
  expect(PAGE).toContain('Marketplace 目录暂不可用');
  expect(PAGE).toContain('暂无可添加插件');
  expect(DESIGN).toContain('platform-global');
  expect(DESIGN).toContain('fail-closed');
});

test('menu and dialogs expose keyboard, focus, ARIA, and narrow-screen contracts', () => {
  expect(PAGE).toContain("event.key === 'ArrowDown'");
  expect(PAGE).toContain("event.key === 'ArrowUp'");
  expect(PAGE).toContain("event.key === 'Home'");
  expect(PAGE).toContain("event.key === 'End'");
  expect(PAGE).toContain("event.key === 'Escape'");
  expect(PAGE).toContain('aria-modal="true"');
  expect(PAGE).toContain('role="dialog"');
  expect(PAGE).toContain('useLayoutEffect');
  expect(PAGE).toContain('menuTriggerRef.current?.focus()');
  expect(PAGE).toContain("event.key !== 'Tab'");
  expect(STYLES).toContain('min-height: 44px');
  expect(STYLES).toContain('@media (max-width: 640px)');
  expect(STYLES).toContain('max-width: calc(100vw - 2rem)');
  expect(STYLES).toContain('outline: 2px solid var(--color-border-focus)');
});
