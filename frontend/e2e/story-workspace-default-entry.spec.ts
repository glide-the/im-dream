// [Input] Authenticated root App entry with deterministic API responses.
// [Output] Browser regression proving the default shell is Story Workspace.
// [Pos] Story Workspace authenticated-entry E2E seam.

import { expect, test } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chromium' });

test('password login at root opens the canonical Story Workspace shell', async ({ page }) => {
  const diagnostics: string[] = [];
  const unexpectedApiRequests: string[] = [];
  const isKnownExternal = (url: string) => (
    url.includes('react-grab.com')
    || url.includes('fonts.googleapis.com')
    || url.includes('fonts.gstatic.com')
  );
  const isKnownPreAuthVoiceError = (message: string) => (
    message.includes('Failed to load voices from decks: Error: Not authenticated')
  );
  page.on('console', (message) => {
    if (
      message.type() === 'error'
      && !isKnownExternal(message.text())
      && !isKnownPreAuthVoiceError(message.text())
    ) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (failedRequest) => {
    const isExpectedNavigationAbort = (
      failedRequest.failure()?.errorText === 'net::ERR_ABORTED'
      && failedRequest.url().includes('/api/story-workspace/dream-runs')
    );
    if (!isKnownExternal(failedRequest.url()) && !isExpectedNavigationAbort) {
      diagnostics.push(`${failedRequest.failure()?.errorText ?? 'request failed'} ${failedRequest.url()}`);
    }
  });

  const email = 'story-workspace-default@example.test';
  const password = 'story-workspace-default-entry';
  await page.route(`${WEB_BASE}/api/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === '/api/login' && request.method() === 'POST') {
      await route.fulfill({ json: { token: 'story-workspace-default-token' } });
      return;
    }
    if (pathname === '/api/me') {
      await route.fulfill({
        json: { id: 101, email, display_name: 'Story Workspace Default Entry' },
      });
      return;
    }
    if (pathname === '/api/sessions') {
      await route.fulfill({ json: request.method() === 'GET' ? { sessions: [] } : { ok: true } });
      return;
    }
    if (pathname === '/api/sessions/range') {
      await route.fulfill({ json: { sessions: [] } });
      return;
    }
    if (pathname === '/api/pictures/range') {
      await route.fulfill({ json: { pictures: [] } });
      return;
    }
    if (pathname === '/api/sessions/events') {
      await route.fulfill({ contentType: 'text/event-stream', body: ': connected\n\n' });
      return;
    }
    if (pathname === '/api/preferences') {
      await route.fulfill({ json: { first_login_completed: true, timezone: 'UTC' } });
      return;
    }
    if (pathname === '/api/default-voices') {
      await route.fulfill({ json: {} });
      return;
    }
    if (pathname === '/api/decks') {
      await route.fulfill({ json: { decks: [] } });
      return;
    }
    if (pathname === '/api/story-workspace/dream-runs') {
      await route.fulfill({ json: { runs: [] } });
      return;
    }
    unexpectedApiRequests.push(`${request.method()} ${pathname}`);
    await route.fulfill({ json: {} });
  });

  await page.goto(WEB_BASE);
  await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible();
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Login', exact: true }).click();

  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/dream`);
  const storyWorkspaceNavigation = page.getByRole('navigation', { name: 'Story Workspace 导航' });
  await expect(storyWorkspaceNavigation).toBeVisible();
  await expect(storyWorkspaceNavigation.getByRole('button', { name: 'Dream' })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByTitle('Writing')).toHaveCount(0);

  await page.reload();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/dream`);
  const reloadedNavigation = page.getByRole('navigation', { name: 'Story Workspace 导航' });
  await expect(reloadedNavigation).toBeVisible();
  await expect(reloadedNavigation.getByRole('button', { name: 'Dream' })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByTitle('Writing')).toHaveCount(0);
  await expect.poll(() => diagnostics).toEqual([]);
  expect(unexpectedApiRequests).toEqual([]);

  await page.screenshot({
    path: 'output/playwright/story-workspace-default-entry-2026-08-10/login-default-desktop.png',
    fullPage: true,
  });
});
