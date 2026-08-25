// [Input] Existing local Admin account plus the exact Gateway request IDs produced by the real MCP/Dream acceptance.
// [Output] Read-only visible Admin proof for request lifecycle and append-only subscription Token ledger rows.
// [Pos] Opt-in cross-system business acceptance; normal Admin login/logout and read routes only.
// [Sync] 2026-08-25: add real Gateway request and Token ledger visibility acceptance for MCP routing release evidence.
// [Sync] 2026-08-25: use Admin's configured localhost origin and tolerate only its known signed-out probe/id-only hydration diagnostics.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { mkdirSync } from 'node:fs';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_ADMIN_MCP_VISIBILITY_QA === '1';
const ADMIN_BASE = process.env.INK_REAL_ADMIN_MCP_BASE_URL ?? 'http://localhost:3000';
const ADMIN_EMAIL = process.env.INK_REAL_ADMIN_MCP_EMAIL ?? '';
const ADMIN_PASSWORD = process.env.INK_REAL_ADMIN_MCP_PASSWORD ?? '';
const ACTOR_EMAIL = process.env.INK_REAL_ADMIN_MCP_ACTOR_EMAIL ?? '';
const REQUEST_IDS = (process.env.INK_REAL_ADMIN_MCP_REQUEST_IDS ?? '')
  .split(',')
  .map((value) => value.trim())
  .filter(Boolean);
const EVIDENCE_DIR = resolve(process.cwd(), 'output/playwright/mcp-auth-routing');

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1440, height: 1000 },
});
test.skip(!ENABLED, 'Run only with the named local Admin and real Gateway request IDs.');

function requireInputs(): void {
  if (!ADMIN_EMAIL || !ADMIN_PASSWORD || !ACTOR_EMAIL || REQUEST_IDS.length < 2) {
    throw new Error('Admin credentials, actor email, and at least two Gateway request IDs are required.');
  }
  if (new Set(REQUEST_IDS).size !== REQUEST_IDS.length) {
    throw new Error('Gateway request IDs must be unique.');
  }
  if (!REQUEST_IDS.every((value) => /^req_[0-9a-f]{32}$/.test(value))) {
    throw new Error('Every Gateway request ID must use the canonical req_<hex> form.');
  }
}

function diagnosticsFor(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    const text = message.text();
    if (message.type() === 'error'
      && !/(?:react-grab\.com|react-grab\.js|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(text)
      // The signed-out login probe is expected to receive 401 before credentials are submitted.
      && !/^Failed to load resource: the server responded with a status of 401 \(Unauthorized\)$/.test(text)
      // Admin currently emits an id-only React useId hydration warning; it does not affect these read paths.
      && !/^A tree hydrated but some attributes of the server rendered HTML didn't match/.test(text)) {
      diagnostics.push(`console: ${text}`);
    }
  });
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText !== 'net::ERR_ABORTED') {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
    }
  });
  page.on('response', (response) => {
    if (response.status() >= 500 && response.url().includes('/api/')) {
      diagnostics.push(`http ${response.status()}: ${new URL(response.url()).pathname}`);
    }
  });
  return diagnostics;
}

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  await expect.poll(async () => page.evaluate(() => (
    document.documentElement.scrollWidth - document.documentElement.clientWidth
  ))).toBeLessThanOrEqual(1);
}

test('Admin can query this release acceptance in Gateway requests and Token ledger', async ({
  page,
}) => {
  test.setTimeout(120_000);
  requireInputs();
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  const diagnostics = diagnosticsFor(page);
  await page.route('http://unpkg.com/react-grab/dist/index.global.js', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/javascript', body: '' });
  });

  await page.goto(`${ADMIN_BASE}/admin/login`);
  await page.getByLabel('管理员邮箱').fill(ADMIN_EMAIL);
  await page.getByLabel('密码').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: '登录控制台' }).click();
  await expect(page).toHaveURL(`${ADMIN_BASE}/admin`);

  await page.goto(`${ADMIN_BASE}/admin/gateway/requests`);
  await expect(page.getByRole('heading', { name: '请求日志', exact: true })).toBeVisible();
  const requestPanel = page.locator('section.admin-panel').filter({
    has: page.getByRole('heading', { name: 'Gateway 请求', exact: true }),
  });
  await requestPanel.getByRole('button', { name: '展开筛选' }).click();
  await requestPanel.getByLabel('用户邮箱').fill(ACTOR_EMAIL);
  await requestPanel.getByRole('button', { name: '应用' }).click();

  for (const requestId of REQUEST_IDS) {
    const row = requestPanel.locator('tbody tr').filter({ hasText: requestId });
    await expect(row).toBeVisible({ timeout: 30_000 });
    await expect(row).toContainText('settled');
    await expect(row).toContainText('succeeded');
  }
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: resolve(EVIDENCE_DIR, 'admin-gateway-requests.png'),
    fullPage: true,
  });

  for (const [index, requestId] of REQUEST_IDS.entries()) {
    await requestPanel.getByRole('button', { name: `查看 ${requestId} 详情` }).click();
    const dialog = page.getByRole('dialog', { name: '请求详情' });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(requestId);
    await expect(dialog).toContainText('settled');
    await expect(dialog).toContainText('succeeded');
    await expect(dialog).toContainText('200');
    if (index === 0) {
      await page.screenshot({
        path: resolve(EVIDENCE_DIR, 'admin-gateway-request-detail.png'),
        fullPage: true,
      });
    }
    await dialog.getByRole('button', { name: '关闭', exact: true }).click();
    await expect(dialog).toBeHidden();
  }

  const ledgerRequestId = REQUEST_IDS.at(-1)!;
  await page.goto(`${ADMIN_BASE}/admin/subscriptions/token-ledger`);
  await expect(page.getByRole('heading', { name: 'Token 流水', exact: true })).toBeVisible();
  const ledgerPanel = page.locator('section.admin-panel').filter({
    has: page.getByRole('heading', { name: 'Gateway Token 使用流水', exact: true }),
  });
  await ledgerPanel.getByRole('button', { name: '展开筛选' }).click();
  await ledgerPanel.getByLabel('Gateway Request').fill(ledgerRequestId);
  await ledgerPanel.getByRole('button', { name: '应用' }).click();
  const ledgerRows = ledgerPanel.locator('tbody tr').filter({ hasText: ledgerRequestId });
  await expect(ledgerRows).toHaveCount(3, { timeout: 30_000 });
  await expect(ledgerPanel).toContainText('reserve');
  await expect(ledgerPanel).toContainText('capture');
  await expect(ledgerPanel).toContainText('release');
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: resolve(EVIDENCE_DIR, 'admin-token-ledger.png'),
    fullPage: true,
  });

  expect(diagnostics).toEqual([]);
  await page.getByRole('button', { name: '退出管理后台' }).click();
  await expect(page).toHaveURL(`${ADMIN_BASE}/admin/login`);
});
