// [Input] Authenticated root App entry with deterministic API responses.
// [Output] Browser regression proving authenticated root entry is canonical Story
//          Workspace Chat with hidden legacy navigation and global UI typography.
// [Pos] Story Workspace authenticated-entry E2E seam.
// [Sync] 2026-08-14: change the authenticated root expectation from Dream to Chat,
//                    assert hidden entries, refresh persistence, and Microsoft YaHei.
// [Sync] 2026-08-14: assert primary navigation order is Chat, Dream, Decks.

import { expect, test } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chromium' });

test('password login at root opens canonical Story Workspace Chat', async ({ page }) => {
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
    if (pathname === '/api/storage') {
      await route.fulfill({ json: {
        type: 'unknown', supportsDirectUpload: false, isConfigured: true,
      } });
      return;
    }
    if (pathname === '/api/system-config') {
      await route.fulfill({ json: {
        data: { im_full_access_enabled: false, workspace_enabled: false },
      } });
      return;
    }
    if (pathname === '/api/decks') {
      await route.fulfill({ json: { decks: [] } });
      return;
    }
    if (pathname === '/api/claude-agent/threads') {
      await route.fulfill({ json: { threads: [] } });
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

  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/chat`);
  const storyWorkspaceNavigation = page.getByRole('navigation', { name: 'Story Workspace 导航' });
  await expect(storyWorkspaceNavigation).toBeVisible();
  await expect(storyWorkspaceNavigation.getByRole('button')).toHaveCount(3);
  await expect(storyWorkspaceNavigation.getByRole('button')).toHaveText(['Chat', 'Dream', 'Decks']);
  await expect(storyWorkspaceNavigation.getByRole('button', { name: 'Chat' })).toHaveAttribute('aria-current', 'page');
  await expect(storyWorkspaceNavigation.getByRole('button', { name: 'Writing' })).toHaveCount(0);
  await expect(storyWorkspaceNavigation.getByRole('button', { name: 'Timeline' })).toHaveCount(0);
  await expect(storyWorkspaceNavigation.getByRole('button', { name: 'Reflections' })).toHaveCount(0);
  await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeVisible();
  await expect.poll(async () => page.locator('body').evaluate((body) => (
    getComputedStyle(body).fontFamily
  ))).toContain('Microsoft YaHei');

  await page.reload();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/chat`);
  const reloadedNavigation = page.getByRole('navigation', { name: 'Story Workspace 导航' });
  await expect(reloadedNavigation).toBeVisible();
  await expect(reloadedNavigation.getByRole('button', { name: 'Chat' })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeVisible();

  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/login-default-desktop.png',
    fullPage: true,
  });

  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/dream`);
  await expect(
    page.getByRole('navigation', { name: 'Story Workspace 导航' })
      .getByRole('button', { name: 'Dream' }),
  ).toHaveAttribute('aria-current', 'page');
  await expect.poll(() => diagnostics).toEqual([]);
  expect(unexpectedApiRequests).toEqual([]);
});
