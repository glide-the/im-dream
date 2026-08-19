// [Input] Running frontend public entry point plus production-shaped, read-only ClaudePlugin API fixtures.
// [Output] Verify Work / Plugins auth transport, three-action keyboard menu, Marketplace fail-closed dialog, and responsive placement.
// [Pos] Technical ClaudePlugin Settings browser journey; it never calls the normal backend or mutates business data.
// [Sync] 2026-08-19: cover the create-menu migration and no-catalog Marketplace entry with strict diagnostics.

import { expect, test, type Request as PlaywrightRequest } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chromium' });

test('Work / Plugins exposes the accessible create menu and fail-closed Marketplace entry', async ({ page }) => {
  const token = 'claude-plugin-settings-technical-token';
  const pluginRequests = new Map<string, PlaywrightRequest>();
  const pluginResponses = new Map<string, number>();
  const pluginMutationRequests: string[] = [];
  const retiredDeckPluginRequests: string[] = [];
  const unexpectedApiRequests: string[] = [];
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('react-grab.com')) diagnostics.push(message.text());
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
      url.includes('/api/claude-plugins/installations') || url.includes('/api/claude-plugins/operations')
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
      url.includes('/api/claude-plugins/installations') || url.includes('/api/claude-plugins/operations')
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
  await expect(marketplaceDialog.getByText('Marketplace 目录暂不可用')).toBeVisible();
  await expect(marketplaceDialog.getByText('当前服务没有可浏览的 Marketplace 插件目录 API', { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({
    fullPage: true,
    path: 'output/playwright/claude-plugin-marketplace-wide.png',
  });
  expect(pluginMutationRequests).toEqual([]);

  await page.keyboard.press('Escape');
  await expect(marketplaceDialog).toBeHidden();
  await expect(createButton).toBeFocused();

  await createButton.press('Enter');
  await expect(menuItems.nth(0)).toBeFocused();
  await menuItems.nth(0).press('End');
  await expect(menuItems.nth(2)).toBeFocused();
  await menuItems.nth(2).press('Enter');
  const operationsDialog = page.getByRole('dialog', { name: '最近操作' });
  await expect(operationsDialog).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(createButton).toBeFocused();

  await createButton.press('Enter');
  await menuItems.nth(0).press('Enter');
  const installDialog = page.getByRole('dialog', { name: '安装 Claude 插件' });
  await expect(installDialog).toBeVisible();
  await expect(installDialog.getByLabel('Package spec')).toBeFocused();
  await page.keyboard.press('Escape');
  expect(pluginMutationRequests).toEqual([]);

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
