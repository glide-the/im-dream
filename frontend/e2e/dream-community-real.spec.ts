// [Input] Named existing actor, normal local Deck APIs, and the real Dream home.
// [Output] Prove the System default Deck is visible without a shared system-template row.
// [Pos] Opt-in read-only real-business Dream community acceptance in frontend/e2e.
// [Sync] 2026-08-14: cover dmeck123@suoxya.com system-default visibility.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DREAM_COMMUNITY_QA === '1';
const WEB_BASE = process.env.INK_REAL_DREAM_COMMUNITY_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_DREAM_COMMUNITY_ACTOR_EMAIL ?? 'dmeck123@suoxya.com';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

test.use({ channel: 'chromium', viewport: { width: 1440, height: 1000 } });
test.skip(!ENABLED, 'Set INK_REAL_DREAM_COMMUNITY_QA=1 for named-account Dream community QA.');

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
  ].join(';'), email], { cwd: BACKEND_DIR, encoding: 'utf-8' }).trim();
}

function diagnosticsFor(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error' && !/(?:react-grab\.com|fonts\.)/.test(message.text())) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText !== 'net::ERR_ABORTED'
      && !/(?:react-grab\.com|fonts\.)/.test(request.url())) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
    }
  });
  return diagnostics;
}

test('named actor sees the initialized default Deck on the Dream home', async ({ page }) => {
  const token = createActorToken(ACTOR_EMAIL);
  const headers = { authorization: `Bearer ${token}` };
  const diagnostics = diagnosticsFor(page);

  const actorDeckResponse = await page.request.get(`${WEB_BASE}/api/decks`, { headers });
  expect(actorDeckResponse.status(), await actorDeckResponse.text()).toBe(200);
  const actorDecks = await actorDeckResponse.json() as {
    decks: Array<{ id: string; publish_block_reason?: string | null }>;
  };
  const initializedDefault = actorDecks.decks.find(
    (deck) => deck.publish_block_reason === 'default_initialized',
  );
  expect(initializedDefault, 'named actor must have a server-identified initialized default').toBeTruthy();

  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);
  await page.goto(`${WEB_BASE}/story-workspace/dream`);

  await expect(page.getByRole('heading', { name: /社区卡组（\d+）/ })).toBeVisible();
  await expect(page.getByText('System default Deck', { exact: true })).toBeVisible();
  await expect(page.getByText('剧本创作团队', { exact: true })).toBeVisible();
  const directUse = page.getByRole('button', { name: '在 Chat 中使用' });
  await expect(directUse).toBeVisible();
  await expect(directUse).toBeEnabled();
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  await page.screenshot({
    path: '../output/playwright/dream-community-real-system-default.png',
    fullPage: true,
  });
  await directUse.click();
  await expect(page).toHaveURL(
    `${WEB_BASE}/story-workspace/chat?deck=${encodeURIComponent(initializedDefault!.id)}`,
  );
  expect(diagnostics).toEqual([]);
});
