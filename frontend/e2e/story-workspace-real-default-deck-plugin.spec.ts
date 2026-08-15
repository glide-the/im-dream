// [Input] Existing local default actor, normal Dream backend/PostgreSQL, and
//         Story Workspace Decks UI.
// [Output] Real-business proof that opening Decks repairs a zero-ref default
//          screenplay team and renders drama-forge v1.0.1 as selected.
// [Pos] Opt-in real-data default-Deck plugin acceptance in frontend/e2e.
// [Sync] 2026-08-14: add visible default-account reconciliation coverage.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DEFAULT_DECK_PLUGIN_QA === '1';
const WEB_BASE = process.env.INK_REAL_DEFAULT_DECK_PLUGIN_QA_WEB_BASE
  ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_DEFAULT_DECK_PLUGIN_QA_ACTOR_EMAIL
  ?? 'test333@suoxya.com';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

/**
 * Business impact brief:
 *
 * | Fact | Authority | Expected impact |
 * | Default screenplay Deck identity/voices | decks + voices | unchanged |
 * | Default Deck Claude refs | deck_claude_plugin_refs | empty -> one enabled drama-forge 1.0.1 ref, or preserved if already present |
 * | Plugin installation | claude_plugin_installations | unchanged; ready installation is referenced |
 * | Other Deck refs | deck_claude_plugin_refs | unchanged |
 * | Project/Episode/Run/Thread/files/billing | their existing authorities | out of scope and unchanged |
 */

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 800 },
});
test.skip(!ENABLED, 'Set INK_REAL_DEFAULT_DECK_PLUGIN_QA=1 for real default-account QA.');

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

test('default account sees drama-forge v1.0.1 selected on 剧本创作团队', async ({ page }) => {
  const token = createActorToken(ACTOR_EMAIL);
  const diagnostics = diagnosticsFor(page);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  await page.goto(`${WEB_BASE}/story-workspace/decks`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await page.getByRole('tab', { name: '创作 Deck' }).click();
  const defaultDeck = page.locator('[data-deck-card-kind="owned"]').filter({ hasText: '剧本创作团队' });
  await expect(defaultDeck).toBeVisible();
  await defaultDeck.getByRole('button', { name: /编辑|查看模板/ }).click();

  await expect(page.getByText('Deck Editor', { exact: true })).toBeVisible();
  const dramaForge = page.locator('label').filter({ hasText: 'drama-forge' });
  await expect(dramaForge).toContainText('v1.0.1');
  await expect(dramaForge.getByRole('checkbox')).toBeChecked();

  const decksResponse = await page.request.get(`${WEB_BASE}/api/decks`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(decksResponse.status(), await decksResponse.text()).toBe(200);
  const decksPayload = await decksResponse.json() as {
    decks: Array<{ id: string; name: string; name_zh?: string }>;
  };
  const screenplayDeck = decksPayload.decks.find(
    (deck) => deck.name === '剧本创作团队' || deck.name_zh === '剧本创作团队',
  );
  expect(screenplayDeck).toBeTruthy();

  const refsResponse = await page.request.get(
    `${WEB_BASE}/api/decks/${encodeURIComponent(screenplayDeck!.id)}/claude-plugins`,
    { headers: { authorization: `Bearer ${token}` } },
  );
  expect(refsResponse.status(), await refsResponse.text()).toBe(200);
  const refsPayload = await refsResponse.json() as {
    refs: Array<{
      package_spec: string;
      resolved_version: string;
      enabled: number;
      installation_status: string;
    }>;
  };
  expect(refsPayload.refs).toEqual(expect.arrayContaining([
    expect.objectContaining({
      package_spec: 'drama-forge@drama-studio',
      resolved_version: '1.0.1',
      enabled: 1,
      installation_status: 'ready',
    }),
  ]));

  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/real-default-deck-plugin.png',
    fullPage: true,
  });
  expect(diagnostics).toEqual([]);
});
