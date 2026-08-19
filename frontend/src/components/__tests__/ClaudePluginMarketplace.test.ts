// [Input] ClaudePlugin admin source/styles/API, Story Workspace Work/Layout wiring, and Marketplace interaction design.
// [Output] Lock the three-action menu, real install transport, no-catalog fail-closed state, focus behavior, and responsive presentation.
// [Pos] Source-contract regression for ClaudePlugin Marketplace add scope.
// [Sync] 2026-08-19: add create-menu, accessibility, production-call, and no-fake-catalog assertions.

// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { readFileSync } from 'node:fs';
// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

declare const process: { cwd(): string };

const read = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8');
const PAGE = read('src/components/claude-plugin-admin/ClaudePluginAdminPage.tsx');
const STYLES = read('src/components/claude-plugin-admin/ClaudePluginAdminPage.css');
const API = read('src/api/claudePluginAdminApi.ts');
const SETTINGS = read('src/pages/story-workspace/StoryWorkspaceSettingsPage.tsx');
const LAYOUT = read('src/components/story-workspace/layout/StoryWorkspaceLayout.tsx');
const DESIGN = read('../docs/design/deck-plugin/claude-plugin-marketplace-add.md');

test('Work / Plugins keeps the shared Settings layout and mounts one ClaudePlugin manager', () => {
  expect(SETTINGS).toContain("workTab === 'plugins'");
  expect(SETTINGS).toContain('<ClaudePluginAdminPage />');
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
  expect(PAGE).toContain('installClaudePlugin({ packageSpec: trimmed })');
  expect(PAGE).toContain('getClaudePluginOperation(trackedOperationId)');
  expect(PAGE).toContain('Boolean(installResult.permissions?.can_manage_shared_plugins)');
  expect(PAGE).toContain("setActiveDialog('operations')");
  expect(PAGE).toContain('setInstallError(errorMessage(reason))');
  expect(PAGE).not.toContain('forkDeck');
});

test('Marketplace remains a truthful no-catalog capability state', () => {
  expect(PAGE).toContain('Marketplace 目录暂不可用');
  expect(PAGE).toContain('当前服务没有可浏览的 Marketplace 插件目录 API');
  expect(PAGE).toContain('改用安装');
  expect(API).not.toMatch(/marketplace-catalog|marketplace\/catalog|marketplaces\/plugins/i);
  expect(DESIGN).toContain('没有 Marketplace catalog DTO/API');
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
  expect(PAGE).toContain('menuTriggerRef.current?.focus()');
  expect(PAGE).toContain("event.key !== 'Tab'");
  expect(STYLES).toContain('min-height: 44px');
  expect(STYLES).toContain('@media (max-width: 640px)');
  expect(STYLES).toContain('max-width: calc(100vw - 2rem)');
  expect(STYLES).toContain('outline: 2px solid var(--color-border-focus)');
});
