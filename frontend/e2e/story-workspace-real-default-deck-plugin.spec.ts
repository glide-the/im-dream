// [Input] Existing local default actor, normal Dream backend/PostgreSQL, and
//         Story Workspace Decks UI.
// [Output] Real-business proof that the named actor's management list searches,
//          filters, refreshes, reflows, hides unsupported version/market UI, opens
//          popup metadata area, and preserves the configured server-owned plugin ref through its existing API facts.
// [Pos] Opt-in real-data default-Deck plugin acceptance in frontend/e2e.
// [Sync] 2026-08-16: identify duplicate-name defaults by server ID and cover the
//                    real responsive list journey before popup metadata inspection.
// [Sync] 2026-08-16: verify the Deck route opens directly on its toolbar-first management list.
// [Sync] 2026-08-16: keep the popup metadata-only while verifying configured refs through normal services.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DEFAULT_DECK_PLUGIN_QA === '1';
const WEB_BASE = process.env.INK_REAL_DEFAULT_DECK_PLUGIN_QA_WEB_BASE;
const ACTOR_EMAIL = process.env.INK_REAL_DEFAULT_DECK_PLUGIN_QA_ACTOR_EMAIL;
const EXPECTED_PLUGIN_PACKAGE = process.env.INK_REAL_DEFAULT_DECK_PLUGIN_QA_PACKAGE;
const EXPECTED_PLUGIN_VERSION = process.env.INK_REAL_DEFAULT_DECK_PLUGIN_QA_VERSION;
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

/**
 * Business impact brief:
 *
 * | Fact | Authority | Expected impact |
 * | Default screenplay Deck identity/voices | decks + voices | unchanged |
 * | Default Deck Claude refs | deck_claude_plugin_refs | configured ready ref exists or the existing selection remains preserved |
 * | Plugin installation | claude_plugin_installations | unchanged; ready installation is referenced |
 * | Other Deck refs | deck_claude_plugin_refs | unchanged |
 * | Project/Episode/Run/Thread/files/billing | their existing authorities | out of scope and unchanged |
 */

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 800 },
});
test.skip(
  !ENABLED || !WEB_BASE || !ACTOR_EMAIL || !EXPECTED_PLUGIN_PACKAGE || !EXPECTED_PLUGIN_VERSION,
  'Set the real-QA flag, web base, actor email, default plugin package, and version explicitly.',
);

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

test('default account keeps the configured plugin while Deck management stays popup-scoped', async ({ page }) => {
  if (!WEB_BASE || !ACTOR_EMAIL || !EXPECTED_PLUGIN_PACKAGE || !EXPECTED_PLUGIN_VERSION) {
    throw new Error('Real Deck QA requires explicit host, actor, and plugin policy inputs.');
  }
  const token = createActorToken(ACTOR_EMAIL);
  const headers = { authorization: `Bearer ${token}` };
  const diagnostics = diagnosticsFor(page);
  const decksResponse = await page.request.get(`${WEB_BASE}/api/decks`, { headers });
  expect(decksResponse.status(), await decksResponse.text()).toBe(200);
  const decksPayload = await decksResponse.json() as {
    decks: Array<{
      id: string;
      name: string;
      name_zh?: string;
      agent_type?: 'chat' | 'dream';
      enabled?: boolean;
      can_publish?: boolean;
      publish_block_reason?: string | null;
    }>;
  };
  const screenplayDeck = decksPayload.decks.find(
    (deck) => deck.can_publish === false && deck.publish_block_reason === 'default_initialized',
  );
  expect(screenplayDeck, 'the named actor must have one server-identified default Deck').toBeTruthy();
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  await page.goto(`${WEB_BASE}/story-workspace/decks`);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await expect(page.getByRole('tab', { name: /使用 Deck|创作 Deck/ })).toHaveCount(0);
  const deckSettingsList = page.getByRole('list', { name: 'Deck 设置列表' });
  await expect(deckSettingsList).toBeVisible();
  await expect(page.locator('.deck-manager-home table')).toHaveCount(0);
  await expect(page.locator('.deck-manager-enabled__strip')).toBeVisible();
  await expect(page.getByText(/草稿状态|最新发布版本|可升级/)).toHaveCount(0);
  await expect(page.getByText(/发布到社区|我发布的卡组|安装/)).toHaveCount(0);
  const defaultDeck = page.locator(
    `[data-deck-card-kind="owned"][data-deck-card-id="${screenplayDeck!.id}"]`,
  );
  const search = page.getByRole('searchbox', { name: '搜索可管理的 Deck' });
  await search.fill('剧本创作团队');
  await expect(defaultDeck).toBeVisible();
  await page.getByRole('tab', {
    name: screenplayDeck!.agent_type === 'dream' ? /^Dream/ : /^Chat/,
  }).click();
  await expect(defaultDeck).toBeVisible();
  await page.getByLabel('按启用状态筛选').selectOption(screenplayDeck!.enabled ? 'disabled' : 'enabled');
  await expect(defaultDeck).toHaveCount(0);
  await page.getByRole('button', { name: '清除筛选' }).click();
  await page.getByRole('button', { name: '刷新', exact: true }).click();
  await expect(deckSettingsList).toBeVisible();

  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/real-deck-pdf-home-wide.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 640, height: 780 });
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  await expect(defaultDeck).toBeVisible();
  await expect(defaultDeck.locator('.deck-manager-list__description')).toBeVisible();
  expect((await defaultDeck.locator('.deck-manager-list__identity').boundingBox())?.height ?? 0)
    .toBeGreaterThanOrEqual(44);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/real-deck-pdf-home-narrow.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 1280, height: 800 });
  await defaultDeck.locator('.deck-manager-list__identity').click();

  const detailsDialog = page.getByRole('dialog', { name: /编辑 Deck|Deck 详情/ });
  await expect(detailsDialog).toBeVisible();
  await expect(detailsDialog.getByLabel('Deck 名称')).toHaveValue(screenplayDeck!.name);
  await expect(detailsDialog.getByText(EXPECTED_PLUGIN_PACKAGE)).toHaveCount(0);
  await expect(detailsDialog.getByText(/Agent Prompt|Memory|保存插件选择/)).toHaveCount(0);

  const refsResponse = await page.request.get(
    `${WEB_BASE}/api/decks/${encodeURIComponent(screenplayDeck!.id)}/claude-plugins`,
    { headers },
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
      package_spec: EXPECTED_PLUGIN_PACKAGE,
      resolved_version: EXPECTED_PLUGIN_VERSION,
      enabled: 1,
      installation_status: 'ready',
    }),
  ]));

  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/real-default-deck-lightweight-details.png',
    fullPage: true,
  });
  expect(diagnostics).toEqual([]);
});
