// [Input] Production StoryWorkspaceSettingsPage and isolated public API fixtures.
// [Output] Local Chrome checks of workflow scope, removal of the runtime category, detail recovery and narrow layout.
// [Pos] Provider-free Settings UI regression; no model, plugin installation or database writes.
// [Sync] 2026-10-10: exercise the actual Settings mount rather than a duplicate plugin page.

import { expect, test } from '@playwright/test';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';

test.use({ channel: 'chrome' });

/* Impact brief:
 * Changes: workflow purpose and catalog/detail presentation in Settings.
 * Must remain unchanged: separate Claude Code Plugins component and permission-controlled actions.
 * Not in scope: Project identity/content, Episode content, canonical stories files,
 * Run-private .dream publication, after-turn Hook, PostgreSQL projection, Agent and Thread.
 * These facts have no write/sync operation in this UI-only scenario.
 */

const PLUGIN_ID = 'fixture.story-workflow';
const VERSION = '1.2.3';
const HARNESS_PATH = '/deck-workflow-settings-technical';
const runtimeDependency = {
  claude_code_plugin_id: 'fixture-execution-dependency',
  resolved_version: VERSION,
  declaration_status: 'declared',
  materialization_status: 'materialized',
  activation_status: 'loadable',
};
const installation = {
  deck_plugin_installation_id: 'dpi_fixture', deck_plugin_id: PLUGIN_ID,
  display_name: 'Dream Story Workflow', deck_plugin_version: VERSION,
  installed_versions: [VERSION], default_version: VERSION, status: 'ready',
  source: { type: 'controlled', label: 'Admin 工作流目录' },
  runtime_readiness: { declaration_status: 'declared', materialization_status: 'materialized', activation_status: 'loadable' },
  compatibility: { status: 'compatible', passed: true, effective_capabilities: [] },
  health_status: 'healthy', runtime_plugins: [runtimeDependency], is_system: true,
};

const moduleSource = `
  import React from 'react';
  import { createRoot } from 'react-dom/client';
  import i18n from '/app/_dream/i18n.ts';
  import { loadBrowserSession } from '/app/_dream/lib/browserSession.ts';
  import { StoryWorkspaceSettingsPage } from '/app/_dream/views/story-workspace/StoryWorkspaceSettingsPage.tsx';
  import '/app/_dream/styles/tokens.css';
  import '/app/_dream/index.css';
  await loadBrowserSession();
  await i18n.changeLanguage('zh');
  document.documentElement.setAttribute('data-theme', 'light');
  createRoot(document.getElementById('root')).render(React.createElement(StoryWorkspaceSettingsPage, {
    activeSection: 'settings-plugins', currentLanguage: 'zh', languageCodes: ['zh', 'en'],
    onLanguageChange: () => {}, showEnergyBar: false, onEnergyBarChange: () => {}, onNavigate: () => {},
  }));
`;

test('Settings explains the story workflow and opens only workflow-owned details, including recovery and narrow layout', async ({ page }) => {
  const errors: string[] = [];
  const unexpected: string[] = [];
  const writes: string[] = [];
  const expectedHttpFailures: string[] = [];
  let failCatalog = true;
  let failDetail = true;
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() !== 'error') return;
    if (message.text().includes('503 (Service Unavailable)')) expectedHttpFailures.push(message.text());
    else errors.push(message.text());
  });
  page.on('requestfailed', request => errors.push(`${request.failure()?.errorText} ${request.url()}`));
  await page.route('**/auth/session', route => route.fulfill({ json: {
    user: { id: '1', email: 'workflow@example.test', display_name: 'Workflow fixture', avatar_url: null, role: 'user', created_at: null },
    csrf_token: 'w'.repeat(43),
  } }));
  await page.route('**/api/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith('/api/')) return route.continue();
    if (request.method() !== 'GET') {
      writes.push(`${request.method()} ${path}`);
      return route.fulfill({ status: 501, json: { error: 'UI-only fixture forbids mutations' } });
    }
    if (path === '/api/deck-plugins/installations') {
      if (failCatalog) return route.fulfill({ status: 503, json: { error: { summary: '工作流目录暂不可用' } } });
      return route.fulfill({ json: { installations: [installation], runtime_plugins: [runtimeDependency], permissions: { can_manage: false } } });
    }
    if (path === `/api/deck-plugins/${PLUGIN_ID}/versions/${VERSION}`) {
      if (failDetail) return route.fulfill({ status: 503, json: { error: { summary: '工作流详情暂不可用' } } });
      return route.fulfill({ json: installation });
    }
    if (path === `/api/deck-plugins/${PLUGIN_ID}/runtime-readiness`) return route.fulfill({ json: installation.runtime_readiness });
    if (path === '/api/claude-plugins/installations') return route.fulfill({ json: { installations: [], permissions: { can_manage_shared_plugins: false } } });
    if (path === '/api/claude-plugins/operations') return route.fulfill({ json: { operations: [] } });
    unexpected.push(`${request.method()} ${path}`);
    return route.fulfill({ status: 501, json: { error: 'Unexpected fixture request' } });
  });

  const server = await createServer({
    root: fileURLToPath(new URL('../', import.meta.url)), configFile: false, logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, strictPort: true },
    plugins: [{
      name: 'deck-workflow-settings-owned-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== HARNESS_PATH) return next();
          try {
            response.setHeader('Content-Type', 'text/html');
            response.end(await vite.transformIndexHtml(HARNESS_PATH,
              '<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/workflow-settings-fixture.js"></script></body></html>'));
          } catch (error) { next(error as Error); }
        });
      },
      resolveId: id => id === '/workflow-settings-fixture.js' ? '\0workflow-settings-fixture.js' : null,
      load: id => id === '\0workflow-settings-fixture.js' ? moduleSource : null,
    }],
  });
  await server.listen();
  try {
    const address = server.httpServer!.address();
    if (!address || typeof address === 'string') throw new Error('Workflow fixture port unavailable');
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(`http://127.0.0.1:${address.port}${HARNESS_PATH}`);
    const workflow = page.getByRole('region', { name: 'Deck 工作流插件', exact: true });
    await expect(workflow.getByRole('heading', { name: 'Dream Story Workflow', exact: true })).toBeVisible();
    await expect(workflow.getByText('项目准备', { exact: true })).toBeVisible();
    await expect(workflow.getByText('分集创作', { exact: true })).toBeVisible();
    await expect(workflow.getByRole('tab')).toHaveCount(0);
    await expect(workflow).not.toContainText('ClaudeAgent');
    await expect(workflow).not.toContainText('Paperclip');
    await expect(workflow.getByRole('button', { name: '安装工作流', exact: true })).toHaveCount(0);
    await expect(workflow.getByRole('alert')).toContainText('插件目录暂不可用');
    failCatalog = false;
    await workflow.getByRole('button', { name: '重试', exact: true }).click();
    await expect(workflow.locator('.plugin-admin-list-item')).toHaveCount(1);
    await expect(workflow).not.toContainText(runtimeDependency.claude_code_plugin_id);
    await expect(page.locator('.claude-plugin-admin__section-label')).toHaveText('Claude Code Plugins');
    await page.screenshot({ path: 'output/playwright/deck-workflow-settings-wide.png', fullPage: true });

    await workflow.getByRole('button', { name: '工作流详情', exact: true }).click();
    const dialog = page.getByRole('dialog', { name: 'Dream Story Workflow', exact: true });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('详情刷新失败');
    failDetail = false;
    await dialog.getByRole('button', { name: '重试', exact: true }).click();
    await expect(dialog.getByText('详情刷新失败', { exact: false })).toHaveCount(0);
    await expect(dialog).not.toContainText(runtimeDependency.claude_code_plugin_id);
    await expect(dialog.getByRole('tab')).toHaveCount(2);
    await dialog.getByRole('tab', { name: '状态与记录', exact: true }).click();
    await expect(dialog.getByRole('heading', { name: '工作流状态', exact: true })).toBeVisible();
    await dialog.getByRole('button', { name: '关闭插件详情', exact: true }).click();

    await page.setViewportSize({ width: 390, height: 844 });
    await workflow.getByRole('heading', { name: 'Deck 工作流插件', exact: true }).scrollIntoViewIfNeeded();
    await expect(workflow.getByText('分集创作', { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await page.screenshot({ path: 'output/playwright/deck-workflow-settings-narrow.png', fullPage: true });
    await workflow.getByRole('button', { name: '工作流详情', exact: true }).click();
    await expect(dialog).toBeVisible();
    expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
    await dialog.getByRole('button', { name: '关闭插件详情', exact: true }).click();
    expect(writes).toEqual([]);
    expect(unexpected).toEqual([]);
    expect(errors).toEqual([]);
    expect(expectedHttpFailures.length).toBeGreaterThanOrEqual(2);
  } catch (error) {
    throw new Error(`Workflow Settings UI failed: ${JSON.stringify({ errors, unexpected, writes, body: (await page.locator('body').innerText()).slice(0, 1800) })}`, { cause: error });
  } finally {
    await server.close();
  }
});
