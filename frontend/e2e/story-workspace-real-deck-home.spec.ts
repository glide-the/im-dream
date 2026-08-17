// [Input] Named existing local actor, normal Dream backend/PostgreSQL, and Story Workspace Deck UI.
// [Output] Read-only real-business proof that Deck home shows only published-clean enabled Decks
//          while Work retains the complete inventory and reads Deck-related Chat history without writes.
// [Pos] Opt-in non-cloning real Deck-home acceptance in frontend/e2e.
// [Sync] 2026-08-17: add real-content published/draft visibility and zero-write verification.
// [Sync] 2026-08-17: verify More → related conversations against the normal Deck-filtered Thread API.
// [Sync] 2026-08-17: verify the real Work route renders the Chinese locale without a bilingual title.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DECK_HOME_QA === '1';
const WEB_BASE = process.env.INK_REAL_DECK_HOME_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_DECK_HOME_ACTOR_EMAIL ?? 'dmeck123@suoxya.com';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

interface RealDeck {
  id: string;
  name: string;
  enabled: boolean;
  is_system: boolean;
  deck_version_capability?: boolean;
  deck_version?: number | null;
  deck_version_dirty?: boolean;
  deck_version_status?: 'unpublished' | 'draft' | 'published';
}

/**
 * Real-business impact brief:
 *
 * | Fact | Authority | Expected impact |
 * | Deck inventory/version facts | normal PostgreSQL through GET /api/decks | read only; unchanged |
 * | Deck home | Deck DTO published-clean predicate | only eligible Decks visible |
 * | Settings / Work | complete actor Deck inventory | every existing Deck remains visible |
 * | Default reconcile | POST /api/decks/defaults/reconcile | production page-load path may run; Deck facts remain unchanged |
 * | Other Deck/Voice writes | public mutation APIs | zero requests |
 * | Project/Episode/Run/Thread/Admin/Gateway/billing | their existing authorities | out of scope and unchanged |
 */

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 800 },
});
test.skip(!ENABLED, 'Set INK_REAL_DECK_HOME_QA=1 to use the named existing local actor.');

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
      && !/(?:react-grab\.com|react-grab\.js|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(text)) {
      diagnostics.push(`console: ${text}`);
    }
  });
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText !== 'net::ERR_ABORTED'
      && !/(?:react-grab\.com|react-grab\.js|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(url)) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  return diagnostics;
}

const isHomeVisible = (deck: RealDeck): boolean => (
  deck.enabled
  && deck.deck_version_capability === true
  && typeof deck.deck_version === 'number'
  && deck.deck_version > 0
  && deck.deck_version_dirty === false
  && deck.deck_version_status === 'published'
);

test('real Deck home hides drafts while Work preserves complete inventory without writes', async ({ page }) => {
  const token = createActorToken(ACTOR_EMAIL);
  const headers = { authorization: `Bearer ${token}` };
  const diagnostics = diagnosticsFor(page);
  const mutationRequests: string[] = [];
  let reconcileRequests = 0;
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (request.method() === 'POST' && url.pathname === '/api/decks/defaults/reconcile') {
      reconcileRequests += 1;
    } else if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method())
      && (url.pathname.startsWith('/api/decks')
        || url.pathname.startsWith('/api/voices')
        || url.pathname.startsWith('/api/claude-agent/threads'))) {
      mutationRequests.push(`${request.method()} ${url.pathname}`);
    }
  });

  const response = await page.request.get(`${WEB_BASE}/api/decks`, { headers });
  expect(response.status(), await response.text()).toBe(200);
  const payload = await response.json() as { decks: RealDeck[] };
  expect(payload.decks.length, 'named actor must already own real Deck content').toBeGreaterThan(0);
  const eligible = payload.decks.filter(isHomeVisible);
  const ineligible = payload.decks.filter((deck) => !isHomeVisible(deck));

  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  await page.goto(`${WEB_BASE}/story-workspace/decks`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  const launcher = page.locator('[data-deck-manager-launcher]');
  await expect(launcher).toBeVisible();
  await expect(launcher.locator('.deck-manager-enabled__item')).toHaveCount(Math.min(eligible.length, 14));
  await expect(launcher.locator('.deck-manager-launch-card')).toHaveCount(eligible.length);
  for (const deck of eligible) {
    await expect(launcher.locator(`[data-deck-home-id="${deck.id}"]`)).toHaveCount(2);
  }
  for (const deck of ineligible) {
    await expect(launcher.locator(`[data-deck-home-id="${deck.id}"]`)).toHaveCount(0);
  }
  await expect(launcher.locator('.deck-manager-enabled__item--system')).toHaveCount(
    eligible.filter((deck) => deck.is_system).slice(0, 14).length,
  );
  await expect(launcher.locator('.deck-manager-launch-card--system')).toHaveCount(
    eligible.filter((deck) => deck.is_system).length,
  );
  if (eligible.length === 0) {
    await expect(launcher.getByText('当前没有已启用、已发布且无草稿变更的 Deck。')).toBeVisible();
  }
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/real-deck-home-published-filter-wide.png',
    fullPage: true,
  });

  await launcher.getByRole('button', { name: '打开 Deck 设置' }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/settings/work`);
  await expect(page.getByRole('heading', { name: '工作台', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '工作台 / Work', exact: true })).toHaveCount(0);
  const workList = page.getByRole('list', { name: 'Deck 设置列表' });
  await expect(workList).toBeVisible();
  for (const deck of payload.decks) {
    await expect(workList.locator(`[data-deck-card-id="${deck.id}"]`)).toBeVisible();
  }

  const inspectedDeck = payload.decks.find((deck) => !deck.is_system);
  expect(inspectedDeck, 'named actor must own a manageable Deck').toBeTruthy();
  const relatedResponse = await page.request.get(
    `${WEB_BASE}/api/claude-agent/threads?deck_id=${encodeURIComponent(inspectedDeck!.id)}&limit=20`,
    { headers },
  );
  expect(relatedResponse.status(), await relatedResponse.text()).toBe(200);
  const relatedPayload = await relatedResponse.json() as { threads: Array<{ id: string }> };
  const inspectedRow = workList.locator(`[data-deck-card-id="${inspectedDeck!.id}"]`);
  await inspectedRow.getByRole('button', { name: `${inspectedDeck!.name} 的更多操作` }).click();
  await page.getByRole('menuitem', { name: '相关对话' }).click();
  const relatedDialog = page.getByRole('dialog', { name: '相关对话' });
  await expect(relatedDialog).toBeVisible();
  await expect(relatedDialog.locator('.deck-manager-related-list__item')).toHaveCount(relatedPayload.threads.length);
  const deleteDeckButton = relatedDialog.getByRole('button', { name: '删除 Deck' });
  if (relatedPayload.threads.length > 0) await expect(deleteDeckButton).toBeDisabled();
  else await expect(deleteDeckButton).toBeEnabled();
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/real-deck-related-conversations-wide.png',
    fullPage: true,
  });
  await relatedDialog.getByRole('button', { name: '关闭' }).last().click();
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/real-deck-work-full-inventory-wide.png',
    fullPage: true,
  });

  const afterResponse = await page.request.get(`${WEB_BASE}/api/decks`, { headers });
  expect(afterResponse.status(), await afterResponse.text()).toBe(200);
  const afterPayload = await afterResponse.json() as { decks: RealDeck[] };
  expect(afterPayload.decks).toEqual(payload.decks);
  expect(reconcileRequests).toBeGreaterThan(0);
  expect(mutationRequests).toEqual([]);
  expect(diagnostics).toEqual([]);
});
