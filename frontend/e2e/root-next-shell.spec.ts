// [Input] Canonical root Next Web Shell with deterministic browser-only auth and boot API fixtures.
// [Output] Focused URL, login, direct-load, and refresh regression for the client-only compatibility shell.
// [Pos] task_411-01 provider-free browser gate; it mutates no backend, database, model, or business artifact.
// [Sync] 2026-09-05: cover the Vite-to-root-Next default-entry migration with system Chrome.

import { expect, test } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chrome' });

test('root Next shell preserves login, canonical URL, direct load, and refresh', async ({ page }) => {
  const diagnostics: string[] = [];
  const unexpectedApiRequests: string[] = [];
  const knownExternal = (url: string) => (
    url.includes('react-grab.com')
    || url.includes('fonts.googleapis.com')
    || url.includes('fonts.gstatic.com')
  );

  page.on('console', (message) => {
    if (message.type() === 'error' && !knownExternal(message.text())) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const requestPath = new URL(request.url()).pathname;
    const expectedNavigationAbort = (
      request.failure()?.errorText === 'net::ERR_ABORTED'
      && ['/api/sessions/events', '/api/story-workspace/dream-runs'].includes(requestPath)
    );
    if (!knownExternal(request.url()) && !expectedNavigationAbort) {
      diagnostics.push(`${request.failure()?.errorText ?? 'request failed'} ${request.url()}`);
    }
  });

  await page.route(`${WEB_BASE}/api/**`, async (route) => {
    const request = route.request();
    const requestPath = new URL(request.url()).pathname;
    if (requestPath === '/api/login' && request.method() === 'POST') {
      await route.fulfill({ json: { token: 'root-next-shell-token' } });
      return;
    }
    if (requestPath === '/api/me') {
      await route.fulfill({ json: { id: 41101, email: 'root-next-shell@example.test', display_name: 'Root Next Shell' } });
      return;
    }
    if (requestPath === '/api/preferences') {
      await route.fulfill({ json: { first_login_completed: true, timezone: 'UTC' } });
      return;
    }
    if (requestPath === '/api/default-voices') {
      await route.fulfill({ json: {} });
      return;
    }
    if (requestPath === '/api/storage') {
      await route.fulfill({ json: { type: 'unknown', supportsDirectUpload: false, isConfigured: true } });
      return;
    }
    if (requestPath === '/api/system-config') {
      await route.fulfill({ json: { data: { im_full_access_enabled: false, workspace_enabled: false } } });
      return;
    }
    if (requestPath === '/api/sessions') {
      await route.fulfill({ json: request.method() === 'GET' ? { sessions: [] } : { ok: true } });
      return;
    }
    if (requestPath === '/api/sessions/range') {
      await route.fulfill({ json: { sessions: [] } });
      return;
    }
    if (requestPath === '/api/sessions/events') {
      await route.fulfill({ contentType: 'text/event-stream', body: ': connected\n\n' });
      return;
    }
    if (requestPath === '/api/pictures/range') {
      await route.fulfill({ json: { pictures: [] } });
      return;
    }
    if (requestPath === '/api/decks') {
      await route.fulfill({ json: { decks: [] } });
      return;
    }
    if (requestPath === '/api/decks/defaults/reconcile' && request.method() === 'POST') {
      await route.fulfill({ json: { deck_id: null, reconciled: false, reason: 'default_not_found' } });
      return;
    }
    if (requestPath === '/api/claude-agent/threads') {
      await route.fulfill({ json: { threads: [] } });
      return;
    }
    if (requestPath === '/api/story-workspace/dream-runs') {
      await route.fulfill({ json: { runs: [] } });
      return;
    }
    if (requestPath === '/api/reports') {
      await route.fulfill({ json: { reports: [] } });
      return;
    }
    if (requestPath === '/api/reflections/latest') {
      await route.fulfill({ json: { task: null, results: [] } });
      return;
    }
    unexpectedApiRequests.push(`${request.method()} ${requestPath}`);
    await route.fulfill({ json: {} });
  });

  await page.goto(WEB_BASE);
  await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible();
  await page.locator('input[type="email"]').fill('root-next-shell@example.test');
  await page.locator('input[type="password"]').fill('root-next-shell-password');
  await page.getByRole('button', { name: 'Login', exact: true }).click();

  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/chat`);
  await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/chat`);
  await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeVisible();

  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/dream`);
  await expect(page.getByRole('navigation', { name: 'Story Workspace 导航' })).toBeVisible();

  expect(unexpectedApiRequests).toEqual([]);
  expect(diagnostics).toEqual([]);
});
