import { expect, test } from '@playwright/test';

const WEB_BASE = 'http://127.0.0.1:5173';
const API_BASE = 'http://127.0.0.1:8765';

// Use Playwright's full Chromium build (new headless mode) in local and CI runs.
test.use({ channel: 'chromium' });

test('Dream selects one Deck and persists immutable thread provenance', async ({ page, request }) => {
  const email = `deck-dream-${Date.now()}@example.test`;
  const registration = await request.post(`${API_BASE}/api/register`, {
    data: { email, password: 'deck-dream-test', display_name: 'Deck Dream E2E' },
  });
  expect(registration.ok()).toBeTruthy();
  const auth = await registration.json() as { token: string };
  const decksResponse = await request.get(`${API_BASE}/api/decks`, {
    headers: { Authorization: `Bearer ${auth.token}` },
  });
  expect(decksResponse.ok()).toBeTruthy();
  const decks = (await decksResponse.json() as {
    decks: Array<{ id: string; name: string; name_en?: string }>;
  }).decks;
  expect(decks.length).toBeGreaterThan(0);
  const selectedDeck = decks[0];
  let storyReviewStatus: 'pending' | 'confirmed' = 'pending';
  let storyStatus: 'draft' | 'published' = 'draft';

  const storyPayload = () => ({
    id: 'story-e2e',
    identifier: 'story-e2e',
    title: '雨夜电台',
    description: '一名夜班主播收到来自未来的电话。',
    content: '电话只会响三次，而第三次由她自己打来。',
    type: 'short',
    status: storyStatus,
    review_status: storyReviewStatus,
    agent_generated: true,
    characters: [{
      id: 'character-e2e',
      identifier: 'character-e2e',
      name: '林岚',
      status: 'active',
      review_status: storyReviewStatus,
      agent_generated: true,
    }],
    scenes: [{
      id: 'scene-e2e',
      identifier: 'scene-e2e',
      name: '午夜直播间',
      status: 'active',
      order_index: 0,
      review_status: storyReviewStatus,
      agent_generated: true,
    }],
    ...(storyStatus === 'published' ? {
      execution: {
        action: 'publish_story_bundle',
        status: 'completed',
        completed_at: '2026-08-02T00:00:00Z',
      },
    } : {}),
  });

  await page.addInitScript(({ token }) => {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'en');
  }, { token: auth.token });

  await page.route(`${WEB_BASE}/api/claude-agent`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: [
        'data: {"type":"text-start","id":"deck-e2e"}',
        'data: {"type":"text-delta","id":"deck-e2e","delta":"Draft ready for review."}',
        'data: {"type":"text-end","id":"deck-e2e"}',
        `data: ${JSON.stringify({
          type: 'story-workspace-output',
          story_id: 'story-e2e',
          review_status: 'pending',
          character_ids: ['character-e2e'],
          scene_ids: ['scene-e2e'],
          chat_thread_id: 'thread-e2e-source',
          deck_id: selectedDeck.id,
          deck_name: selectedDeck.name,
          deck_name_en: selectedDeck.name_en,
        })}`,
        'data: {"type":"finish","finishReason":"stop"}',
        '',
      ].join('\n\n'),
    });
  });

  await page.route(`${WEB_BASE}/api/story-workspace/stories/story-e2e`, async (route) => {
    if (route.request().method() === 'PATCH') {
      const patch = route.request().postDataJSON() as { title?: string };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        ...storyPayload(),
        title: patch.title ?? storyPayload().title,
      }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(storyPayload()) });
  });
  await page.route(`${WEB_BASE}/api/story-workspace/stories/story-e2e/confirm`, async (route) => {
    storyReviewStatus = 'confirmed';
    storyStatus = 'published';
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(storyPayload()) });
  });

  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await expect(page).toHaveURL(/\/story-workspace\/dream$/);
  const deckSelect = page.getByLabel('Select one Deck for this conversation');
  await expect(deckSelect).toBeVisible();
  await deckSelect.selectOption(selectedDeck.id);

  const threadResponsePromise = page.waitForResponse((response) => (
    response.url().endsWith('/api/claude-agent/threads')
    && response.request().method() === 'POST'
  ));
  await page.getByPlaceholder('Ask Ink & Memory…').fill('Create a short story premise.');
  await page.getByRole('button', { name: 'Send' }).click();
  const threadResponse = await threadResponsePromise;
  expect(threadResponse.ok()).toBeTruthy();
  expect(threadResponse.request().postDataJSON()).toEqual({ deckId: selectedDeck.id });
  const thread = await threadResponse.json() as { thread_id: string; deck_id: string };
  expect(thread.deck_id).toBe(selectedDeck.id);

  await expect(page.getByLabel(
    `Conversation Deck: ${selectedDeck.name_en || selectedDeck.name}`,
  )).toBeVisible();
  await expect(page.getByLabel('Select one Deck for this conversation')).toHaveCount(0);
  await expect(page.getByText('雨夜电台', { exact: true })).toBeVisible();
  await expect(page.getByText('等待你的决定', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '确认提案并执行发布' })).toBeVisible();
  await expect(page.getByText('午夜直播间', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '确认提案并执行发布' }).click();
  await expect(page.getByText('已确认 · 后续发布已完成', { exact: true })).toBeVisible();
  await page.screenshot({ path: '../output/playwright/deck-dream.png', fullPage: true });

  const snapshot = await request.get(
    `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(thread.thread_id)}/messages`,
    { headers: { Authorization: `Bearer ${auth.token}` } },
  );
  expect(snapshot.ok()).toBeTruthy();
  expect((await snapshot.json() as { thread: { deck_id: string } }).thread.deck_id)
    .toBe(selectedDeck.id);
});
