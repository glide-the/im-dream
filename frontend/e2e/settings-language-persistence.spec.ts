// [Input] Production Next shell, App, Settings, auth forms and intercepted public boot/import DTOs.
// [Output] Regression receipts for language/theme retention after login, repeated reloads and migration cleanup.
// [Pos] Provider-free browser contract; all auth/API requests are intercepted before the first navigation.
// [Sync] 2026-10-07: cover completed-account login, successful migration, skip and failed-marker recovery.
// Business impact: only browser language/theme and fixture-owned local data change. Project, Episode,
// canonical Artifacts, Run-private publication, after-turn Hook, shared Thread and PostgreSQL are out of scope.

import { expect, test, type Page } from '@playwright/test';
import { STORAGE_KEYS } from '../app/_dream/constants/storageKeys';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://localhost:5173';
const SETTINGS_URL = `${WEB_BASE}/story-workspace/settings`;
test.use({ channel: 'chrome', viewport: { width: 1440, height: 900 } });

async function fixture(page: Page, completed = true, markerFailsOnce = false) {
  let authenticated = false;
  let firstLoginCompleted = completed;
  let markerPendingFailure = markerFailsOnce;
  const diagnostics: string[] = [];
  const mutations: string[] = [];
  const external = (url: string) => /react-grab\.com|fonts\.googleapis\.com|fonts\.gstatic\.com/.test(url);
  page.on('console', (message) => {
    const expectedNoSession = new URL(message.location().url || WEB_BASE).pathname === '/auth/session'
      && message.text().includes('401 (Unauthorized)');
    const expectedMarkerFailure = markerFailsOnce
      && new URL(message.location().url || WEB_BASE).pathname === '/api/mark-first-login-completed'
      && message.text().includes('503 (Service Unavailable)');
    const expectedSkipFeedback = markerFailsOnce && message.text().startsWith('Failed to skip migration:');
    if (message.type() === 'error' && !external(message.text()) && !expectedNoSession && !expectedMarkerFailure && !expectedSkipFeedback) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const path = new URL(request.url()).pathname;
    const navigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && ['/auth/options', '/api/sessions/events', '/api/story-workspace/dream-runs'].includes(path);
    if (!external(request.url()) && !navigationAbort) diagnostics.push(`request: ${request.url()}`);
  });
  await page.route('**/react-grab/**', (route) => route.fulfill({ contentType: 'application/javascript', body: '' }));
  await page.route('**/auth/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/auth/session') {
      await route.fulfill(authenticated ? { json: {
        user: { id: '20261007', email: 'language@example.test', display_name: 'Language QA',
          avatar_url: null, role: 'user', created_at: '2026-10-07T00:00:00Z' }, csrf_token: 'c'.repeat(43),
      } } : { status: 401, json: {} });
    } else if (path === '/auth/options') {
      await route.fulfill({ json: { password_action: `${WEB_BASE}/auth/language-fixture`,
        google_action: `${WEB_BASE}/auth/language-fixture` } });
    } else if (path === '/auth/language-fixture') {
      authenticated = true;
      await route.fulfill({ status: 303, headers: { location: SETTINGS_URL }, body: '' });
    } else if (path === '/auth/logout') {
      authenticated = false;
      await route.fulfill({ json: { success: true } });
    } else {
      diagnostics.push(`unexpected auth ${path}`);
      await route.fulfill({ status: 501, json: {} });
    }
  });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() !== 'GET') mutations.push(`${request.method()} ${path}`);
    if (path === '/api/preferences') {
      await route.fulfill({ json: { first_login_completed: firstLoginCompleted ? 1 : 0, timezone: 'UTC' } });
    } else if (path === '/api/mark-first-login-completed') {
      if (markerPendingFailure) {
        markerPendingFailure = false;
        await route.fulfill({ status: 503, json: { detail: 'Fixture marker unavailable' } });
      } else {
        firstLoginCompleted = true;
        await route.fulfill({ json: { success: true } });
      }
    } else if (path === '/api/import-local-data') {
      await route.fulfill({ json: { success: true, imported: { sessions: 0, pictures: 0, preferences: 1, reports: 0 } } });
    } else if (path === '/api/sessions/events') {
      await route.fulfill({ contentType: 'text/event-stream', body: ': connected\n\n' });
    } else if (path === '/api/sessions' || path === '/api/sessions/range') {
      await route.fulfill({ json: { sessions: [] } });
    } else if (path === '/api/system-config') {
      await route.fulfill({ json: { data: { workspace_enabled: false } } });
    } else if (path === '/api/storage') {
      await route.fulfill({ json: { type: 'unknown', supportsDirectUpload: false, isConfigured: true } });
    } else if (request.method() === 'GET') {
      await route.fulfill({ json: path === '/api/decks' ? { decks: [] }
        : path === '/api/claude-agent/threads' ? { threads: [] }
          : path === '/api/story-workspace/dream-runs' ? { runs: [] } : {} });
    } else {
      diagnostics.push(`unexpected API ${request.method()} ${path}`);
      await route.fulfill({ status: 501, json: {} });
    }
  });
  return { diagnostics, mutations };
}

async function login(page: Page) {
  await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible();
  await page.getByLabel('Email', { exact: true }).fill('language@example.test');
  await page.getByLabel('Password', { exact: true }).fill('fixture-password');
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page).toHaveURL(SETTINGS_URL);
  await expect(page.locator('#settings-general')).toBeVisible();
}

async function assertPreferences(page: Page, language: 'en' | 'zh') {
  await expect(page.locator('#story-workspace-language').getByRole('button', {
    name: language === 'zh' ? /^中文/ : /^English/,
  })).toHaveAttribute('aria-pressed', 'true');
  await expect.poll(() => page.evaluate((keys) => ({
    language: localStorage.getItem(keys.LANGUAGE), theme: localStorage.getItem(keys.THEME),
  }), STORAGE_KEYS)).toEqual({ language, theme: 'dark' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
}

test('language and theme survive repeated loads and visible sign out / sign in', async ({ page }) => {
  const state = await fixture(page);
  await page.goto(SETTINGS_URL);
  await login(page);
  await page.locator('#story-workspace-language').getByRole('button', { name: /^中文/ }).click();
  await page.getByRole('button', { name: /^(Dark|深色)$/ }).click();
  await assertPreferences(page, 'zh');
  await page.evaluate((keys) => {
    localStorage.setItem(keys.META_PROMPT, 'Completed-account cache');
    localStorage.setItem(keys.SELECTED_FRIEND, 'Fixture friend cache');
  }, STORAGE_KEYS);
  for (let load = 0; load < 2; load++) {
    await page.reload();
    await assertPreferences(page, 'zh');
    await expect.poll(() => page.evaluate((keys) => [
      localStorage.getItem(keys.META_PROMPT), localStorage.getItem(keys.SELECTED_FRIEND),
    ], STORAGE_KEYS)).toEqual([null, null]);
  }
  // The Settings surface hides the global user menu; open Chat to sign out through it.
  await page.goto(`${WEB_BASE}/story-workspace/chat`);
  await page.getByRole('button', { name: '打开用户菜单' }).click();
  await page.getByRole('menuitem', { name: 'Logout' }).click();
  await login(page);
  await assertPreferences(page, 'zh');
  await page.locator('#story-workspace-language').getByRole('button', { name: /^English/ }).click();
  await page.reload();
  await assertPreferences(page, 'en');
  expect(state.diagnostics).toEqual([]);
});

for (const action of ['Migrate Data', 'Skip'] as const) {
  test(`${action} retains language/theme and removes completed local data`, async ({ page }) => {
    const state = await fixture(page, false);
    await page.goto(SETTINGS_URL);
    // Seed once before the visible login; a reload must restore production storage itself.
    await page.evaluate((keys) => {
      localStorage.setItem(keys.LANGUAGE, 'zh'); localStorage.setItem(keys.THEME, 'dark');
      localStorage.setItem(keys.META_PROMPT, 'Fixture local preference');
    }, STORAGE_KEYS);
    await login(page);
    await expect(page.getByRole('heading', { name: 'Migrate Your Data?' })).toBeVisible();
    page.on('dialog', (dialog) => dialog.accept());
    await page.getByRole('button', { name: action, exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Migrate Your Data?' })).toBeHidden();
    await assertPreferences(page, 'zh');
    expect(await page.evaluate((key) => localStorage.getItem(key), STORAGE_KEYS.META_PROMPT)).toBeNull();
    await page.reload();
    await assertPreferences(page, 'zh');
    expect(state.mutations.filter((path) => path.includes('import-local-data'))).toHaveLength(action === 'Migrate Data' ? 1 : 0);
    expect(state.diagnostics).toEqual([]);
  });
}

test('failed migration marker retains data and preferences for retry', async ({ page }) => {
  const state = await fixture(page, false, true);
  await page.goto(SETTINGS_URL);
  await page.evaluate((keys) => {
    localStorage.setItem(keys.LANGUAGE, 'zh'); localStorage.setItem(keys.THEME, 'dark');
    localStorage.setItem(keys.META_PROMPT, 'Fixture local preference');
  }, STORAGE_KEYS);
  await login(page);
  const alertMessage = page.waitForEvent('dialog');
  await page.getByRole('button', { name: 'Skip', exact: true }).click();
  const alert = await alertMessage;
  expect(alert.message()).toBe('Failed to skip migration. Please try again.');
  await alert.accept();
  await expect(page.getByRole('heading', { name: 'Migrate Your Data?' })).toBeVisible();
  await assertPreferences(page, 'zh');
  expect(await page.evaluate((key) => localStorage.getItem(key), STORAGE_KEYS.META_PROMPT)).toBe('Fixture local preference');
  await page.getByRole('button', { name: 'Skip', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Migrate Your Data?' })).toBeHidden();
  await assertPreferences(page, 'zh');
  expect(await page.evaluate((key) => localStorage.getItem(key), STORAGE_KEYS.META_PROMPT)).toBeNull();
  expect(state.diagnostics).toEqual([]);
});
