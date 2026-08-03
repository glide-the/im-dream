import { expect, test, type Request as PlaywrightRequest } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';
const API_BASE = process.env.E2E_API_BASE ?? 'http://127.0.0.1:8765';

test.use({ channel: 'chromium' });

test('Settings loads Claude plugin state with auth and never loads the retired Deck workflow plugin page', async ({ page, request }) => {
  const registration = await request.post(`${API_BASE}/api/register`, {
    data: {
      email: `claude-plugin-settings-${Date.now()}@example.test`,
      password: 'claude-plugin-settings-test',
      display_name: 'Claude Plugin Settings E2E',
    },
  });
  expect(registration.ok()).toBeTruthy();
  const { token } = await registration.json() as { token: string };

  const pluginRequests = new Map<string, PlaywrightRequest>();
  const pluginResponses = new Map<string, number>();
  const retiredDeckPluginRequests: string[] = [];
  page.on('request', (outgoing) => {
    const url = outgoing.url();
    if (outgoing.method() === 'GET' && (
      url.includes('/api/claude-plugins/installations') || url.includes('/api/claude-plugins/operations')
    )) {
      pluginRequests.set(url.replace(/\?.*$/, ''), outgoing);
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

  await page.addInitScript((authToken) => {
    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('migration_completed', 'true');
  }, token);
  await page.goto(WEB_BASE);
  // The local dev overlay may cover the nav in browser-test mode. Keyboard
  // activation exercises the button's normal accessible Settings handler.
  const settingsButton = page.getByTitle('Settings');
  await settingsButton.focus();
  await settingsButton.press('Enter');

  await expect(page.getByRole('heading', { name: 'Claude 插件' })).toBeVisible();
  // Any signed-in user can install/uninstall now (permission model simplified);
  // the install form must be visible without an admin role.
  await expect(page.getByRole('button', { name: 'Install Plugin' })).toBeVisible();
  await expect.poll(() => pluginRequests.size).toBe(2);
  await expect.poll(() => pluginResponses.size).toBe(2);
  expect([...pluginRequests.values()]).toHaveLength(2);
  const pluginRequestHeaders = await Promise.all(
    [...pluginRequests.values()].map((outgoing) => outgoing.allHeaders()),
  );
  expect(pluginRequestHeaders.map((headers) => headers.authorization)).toEqual([`Bearer ${token}`, `Bearer ${token}`]);
  expect([...pluginResponses.values()]).toEqual([200, 200]);
  expect(retiredDeckPluginRequests).toEqual([]);
});
