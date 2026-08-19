// [Input] Running frontend public entry point plus production-shaped intercepted ClaudePlugin API fixtures.
// [Output] Verify Work / Plugins auth transport, global Marketplace four-stage install, fail-closed recovery, and responsive placement.
// [Pos] Technical ClaudePlugin Settings browser journey; it never calls the normal backend or mutates business data.
// [Sync] 2026-08-19: cover Comfy entry install, capability recovery, immediate dialog focus, and narrow layout.

import { expect, test, type Request as PlaywrightRequest } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chromium' });

test('Work / Plugins installs an approved Comfy Marketplace entry through the accessible create menu', async ({ page }) => {
  const token = 'claude-plugin-settings-technical-token';
  const pluginRequests = new Map<string, PlaywrightRequest>();
  const pluginResponses = new Map<string, number>();
  const pluginMutationRequests: string[] = [];
  const retiredDeckPluginRequests: string[] = [];
  const unexpectedApiRequests: string[] = [];
  const diagnostics: string[] = [];
  let marketplaceAvailable = true;
  let marketplaceInstallBody: unknown = null;
  page.on('console', (message) => {
    const expectedCapabilityFailure = !marketplaceAvailable
      && message.text().includes('503 (Service Unavailable)');
    if (message.type() === 'error' && !message.text().includes('react-grab.com') && !expectedCapabilityFailure) diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (failedRequest) => {
    const url = failedRequest.url();
    if (!url.includes('react-grab.com') && !url.includes('fonts.googleapis.com') && !url.includes('fonts.gstatic.com')) {
      diagnostics.push(`${failedRequest.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  page.on('request', (outgoing) => {
    const url = outgoing.url();
    if (outgoing.method() === 'GET' && (
      url.includes('/api/claude-plugins/installations') || url.includes('/api/claude-plugins/operations') || url.includes('/api/claude-plugins/marketplace')
    )) {
      pluginRequests.set(url.replace(/\?.*$/, ''), outgoing);
    }
    if (outgoing.method() !== 'GET' && url.includes('/api/claude-plugins/')) {
      pluginMutationRequests.push(url);
    }
    if (url.includes('/api/deck-plugins/')) retiredDeckPluginRequests.push(url);
  });
  page.on('response', (incoming) => {
    const url = incoming.url();
    if (incoming.request().method() === 'GET' && (
      url.includes('/api/claude-plugins/installations') || url.includes('/api/claude-plugins/operations') || url.includes('/api/claude-plugins/marketplace')
    )) {
      pluginResponses.set(url.replace(/\?.*$/, ''), incoming.status());
    }
  });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (!url.pathname.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/me') {
      await route.fulfill({
        json: {
          user_id: 'claude-plugin-settings-technical-user',
          email: 'claude-plugin-settings@example.test',
          display_name: 'Claude Plugin Settings Technical User',
          role: 'user',
        },
      });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/claude-plugins/installations') {
      await route.fulfill({
        json: {
          installations: [],
          permissions: { can_manage_shared_plugins: true },
        },
      });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/claude-plugins/operations') {
      await route.fulfill({ json: { operations: [] } });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/claude-plugins/marketplace') {
      if (!marketplaceAvailable) {
        await route.fulfill({
          status: 503,
          json: {
            error: {
              code: 'CLAUDE_PLUGIN_MARKETPLACE_CAPABILITY_MISSING',
              message: 'The global ClaudePlugin Marketplace capability is not available.',
            },
          },
        });
        return;
      }
      await route.fulfill({
        json: {
          scope: 'platform-global',
          permissions: { can_install_shared_plugins: true },
          entries: [{
            id: 'cpme_comfy_cloud',
            package_name: 'comfy-cloud',
            marketplace_name: 'comfy-skills',
            package_spec: 'comfy-cloud@comfy-skills',
            display_name: 'comfy-cloud',
            description: 'Comfy Cloud in Claude Code: hosted MCP plus generation commands.',
            version: '0.1.0',
            homepage: 'https://docs.comfy.org/cloud/mcp',
            component_inventory: { skills: 0, commands: 12, agents: 0, mcpServers: 1 },
            compatibility: {},
            revision: {
              id: 'cpmr_comfy',
              commit_sha: '4a1db97094bd30da911a72110d60bc4464744367',
              marketplace_manifest_sha256: '198b653a9d8990af2c6afa94a66d5b7db96e715a9466ed3bb98d2e49a82ad06e',
              plugin_manifest_sha256: '3fe35a29324ec64f5a661f51a8778057168b63bbfe278bcbffba8df471d64dc8',
              plugin_digest: 'sha256:a63778a6c4451006c66c31e308a15d717f8909b82252f077ab240bd30adf25f4',
              requested_ref: null,
            },
            marketplace: {
              id: 'cpm_comfy',
              display_name: 'Comfy Skills',
              remote_url: 'https://github.com/Comfy-Org/comfy-skills',
            },
            installation: null,
          }],
        },
      });
      return;
    }
    if (request.method() === 'POST' && url.pathname === '/api/claude-plugins/install') {
      marketplaceInstallBody = request.postDataJSON();
      await route.fulfill({
        status: 202,
        json: {
          accepted: true,
          operation_id: 'cop_comfy_install',
          package_spec: 'comfy-cloud@comfy-skills',
          marketplace_entry_id: 'cpme_comfy_cloud',
        },
      });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/claude-plugins/operations/cop_comfy_install') {
      await route.fulfill({
        json: {
          id: 'cop_comfy_install',
          operation_kind: 'install',
          requested_package_spec: 'comfy-cloud@comfy-skills',
          marketplace_entry_id: 'cpme_comfy_cloud',
          status: 'ready',
          phase: 'ready',
          progress: 100,
          message: 'Installed comfy-cloud@comfy-skills 0.1.0',
          executable: '/usr/local/bin/claude',
          argv_json: '["claude","plugin","install","comfy-cloud@comfy-skills"]',
          cwd: '/managed/install-workspace',
          cli_version: '2.1.220',
          exit_code: 0,
          evidence_path: '/managed/operations/cop_comfy_install/operation.json',
          installation_id: 'cpi_comfy',
          error_code: null,
          error_summary: null,
          created_at: '2026-08-19T00:00:00Z',
          updated_at: '2026-08-19T00:00:01Z',
          finished_at: '2026-08-19T00:00:01Z',
        },
      });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/default-voices') {
      await route.fulfill({ json: {} });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/sessions') {
      await route.fulfill({ json: { sessions: [] } });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/sessions/range') {
      await route.fulfill({ json: { sessions: [] } });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/sessions/events') {
      await route.fulfill({ body: ': connected\n\n', contentType: 'text/event-stream' });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/pictures/range') {
      await route.fulfill({ json: { pictures: [] } });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/preferences') {
      await route.fulfill({ json: { first_login_completed: true, timezone: 'Asia/Shanghai' } });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/decks') {
      await route.fulfill({ json: { decks: [] } });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/version') {
      await route.fulfill({ json: { version: 'technical-e2e' } });
      return;
    }
    unexpectedApiRequests.push(`${request.method()} ${url.pathname}`);
    await route.fulfill({ status: 501, json: { error: { code: 'UNEXPECTED_E2E_API' } } });
  });

  await page.addInitScript((authToken) => {
    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('migration_completed', 'true');
  }, token);
  await page.goto(`${WEB_BASE}/story-workspace/settings/work?tab=plugins`);

  await expect(page.getByRole('heading', { name: 'Claude 插件' })).toBeVisible();
  await expect.poll(() => pluginRequests.size).toBe(2);
  await expect.poll(() => pluginResponses.size).toBe(2);
  expect([...pluginRequests.values()]).toHaveLength(2);
  const pluginRequestHeaders = await Promise.all(
    [...pluginRequests.values()].map((outgoing) => outgoing.allHeaders()),
  );
  expect(pluginRequestHeaders.map((headers) => headers.authorization)).toEqual([`Bearer ${token}`, `Bearer ${token}`]);
  expect([...pluginResponses.values()]).toEqual([200, 200]);

  const createButton = page.getByRole('button', { name: '创建' });
  await expect(createButton).toBeVisible();
  await expect(page.getByRole('button', { name: 'Install Plugin' })).toHaveCount(0);
  await createButton.focus();
  await createButton.press('Enter');

  const menu = page.getByRole('menu', { name: 'Claude 插件创建操作' });
  await expect(menu).toBeVisible();
  const menuItems = menu.getByRole('menuitem');
  await expect(menuItems).toHaveCount(3);
  await expect(menuItems.nth(0)).toHaveText('安装');
  await expect(menuItems.nth(1)).toHaveText('从 Marketplace 添加');
  await expect(menuItems.nth(2)).toContainText('最近操作');
  await expect(menuItems.nth(0)).toBeFocused();

  await menuItems.nth(0).press('ArrowDown');
  await expect(menuItems.nth(1)).toBeFocused();
  await menuItems.nth(1).press('Enter');
  const marketplaceDialog = page.getByRole('dialog', { name: '从 Marketplace 添加' });
  await expect(marketplaceDialog).toBeVisible();
  await expect(marketplaceDialog.getByRole('list', { name: 'Marketplace 安装进度' }).getByRole('listitem').first()).toContainText('选择插件');
  await expect(marketplaceDialog.getByRole('button', { name: /comfy-cloud/ })).toBeVisible();
  await expect.poll(() => pluginRequests.size).toBe(3);
  const marketplaceRequest = [...pluginRequests.values()].find((request) => request.url().includes('/api/claude-plugins/marketplace'));
  expect((await marketplaceRequest!.allHeaders()).authorization).toBe(`Bearer ${token}`);
  await marketplaceDialog.getByRole('button', { name: /comfy-cloud/ }).click();
  await marketplaceDialog.getByRole('button', { name: '继续' }).click();
  await expect(marketplaceDialog.getByText('确认全局目录版本')).toBeVisible();
  await expect(marketplaceDialog.getByText('4a1db97094bd30da911a72110d60bc4464744367')).toBeVisible();
  await expect(marketplaceDialog.getByText('远程默认分支')).toBeVisible();
  await expect(marketplaceDialog.getByText('sha256:a63778a6c4451006c66c31e308a15d717f8909b82252f077ab240bd30adf25f4')).toBeVisible();
  await marketplaceDialog.getByRole('button', { name: '确认安装' }).click();
  expect(marketplaceInstallBody).toEqual({ marketplace_entry_id: 'cpme_comfy_cloud' });
  await expect(marketplaceDialog.getByText('插件可以使用')).toBeVisible();
  await expect(marketplaceDialog.getByText('comfy-cloud@comfy-skills 已进入共享安装列表', { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({
    fullPage: true,
    path: 'output/playwright/claude-plugin-marketplace-wide.png',
  });
  expect(pluginMutationRequests).toHaveLength(1);

  await marketplaceDialog.getByRole('button', { name: '完成' }).click();
  await expect(marketplaceDialog).toBeHidden();
  await expect(createButton).toBeFocused();

  await createButton.press('Enter');
  await expect(menuItems.nth(0)).toBeFocused();
  await menuItems.nth(0).press('End');
  await expect(menuItems.nth(2)).toBeFocused();
  await menuItems.nth(2).press('Enter');
  const operationsDialog = page.getByRole('dialog', { name: '最近操作' });
  await expect(operationsDialog).toBeVisible();
  await expect(operationsDialog.locator('[data-dialog-autofocus]')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(createButton).toBeFocused();

  await createButton.press('Enter');
  await menuItems.nth(0).press('Enter');
  const installDialog = page.getByRole('dialog', { name: '安装 Claude 插件' });
  await expect(installDialog).toBeVisible();
  await expect(installDialog.getByLabel('Package spec')).toBeFocused();
  await page.keyboard.press('Escape');
  expect(pluginMutationRequests).toHaveLength(1);

  marketplaceAvailable = false;
  await createButton.press('Enter');
  await menuItems.nth(0).press('ArrowDown');
  await menuItems.nth(1).press('Enter');
  await expect(marketplaceDialog.getByText('Marketplace 目录暂不可用')).toBeVisible();
  await expect(marketplaceDialog.getByText('The global ClaudePlugin Marketplace capability is not available.')).toBeVisible();
  await marketplaceDialog.getByRole('button', { name: '重新加载' }).focus();
  await page.keyboard.press('Escape');
  await expect(marketplaceDialog).toBeHidden();
  await expect(createButton).toBeFocused();

  await page.setViewportSize({ width: 390, height: 760 });
  await createButton.press('Enter');
  const menuBox = await menu.boundingBox();
  expect(menuBox).not.toBeNull();
  expect(menuBox!.x).toBeGreaterThanOrEqual(0);
  expect(menuBox!.x + menuBox!.width).toBeLessThanOrEqual(390);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({
    fullPage: true,
    path: 'output/playwright/claude-plugin-create-menu-narrow.png',
  });
  await page.keyboard.press('Escape');

  expect(retiredDeckPluginRequests).toEqual([]);
  expect(unexpectedApiRequests).toEqual([]);
  expect(diagnostics).toEqual([]);
});
