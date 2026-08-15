// [Input] Named existing actor, normal local Deck UI/API, and real PostgreSQL state.
// [Output] Prove My Published Decks ownership, default-Deck publish denial, and self-collection denial.
// [Pos] Opt-in real-business Deck sharing acceptance in frontend/e2e.
// [Sync] 2026-08-15: enter creator mode before the real publication-policy assertions.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DECK_SHARING_QA === '1';
const WEB_BASE = process.env.INK_REAL_DECK_SHARING_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_DECK_SHARING_ACTOR_EMAIL ?? 'dmeck123@suoxya.com';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

/**
 * Business impact brief:
 *
 * | Fact | Source of truth | Expected impact |
 * | Actor-owned publications | decks.owner_id + decks.published | Decks UI shows only this actor's published Decks |
 * | Default Deck identity | is_system / parent template / exact legacy fingerprint | cannot transition from unpublished to published |
 * | Collection eligibility | source owner + published/system state | actor cannot fork their own Deck; other public Decks remain available |
 * | Existing published default | decks.published | if present, visibly unpublish once so persisted state becomes policy-compliant |
 * | Other Decks/voices/plugins | existing Deck authorities | unchanged |
 * | Project/Episode/Run/Thread/files/model/billing | their existing authorities | out of scope and unchanged |
 */

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 820 },
});
test.skip(!ENABLED, 'Set INK_REAL_DECK_SHARING_QA=1 for named-account Deck sharing QA.');

function createActorToken(email: string): string {
  return execFileSync(BACKEND_PYTHON, ['-c', [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import auth,database,sys',
    'db=database.get_db()',
    "user=db.execute(\"select id,email from users where email=%s and status='active'\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'actor not found'",
    "print(auth.create_access_token(user['id'],user['email']))",
  ].join(';'), email], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim();
}

function diagnosticsFor(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    const text = message.text();
    if (message.type() === 'error'
      && !/(?:react-grab\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(text)) {
      diagnostics.push(`console: ${text}`);
    }
  });
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText !== 'net::ERR_ABORTED'
      && !/(?:react-grab\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(url)) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  return diagnostics;
}

test('named actor sees My Published Decks and cannot publish or collect their default Deck', async ({ page }) => {
  const token = createActorToken(ACTOR_EMAIL);
  const headers = { authorization: `Bearer ${token}` };
  const diagnostics = diagnosticsFor(page);

  const actorResponse = await page.request.get(`${WEB_BASE}/api/me`, { headers });
  expect(actorResponse.status(), await actorResponse.text()).toBe(200);
  const actor = await actorResponse.json() as { id: number; email: string };
  expect(actor.email).toBe(ACTOR_EMAIL);

  const initialResponse = await page.request.get(`${WEB_BASE}/api/decks`, { headers });
  expect(initialResponse.status(), await initialResponse.text()).toBe(200);
  const initial = await initialResponse.json() as {
    decks: Array<{
      id: string;
      name: string;
      name_zh?: string;
      owner_id?: number;
      published?: boolean;
      can_publish?: boolean;
      publish_block_reason?: string | null;
    }>;
  };
  const defaultDeck = initial.decks.find(
    (deck) => deck.can_publish === false && deck.publish_block_reason === 'default_initialized',
  );
  expect(defaultDeck, 'named actor must have a server-identified default Deck').toBeTruthy();

  const communityResponse = await page.request.get(`${WEB_BASE}/api/decks?published=true`, { headers });
  expect(communityResponse.status(), await communityResponse.text()).toBe(200);
  const community = await communityResponse.json() as { decks: Array<{ owner_id?: number }> };
  expect(community.decks.some((deck) => deck.owner_id === actor.id)).toBe(false);

  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);
  await page.goto(`${WEB_BASE}/story-workspace/decks`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await page.getByRole('tab', { name: '创作 Deck' }).click();
  await expect(page.getByRole('heading', { name: /我发布的卡组（\d+）/ })).toBeVisible();

  const ownedCard = page.locator(
    `[data-deck-card-kind="owned"][data-deck-card-id="${defaultDeck!.id}"]`,
  );
  await expect(ownedCard).toBeVisible();

  if (defaultDeck!.published) {
    const publishedCard = page.locator(
      `[data-deck-card-kind="published-by-me"][data-deck-card-id="${defaultDeck!.id}"]`,
    );
    await expect(publishedCard).toBeVisible();
    await expect(publishedCard.getByRole('button', { name: '安装', exact: true })).toHaveCount(0);

    const selfCollect = await page.request.post(
      `${WEB_BASE}/api/decks/${encodeURIComponent(defaultDeck!.id)}/fork`,
      { headers },
    );
    expect(selfCollect.status(), await selfCollect.text()).toBe(409);
    expect((await selfCollect.json() as { detail: string }).detail).toContain('own published Deck');

    page.once('dialog', async (dialog) => dialog.accept());
    await ownedCard.getByRole('button', { name: '取消发布', exact: true }).click();
  }

  const unavailable = ownedCard.getByRole('button', { name: '系统默认 · 不可发布', exact: true });
  await expect(unavailable).toBeDisabled();
  await expect(page.locator(
    `[data-deck-card-kind="published-by-me"][data-deck-card-id="${defaultDeck!.id}"]`,
  )).toHaveCount(0);

  const finalResponse = await page.request.get(`${WEB_BASE}/api/decks`, { headers });
  expect(finalResponse.status(), await finalResponse.text()).toBe(200);
  const finalPayload = await finalResponse.json() as {
    decks: Array<{ id: string; published?: boolean; can_publish?: boolean }>;
  };
  expect(finalPayload.decks.find((deck) => deck.id === defaultDeck!.id)).toMatchObject({
    published: false,
    can_publish: false,
  });
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  await page.screenshot({ path: '../output/playwright/deck-sharing-real-my-published.png', fullPage: true });
  expect(diagnostics).toEqual([]);
});
