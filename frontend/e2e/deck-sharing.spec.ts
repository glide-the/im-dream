// [Input] Production-shaped Deck ownership/sharing DTOs and Story Workspace Decks UI.
// [Output] Verify My Published Decks, disabled default publication, and no self-collection action.
// [Pos] Provider-free browser regression for Deck sharing presentation.
// [Sync] 2026-08-15: enter explicit creator mode before publication management.

import { expect, test } from '@playwright/test';

const WEB_BASE = 'http://127.0.0.1:5173';
const defaultDeck = {
  id: 'default-deck', name: '剧本创作团队', name_zh: '剧本创作团队',
  description: '系统初始化', icon: 'book', color: 'brown', is_system: false,
  enabled: true, published: false, can_publish: false,
  publish_block_reason: 'default_initialized', voice_count: 5, voices: [],
  agent_type: 'dream', agent_type_revision: 1,
};
const publishedDeck = {
  id: 'my-published-deck', name: '我的雨夜卡组', description: '用户原创',
  icon: 'moon', color: 'blue', is_system: false, enabled: true,
  published: true, can_publish: true, publish_block_reason: null,
  voice_count: 1, install_count: 2, voices: [], agent_type: 'chat', agent_type_revision: 1,
};

test.use({ channel: 'chromium', viewport: { width: 1200, height: 760 } });

test('Decks shows actor publications and never offers self-collection', async ({ page }) => {
  let published = true;
  let communityReads = 0;
  const diagnostics: string[] = [];
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('react-grab.com')) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('requestfailed', (request) => diagnostics.push(`requestfailed: ${request.url()}`));

  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'deck-sharing-provider-free');
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  });
  await page.route(`${WEB_BASE}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === '/api/me') return route.fulfill({ json: { id: 28, email: 'actor@example.test', display_name: 'Actor' } });
    if (url.pathname === '/api/preferences') return route.fulfill({ json: { first_login_completed: true } });
    if (url.pathname === '/api/decks/defaults/reconcile') return route.fulfill({ json: { deck_id: null, reconciled: false, reason: 'default_not_found' } });
    if (url.pathname === '/api/decks' && request.method() === 'GET') {
      if (url.searchParams.get('published') === 'true') communityReads += 1;
      return route.fulfill({ json: { decks: [defaultDeck, { ...publishedDeck, published }] } });
    }
    if (url.pathname === `/api/decks/${defaultDeck.id}`) return route.fulfill({ json: defaultDeck });
    if (url.pathname === `/api/decks/${publishedDeck.id}`) return route.fulfill({ json: { ...publishedDeck, published } });
    if (url.pathname === `/api/decks/${publishedDeck.id}/publish` && request.method() === 'POST') {
      published = false;
      return route.fulfill({ json: { success: true, published: false } });
    }
    if (url.pathname === '/api/sessions' || url.pathname === '/api/sessions/range') return route.fulfill({ json: { sessions: [] } });
    if (url.pathname === '/api/sessions/events') return route.fulfill({ contentType: 'text/event-stream', body: ': connected\n\n' });
    if (url.pathname === '/api/pictures/range') return route.fulfill({ json: { pictures: [] } });
    if (url.pathname === '/api/default-voices') return route.fulfill({ json: {} });
    if (url.pathname === '/api/storage') return route.fulfill({ json: { type: 'unknown', supportsDirectUpload: false, isConfigured: true } });
    if (url.pathname === '/api/system-config') return route.fulfill({ json: { data: {} } });
    return route.fulfill({ json: {} });
  });

  await page.goto(`${WEB_BASE}/story-workspace/decks`);
  await page.getByRole('tab', { name: '创作 Deck' }).click();
  await expect(page.getByRole('heading', { name: '我发布的卡组（1）' })).toBeVisible();
  await expect(page.getByRole('heading', { name: /社区卡组/ })).toHaveCount(0);
  const defaultCard = page.locator('[data-deck-card-kind="owned"][data-deck-card-id="default-deck"]');
  await expect(defaultCard.getByRole('button', { name: '系统默认 · 不可发布' })).toBeDisabled();
  const publishedCard = page.locator('[data-deck-card-kind="published-by-me"][data-deck-card-id="my-published-deck"]');
  await expect(publishedCard).toBeVisible();
  await expect(publishedCard.getByRole('button', { name: '安装', exact: true })).toHaveCount(0);
  expect(communityReads).toBe(0);
  await page.screenshot({ path: '../output/playwright/deck-sharing-my-published-filled.png', fullPage: true });

  page.once('dialog', async (dialog) => dialog.accept());
  await publishedCard.getByRole('button', { name: '取消发布' }).click();
  await expect(page.getByRole('heading', { name: '我发布的卡组（0）' })).toBeVisible();
  await expect(page.getByText('你还没有发布任何卡组。')).toBeVisible();
  await page.screenshot({ path: '../output/playwright/deck-sharing-my-published.png', fullPage: true });
  expect(diagnostics).toEqual([]);
});
